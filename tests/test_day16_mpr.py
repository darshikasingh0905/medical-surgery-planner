"""
tests/test_day16_mpr.py

Comprehensive unit tests for Day 16: Multi-Planar Reconstruction (MPR).

CLINICAL GOVERNANCE:
  This module is an educational/research visualization tool.
  Outputs are NOT clinically validated measurements or surgical guidance.
"""

from pathlib import Path
import io
import json

import numpy as np
import nibabel as nib
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.visualization.mpr import (
    WINDOW_PRESETS,
    clamp_coordinates,
    voxel_to_world,
    world_to_voxel,
    voxel_to_physical,
    physical_to_voxel,
    get_plane_dimensions,
    get_axial_slice,
    get_coronal_slice,
    get_sagittal_slice,
    extract_plane_slice,
    apply_window_to_slice,
    encode_slice_to_png,
    voxel_to_display_crosshair,
    display_to_voxel_crosshair,
    MPRVolumeManager,
)

client = TestClient(app)

SHAPE_4x5x6 = (4, 5, 6)
IDENTITY_AFFINE = np.eye(4, dtype=np.float64)
SPACING_1_1_1 = (1.0, 1.0, 1.0)
SPACING_1_5 = (1.5, 1.5, 2.0)


def make_synthetic_volume(shape=(10, 12, 8), dtype=np.float32):
    vol = np.zeros(shape, dtype=dtype)
    nx, ny, nz = shape
    for z in range(nz):
        vol[:, :, z] = float(z) * 10.0
    return vol


def make_synthetic_nifti(tmp_path: Path, shape=(10, 12, 8), spacing=(1.5, 1.5, 2.0)):
    data = make_synthetic_volume(shape)
    affine = np.diag([spacing[0], spacing[1], spacing[2], 1.0])
    img = nib.Nifti1Image(data, affine)
    fpath = tmp_path / "synthetic_ct.nii.gz"
    nib.save(img, str(fpath))
    return fpath


class TestClampCoordinates:
    def test_in_range_unchanged(self):
        assert clamp_coordinates([2, 3, 4], SHAPE_4x5x6) == [2, 3, 4]

    def test_negative_clamped_to_zero(self):
        assert clamp_coordinates([-1, -5, -100], SHAPE_4x5x6) == [0, 0, 0]

    def test_exceeds_max_clamped_to_max(self):
        assert clamp_coordinates([100, 200, 300], SHAPE_4x5x6) == [3, 4, 5]

    def test_boundary_values_unchanged(self):
        assert clamp_coordinates([0, 0, 0], SHAPE_4x5x6) == [0, 0, 0]
        assert clamp_coordinates([3, 4, 5], SHAPE_4x5x6) == [3, 4, 5]

    def test_float_inputs_rounded(self):
        assert clamp_coordinates([1.7, 2.3, 4.6], SHAPE_4x5x6) == [2, 2, 5]

    def test_numpy_input_supported(self):
        assert clamp_coordinates(np.array([1, 2, 3]), SHAPE_4x5x6) == [1, 2, 3]


class TestVoxelWorldTransforms:
    def test_identity_affine_passthrough(self):
        world = voxel_to_world(IDENTITY_AFFINE, [10, 20, 30])
        assert world == [10.0, 20.0, 30.0]

    def test_scaled_affine(self):
        affine = np.diag([1.5, 1.5, 2.0, 1.0])
        world = voxel_to_world(affine, [10, 10, 10])
        assert abs(world[0] - 15.0) < 1e-6
        assert abs(world[1] - 15.0) < 1e-6
        assert abs(world[2] - 20.0) < 1e-6

    def test_roundtrip(self):
        affine = np.diag([1.5, 1.5, 2.0, 1.0])
        original = [7, 11, 5]
        assert world_to_voxel(affine, voxel_to_world(affine, original)) == original

    def test_origin_maps_to_origin(self):
        assert voxel_to_world(IDENTITY_AFFINE, [0, 0, 0]) == [0.0, 0.0, 0.0]


class TestVoxelPhysicalTransforms:
    def test_spacing_1_passthrough(self):
        assert voxel_to_physical(SPACING_1_1_1, [5, 10, 15]) == [5.0, 10.0, 15.0]

    def test_anisotropic_spacing(self):
        phys = voxel_to_physical(SPACING_1_5, [10, 10, 10])
        assert abs(phys[0] - 15.0) < 1e-6
        assert abs(phys[2] - 20.0) < 1e-6

    def test_roundtrip(self):
        voxel = [4, 7, 3]
        assert physical_to_voxel(SPACING_1_5, voxel_to_physical(SPACING_1_5, voxel)) == voxel


class TestPlaneDimensions:
    def test_axial(self):
        r = get_plane_dimensions((4, 5, 6), "axial")
        assert r["total_slices"] == 6 and r["height"] == 5 and r["width"] == 4 and r["slice_axis"] == 2

    def test_coronal(self):
        r = get_plane_dimensions((4, 5, 6), "coronal")
        assert r["total_slices"] == 5 and r["height"] == 6 and r["width"] == 4 and r["slice_axis"] == 1

    def test_sagittal(self):
        r = get_plane_dimensions((4, 5, 6), "sagittal")
        assert r["total_slices"] == 4 and r["height"] == 6 and r["width"] == 5 and r["slice_axis"] == 0

    def test_invalid_plane_raises(self):
        with pytest.raises(ValueError, match="Invalid plane"):
            get_plane_dimensions((4, 5, 6), "oblique")

    def test_case_insensitive(self):
        assert get_plane_dimensions((4, 5, 6), "Axial")["total_slices"] == 6


class TestSliceExtraction:
    def setup_method(self):
        self.vol = make_synthetic_volume((10, 12, 8))

    def test_axial_slice_shape(self):
        assert get_axial_slice(self.vol, 3).shape == (12, 10)

    def test_coronal_slice_shape(self):
        assert get_coronal_slice(self.vol, 5).shape == (8, 10)

    def test_sagittal_slice_shape(self):
        assert get_sagittal_slice(self.vol, 7).shape == (8, 12)

    def test_axial_clamping_below_zero(self):
        assert get_axial_slice(self.vol, -5).shape == (12, 10)

    def test_axial_clamping_above_max(self):
        assert get_axial_slice(self.vol, 9999).shape == (12, 10)

    def test_extract_delegates_axial(self):
        np.testing.assert_array_equal(
            get_axial_slice(self.vol, 4),
            extract_plane_slice(self.vol, "axial", 4)
        )

    def test_extract_delegates_coronal(self):
        np.testing.assert_array_equal(
            get_coronal_slice(self.vol, 6),
            extract_plane_slice(self.vol, "coronal", 6)
        )

    def test_extract_delegates_sagittal(self):
        np.testing.assert_array_equal(
            get_sagittal_slice(self.vol, 2),
            extract_plane_slice(self.vol, "sagittal", 2)
        )

    def test_extract_invalid_raises(self):
        with pytest.raises(ValueError, match="Invalid plane"):
            extract_plane_slice(self.vol, "coronal-oblique", 0)


class TestWindowLevel:
    def test_output_dtype_is_uint8(self):
        slc = np.array([[0.0, 100.0], [200.0, 300.0]], dtype=np.float32)
        assert apply_window_to_slice(slc, window_width=400, window_level=40).dtype == np.uint8

    def test_values_mapped_proportionally(self):
        slc = np.array([[0.0, 100.0, 200.0]], dtype=np.float32)
        result = apply_window_to_slice(slc, window_width=200, window_level=100)
        assert result[0, 0] == 0
        assert result[0, 1] in (127, 128)
        assert result[0, 2] == 255

    def test_below_window_clamped_to_zero(self):
        assert apply_window_to_slice(np.array([[-9999.0]]), window_width=400, window_level=40)[0, 0] == 0

    def test_above_window_clamped_to_255(self):
        assert apply_window_to_slice(np.array([[9999.0]]), window_width=400, window_level=40)[0, 0] == 255

    def test_all_presets_valid(self):
        for k, v in WINDOW_PRESETS.items():
            assert "name" in v and "ww" in v and "wl" in v

    def test_bone_preset_high_ww(self):
        assert WINDOW_PRESETS["bone"]["ww"] >= 1000.0

    def test_lung_preset_negative_wl(self):
        assert WINDOW_PRESETS["lung"]["wl"] < 0


class TestPNGEncoding:
    def _decode(self, png_bytes):
        from PIL import Image
        return np.asarray(Image.open(io.BytesIO(png_bytes)))

    def test_grayscale_no_mask(self):
        slc = np.zeros((10, 10), dtype=np.uint8)
        png = encode_slice_to_png(slc, mask_u8=None)
        assert self._decode(png).ndim == 2

    def test_rgb_with_mask(self):
        slc = np.zeros((10, 10), dtype=np.uint8)
        mask = np.zeros((10, 10), dtype=np.uint8)
        mask[3:7, 3:7] = 1
        assert self._decode(encode_slice_to_png(slc, mask_u8=mask)).ndim == 3

    def test_empty_mask_produces_grayscale(self):
        slc = np.full((8, 8), 128, dtype=np.uint8)
        mask = np.zeros((8, 8), dtype=np.uint8)
        assert self._decode(encode_slice_to_png(slc, mask_u8=mask)).ndim == 2

    def test_png_magic_bytes(self):
        slc = np.zeros((5, 5), dtype=np.uint8)
        assert encode_slice_to_png(slc)[:8] == b"\x89PNG\r\n\x1a\n"

    def test_output_dimensions(self):
        slc = np.zeros((20, 30), dtype=np.uint8)
        arr = self._decode(encode_slice_to_png(slc))
        assert arr.shape[0] == 20 and arr.shape[1] == 30


class TestCrosshairTransforms:
    SHAPE = (10, 12, 8)

    def test_voxel_to_crosshair_axial(self):
        r = voxel_to_display_crosshair([4, 6, 3], self.SHAPE)
        assert r["axial"]["col"] == 5 and r["axial"]["row"] == 5 and r["axial"]["slice_index"] == 3

    def test_voxel_to_crosshair_coronal(self):
        r = voxel_to_display_crosshair([4, 6, 3], self.SHAPE)
        assert r["coronal"]["col"] == 5 and r["coronal"]["row"] == 4 and r["coronal"]["slice_index"] == 6

    def test_voxel_to_crosshair_sagittal(self):
        r = voxel_to_display_crosshair([4, 6, 3], self.SHAPE)
        assert r["sagittal"]["col"] == 5 and r["sagittal"]["row"] == 4 and r["sagittal"]["slice_index"] == 4

    def test_roundtrip_axial(self):
        shape, original = self.SHAPE, [4, 6, 3]
        ch = voxel_to_display_crosshair(original, shape)
        rec = display_to_voxel_crosshair("axial", ch["axial"]["col"], ch["axial"]["row"], original, shape)
        assert rec[:2] == original[:2]

    def test_roundtrip_coronal(self):
        shape, original = self.SHAPE, [4, 6, 3]
        ch = voxel_to_display_crosshair(original, shape)
        rec = display_to_voxel_crosshair("coronal", ch["coronal"]["col"], ch["coronal"]["row"], original, shape)
        assert rec[0] == original[0] and rec[2] == original[2]

    def test_roundtrip_sagittal(self):
        shape, original = self.SHAPE, [4, 6, 3]
        ch = voxel_to_display_crosshair(original, shape)
        rec = display_to_voxel_crosshair("sagittal", ch["sagittal"]["col"], ch["sagittal"]["row"], original, shape)
        assert rec[0] == original[0]

    def test_invalid_plane_raises(self):
        with pytest.raises(ValueError, match="Invalid plane"):
            display_to_voxel_crosshair("axial-tilt", 5, 5, [0, 0, 0], self.SHAPE)

    def test_origin_voxel(self):
        r = voxel_to_display_crosshair([0, 0, 0], self.SHAPE)
        assert r["axial"]["col"] == self.SHAPE[0] - 1 and r["axial"]["row"] == self.SHAPE[1] - 1

    def test_max_voxel(self):
        nx, ny, nz = self.SHAPE
        r = voxel_to_display_crosshair([nx-1, ny-1, nz-1], self.SHAPE)
        assert r["axial"]["col"] == 0 and r["axial"]["row"] == 0


class TestMPRVolumeManager:
    def _make_manager(self, tmp_path, shape=(10, 12, 8)):
        nifti_path = make_synthetic_nifti(tmp_path, shape=shape)
        manager = MPRVolumeManager()
        manager.get_case_ct_path = lambda cid: nifti_path
        manager.get_case_lesion_path = lambda *a, **kw: None
        return manager

    def test_load_returns_dict(self, tmp_path):
        entry = self._make_manager(tmp_path).load_case_volume("t")
        for k in ("volume", "shape", "voxel_spacing", "affine"):
            assert k in entry

    def test_shape_matches_nifti(self, tmp_path):
        assert self._make_manager(tmp_path, shape=(10, 12, 8)).load_case_volume("t")["shape"] == (10, 12, 8)

    def test_cache_same_object(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.load_case_volume("t") is mgr.load_case_volume("t")

    def test_metadata_structure(self, tmp_path):
        meta = self._make_manager(tmp_path).get_metadata("t")
        for k in ("shape", "voxel_spacing_mm", "planes", "presets", "default_cursor", "affine"):
            assert k in meta

    def test_metadata_planes(self, tmp_path):
        planes = self._make_manager(tmp_path, shape=(10, 12, 8)).get_metadata("t")["planes"]
        assert planes["axial"]["total_slices"] == 8
        assert planes["coronal"]["total_slices"] == 12
        assert planes["sagittal"]["total_slices"] == 10

    def test_slice_bytes_is_png(self, tmp_path):
        png = self._make_manager(tmp_path).get_slice_bytes("t", "axial", 4, 400, 40, False)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_all_planes_produce_png(self, tmp_path):
        mgr = self._make_manager(tmp_path, shape=(10, 12, 8))
        for plane, idx in [("axial", 4), ("coronal", 5), ("sagittal", 3)]:
            png = mgr.get_slice_bytes("t", plane, idx, 400, 40, False)
            assert png[:8] == b"\x89PNG\r\n\x1a\n"

    def test_missing_ct_raises(self):
        mgr = MPRVolumeManager()
        mgr.get_case_ct_path = lambda cid: None
        with pytest.raises(FileNotFoundError):
            mgr.load_case_volume("bad-case")


class TestMPREndpoints:
    def _setup(self, tmp_path, monkeypatch):
        import src.api.utils.case_manager as cm
        monkeypatch.setattr(cm, "CASES_DIR", tmp_path / "cases")
        case_id = "mpr-test-case"
        from src.api.utils.case_manager import init_case_directory
        case_path = init_case_directory(case_id, "scan.nii.gz")
        with open(case_path / "case.json", "w") as f:
            json.dump({"case_id": case_id, "filename": "scan.nii.gz", "status": "completed"}, f)
        nifti_path = make_synthetic_nifti(tmp_path, shape=(10, 12, 8))
        import shutil
        shutil.copy(str(nifti_path), str(case_path / "input" / "scan.nii.gz"))
        from src.visualization import mpr as mpr_mod
        orig = mpr_mod.mpr_manager.get_case_ct_path
        def patched(cid):
            return case_path / "input" / "scan.nii.gz" if cid == case_id else orig(cid)
        monkeypatch.setattr(mpr_mod.mpr_manager, "get_case_ct_path", patched)
        mpr_mod.mpr_manager._cache.pop(case_id, None)
        return case_id

    def test_metadata_200(self, tmp_path, monkeypatch):
        cid = self._setup(tmp_path, monkeypatch)
        assert client.get(f"/api/cases/{cid}/mpr").status_code == 200

    def test_metadata_fields(self, tmp_path, monkeypatch):
        cid = self._setup(tmp_path, monkeypatch)
        data = client.get(f"/api/cases/{cid}/mpr").json()
        for k in ("shape", "voxel_spacing_mm", "planes", "presets"):
            assert k in data

    def test_metadata_planes(self, tmp_path, monkeypatch):
        cid = self._setup(tmp_path, monkeypatch)
        planes = client.get(f"/api/cases/{cid}/mpr").json()["planes"]
        assert planes["axial"]["total_slices"] == 8
        assert planes["coronal"]["total_slices"] == 12
        assert planes["sagittal"]["total_slices"] == 10

    def test_metadata_unknown_404(self):
        assert client.get("/api/cases/nonexistent-uuid/mpr").status_code == 404

    def test_axial_png(self, tmp_path, monkeypatch):
        cid = self._setup(tmp_path, monkeypatch)
        r = client.get(f"/api/cases/{cid}/mpr/slice/axial/4")
        assert r.status_code == 200 and r.headers["content-type"] == "image/png"
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_coronal_png(self, tmp_path, monkeypatch):
        cid = self._setup(tmp_path, monkeypatch)
        assert client.get(f"/api/cases/{cid}/mpr/slice/coronal/5").status_code == 200

    def test_sagittal_png(self, tmp_path, monkeypatch):
        cid = self._setup(tmp_path, monkeypatch)
        assert client.get(f"/api/cases/{cid}/mpr/slice/sagittal/3").status_code == 200

    def test_windowing_params(self, tmp_path, monkeypatch):
        cid = self._setup(tmp_path, monkeypatch)
        assert client.get(f"/api/cases/{cid}/mpr/slice/axial/4?ww=2000&wl=500").status_code == 200

    def test_overlay_disabled(self, tmp_path, monkeypatch):
        cid = self._setup(tmp_path, monkeypatch)
        assert client.get(f"/api/cases/{cid}/mpr/slice/axial/4?overlay_lesion=false").status_code == 200

    def test_invalid_plane_400(self, tmp_path, monkeypatch):
        cid = self._setup(tmp_path, monkeypatch)
        r = client.get(f"/api/cases/{cid}/mpr/slice/oblique/4")
        assert r.status_code == 400 and "Invalid plane" in r.json()["detail"]

    def test_out_of_range_400(self, tmp_path, monkeypatch):
        cid = self._setup(tmp_path, monkeypatch)
        r = client.get(f"/api/cases/{cid}/mpr/slice/axial/9999")
        assert r.status_code == 400 and "out of range" in r.json()["detail"]

    def test_unknown_case_404(self):
        assert client.get("/api/cases/nonexistent-uuid/mpr/slice/axial/0").status_code == 404


REAL_CASE_ID = "b2f89382-9416-4e94-9486-b00c6b1de64b"
REAL_CASE_DIR = Path("outputs/cases") / REAL_CASE_ID
real_case_available = (REAL_CASE_DIR / "input").is_dir() and any(
    (REAL_CASE_DIR / "input").glob("*.nii*")
)


@pytest.mark.skipif(not real_case_available, reason="Real KiTS23 case not available")
class TestMPRRealCase:
    def test_metadata_api(self):
        r = client.get(f"/api/cases/{REAL_CASE_ID}/mpr")
        assert r.status_code == 200
        meta = r.json()
        assert meta["shape"][0] > 100 and meta["voxel_spacing_mm"][0] > 0.1

    def test_axial_slice_api(self):
        r = client.get(f"/api/cases/{REAL_CASE_ID}/mpr/slice/axial/172")
        assert r.status_code == 200 and r.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_coronal_kidney_preset(self):
        r = client.get(f"/api/cases/{REAL_CASE_ID}/mpr/slice/coronal/146?ww=350&wl=50")
        assert r.status_code == 200

    def test_sagittal_no_overlay(self):
        r = client.get(f"/api/cases/{REAL_CASE_ID}/mpr/slice/sagittal/146?overlay_lesion=false")
        assert r.status_code == 200

    def test_lesion_overlay_axial(self):
        r = client.get(f"/api/cases/{REAL_CASE_ID}/mpr/slice/axial/180?overlay_lesion=true")
        assert r.status_code == 200
