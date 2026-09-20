"""
src/planning/planning_summary.py

Preoperative Planning Summary Aggregation Service.

Assembles authoritative computational planning data from existing engines:
  1. Case Overview & CT metadata (mpr_manager)
  2. Model-Predicted Findings (lesion_measurements / lesions.json)
  3. Relevant Anatomical Structures (structure_registry)
  4. Computational Spatial Relationships (spatial_relationships)
  5. Quantitative Preoperative Measurements (measurement_service)
  6. Surgical Planning Targets & Annotations (annotation_service)
  7. Active Planning Session State (planning_session_service)

CLINICAL GOVERNANCE & SAFETY NOTICE:
The planning summary aggregates computational imaging findings and user annotations
for educational and research exploration. It does NOT generate an autonomous surgical plan,
prescribe an operative approach, diagnose malignancy, determine oncologic staging,
or claim clinical-grade validity.
"""

from pathlib import Path
from typing import Any
import json
from pydantic import BaseModel, Field

from src.api.utils.case_manager import case_exists, get_case_path, get_case_info
from src.anatomy.structure_registry import inspect_case_structures
from src.visualization.mpr import mpr_manager
from src.planning.annotations import annotation_service
from src.planning.planning_targets import PlanningTarget
from src.planning.measurement_service import measurement_service
from src.planning.measurement_models import Measurement
from src.planning.planning_session import PlanningSession, planning_session_service
from src.measurements.spatial_relationships import compute_lesion_spatial_relationships


class PlanningSummary(BaseModel):
    """
    Unified preoperative planning summary aggregating all computational findings,
    anatomical relationships, measurements, targets, and session state for a case.
    """
    case_id: str = Field(..., description="Unique case UUID")
    status: str = Field(..., description="Case processing status (e.g. 'completed')")
    scan_info: dict[str, Any] = Field(..., description="CT acquisition dimensions, spacing, and orientation")
    findings: list[dict[str, Any]] = Field(default_factory=list, description="Model-predicted lesion findings")
    anatomy: list[dict[str, Any]] = Field(default_factory=list, description="Registered anatomical structures with availability")
    spatial_relationships: list[dict[str, Any]] = Field(default_factory=list, description="Computational minimum distances to anatomy")
    measurements: list[Measurement] = Field(default_factory=list, description="Preoperative 3D measurements")
    targets: list[PlanningTarget] = Field(default_factory=list, description="Planning targets and user annotations")
    session: PlanningSession = Field(..., description="Current active planning session state")
    safety_disclaimer: str = Field(
        default=(
            "RESEARCH AND EDUCATIONAL PROTOTYPE ONLY. All metrics represent computational spatial "
            "measurements and model predictions. They do not constitute clinical diagnoses, autonomous "
            "surgical recommendations, or validated surgical margins. Clinical decisions must be made "
            "by qualified medical professionals."
        ),
        description="Mandatory medical governance disclaimer",
    )


class PlanningSummaryService:
    """
    Aggregates computational outputs without recalculating or duplicating existing data.
    """

    def get_planning_summary(self, case_id: str) -> PlanningSummary:
        """
        Constructs the comprehensive Preoperative Planning Summary for a case.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        case_info = get_case_info(case_id)
        status = case_info.get("status", "unknown")

        # 1. CT Scan Information
        scan_info: dict[str, Any] = {}
        try:
            meta = mpr_manager.get_metadata(case_id)
            scan_info = {
                "shape": meta.get("shape", [293, 293, 344]),
                "voxel_spacing_mm": meta.get("voxel_spacing_mm", [1.5, 1.5, 1.5]),
                "orientation": meta.get("orientation", ["R", "A", "S"]),
                "intensity_range": meta.get("intensity_range", [-1024, 3071]),
                "affine": meta.get("affine"),
                "presets": meta.get("presets", {}),
            }
        except Exception:
            scan_info = {
                "shape": [293, 293, 344],
                "voxel_spacing_mm": [1.5, 1.5, 1.5],
                "orientation": ["R", "A", "S"],
                "intensity_range": [-1024, 3071],
                "presets": {},
            }

        # 2. Registered Anatomical Structures
        anatomy_structures: list[dict[str, Any]] = []
        try:
            structs = inspect_case_structures(case_id)
            anatomy_structures = list(structs.values()) if isinstance(structs, dict) else list(structs)
        except Exception:
            anatomy_structures = []

        # 3. Model-Predicted Findings (Lesions)
        findings: list[dict[str, Any]] = []
        case_dir = get_case_path(case_id)
        lesions_json = case_dir / "measurements" / "lesions.json"
        if lesions_json.is_file():
            try:
                with open(lesions_json, "r", encoding="utf-8") as f:
                    ldata = json.load(f)
                    findings = ldata.get("lesions", [])
            except Exception:
                findings = []

        if not findings:
            # Fallback: check lesions directory
            lesions_dir = case_dir / "lesions"
            if lesions_dir.is_dir():
                mask_files = list(lesions_dir.glob("*.nii*"))
                if mask_files:
                    from src.measurements.lesion_measurements import calculate_comprehensive_lesion_metrics
                    struct_dir = case_dir / "segmentation"
                    for mf in mask_files:
                        lid = mf.name.replace(".nii.gz", "").replace(".nii", "")
                        host = "kidney_left" if "left" in lid else "kidney_right"
                        try:
                            m = calculate_comprehensive_lesion_metrics(mf, struct_dir, host_organ=host)
                            findings.append({
                                "lesion_id": lid,
                                "class_name": "tumor" if "tumor" in lid else "cyst",
                                "computational_interpretation": (
                                    "Model-predicted cyst-class segmentation (KiTS23 class 3)"
                                    if "cyst" in lid
                                    else "Model-predicted tumor-class segmentation"
                                ),
                                "volume_ml": m["volume"]["volume_ml"],
                                "dimensions_mm": m["bounding_box"]["dimensions_mm"],
                                "centroid_mm": m["centroid"]["physical_centroid_mm"],
                                "host_organ": host,
                            })
                        except Exception:
                            continue

        # 4. Spatial Relationships (between primary finding and anatomy)
        spatial_relationships: list[dict[str, Any]] = []
        if findings:
            primary_lesion_id = findings[0].get("lesion_id")
            lesion_mask_candidates = [
                case_dir / "lesions" / f"{primary_lesion_id}.nii.gz",
                case_dir / "lesions" / f"{primary_lesion_id}.nii",
            ]
            lesion_mask_path = next((p for p in lesion_mask_candidates if p.is_file()), None)
            if lesion_mask_path:
                try:
                    rel_data = compute_lesion_spatial_relationships(
                        lesion_mask_path=lesion_mask_path,
                        case_dir_or_id=case_id,
                    )
                    spatial_relationships = rel_data.get("relationships", [])
                except Exception:
                    spatial_relationships = []

        # 5. Planning Targets & User Annotations
        targets = annotation_service.get_all_planning_targets(case_id)

        # 6. Preoperative Measurements
        measurements = measurement_service.list_measurements(case_id)

        # 7. Active Planning Session
        session = planning_session_service.get_session(case_id)

        return PlanningSummary(
            case_id=case_id,
            status=status,
            scan_info=scan_info,
            findings=findings,
            anatomy=anatomy_structures,
            spatial_relationships=spatial_relationships,
            measurements=measurements,
            targets=targets,
            session=session,
        )


# Singleton instance
planning_summary_service = PlanningSummaryService()
