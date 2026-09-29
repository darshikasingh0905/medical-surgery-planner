import pytest
from fastapi.testclient import TestClient
import io
import json

from src.api.main import app
from src.api.utils.case_manager import get_case_path, init_case_directory

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_upload_successful(tmp_path, monkeypatch):
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")
    
    # Mock the background task so it doesn't run the heavy AI pipeline
    import src.api.routes.cases
    def mock_process_case(case_id):
        pass
    monkeypatch.setattr(src.api.routes.cases, "process_case_background", mock_process_case)
    
    file_content = b"fake nifti content"
    files = {"file": ("test_scan.nii.gz", io.BytesIO(file_content), "application/gzip")}
    
    response = client.post("/api/cases/upload", files=files)
    
    assert response.status_code == 201
    data = response.json()
    assert "case_id" in data
    assert data["filename"] == "test_scan.nii.gz"
    assert data["status"] == "uploaded"
    
    case_dir = tmp_path / "cases" / data["case_id"]
    saved_file = case_dir / "input" / "test_scan.nii.gz"
    assert saved_file.exists()
    assert saved_file.read_bytes() == file_content
    
    # Verify case.json exists
    case_json = case_dir / "case.json"
    assert case_json.exists()
    
def test_upload_invalid_extension():
    file_content = b"fake content"
    files = {"file": ("test_scan.txt", io.BytesIO(file_content), "text/plain")}
    
    response = client.post("/api/cases/upload", files=files)
    
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

def test_get_case_status_existing(tmp_path, monkeypatch):
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")
    
    case_id = "test-case-uuid"
    init_case_directory(case_id, "test.nii")
    
    response = client.get(f"/api/cases/{case_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case_id
    assert data["filename"] == "test.nii"
    assert data["status"] == "uploaded"

def test_get_case_status_not_found(tmp_path, monkeypatch):
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")
    
    response = client.get("/api/cases/nonexistent-case")
    assert response.status_code == 404
    assert response.json()["detail"] == "Case not found"

def test_get_case_results_not_ready(tmp_path, monkeypatch):
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")
    
    case_id = "test-case-uuid"
    init_case_directory(case_id, "test.nii")
    
    response = client.get(f"/api/cases/{case_id}/results")
    assert response.status_code == 400
    assert "Results not ready" in response.json()["detail"]

def test_get_case_results_ready(tmp_path, monkeypatch):
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")
    
    case_id = "test-case-uuid"
    case_path = init_case_directory(case_id, "test.nii")
    
    # Mock completion
    with open(case_path / "case.json", "w") as f:
        json.dump({"case_id": case_id, "filename": "test.nii", "status": "completed"}, f)
        
    measurements_dir = case_path / "measurements"
    dummy_results = {"liver": {"mesh_volume": {"volume_cm3": 1200}}}
    with open(measurements_dir / "results.json", "w") as f:
        json.dump(dummy_results, f)
        
    response = client.get(f"/api/cases/{case_id}/results")
    assert response.status_code == 200
    assert response.json()["organs"] == dummy_results

def test_get_case_mesh_invalid_organ():
    response = client.get("/api/cases/some-case/meshes/brain")
    assert response.status_code == 400
    assert "Invalid organ" in response.json()["detail"]

def test_get_case_mesh_success(tmp_path, monkeypatch):
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")
    
    case_id = "test-case-uuid"
    case_path = init_case_directory(case_id, "test.nii")
    
    meshes_dir = case_path / "meshes"
    mesh_file = meshes_dir / "liver.obj"
    mesh_file.write_text("v 0 0 0\n")
    
    response = client.get(f"/api/cases/{case_id}/meshes/liver")
    assert response.status_code == 200
    assert response.text.strip() == "v 0 0 0"


# --- Regression test for NumPy JSON serialization ---
def test_numpy_serialization():
    """
    Regression test: measurement engine returns NumPy types (float32, float64,
    int64, ndarray). Ensure sanitize_for_json converts them all to native
    Python types so json.dump does not crash.
    """
    import json
    import numpy as np
    from src.api.utils.serialization import sanitize_for_json

    raw = {
        "foreground_voxels": np.int64(753016),
        "voxel_spacing": np.array([1.5, 1.5, 1.5], dtype=np.float32),
        "voxel_volume": np.float32(3.375),
        "volume_mm3": np.float64(2541679.0),
        "volume_cm3": np.float64(2541.679),
        "is_manifold": np.bool_(True),
        "bounds": (np.float64(10.0), np.float64(200.0),
                   np.float64(10.0), np.float64(150.0),
                   np.float64(10.0), np.float64(300.0)),
        "nested": {
            "x_mm": np.float32(190.0),
            "y_mm": np.float32(140.0),
        }
    }

    sanitized = sanitize_for_json(raw)

    # Must not raise
    serialized = json.dumps(sanitized)
    reloaded = json.loads(serialized)

    # Types must be plain Python, not NumPy
    assert type(reloaded["foreground_voxels"]) is int
    assert type(reloaded["voxel_volume"]) is float
    assert type(reloaded["volume_mm3"]) is float
    assert type(reloaded["is_manifold"]) is bool
    assert isinstance(reloaded["voxel_spacing"], list)
    assert all(type(v) is float for v in reloaded["voxel_spacing"])
    assert isinstance(reloaded["bounds"], list)
    assert type(reloaded["nested"]["x_mm"]) is float


# --- Day 14 Lesion API Endpoints Tests ---
def test_get_case_lesions_not_ready(tmp_path, monkeypatch):
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")

    case_id = "test-case-uuid"
    init_case_directory(case_id, "test.nii")

    response = client.get(f"/api/cases/{case_id}/lesions")
    assert response.status_code == 400
    assert "Results not ready" in response.json()["detail"]


def test_get_case_lesions_empty(tmp_path, monkeypatch):
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")

    case_id = "test-case-uuid"
    case_path = init_case_directory(case_id, "test.nii")

    with open(case_path / "case.json", "w") as f:
        json.dump({"case_id": case_id, "filename": "test.nii", "status": "completed"}, f)

    response = client.get(f"/api/cases/{case_id}/lesions")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case_id
    assert data["total_lesions"] == 0
    assert data["lesions"] == []


def test_get_case_lesions_with_cached_results(tmp_path, monkeypatch):
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")

    case_id = "test-case-uuid"
    case_path = init_case_directory(case_id, "test.nii")

    with open(case_path / "case.json", "w") as f:
        json.dump({"case_id": case_id, "filename": "test.nii", "status": "completed"}, f)

    measurements_dir = case_path / "measurements"
    cached_payload = {
        "case_id": case_id,
        "total_lesions": 1,
        "lesions": [
            {
                "lesion_id": "cyst_left",
                "class_label": 3,
                "class_name": "cyst",
                "computational_interpretation": "model-predicted cyst-class segmentation",
                "volume_ml": 0.3071,
                "dimensions_mm": [7.5, 9.0, 9.0],
                "centroid_mm": [-60.2, 86.5, 180.9],
                "mesh_available": True,
                "provenance_reference": "outputs/provenance/kiTS2023_nnunet_run_metadata.json"
            }
        ],
        "disclaimer": "Computational metrics for decision support only."
    }
    with open(measurements_dir / "lesions.json", "w") as f:
        json.dump(cached_payload, f)

    # Test list endpoint
    response = client.get(f"/api/cases/{case_id}/lesions")
    assert response.status_code == 200
    data = response.json()
    assert data["total_lesions"] == 1
    assert data["lesions"][0]["lesion_id"] == "cyst_left"

    # Test single lesion endpoint
    res_single = client.get(f"/api/cases/{case_id}/lesions/cyst_left")
    assert res_single.status_code == 200
    assert res_single.json()["lesion_id"] == "cyst_left"
    assert res_single.json()["volume_ml"] == 0.3071

    # Test single lesion not found
    res_404 = client.get(f"/api/cases/{case_id}/lesions/tumor_right")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"]


# =====================================================================
# Day 27: Case History / Resume Previous Case (GET /api/cases)
# =====================================================================

def test_list_cases_empty(tmp_path, monkeypatch):
    """An empty (or nonexistent) CASES_DIR yields an empty list, not an error."""
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")

    response = client.get("/api/cases")
    assert response.status_code == 200
    assert response.json() == {"cases": []}


def test_list_cases_multiple_and_sorting(tmp_path, monkeypatch):
    """
    Covers: multiple valid cases, a completed case, a failed case, and
    deterministic most-recently-modified-first sorting.
    """
    import os
    import time
    import src.api.utils.case_manager
    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", cases_dir)

    # Case A: completed, older
    init_case_directory("case-a", "scan_a.nii")
    case_a_json = cases_dir / "case-a" / "case.json"
    with open(case_a_json, "w") as f:
        json.dump({"case_id": "case-a", "filename": "scan_a.nii", "status": "completed"}, f)
    old_time = time.time() - 3600
    os.utime(case_a_json, (old_time, old_time))

    # Case B: failed, newer
    init_case_directory("case-b", "scan_b.nii")
    case_b_json = cases_dir / "case-b" / "case.json"
    with open(case_b_json, "w") as f:
        json.dump({"case_id": "case-b", "filename": "scan_b.nii", "status": "failed", "error": "boom"}, f)
    new_time = time.time()
    os.utime(case_b_json, (new_time, new_time))

    response = client.get("/api/cases")
    assert response.status_code == 200
    data = response.json()
    assert len(data["cases"]) == 2

    # Most recently modified first
    assert data["cases"][0]["case_id"] == "case-b"
    assert data["cases"][0]["status"] == "failed"
    assert data["cases"][1]["case_id"] == "case-a"
    assert data["cases"][1]["status"] == "completed"
    for c in data["cases"]:
        assert c["last_modified"], "last_modified must be present and non-empty"


def test_list_cases_missing_case_json_fallback(tmp_path, monkeypatch):
    """
    A case directory with no case.json at all must still be listed, using the
    same input/-scan fallback semantics get_case_info() already implements —
    not a separate, duplicated fallback.
    """
    import src.api.utils.case_manager
    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", cases_dir)

    case_dir = cases_dir / "orphan-case"
    (case_dir / "input").mkdir(parents=True)
    (case_dir / "input" / "orphan_scan.nii").write_bytes(b"fake")

    response = client.get("/api/cases")
    assert response.status_code == 200
    data = response.json()
    assert len(data["cases"]) == 1
    entry = data["cases"][0]
    assert entry["case_id"] == "orphan-case"
    assert entry["filename"] == "orphan_scan.nii"
    assert entry["status"] == "uploaded"


def test_list_cases_malformed_case_json_is_skipped_not_fatal(tmp_path, monkeypatch):
    """
    A malformed/unreadable case.json must not abort the entire listing — that
    one case is skipped and every other valid case is still returned.
    """
    import src.api.utils.case_manager
    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", cases_dir)

    init_case_directory("good-case", "good.nii")

    bad_dir = cases_dir / "bad-case"
    bad_dir.mkdir(parents=True)
    (bad_dir / "case.json").write_text("{ this is not valid json ")

    response = client.get("/api/cases")
    assert response.status_code == 200
    data = response.json()
    case_ids = {c["case_id"] for c in data["cases"]}
    assert "good-case" in case_ids
    assert "bad-case" not in case_ids


def test_list_cases_is_read_only(tmp_path, monkeypatch):
    """Listing must never create, modify, or delete any case file."""
    import src.api.utils.case_manager
    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", cases_dir)

    init_case_directory("ro-case", "ro.nii")
    case_json = cases_dir / "ro-case" / "case.json"
    before_content = case_json.read_bytes()
    before_mtime = case_json.stat().st_mtime

    response = client.get("/api/cases")
    assert response.status_code == 200

    after_content = case_json.read_bytes()
    after_mtime = case_json.stat().st_mtime
    assert before_content == after_content
    assert before_mtime == after_mtime


def test_list_cases_response_shape(tmp_path, monkeypatch):
    """GET /api/cases response envelope matches the documented contract exactly."""
    import src.api.utils.case_manager
    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", cases_dir)

    init_case_directory("shape-case", "shape.nii")

    response = client.get("/api/cases")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"cases"}
    assert isinstance(data["cases"], list)
    entry = data["cases"][0]
    assert set(entry.keys()) == {"case_id", "filename", "status", "last_modified"}


def test_real_case_appears_in_case_list():
    """
    Non-destructive: confirms the real golden case is discoverable via the
    new case-history endpoint without mutating it.
    """
    real_case_id = "b2f89382-9416-4e94-9486-b00c6b1de64b"
    from pathlib import Path
    if not (Path("outputs/cases") / real_case_id).is_dir():
        pytest.skip(f"Real case {real_case_id} not found on disk")

    response = client.get("/api/cases")
    assert response.status_code == 200
    data = response.json()
    entry = next((c for c in data["cases"] if c["case_id"] == real_case_id), None)
    assert entry is not None, "Golden case must appear in the case history listing"
    assert entry["status"] == "completed"
    assert entry["filename"] == "ct_15mm_defaced.nii"
    assert entry["last_modified"]


# =====================================================================
# Day 28: Case Deletion (DELETE /api/cases/{case_id})
#
# SAFETY: every test in this section operates exclusively on a monkeypatched,
# pytest-managed tmp_path CASES_DIR. None of these tests ever call DELETE
# against the real outputs/cases/ directory or the golden case. The final
# test in this section explicitly re-verifies the golden case is untouched.
# =====================================================================

def test_delete_case_success(tmp_path, monkeypatch):
    """Deleting an existing case returns 200 and removes its directory entirely."""
    import src.api.utils.case_manager
    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", cases_dir)

    case_path = init_case_directory("delete-me", "delete_me.nii")
    assert case_path.is_dir()

    response = client.delete("/api/cases/delete-me")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "deleted", "case_id": "delete-me"}
    assert not case_path.is_dir()


def test_delete_case_not_found(tmp_path, monkeypatch):
    """Deleting a case_id that does not exist returns 404, not an error."""
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")

    response = client.delete("/api/cases/does-not-exist")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_delete_case_removes_all_associated_data(tmp_path, monkeypatch):
    """
    Deletion must remove the entire case tree — not just case.json — including
    nested planning/segmentation/lesions data.
    """
    import src.api.utils.case_manager
    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", cases_dir)

    case_path = init_case_directory("full-case", "full.nii")
    # Simulate a fully-processed case with nested planning/lesions data
    (case_path / "planning").mkdir(parents=True, exist_ok=True)
    (case_path / "planning" / "measurements.json").write_text('{"measurements": []}')
    (case_path / "planning" / "annotations.json").write_text('{"annotations": []}')
    (case_path / "lesions").mkdir(parents=True, exist_ok=True)
    (case_path / "lesions" / "cyst_left.nii.gz").write_bytes(b"fake mask bytes")
    (case_path / "segmentation" / "kidney_left.nii.gz").write_bytes(b"fake seg bytes")

    assert (case_path / "planning" / "measurements.json").is_file()
    assert (case_path / "lesions" / "cyst_left.nii.gz").is_file()

    response = client.delete("/api/cases/full-case")
    assert response.status_code == 200
    assert not case_path.exists(), "Entire case directory tree must be gone, not just case.json"


def test_delete_case_does_not_affect_other_cases(tmp_path, monkeypatch):
    """Deleting one case must never touch any other case's data."""
    import src.api.utils.case_manager
    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", cases_dir)

    init_case_directory("case-keep", "keep.nii")
    init_case_directory("case-remove", "remove.nii")
    keep_json = cases_dir / "case-keep" / "case.json"
    before_content = keep_json.read_bytes()
    before_mtime = keep_json.stat().st_mtime

    response = client.delete("/api/cases/case-remove")
    assert response.status_code == 200

    assert (cases_dir / "case-keep").is_dir()
    after_content = keep_json.read_bytes()
    after_mtime = keep_json.stat().st_mtime
    assert before_content == after_content
    assert before_mtime == after_mtime

    # Still correctly reported by the listing endpoint
    listing = client.get("/api/cases").json()
    remaining_ids = {c["case_id"] for c in listing["cases"]}
    assert remaining_ids == {"case-keep"}


def test_deleted_case_no_longer_appears_in_list(tmp_path, monkeypatch):
    """After deletion, GET /api/cases must no longer include the deleted case."""
    import src.api.utils.case_manager
    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", cases_dir)

    init_case_directory("ephemeral-case", "ephemeral.nii")
    before = client.get("/api/cases").json()
    assert any(c["case_id"] == "ephemeral-case" for c in before["cases"])

    client.delete("/api/cases/ephemeral-case")

    after = client.get("/api/cases").json()
    assert not any(c["case_id"] == "ephemeral-case" for c in after["cases"])


def test_delete_case_double_delete_returns_404(tmp_path, monkeypatch):
    """Deleting the same case twice: first succeeds, second is a clean 404."""
    import src.api.utils.case_manager
    cases_dir = tmp_path / "cases"
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", cases_dir)

    init_case_directory("twice-case", "twice.nii")
    first = client.delete("/api/cases/twice-case")
    assert first.status_code == 200
    second = client.delete("/api/cases/twice-case")
    assert second.status_code == 404


def test_golden_case_untouched_after_deletion_test_battery():
    """
    Regression safety net: after the entire Day 28 delete-test battery above
    has run (all against monkeypatched tmp_path directories only), the real
    golden case must still exist on disk, completely intact.
    """
    real_case_id = "b2f89382-9416-4e94-9486-b00c6b1de64b"
    from pathlib import Path
    if not (Path("outputs/cases") / real_case_id).is_dir():
        pytest.skip(f"Real case {real_case_id} not found on disk")

    response = client.get(f"/api/cases/{real_case_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == real_case_id
    assert data["status"] == "completed"
    assert data["filename"] == "ct_15mm_defaced.nii"

    targets = client.get(f"/api/cases/{real_case_id}/planning/targets").json()
    model_target = next(t for t in targets["targets"] if t["target_id"] == "model_cyst_left")
    assert model_target["voxel_coordinate"] == [110, 89, 218]

