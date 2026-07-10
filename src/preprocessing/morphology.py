import numpy as np
from scipy.ndimage import binary_dilation
from scipy.ndimage import binary_erosion
from scipy.ndimage import label

def apply_dilation(
    binary_image: np.ndarray,
) -> np.ndarray:
    """
    Expand white regions.
    """

    dilated = binary_dilation(binary_image)

    return dilated.astype(np.uint8)

def apply_erosion(
    binary_image: np.ndarray,
) -> np.ndarray:
    """
    Shrink white regions.
    """

    eroded = binary_erosion(binary_image)

    return eroded.astype(np.uint8)

from scipy.ndimage import binary_opening


def apply_opening(
    binary_image: np.ndarray,
) -> np.ndarray:
    """
    Remove small white noise.
    """

    opened = binary_opening(binary_image)

    return opened.astype(np.uint8)

from scipy.ndimage import binary_closing


def apply_closing(
    binary_image: np.ndarray,
) -> np.ndarray:
    """
    Fill small holes inside objects.
    """

    closed = binary_closing(binary_image)

    return closed.astype(np.uint8)

def keep_largest_component(
    binary_image: np.ndarray,
) -> np.ndarray:
    """
    Keep only the largest connected component.
    """

    labeled_image, num_features = label(binary_image)

    largest_size = 0
    largest_label = 0

    for component in range(1, num_features + 1):

        component_size = np.sum(
            labeled_image == component
        )

        if component_size > largest_size:
            largest_size = component_size
            largest_label = component

    largest_component = (
        labeled_image == largest_label
    )

    return largest_component.astype(np.uint8)