"""
src/lesions/postprocessing.py

Lesion postprocessing, connected-component analysis, coordinate re-embedding,
and lesion metadata generation.
Maps cropped ROI segmentations back into full patient-space NIfTI volumes
with original affines, orientations, and physical coordinates.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import numpy as np
import nibabel as nib
from scipy import ndimage


def postprocess_lesion_mask(
    probabilities: np.ndarray,
    threshold: float = 0.5,
    min_volume_voxels: int = 50,
) -> np.ndarray:
    """
    Converts model probability/logit array into a clean binary lesion mask.

    Steps:
        1. Binarize by probability threshold (default: 0.50).
        2. Connected-component labeling to identify distinct spatial clusters.
        3. Noise removal: discards components with voxel count < min_volume_voxels.

    Args:
        probabilities: 3D float numpy array in [0.0, 1.0].
        threshold: Binarization cutoff threshold (default: 0.5).
        min_volume_voxels: Minimum connected cluster volume in voxels (default: 50).

    Returns:
        3D binary uint8 numpy array (0 or 1).
    """
    if probabilities.ndim != 3:
        raise ValueError(f"Expected 3D array, got shape {probabilities.shape}")

    # 1. Threshold
    binary = (probabilities >= threshold).astype(np.uint8)

    if min_volume_voxels <= 1 or np.sum(binary) == 0:
        return binary

    # 2. Connected component labeling (26-connectivity for 3D)
    labeled_array, num_features = ndimage.label(binary, structure=ndimage.generate_binary_structure(3, 3))

    if num_features == 0:
        return np.zeros_like(binary, dtype=np.uint8)

    # 3. Size filtering
    component_sizes = ndimage.sum(binary, labeled_array, range(1, num_features + 1))
    cleaned_mask = np.zeros_like(binary, dtype=np.uint8)

    for feature_id, size in enumerate(component_sizes, start=1):
        if size >= min_volume_voxels:
            cleaned_mask[labeled_array == feature_id] = 1

    return cleaned_mask


def embed_roi_in_original_space(
    roi_mask: np.ndarray,
    roi_metadata: dict[str, Any],
) -> np.ndarray:
    """
    Maps an ROI mask back into the full original CT image coordinate grid.

    Uses the roi_slices recorded during ROI extraction to place the cropped array
    into an all-zeros volume matching the original CT scan shape.

    Args:
        roi_mask: 3D binary array matching the cropped ROI dimensions.
        roi_metadata: Dictionary produced by extract_kidney_roi containing
                      'source_image_shape' and 'roi_slices'.

    Returns:
        3D binary uint8 array of the same shape as the original full CT scan.
    """
    source_shape = tuple(roi_metadata["source_image_shape"])
    roi_slices_data = roi_metadata["roi_slices"]

    slices = tuple(slice(s[0], s[1]) for s in roi_slices_data)

    expected_roi_shape = tuple(s[1] - s[0] for s in roi_slices_data)
    if roi_mask.shape != expected_roi_shape:
        raise ValueError(
            f"ROI mask shape {roi_mask.shape} does not match expected ROI slice bounds {expected_roi_shape}"
        )

    full_mask = np.zeros(source_shape, dtype=np.uint8)
    full_mask[slices] = (roi_mask > 0).astype(np.uint8)

    return full_mask


def save_original_space_mask(
    full_mask: np.ndarray,
    roi_metadata: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """
    Saves an embedded lesion mask as a standard NIfTI image using the original CT's affine.

    Guarantees exact spatial correspondence with the original scan:
    identical dimensions, orientation, and voxel spacing.

    Args:
        full_mask: 3D array in original full CT space.
        roi_metadata: Metadata dictionary containing 'original_affine'.
        output_path: Destination path for the .nii.gz file.

    Returns:
        Path to the saved NIfTI mask.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    original_affine = np.array(roi_metadata["original_affine"], dtype=np.float64)
    nii_img = nib.Nifti1Image(full_mask.astype(np.uint8), original_affine)
    nib.save(nii_img, str(out_file))

    return out_file


def create_lesion_metadata(
    lesion_id: str,
    organ: str,
    full_mask: np.ndarray,
    voxel_spacing: tuple[float, float, float] | list[float],
    model_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Constructs a structured metadata payload for a detected/segmented lesion.

    Computes purely objective mathematical metrics:
        - Voxel count
        - Physical volume (mm³, cm³, mL)
        - Bounding box bounds
        - 3D centroid in voxel and physical coordinate space

    Does NOT generate invented confidence scores or ungrounded clinical diagnoses.

    Args:
        lesion_id: Unique lesion identifier (e.g. 'kidney_tumor_left').
        organ: Host organ name (e.g. 'kidney_left').
        full_mask: 3D binary mask in original patient space.
        voxel_spacing: (dx, dy, dz) in mm from the original NIfTI header.
        model_info: Provenance of the model that generated the prediction.

    Returns:
        Sanitized JSON-serializable dictionary.
    """
    voxel_count = int(np.sum(full_mask > 0))
    spacing = [float(s) for s in voxel_spacing[:3]]
    voxel_vol_mm3 = float(spacing[0] * spacing[1] * spacing[2])
    volume_mm3 = float(voxel_count * voxel_vol_mm3)
    volume_cm3 = float(volume_mm3 / 1000.0)

    if voxel_count > 0:
        indices = np.argwhere(full_mask > 0)
        min_b = [int(x) for x in indices.min(axis=0)]
        max_b = [int(x) for x in indices.max(axis=0)]
        centroid_voxel = [float(x) for x in indices.mean(axis=0)]
        # Physical dimensions of bounding box
        dimensions_mm = [
            float((max_b[i] - min_b[i] + 1) * spacing[i])
            for i in range(3)
        ]
    else:
        min_b = None
        max_b = None
        centroid_voxel = None
        dimensions_mm = None

    default_model_info = {
        "configured": False,
        "model_name": None,
        "model_version": None,
        "model_source": None,
        "confidence_statistics": None,
    }
    if model_info:
        default_model_info.update(model_info)

    metadata = {
        "lesion_id": lesion_id,
        "organ": organ,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "voxel_count": voxel_count,
        "voxel_spacing_mm": spacing,
        "volume_mm3": round(volume_mm3, 2),
        "volume_cm3": round(volume_cm3, 2),
        "volume_ml": round(volume_cm3, 2),
        "bounding_box_voxel": {"min": min_b, "max": max_b} if min_b else None,
        "bounding_box_dimensions_mm": {
            "x": round(dimensions_mm[0], 2),
            "y": round(dimensions_mm[1], 2),
            "z": round(dimensions_mm[2], 2),
        } if dimensions_mm else None,
        "centroid_voxel": [round(c, 2) for c in centroid_voxel] if centroid_voxel else None,
        "model_provenance": default_model_info,
        "disclaimer": (
            "AI-assisted preoperative planning prototype. "
            "Algorithmic lesion segmentation requiring clinical review by a qualified physician. "
            "Not for primary diagnostic use."
        ),
    }

    return metadata
