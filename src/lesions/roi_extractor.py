"""
src/lesions/roi_extractor.py

Kidney Region of Interest (ROI) extraction engine.
Crops abdominal CT scans using TotalSegmentator kidney segmentations as anatomical priors.
Applies physical margin expansion in true millimeters (accounting for anisotropic voxel spacing)
and maintains full spatial transformation metadata for coordinate mapping.
"""

from pathlib import Path
import json
import numpy as np
import nibabel as nib


def extract_kidney_roi(
    ct_path: str | Path,
    mask_path: str | Path,
    physical_margin_mm: float = 20.0,
) -> tuple[np.ndarray, np.ndarray, dict, np.ndarray, nib.Nifti1Header]:
    """
    Extracts an expanded physical bounding box ROI around a kidney mask from a CT scan.

    Args:
        ct_path: Path to the input CT NIfTI scan.
        mask_path: Path to the kidney segmentation mask NIfTI.
        physical_margin_mm: Margin in millimeters to expand the bounding box (default: 20.0 mm).

    Returns:
        tuple containing:
            - ct_roi: 3D numpy array of cropped CT intensities.
            - mask_roi: 3D numpy array of cropped kidney mask voxels.
            - roi_metadata: Dictionary with complete geometric and coordinate mapping data.
            - roi_affine: 4x4 affine matrix of the cropped ROI.
            - ct_header: Original CT NIfTI header.

    Raises:
        FileNotFoundError: If CT or mask file does not exist.
        ValueError: If CT and mask shapes differ, or if the mask contains no foreground voxels.
    """
    ct_file = Path(ct_path)
    mask_file = Path(mask_path)

    if not ct_file.exists():
        raise FileNotFoundError(f"CT file not found: {ct_file}")
    if not mask_file.exists():
        raise FileNotFoundError(f"Mask file not found: {mask_file}")

    ct_img = nib.load(str(ct_file))
    mask_img = nib.load(str(mask_file))

    ct_data = ct_img.get_fdata(dtype=np.float32)
    mask_data = mask_img.get_fdata(dtype=np.float32)

    if ct_data.shape != mask_data.shape:
        raise ValueError(
            f"Shape mismatch: CT scan {ct_data.shape} vs Mask {mask_data.shape}"
        )

    # Extract voxel spacing (zooms) from NIfTI header in mm: (dx, dy, dz)
    spacing = tuple(float(s) for s in ct_img.header.get_zooms()[:3])

    # Find non-zero mask voxels
    fg_indices = np.argwhere(mask_data > 0)
    if len(fg_indices) == 0:
        raise ValueError(f"Mask contains no foreground voxels: {mask_file}")

    min_coords = fg_indices.min(axis=0)  # [x_min, y_min, z_min]
    max_coords = fg_indices.max(axis=0)  # [x_max, y_max, z_max] inclusive

    # Convert physical margin (mm) to voxel padding per axis
    # pad_voxels = ceil(margin_mm / voxel_spacing)
    pad_voxels = [
        int(np.ceil(physical_margin_mm / s)) if s > 0 else 0
        for s in spacing
    ]

    # Expand bounding box and clamp strictly to image boundaries [0, dim - 1]
    roi_bounds = []
    roi_slices = []
    for i in range(3):
        dim_size = ct_data.shape[i]
        b_min = max(0, int(min_coords[i]) - pad_voxels[i])
        b_max = min(dim_size - 1, int(max_coords[i]) + pad_voxels[i])
        roi_bounds.append([b_min, b_max])
        # Python slice is end-exclusive
        roi_slices.append([b_min, b_max + 1])

    slices = tuple(slice(s[0], s[1]) for s in roi_slices)

    # Crop arrays
    ct_roi = ct_data[slices].copy()
    mask_roi = mask_data[slices].copy()

    # Compute the new affine matrix for the cropped ROI
    # Coordinate (0, 0, 0) in ROI space corresponds to (b_min[0], b_min[1], b_min[2]) in source space
    origin_offset = np.array([roi_slices[0][0], roi_slices[1][0], roi_slices[2][0], 1.0])
    roi_affine = ct_img.affine.copy()
    roi_affine[:, 3] = ct_img.affine @ origin_offset

    roi_metadata = {
        "source_mask_name": mask_file.name,
        "source_image_shape": list(ct_data.shape),
        "source_voxel_spacing": list(spacing),
        "original_affine": ct_img.affine.tolist(),
        "roi_affine": roi_affine.tolist(),
        "roi_voxel_bounds": roi_bounds,
        "roi_slices": roi_slices,
        "roi_shape": list(ct_roi.shape),
        "physical_margin_mm": float(physical_margin_mm),
        "voxel_padding": pad_voxels,
        "mask_foreground_voxels": int(len(fg_indices)),
        "mask_bounding_box_unpadded": [
            [int(min_coords[i]), int(max_coords[i])] for i in range(3)
        ],
    }

    return ct_roi, mask_roi, roi_metadata, roi_affine, ct_img.header


def save_roi_package(
    output_dir: str | Path,
    ct_roi: np.ndarray,
    mask_roi: np.ndarray,
    metadata: dict,
    roi_affine: np.ndarray,
    organ_name: str = "kidney_left",
) -> dict[str, Path]:
    """
    Saves the extracted ROI scan, mask, and spatial metadata to disk.

    Output layout:
        <output_dir>/
            <organ_name>_ct.nii.gz
            <organ_name>_mask.nii.gz
            roi_metadata.json

    Returns:
        Dictionary with paths to saved files.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    ct_roi_path = out_path / f"{organ_name}_ct.nii.gz"
    mask_roi_path = out_path / f"{organ_name}_mask.nii.gz"
    meta_path = out_path / "roi_metadata.json"

    # Save NIfTI volumes with computed ROI affine
    ct_nii = nib.Nifti1Image(ct_roi.astype(np.float32), roi_affine)
    nib.save(ct_nii, str(ct_roi_path))

    mask_nii = nib.Nifti1Image(mask_roi.astype(np.uint8), roi_affine)
    nib.save(mask_nii, str(mask_roi_path))

    # Save metadata
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    return {
        "ct_roi_path": ct_roi_path,
        "mask_roi_path": mask_roi_path,
        "metadata_path": meta_path,
    }
