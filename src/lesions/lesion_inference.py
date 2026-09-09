"""
src/lesions/lesion_inference.py

Lesion model inference interface and preprocessing framework.
Provides explicit architectural contracts for future validated models (e.g. MONAI SegResNet/DynUNet).

MEDICAL ENGINEERING CONSTRAINT:
Does NOT fabricate predictions or return mock tumor masks.
If validated model weights are not configured, the inference engine halts safely
and raises an explicit configuration error.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import numpy as np


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
    """Configuration for lesion inference models."""
    model_path: str | Path | None = None
    model_type: str = "monai_segresnet"
    device: str = "cpu"
    batch_size: int = 1
    roi_patch_size: tuple[int, int, int] = (96, 96, 96)
    sliding_window_overlap: float = 0.5
    num_classes: int = 2  # 0: background/parenchyma, 1: lesion

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.model_path is not None:
            d["model_path"] = str(self.model_path)
        return d


class LesionInferenceEngine:
    """
    Abstract inference runner for lesion segmentation.

    Enforces strict medical engineering safety:
    If verified model weights are not configured on the filesystem,
    the engine raises a RuntimeError and halts safely without fabricating predictions.
    """

    def __init__(self, config: LesionModelConfig | None = None):
        self.config = config or LesionModelConfig()
        self._model = None

    @property
    def is_configured(self) -> bool:
        """Checks whether a valid model weights file is present."""
        if not self.config.model_path:
            return False
        p = Path(self.config.model_path)
        return p.exists() and p.is_file()

    def predict(self, ct_roi: np.ndarray, metadata: dict[str, Any]) -> np.ndarray:
        """
        Executes inference on a preprocessed CT ROI.

        Raises:
            RuntimeError: If validated model weights are not configured.
                          Never returns a fabricated or mock tumor mask.
        """
        if not self.is_configured:
            raise RuntimeError(
                "Validated lesion model weights are not configured. "
                "The system will not generate ungrounded or synthetic tumor predictions. "
                f"Configured model path: {self.config.model_path}"
            )

        # Future integration point for loaded PyTorch/MONAI model:
        # with torch.no_grad():
        #     logits = self._model(tensor_roi)
        #     probs = torch.softmax(logits, dim=1)
        # return probs.cpu().numpy()
        raise NotImplementedError("Model execution backend pending verified checkpoint integration.")
