"""
tests/test_coordinate_system.py

Day 19 — Comprehensive Coordinate System & Spatial Registration Audit Test Suite.
Validates the complete spatial pipeline across:
  Voxel Space <-> Physical Space <-> NIfTI World (RAS) Space <-> MPR Display Space <-> 3D Scene / Meshes.

CLINICAL GOVERNANCE NOTICE:
These tests validate computational spatial consistency within the research/educational prototype.
They do not certify clinical-grade registration accuracy or surgical navigation safety.
"""

import math
from pathlib import Path
import nibabel as nib
import numpy as np
import pytest

from src.geometry.coordinate_system import (
    clamp_coordinates,
    voxel_to_world,
    world_to_voxel,
    voxel_to_physical,
    physical_to_voxel,
    calculate_physical_distance,
    voxel_to_display_crosshair,
    display_to_voxel_crosshair,
    get_plane_dimensions,
)
import src.visualization.mpr as mpr_module
from src.planning.annotations import annotation_service
from src.planning.measurement_service import measurement_service
from src.planning.measurement_models import PointToPointRequest


REAL_CT_PATH = Path("datasets/raw/ct/ct_15mm_defaced.nii")
REAL_CASE_ID = "b2f89382-9416-4e94-9486-b00c6b1de64b"


# =====================================================================
# 1. NIfTI Affine & Real CT Inspection Tests
# =====================================================================

def test_real_ct_affine_and_orientation():
    """Validates real CT affine matrix, orientation codes, and spacing."""
    assert REAL_CT_PATH.is_file(), f"Real CT file missing at {REAL_CT_PATH}"

    img = nib.load(str(REAL_CT_PATH))
    affine = img.affine
    shape = img.shape
    zooms = img.header.get_zooms()[:3]

    assert shape == (293, 293, 344)
    assert np.allclose(zooms, (1.5, 1.5, 1.5), atol=1e-3)

    # Orientation must be RAS (Right, Anterior, Superior)
    axcodes = nib.aff2axcodes(affine)
    assert axcodes == ("R", "A", "S")

    # Rotation/scaling 3x3 must be diagonal with positive entries (no skew, no flips)
    R = affine[:3, :3]
    assert np.allclose(R, np.diag([1.5, 1.5, 1.5]), atol=1e-3)

    # Translation offset
    T = affine[:3, 3]
    expected_T = np.array([-225.07128906, -46.57128906, -146.5])
    assert np.allclose(T, expected_T, atol=1e-2)


# =====================================================================
# 2. Voxel <-> World (Affine) Roundtrip Tests
# =====================================================================

@pytest.mark.parametrize(
    "voxel",
    [
        [0, 0, 0],                         # Origin voxel
        [146, 146, 172],                   # Volume center voxel
        [292, 292, 343],                   # Max corner voxel
        [110, 89, 218],                    # KiTS23 lesion centroid voxel
        [50, 100, 200],                    # Arbitrary internal point
        [200, 50, 100],                    # Arbitrary internal point 2
    ],
)
def test_voxel_world_voxel_roundtrip(voxel):
    """
    Validates that transforming voxel -> world -> voxel recovers the original voxel
    with zero integer discrepancy.
    """
    img = nib.load(str(REAL_CT_PATH))
    affine = img.affine

    world = voxel_to_world(affine, voxel)
    recovered_voxel = world_to_voxel(affine, world)

    assert recovered_voxel == voxel, (
        f"Roundtrip mismatch for voxel {voxel}: "
        f"world={world}, recovered={recovered_voxel}"
    )


def test_voxel_world_floating_point_precision():
    """
    Tests sub-millimeter precision between affine multiplication and inverse affine.
    """
    img = nib.load(str(REAL_CT_PATH))
    affine = img.affine
    inv_affine = np.linalg.inv(affine)

    v_orig = np.array([110.4, 88.7, 218.2, 1.0])
    w = affine @ v_orig
    v_rec = inv_affine @ w

    error = np.linalg.norm(v_orig[:3] - v_rec[:3])
    assert error < 1e-12, f"Floating point inversion error: {error}"


# =====================================================================
# 3. Voxel <-> Physical (Spacing) Roundtrip & Anisotropic Distance
# =====================================================================

@pytest.mark.parametrize(
    "spacing,voxel",
    [
        ((1.5, 1.5, 1.5), [0, 0, 0]),
        ((1.5, 1.5, 1.5), [146, 146, 172]),
        ((1.5, 1.5, 1.5), [110, 89, 218]),
        ((0.75, 0.75, 2.5), [10, 20, 30]),  # Anisotropic slice thickness
        ((0.5, 0.5, 1.0), [100, 200, 150]),
    ],
)
def test_voxel_physical_voxel_roundtrip(spacing, voxel):
    """
    Validates that transforming voxel -> physical -> voxel returns identical integer coordinates.
    """
    phys = voxel_to_physical(spacing, voxel)
    rec_voxel = physical_to_voxel(spacing, phys)
    assert rec_voxel == voxel


def test_physical_distance_anisotropic_spacing():
    """
    Validates that physical distance strictly uses millimeter spacing and does NOT
    calculate naive Euclidean distance in raw voxel space.
    """
    aniso_spacing = (0.8, 0.8, 2.5)  # 2.5 mm slice thickness
    vox_a = [10, 10, 10]
    vox_b = [10, 10, 14]             # 4 slices along Z = 4 * 2.5 = 10.0 mm

    phys_a = voxel_to_physical(aniso_spacing, vox_a)  # [8.0, 8.0, 25.0]
    phys_b = voxel_to_physical(aniso_spacing, vox_b)  # [8.0, 8.0, 35.0]

    dist = calculate_physical_distance(phys_a, phys_b)
    assert abs(dist - 10.0) < 1e-3

    # Raw voxel distance would have been 4.0, which is incorrect
    raw_voxel_dist = math.sqrt(sum((b - a) ** 2 for a, b in zip(vox_a, vox_b)))
    assert raw_voxel_dist == 4.0
    assert abs(dist - raw_voxel_dist) > 5.0, "Physical distance must not equal naive voxel distance!"


# =====================================================================
# 4. MPR Display Space Forward & Inverse Roundtrips
# =====================================================================

@pytest.mark.parametrize(
    "voxel",
    [
        [0, 0, 0],
        [146, 146, 172],
        [292, 292, 343],
        [110, 89, 218],
        [75, 180, 250],
    ],
)
def test_mpr_display_crosshair_roundtrip(voxel):
    """
    Validates that for all 3 orthogonal planes (Axial, Coronal, Sagittal):
        voxel -> (col, row, slice) -> voxel
    is an exact mathematical inverse.
    """
    shape = (293, 293, 344)
    disp = voxel_to_display_crosshair(voxel, shape)

    # Axial projection check
    ax_col = disp["axial"]["col"]
    ax_row = disp["axial"]["row"]
    assert disp["axial"]["slice_index"] == voxel[2]
    rec_axial = display_to_voxel_crosshair("axial", ax_col, ax_row, voxel, shape)
    assert rec_axial == voxel

    # Coronal projection check
    cor_col = disp["coronal"]["col"]
    cor_row = disp["coronal"]["row"]
    assert disp["coronal"]["slice_index"] == voxel[1]
    rec_coronal = display_to_voxel_crosshair("coronal", cor_col, cor_row, voxel, shape)
    assert rec_coronal == voxel

    # Sagittal projection check
    sag_col = disp["sagittal"]["col"]
    sag_row = disp["sagittal"]["row"]
    assert disp["sagittal"]["slice_index"] == voxel[0]
    rec_sagittal = display_to_voxel_crosshair("sagittal", sag_col, sag_row, voxel, shape)
    assert rec_sagittal == voxel


def test_mpr_plane_dimensions():
    """Validates orthogonal plane slice count, height, and width."""
    shape = (293, 293, 344)
    dims_ax = get_plane_dimensions(shape, "axial")
    assert dims_ax == {"total_slices": 344, "height": 293, "width": 293, "slice_axis": 2}

    dims_cor = get_plane_dimensions(shape, "coronal")
    assert dims_cor == {"total_slices": 293, "height": 344, "width": 293, "slice_axis": 1}

    dims_sag = get_plane_dimensions(shape, "sagittal")
    assert dims_sag == {"total_slices": 293, "height": 344, "width": 293, "slice_axis": 0}


# =====================================================================
# 5. Real KiTS23 Lesion Registration Audit
# =====================================================================

def test_real_kits23_lesion_registration():
    """
    End-to-end verification for case b2f89382-9416-4e94-9486-b00c6b1de64b finding model_cyst_left:
    lesion voxel -> NIfTI world -> planning target -> MPR -> 3D lesion mesh
    """
    case_dir = Path("outputs/cases") / REAL_CASE_ID
    assert case_dir.is_dir(), f"Case directory not found: {case_dir}"

    # 1. Lesion mask verification
    lesion_mask_path = case_dir / "lesions" / "cyst_left.nii.gz"
    assert lesion_mask_path.is_file()
    l_img = nib.load(str(lesion_mask_path))
    l_data = l_img.get_fdata() > 0
    fg_indices = np.argwhere(l_data)
    assert len(fg_indices) == 91

    mean_vox = fg_indices.mean(axis=0)
    rounded_vox = [int(round(c)) for c in mean_vox]
    assert rounded_vox == [110, 89, 218]

    # 2. Physical & World coordinates
    spacing = tuple(float(s) for s in l_img.header.get_zooms()[:3])
    phys_centroid = mean_vox * np.array(spacing)
    assert np.allclose(phys_centroid, [164.868, 133.104, 327.363], atol=1e-2)

    world_centroid = voxel_to_world(l_img.affine, rounded_vox)
    # world x = 110 * 1.5 - 225.071 = -60.071 mm
    # world y = 89 * 1.5 - 46.571 = 86.929 mm
    # world z = 218 * 1.5 - 146.5 = 180.500 mm
    assert np.allclose(world_centroid, [-60.071, 86.929, 180.500], atol=1e-2)

    # 3. Planning target exposure
    targets = annotation_service.get_all_planning_targets(REAL_CASE_ID)
    model_targets = [t for t in targets if t.target_id == "model_cyst_left"]
    assert len(model_targets) == 1
    t = model_targets[0]
    assert t.voxel_coordinate == [110, 89, 218]
    assert np.allclose(t.physical_coordinate, [164.868, 133.104, 327.363], atol=1e-2)

    # 4. 3D OBJ mesh vertex mean vs voxel centroid in physical space
    mesh_path = case_dir / "meshes" / "cyst_left.obj"
    assert mesh_path.is_file()
    verts = []
    with open(mesh_path) as f:
        for line in f:
            if line.startswith("v "):
                parts = line.strip().split()
                verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
    mesh_centroid = np.mean(verts, axis=0)

    # Spatial difference between Marching Cubes mesh surface centroid and mask voxel centroid
    diff_mm = np.linalg.norm(mesh_centroid - phys_centroid)
    assert diff_mm < 0.15, (
        f"Mesh surface centroid {mesh_centroid} differs from voxel physical centroid "
        f"{phys_centroid} by {diff_mm} mm (expected < 0.15 mm)."
    )


# =====================================================================
# 6. Planning Point & Measurement Geometry Consistency
# =====================================================================

def test_measurement_endpoint_registration():
    """
    Validates that a point-to-point measurement created between two MPR voxels:
      1. Converts accurately to physical millimeters.
      2. Calculates true physical Euclidean distance.
      3. Provides coordinates directly consumable by Three.js 3D measurement lines.
    """
    voxel_a = [100, 100, 200]
    voxel_b = [120, 110, 220]
    spacing = (1.5, 1.5, 1.5)

    phys_a = voxel_to_physical(spacing, voxel_a)  # [150.0, 150.0, 300.0]
    phys_b = voxel_to_physical(spacing, voxel_b)  # [180.0, 165.0, 330.0]

    # Delta: [30.0, 15.0, 30.0] -> sqrt(900 + 225 + 900) = sqrt(2025) = 45.0 mm
    expected_dist_mm = 45.0
    calc_dist = calculate_physical_distance(phys_a, phys_b)
    assert abs(calc_dist - expected_dist_mm) < 1e-3

    req = PointToPointRequest(
        start_voxel=voxel_a,
        end_voxel=voxel_b,
        label="Test Registration Measurement",
    )
    m = measurement_service.create_point_to_point_measurement(REAL_CASE_ID, req)
    try:
        assert m.start_voxel == voxel_a
        assert m.end_voxel == voxel_b
        assert m.start_physical == phys_a
        assert m.end_physical == phys_b
        assert m.distance_mm == expected_dist_mm
        assert m.distance_cm == round(expected_dist_mm / 10.0, 4)
    finally:
        # Cleanup
        measurement_service.delete_measurement(REAL_CASE_ID, m.measurement_id)


# =====================================================================
# 7. Backward Compatibility Re-export Check
# =====================================================================

def test_mpr_module_reexport_integrity():
    """
    Verifies that src.visualization.mpr re-exports all coordinate functions
    from src.geometry.coordinate_system with identical identity/behavior.
    """
    assert mpr_module.clamp_coordinates is clamp_coordinates
    assert mpr_module.voxel_to_world is voxel_to_world
    assert mpr_module.world_to_voxel is world_to_voxel
    assert mpr_module.voxel_to_physical is voxel_to_physical
    assert mpr_module.physical_to_voxel is physical_to_voxel
    assert mpr_module.get_plane_dimensions is get_plane_dimensions
    assert mpr_module.voxel_to_display_crosshair is voxel_to_display_crosshair
    assert mpr_module.display_to_voxel_crosshair is display_to_voxel_crosshair
