import pytest
from fastapi.testclient import TestClient
import io

from src.api.main import app
from src.api.utils.case_manager import get_case_path

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_upload_successful(tmp_path, monkeypatch):
    # Mock the outputs directory to use a temporary path for testing
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")
    
    # Create a dummy .nii.gz file content
    file_content = b"fake nifti content"
    files = {"file": ("test_scan.nii.gz", io.BytesIO(file_content), "application/gzip")}
    
    response = client.post("/api/cases/upload", files=files)
    
    assert response.status_code == 201
    data = response.json()
    assert "case_id" in data
    assert data["filename"] == "test_scan.nii.gz"
    assert data["status"] == "uploaded"
    
    # Verify file was actually saved
    case_dir = tmp_path / "cases" / data["case_id"]
    saved_file = case_dir / "input" / "test_scan.nii.gz"
    assert saved_file.exists()
    assert saved_file.read_bytes() == file_content

def test_upload_invalid_extension():
    file_content = b"fake content"
    files = {"file": ("test_scan.txt", io.BytesIO(file_content), "text/plain")}
    
    response = client.post("/api/cases/upload", files=files)
    
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

def test_get_case_status_existing(tmp_path, monkeypatch):
    import src.api.utils.case_manager
    monkeypatch.setattr(src.api.utils.case_manager, "CASES_DIR", tmp_path / "cases")
    
    # Setup a mock case
    case_id = "test-case-uuid"
    case_dir = tmp_path / "cases" / case_id / "input"
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "test.nii").write_bytes(b"content")
    
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
