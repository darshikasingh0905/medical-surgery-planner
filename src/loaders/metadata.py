"""
metadata.py

Utilities for extracting metadata from NIfTI medical images.
"""

from dataclasses import dataclass

import nibabel as nib
import numpy as np

@dataclass
class ScanMetadata:
    shape: tuple
    voxel_spacing: tuple
    data_type: str
    affine: np.ndarray
    
def extract_metadata(image: nib.Nifti1Image) -> ScanMetadata:
    """
    Extract important metadata from a NIfTI image.

    Args:
        image: Loaded NIfTI image.

    Returns:
        ScanMetadata object containing essential scan information.
    """
    
    shape = image.shape
    