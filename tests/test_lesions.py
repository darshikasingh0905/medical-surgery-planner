"""
tests/test_lesions.py

Unit tests for Day 9: Renal Lesion Pipeline Foundation.
Verifies ROI extraction, physical margin calculations, boundary clamping,
intensity preprocessing, model abstraction error handling, connected-component
postprocessing, and original-space coordinate re-embedding.

NOTE: All test volumes use synthetic geometric test fixtures created solely
for deterministic software unit testing. None of these tests imply clinical validation.
"""

from pathlib import Path
import json
import pytest
import numpy as np
import nibabel as nib

from src.lesions.roi_extractor import extract_kidney_roi, save_roi_package
from src.lesions.lesion_inference import (
    preprocess_ct_roi,
    LesionModelConfig,
    LesionInferenceEngine,
)
from src.lesions.postprocessing import (
    postprocess_lesion_mask,
    embed_roi_in_original_space,
    save_original_space_mask,
    create_lesion_metadata,
)


@pytest.fixture
def synthetic_ct_and_mask(tmp_path: Path):
    """
    Creates a synthetic 3D CT scan and a kidney mask in a temporary folder.
    CT volume: 60 x 60 x 50 with anisotropic voxel spacing (1.0, 1.5, 2.0) mm.
    Kidney mask: Foreground sphere placed at indices [20:35, 20:35, 15:30].
    """
    shape = (60, 60, 50)
    spacing = (1.0, 1.5, 2.0)

    # Affine with anisotropic spacing
    affine = np.diag([spacing[0], spacing[1], spacing[2], 1.0])
    affine[0, 3] = -30.0  # origin offset
    affine[1, 3] = -45.0
    affine[2, 3] = 10.0

    # Synthetic CT with soft-tissue intensities (-100 to 150 HU)
    ct_data = np.random.uniform(-100, 150, size=shape).astype(np.float32)

    # Synthetic binary kidney mask
    mask_data = np.zeros(shape, dtype=np.uint8)
    mask_data[20:35, 20:35, 15:30] = 1

    ct_path = tmp_path / "synthetic_scan.nii.gz"
    mask_path = tmp_path / "synthetic_kidney.nii.gz"

    ct_nii = nib.Nifti1Image(ct_data, affine)
    mask_nii = nib.Nifti1Image(mask_data, affine)

    nib.save(ct_nii, str(ct_path))
    nib.save(mask_nii, str(mask_path))

    return ct_path, mask_path, ct_data, mask_data, affine, spacing


def test_roi_bounding_box_and_metadata(synthetic_ct_and_mask):
    """Verifies that the extracted ROI strictly encloses the mask and preserves metadata."""
    ct_path, mask_path, ct_data, mask_data, affine, spacing = synthetic_ct_and_mask

    physical_margin_mm = 15.0
    ct_roi, mask_roi, metadata, roi_affine, header = extract_kidney_roi(
        ct_path, mask_path, physical_margin_mm=physical_margin_mm
    )

    # Check that mask foreground voxels are completely preserved inside the ROI
    assert np.sum(mask_roi > 0) == np.sum(mask_data > 0)

    # Check metadata fields
    assert metadata["source_image_shape"] == list(ct_data.shape)
    assert metadata["source_voxel_spacing"] == list(spacing)
    assert metadata["physical_margin_mm"] == physical_margin_mm
    assert "roi_voxel_bounds" in metadata
    assert "roi_slices" in metadata
    assert metadata["roi_shape"] == list(ct_roi.shape)

    # Verify ROI shape matches slice bounds
    expected_shape = [
        metadata["roi_slices"][i][1] - metadata["roi_slices"][i][0]
        for i in range(3)
    ]
    assert list(ct_roi.shape) == expected_shape


def test_physical_margin_voxel_conversion(synthetic_ct_and_mask):
    """
    Verifies that physical margin (in mm) correctly translates into anisotropic voxel padding.
    Spacing is (1.0, 1.5, 2.0) mm.
    For margin = 10.0 mm:
    axis 0: ceil(10 / 1.0) = 10 voxels
    axis 1: ceil(10 / 1.5) = 7 voxels
    axis 2: ceil(10 / 2.0) = 5 voxels
    """
    ct_path, mask_path, _, _, _, _ = synthetic_ct_and_mask

    _, _, metadata, _, _ = extract_kidney_roi(ct_path, mask_path, physical_margin_mm=10.0)

    expected_padding = [10, 7, 5]
    assert metadata["voxel_padding"] == expected_padding


def test_roi_boundary_clamping(tmp_path: Path):
    """Verifies that an ROI near the image edge is clamped cleanly to boundaries [0, dim - 1]."""
    shape = (40, 40, 40)
    affine = np.eye(4)

    ct_data = np.zeros(shape, dtype=np.float32)
    mask_data = np.zeros(shape, dtype=np.uint8)

    # Place mask directly at the volume edge [0:5, 35:40, 0:5]
    mask_data[0:5, 35:40, 0:5] = 1

    ct_path = tmp_path / "edge_ct.nii.gz"
    mask_path = tmp_path / "edge_mask.nii.gz"

    nib.save(nib.Nifti1Image(ct_data, affine), str(ct_path))
    nib.save(nib.Nifti1Image(mask_data, affine), str(mask_path))

    # Request large 30mm margin
    ct_roi, mask_roi, metadata, _, _ = extract_kidney_roi(ct_path, mask_path, physical_margin_mm=30.0)

    # Bounds must be within [0, 39]
    for i in range(3):
        assert metadata["roi_voxel_bounds"][i][0] >= 0
        assert metadata["roi_voxel_bounds"][i][1] < shape[i]
        assert metadata["roi_slices"][i][0] >= 0
        assert metadata["roi_slices"][i][1] <= shape[i]

    # Bounds for axis 0 must clamp at 0
    assert metadata["roi_voxel_bounds"][0][0] == 0
    # Bounds for axis 1 must clamp at 39
    assert metadata["roi_voxel_bounds"][1][1] == 39


def test_save_roi_package(synthetic_ct_and_mask, tmp_path: Path):
    """Tests writing the ROI NIfTI files and metadata to a package directory."""
    ct_path, mask_path, _, _, _, _ = synthetic_ct_and_mask
    ct_roi, mask_roi, metadata, roi_affine, _ = extract_kidney_roi(ct_path, mask_path)

    out_dir = tmp_path / "roi_package"
    saved = save_roi_package(out_dir, ct_roi, mask_roi, metadata, roi_affine, "test_kidney")

    assert saved["ct_roi_path"].exists()
    assert saved["mask_roi_path"].exists()
    assert saved["metadata_path"].exists()

    with open(saved["metadata_path"], "r") as f:
        meta_loaded = json.load(f)
    assert meta_loaded["source_mask_name"] == Path(mask_path).name


def test_preprocessing_windowing_and_normalization():
    """Tests HU windowing and normalization transforms."""
    # Test array with values spanning from -1000 to +1000 HU
    raw = np.array([[-1000.0, -150.0], [50.0, 500.0]], dtype=np.float32)[:, :, np.newaxis]

    norm, params = preprocess_ct_roi(raw, hu_min=-150.0, hu_max=250.0, normalize_mode="minmax")

    assert params["hu_min"] == -150.0
    assert params["hu_max"] == 250.0
    assert params["normalize_mode"] == "minmax"
    # Values <= -150 should map to 0.0
    assert norm[0, 0, 0] == 0.0
    assert norm[0, 1, 0] == 0.0
    # Values >= 250 should map to 1.0
    assert norm[1, 1, 0] == 1.0
    # 50 HU should map to (50 - (-150)) / (250 - (-150)) = 200 / 400 = 0.5
    assert pytest.approx(norm[1, 0, 0], 1e-4) == 0.5


def test_inference_engine_unconfigured_safety():
    """
    CRITICAL MEDICAL SAFETY TEST:
    Verifies that LesionInferenceEngine raises an explicit error and stops safely
    when validated weights are not configured, rather than generating synthetic masks.
    """
    config = LesionModelConfig(model_path=None)
    engine = LesionInferenceEngine(config)

    assert not engine.is_configured

    with pytest.raises(RuntimeError, match="Validated lesion model weights are not configured"):
        engine.predict(np.zeros((10, 10, 10)), {})


def test_postprocessing_connected_components():
    """
    Tests postprocessing binarization and size-based noise removal.
    A small 5-voxel artifact must be discarded; a 100-voxel lesion cluster must be preserved.
    """
    probs = np.zeros((30, 30, 30), dtype=np.float32)

    # Component A: Large cluster (size 5 x 5 x 5 = 125 voxels) with p = 0.85
    probs[5:10, 5:10, 5:10] = 0.85

    # Component B: Small noise cluster (size 2 x 2 x 1 = 4 voxels) with p = 0.90
    probs[20:22, 20:22, 20] = 0.90

    # Low probability region (p = 0.30)
    probs[0:3, 0:3, 0:3] = 0.30

    cleaned = postprocess_lesion_mask(probs, threshold=0.5, min_volume_voxels=50)

    # Component A preserved
    assert np.all(cleaned[5:10, 5:10, 5:10] == 1)
    # Component B removed due to size < 50
    assert np.all(cleaned[20:22, 20:22, 20] == 0)
    # Low probability region removed due to threshold 0.5
    assert np.all(cleaned[0:3, 0:3, 0:3] == 0)
    assert np.sum(cleaned) == 125


def test_inverse_roi_mapping_to_original_space(synthetic_ct_and_mask, tmp_path: Path):
    """
    Tests embedding an ROI mask back into original patient space.
    Verifies exact coordinate recovery between cropped ROI and original array.
    """
    ct_path, mask_path, ct_data, mask_data, affine, spacing = synthetic_ct_and_mask

    # Extract ROI
    ct_roi, mask_roi, metadata, roi_affine, _ = extract_kidney_roi(ct_path, mask_path, physical_margin_mm=10.0)

    # In our synthetic fixture, the mask was placed at [20:35, 20:35, 15:30]
    # Simulate a lesion mask inside the ROI matching the original mask
    simulated_lesion_roi = mask_roi.copy()

    # Embed back into full original space
    full_mask = embed_roi_in_original_space(simulated_lesion_roi, metadata)

    assert full_mask.shape == ct_data.shape
    assert np.array_equal(full_mask, mask_data)

    # Save to NIfTI and verify header/affine matches original CT
    out_mask_path = tmp_path / "re_embedded_lesion.nii.gz"
    save_original_space_mask(full_mask, metadata, out_mask_path)

    saved_nii = nib.load(str(out_mask_path))
    assert saved_nii.shape == ct_data.shape
    assert np.allclose(saved_nii.affine, affine)


def test_create_lesion_metadata():
    """Tests structured lesion metadata creation and volume computation."""
    mask = np.zeros((20, 20, 20), dtype=np.uint8)
    # 10 x 10 x 10 = 1000 voxels
    mask[5:15, 5:15, 5:15] = 1
    spacing = (1.0, 1.0, 1.0)  # 1 mm³ per voxel -> 1000 mm³ = 1.0 cm³

    meta = create_lesion_metadata("kidney_tumor_left", "kidney_left", mask, spacing)

    assert meta["lesion_id"] == "kidney_tumor_left"
    assert meta["organ"] == "kidney_left"
    assert meta["voxel_count"] == 1000
    assert meta["volume_mm3"] == 1000.0
    assert meta["volume_cm3"] == 1.0
    assert meta["volume_ml"] == 1.0
    assert meta["centroid_voxel"] == [9.5, 9.5, 9.5]
    assert "disclaimer" in meta
