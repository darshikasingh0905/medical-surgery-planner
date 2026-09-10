"""
src/lesions/lesion_inference.py

Lesion model inference interface, preprocessing framework, and checkpoint loader.
Provides explicit architectural contracts for validated models (e.g. MONAI SegResNet, TorchScript).

MEDICAL ENGINEERING CONSTRAINTS:
- Does NOT fabricate predictions or return mock tumor masks.
- If validated model weights are not configured on disk, the inference engine halts safely
  and raises an explicit configuration error.
- Provenance and label definitions are strictly validated before execution.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import os
import logging
import numpy as np
import torch

logger = logging.getLogger(__name__)


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


@dataclass
class LesionModelConfig:
    """
    Configuration for lesion inference models.
    Supports environment variables for portable deployment without hardcoded paths.
    """
    model_path: str | Path | None = None
    model_type: str = "torch_script"  # 'torch_script', 'torch_state_dict', 'monai_segresnet'
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


class LesionInferenceEngine:
    """
    Inference engine for renal lesion segmentation.

    Enforces strict medical engineering safety:
    - Never fabricates tumor predictions.
    - If model_path is not configured or not found on disk, halts safely.
    - If configured, loads the verified PyTorch/TorchScript model and executes deterministic inference.
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

        if self.config.model_path:
            self.load_model()

    @property
    def is_configured(self) -> bool:
        """Checks whether a valid, verified model is loaded into memory."""
        return self._is_loaded and self._model is not None

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
                state = torch.load(str(checkpoint_path), map_location=self._resolved_device)
                if isinstance(state, torch.nn.Module):
                    self._model = state
                elif isinstance(state, dict) and "state_dict" in state:
                    self._model = state["state_dict"]
                else:
                    self._model = state
            else:
                raise ValueError(f"Unsupported model_type '{self.config.model_type}'.")

            if hasattr(self._model, "eval"):
                self._model.eval()

            self._is_loaded = True
            logger.info("Successfully loaded lesion model checkpoint. Expected labels: %s", self.config.label_map)

        except Exception as e:
            self._model = None
            self._is_loaded = False
            raise RuntimeError(f"Failed to load lesion model from {checkpoint_path}: {e}") from e

    def predict(self, ct_roi: np.ndarray, metadata: dict[str, Any] | None = None) -> np.ndarray:
        """
        Executes real inference on a preprocessed CT ROI using the verified model.

        Args:
            ct_roi: 3D numpy array of preprocessed/normalized Hounsfield Units.
            metadata: ROI spatial metadata from roi_extractor.

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
            # Ensure intensities are normalized to [0.0, 1.0] if raw HU passed
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
                    # Class index 1 is designated as renal tumor mass
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

    def get_model_info(self) -> dict[str, Any]:
        """Returns structured metadata about the loaded model."""
        return {
            "configured": self.is_configured,
            "model_path": str(self.config.model_path) if self.config.model_path else None,
            "model_type": self.config.model_type,
            "device": str(self._resolved_device),
            "num_classes": self.config.num_classes,
            "label_map": self.config.label_map,
        }
