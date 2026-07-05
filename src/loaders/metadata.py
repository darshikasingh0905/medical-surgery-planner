from dataclasses import dataclass

import nibabel as nib
import numpy as np


@dataclass
class ScanMetadata:
    shape: tuple
    voxel_spacing: tuple
    data_type: str
    affine: np.ndarray

    def __repr__(self):
        output = "========== CT Scan Metadata ==========\n"

        output += f"Shape           : {self.shape}\n"
        output += f"Voxel Spacing   : {self.voxel_spacing} mm\n"
        output += f"Data Type       : {self.data_type}\n"

        output += "\nAffine Matrix:\n"
        output += str(self.affine)

        output += "\n======================================"

        return output


def extract_metadata(image: nib.Nifti1Image) -> ScanMetadata:
    """
    Extract important metadata from a NIfTI image.

    Args:
        image: Loaded NIfTI image.

    Returns:
        ScanMetadata object containing essential scan information.
    """

    shape = image.shape
    voxel_spacing = tuple(float(value) for value in image.header.get_zooms())    
    data_type = image.header.get_data_dtype()
    affine = image.affine

    return ScanMetadata(
        shape=shape,
        voxel_spacing=voxel_spacing,
        data_type=data_type,
        affine=affine,
    )