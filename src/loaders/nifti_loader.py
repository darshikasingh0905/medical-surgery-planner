"""
nifti_loader.py

Functions for loading NIfTI (.nii and .nii.gz) medical images.
"""

from pathlib import Path
import nibabel as nib

def load_nifti(path: Path) -> nib.Nifti1Image:
    """
    Load a NIfTI (.nii or .nii.gz) medical image.

    Args:
        path: Path to the NIfTI file.

    Returns:
        A loaded Nifti1Image object.
    """
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if not str(path).endswith((".nii", ".nii.gz")):
        raise ValueError(
            "Unsupported file format. Expected '.nii' or '.nii.gz'."
        )
    
    try:
        image = nib.load(path)

    except nib.filebasedimages.ImageFileError as error:
        raise ValueError(
            f"Failed to load NIfTI file: {path}"
        ) from error

    return image