"""
tests/test_planning.py

Comprehensive tests for Preoperative Surgical Target Annotation & Planning Marker layer.

Validates:
1. Creation of user planning annotation
2. Retrieval of annotations
3. Updating label, notes, and coordinates
4. Deletion of user annotation
5. Missing case handling (404)
6. Malformed and out-of-bounds coordinates (400)
7. Missing lesion handling (404)
8. Lesion-derived annotation creation
9. Persistence after reload (disk round-trip)
10. Exact coordinate preservation (voxel <-> physical mm)
11. Unified planning targets listing (model findings + user annotations)
12. Real case KiTS23 model target validation
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.planning.annotations import annotation_service
from src.planning.planning_targets import (
    PlanningTarget,
    TargetType,
    TargetSource,
    AnnotationCreateRequest,
    AnnotationUpdateRequest,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_case(tmp_path, monkeypatch):
    """Creates a temporary mock case directory with NIfTI structure."""
    cases_dir = tmp_path / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("src.api.utils.case_manager.CASES_DIR", cases_dir)

    case_id = "test-planning-case-1234"
    case_path = cases_dir / case_id
    case_path.mkdir(parents=True, exist_ok=True)
    (case_path / "planning").mkdir(parents=True, exist_ok=True)
    (case_path / "measurements").mkdir(parents=True, exist_ok=True)
    (case_path / "lesions").mkdir(parents=True, exist_ok=True)

    # Mock case.json
    with open(case_path / "case.json", "w", encoding="utf-8") as f:
        json.dump({"case_id": case_id, "status": "completed", "filename": "test.nii.gz"}, f)

    # Mock lesions.json
    mock_lesions = {
        "case_id": case_id,
        "total_lesions": 1,
        "lesions": [
            {
                "lesion_id": "cyst_left",
                "class_name": "cyst",
                "host_organ": "kidney_left",
                "computational_interpretation": "Model-predicted cyst-class segmentation (KiTS23 class 3)",
                "volume_ml": 0.3071,
                "dimensions_mm": [7.5, 9.0, 9.0],
                "centroid_mm": [165.0, 135.0, 330.0],
                "voxel_count": 91,
            }
        ]
    }
    with open(case_path / "measurements" / "lesions.json", "w", encoding="utf-8") as f:
        json.dump(mock_lesions, f)

    # Mock volume meta
    monkeypatch.setattr(
        annotation_service,
        "_get_volume_meta",
        lambda cid: ((300, 300, 400), (1.5, 1.5, 1.5))
    )

    return case_id, case_path


def test_create_user_annotation(client, temp_case):
    case_id, case_path = temp_case
    payload = {
        "label": "Biopsy Entry Trajectory Point",
        "target_type": "custom_point",
        "voxel_coordinate": [100, 110, 120],
        "notes": "Planned entry point on lateral renal cortex",
    }
    response = client.post(f"/api/cases/{case_id}/planning/annotations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["label"] == "Biopsy Entry Trajectory Point"
    assert data["source"] == "user"
    assert data["target_type"] == "custom_point"
    assert data["voxel_coordinate"] == [100, 110, 120]
    # Spacing is 1.5, so 100*1.5 = 150.0, 110*1.5 = 165.0, 120*1.5 = 180.0
    assert data["physical_coordinate"] == [150.0, 165.0, 180.0]
    assert data["notes"] == "Planned entry point on lateral renal cortex"
    assert "target_id" in data


def test_get_user_annotations(client, temp_case):
    case_id, _ = temp_case
    # Create two annotations
    client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Point A", "voxel_coordinate": [50, 50, 50]},
    )
    client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Point B", "voxel_coordinate": [60, 60, 60]},
    )

    response = client.get(f"/api/cases/{case_id}/planning/annotations")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == case_id
    assert data["total_annotations"] == 2
    labels = [a["label"] for a in data["annotations"]]
    assert "Point A" in labels
    assert "Point B" in labels


def test_update_user_annotation(client, temp_case):
    case_id, _ = temp_case
    res = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Old Label", "voxel_coordinate": [40, 40, 40]},
    )
    ann_id = res.json()["target_id"]

    update_payload = {
        "label": "Updated Planning Target",
        "notes": "Adjusted after review",
        "voxel_coordinate": [45, 45, 45],
    }
    up_res = client.put(f"/api/cases/{case_id}/planning/annotations/{ann_id}", json=update_payload)
    assert up_res.status_code == 200
    updated_data = up_res.json()
    assert updated_data["label"] == "Updated Planning Target"
    assert updated_data["notes"] == "Adjusted after review"
    assert updated_data["voxel_coordinate"] == [45, 45, 45]
    assert updated_data["physical_coordinate"] == [67.5, 67.5, 67.5]


def test_delete_user_annotation(client, temp_case):
    case_id, _ = temp_case
    res = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "To Delete", "voxel_coordinate": [30, 30, 30]},
    )
    ann_id = res.json()["target_id"]

    # Delete
    del_res = client.delete(f"/api/cases/{case_id}/planning/annotations/{ann_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify absence
    list_res = client.get(f"/api/cases/{case_id}/planning/annotations")
    ids = [a["target_id"] for a in list_res.json()["annotations"]]
    assert ann_id not in ids

    # Deleting again returns 404
    del_res2 = client.delete(f"/api/cases/{case_id}/planning/annotations/{ann_id}")
    assert del_res2.status_code == 404


def test_missing_case_error(client):
    fake_case = "non-existent-case-9999"
    res = client.get(f"/api/cases/{fake_case}/planning/targets")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    res_ann = client.get(f"/api/cases/{fake_case}/planning/annotations")
    assert res_ann.status_code == 404

    res_create = client.post(
        f"/api/cases/{fake_case}/planning/annotations",
        json={"label": "Point", "voxel_coordinate": [10, 10, 10]},
    )
    assert res_create.status_code == 404


def test_malformed_and_out_of_bounds_coordinates(client, temp_case):
    case_id, _ = temp_case
    # Non-3D coordinate (2 elements)
    res1 = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Bad 2D", "voxel_coordinate": [10, 20]},
    )
    assert res1.status_code == 400

    # Out of bounds (> 200 for mock volume)
    res2 = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Out of bounds", "voxel_coordinate": [300, 100, 100]},
    )
    assert res2.status_code == 400
    assert "out of bounds" in res2.json()["detail"].lower()

    # Negative coordinates
    res3 = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Negative bounds", "voxel_coordinate": [-5, 100, 100]},
    )
    assert res3.status_code == 400


def test_create_annotation_from_lesion(client, temp_case):
    case_id, _ = temp_case
    res = client.post(
        f"/api/cases/{case_id}/planning/annotations/from-lesion/cyst_left",
        json={"label": "Primary Renal Lesion Annotation", "notes": "Target for parenchymal inspection"},
    )
    assert res.status_code == 201
    data = response = res.json()
    assert data["target_type"] == "lesion"
    assert data["lesion_id"] == "cyst_left"
    assert data["physical_coordinate"] == [165.0, 135.0, 330.0]
    # Spacing 1.5 -> [165/1.5, 135/1.5, 330/1.5] = [110, 90, 220]
    assert data["voxel_coordinate"] == [110, 90, 220]


def test_missing_lesion_error(client, temp_case):
    case_id, _ = temp_case
    res = client.post(
        f"/api/cases/{case_id}/planning/annotations/from-lesion/non_existent_lesion",
        json={},
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_persistence_after_reload(client, temp_case):
    case_id, case_path = temp_case
    res = client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "Persistent Point", "voxel_coordinate": [80, 85, 90]},
    )
    ann_id = res.json()["target_id"]

    # Verify JSON file on disk
    ann_file = case_path / "planning" / "annotations.json"
    assert ann_file.is_file()
    with open(ann_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert any(a["target_id"] == ann_id for a in data["annotations"])

    # Reload from fresh service call
    fresh_anns = annotation_service.list_user_annotations(case_id)
    assert any(a.target_id == ann_id for a in fresh_anns)


def test_target_listing_combines_model_and_user(client, temp_case):
    case_id, _ = temp_case
    # Add a user annotation
    client.post(
        f"/api/cases/{case_id}/planning/annotations",
        json={"label": "User Planning Point 1", "voxel_coordinate": [70, 75, 80]},
    )

    res = client.get(f"/api/cases/{case_id}/planning/targets")
    assert res.status_code == 200
    data = res.json()
    assert data["total_targets"] == 2  # 1 model lesion + 1 user annotation
    assert data["model_findings_count"] == 1
    assert data["user_annotations_count"] == 1
    sources = [t["source"] for t in data["targets"]]
    assert "model" in sources
    assert "user" in sources


def test_real_case_planning_target(client):
    """Validates real KiTS23 case b2f89382-9416-4e94-9486-b00c6b1de64b if present."""
    real_case = "b2f89382-9416-4e94-9486-b00c6b1de64b"
    res = client.get(f"/api/cases/{real_case}/planning/targets")
    if res.status_code == 200:
        data = res.json()
        assert data["model_findings_count"] >= 1
        model_targets = [t for t in data["targets"] if t["source"] == "model"]
        assert any(t["lesion_id"] == "cyst_left" for t in model_targets)
        cyst_target = next(t for t in model_targets if t["lesion_id"] == "cyst_left")
        assert cyst_target["physical_coordinate"] == [164.868, 133.104, 327.363]
        assert cyst_target["voxel_coordinate"] == [110, 89, 218]


def test_mpr_click_coordinate_conversion():
    """Validates 2D display click to 3D voxel coordinate mapping for all orthogonal planes."""
    from src.visualization.mpr import display_to_voxel_crosshair, voxel_to_display_crosshair

    shape = (293, 293, 344)
    current_voxel = [146, 146, 172]

    # Axial plane click: modifies X and Y, preserves Z
    axial_click_col, axial_click_row = 100, 150
    axial_result = display_to_voxel_crosshair("axial", axial_click_col, axial_click_row, current_voxel, shape)
    assert axial_result[0] == (shape[0] - 1) - 100
    assert axial_result[1] == (shape[1] - 1) - 150
    assert axial_result[2] == current_voxel[2]

    # Coronal plane click: modifies X and Z, preserves Y
    coronal_click_col, coronal_click_row = 120, 200
    coronal_result = display_to_voxel_crosshair("coronal", coronal_click_col, coronal_click_row, current_voxel, shape)
    assert coronal_result[0] == (shape[0] - 1) - 120
    assert coronal_result[1] == current_voxel[1]
    assert coronal_result[2] == (shape[2] - 1) - 200

    # Sagittal plane click: modifies Y and Z, preserves X
    sagittal_click_col, sagittal_click_row = 130, 210
    sagittal_result = display_to_voxel_crosshair("sagittal", sagittal_click_col, sagittal_click_row, current_voxel, shape)
    assert sagittal_result[0] == current_voxel[0]
    assert sagittal_result[1] == (shape[1] - 1) - 130
    assert sagittal_result[2] == (shape[2] - 1) - 210


def test_voxel_physical_roundtrip():
    """Validates exact voxel-to-physical and physical-to-voxel conversions."""
    from src.visualization.mpr import voxel_to_physical, physical_to_voxel

    spacing = (1.5, 1.5, 1.5)
    orig_voxel = [110, 89, 218]

    # Voxel -> Physical mm
    phys = voxel_to_physical(spacing, orig_voxel)
    assert phys == [165.0, 133.5, 327.0]

    # Physical mm -> Voxel
    recon_voxel = physical_to_voxel(spacing, phys)
    assert recon_voxel == orig_voxel


def test_mpr_cross_plane_synchronization():
    """
    Validates cross-plane spatial synchronization:
    A target at [tx, ty, tz] has consistent display projections across all three planes,
    and clicking that display projection reconstructs the exact original coordinate.
    """
    from src.visualization.mpr import voxel_to_display_crosshair, display_to_voxel_crosshair

    shape = (293, 293, 344)
    target_voxel = [110, 89, 218]

    # Get projections on each view
    crosshairs = voxel_to_display_crosshair(target_voxel, shape)

    # 1. Axial view: slice_index must match target Z (218)
    assert crosshairs["axial"]["slice_index"] == 218
    axial_col = crosshairs["axial"]["col"]
    axial_row = crosshairs["axial"]["row"]
    # Reconstructing from axial click preserves Z and matches X, Y
    recon_axial = display_to_voxel_crosshair("axial", axial_col, axial_row, target_voxel, shape)
    assert recon_axial == target_voxel

    # 2. Coronal view: slice_index must match target Y (89)
    assert crosshairs["coronal"]["slice_index"] == 89
    coronal_col = crosshairs["coronal"]["col"]
    coronal_row = crosshairs["coronal"]["row"]
    recon_coronal = display_to_voxel_crosshair("coronal", coronal_col, coronal_row, target_voxel, shape)
    assert recon_coronal == target_voxel

    # 3. Sagittal view: slice_index must match target X (110)
    assert crosshairs["sagittal"]["slice_index"] == 110
    sagittal_col = crosshairs["sagittal"]["col"]
    sagittal_row = crosshairs["sagittal"]["row"]
    recon_sagittal = display_to_voxel_crosshair("sagittal", sagittal_col, sagittal_row, target_voxel, shape)
    assert recon_sagittal == target_voxel

