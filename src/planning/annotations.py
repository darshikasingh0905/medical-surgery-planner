"""
src/planning/annotations.py

Annotation Management Service for Preoperative Surgical Planning.

Provides persistent storage, retrieval, lifecycle management, and coordinate
synchronization for user-created planning annotations and model-predicted targets.

Persists user annotations in:
    outputs/cases/<case_id>/planning/annotations.json

CLINICAL GOVERNANCE NOTICE:
Planning targets and annotations are visualization and organizational aids for
research/educational preoperative analysis. They do not constitute autonomous
surgical plans, clinical diagnoses, or validated margins.
"""

from pathlib import Path
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from src.planning.planning_targets import (
    PlanningTarget,
    TargetType,
    TargetSource,
    AnnotationCreateRequest,
    AnnotationUpdateRequest,
)
from src.api.utils.case_manager import case_exists, get_case_path
from src.visualization.mpr import (
    mpr_manager,
    voxel_to_physical,
    physical_to_voxel,
)


class AnnotationService:
    """
    Manages persistence and retrieval of surgical planning annotations and targets.
    """

    def _get_planning_dir(self, case_id: str) -> Path:
        """Resolves outputs/cases/<case_id>/planning directory."""
        case_dir = get_case_path(case_id)
        planning_dir = case_dir / "planning"
        planning_dir.mkdir(parents=True, exist_ok=True)
        return planning_dir

    def _get_annotations_file(self, case_id: str) -> Path:
        """Resolves path to annotations.json."""
        return self._get_planning_dir(case_id) / "annotations.json"

    def _load_annotations_raw(self, case_id: str) -> dict[str, Any]:
        """Loads the raw annotations JSON file, initializing if absent."""
        ann_file = self._get_annotations_file(case_id)
        if not ann_file.is_file():
            return {"case_id": case_id, "annotations": []}
        try:
            with open(ann_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict) or "annotations" not in data:
                    return {"case_id": case_id, "annotations": []}
                return data
        except Exception:
            return {"case_id": case_id, "annotations": []}

    def _save_annotations_raw(self, case_id: str, data: dict[str, Any]) -> None:
        """Saves the annotations data to annotations.json atomically."""
        ann_file = self._get_annotations_file(case_id)
        temp_file = ann_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_file.replace(ann_file)

    def _get_volume_meta(self, case_id: str) -> tuple[tuple[int, int, int], tuple[float, float, float]]:
        """
        Retrieves volume shape and voxel spacing from mpr_manager or sensible fallback.
        """
        try:
            meta = mpr_manager.get_metadata(case_id)
            shape = tuple(meta["shape"])
            spacing = tuple(meta["voxel_spacing_mm"])
            return shape, spacing
        except Exception:
            # Fallback standard spacing if CT volume metadata loading is delayed
            return (512, 512, 512), (1.5, 1.5, 1.5)

    def validate_voxel_bounds(self, case_id: str, voxel_coord: list[int]) -> None:
        """
        Validates that voxel coordinate is within the actual CT volume boundaries.
        Raises ValueError if out of bounds.
        """
        shape, _ = self._get_volume_meta(case_id)
        x, y, z = voxel_coord
        nx, ny, nz = shape
        if not (0 <= x < nx and 0 <= y < ny and 0 <= z < nz):
            raise ValueError(
                f"Voxel coordinate [{x}, {y}, {z}] is out of bounds for volume shape {list(shape)}."
            )

    # ─────────────────────────────────────────────────────────────────
    # User Annotations CRUD
    # ─────────────────────────────────────────────────────────────────

    def list_user_annotations(self, case_id: str) -> list[PlanningTarget]:
        """Returns all persistent user-created planning annotations for a case."""
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        raw_data = self._load_annotations_raw(case_id)
        targets: list[PlanningTarget] = []
        for item in raw_data.get("annotations", []):
            try:
                targets.append(PlanningTarget(**item))
            except Exception:
                continue
        return targets

    def get_user_annotation(self, case_id: str, annotation_id: str) -> PlanningTarget | None:
        """Retrieves a single user annotation by ID."""
        annotations = self.list_user_annotations(case_id)
        for ann in annotations:
            if ann.target_id == annotation_id:
                return ann
        return None

    def create_user_annotation(
        self, case_id: str, req: AnnotationCreateRequest
    ) -> PlanningTarget:
        """Creates and persists a new user planning annotation."""
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        self.validate_voxel_bounds(case_id, req.voxel_coordinate)

        _, spacing = self._get_volume_meta(case_id)

        # Synchronize physical coordinate
        if req.physical_coordinate is not None and len(req.physical_coordinate) == 3:
            phys_coord = [round(float(c), 3) for c in req.physical_coordinate]
        else:
            phys_coord = voxel_to_physical(spacing, req.voxel_coordinate)

        target_id = f"ann_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        target = PlanningTarget(
            target_id=target_id,
            target_type=req.target_type,
            label=req.label,
            source=TargetSource.USER,
            voxel_coordinate=req.voxel_coordinate,
            physical_coordinate=phys_coord,
            lesion_id=req.lesion_id,
            structure_id=req.structure_id,
            notes=req.notes,
            created_at=now_iso,
        )

        raw_data = self._load_annotations_raw(case_id)
        raw_data["annotations"].append(target.model_dump())
        self._save_annotations_raw(case_id, raw_data)

        return target

    def update_user_annotation(
        self, case_id: str, annotation_id: str, req: AnnotationUpdateRequest
    ) -> PlanningTarget | None:
        """Updates label, notes, or coordinates of an existing user annotation."""
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        raw_data = self._load_annotations_raw(case_id)
        found_idx = -1
        for idx, item in enumerate(raw_data.get("annotations", [])):
            if item.get("target_id") == annotation_id:
                found_idx = idx
                break

        if found_idx == -1:
            return None

        current = raw_data["annotations"][found_idx]

        if req.label is not None:
            current["label"] = req.label
        if req.notes is not None:
            current["notes"] = req.notes

        if req.voxel_coordinate is not None:
            self.validate_voxel_bounds(case_id, req.voxel_coordinate)
            current["voxel_coordinate"] = req.voxel_coordinate
            _, spacing = self._get_volume_meta(case_id)
            if req.physical_coordinate is not None:
                current["physical_coordinate"] = [round(float(c), 3) for c in req.physical_coordinate]
            else:
                current["physical_coordinate"] = voxel_to_physical(spacing, req.voxel_coordinate)
        elif req.physical_coordinate is not None:
            current["physical_coordinate"] = [round(float(c), 3) for c in req.physical_coordinate]

        updated_target = PlanningTarget(**current)
        raw_data["annotations"][found_idx] = updated_target.model_dump()
        self._save_annotations_raw(case_id, raw_data)

        return updated_target

    def delete_user_annotation(self, case_id: str, annotation_id: str) -> bool:
        """Deletes a user planning annotation by ID."""
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        raw_data = self._load_annotations_raw(case_id)
        annotations = raw_data.get("annotations", [])
        initial_len = len(annotations)
        raw_data["annotations"] = [a for a in annotations if a.get("target_id") != annotation_id]

        if len(raw_data["annotations"]) < initial_len:
            self._save_annotations_raw(case_id, raw_data)
            return True
        return False

    def create_annotation_from_lesion(
        self, case_id: str, lesion_id: str, label: str | None = None, notes: str | None = None
    ) -> PlanningTarget:
        """
        Creates a user-focused planning annotation anchored to a model-predicted lesion.
        Validates lesion existence and extracts centroid coordinates.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        # Resolve lesion metrics
        case_dir = get_case_path(case_id)
        lesions_json_path = case_dir / "measurements" / "lesions.json"

        lesion_data = None
        if lesions_json_path.is_file():
            with open(lesions_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for l_item in data.get("lesions", []):
                    if l_item.get("lesion_id") == lesion_id:
                        lesion_data = l_item
                        break

        if lesion_data is None:
            # Check if mask file exists on disk
            mask_path = case_dir / "lesions" / f"{lesion_id}.nii.gz"
            if not mask_path.is_file():
                mask_candidates = list((case_dir / "lesions").glob(f"{lesion_id}*.nii*"))
                if mask_candidates:
                    mask_path = mask_candidates[0]
                else:
                    raise FileNotFoundError(f"Lesion '{lesion_id}' not found in case '{case_id}'.")

            from src.measurements.lesion_measurements import calculate_comprehensive_lesion_metrics
            host = "kidney_left" if "left" in lesion_id else "kidney_right"
            struct_dir = case_dir / "segmentation"
            metrics = calculate_comprehensive_lesion_metrics(mask_path, struct_dir, host_organ=host)
            lesion_data = {
                "lesion_id": lesion_id,
                "class_name": "tumor" if "tumor" in lesion_id else "cyst",
                "computational_interpretation": (
                    "Model-predicted cyst-class segmentation" if "cyst" in lesion_id
                    else "Model-predicted tumor-class segmentation"
                ),
                "volume_ml": metrics["volume"]["volume_ml"],
                "dimensions_mm": metrics["bounding_box"]["dimensions_mm"],
                "centroid_mm": metrics["centroid"]["physical_centroid_mm"],
                "host_organ": host,
            }

        shape, spacing = self._get_volume_meta(case_id)
        centroid_phys = lesion_data["centroid_mm"]
        centroid_vox = physical_to_voxel(spacing, centroid_phys)

        self.validate_voxel_bounds(case_id, centroid_vox)

        ann_label = label or f"Target: {lesion_data.get('computational_interpretation', lesion_id)}"
        ann_notes = notes or f"Referencing model-derived lesion {lesion_id} (volume: {lesion_data.get('volume_ml', 0):.3f} mL)"

        req = AnnotationCreateRequest(
            label=ann_label,
            target_type=TargetType.LESION,
            voxel_coordinate=centroid_vox,
            physical_coordinate=centroid_phys,
            notes=ann_notes,
            structure_id=lesion_data.get("host_organ"),
            lesion_id=lesion_id,
        )

        return self.create_user_annotation(case_id, req)

    # ─────────────────────────────────────────────────────────────────
    # Auto-Generated Model Findings as Planning Targets
    # ─────────────────────────────────────────────────────────────────

    def get_model_lesion_targets(self, case_id: str) -> list[PlanningTarget]:
        """
        Exposes existing model-predicted lesion findings as planning targets.
        Preserves lesion ID, class, centroid, volume, dimensions, and provenance.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        case_dir = get_case_path(case_id)
        lesions_json_path = case_dir / "measurements" / "lesions.json"

        lesion_list = []
        if lesions_json_path.is_file():
            try:
                with open(lesions_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    lesion_list = data.get("lesions", [])
            except Exception:
                lesion_list = []

        if not lesion_list:
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
                            lesion_list.append({
                                "lesion_id": lid,
                                "class_name": "tumor" if "tumor" in lid else "cyst",
                                "computational_interpretation": (
                                    "Model-predicted cyst-class segmentation" if "cyst" in lid
                                    else "Model-predicted tumor-class segmentation"
                                ),
                                "volume_ml": m["volume"]["volume_ml"],
                                "dimensions_mm": m["bounding_box"]["dimensions_mm"],
                                "centroid_mm": m["centroid"]["physical_centroid_mm"],
                                "host_organ": host,
                            })
                        except Exception:
                            continue

        shape, spacing = self._get_volume_meta(case_id)
        targets: list[PlanningTarget] = []

        for lesion in lesion_list:
            lid = lesion.get("lesion_id")
            centroid_phys = lesion.get("centroid_mm")
            if not centroid_phys or len(centroid_phys) != 3:
                continue

            centroid_vox = physical_to_voxel(spacing, centroid_phys)
            # Clamp or validate
            target_id = f"model_{lid}"
            interpretation = lesion.get("computational_interpretation") or f"Model-predicted {lesion.get('class_name', 'lesion')}"

            targets.append(
                PlanningTarget(
                    target_id=target_id,
                    target_type=TargetType.LESION,
                    label=interpretation,
                    source=TargetSource.MODEL,
                    voxel_coordinate=centroid_vox,
                    physical_coordinate=centroid_phys,
                    lesion_id=lid,
                    structure_id=lesion.get("host_organ"),
                    notes=f"Automated KiTS23 model finding. Centroid: ({centroid_phys[0]:.1f}, {centroid_phys[1]:.1f}, {centroid_phys[2]:.1f}) mm",
                    volume_ml=lesion.get("volume_ml"),
                    dimensions_mm=lesion.get("dimensions_mm"),
                    computational_interpretation=interpretation,
                    host_organ=lesion.get("host_organ"),
                )
            )

        return targets

    def get_all_planning_targets(self, case_id: str) -> list[PlanningTarget]:
        """
        Combines model-predicted lesion targets and user annotations.
        """
        model_targets = self.get_model_lesion_targets(case_id)
        user_annotations = self.list_user_annotations(case_id)
        return model_targets + user_annotations


# Singleton instance
annotation_service = AnnotationService()
