"""
src/planning/__init__.py

Preoperative Planning Targets, Surgical Annotations, and Measurement module.
"""

from src.planning.planning_targets import (
    TargetType,
    TargetSource,
    PlanningTarget,
    AnnotationCreateRequest,
    AnnotationUpdateRequest,
    FromLesionRequest,
    PlanningTargetsResponse,
)
from src.planning.annotations import (
    AnnotationService,
    annotation_service,
)
from src.planning.measurement_models import (
    MeasurementType,
    MeasurementSource,
    Measurement,
    PointToPointRequest,
    TargetToTargetRequest,
    TargetToStructureRequest,
    StructureToStructureRequest,
    MeasurementsResponse,
)
from src.planning.measurement_service import (
    MeasurementService,
    measurement_service,
)
from src.planning.planning_session import (
    PlanningSession,
    PlanningSessionUpdateRequest,
    PlanningSessionService,
    planning_session_service,
)
from src.planning.planning_summary import (
    PlanningSummary,
    PlanningSummaryService,
    planning_summary_service,
)
from src.planning.procedure_explanation import (
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
    ProcedureExplanation,
)
from src.planning.procedure_explanation_service import (
    ProcedureExplanationService,
    procedure_explanation_service,
)
from src.planning.report_models import (
    PreoperativeReport,
    ReportMetadata,
    ReportCaseOverview,
    ReportImagingInfo,
    ReportFindingItem,
    ReportAnatomyItem,
    ReportSpatialRelationshipItem,
    ReportLesionMeasurementItem,
    ReportPlanningTargetItem,
    ReportPlanningMeasurementItem,
    ReportPlanningSessionNotes,
    ReportProceduralContextItem,
    ReportClinicalReviewItem,
    ReportLimitationItem,
    ReportProvenance,
    ReportGovernance,
)
from src.planning.report_service import (
    PreoperativeReportService,
    preoperative_report_service,
)

__all__ = [
    "PreoperativeReport",
    "PreoperativeReportService",
    "preoperative_report_service",
    "TargetType",
    "TargetSource",
    "PlanningTarget",
    "AnnotationCreateRequest",
    "AnnotationUpdateRequest",
    "FromLesionRequest",
    "PlanningTargetsResponse",
    "AnnotationService",
    "annotation_service",
    "MeasurementType",
    "MeasurementSource",
    "Measurement",
    "PointToPointRequest",
    "TargetToTargetRequest",
    "TargetToStructureRequest",
    "StructureToStructureRequest",
    "MeasurementsResponse",
    "MeasurementService",
    "measurement_service",
    "PlanningSession",
    "PlanningSessionUpdateRequest",
    "PlanningSessionService",
    "planning_session_service",
    "PlanningSummary",
    "PlanningSummaryService",
    "planning_summary_service",
    # Day 21 — Procedure Explanation Engine
    "CaseOverview",
    "ComputationalFinding",
    "AnatomyItem",
    "RelationshipItem",
    "MeasurementItem",
    "PlanningTargetItem",
    "GeneralProceduralContext",
    "ClinicalReviewItem",
    "LimitationItem",
    "ExplanationProvenance",
    "ProcedureExplanation",
    "ProcedureExplanationService",
    "procedure_explanation_service",
]

