"""
tests/test_planning_workspace.py

Day 20 — Preoperative Planning Workspace Test Suite.
Tests:
  1. Planning session model, validation, and defaults
  2. Planning session atomic persistence and recovery
  3. Planning session partial updates
  4. Planning summary aggregation on real case b2f89382-9416-4e94-9486-b00c6b1de64b
  5. Missing case handling and 404 error behavior
  6. FastAPI REST endpoints (/planning/summary and /planning/session)
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.planning.planning_session import (
    PlanningSession,
    PlanningSessionUpdateRequest,
    planning_session_service,
)
from src.planning.planning_summary import (
    PlanningSummary,
    planning_summary_service,
)

REAL_CASE_ID = "b2f89382-9416-4e94-9486-b00c6b1de64b"
client = TestClient(app)


# =====================================================================
# 1. Planning Session Model & Default Initialization
# =====================================================================

def test_default_planning_session_creation():
    """Validates creation and field defaults of a new planning session."""
    session = planning_session_service.create_default_session(REAL_CASE_ID)

    assert session.case_id == REAL_CASE_ID
    assert session.session_id.startswith("session_")
    assert session.view_mode == "3d"
    assert session.selected_mpr_plane == "axial"
    assert len(session.voxel_cursor) == 3
    assert session.organ_opacity == 0.85
    assert session.lesion_opacity == 1.0
    assert session.planning_notes == ""
    # Should automatically link to genuine model lesion if present
    assert session.selected_lesion_id == "cyst_left"
    assert session.selected_target_id == "model_cyst_left"


def test_planning_session_validation():
    """Validates boundary constraints on view_mode and voxel_cursor."""
    with pytest.raises(ValueError):
        PlanningSession(
            case_id="case_test",
            session_id="s1",
            view_mode="invalid_mode",  # only '3d', 'mpr', 'split' allowed
            voxel_cursor=[10, 10, 10],
        )

    with pytest.raises(ValueError):
        PlanningSession(
            case_id="case_test",
            session_id="s1",
            view_mode="3d",
            voxel_cursor=[10, 10],  # must be 3 integers
        )


# =====================================================================
# 2. Planning Session Persistence & Updates
# =====================================================================

def test_planning_session_atomic_persistence():
    """Tests saving and reloading session state from disk."""
    session = planning_session_service.get_session(REAL_CASE_ID)
    original_id = session.session_id

    # Update note and cursor
    update = PlanningSessionUpdateRequest(
        planning_notes="Patient has model finding near upper left renal parenchyma.",
        view_mode="split",
        voxel_cursor=[110, 89, 218],
    )
    updated = planning_session_service.update_session(REAL_CASE_ID, update)
    assert updated.planning_notes == "Patient has model finding near upper left renal parenchyma."
    assert updated.view_mode == "split"
    assert updated.voxel_cursor == [110, 89, 218]

    # Re-fetch fresh from disk
    reloaded = planning_session_service.get_session(REAL_CASE_ID)
    assert reloaded.planning_notes == updated.planning_notes
    assert reloaded.view_mode == "split"
    assert reloaded.voxel_cursor == [110, 89, 218]

    # Verify session file exists on disk
    case_dir = Path("outputs/cases") / REAL_CASE_ID
    session_file = case_dir / "planning" / "planning_session.json"
    assert session_file.is_file()


def test_planning_session_partial_update():
    """Validates that partial update modifies only provided fields."""
    session_before = planning_session_service.get_session(REAL_CASE_ID)
    cursor_before = list(session_before.voxel_cursor)

    # Only update notes
    updated = planning_session_service.update_session(
        REAL_CASE_ID,
        {"planning_notes": "Second revision of planning notes."}
    )
    assert updated.planning_notes == "Second revision of planning notes."
    assert updated.voxel_cursor == cursor_before
    assert updated.view_mode == session_before.view_mode


def test_planning_session_corrupt_file_graceful_recovery(tmp_path):
    """Verifies that an empty or malformed session file triggers default recovery."""
    case_dir = Path("outputs/cases") / REAL_CASE_ID
    session_file = case_dir / "planning" / "planning_session.json"

    # Save backup content
    backup = session_file.read_text(encoding="utf-8") if session_file.is_file() else None
    try:
        # Corrupt file
        session_file.write_text("{ corrupt json ...", encoding="utf-8")
        session = planning_session_service.get_session(REAL_CASE_ID)
        assert session.case_id == REAL_CASE_ID
        assert session.view_mode == "3d"
    finally:
        if backup:
            session_file.write_text(backup, encoding="utf-8")


# =====================================================================
# 3. Planning Summary Service (Real KiTS23 Case)
# =====================================================================

def test_planning_summary_aggregation_real_case():
    """
    Validates that PlanningSummary aggregates all computational planning components
    for real case b2f89382-9416-4e94-9486-b00c6b1de64b.
    """
    summary = planning_summary_service.get_planning_summary(REAL_CASE_ID)
    assert isinstance(summary, PlanningSummary)
    assert summary.case_id == REAL_CASE_ID
    assert summary.status == "completed"

    # Scan info
    assert summary.scan_info["shape"] == [293, 293, 344]
    assert summary.scan_info["voxel_spacing_mm"] == [1.5, 1.5, 1.5]
    assert summary.scan_info["orientation"] == ["R", "A", "S"]

    # Model-predicted findings
    assert len(summary.findings) >= 1
    cyst_finding = next((f for f in summary.findings if f["lesion_id"] == "cyst_left"), None)
    assert cyst_finding is not None
    assert cyst_finding["class_name"] == "cyst"
    assert abs(cyst_finding["volume_ml"] - 0.3071) < 1e-2

    # Registered anatomical structures
    assert len(summary.anatomy) > 0
    kidney_left = next((s for s in summary.anatomy if s["structure_id"] == "kidney_left"), None)
    assert kidney_left is not None
    assert kidney_left["available"] is True

    # Planning targets
    assert len(summary.targets) >= 1
    model_target = next((t for t in summary.targets if t.target_id == "model_cyst_left"), None)
    assert model_target is not None
    assert model_target.voxel_coordinate == [110, 89, 218]

    # Preoperative measurements list
    assert isinstance(summary.measurements, list)

    # Active session attached
    assert isinstance(summary.session, PlanningSession)
    assert summary.session.case_id == REAL_CASE_ID

    # Safety disclaimer present
    assert "RESEARCH AND EDUCATIONAL PROTOTYPE ONLY" in summary.safety_disclaimer


def test_planning_summary_nonexistent_case():
    """Verifies that non-existent cases raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        planning_summary_service.get_planning_summary("nonexistent-uuid-1234")


# =====================================================================
# 4. FastAPI REST Endpoints Integration Tests
# =====================================================================

def test_api_get_planning_summary():
    """Tests GET /api/cases/{case_id}/planning/summary."""
    res = client.get(f"/api/cases/{REAL_CASE_ID}/planning/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == REAL_CASE_ID
    assert data["status"] == "completed"
    assert "scan_info" in data
    assert "findings" in data
    assert "anatomy" in data
    assert "targets" in data
    assert "session" in data


def test_api_get_planning_session():
    """Tests GET /api/cases/{case_id}/planning/session."""
    res = client.get(f"/api/cases/{REAL_CASE_ID}/planning/session")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == REAL_CASE_ID
    assert "session_id" in data
    assert "view_mode" in data
    assert "voxel_cursor" in data


def test_api_put_planning_session():
    """Tests PUT /api/cases/{case_id}/planning/session."""
    payload = {
        "planning_notes": "API test notes: Reviewed renal lesion in split view.",
        "view_mode": "split",
        "voxel_cursor": [110, 89, 218],
    }
    res = client.put(f"/api/cases/{REAL_CASE_ID}/planning/session", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["planning_notes"] == "API test notes: Reviewed renal lesion in split view."
    assert data["view_mode"] == "split"
    assert data["voxel_cursor"] == [110, 89, 218]


def test_api_post_reset_planning_session():
    """Tests POST /api/cases/{case_id}/planning/session (reset)."""
    res = client.post(f"/api/cases/{REAL_CASE_ID}/planning/session")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == REAL_CASE_ID
    assert data["view_mode"] == "3d"


def test_api_nonexistent_case_404():
    """Tests 404 response on missing case for planning summary and session."""
    bad_id = "00000000-0000-0000-0000-000000000000"
    res1 = client.get(f"/api/cases/{bad_id}/planning/summary")
    assert res1.status_code == 404

    res2 = client.get(f"/api/cases/{bad_id}/planning/session")
    assert res2.status_code == 404

    res3 = client.put(f"/api/cases/{bad_id}/planning/session", json={"planning_notes": "abc"})
    assert res3.status_code == 404


# =====================================================================
# 5. Day 20 Final Audit: Structure Availability, No Clinical Threshold
# =====================================================================

def test_renal_vein_unavailable_no_distance():
    """
    AUDIT: renal_vein is NOT in standard TotalSegmentator output.
    It must appear in spatial_relationships as available=False with distance_mm=None.
    """
    summary = planning_summary_service.get_planning_summary(REAL_CASE_ID)
    renal_vein_rel = next(
        (r for r in summary.spatial_relationships if r["structure_id"] == "renal_vein"),
        None,
    )
    assert renal_vein_rel is not None, "renal_vein entry must be present (as unavailable)"
    assert renal_vein_rel["available"] is False, "renal_vein must be marked available=False"
    assert renal_vein_rel["distance_mm"] is None, (
        "renal_vein must have distance_mm=None (no mask => no distance)"
    )
    assert renal_vein_rel["computational_minimum_distance_mm"] is None


def test_unavailable_structures_have_no_distance():
    """
    AUDIT: All known-unavailable structures (renal_artery, renal_vein, renal_pelvis, ureter)
    must have available=False and distance_mm=None for the real validated case.
    """
    summary = planning_summary_service.get_planning_summary(REAL_CASE_ID)
    known_unavailable = {"renal_artery", "renal_vein", "renal_pelvis", "ureter"}
    for rel in summary.spatial_relationships:
        if rel["structure_id"] in known_unavailable:
            assert rel["available"] is False, (
                f"{rel['structure_id']} must be unavailable (no segmentation mask)"
            )
            assert rel["distance_mm"] is None, (
                f"{rel['structure_id']} must have distance_mm=None (not segmented)"
            )


def test_no_proximity_threshold_in_api_response():
    """
    AUDIT: The API planning summary must not expose any clinical proximity threshold.
    No relationship should contain keys like 'risk_level', 'alert', 'threshold_mm',
    or numeric alert values.
    """
    summary = planning_summary_service.get_planning_summary(REAL_CASE_ID)
    forbidden_keys = {"risk_level", "alert", "threshold_mm", "proximity_alert", "safe", "unsafe"}
    for rel in summary.spatial_relationships:
        for key in forbidden_keys:
            assert key not in rel, (
                f"Relationship for {rel['structure_id']} must not expose key '{key}'"
            )


def test_available_structures_have_real_distances():
    """
    AUDIT: Available structures (kidney_left, aorta, inferior_vena_cava, adrenal glands)
    must have genuine computed distance_mm values (not None) for the real case.
    """
    summary = planning_summary_service.get_planning_summary(REAL_CASE_ID)
    expected_available = {"kidney_left", "kidney_right", "aorta", "inferior_vena_cava",
                          "adrenal_gland_left", "adrenal_gland_right"}
    for rel in summary.spatial_relationships:
        if rel["structure_id"] in expected_available:
            assert rel["available"] is True, (
                f"{rel['structure_id']} must be available (mask exists)"
            )
            assert rel["distance_mm"] is not None, (
                f"{rel['structure_id']} must have a computed distance_mm"
            )
            assert isinstance(rel["distance_mm"], (int, float)), (
                f"{rel['structure_id']} distance_mm must be numeric"
            )


def test_planning_notes_are_user_entered_not_ai_generated():
    """
    AUDIT: Planning notes must be a plain user-editable string.
    The API must not inject AI-generated surgical conclusions, diagnoses,
    or recommendations into planning_notes.
    """
    # Reset to fresh defaults
    client.post(f"/api/cases/{REAL_CASE_ID}/planning/session")
    session_res = client.get(f"/api/cases/{REAL_CASE_ID}/planning/session")
    data = session_res.json()

    # Default notes must be empty
    assert data["planning_notes"] == "", "Default planning_notes must be empty string"

    # User can set arbitrary text
    user_text = "User note: Reviewed axial slice 218. Model finding in upper pole."
    put_res = client.put(
        f"/api/cases/{REAL_CASE_ID}/planning/session",
        json={"planning_notes": user_text}
    )
    assert put_res.status_code == 200
    assert put_res.json()["planning_notes"] == user_text

    # Session must NOT contain forbidden clinical conclusions
    forbidden_phrases = [
        "recommended approach", "optimal approach", "surgical risk",
        "safe margin", "malignant", "benign", "diagnosis",
    ]
    notes_lower = put_res.json()["planning_notes"].lower()
    for phrase in forbidden_phrases:
        assert phrase not in notes_lower, (
            f"planning_notes must not contain AI-generated phrase: '{phrase}'"
        )


# =====================================================================
# 6. Day 23: Complete MPR Session Persistence
#    (window preset/width/level, lesion overlay, crosshair visibility,
#    planning-marker visibility)
# =====================================================================

def test_mpr_window_preset_width_level_round_trip():
    """Verify MPR window preset + resolved width/level persist and reload correctly."""
    updated = planning_session_service.update_session(
        REAL_CASE_ID,
        {
            "mpr_window_preset": "bone",
            "mpr_window_width": 1800.0,
            "mpr_window_level": 400.0,
        },
    )
    assert updated.mpr_window_preset == "bone"
    assert updated.mpr_window_width == 1800.0
    assert updated.mpr_window_level == 400.0

    reloaded = planning_session_service.get_session(REAL_CASE_ID)
    assert reloaded.mpr_window_preset == "bone"
    assert reloaded.mpr_window_width == 1800.0
    assert reloaded.mpr_window_level == 400.0


def test_mpr_lesion_overlay_round_trip():
    """Verify lesion-overlay visibility toggle persists and reloads correctly (both directions)."""
    updated = planning_session_service.update_session(
        REAL_CASE_ID, {"mpr_show_lesion_overlay": False}
    )
    assert updated.mpr_show_lesion_overlay is False
    assert planning_session_service.get_session(REAL_CASE_ID).mpr_show_lesion_overlay is False

    updated2 = planning_session_service.update_session(
        REAL_CASE_ID, {"mpr_show_lesion_overlay": True}
    )
    assert updated2.mpr_show_lesion_overlay is True
    assert planning_session_service.get_session(REAL_CASE_ID).mpr_show_lesion_overlay is True


def test_mpr_crosshair_visibility_round_trip():
    """Verify crosshair visibility toggle persists and reloads correctly (both directions)."""
    updated = planning_session_service.update_session(
        REAL_CASE_ID, {"mpr_show_crosshairs": False}
    )
    assert updated.mpr_show_crosshairs is False
    assert planning_session_service.get_session(REAL_CASE_ID).mpr_show_crosshairs is False

    updated2 = planning_session_service.update_session(
        REAL_CASE_ID, {"mpr_show_crosshairs": True}
    )
    assert updated2.mpr_show_crosshairs is True
    assert planning_session_service.get_session(REAL_CASE_ID).mpr_show_crosshairs is True


def test_mpr_planning_marker_visibility_round_trip():
    """Verify planning-marker visibility toggle persists and reloads correctly (both directions)."""
    updated = planning_session_service.update_session(
        REAL_CASE_ID, {"mpr_show_planning_markers": False}
    )
    assert updated.mpr_show_planning_markers is False
    assert planning_session_service.get_session(REAL_CASE_ID).mpr_show_planning_markers is False

    updated2 = planning_session_service.update_session(
        REAL_CASE_ID, {"mpr_show_planning_markers": True}
    )
    assert updated2.mpr_show_planning_markers is True
    assert planning_session_service.get_session(REAL_CASE_ID).mpr_show_planning_markers is True


def test_api_put_session_mpr_fields_round_trip():
    """REST-level verification: PUT session with all Day 23 MPR fields together."""
    payload = {
        "mpr_window_preset": "lung",
        "mpr_window_width": 1500.0,
        "mpr_window_level": -600.0,
        "mpr_show_lesion_overlay": False,
        "mpr_show_crosshairs": False,
        "mpr_show_planning_markers": False,
    }
    res = client.put(f"/api/cases/{REAL_CASE_ID}/planning/session", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["mpr_window_preset"] == "lung"
    assert data["mpr_window_width"] == 1500.0
    assert data["mpr_window_level"] == -600.0
    assert data["mpr_show_lesion_overlay"] is False
    assert data["mpr_show_crosshairs"] is False
    assert data["mpr_show_planning_markers"] is False

    # Confirm a fresh GET reflects the same persisted values (not silently reset)
    get_res = client.get(f"/api/cases/{REAL_CASE_ID}/planning/session")
    get_data = get_res.json()
    assert get_data["mpr_window_preset"] == "lung"
    assert get_data["mpr_show_crosshairs"] is False
    assert get_data["mpr_show_planning_markers"] is False


def test_loading_session_does_not_overwrite_persisted_state_with_defaults():
    """
    AUDIT (Day 23, Part 2.E): retrieving/loading a session must be read-only —
    it must never silently reset a persisted non-default value back to the
    PlanningSession default. This guards against a 'save loop' where the
    frontend's initial mount-time load effect would clobber a user's prior
    toggle state.
    """
    # Put the session into a distinctly non-default state
    planning_session_service.update_session(
        REAL_CASE_ID,
        {
            "mpr_window_preset": "bone",
            "mpr_show_lesion_overlay": False,
            "mpr_show_crosshairs": False,
            "mpr_show_planning_markers": False,
        },
    )

    # Simulate the frontend's mount-time load: GET (read-only) repeated twice
    first_load = client.get(f"/api/cases/{REAL_CASE_ID}/planning/session").json()
    second_load = client.get(f"/api/cases/{REAL_CASE_ID}/planning/session").json()

    assert first_load["mpr_window_preset"] == "bone"
    assert first_load["mpr_show_lesion_overlay"] is False
    assert first_load["mpr_show_crosshairs"] is False
    assert first_load["mpr_show_planning_markers"] is False
    # A second read must be identical — reading must never mutate state
    assert second_load == first_load

    # Restore neutral defaults so later test runs in this module aren't affected
    planning_session_service.update_session(
        REAL_CASE_ID,
        {
            "mpr_window_preset": "soft_tissue",
            "mpr_window_width": 400.0,
            "mpr_window_level": 40.0,
            "mpr_show_lesion_overlay": True,
            "mpr_show_crosshairs": True,
            "mpr_show_planning_markers": True,
        },
    )

