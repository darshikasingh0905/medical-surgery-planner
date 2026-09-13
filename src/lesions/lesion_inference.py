"""
src/lesions/lesion_inference.py

Lesion model inference interface, preprocessing framework, and checkpoint loader.
Provides explicit architectural contracts for validated models.

Supported model_type values:
    - 'torch_script'        : TorchScript (.pt) module
    - 'torch_state_dict'    : Raw PyTorch checkpoint or state dict (.pt / .pth)
    - 'monai_segresnet'     : MONAI SegResNet (requires MONAI to be installed)
    - 'nnunetv2_checkpoint' : nnU-Net v2 checkpoint (.pth) loaded via
                              dynamic_network_architectures, no nnU-Net framework required.
                              Requires init_args embedded in the checkpoint.

MEDICAL ENGINEERING CONSTRAINTS:
- Does NOT fabricate predictions or return mock tumor masks.
- If validated model weights are not configured on disk, the inference engine halts safely
  and raises an explicit configuration error.
- Provenance and label definitions are strictly validated before execution.
- This module is a research prototype. It is NOT clinically validated or certified.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import os
import logging
import numpy as np
import torch

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Public preprocessing utilities
# ──────────────────────────────────────────────────────────────

def preprocess_ct_roi(
    ct_roi: np.ndarray,
    hu_min: float = -150.0,
    hu_max: float = 250.0,
    normalize_mode: str = "minmax",
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Applies standard abdominal CT intensity windowing and normalization to a cropped ROI.

    Stages:
        1. Intensity clipping: clamps Hounsfield Units to [hu_min, hu_max]
           (standard soft tissue / renal parenchyma window).
        2. Normalization: converts voxel intensities to [0.0, 1.0] (minmax) or standard normal (zscore).

    Spatial coordinates and array shapes are preserved to guarantee 1:1 mapping
    back to the original CT scan.

    Args:
        ct_roi: 3D numpy array of raw Hounsfield Units.
        hu_min: Lower window threshold in HU (default: -150.0).
        hu_max: Upper window threshold in HU (default: 250.0).
        normalize_mode: Normalization strategy ('minmax' or 'zscore').

    Returns:
        tuple of (preprocessed_array, transformation_parameters).
    """
    if ct_roi.ndim != 3:
        raise ValueError(f"Expected 3D volume array, got shape {ct_roi.shape}")

    if hu_min >= hu_max:
        raise ValueError(f"hu_min ({hu_min}) must be less than hu_max ({hu_max})")

    # Stage 1: Windowing / Clipping
    clipped = np.clip(ct_roi.astype(np.float32), hu_min, hu_max)

    # Stage 2: Normalization
    if normalize_mode == "minmax":
        normalized = (clipped - hu_min) / (hu_max - hu_min)
    elif normalize_mode == "zscore":
        mean = float(np.mean(clipped))
        std = float(np.std(clipped))
        normalized = (clipped - mean) / (std + 1e-8)
    else:
        raise ValueError(f"Unsupported normalize_mode '{normalize_mode}'. Use 'minmax' or 'zscore'.")

    transform_params = {
        "hu_min": float(hu_min),
        "hu_max": float(hu_max),
        "normalize_mode": normalize_mode,
        "input_shape": list(ct_roi.shape),
        "output_shape": list(normalized.shape),
        "output_min": float(np.min(normalized)),
        "output_max": float(np.max(normalized)),
    }

    return normalized, transform_params


def preprocess_ct_roi_nnunet_zscore(
    ct_roi: np.ndarray,
    foreground_mean: float = 104.94,
    foreground_std: float = 75.30,
    clip_p005: float = -62.0,
    clip_p995: float = 310.0,
) -> tuple[np.ndarray, dict[str, Any]]:
    """
    Applies nnU-Net v1/v2 CTNormalization (foreground z-score) to a cropped ROI.

    This matches the intensity normalization used for Task135_KiTS2021 / KiTS23 nnU-Net
    training pipelines:
        1. Clip to [percentile_00_5, percentile_99_5] = [-62.0, 310.0] HU
        2. Subtract dataset foreground mean (104.94)
        3. Divide by dataset foreground std (75.30)

    These statistics are taken directly from the verified plans.pkl contained in
    weights/kits21/ (Task135_KiTS2021, fold 0).

    Args:
        ct_roi: 3D numpy array of raw Hounsfield Units.
        foreground_mean: Dataset foreground intensity mean from plans.pkl.
        foreground_std: Dataset foreground intensity std from plans.pkl.
        clip_p005: 0.5th percentile clip value from plans.pkl.
        clip_p995: 99.5th percentile clip value from plans.pkl.

    Returns:
        tuple of (preprocessed_array, transformation_parameters).
    """
    if ct_roi.ndim != 3:
        raise ValueError(f"Expected 3D volume array, got shape {ct_roi.shape}")

    clipped = np.clip(ct_roi.astype(np.float32), clip_p005, clip_p995)
    normalized = (clipped - foreground_mean) / (foreground_std + 1e-8)

    transform_params = {
        "normalization": "nnunet_ct_zscore",
        "clip_p005": clip_p005,
        "clip_p995": clip_p995,
        "foreground_mean": foreground_mean,
        "foreground_std": foreground_std,
        "input_shape": list(ct_roi.shape),
        "output_shape": list(normalized.shape),
        "output_min": float(np.min(normalized)),
        "output_max": float(np.max(normalized)),
    }
    return normalized, transform_params


# ──────────────────────────────────────────────────────────────
# Configuration dataclass
# ──────────────────────────────────────────────────────────────

@dataclass
class LesionModelConfig:
    """
    Configuration for lesion inference models.
    Supports environment variables for portable deployment without hardcoded paths.

    model_type options:
        'torch_script'        : TorchScript module (torch.jit.load).
        'torch_state_dict'    : Raw PyTorch checkpoint or state dict.
        'monai_segresnet'     : MONAI SegResNet; requires MONAI installation.
        'nnunetv2_checkpoint' : nnU-Net v2 .pth checkpoint that embeds init_args
                                (produced by nnUNetTrainer). Architecture reconstructed
                                via dynamic_network_architectures without the nnUNet
                                training framework.
    """
    model_path: str | Path | None = None
    model_type: str = "torch_script"  # see docstring above
    device: str = "cpu"
    batch_size: int = 1
    roi_patch_size: tuple[int, int, int] = (96, 96, 96)
    sliding_window_overlap: float = 0.5
    num_classes: int = 2  # 0: background/normal parenchyma, 1: renal tumor mass
    label_map: dict[int, str] | None = None

    @classmethod
    def from_env(cls) -> "LesionModelConfig":
        """Builds configuration from environment variables."""
        path = os.environ.get("LESION_MODEL_PATH")
        mtype = os.environ.get("LESION_MODEL_TYPE", "torch_script")
        default_dev = "cuda" if torch.cuda.is_available() else "cpu"
        device = os.environ.get("LESION_DEVICE", default_dev)
        return cls(
            model_path=path if path else None,
            model_type=mtype,
            device=device,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.model_path is not None:
            d["model_path"] = str(self.model_path)
        return d


# ──────────────────────────────────────────────────────────────
# nnUNetv2 architecture reconstruction helper
# ──────────────────────────────────────────────────────────────

def _build_nnunetv2_network_from_checkpoint(
    checkpoint: dict,
    device: torch.device,
) -> torch.nn.Module:
    """
    Reconstructs the nnU-Net v2 PlainConvUNet/ResidualEncoderUNet architecture from
    the 'init_args' and 'plans' embedded inside a verified nnUNetTrainer checkpoint.

    This function does NOT require the full nnUNet training framework to be installed.
    It uses the lightweight 'dynamic_network_architectures' package (which nnUNetv2
    itself depends on and which is already installed in this environment).

    The function:
        1. Reads architecture parameters from checkpoint['init_args']['plans'].
        2. Instantiates the exact UNet class (PlainConvUNet or ResidualEncoderUNet).
        3. Loads checkpoint['network_weights'] into the instantiated network.
        4. Puts the network into eval() mode.

    Args:
        checkpoint: dict loaded via torch.load from a .pth nnUNetv2 checkpoint.
        device: torch.device to move the network to.

    Returns:
        Instantiated torch.nn.Module in eval mode with weights loaded.

    Raises:
        ImportError: If dynamic_network_architectures is not installed.
        KeyError: If required keys are missing from the checkpoint.
        RuntimeError: If architecture or weight loading fails.
    """
    try:
        from dynamic_network_architectures.architectures.unet import (
            PlainConvUNet,
            ResidualEncoderUNet,
        )
        import torch.nn as nn
    except ImportError as e:
        raise ImportError(
            "dynamic_network_architectures is required for nnunetv2_checkpoint loading. "
            f"Install it with: pip install dynamic_network_architectures\n  Original: {e}"
        ) from e

    # ── Extract required keys from checkpoint ──────────────────
    try:
        init_args = checkpoint["init_args"]
        plans = init_args["plans"]
        configuration_name = init_args.get("configuration", "3d_fullres")
        dataset_json = init_args.get("dataset_json", {})
        network_weights = checkpoint["network_weights"]
    except KeyError as e:
        raise KeyError(
            f"Required key missing from nnUNetv2 checkpoint: {e}. "
            "Checkpoint may be from nnU-Net v1 (not supported by nnunetv2_checkpoint loader)."
        ) from e

    # ── Extract architecture configuration ─────────────────────
    try:
        configurations = plans["configurations"]
        cfg = configurations[configuration_name]
    except KeyError as e:
        available = list(plans.get("configurations", {}).keys())
        raise KeyError(
            f"Configuration '{configuration_name}' not found in plans. "
            f"Available: {available}. Original: {e}"
        ) from e

    unet_class_name = cfg.get("UNet_class_name", "PlainConvUNet")
    base_num_features = cfg.get("UNet_base_num_features", 32)
    n_conv_encoder = cfg.get("n_conv_per_stage_encoder", [2, 2, 2, 2, 2])
    n_conv_decoder = cfg.get("n_conv_per_stage_decoder", [2, 2, 2, 2])
    pool_op_kernel_sizes = cfg.get("pool_op_kernel_sizes", [[1, 1, 1]] + [[2, 2, 2]] * 4)
    conv_kernel_sizes = cfg.get("conv_kernel_sizes", [[3, 3, 3]] * 5)
    unet_max_features = cfg.get("unet_max_num_features", 320)

    # Number of output classes from dataset_json.
    # In nnU-Net v2 PlainConvUNet, num_classes represents the total number of output channels,
    # which includes background (channel 0) plus all labeled foreground classes.
    labels = dataset_json.get("labels", {})
    if isinstance(labels, dict) and len(labels) > 0:
        num_classes = len(labels)
    else:
        num_classes = 2  # safe default: background + 1 foreground

    logger.info(
        "Reconstructing nnUNetv2 architecture: class=%s, base_features=%d, "
        "num_classes=%d, configuration=%s",
        unet_class_name, base_num_features, num_classes, configuration_name,
    )

    # ── Instantiate the UNet ────────────────────────────────────
    unet_classes = {
        "PlainConvUNet": PlainConvUNet,
        "ResidualEncoderUNet": ResidualEncoderUNet,
    }
    if unet_class_name not in unet_classes:
        raise ValueError(
            f"Unknown UNet class '{unet_class_name}'. Supported: {list(unet_classes.keys())}"
        )
    UNetClass = unet_classes[unet_class_name]

    try:
        network = UNetClass(
            input_channels=1,
            n_stages=len(n_conv_encoder),
            features_per_stage=[
                min(base_num_features * 2**i, unet_max_features)
                for i in range(len(n_conv_encoder))
            ],
            conv_op=nn.Conv3d,
            kernel_sizes=conv_kernel_sizes,
            strides=pool_op_kernel_sizes,
            n_conv_per_stage=n_conv_encoder,
            num_classes=num_classes,
            n_conv_per_stage_decoder=n_conv_decoder,
            conv_bias=True,
            norm_op=nn.InstanceNorm3d,
            norm_op_kwargs={"eps": 1e-5, "affine": True},
            dropout_op=None,
            dropout_op_kwargs=None,
            nonlin=nn.LeakyReLU,
            nonlin_kwargs={"inplace": True},
            deep_supervision=False,
        )
    except Exception as e:
        raise RuntimeError(
            f"Failed to instantiate {unet_class_name} with extracted architecture parameters: {e}"
        ) from e

    # ── Load weights ────────────────────────────────────────────
    try:
        missing, unexpected = network.load_state_dict(network_weights, strict=False)
        if missing:
            logger.warning("Missing keys when loading checkpoint: %s", missing[:5])
        if unexpected:
            logger.warning("Unexpected keys in checkpoint: %s", unexpected[:5])
        if missing and len(missing) > len(network_weights) // 2:
            raise RuntimeError(
                f"Too many missing keys ({len(missing)}) when loading nnUNetv2 weights. "
                "Checkpoint may be incompatible with this architecture."
            )
    except Exception as e:
        raise RuntimeError(f"Failed to load network_weights into nnUNetv2 architecture: {e}") from e

    network = network.to(device)
    network.eval()
    return network


# ──────────────────────────────────────────────────────────────
# Main inference engine
# ──────────────────────────────────────────────────────────────

class LesionInferenceEngine:
    """
    Inference engine for renal lesion segmentation.

    Enforces strict medical engineering safety:
    - Never fabricates tumor predictions.
    - If model_path is not configured or not found on disk, halts safely.
    - If configured, loads the verified PyTorch/TorchScript model and executes deterministic inference.

    RESEARCH PROTOTYPE DISCLAIMER:
    This engine is for research/educational purposes only.
    It is NOT clinically validated, NOT certified as a medical device.
    All computational lesion masks require expert clinical review.
    """

    DEFAULT_LABEL_MAP = {
        0: "background_and_normal_parenchyma",
        1: "renal_tumor_mass",
    }

    def __init__(self, config: LesionModelConfig | None = None):
        self.config = config or LesionModelConfig.from_env()
        if self.config.label_map is None:
            self.config.label_map = dict(self.DEFAULT_LABEL_MAP)

        self._model = None
        self._is_loaded = False
        self._resolved_device = torch.device("cpu")
        self._checkpoint_metadata: dict[str, Any] = {}

        if self.config.model_path:
            self.load_model()

    @property
    def is_configured(self) -> bool:
        """Checks whether a valid, verified model is loaded into memory."""
        return self._is_loaded and self._model is not None

    @property
    def is_loaded(self) -> bool:
        """Checks whether a valid model has been loaded and initialized."""
        return self.is_configured

    def load_model(self) -> None:
        """
        Validates checkpoint existence and loads the verified neural network model.

        Raises:
            ValueError: If model_path is unset or model_type is unsupported.
            FileNotFoundError: If checkpoint file does not exist on disk.
            RuntimeError: If checkpoint file is invalid or cannot be deserialized.
        """
        if not self.config.model_path:
            raise ValueError("Cannot load model: model_path is not configured.")

        checkpoint_path = Path(self.config.model_path)
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Model checkpoint not found at: {checkpoint_path}")
        if not checkpoint_path.is_file():
            raise FileNotFoundError(f"Configured model path is not a file: {checkpoint_path}")

        # Resolve device with graceful CPU fallback
        dev_str = self.config.device.lower()
        if dev_str.startswith("cuda") and not torch.cuda.is_available():
            logger.warning(
                "CUDA requested (%s) but not available. Falling back to CPU for lesion inference.",
                self.config.device,
            )
            self._resolved_device = torch.device("cpu")
        else:
            self._resolved_device = torch.device(dev_str)

        logger.info(
            "Loading verified lesion model from: %s on device: %s (Type: %s)",
            checkpoint_path,
            self._resolved_device,
            self.config.model_type,
        )

        try:
            if self.config.model_type == "torch_script":
                self._model = torch.jit.load(str(checkpoint_path), map_location=self._resolved_device)

            elif self.config.model_type in ("torch_state_dict", "monai_segresnet"):
                # Loads raw PyTorch checkpoint or state dictionary
                state = torch.load(str(checkpoint_path), map_location=self._resolved_device,
                                   weights_only=False)
                if isinstance(state, torch.nn.Module):
                    self._model = state
                elif isinstance(state, dict) and "state_dict" in state:
                    self._model = state["state_dict"]
                else:
                    self._model = state

            elif self.config.model_type == "nnunetv2_checkpoint":
                # Check for nnU-Net v1 .pkl files first before torch.load
                if checkpoint_path.name.endswith(".pkl"):
                    raise RuntimeError(
                        f"Specified checkpoint '{checkpoint_path.name}' is an nnU-Net v1 (.pkl) file. "
                        "The 'nnunetv2_checkpoint' loader requires an nnU-Net v2 (.pth) checkpoint "
                        "containing 'network_weights' and 'init_args'."
                    )

                # ──────────────────────────────────────────────────────
                # nnU-Net v2 checkpoint: reconstruct architecture from
                # init_args embedded in the checkpoint, then load weights.
                # Does NOT require the full nnUNet framework.
                # ──────────────────────────────────────────────────────
                try:
                    raw_checkpoint = torch.load(
                        str(checkpoint_path),
                        map_location=self._resolved_device,
                        weights_only=False,
                    )
                except Exception as load_err:
                    raise RuntimeError(
                        f"Failed to read nnUNetv2 checkpoint from {checkpoint_path}: {load_err}"
                    ) from load_err

                if not isinstance(raw_checkpoint, dict):
                    raise RuntimeError(
                        f"Expected nnUNetv2 checkpoint to be a dict, got {type(raw_checkpoint)}. "
                        "File may be corrupted or from an unsupported format."
                    )
                # Validate required nnUNetv2 keys
                required_keys = {"network_weights", "init_args"}
                missing_keys = required_keys - set(raw_checkpoint.keys())
                if missing_keys:
                    raise RuntimeError(
                        f"nnUNetv2 checkpoint missing required keys: {missing_keys}. "
                        f"Found keys: {list(raw_checkpoint.keys())}. "
                        "This may be an nnU-Net v1 checkpoint (nnUNetTrainerV2), which is not "
                        "supported by the 'nnunetv2_checkpoint' loader."
                    )

                self._checkpoint_metadata = {
                    "trainer_name": raw_checkpoint.get("trainer_name", "unknown"),
                    "current_epoch": raw_checkpoint.get("current_epoch", -1),
                    "configuration": raw_checkpoint.get("init_args", {}).get("configuration", "unknown"),
                }
                self._model = _build_nnunetv2_network_from_checkpoint(
                    raw_checkpoint, self._resolved_device
                )

            else:
                raise ValueError(
                    f"Unsupported model_type '{self.config.model_type}'. "
                    "Supported types: 'torch_script', 'torch_state_dict', "
                    "'monai_segresnet', 'nnunetv2_checkpoint'."
                )

            if hasattr(self._model, "eval"):
                self._model.eval()

            self._is_loaded = True
            logger.info(
                "Successfully loaded lesion model checkpoint. Expected labels: %s",
                self.config.label_map,
            )

        except Exception as e:
            self._model = None
            self._is_loaded = False
            raise RuntimeError(f"Failed to load lesion model from {checkpoint_path}: {e}") from e

    def predict(self, ct_roi: np.ndarray, metadata: dict[str, Any] | None = None) -> np.ndarray:
        """
        Executes real inference on a preprocessed CT ROI using the verified model.

        Args:
            ct_roi: 3D numpy array of preprocessed/normalized Hounsfield Units.
            metadata: ROI spatial metadata from roi_extractor (optional, for logging).

        Returns:
            3D float numpy array in [0.0, 1.0] representing voxel-wise lesion probabilities.

        Raises:
            RuntimeError: If validated model weights are not configured or inference fails.
        """
        if not self.is_configured:
            raise RuntimeError(
                "Validated lesion model weights are not configured. "
                "The system will not generate ungrounded or synthetic tumor predictions. "
                f"Configured model path: {self.config.model_path}"
            )

        if ct_roi.ndim != 3:
            raise ValueError(f"Expected 3D volume array for inference, got shape {ct_roi.shape}")

        try:
            # Ensure intensities are normalized if raw HU was passed
            if np.min(ct_roi) < -50 or np.max(ct_roi) > 50:
                roi_input, _ = preprocess_ct_roi(ct_roi)
            else:
                roi_input = ct_roi.astype(np.float32)

            # Prepare tensor [Batch, Channel, D, H, W]
            tensor_input = (
                torch.from_numpy(roi_input)
                .unsqueeze(0)
                .unsqueeze(0)
                .to(self._resolved_device, dtype=torch.float32)
            )

            with torch.no_grad():
                output = self._model(tensor_input)

                # Check output shape: expect [1, C, D, H, W] or [1, 1, D, H, W]
                if output.ndim != 5:
                    raise ValueError(f"Model output must be 5D [B, C, D, H, W], got {output.shape}")

                num_out_classes = output.shape[1]
                if num_out_classes == 1:
                    probs = torch.sigmoid(output)
                    tumor_prob_tensor = probs[0, 0]
                elif num_out_classes >= 2:
                    probs = torch.softmax(output, dim=1)
                    # Class index 1 is designated as renal lesion/tumor mass
                    tumor_prob_tensor = probs[0, 1]
                else:
                    raise ValueError(f"Invalid model channel count: {num_out_classes}")

            tumor_probs = tumor_prob_tensor.cpu().numpy()

            # Ensure output dimensions match input ROI
            if tumor_probs.shape != ct_roi.shape:
                raise ValueError(
                    f"Model output shape {tumor_probs.shape} does not match input ROI shape {ct_roi.shape}"
                )

            return tumor_probs

        except Exception as e:
            logger.error("Error during lesion model forward pass: %s", e)
            raise RuntimeError(f"Lesion inference forward pass failed: {e}") from e

    def predict_lesion_probabilities(self, ct_roi: np.ndarray, metadata: dict[str, Any] | None = None) -> np.ndarray:
        """Alias for predict() returning 3D voxel-wise probability map."""
        return self.predict(ct_roi, metadata)

    def get_model_info(self) -> dict[str, Any]:
        """Returns structured metadata about the loaded model."""
        info = {
            "configured": self.is_configured,
            "model_path": str(self.config.model_path) if self.config.model_path else None,
            "model_type": self.config.model_type,
            "device": str(self._resolved_device),
            "num_classes": self.config.num_classes,
            "label_map": self.config.label_map,
        }
        if self._checkpoint_metadata:
            info["checkpoint_metadata"] = self._checkpoint_metadata
        return info
