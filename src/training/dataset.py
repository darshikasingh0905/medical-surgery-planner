"""
Custom PyTorch Dataset for Medical Image Segmentation.

This module will load:
- CT images
- Corresponding segmentation masks

The implementation will be completed after selecting
the final medical imaging dataset.
"""

from torch.utils.data import Dataset


class MedicalSegmentationDataset(Dataset):
    """
    Placeholder dataset class.
    """

    def __init__(self):
        pass

    def __len__(self):
        return 0

    def __getitem__(self, index):
        raise NotImplementedError(
            "Dataset implementation coming next."
        )