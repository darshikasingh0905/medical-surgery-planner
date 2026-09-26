from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class CaseOverview(BaseModel):
    """High-level case context derived from CT metadata."""
    case_id: str = Field(..., description="Unique case UUID")
    case_type: str = Field(default="CT-based computational planning case")
    status: str = Field(..., description="Case processing status")
    scan_dimensions: list[int] | None = Field(default=None)
    voxel_spacing_mm: list[float] | None = Field(default=None)
    orientation: list[str] | None = Field(default=None)
    intensity_range_hu: list[float] | None = Field(default=None)
    processing_status: str = Field(default="completed")


class ComputationalFinding(BaseModel):
    """Structured representation of a single model-predicted finding."""
    finding_id: str
    label: str = ""
    model_class: str
    model_confidence: float | None = None
    host_organ: str | None = None
    host_organ_display: str | None = None
    volume_ml: float | None = None
    dimensions_mm: list[float] | None = None
    centroid_voxel: list[int] | None = None
    centroid_physical_mm: list[float] | None = None
    computational_interpretation: str | None = None
    source_provenance: str | None = None


class AnatomyItem(BaseModel):
    """Representation of a single anatomical structure with availability context."""
    structure_id: str
    display_name: str
    category: str
    available: bool
    voxel_count: int = 0
    mesh_available: bool = False
    source_segmentation: str | None = None
    relationship_to_finding: str | None = None
    unavailability_reason: str | None = None
    color: str | None = None


class RelationshipItem(BaseModel):
    """Computational spatial relationship between primary finding and one structure."""
    source_id: str = "primary_finding"
    target_id: str
    target_display_name: str
    distance_mm: float | None = None
    overlap: bool | None = None
    overlap_voxel_count: int = 0
    available: bool = True
    unavailability_reason: str | None = None
    interpretation: str = ""
    source: str = "Physical Euclidean surface distance matrix"
    source_service: str = "src.measurements.spatial_relationships"


class MeasurementItem(BaseModel):
    """A single quantitative preoperative measurement with provenance reference."""
    measurement_id: str
    measurement_type: str
    label: str
    value_mm: float
    value_cm: float
    units: str = "mm"
    start_voxel: list[int] | None = None
    end_voxel: list[int] | None = None
    source_target_id: str | None = None
    target_target_id: str | None = None
    source_structure_id: str | None = None
    target_structure_id: str | None = None
    source_service: str = "src.planning.measurement_service"
    created_at: str | None = None


class PlanningTargetItem(BaseModel):
    """A planning target as it appears in the explanation context."""
    target_id: str
    label: str
    target_type: str
    source: str
    voxel_coordinate: list[int]
    physical_coordinate: list[float]
    linked_finding_id: str | None = None


class GeneralProceduralContext(BaseModel):
    """Static, general procedural context items."""
    items: list[dict[str, str]] = Field(default_factory=list)
    audience: str = "technical"
    disclaimer: str = (
        "The following provides general procedural context only. "
        "It does not recommend a specific surgical procedure, operative approach, "
        "or clinical course of action."
    )


class ClinicalReviewItem(BaseModel):
    """Explicit statement of something this system CANNOT determine."""
    item_id: str
    category: str
    statement: str


class LimitationItem(BaseModel):
    """Technical or methodological limitation of the current implementation."""
    limitation_id: str
    domain: str
    description: str


class ExplanationProvenance(BaseModel):
    """Traceable source references for all computational outputs."""
    case_id: str | None = None
    ct_source: str | None = None
    segmentation_source: str | None = "TotalSegmentator v2 (117-class CT segmentation)"
    lesion_model_source: str | None = "KiTS23 renal segmentation model (cyst/tumor class inference)"
    lesion_class_mapping: dict[str, str] | None = Field(
        default_factory=lambda: {"1": "kidney", "2": "tumor", "3": "cyst"}
    )
    coordinate_system_source: str = "src.geometry.coordinate_system"
    measurement_source: str = "src.planning.measurement_service"
    spatial_relationship_source: str = "src.measurements.spatial_relationships (Euclidean surface distance matrix)"
    anatomy_registry_source: str = "src.anatomy.structure_registry (TotalSegmentator verified on disk)"
    planning_session_source: str = "src.planning.planning_session"
    generation_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    generation_method: str = "deterministic_data_aggregation"


class ProcedureExplanation(BaseModel):
    """
    Structured preoperative procedure explanation.

    GOVERNANCE: This model organizes computational findings and provides
    general procedural context only. It does not diagnose disease, determine
    pathology, recommend an operative approach, or make clinical decisions.
    """
    case_id: str
    audience: str = "technical"
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    case_overview: CaseOverview | None = None
    computational_findings: list[ComputationalFinding] = Field(default_factory=list)
    relevant_anatomy: list[AnatomyItem] = Field(default_factory=list)
    spatial_relationships: list[RelationshipItem] = Field(default_factory=list)
    measurements: list[MeasurementItem] = Field(default_factory=list)
    planning_targets: list[PlanningTargetItem] = Field(default_factory=list)
    procedural_context: GeneralProceduralContext = Field(default_factory=GeneralProceduralContext)
    clinical_review_items: list[ClinicalReviewItem] = Field(default_factory=list)
    limitations: list[LimitationItem] = Field(default_factory=list)
    provenance: ExplanationProvenance = Field(default_factory=ExplanationProvenance)
    governance_statement: str = (
        "RESEARCH AND EDUCATIONAL PROTOTYPE ONLY: The procedure explanation engine organizes "
        "computational imaging findings and provides general procedural context. It does not "
        "diagnose disease, determine pathology, recommend a surgical procedure or operative "
        "approach, determine surgical risk, or make autonomous clinical decisions. "
        "All findings require review and validation by qualified medical professionals."
    )

    def get_primary_finding(self):
        return self.computational_findings[0] if self.computational_findings else None

    def get_available_anatomy(self):
        return [a for a in self.relevant_anatomy if a.available]

    def get_available_relationships(self):
        return [r for r in self.spatial_relationships if r.available]
