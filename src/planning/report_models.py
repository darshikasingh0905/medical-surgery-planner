"""
src/planning/report_models.py

Structured Pydantic data models for the Preoperative Case Planning Report Layer (Day 22).

Consolidates all 15 authoritative data sections:
1. Report metadata
2. Case overview
3. Imaging information
4. Computational findings
5. Anatomical structures
6. Spatial relationships
7. Lesion measurements
8. Planning targets
9. Planning measurements
10. Planning session notes
11. Procedural context
12. Clinical review items
13. System limitations
14. Provenance / audit trail
15. Governance notice

CLINICAL GOVERNANCE & PRODUCT BOUNDARY:
This report compiles computational imaging outputs and user annotations for
educational and research exploration only.
It DOES NOT:
- provide a clinical diagnosis
- assess malignancy or benign status
- determine histological staging or TNM classification
- recommend a surgical procedure or operative approach
- determine surgical risk or feasibility
- substitute for medical specialist consultation or clinical records
"""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class ReportMetadata(BaseModel):
    """Metadata describing report generation, audience, and system version."""
    report_id: str = Field(..., description="Deterministic unique report identifier")
    case_id: str = Field(..., description="Unique case UUID")
    target_audience: str = Field(default="technical", description="'technical' or 'general'")
    generated_at_utc: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of report compilation",
    )
    software_version: str = Field(default="v1.0-research", description="Pipeline software version")
    schema_version: str = Field(default="1.0.0", description="Report schema version")
    system_name: str = Field(
        default="AI-Assisted Preoperative Planning System",
        description="Formal system name",
    )
    report_title: str = Field(
        default="Preoperative Case Planning & Computational Findings Report",
        description="Document title",
    )


class ReportCaseOverview(BaseModel):
    """High-level case identification and processing status."""
    case_id: str
    target_anatomy: str | None = None
    status: str = "completed"
    narrative_summary: str = ""
    original_filename: str | None = None
    source_type: str = "case_metadata"


class ReportImagingInfo(BaseModel):
    """CT volume matrix dimensions, voxel spacing, and HU ranges."""
    modality: str = "CT"
    dimensions: list[int] | None = None
    spacing_mm: list[float] | None = None
    orientation: list[str] | str | None = None
    intensity_range_hu: list[float] | None = None
    provenance: str = "derived_computation"
    source_type: str = "derived_computation"


class ReportFindingItem(BaseModel):
    """A model-predicted lesion segmentation finding."""
    finding_id: str
    label: str = ""
    class_name: str
    host_organ: str | None = None
    host_organ_display: str | None = None
    volume_ml: float | None = None
    bounding_box_mm: list[float] | None = None
    centroid_voxel: list[int] | None = None
    centroid_physical_mm: list[float] | None = None
    computational_interpretation: str | None = None
    source_provenance: str | None = None
    review_requirement: str = "Qualified clinical review required"
    source_type: str = "model_inference"


class ReportAnatomyItem(BaseModel):
    """Anatomical structure with verified presence/absence on disk."""
    structure_id: str
    display_name: str
    category: str = ""
    available: bool = True
    voxel_count: int = 0
    volume_ml: float | None = None
    centroid_physical_mm: list[float] | None = None
    mesh_available: bool = False
    relationship_to_finding: str | None = None
    unavailability_reason: str | None = None
    availability_note: str | None = None
    color: str | None = None
    source_type: str = "derived_computation"


class ReportSpatialRelationshipItem(BaseModel):
    """Objective minimum Euclidean distance between finding and structure."""
    finding_id: str = "primary_finding"
    target_structure: str = ""
    target_display_name: str = ""
    min_distance_mm: float | None = None
    centroid_distance_mm: float | None = None
    overlap_detected: bool = False
    overlap_voxel_count: int = 0
    available: bool = True
    unavailability_reason: str | None = None
    interpretation: str = ""
    source: str = "Euclidean surface distance matrix"
    source_type: str = "derived_computation"


class ReportLesionMeasurementItem(BaseModel):
    """Quantitative volumetric and geometric dimensions of detected findings."""
    finding_id: str
    volume_ml: float | None = None
    dimensions_mm: list[float] | None = None
    voxel_count: int | None = None
    source_type: str = "derived_computation"


class ReportPlanningTargetItem(BaseModel):
    """Surgical reference coordinates (model-derived or user-annotated)."""
    target_id: str
    label: str
    target_type: str = "model"
    provenance: str = "model_inference"
    voxel_coordinate: list[int]
    physical_coordinate_mm: list[float]
    linked_finding_id: str | None = None
    source_type: str = "model_inference"


class ReportPlanningMeasurementItem(BaseModel):
    """Quantitative linear distance measurement between planning points."""
    measurement_id: str
    label: str = ""
    length_mm: float
    length_cm: float = 0.0
    slice_plane: str = ""
    slice_index: int = 0
    units: str = "mm"
    start_voxel: list[int] | None = None
    end_voxel: list[int] | None = None
    source_type: str = "user_annotation"


class ReportPlanningSessionNotes(BaseModel):
    """User-authored planning session observations and review state."""
    session_id: str | None = None
    content: str | None = None
    author: str = "Computational Planning System"
    updated_at: str | None = None
    provenance: str = "user_annotation"
    source_type: str = "user_annotation"


class ReportProceduralContextItem(BaseModel):
    """General educational procedural context."""
    topic: str = ""
    summary: str = ""
    heading: str = ""
    text: str = ""
    source_type: str = "explanatory_context"


class ReportClinicalReviewItem(BaseModel):
    """Explicit item requiring qualified clinical/pathological evaluation."""
    item_id: str = ""
    item: str = ""
    category: str = ""
    rationale: str = ""
    statement: str = ""
    source_type: str = "mandatory_clinical_review"


class ReportLimitationItem(BaseModel):
    """Technical and methodological boundaries of the system."""
    limitation_id: str = ""
    domain: str
    limitation: str = ""
    description: str = ""
    recommended_action: str = "Consult qualified professional"
    source_type: str = "system_limitation"


class ReportProvenance(BaseModel):
    """Traceable chain of custody for algorithms, pipelines, and inputs."""
    report_generator: str = "PreoperativeReportService"
    summary_service: str = "PlanningSummaryService"
    explanation_service: str = "ProcedureExplanationService"
    deterministic_hash: str = ""
    data_sources: dict[str, str] = Field(default_factory=dict)
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
    generation_method: str = "deterministic_data_aggregation"
    source_type: str = "audit_trail"


class ReportGovernance(BaseModel):
    """Mandatory clinical governance and legal product boundary statement."""
    statement: str = (
        "Research Prototype — Educational Use Only"
    )
    intended_use: str = (
        "Educational and research computational planning demonstration only. "
        "Not intended for clinical diagnostic, therapeutic, or surgical decision-making."
    )
    mandatory_disclaimer: str = (
        "This report compiles computational imaging outputs, model-predicted segmentations, "
        "Euclidean geometric distances, and user annotations. "
        "It DOES NOT provide medical diagnoses, assess malignancy or staging, recommend surgical "
        "procedures or operative approaches, determine surgical risk, or make clinical treatment "
        "decisions. All computational findings require verification and validation by qualified "
        "medical professionals prior to any clinical decision-making."
    )
    rules: list[str] = Field(
        default_factory=lambda: [
            "Model segmentation class labels are NOT pathology classifications.",
            "Computational distances are geometric measurements, not clinical proximity assessments.",
            "Planning annotations may be user-authored and require professional review.",
            "This report does not replace clinical records or professional medical opinions.",
            "All findings require qualified professional verification before any clinical use.",
            "The system provides no autonomous diagnosis, treatment planning, or surgical recommendations.",
        ]
    )
    source_type: str = "governance_policy"


class PreoperativeReport(BaseModel):
    """
    Consolidated Preoperative Planning Case Report.
    Aggregates all 15 authoritative computational and planning sections.
    """
    metadata: ReportMetadata
    case_overview: ReportCaseOverview
    imaging_info: ReportImagingInfo
    computational_findings: list[ReportFindingItem] = Field(default_factory=list)
    anatomical_structures: list[ReportAnatomyItem] = Field(default_factory=list)
    spatial_relationships: list[ReportSpatialRelationshipItem] = Field(default_factory=list)
    lesion_measurements: list[ReportLesionMeasurementItem] = Field(default_factory=list)
    planning_targets: list[ReportPlanningTargetItem] = Field(default_factory=list)
    planning_measurements: list[ReportPlanningMeasurementItem] = Field(default_factory=list)
    planning_session_notes: ReportPlanningSessionNotes = Field(default_factory=ReportPlanningSessionNotes)
    procedural_context: list[ReportProceduralContextItem] = Field(default_factory=list)
    clinical_review_items: list[ReportClinicalReviewItem] = Field(default_factory=list)
    system_limitations: list[ReportLimitationItem] = Field(default_factory=list)
    provenance: ReportProvenance = Field(default_factory=ReportProvenance)
    governance: ReportGovernance = Field(default_factory=ReportGovernance)
