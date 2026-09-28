"""
tests/test_preoperative_report.py

Comprehensive tests for the Day 22 Preoperative Report & Export Layer.

Covers:
1. REPORT MODELS: instantiation, optional fields, defaults
2. REPORT SERVICE: technical/general audiences, determinism, missing case, invalid audience
3. REST JSON API: 200 OK, audience toggle, 404, 422
4. REST PDF API: 200, %PDF-, %%EOF, > 5 KB
5. GOVERNANCE: mandatory disclaimers, no prohibited clinical claims
6. REAL VALIDATED CASE: b2f89382-9416-4e94-9486-b00c6b1de64b numerical fidelity
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from src.api.main import app
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
    report_service,
    build_pdf_document,
    _resolve_report_center_voxel,
)

REAL_CASE_ID = "b2f89382-9416-4e94-9486-b00c6b1de64b"


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. REPORT MODELS TESTS
# ==============================================================================

def test_report_models_instantiation():
    """Verify that PreoperativeReport and all sub-models instantiate correctly."""
    metadata = ReportMetadata(
        report_id="rep_test_001",
        case_id="case_123",
        target_audience="technical",
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    case_overview = ReportCaseOverview(
        case_id="case_123",
        target_anatomy="kidney_left",
        status="completed",
        narrative_summary="Computational test summary.",
    )
    imaging_info = ReportImagingInfo(
        modality="CT",
        dimensions=[512, 512, 100],
        spacing_mm=[0.75, 0.75, 1.5],
        orientation="LPS",
        provenance="derived_computation",
    )
    governance = ReportGovernance(
        statement="Research Prototype — Educational Use Only",
        intended_use="Educational and research computational demonstration only.",
        mandatory_disclaimer="Not for clinical diagnostic use.",
        rules=["Rule 1", "Rule 2"],
    )
    provenance = ReportProvenance(
        report_generator="PreoperativeReportService",
        summary_service="PlanningSummaryService",
        explanation_service="ProcedureExplanationService",
        deterministic_hash="abc123hash",
        data_sources={"findings": "model_inference"},
    )

    report = PreoperativeReport(
        metadata=metadata,
        case_overview=case_overview,
        imaging_info=imaging_info,
        governance=governance,
        provenance=provenance,
    )

    assert report.metadata.report_id == "rep_test_001"
    assert report.governance.statement == "Research Prototype — Educational Use Only"
    assert report.governance.rules == ["Rule 1", "Rule 2"]
    assert len(report.computational_findings) == 0
    assert len(report.system_limitations) == 0


def test_report_models_optional_empty_collections():
    """Verify that default empty collections behave safely."""
    report = PreoperativeReport(
        metadata=ReportMetadata(
            report_id="rep_test_002",
            case_id="case_empty",
            target_audience="general",
            generated_at_utc="2026-01-01T00:00:00Z",
        ),
        case_overview=ReportCaseOverview(case_id="case_empty", status="completed"),
        imaging_info=ReportImagingInfo(),
        governance=ReportGovernance(),
        provenance=ReportProvenance(
            report_generator="PreoperativeReportService",
            summary_service="PlanningSummaryService",
            explanation_service="ProcedureExplanationService",
            deterministic_hash="hash",
        ),
    )
    assert report.computational_findings == []
    assert report.anatomical_structures == []
    assert report.planning_session_notes.content is None


def test_report_finding_item_fields():
    """Verify ReportFindingItem has correct field names."""
    f = ReportFindingItem(
        finding_id="cyst_left",
        class_name="cyst",
        volume_ml=0.3071,
        centroid_voxel=[110, 89, 218],
        centroid_physical_mm=[164.868, 133.104, 327.363],
        bounding_box_mm=[7.5, 9.0, 9.0],
        host_organ="kidney_left",
        review_requirement="Qualified clinical review required",
    )
    assert f.class_name == "cyst"
    assert f.volume_ml == pytest.approx(0.3071)
    assert f.bounding_box_mm == [7.5, 9.0, 9.0]


def test_report_anatomy_item_unavailable():
    """Verify ReportAnatomyItem handles unavailable structures."""
    a = ReportAnatomyItem(
        structure_id="renal_artery",
        display_name="Renal Artery",
        available=False,
        availability_note="Not segmented — not available in TotalSegmentator output for this case.",
    )
    assert a.available is False
    assert "not segmented" in a.availability_note.lower()


def test_report_spatial_relationship_item_fields():
    """Verify ReportSpatialRelationshipItem has correct field names."""
    r = ReportSpatialRelationshipItem(
        finding_id="cyst_left",
        target_structure="kidney_left",
        min_distance_mm=0.0,
        overlap_detected=True,
    )
    assert r.finding_id == "cyst_left"
    assert r.min_distance_mm == 0.0
    assert r.overlap_detected is True


def test_report_planning_target_item_fields():
    """Verify ReportPlanningTargetItem field names."""
    t = ReportPlanningTargetItem(
        target_id="model_cyst_left",
        label="Model: cyst_left",
        voxel_coordinate=[110, 89, 218],
        physical_coordinate_mm=[164.868, 133.104, 327.363],
    )
    assert t.voxel_coordinate == [110, 89, 218]
    assert t.physical_coordinate_mm[0] == pytest.approx(164.868)


def test_report_planning_measurement_item_fields():
    """Verify ReportPlanningMeasurementItem field names."""
    m = ReportPlanningMeasurementItem(
        measurement_id="meas_abc123",
        label="Test measurement",
        length_mm=45.67,
        length_cm=4.567,
    )
    assert m.length_mm == pytest.approx(45.67)


def test_report_session_notes_content():
    """Verify ReportPlanningSessionNotes uses `content` field."""
    notes = ReportPlanningSessionNotes(
        content="Clinician notes go here",
        author="Planning System",
    )
    assert notes.content == "Clinician notes go here"
    # Empty notes have content = None by default
    empty = ReportPlanningSessionNotes()
    assert empty.content is None


def test_report_limitation_item_fields():
    """Verify ReportLimitationItem has domain, limitation, recommended_action."""
    lim = ReportLimitationItem(
        domain="Clinical Status & Resectability",
        limitation="No resectability determination.",
        recommended_action="Consult surgeon.",
    )
    assert lim.domain == "Clinical Status & Resectability"
    assert lim.recommended_action == "Consult surgeon."


def test_report_provenance_fields():
    """Verify ReportProvenance has the required named fields."""
    prov = ReportProvenance(
        report_generator="PreoperativeReportService",
        summary_service="PlanningSummaryService",
        explanation_service="ProcedureExplanationService",
        deterministic_hash="deadbeef12345678",
    )
    assert prov.report_generator == "PreoperativeReportService"
    assert prov.deterministic_hash == "deadbeef12345678"


# ==============================================================================
# 2. REPORT SERVICE TESTS
# ==============================================================================

def test_report_service_technical_generation():
    """Test generating a report for technical audience."""
    svc = PreoperativeReportService()
    report = svc.generate_report(REAL_CASE_ID, audience="technical")

    assert isinstance(report, PreoperativeReport)
    assert report.metadata.case_id == REAL_CASE_ID
    assert report.metadata.target_audience == "technical"
    assert report.case_overview.case_id == REAL_CASE_ID
    assert len(report.computational_findings) >= 1
    assert len(report.anatomical_structures) >= 1
    assert report.provenance.report_generator == "PreoperativeReportService"
    assert report.provenance.deterministic_hash != ""


def test_report_service_general_generation():
    """Test generating a report for general audience."""
    svc = PreoperativeReportService()
    report = svc.generate_report(REAL_CASE_ID, audience="general")

    assert report.metadata.target_audience == "general"
    assert report.case_overview.case_id == REAL_CASE_ID


def test_report_service_deterministic_substantive_payload():
    """Verify that substantive payload is deterministic across runs."""
    svc = PreoperativeReportService()
    rep1 = svc.generate_report(REAL_CASE_ID, audience="technical")
    rep2 = svc.generate_report(REAL_CASE_ID, audience="technical")

    assert rep1.provenance.deterministic_hash == rep2.provenance.deterministic_hash
    assert len(rep1.computational_findings) == len(rep2.computational_findings)
    assert rep1.computational_findings[0].volume_ml == rep2.computational_findings[0].volume_ml
    assert rep1.computational_findings[0].centroid_physical_mm == rep2.computational_findings[0].centroid_physical_mm


def test_report_service_missing_case_raises():
    """Verify that non-existent case raises ValueError."""
    svc = PreoperativeReportService()
    with pytest.raises(ValueError, match="not found"):
        svc.generate_report("missing-case-id", audience="technical")


def test_report_service_invalid_audience_raises():
    """Verify that invalid audience raises ValueError."""
    svc = PreoperativeReportService()
    with pytest.raises(ValueError, match="Invalid audience"):
        svc.generate_report(REAL_CASE_ID, audience="unsupported_audience")


# ==============================================================================
# 3. REST JSON API TESTS
# ==============================================================================

def test_api_get_report_technical_200(client):
    """GET /api/cases/{case_id}/planning/report returns 200 with valid schema."""
    resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/report?audience=technical")
    assert resp.status_code == 200
    data = resp.json()

    assert data["metadata"]["case_id"] == REAL_CASE_ID
    assert data["metadata"]["target_audience"] == "technical"
    assert "governance" in data
    assert "computational_findings" in data
    assert "anatomical_structures" in data
    assert "spatial_relationships" in data
    assert "system_limitations" in data


def test_api_get_report_general_200(client):
    """GET /api/cases/{case_id}/planning/report?audience=general returns 200."""
    resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/report?audience=general")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metadata"]["target_audience"] == "general"


def test_api_get_report_missing_case_404(client):
    """GET /api/cases/{case_id}/planning/report returns 404 for missing case."""
    resp = client.get("/api/cases/non-existent-case-id-12345/planning/report")
    assert resp.status_code == 404


def test_api_get_report_invalid_audience_422(client):
    """GET /api/cases/{case_id}/planning/report returns 422 for invalid audience."""
    resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/report?audience=invalid_aud")
    assert resp.status_code == 422


# ==============================================================================
# 4. REST PDF API TESTS
# ==============================================================================

def test_api_get_report_pdf_200(client):
    """GET /api/cases/{case_id}/planning/report/pdf returns 200 application/pdf."""
    resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/report/pdf?audience=technical")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment;" in resp.headers["content-disposition"]
    assert "preoperative_report_" in resp.headers["content-disposition"]

    pdf_bytes = resp.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes
    assert len(pdf_bytes) > 5000


def test_api_get_report_pdf_general_200(client):
    """GET /api/cases/{case_id}/planning/report/pdf for general audience."""
    resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/report/pdf?audience=general")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-")


def test_api_get_report_pdf_missing_case_404(client):
    """PDF endpoint returns 404 for non-existent case."""
    resp = client.get("/api/cases/missing-case-id-9999/planning/report/pdf")
    assert resp.status_code == 404


# ==============================================================================
# 5. GOVERNANCE & CLINICAL SAFETY BOUNDARIES
# ==============================================================================

def test_governance_disclaimers_present():
    """Verify required research prototype governance statements are present."""
    svc = PreoperativeReportService()
    report = svc.generate_report(REAL_CASE_ID)

    assert "Research Prototype" in report.governance.statement
    assert "Educational Use Only" in report.governance.statement
    assert len(report.governance.rules) >= 4

    # Ensure system limitations list unsegmented/unavailable boundaries
    limitation_domains = [lim.domain for lim in report.system_limitations]
    # At least one segmentation and one clinical limitation expected
    assert any("segmentation" in d.lower() or "Segmentation" in d for d in limitation_domains)


def test_no_prohibited_clinical_conclusions():
    """Verify that generated report fields contain no prohibited diagnostic or safety claims."""
    svc = PreoperativeReportService()
    report = svc.generate_report(REAL_CASE_ID)

    rep_dict = report.model_dump()
    json_str = str(rep_dict).lower()

    forbidden_terms = [
        "malignant tumor confirmed",
        "benign tumor confirmed",
        "recommended approach:",
        "safe margin confirmed",
        "safe distance confirmed",
        "unresectable tumor",
        "surgical risk: low",
        "surgical risk: high",
    ]
    for term in forbidden_terms:
        assert term not in json_str, f"Found prohibited clinical claim: '{term}'"


# ==============================================================================
# 6. REAL VALIDATED CASE VERIFICATION
# ==============================================================================

def test_real_case_numerical_fidelity():
    """
    Verify exact fidelity of computational values for real case:
    b2f89382-9416-4e94-9486-b00c6b1de64b

    Expectations:
    - Finding: cyst_left, class_name=cyst
    - Volume: 0.3071 mL
    - Centroid voxel: [110, 89, 218]
    - Centroid physical: [164.868, 133.104, 327.363] mm
    - Bounding box: 7.5 x 9.0 x 9.0 mm
    - Host organ: kidney_left
    - Available structures include: kidney_left
    - Unavailable structures explicitly flagged: renal_artery, renal_vein, renal_pelvis, ureter
    - Spatial relationship to kidney_left: overlap_detected = True
    - Planning target at voxel [110, 89, 218]
    - Planning measurements: authoritatively empty (this reference case is kept
      measurement-free; see docs/DAY22.md "Planning-Measurement Decision")
    - Provenance fields populated
    """
    svc = PreoperativeReportService()
    report = svc.generate_report(REAL_CASE_ID, audience="technical")

    # 1. Findings check
    assert len(report.computational_findings) >= 1
    finding = next((f for f in report.computational_findings if "cyst" in f.finding_id), None)
    assert finding is not None, "cyst_left finding should be present"
    assert finding.class_name == "cyst"
    assert pytest.approx(finding.volume_ml, rel=1e-3) == 0.3071
    assert finding.centroid_voxel == [110, 89, 218]
    assert pytest.approx(finding.centroid_physical_mm[0], abs=0.1) == 164.868
    assert pytest.approx(finding.centroid_physical_mm[1], abs=0.1) == 133.104
    assert pytest.approx(finding.centroid_physical_mm[2], abs=0.1) == 327.363
    assert finding.bounding_box_mm == [7.5, 9.0, 9.0]
    assert finding.host_organ == "kidney_left"

    # 2. Anatomical structures check
    struct_map = {s.structure_id: s for s in report.anatomical_structures}
    assert "kidney_left" in struct_map
    assert struct_map["kidney_left"].available is True

    # Check explicitly unavailable structures
    unavailable_ids = ["renal_artery", "renal_vein", "renal_pelvis", "ureter"]
    for u_id in unavailable_ids:
        assert u_id in struct_map, f"Unavailable structure {u_id} must be explicitly reported"
        assert struct_map[u_id].available is False
        assert struct_map[u_id].availability_note is not None
        assert "not segmented" in struct_map[u_id].availability_note.lower()

    # 3. Spatial relationships check
    assert len(report.spatial_relationships) >= 1
    kidney_rel = next(
        (r for r in report.spatial_relationships if r.target_structure == "kidney_left"),
        None
    )
    assert kidney_rel is not None
    assert kidney_rel.overlap_detected is True

    # 4. Planning targets check
    assert len(report.planning_targets) >= 1
    target = report.planning_targets[0]
    assert target.voxel_coordinate == [110, 89, 218]

    # 5. Planning measurements check
    # This golden reference case is intentionally kept measurement-free: the
    # existing Day 18 integration test (test_planning_measurements.py::
    # test_real_case_measurements_integration) explicitly creates-then-deletes
    # any measurement on this case to leave it pristine. An authoritatively
    # empty list is therefore the correct, expected state — not missing data.
    assert isinstance(report.planning_measurements, list)
    assert report.planning_measurements == []

    # 6. Provenance check
    assert report.provenance.report_generator == "PreoperativeReportService"
    assert report.provenance.summary_service == "PlanningSummaryService"
    assert report.provenance.explanation_service == "ProcedureExplanationService"
    assert report.provenance.deterministic_hash != ""


# ==============================================================================
# 7. DAY 25: Report Identifier Consistency (safety contract for interactive rows)
# ==============================================================================

def test_report_identifiers_match_live_authoritative_endpoints(client):
    """
    Day 25 makes report rows in PreoperativeReportModal clickable: clicking a
    finding/structure/target/measurement row passes its report-schema ID back
    to the workspace, which looks that ID up in its own already-loaded live
    arrays (from /planning/targets, /planning/measurements, /structures,
    /lesions) before calling the existing selection handlers. That design is
    only safe if the report's IDs are exactly the same authoritative IDs the
    live endpoints use — this test proves that invariant holds, rather than
    trusting it implicitly.
    """
    # Findings: report finding_id must match a real lesion_id from /lesions
    lesions_resp = client.get(f"/api/cases/{REAL_CASE_ID}/lesions")
    assert lesions_resp.status_code == 200
    live_lesion_ids = {l["lesion_id"] for l in lesions_resp.json()["lesions"]}

    report = report_service.generate_report(REAL_CASE_ID, audience="technical")
    report_finding_ids = {f.finding_id for f in report.computational_findings}
    assert report_finding_ids and report_finding_ids.issubset(live_lesion_ids)

    # Anatomy / spatial relationships: report structure_id must match a real
    # structure_id from /structures
    structs_resp = client.get(f"/api/cases/{REAL_CASE_ID}/structures")
    assert structs_resp.status_code == 200
    live_structure_ids = {s["structure_id"] for s in structs_resp.json()["structures"]}

    report_structure_ids = {a.structure_id for a in report.anatomical_structures}
    assert report_structure_ids.issubset(live_structure_ids)

    available_rel_structure_ids = {
        r.target_structure for r in report.spatial_relationships if r.available
    }
    assert available_rel_structure_ids.issubset(live_structure_ids)

    # Planning targets: report target_id must match a real target_id from
    # /planning/targets
    targets_resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/targets")
    assert targets_resp.status_code == 200
    live_target_ids = {t["target_id"] for t in targets_resp.json()["targets"]}

    report_target_ids = {t.target_id for t in report.planning_targets}
    assert report_target_ids and report_target_ids.issubset(live_target_ids)

    # Planning measurements: report measurement_id must match a real
    # measurement_id from /planning/measurements. The golden case is kept
    # measurement-free, so create one temporarily to exercise this path, then
    # remove it — leaving the case pristine.
    created = client.post(
        f"/api/cases/{REAL_CASE_ID}/planning/measurements",
        json={"start_voxel": [100, 100, 100], "end_voxel": [110, 100, 100], "label": "Day 25 ID-consistency check"},
    )
    assert created.status_code == 201
    meas_id = created.json()["measurement_id"]
    try:
        live_meas_resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/measurements")
        live_measurement_ids = {m["measurement_id"] for m in live_meas_resp.json()["measurements"]}

        report_with_meas = report_service.generate_report(REAL_CASE_ID, audience="technical")
        report_measurement_ids = {m.measurement_id for m in report_with_meas.planning_measurements}
        assert report_measurement_ids and report_measurement_ids.issubset(live_measurement_ids)
    finally:
        client.delete(f"/api/cases/{REAL_CASE_ID}/planning/measurements/{meas_id}")

    # Golden case restored to pristine measurement state
    final = client.get(f"/api/cases/{REAL_CASE_ID}/planning/measurements")
    assert final.json()["total_measurements"] == 0


# ==============================================================================
# 8. DAY 26: Preoperative Imaging Reference Views (embedded CT slice imagery)
# ==============================================================================

def _tiny_png_bytes(size=(10, 10), fill=0) -> bytes:
    """
    A minimal valid PNG for mocking mpr_manager.get_slice_bytes in unit tests.
    `fill` must differ between calls in the same test: ReportLab deduplicates
    byte-identical embedded images into a single shared XObject, so returning
    the same bytes for all three planes would (correctly) collapse to one
    embedded image rather than three, even though three distinct planes were
    genuinely requested and rendered.
    """
    from PIL import Image as PILImage
    import io as _io
    buf = _io.BytesIO()
    PILImage.new("L", size, color=fill).save(buf, format="PNG")
    return buf.getvalue()


def _minimal_report(
    computational_findings=None,
    planning_targets=None,
    dimensions=None,
) -> PreoperativeReport:
    """Builds a minimal-but-valid PreoperativeReport for build_pdf_document unit tests."""
    return PreoperativeReport(
        metadata=ReportMetadata(
            report_id="rep_test_day26",
            case_id="unit-test-case",
            target_audience="technical",
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
        ),
        case_overview=ReportCaseOverview(case_id="unit-test-case", status="completed"),
        imaging_info=ReportImagingInfo(dimensions=dimensions),
        computational_findings=computational_findings or [],
        planning_targets=planning_targets or [],
        governance=ReportGovernance(),
        provenance=ReportProvenance(
            report_generator="PreoperativeReportService",
            summary_service="PlanningSummaryService",
            explanation_service="ProcedureExplanationService",
            deterministic_hash="unittest",
        ),
    )


# ---------------------------------------------------------------------------
# 8.1 Deterministic center-voxel fallback chain (pure logic, no I/O)
# ---------------------------------------------------------------------------

def test_resolve_center_voxel_prefers_finding_centroid():
    """Finding centroid takes priority over a planning target when both exist."""
    report = _minimal_report(
        computational_findings=[
            ReportFindingItem(finding_id="cyst_left", class_name="cyst", centroid_voxel=[1, 2, 3])
        ],
        planning_targets=[
            ReportPlanningTargetItem(
                target_id="ann_x", label="Point", voxel_coordinate=[9, 9, 9],
                physical_coordinate_mm=[9.0, 9.0, 9.0],
            )
        ],
        dimensions=[100, 100, 100],
    )
    voxel, source = _resolve_report_center_voxel(report)
    assert voxel == [1, 2, 3]
    assert "cyst_left" in source


def test_resolve_center_voxel_falls_back_to_planning_target():
    """No finding centroid -> falls back to the first planning target."""
    report = _minimal_report(
        computational_findings=[],
        planning_targets=[
            ReportPlanningTargetItem(
                target_id="ann_solo", label="Solo Point", voxel_coordinate=[5, 6, 7],
                physical_coordinate_mm=[5.0, 6.0, 7.0],
            )
        ],
        dimensions=[100, 100, 100],
    )
    voxel, source = _resolve_report_center_voxel(report)
    assert voxel == [5, 6, 7]
    assert "ann_solo" in source


def test_resolve_center_voxel_falls_back_to_volume_center():
    """No finding, no target -> falls back to the CT volume center."""
    report = _minimal_report(computational_findings=[], planning_targets=[], dimensions=[100, 200, 300])
    voxel, source = _resolve_report_center_voxel(report)
    assert voxel == [50, 100, 150]
    assert "volume center" in source.lower()


def test_resolve_center_voxel_returns_none_when_no_data():
    """No finding, no target, no dimensions -> explicit None, never a fabricated voxel."""
    report = _minimal_report(computational_findings=[], planning_targets=[], dimensions=None)
    voxel, source = _resolve_report_center_voxel(report)
    assert voxel is None
    assert "unavailable" in source.lower()


# ---------------------------------------------------------------------------
# 8.2 PDF embedding: exact rendering-path parameters (mocked slice generation)
# ---------------------------------------------------------------------------

def test_pdf_generation_uses_expected_planes_window_and_overlay(monkeypatch):
    """
    Verifies the exact contract Day 26 is required to preserve: three planes
    (axial/coronal/sagittal), centered on the known finding centroid, using
    the soft-tissue window (WW 400 / WL 40), with lesion overlay enabled —
    all passed through unmodified to the existing, already-tested
    mpr_manager.get_slice_bytes() rendering path.
    """
    calls = []

    def fake_get_slice_bytes(case_id, plane, index, window_width=400.0, window_level=40.0, overlay_lesion=True):
        calls.append({
            "case_id": case_id, "plane": plane, "index": index,
            "window_width": window_width, "window_level": window_level,
            "overlay_lesion": overlay_lesion,
        })
        # Distinct fill per plane so ReportLab embeds 3 separate images
        # rather than deduplicating byte-identical streams (see _tiny_png_bytes).
        return _tiny_png_bytes(fill=len(calls) * 40)

    # report_service imports mpr_manager locally inside build_pdf_document, so
    # patch the singleton at its source module — the local import will still
    # resolve to this same, now-patched object.
    from src.visualization import mpr as mpr_module
    monkeypatch.setattr(mpr_module.mpr_manager, "get_slice_bytes", fake_get_slice_bytes)

    report = _minimal_report(
        computational_findings=[
            ReportFindingItem(
                finding_id="cyst_left", class_name="cyst", centroid_voxel=[110, 89, 218],
            )
        ],
        dimensions=[293, 293, 344],
    )
    report.metadata.case_id = "b2f89382-9416-4e94-9486-b00c6b1de64b"

    pdf_bytes = build_pdf_document(report)
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes

    assert len(calls) == 3
    called_planes = {c["plane"] for c in calls}
    assert called_planes == {"axial", "coronal", "sagittal"}
    for c in calls:
        assert c["case_id"] == "b2f89382-9416-4e94-9486-b00c6b1de64b"
        assert c["window_width"] == 400.0
        assert c["window_level"] == 40.0
        assert c["overlay_lesion"] is True

    by_plane = {c["plane"]: c["index"] for c in calls}
    # voxel [110, 89, 218] = [x, y, z] -> axial uses z, coronal uses y, sagittal uses x
    assert by_plane["axial"] == 218
    assert by_plane["coronal"] == 89
    assert by_plane["sagittal"] == 110

    # Exactly 3 images actually embedded in the resulting PDF
    assert pdf_bytes.count(b"/Subtype /Image") == 3


def test_pdf_builds_successfully_with_volume_center_fallback(monkeypatch):
    """
    Day 26 Part 9: a case with no computational finding and no planning target
    must still produce a valid PDF, using the CT volume center.
    """
    from src.visualization import mpr as mpr_module
    fallback_calls = []

    def fake_get_slice_bytes(case_id, plane, index, **kwargs):
        fallback_calls.append(plane)
        # Distinct fill per call so ReportLab doesn't dedupe the 3 images.
        return _tiny_png_bytes(fill=len(fallback_calls) * 40)

    monkeypatch.setattr(mpr_module.mpr_manager, "get_slice_bytes", fake_get_slice_bytes)

    report = _minimal_report(computational_findings=[], planning_targets=[], dimensions=[100, 120, 140])
    pdf_bytes = build_pdf_document(report)

    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes
    assert pdf_bytes.count(b"/Subtype /Image") == 3


def test_pdf_handles_image_generation_failure_gracefully(monkeypatch):
    """
    Day 26 Part 10: if slice generation fails, the PDF must still build
    successfully with a graceful limitation notice — never a crash, never a
    fabricated image.
    """
    from src.visualization import mpr as mpr_module

    def failing_get_slice_bytes(*args, **kwargs):
        raise FileNotFoundError("mock: CT volume not available")

    monkeypatch.setattr(mpr_module.mpr_manager, "get_slice_bytes", failing_get_slice_bytes)

    report = _minimal_report(
        computational_findings=[
            ReportFindingItem(finding_id="cyst_left", class_name="cyst", centroid_voxel=[10, 10, 10])
        ],
        dimensions=[100, 100, 100],
    )
    pdf_bytes = build_pdf_document(report)

    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes
    # No images were fabricated when generation fails for every plane
    assert pdf_bytes.count(b"/Subtype /Image") == 0


# ---------------------------------------------------------------------------
# 8.3 Real-case PDF verification (technical + general audiences)
# ---------------------------------------------------------------------------

def test_real_case_pdf_contains_three_embedded_images_technical(client):
    """Real golden case: technical-audience PDF embeds exactly 3 CT slice images."""
    resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/report/pdf?audience=technical")
    assert resp.status_code == 200
    pdf_bytes = resp.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes
    assert pdf_bytes.count(b"/Subtype /Image") == 3
    # Meaningfully larger than the pre-Day-26 text-only baseline (~9-10 KB)
    assert len(pdf_bytes) > 50_000


def test_real_case_pdf_contains_three_embedded_images_general(client):
    """Real golden case: general-audience PDF also embeds exactly 3 CT slice images."""
    resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/report/pdf?audience=general")
    assert resp.status_code == 200
    pdf_bytes = resp.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"%%EOF" in pdf_bytes
    assert pdf_bytes.count(b"/Subtype /Image") == 3
    assert len(pdf_bytes) > 50_000


def test_real_case_json_report_schema_unchanged(client):
    """
    Day 26 must not change the JSON report schema. Verify the top-level
    PreoperativeReport field set is exactly the pre-existing 15 sections, and
    the real case's JSON response is unaffected by the new PDF-only imagery.
    """
    expected_fields = {
        "metadata", "case_overview", "imaging_info", "computational_findings",
        "anatomical_structures", "spatial_relationships", "lesion_measurements",
        "planning_targets", "planning_measurements", "planning_session_notes",
        "procedural_context", "clinical_review_items", "system_limitations",
        "provenance", "governance",
    }
    assert set(PreoperativeReport.model_fields.keys()) == expected_fields

    resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/report?audience=technical")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == expected_fields
    finding = next(f for f in data["computational_findings"] if "cyst" in f["finding_id"])
    assert finding["centroid_voxel"] == [110, 89, 218]


def test_real_case_explanation_endpoint_unaffected(client):
    """Day 26 touches only the PDF builder — /planning/explanation must be unaffected."""
    resp = client.get(f"/api/cases/{REAL_CASE_ID}/planning/explanation?audience=technical")
    assert resp.status_code == 200
