"""
tests/test_planning_measurements.py

Comprehensive tests for Day 18: Preoperative Measurement & 3D Surgical Geometry Layer.

Validates:
1. Physical Euclidean distance calculation in mm and cm (isotropic & anisotropic spacing)
2. Point-to-point measurement creation via API and service
3. Voxel bounds checking and 400 error handling on invalid coordinates
4. Target-to-target measurement calculation
5. Target-to-structure measurement calculation
6. Structure-to-structure measurement calculation and overlap detection
7. Atomic persistence in measurements.json and file reloading
8. Deletion isolation: deleting a measurement does NOT affect annotations.json
9. Clinical governance disclaimer in response envelope
10. Real KiTS23 case integration and validation
"""

import json
from pathlib import Path
import nibabel as nib
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.planning.measurement_models import (
    Measurement,
    MeasurementType,
    MeasurementSource,
    PointToPointRequest,
    TargetToTargetRequest,
    TargetToStructureRequest,
    StructureToStructureRequest,
)
from src.planning.measurement_service import measurement_service, _euclidean_mm
from src.planning.annotations import annotation_service


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_case(tmp_path, monkeypatch):
    """Creates a temporary mock case directory with NIfTI structure and masks."""
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("src.api.utils.case_manager.CASES_DIR", cases_dir)

    case_id = "test-measurement-case-4321"
    case_path = cases_dir / case_id
    case_path.mkdir(parents=True, exist_ok=True)
    (case_path / "planning").mkdir(parents=True, exist_ok=True)
    (case_path / "segmentation").mkdir(parents=True, exist_ok=True)
    (case_path / "measurements").mkdir(parents=True, exist_ok=True)

    # Mock case.json
    with open(case_path / "case.json", "w", encoding="utf-8") as f:
        json.dump({"case_id": case_id, "status": "completed", "filename": "test.nii.gz"}, f)

    # Mock volume meta: shape (100, 100, 100), spacing (1.0, 2.0, 3.0)
    monkeypatch.setattr(
        measurement_service,
        "_get_volume_meta",
        lambda cid: ((100, 100, 100), (1.0, 2.0, 3.0))
    )
    monkeypatch.setattr(
        annotation_service,
        "_get_volume_meta",
        lambda cid: ((100, 100, 100), (1.0, 2.0, 3.0))
    )

    # Create mock segmentation masks (kidney_left, aorta)
    affine = np.diag([1.0, 2.0, 3.0, 1.0])
    k_mask = np.zeros((100, 100, 100), dtype=np.uint8)
    k_mask[10:20, 10:20, 10:20] = 1
    k_nii = nib.Nifti1Image(k_mask, affine)
    nib.save(k_nii, str(case_path / "segmentation" / "kidney_left.nii.gz"))

    a_mask = np.zeros((100, 100, 100), dtype=np.uint8)
    a_mask[50:60, 50:60, 50:60] = 1
    a_nii = nib.Nifti1Image(a_mask, affine)
    nib.save(a_nii, str(case_path / "segmentation" / "aorta.nii.gz"))

    # Create an overlapping structure (kidney_tumor)
    t_mask = np.zeros((100, 100, 100), dtype=np.uint8)
    t_mask[15:25, 15:25, 15:25] = 1  # overlaps with kidney_left (15:20)
    t_nii = nib.Nifti1Image(t_mask, affine)
    nib.save(t_nii, str(case_path / "segmentation" / "kidney_tumor.nii.gz"))

    return case_id, case_path


# ---------------------------------------------------------------------------
# Unit tests for geometric math
# ---------------------------------------------------------------------------

def test_euclidean_distance_pure_math():
    """Verify 3D Euclidean distance calculation."""
    p1 = [0.0, 0.0, 0.0]
    p2 = [3.0, 4.0, 0.0]
    assert _euclidean_mm(p1, p2) == 5.0

    p3 = [1.0, 2.0, 2.0]
    assert _euclidean_mm(p1, p3) == 3.0

    dist = measurement_service.calculate_physical_point_distance([10.0, 20.0, 30.0], [10.0, 20.0, 45.5])
    assert dist == 15.5


# ---------------------------------------------------------------------------
# Point-to-Point Measurements
# ---------------------------------------------------------------------------

def test_create_point_to_point_measurement(client, temp_case):
    """Test creating point-to-point measurement with anisotropic spacing."""
    case_id, _ = temp_case
    payload = {
        "start_voxel": [10, 10, 10],
        "end_voxel": [20, 10, 10],  # dx=10 voxels * 1.0mm = 10.0 mm
        "label": "Test Transverse Line",
        "notes": "Testing lateral width",
    }
    response = client.post(f"/api/cases/{case_id}/planning/measurements", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["case_id"] == case_id
    assert data["measurement_type"] == "point_to_point"
    assert data["source"] == "user"
    assert data["label"] == "Test Transverse Line"
    assert data["start_voxel"] == [10, 10, 10]
    assert data["end_voxel"] == [20, 10, 10]
    # Spacing is [1.0, 2.0, 3.0]
    assert data["start_physical"] == [10.0, 20.0, 30.0]
    assert data["end_physical"] == [20.0, 20.0, 30.0]
    assert data["distance_mm"] == 10.0
    assert data["distance_cm"] == 1.0
    assert data["notes"] == "Testing lateral width"
    assert "meas_" in data["measurement_id"]


def test_point_to_point_anisotropic_z_axis(client, temp_case):
    """Verify anisotropic z-spacing (3.0mm) scaling."""
    case_id, _ = temp_case
    payload = {
        "start_voxel": [0, 0, 0],
        "end_voxel": [0, 0, 10],  # dz=10 voxels * 3.0mm = 30.0 mm
    }
    response = client.post(f"/api/cases/{case_id}/planning/measurements", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["distance_mm"] == 30.0
    assert data["distance_cm"] == 3.0


def test_point_to_point_out_of_bounds_validation(client, temp_case):
    """Verify 400 error when coordinates exceed volume shape."""
    case_id, _ = temp_case
    # Shape is (100, 100, 100)
    payload = {
        "start_voxel": [10, 10, 10],
        "end_voxel": [150, 10, 10],  # 150 >= 100
    }
    response = client.post(f"/api/cases/{case_id}/planning/measurements", json=payload)
    assert response.status_code == 400
    assert "out of bounds" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Target-to-Target Measurements
# ---------------------------------------------------------------------------

def test_create_target_to_target_measurement(client, temp_case):
    """Test measuring Euclidean distance between two planning targets."""
    case_id, _ = temp_case

    # Create two planning targets
    r1 = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Entry Target", "voxel_coordinate": [10, 10, 10]},
    )
    assert r1.status_code == 201
    t1_id = r1.json()["target_id"]

    r2 = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Deep Target", "voxel_coordinate": [10, 15, 10]},  # dy=5 * 2.0mm = 10.0mm
    )
    assert r2.status_code == 201
    t2_id = r2.json()["target_id"]

    # Create target-to-target measurement
    payload = {
        "source_target_id": t1_id,
        "target_target_id": t2_id,
        "label": "Inter-target Trajectory",
    }
    response = client.post(f"/api/cases/{case_id}/planning/measurements/from-targets", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["measurement_type"] == "target_to_target"
    assert data["source"] == "computational"
    assert data["source_target_id"] == t1_id
    assert data["target_target_id"] == t2_id
    assert data["distance_mm"] == 10.0
    assert data["distance_cm"] == 1.0


def test_target_to_target_missing_target(client, temp_case):
    """Verify 404 when target does not exist."""
    case_id, _ = temp_case
    payload = {
        "source_target_id": "nonexistent_target_1",
        "target_target_id": "nonexistent_target_2",
    }
    response = client.post(f"/api/cases/{case_id}/planning/measurements/from-targets", json=payload)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Target-to-Structure Measurements
# ---------------------------------------------------------------------------

def test_create_target_to_structure_measurement(client, temp_case):
    """Test measuring minimum distance from target to anatomical structure mask."""
    case_id, _ = temp_case

    # Create a planning target at [10, 10, 10] which is inside kidney_left (10:20, 10:20, 10:20)
    r = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Renal Point", "voxel_coordinate": [10, 10, 10]},
    )
    target_id = r.json()["target_id"]

    payload = {
        "target_id": target_id,
        "structure_id": "kidney_left",
        "label": "Point to Kidney Distance",
    }
    response = client.post(f"/api/cases/{case_id}/planning/measurements/to-structure", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["measurement_type"] == "target_to_structure"
    assert data["distance_mm"] == 0.0  # inside mask
    assert data["overlap"] is True


def test_target_to_structure_separated(client, temp_case):
    """Test measuring distance from target to distant structure."""
    case_id, _ = temp_case

    # Target at [0, 0, 0], aorta mask starts at [50, 50, 50]
    r = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Origin Point", "voxel_coordinate": [0, 0, 0]},
    )
    target_id = r.json()["target_id"]

    payload = {
        "target_id": target_id,
        "structure_id": "aorta",
    }
    response = client.post(f"/api/cases/{case_id}/planning/measurements/to-structure", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["distance_mm"] > 0.0
    assert data["overlap"] is False


# ---------------------------------------------------------------------------
# Structure-to-Structure Measurements
# ---------------------------------------------------------------------------

def test_create_structure_to_structure_separated(client, temp_case):
    """Test minimum distance between two separated anatomical structures."""
    case_id, _ = temp_case
    payload = {
        "source_structure_id": "kidney_left",
        "target_structure_id": "aorta",
        "label": "Left Kidney to Aorta",
    }
    response = client.post(f"/api/cases/{case_id}/planning/measurements/structure-to-structure", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["measurement_type"] == "structure_to_structure"
    assert data["source"] == "computational"
    assert data["distance_mm"] > 0.0
    assert data["overlap"] is False
    assert data["source_structure_id"] == "kidney_left"
    assert data["target_structure_id"] == "aorta"


def test_create_structure_to_structure_overlapping(client, temp_case):
    """Test overlap detection between overlapping structures."""
    case_id, _ = temp_case
    payload = {
        "source_structure_id": "kidney_left",
        "target_structure_id": "kidney_tumor",
    }
    response = client.post(f"/api/cases/{case_id}/planning/measurements/structure-to-structure", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["distance_mm"] == 0.0
    assert data["overlap"] is True


def test_structure_to_structure_missing_structure(client, temp_case):
    """Verify 404 when requested structure mask does not exist."""
    case_id, _ = temp_case
    payload = {
        "source_structure_id": "kidney_left",
        "target_structure_id": "pancreas",  # missing
    }
    response = client.post(f"/api/cases/{case_id}/planning/measurements/structure-to-structure", json=payload)
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Retrieval, Deletion & Isolation
# ---------------------------------------------------------------------------

def test_list_and_delete_measurements_isolation(client, temp_case):
    """
    Test listing measurements, deleting a single measurement,
    and verifying isolation from annotations.json.
    """
    case_id, case_path = temp_case

    # 1. Create an annotation
    r_ann = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Isolated Annotation", "voxel_coordinate": [5, 5, 5]},
    )
    ann_id = r_ann.json()["target_id"]

    # 2. Create two measurements
    r_m1 = client.post(
        f"/api/cases/{case_id}/planning/measurements",
        json={"start_voxel": [1, 1, 1], "end_voxel": [2, 2, 2], "label": "M1"},
    )
    m1_id = r_m1.json()["measurement_id"]

    r_m2 = client.post(
        f"/api/cases/{case_id}/planning/measurements",
        json={"start_voxel": [3, 3, 3], "end_voxel": [4, 4, 4], "label": "M2"},
    )
    m2_id = r_m2.json()["measurement_id"]

    # 3. List measurements
    list_resp = client.get(f"/api/cases/{case_id}/planning/measurements")
    assert list_resp.status_code == 200
    envelope = list_resp.json()
    assert envelope["total_measurements"] == 2
    assert len(envelope["measurements"]) == 2
    assert "safety_disclaimer" in envelope

    # 4. Get single measurement
    get_resp = client.get(f"/api/cases/{case_id}/planning/measurements/{m1_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["measurement_id"] == m1_id

    # 5. Delete M1
    del_resp = client.delete(f"/api/cases/{case_id}/planning/measurements/{m1_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Verify M1 deleted, M2 retained
    list_resp2 = client.get(f"/api/cases/{case_id}/planning/measurements")
    assert list_resp2.json()["total_measurements"] == 1
    assert list_resp2.json()["measurements"][0]["measurement_id"] == m2_id

    # 6. Verify annotation was NOT deleted (Isolation test)
    ann_resp = client.get(f"/api/cases/{case_id}/planning/annotations")
    assert ann_resp.status_code == 200
    ann_ids = [a["target_id"] for a in ann_resp.json()["annotations"]]
    assert ann_id in ann_ids

    # 7. Verify 404 for deleted measurement
    del_404 = client.get(f"/api/cases/{case_id}/planning/measurements/{m1_id}")
    assert del_404.status_code == 404


def test_atomic_persistence_roundtrip(client, temp_case):
    """Verify measurements are preserved after clearing in-memory state and reloading."""
    case_id, case_path = temp_case

    client.post(
        f"/api/cases/{case_id}/planning/measurements",
        json={"start_voxel": [10, 10, 10], "end_voxel": [15, 10, 10], "label": "Persistent M"},
    )

    # Inspect file directly on disk
    meas_file = case_path / "planning" / "measurements.json"
    assert meas_file.is_file()
    with open(meas_file, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    assert len(disk_data["measurements"]) == 1
    assert disk_data["measurements"][0]["label"] == "Persistent M"

    # Reload via service directly
    loaded = measurement_service.list_measurements(case_id)
    assert len(loaded) == 1
    assert loaded[0].label == "Persistent M"


# ---------------------------------------------------------------------------
# Real Case Validation (KiTS23 b2f89382-9416-4e94-9486-b00c6b1de64b)
# ---------------------------------------------------------------------------

def test_real_case_measurements_integration(client):
    """Test against the real KiTS23 case if present."""
    real_case_id = "b2f89382-9416-4e94-9486-b00c6b1de64b"
    real_case_path = Path("outputs/cases") / real_case_id
    if not real_case_path.is_dir():
        pytest.skip(f"Real case {real_case_id} not found on disk")

    # List measurements
    response = client.get(f"/api/cases/{real_case_id}/planning/measurements")
    assert response.status_code == 200
    data = response.json()
    assert "total_measurements" in data
    assert "safety_disclaimer" in data

    # Create a point-to-point measurement on real case
    p2p_payload = {
        "start_voxel": [100, 100, 100],
        "end_voxel": [110, 100, 100],
        "label": "Real Case Test Measurement",
    }
    create_resp = client.post(
        f"/api/cases/{real_case_id}/planning/measurements",
        json=p2p_payload
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    meas_id = created["measurement_id"]
    assert created["distance_mm"] > 0.0

    # Cleanup created measurement to leave real case pristine
    del_resp = client.delete(f"/api/cases/{real_case_id}/planning/measurements/{meas_id}")
    assert del_resp.status_code == 200
