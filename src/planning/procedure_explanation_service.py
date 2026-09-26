"""
src/planning/procedure_explanation_service.py

Day 21 - Procedure Explanation Generation Service.

Consumes existing case/planning services to build a deterministic
ProcedureExplanation from validated computational data.

Architecture:
  case_id
    -> planning_summary_service.get_planning_summary(case_id)
    -> explanation_builder
    -> ProcedureExplanation

GOVERNANCE:
  - No LLM or generative AI is used.
  - No external AI API is called.
  - Output is deterministic and traceable.
  - No clinical recommendations are generated.
  - No surgical approach is suggested.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.api.utils.case_manager import case_exists, get_case_path, get_case_info
from src.planning.planning_summary import planning_summary_service
from src.planning.procedure_explanation import (
    ProcedureExplanation,
    CaseOverview,
    ComputationalFinding,
    AnatomyItem,
    RelationshipItem,
    MeasurementItem,
    PlanningTargetItem,
    GeneralProceduralContext,
    ClinicalReviewItem,
    LimitationItem,
    ExplanationProvenance,
)


# ---------------------------------------------------------------------------
# Static procedural context (TECHNICAL audience)
# ---------------------------------------------------------------------------
_TECHNICAL_CONTEXT_ITEMS = [
    {
        "heading": "Preoperative CT Review",
        "text": (
            "CT imaging data can be reviewed to understand the three-dimensional "
            "spatial arrangement of anatomical structures and computational findings "
            "prior to a clinical encounter. Multi-planar reconstruction (MPR) allows "
            "review in axial, coronal, and sagittal planes."
        ),
    },
    {
        "heading": "Anatomy Localization",
        "text": (
            "Anatomical segmentation produces binary masks identifying organ boundaries "
            "in CT coordinate space. These masks enable visualization and spatial "
            "relationship computation between structures."
        ),
    },
    {
        "heading": "Lesion Size and Location Measurements",
        "text": (
            "Volume, bounding-box dimensions, and centroid coordinates are computed "
            "from segmentation mask voxel counts and the CT affine transform. These "
            "measurements characterize the spatial extent of the computational finding "
            "in physical millimeter space."
        ),
    },
    {
        "heading": "Spatial Relationship Assessment",
        "text": (
            "Minimum Euclidean distances between the lesion mask and anatomical "
            "structure masks are computed using k-d tree nearest-neighbor queries in "
            "physical coordinate space. These values describe computational proximity "
            "between segmented regions."
        ),
    },
    {
        "heading": "Multi-Planar Review",
        "text": (
            "Reviewing a finding in multiple imaging planes (axial, coronal, sagittal) "
            "may help contextualize its relationship to surrounding anatomy. The "
            "synchronized 3D and MPR viewer allows cursor-linked navigation."
        ),
    },
    {
        "heading": "Imaging vs. Intraoperative Anatomy",
        "text": (
            "Preoperative imaging represents anatomy at the time of CT acquisition. "
            "Intraoperative findings may differ due to tissue deformation, patient "
            "positioning, physiological changes, or structures not captured by CT "
            "segmentation."
        ),
    },
]

# ---------------------------------------------------------------------------
# Static procedural context (GENERAL audience)
# ---------------------------------------------------------------------------
_GENERAL_CONTEXT_ITEMS = [
    {
        "heading": "What Is This Image Review?",
        "text": (
            "CT scans produce detailed cross-sectional images of the body. Computer "
            "software can be used to review these images and identify the location "
            "and size of structures or findings."
        ),
    },
    {
        "heading": "Why Is Location Important?",
        "text": (
            "Understanding where a finding is located relative to surrounding anatomy "
            "helps medical teams review imaging before any clinical decisions are made. "
            "This system shows the computed location of findings in the scan."
        ),
    },
    {
        "heading": "What Are These Measurements?",
        "text": (
            "The measurements shown here are computed distances and sizes in "
            "millimeters, derived from the CT scan data. They describe the "
            "spatial characteristics of computationally identified findings."
        ),
    },
    {
        "heading": "Why Are Multiple Views Shown?",
        "text": (
            "Looking at a scan from different directions (top-to-bottom, front-to-back, "
            "and side-to-side) helps build a complete picture of where a finding is "
            "located in three dimensions."
        ),
    },
    {
        "heading": "Scan vs. Surgery",
        "text": (
            "A CT scan shows what the body looks like at the time the scan was taken. "
            "Actual anatomy seen during a procedure may differ. All clinical decisions "
            "are made by qualified medical professionals."
        ),
    },
]

# ---------------------------------------------------------------------------
# Static clinical review items
# ---------------------------------------------------------------------------
_CLINICAL_REVIEW_ITEMS: list[dict] = [
    {
        "item_id": "cr_diagnosis",
        "category": "diagnosis",
        "statement": (
            "Clinical diagnosis requires review by a qualified clinician. "
            "This system does not establish a diagnosis."
        ),
    },
    {
        "item_id": "cr_pathology",
        "category": "pathology",
        "statement": (
            "Model class assignments (cyst, tumor) are computational segmentation "
            "outputs and do not establish pathological diagnosis or malignancy."
        ),
    },
    {
        "item_id": "cr_staging",
        "category": "staging",
        "statement": (
            "Oncologic staging cannot be determined from computational imaging "
            "segmentation. Clinical staging requires clinician evaluation."
        ),
    },
    {
        "item_id": "cr_operative_approach",
        "category": "operative_approach",
        "statement": (
            "Surgical approach selection requires clinician decision-making based on "
            "complete clinical evaluation. This system does not recommend an operative approach."
        ),
    },
    {
        "item_id": "cr_operative_feasibility",
        "category": "feasibility",
        "statement": (
            "Operative feasibility cannot be determined from this prototype. "
            "Surgical risk assessment requires qualified clinical judgment."
        ),
    },
    {
        "item_id": "cr_vascular_anatomy",
        "category": "segmentation",
        "statement": (
            "Renal vascular anatomy (renal artery, renal vein) was not fully "
            "segmented in the standard TotalSegmentator 117-class output. "
            "Vascular proximity relationships are not available for these structures."
        ),
    },
    {
        "item_id": "cr_imaging_fidelity",
        "category": "imaging",
        "statement": (
            "Imaging findings may not represent intraoperative anatomy due to tissue "
            "deformation, patient positioning, and physiological changes not "
            "captured in the preoperative CT scan."
        ),
    },
    {
        "item_id": "cr_model_uncertainty",
        "category": "model",
        "statement": (
            "Segmentation model outputs carry inherent uncertainty. Small or "
            "atypical lesions may be subject to partial-volume effects or "
            "reduced model confidence."
        ),
    },
]

# ---------------------------------------------------------------------------
# Static limitations
# ---------------------------------------------------------------------------
_LIMITATIONS: list[dict] = [
    {
        "limitation_id": "lim_single_case",
        "domain": "validation",
        "description": (
            "This prototype has been validated on a single real case "
            "(case_id: b2f89382-9416-4e94-9486-b00c6b1de64b). "
            "Generalizability to other cases has not been established."
        ),
    },
    {
        "limitation_id": "lim_segmentation_availability",
        "domain": "segmentation",
        "description": (
            "Anatomical structure availability depends on TotalSegmentator output. "
            "Structures not present in the 117-class model (e.g. renal vessels, "
            "ureter, renal pelvis) cannot be visualized or measured."
        ),
    },
    {
        "limitation_id": "lim_model_uncertainty",
        "domain": "model",
        "description": (
            "KiTS23 segmentation model predictions carry inherent uncertainty. "
            "No confidence scores or uncertainty bounds are currently propagated "
            "into the explanation output."
        ),
    },
    {
        "limitation_id": "lim_partial_volume",
        "domain": "imaging",
        "description": (
            "Small lesions near the voxel resolution limit may be subject to "
            "partial-volume effects, potentially affecting volume and dimension "
            "accuracy."
        ),
    },
    {
        "limitation_id": "lim_no_deformation",
        "domain": "geometry",
        "description": (
            "No intraoperative tissue deformation modeling is performed. "
            "Physical CT coordinates do not account for positional changes "
            "between imaging and any subsequent procedure."
        ),
    },
    {
        "limitation_id": "lim_no_vascular_subseg",
        "domain": "segmentation",
        "description": (
            "Sub-segmentation of renal vasculature (renal artery, renal vein) "
            "is not available in the current TotalSegmentator configuration "
            "used for this case."
        ),
    },
    {
        "limitation_id": "lim_no_clinical_validation",
        "domain": "validation",
        "description": (
            "This system has not undergone clinical validation studies. "
            "It is a research and educational prototype only."
        ),
    },
]


def _build_host_display(host_organ: str | None) -> str | None:
    """Maps internal organ IDs to display names."""
    _MAP = {
        "kidney_left": "Left Kidney",
        "kidney_right": "Right Kidney",
        "aorta": "Abdominal Aorta",
        "inferior_vena_cava": "Inferior Vena Cava",
        "adrenal_gland_left": "Left Adrenal Gland",
        "adrenal_gland_right": "Right Adrenal Gland",
    }
    if host_organ is None:
        return None
    return _MAP.get(host_organ, host_organ.replace("_", " ").title())


def _build_relationship_interpretation(rel: dict) -> str:
    """Generates a neutral textual interpretation for a spatial relationship."""
    if not rel.get("available"):
        return "Not computed (structure not available)"
    if rel.get("overlap"):
        return "Overlap (masks share voxels)"
    dist = rel.get("distance_mm") or rel.get("computational_minimum_distance_mm")
    if dist is not None:
        return f"Separated — computational minimum distance: {dist:.2f} mm"
    return "Not computed"


class ProcedureExplanationService:
    """
    Deterministic service that builds a ProcedureExplanation from
    existing planning services.

    Data flow:
      case_id
        -> planning_summary_service.get_planning_summary()
        -> build each section
        -> ProcedureExplanation

    No LLM. No external API. No invented data.
    """

    def _get_ct_source(self, case_id: str) -> str | None:
        """Attempts to find the original CT filename for provenance."""
        try:
            case_path = get_case_path(case_id)
            input_dir = case_path / "input"
            if input_dir.is_dir():
                files = list(input_dir.glob("*.nii*"))
                if files:
                    return files[0].name
        except Exception:
            pass
        return None

    def _build_context(self, audience: str) -> GeneralProceduralContext:
        """Selects the appropriate context items based on audience."""
        items = (
            _TECHNICAL_CONTEXT_ITEMS
            if audience == "technical"
            else _GENERAL_CONTEXT_ITEMS
        )
        return GeneralProceduralContext(items=items, audience=audience)

    def _build_clinical_review_items(self) -> list[ClinicalReviewItem]:
        return [ClinicalReviewItem(**item) for item in _CLINICAL_REVIEW_ITEMS]

    def _build_limitations(self) -> list[LimitationItem]:
        return [LimitationItem(**lim) for lim in _LIMITATIONS]

    def generate_explanation(
        self,
        case_id: str,
        audience: str = "technical",
    ) -> ProcedureExplanation:
        """
        Generates a ProcedureExplanation for the given case.

        Args:
            case_id: Validated case UUID.
            audience: 'technical' or 'general'. Default: 'technical'.

        Returns:
            ProcedureExplanation — fully structured, traceable, deterministic.

        Raises:
            FileNotFoundError: If the case does not exist.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        if audience not in ("technical", "general"):
            audience = "technical"

        # --- Consume existing service (no recalculation) ---
        summary = planning_summary_service.get_planning_summary(case_id)

        # ── Case Overview ────────────────────────────────────────────────────
        scan = summary.scan_info or {}
        case_overview = CaseOverview(
            case_id=case_id,
            status=summary.status,
            scan_dimensions=scan.get("shape"),
            voxel_spacing_mm=scan.get("voxel_spacing_mm"),
            orientation=scan.get("orientation"),
            intensity_range_hu=scan.get("intensity_range"),
            processing_status=summary.status,
        )

        # ── Computational Findings ───────────────────────────────────────────
        findings_out: list[ComputationalFinding] = []
        for f in summary.findings:
            lid = f.get("lesion_id", "")
            base_interp = f.get("computational_interpretation") or lid.replace("_", " ").title()
            host_disp = _build_host_display(f.get("host_organ"))
            if audience == "general":
                cls_name = f.get("class_name", "finding")
                interp = (
                    f"Computational observation: An imaging region in the {host_disp or 'kidney'} "
                    f"was segmented by the algorithm as consistent with a {cls_name}. "
                    "This is an automated imaging assessment only and does not establish a medical diagnosis."
                )
            else:
                interp = base_interp

            # Resolve voxel centroid from target or physical coordinate / spacing
            centroid_voxel = f.get("centroid_voxel")
            if not centroid_voxel:
                for t in summary.targets:
                    if t.lesion_id == lid or t.target_id == f"model_{lid}" or (lid and lid in t.target_id):
                        centroid_voxel = t.voxel_coordinate
                        break
            if not centroid_voxel and f.get("centroid_mm") and scan.get("voxel_spacing_mm"):
                sp = scan.get("voxel_spacing_mm")
                cm = f.get("centroid_mm")
                centroid_voxel = [int(round(cm[i] / sp[i])) for i in range(3)]

            findings_out.append(
                ComputationalFinding(
                    finding_id=lid,
                    label=f.get("computational_interpretation") or lid.replace("_", " ").title(),
                    model_class=f.get("class_name", "unknown"),
                    host_organ=f.get("host_organ"),
                    host_organ_display=host_disp,
                    volume_ml=f.get("volume_ml"),
                    dimensions_mm=f.get("dimensions_mm"),
                    centroid_voxel=centroid_voxel,
                    centroid_physical_mm=f.get("centroid_mm"),
                    computational_interpretation=interp,
                    source_provenance=(
                        "KiTS23 renal segmentation model — cyst/tumor class inference. "
                        "Label class 3 = cyst."
                    ) if "cyst" in lid else (
                        "KiTS23 renal segmentation model — tumor/cyst class inference."
                    ),
                )
            )

        # ── Relevant Anatomy ─────────────────────────────────────────────────
        anatomy_out: list[AnatomyItem] = []
        primary_finding_id = findings_out[0].finding_id if findings_out else None
        for s in summary.anatomy:
            struct_id = s.get("structure_id", "")
            available = s.get("available", False)

            # Compute relationship description from spatial relationships
            rel_text = None
            if primary_finding_id and available:
                matched = next(
                    (
                        r
                        for r in summary.spatial_relationships
                        if r.get("structure_id") == struct_id
                    ),
                    None,
                )
                if matched:
                    rel_text = _build_relationship_interpretation(matched)

            anatomy_out.append(
                AnatomyItem(
                    structure_id=struct_id,
                    display_name=s.get("display_name", struct_id.replace("_", " ").title()),
                    category=s.get("category", "unknown"),
                    available=available,
                    voxel_count=s.get("voxel_count", 0),
                    mesh_available=s.get("mesh_available", False),
                    relationship_to_finding=rel_text,
                    unavailability_reason=s.get("status_reason"),
                    color=s.get("color"),
                )
            )

        # ── Spatial Relationships ────────────────────────────────────────────
        relationships_out: list[RelationshipItem] = []
        if primary_finding_id:
            for rel in summary.spatial_relationships:
                relationships_out.append(
                    RelationshipItem(
                        source_id=primary_finding_id,
                        target_id=rel.get("structure_id", ""),
                        target_display_name=rel.get("display_name", ""),
                        distance_mm=rel.get("computational_minimum_distance_mm")
                        or rel.get("distance_mm"),
                        overlap=rel.get("overlap"),
                        overlap_voxel_count=rel.get("overlap_voxel_count", 0),
                        available=rel.get("available", False),
                        unavailability_reason=rel.get("status_reason"),
                        interpretation=_build_relationship_interpretation(rel),
                    )
                )

        # ── Measurements ─────────────────────────────────────────────────────
        measurements_out: list[MeasurementItem] = []
        for m in summary.measurements:
            measurements_out.append(
                MeasurementItem(
                    measurement_id=m.measurement_id,
                    measurement_type=m.measurement_type.value
                    if hasattr(m.measurement_type, "value")
                    else str(m.measurement_type),
                    label=m.label,
                    value_mm=m.distance_mm,
                    value_cm=m.distance_cm,
                    source_target_id=m.source_target_id,
                    target_target_id=m.target_target_id,
                    source_structure_id=m.source_structure_id,
                    target_structure_id=m.target_structure_id,
                    created_at=m.created_at,
                )
            )

        # ── Planning Targets ─────────────────────────────────────────────────
        targets_out: list[PlanningTargetItem] = []
        for t in summary.targets:
            targets_out.append(
                PlanningTargetItem(
                    target_id=t.target_id,
                    label=t.label,
                    target_type=t.target_type.value
                    if hasattr(t.target_type, "value")
                    else str(t.target_type),
                    source=t.source.value
                    if hasattr(t.source, "value")
                    else str(t.source),
                    voxel_coordinate=t.voxel_coordinate,
                    physical_coordinate=t.physical_coordinate,
                    linked_finding_id=t.lesion_id,
                )
            )

        # ── Provenance ───────────────────────────────────────────────────────
        provenance = ExplanationProvenance(
            case_id=case_id,
            ct_source=self._get_ct_source(case_id),
        )

        # ── Assemble ─────────────────────────────────────────────────────────
        return ProcedureExplanation(
            case_id=case_id,
            audience=audience,
            generated_at=datetime.now(timezone.utc).isoformat(),
            case_overview=case_overview,
            computational_findings=findings_out,
            relevant_anatomy=anatomy_out,
            spatial_relationships=relationships_out,
            measurements=measurements_out,
            planning_targets=targets_out,
            procedural_context=self._build_context(audience),
            clinical_review_items=self._build_clinical_review_items(),
            limitations=self._build_limitations(),
            provenance=provenance,
        )

    def generate_provenance_only(self, case_id: str) -> ExplanationProvenance:
        """
        Returns only the provenance section for a case.
        Lightweight — does not rebuild the full explanation.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")
        return ExplanationProvenance(
            case_id=case_id,
            ct_source=self._get_ct_source(case_id),
        )

    def get_provenance(self, case_id: str) -> ExplanationProvenance:
        """Alias for generate_provenance_only."""
        return self.generate_provenance_only(case_id)


# Singleton
procedure_explanation_service = ProcedureExplanationService()
