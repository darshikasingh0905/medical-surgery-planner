"""
tests/test_procedure_explanation.py

Comprehensive tests for the Day 21 Preoperative Procedure Explanation Engine.

Validates:
1. Data models (CaseOverview, ComputationalFinding, AnatomyItem, etc.)
2. ProcedureExplanationService logic and deterministic generation
3. Technical vs. General audience adaptation
4. Source traceability & provenance tracking
5. Strict adherence to medical safety boundaries & governance statements
6. REST API endpoints (/planning/explanation and /planning/explanation/provenance)
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
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

REAL_CASE_ID = "b2f89382-9416-4e94-9486-b00c6b1de64b"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_case_id():
    """Returns the verified test case ID."""
    return REAL_CASE_ID


# ==============================================================================
# 1. Pydantic Model Tests
# ==============================================================================

def test_case_overview_model():
    overview = CaseOverview(
        case_id="case_001",
        status="completed",
        scan_dimensions=[512, 512, 120],
        voxel_spacing_mm=[0.8, 0.8, 1.5],
        orientation=["R", "A", "S"],
        modality="CT",
        intensity_range_hu=[-1024, 3071],
    )
    assert overview.case_id == "case_001"
    assert overview.voxel_spacing_mm == [0.8, 0.8, 1.5]
    assert overview.intensity_range_hu == [-1024, 3071]


def test_computational_finding_model():
    finding = ComputationalFinding(
        finding_id="lesion_01",
        model_class="tumor",
        model_confidence=0.94,
        computational_interpretation="Model-predicted lesion segmented in physical space",
        host_organ="kidney_right",
        host_organ_display="Right Kidney",
        centroid_voxel=[256, 256, 60],
        centroid_physical_mm=[204.8, 204.8, 90.0],
        volume_ml=12.45,
        dimensions_mm=[25.0, 30.0, 28.5],
        source_provenance="KiTS23-trained nnU-Net segmentation pipeline",
    )
    assert finding.finding_id == "lesion_01"
    assert finding.model_class == "tumor"
    assert finding.volume_ml == 12.45
    assert "nnU-Net" in finding.source_provenance


def test_anatomy_item_model():
    item = AnatomyItem(
        structure_id="kidney_right",
        display_name="Right Kidney",
        category="organ",
        available=True,
        color="#3b82f6",
        source_segmentation="TotalSegmentator CT multi-organ",
        relationship_to_finding="Host organ containing primary computational finding",
    )
    assert item.available is True
    assert item.category == "organ"


def test_relationship_item_model():
    rel = RelationshipItem(
        target_id="inferior_vena_cava",
        target_display_name="Inferior Vena Cava (IVC)",
        distance_mm=14.25,
        overlap=False,
        available=True,
        source="Physical Euclidean surface distance matrix",
    )
    assert rel.target_id == "inferior_vena_cava"
    assert rel.distance_mm == 14.25
    assert rel.overlap is False


def test_measurement_item_model():
    meas = MeasurementItem(
        measurement_id="m_123",
        measurement_type="linear_distance",
        label="Tumor max dimension",
        value_mm=32.4,
        value_cm=3.24,
        start_voxel=[200, 200, 50],
        end_voxel=[230, 220, 55],
        source_service="Day 19 Preoperative Measurement Service",
    )
    assert meas.value_cm == 3.24
    assert meas.label == "Tumor max dimension"


def test_governance_statement_in_explanation():
    """Verify that every ProcedureExplanation includes the strict governance notice."""
    overview = CaseOverview(case_id="c1", status="completed")
    exp = ProcedureExplanation(
        case_id="c1",
        audience="technical",
        case_overview=overview,
        provenance=ExplanationProvenance(),
    )
    assert "RESEARCH AND EDUCATIONAL PROTOTYPE ONLY" in exp.governance_statement
    assert "does not diagnose disease" in exp.governance_statement.lower()
    assert "recommend a surgical procedure" in exp.governance_statement.lower()


# ==============================================================================
# 2. ProcedureExplanationService Unit Tests
# ==============================================================================

def test_service_generates_explanation(valid_case_id):
    """Test generating a technical explanation from an existing case."""
    exp = procedure_explanation_service.generate_explanation(valid_case_id, audience="technical")
    assert isinstance(exp, ProcedureExplanation)
    assert exp.case_id == valid_case_id
    assert exp.audience == "technical"
    assert exp.case_overview.case_id == valid_case_id
    assert len(exp.relevant_anatomy) > 0
    assert len(exp.limitations) > 0
    assert len(exp.clinical_review_items) > 0
    assert exp.procedural_context is not None


def test_service_audience_adaptation(valid_case_id):
    """Test differences between technical and general audience outputs."""
    exp_tech = procedure_explanation_service.generate_explanation(valid_case_id, audience="technical")
    exp_gen = procedure_explanation_service.generate_explanation(valid_case_id, audience="general")

    assert exp_tech.audience == "technical"
    assert exp_gen.audience == "general"

    # Both explanations must maintain safety boundaries
    assert "RESEARCH AND EDUCATIONAL" in exp_tech.governance_statement
    assert "RESEARCH AND EDUCATIONAL" in exp_gen.governance_statement

    # General explanation uses simplified phrasing for computational findings
    if exp_tech.computational_findings and exp_gen.computational_findings:
        tf = exp_tech.computational_findings[0]
        gf = exp_gen.computational_findings[0]
        assert tf.computational_interpretation != gf.computational_interpretation


def test_service_provenance_tracking(valid_case_id):
    """Verify that provenance details provide exact pipeline traceability."""
    prov = procedure_explanation_service.get_provenance(valid_case_id)
    assert isinstance(prov, ExplanationProvenance)
    assert prov.case_id == valid_case_id
    assert prov.generation_method == "deterministic_data_aggregation"
    assert "TotalSegmentator" in prov.anatomy_registry_source
    assert "Euclidean" in prov.spatial_relationship_source


def test_service_clinical_review_items_boundaries(valid_case_id):
    """Ensure required clinical review items are explicitly highlighted as non-computational."""
    exp = procedure_explanation_service.generate_explanation(valid_case_id)
    categories = [item.category for item in exp.clinical_review_items]
    assert "pathology" in categories
    assert "diagnosis" in categories
    assert "staging" in categories
    assert "operative_approach" in categories

    for item in exp.clinical_review_items:
        # All items must emphasize physician authority or system boundaries
        assert any(term in item.statement.lower() for term in ["clinician", "clinical", "pathology", "diagnosis", "staging", "operative", "judgment", "physician", "uncertainty", "segmented", "prototype"])


def test_service_limitations_included(valid_case_id):
    """Ensure technical and clinical limitations are documented."""
    exp = procedure_explanation_service.generate_explanation(valid_case_id)
    assert len(exp.limitations) >= 4
    domains = [lim.domain for lim in exp.limitations]
    assert "segmentation" in domains
    assert "imaging" in domains
    assert "model" in domains
    assert "validation" in domains


# ==============================================================================
# 3. REST API Endpoint Tests
# ==============================================================================

def test_api_get_explanation_technical(client, valid_case_id):
    """GET /api/cases/{case_id}/planning/explanation returns 200 with structured data."""
    res = client.get(f"/api/cases/{valid_case_id}/planning/explanation?audience=technical")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == valid_case_id
    assert data["audience"] == "technical"
    assert "case_overview" in data
    assert "computational_findings" in data
    assert "relevant_anatomy" in data
    assert "spatial_relationships" in data
    assert "procedural_context" in data
    assert "clinical_review_items" in data
    assert "limitations" in data
    assert "governance_statement" in data
    assert "RESEARCH AND EDUCATIONAL" in data["governance_statement"]


def test_api_get_explanation_general(client, valid_case_id):
    """GET /api/cases/{case_id}/planning/explanation?audience=general returns 200 with general wording."""
    res = client.get(f"/api/cases/{valid_case_id}/planning/explanation?audience=general")
    assert res.status_code == 200
    data = res.json()
    assert data["audience"] == "general"


def test_api_get_provenance(client, valid_case_id):
    """GET /api/cases/{case_id}/planning/explanation/provenance returns pipeline metadata."""
    res = client.get(f"/api/cases/{valid_case_id}/planning/explanation/provenance")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == valid_case_id
    assert data["generation_method"] == "deterministic_data_aggregation"


def test_api_explanation_not_found(client):
    """GET /api/cases/nonexistent_case/planning/explanation returns 404."""
    res = client.get("/api/cases/nonexistent_case_99999/planning/explanation")
    assert res.status_code == 404
