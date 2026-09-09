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
