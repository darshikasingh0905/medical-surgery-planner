"""
tests/test_lesions.py

Unit tests for Days 9, 10 & 11: Renal Lesion Pipeline Foundation, Model Verification,
and KiTS21/KiTS23 nnU-Net checkpoint verification.
Verifies ROI extraction, physical margin calculations, boundary clamping,
intensity preprocessing, model abstraction error handling, checkpoint loading,
TorchScript model execution, connected-component postprocessing,
and original-space coordinate re-embedding.

NOTE: All test volumes use synthetic geometric test fixtures created solely
for deterministic software unit testing. None of these tests imply clinical validation.
"""

from pathlib import Path
import json
import pickle
import os
import pytest
import numpy as np
import nibabel as nib
import torch

from src.lesions.roi_extractor import extract_kidney_roi, save_roi_package
from src.lesions.lesion_inference import (
    preprocess_ct_roi,
    preprocess_ct_roi_nnunet_zscore,
    LesionModelConfig,
    LesionInferenceEngine,
    _build_nnunetv2_network_from_checkpoint,
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


def test_checkpoint_path_not_found(tmp_path: Path):
    """Verifies that an unresolvable model_path raises FileNotFoundError upon initialization."""
    non_existent = tmp_path / "non_existent_weights.pt"
    config = LesionModelConfig(model_path=non_existent)

    with pytest.raises(FileNotFoundError, match="Model checkpoint not found"):
        LesionInferenceEngine(config)


def test_invalid_checkpoint_loading_failure(tmp_path: Path):
    """Verifies that a corrupted or non-model file raises a clear RuntimeError."""
    corrupt_file = tmp_path / "corrupt_model.pt"
    corrupt_file.write_text("NOT A VALID PYTORCH MODEL")
    config = LesionModelConfig(model_path=corrupt_file, model_type="torch_script")

    with pytest.raises(RuntimeError, match="Failed to load lesion model"):
        LesionInferenceEngine(config)


def test_env_configuration(monkeypatch, tmp_path: Path):
    """Verifies that LesionModelConfig correctly reads environment variables."""
    fake_path = str(tmp_path / "weights.pt")
    monkeypatch.setenv("LESION_MODEL_PATH", fake_path)
    monkeypatch.setenv("LESION_MODEL_TYPE", "torch_script")
    monkeypatch.setenv("LESION_DEVICE", "cpu")

    config = LesionModelConfig.from_env()
    assert config.model_path == fake_path
    assert config.model_type == "torch_script"
    assert config.device == "cpu"


def test_torch_script_model_loading_and_execution(tmp_path: Path):
    """
    Creates a deterministic TorchScript unit test module in tmp_path,
    verifies loading, output shape, probability boundaries, and model info.
    """
    # Define a minimal 3D test module: outputs 2 classes [Background, Tumor]
    class Mock3DSegmenter(torch.nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # x is [1, 1, D, H, W]
            # Output logits [1, 2, D, H, W]
            bg = -x
            fg = x - 0.5
            return torch.cat([bg, fg], dim=1)

    model = Mock3DSegmenter()
    scripted = torch.jit.script(model)
    checkpoint_path = tmp_path / "test_module.pt"
    scripted.save(str(checkpoint_path))

    # Initialize engine
    config = LesionModelConfig(
        model_path=checkpoint_path,
        model_type="torch_script",
        device="cpu",
    )
    engine = LesionInferenceEngine(config)

    assert engine.is_configured

    info = engine.get_model_info()
    assert info["configured"] is True
    assert info["model_type"] == "torch_script"
    assert 1 in info["label_map"]

    # Test prediction on synthetic 3D ROI array
    ct_roi = np.random.uniform(-100, 150, size=(16, 16, 16)).astype(np.float32)
    probs = engine.predict(ct_roi)

    assert probs.shape == ct_roi.shape
    assert np.all(probs >= 0.0)
    assert np.all(probs <= 1.0)


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


# ─────────────────────────────────────────────────────────────────────────────
# Day 11 Tests: KiTS21 / KiTS23 Checkpoint Verification & nnUNet Architecture
# ─────────────────────────────────────────────────────────────────────────────

def test_preprocess_ct_roi_nnunet_zscore():
    """Verifies nnU-Net foreground z-score normalization on CT ROI."""
    # Test volume with values outside and inside the clip range [-62.0, 310.0]
    data = np.array([
        [[-200.0, -62.0], [0.0, 104.94]],
        [[200.0, 310.0], [500.0, 104.94]],
    ], dtype=np.float32)

    norm, params = preprocess_ct_roi_nnunet_zscore(
        data,
        foreground_mean=104.94,
        foreground_std=75.30,
        clip_p005=-62.0,
        clip_p995=310.0,
    )

    assert norm.shape == (2, 2, 2)
    assert norm.dtype == np.float32
    assert params["normalization"] == "nnunet_ct_zscore"
    assert params["foreground_mean"] == 104.94
    assert params["foreground_std"] == 75.30

    # Values at mean should normalize to approximately 0.0
    # data[0, 1, 1] is 104.94 -> (104.94 - 104.94) / 75.30 = 0.0
    assert abs(norm[0, 1, 1]) < 1e-4

    # Clipped minimum: -200 is clipped to -62.0
    expected_min = (-62.0 - 104.94) / 75.30
    assert abs(norm[0, 0, 0] - expected_min) < 1e-4

    # Clipped maximum: 500 is clipped to 310.0
    expected_max = (310.0 - 104.94) / 75.30
    assert abs(norm[1, 1, 0] - expected_max) < 1e-4


def test_preprocess_ct_roi_nnunet_zscore_invalid_dimensions():
    """Verifies ValueError when input ROI is not 3D."""
    with pytest.raises(ValueError, match="Expected 3D volume array"):
        preprocess_ct_roi_nnunet_zscore(np.zeros((64, 64), dtype=np.float32))


def test_kits21_plans_pkl_inspection():
    """
    Verifies that weights/kits21/plans.pkl is loadable and contains the
    verified KiTS21 dataset intensity properties and class definitions.
    """
    plans_path = Path("weights/kits21/plans.pkl")
    if not plans_path.exists():
        pytest.skip("weights/kits21/plans.pkl not present on disk")

    with open(plans_path, "rb") as f:
        plans = pickle.load(f)

    assert isinstance(plans, dict)
    assert "dataset_properties" in plans
    props = plans["dataset_properties"]

    # Check intensity properties contain foreground statistics
    assert "intensityproperties" in props
    intensity = props["intensityproperties"][0]
    assert "mean" in intensity
    assert "sd" in intensity
    assert "percentile_00_5" in intensity
    assert "percentile_99_5" in intensity

    # Validate against known KiTS21 foreground values
    assert abs(float(intensity["mean"]) - 104.94) < 1.0
    assert abs(float(intensity["sd"]) - 75.30) < 1.0
    assert abs(float(intensity["percentile_00_5"]) - (-62.0)) < 1.0
    assert abs(float(intensity["percentile_99_5"]) - 310.0) < 1.0

    # Validate classes: 1: kidney, 2: tumor, 3: cyst
    assert plans.get("all_classes") == [1, 2, 3]


def test_kits21_v1_checkpoint_incompatibility_detection(tmp_path):
    """
    Verifies that attempting to load an nnU-Net v1 checkpoint file
    (such as model_final_checkpoint.model.pkl) with model_type='nnunetv2_checkpoint'
    raises an explicit error detailing missing nnUNetv2 keys and v1 incompatibility.
    """
    ckpt_path = Path("weights/kits21/model_final_checkpoint.model.pkl")
    if not ckpt_path.exists():
        pytest.skip("weights/kits21/model_final_checkpoint.model.pkl not present on disk")

    config = LesionModelConfig(
        model_path=ckpt_path,
        model_type="nnunetv2_checkpoint",
    )
    # Must fail safely and explicitly because this is a v1 checkpoint
    with pytest.raises(RuntimeError, match="nnUNetv2 checkpoint missing required keys|nnU-Net v1"):
        LesionInferenceEngine(config)


def test_nnunetv2_checkpoint_missing_keys(tmp_path):
    """Verifies that an incomplete nnUNetv2 checkpoint is rejected safely."""
    bad_ckpt_path = tmp_path / "bad_nnunet.pth"
    # Only save init_args without network_weights
    torch.save({"init_args": {}}, bad_ckpt_path)

    config = LesionModelConfig(
        model_path=bad_ckpt_path,
        model_type="nnunetv2_checkpoint",
    )
    with pytest.raises(RuntimeError, match="missing required keys"):
        LesionInferenceEngine(config)


def test_nnunetv2_checkpoint_non_dict_corrupted(tmp_path):
    """Verifies that a corrupted or non-dict checkpoint file raises RuntimeError."""
    corrupted_path = tmp_path / "corrupted.pth"
    torch.save([1, 2, 3], corrupted_path)  # list instead of dict

    config = LesionModelConfig(
        model_path=corrupted_path,
        model_type="nnunetv2_checkpoint",
    )
    with pytest.raises(RuntimeError, match="Expected nnUNetv2 checkpoint to be a dict"):
        LesionInferenceEngine(config)


def test_build_nnunetv2_network_from_synthetic_checkpoint():
    """
    Verifies that _build_nnunetv2_network_from_checkpoint correctly instantiates
    a PlainConvUNet using dynamic_network_architectures and loads weights.
    """
    from dynamic_network_architectures.architectures.unet import PlainConvUNet
    import torch.nn as nn

    # Build minimal PlainConvUNet for testing
    encoder_stages = [1, 1]
    decoder_stages = [1]
    kernel_sizes = [[3, 3, 3], [3, 3, 3]]
    strides = [[1, 1, 1], [2, 2, 2]]

    ref_model = PlainConvUNet(
        input_channels=1,
        n_stages=2,
        features_per_stage=[8, 16],
        conv_op=nn.Conv3d,
        kernel_sizes=kernel_sizes,
        strides=strides,
        n_conv_per_stage=encoder_stages,
        num_classes=2,
        n_conv_per_stage_decoder=decoder_stages,
        conv_bias=True,
        norm_op=nn.InstanceNorm3d,
        norm_op_kwargs={"eps": 1e-5, "affine": True},
        dropout_op=None,
        dropout_op_kwargs=None,
        nonlin=nn.LeakyReLU,
        nonlin_kwargs={"inplace": True},
        deep_supervision=False,
    )

    synthetic_checkpoint = {
        "network_weights": ref_model.state_dict(),
        "init_args": {
            "configuration": "3d_fullres",
            "plans": {
                "configurations": {
                    "3d_fullres": {
                        "UNet_class_name": "PlainConvUNet",
                        "UNet_base_num_features": 8,
                        "n_conv_per_stage_encoder": encoder_stages,
                        "n_conv_per_stage_decoder": decoder_stages,
                        "pool_op_kernel_sizes": strides,
                        "conv_kernel_sizes": kernel_sizes,
                        "unet_max_num_features": 32,
                    }
                }
            },
            "dataset_json": {
                "labels": {"background": 0, "kidney_tumor": 1}
            },
        },
        "trainer_name": "nnUNetTrainer_KiTS23",
        "current_epoch": 100,
    }

    device = torch.device("cpu")
    built_network = _build_nnunetv2_network_from_checkpoint(synthetic_checkpoint, device)

    assert built_network is not None
    assert isinstance(built_network, PlainConvUNet)
    assert not built_network.training  # must be in eval() mode

    # Test forward pass with a small input volume
    test_input = torch.zeros((1, 1, 16, 16, 16), dtype=torch.float32)
    with torch.no_grad():
        out = built_network(test_input)

    assert out.shape == (1, 2, 16, 16, 16)


def test_nnunetv2_checkpoint_inference_engine_execution(tmp_path):
    """
    Verifies full LesionInferenceEngine loading and prediction workflow
    with an nnunetv2_checkpoint configuration.
    """
    from dynamic_network_architectures.architectures.unet import PlainConvUNet
    import torch.nn as nn

    encoder_stages = [1, 1]
    decoder_stages = [1]
    kernel_sizes = [[3, 3, 3], [3, 3, 3]]
    strides = [[1, 1, 1], [2, 2, 2]]

    model = PlainConvUNet(
        input_channels=1,
        n_stages=2,
        features_per_stage=[8, 16],
        conv_op=nn.Conv3d,
        kernel_sizes=kernel_sizes,
        strides=strides,
        n_conv_per_stage=encoder_stages,
        num_classes=2,
        n_conv_per_stage_decoder=decoder_stages,
        conv_bias=True,
        norm_op=nn.InstanceNorm3d,
        norm_op_kwargs={"eps": 1e-5, "affine": True},
        dropout_op=None,
        dropout_op_kwargs=None,
        nonlin=nn.LeakyReLU,
        nonlin_kwargs={"inplace": True},
        deep_supervision=False,
    )

    ckpt_path = tmp_path / "valid_nnunetv2.pth"
    torch.save({
        "network_weights": model.state_dict(),
        "init_args": {
            "configuration": "3d_fullres",
            "plans": {
                "configurations": {
                    "3d_fullres": {
                        "UNet_class_name": "PlainConvUNet",
                        "UNet_base_num_features": 8,
                        "n_conv_per_stage_encoder": encoder_stages,
                        "n_conv_per_stage_decoder": decoder_stages,
                        "pool_op_kernel_sizes": strides,
                        "conv_kernel_sizes": kernel_sizes,
                        "unet_max_num_features": 32,
                    }
                }
            },
            "dataset_json": {
                "labels": {"background": 0, "kidney_tumor": 1}
            },
        },
        "trainer_name": "nnUNetTrainer_KiTS23",
        "current_epoch": 250,
    }, ckpt_path)

    config = LesionModelConfig(
        model_path=ckpt_path,
        model_type="nnunetv2_checkpoint",
        num_classes=2,
    )

    engine = LesionInferenceEngine(config)
    assert engine.is_loaded
    assert engine.is_configured

    info = engine.get_model_info()
    assert info["configured"] is True
    assert info["model_type"] == "nnunetv2_checkpoint"
    assert info["checkpoint_metadata"]["trainer_name"] == "nnUNetTrainer_KiTS23"
    assert info["checkpoint_metadata"]["current_epoch"] == 250

    # Perform inference on an ROI volume (dimensions must be divisible by stride=2)
    ct_roi = np.zeros((16, 16, 16), dtype=np.float32)
    prob_map = engine.predict_lesion_probabilities(ct_roi)

    assert prob_map.shape == (16, 16, 16)
    assert prob_map.dtype == np.float32
    assert float(np.min(prob_map)) >= 0.0
    assert float(np.max(prob_map)) <= 1.0


def test_unsupported_model_type_rejection(tmp_path):
    """Verifies that an unknown model_type raises an explicit ValueError."""
    dummy_file = tmp_path / "model.bin"
    dummy_file.write_bytes(b"dummy")

    config = LesionModelConfig(
        model_path=dummy_file,
        model_type="unsupported_architecture_xyz",
    )
    with pytest.raises(RuntimeError, match="Unsupported model_type 'unsupported_architecture_xyz'"):
        LesionInferenceEngine(config)


def test_real_kits_checkpoint_inference():
    """
    Day 11 Real Checkpoint & Real Inference Verification Test.

    Explicitly verifies that a genuine, complete, uncorrupted trained KiTS checkpoint
    can be loaded and executed for real lesion inference.

    SAFETY & COMPLIANCE GUARANTEES:
    - SKIPS cleanly when a real trained checkpoint is unavailable or incomplete on disk.
    - NEVER substitutes synthetic, randomized, or mock weights.
    - FAILS clearly if a real checkpoint is configured but fails to load or execute.
    - Validates output dimensions, classes, and probability ranges strictly.
    """
    configured_path = os.environ.get("REAL_KITS_CHECKPOINT_PATH")

    candidate_paths = [
        Path("weights/kits21/model_final_checkpoint.model"),
        Path("weights/kits21/model_final_checkpoint.pth"),
        Path("weights/kits23/checkpoint_final.pth"),
    ]
    if configured_path:
        candidate_paths.insert(0, Path(configured_path))

    real_ckpt = None
    for p in candidate_paths:
        if p.exists() and p.is_file() and p.suffix != ".tmp":
            if not p.name.endswith(".pkl"):
                real_ckpt = p
                break

    if real_ckpt is None:
        tmp_file = Path("weights/kits21/model_final_checkpoint.tmp")
        if tmp_file.exists():
            pytest.skip(
                f"Real KiTS checkpoint is incomplete on disk ({tmp_file} is a truncated/interrupted download). "
                "REAL MODEL INFERENCE IS BLOCKED until a verified uncorrupted checkpoint is mounted."
            )
        pytest.skip(
            "No verified real KiTS checkpoint file found in weights/. "
            "REAL MODEL INFERENCE IS BLOCKED pending verified trained checkpoint."
        )

    # A candidate real checkpoint was found; load strictly with no synthetic substitution
    config = LesionModelConfig(
        model_path=real_ckpt,
        model_type=os.environ.get("LESION_MODEL_TYPE", "nnunetv2_checkpoint"),
    )
    engine = LesionInferenceEngine(config)
    assert engine.is_loaded, f"Failed to load real checkpoint: {real_ckpt}"
    assert engine.is_configured

    info = engine.get_model_info()
    assert info["configured"] is True

    test_roi = np.zeros((32, 32, 32), dtype=np.float32)
    prob_map = engine.predict_lesion_probabilities(test_roi)
    assert prob_map.shape == (32, 32, 32)
    assert prob_map.dtype == np.float32
    assert float(np.min(prob_map)) >= 0.0
    assert float(np.max(prob_map)) <= 1.0


def test_kits23_checkpoint_loading_and_metadata():
    """
    Verifies that the KiTS23 3D fullres checkpoint loads successfully,
    reconstructs 4-class architecture, and extracts dataset labels.
    """
    ckpt_path = Path("weights/kits23/checkpoint_final.pth")
    if not ckpt_path.exists():
        pytest.skip("weights/kits23/checkpoint_final.pth not found on disk.")

    config = LesionModelConfig(
        model_path=ckpt_path,
        model_type="nnunetv2_checkpoint",
        device="cpu",
    )
    engine = LesionInferenceEngine(config)
    assert engine.is_loaded
    assert engine.is_configured

    info = engine.get_model_info()
    assert info["configured"] is True
    assert info["num_classes"] == 4
    assert info["label_map"] == {
        0: "background",
        1: "kidney",
        2: "tumor",
        3: "cyst",
    }
    meta = info["checkpoint_metadata"]
    assert meta["trainer_name"] == "nnUNetTrainer"
    assert meta["current_epoch"] == 1001
    assert meta["configuration"] == "3d_fullres"


def test_kits23_multiclass_inference_probabilities():
    """
    Verifies multiclass probabilities and argmax class predictions using
    the KiTS23 checkpoint.
    """
    ckpt_path = Path("weights/kits23/checkpoint_final.pth")
    if not ckpt_path.exists():
        pytest.skip("weights/kits23/checkpoint_final.pth not found on disk.")

    config = LesionModelConfig(
        model_path=ckpt_path,
        model_type="nnunetv2_checkpoint",
        device="cpu",
    )
    engine = LesionInferenceEngine(config)

    # Test patch with arbitrary dimensions (auto-padding will handle)
    test_roi = np.zeros((35, 42, 50), dtype=np.float32)
    probs = engine.predict_all_probabilities(test_roi)

    assert probs.shape == (4, 35, 42, 50)
    assert probs.dtype == np.float32
    assert float(np.min(probs)) >= 0.0
    assert float(np.max(probs)) <= 1.0

    # Probabilities should sum to 1.0 at every voxel
    prob_sum = np.sum(probs, axis=0)
    np.testing.assert_allclose(prob_sum, 1.0, atol=1e-5)

    classes = engine.predict_classes(test_roi)
    assert classes.shape == (35, 42, 50)
    assert classes.dtype == np.uint8


def test_lesion_physical_volume_and_mesh_reconstruction(tmp_path):
    """
    Verifies lesion mask postprocessing, physical volume computation,
    and 3D Marching Cubes mesh reconstruction with physical voxel spacing.
    """
    from src.mesh.mesh_generator import generate_mesh_from_mask, save_mesh_as_obj

    # Create synthetic sphere lesion mask
    mask = np.zeros((40, 40, 40), dtype=np.uint8)
    z, y, x = np.ogrid[:40, :40, :40]
    sphere = ((x - 20) ** 2 + (y - 20) ** 2 + (z - 20) ** 2) <= 10 ** 2
    mask[sphere] = 1

    voxel_count = int(np.sum(mask))
    assert voxel_count > 0

    spacing = (1.5, 1.5, 1.5)
    voxel_vol_ml = (spacing[0] * spacing[1] * spacing[2]) / 1000.0
    physical_vol_ml = voxel_count * voxel_vol_ml

    # Theoretical volume of sphere radius 10 voxels = 4/3 * pi * 10^3 = ~4188.79 voxels
    # Physical volume = 4188.79 * 3.375 / 1000 = ~14.13 mL
    assert 13.0 < physical_vol_ml < 15.5

    verts, faces = generate_mesh_from_mask(mask, spacing)
    assert len(verts) > 0
    assert len(faces) > 0

    # Check physical coordinates span ~ [10*1.5, 30*1.5] = [15.0, 45.0] mm
    min_pt = verts.min(axis=0)
    max_pt = verts.max(axis=0)
    extent = max_pt - min_pt
    np.testing.assert_allclose(extent, 30.0, atol=2.0)

    obj_path = tmp_path / "test_lesion.obj"
    save_mesh_as_obj(obj_path, verts, faces)
    assert obj_path.exists()
    assert obj_path.stat().st_size > 0

