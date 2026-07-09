import numpy as np


def apply_threshold(
    image: np.ndarray,
    threshold: float,
) -> np.ndarray:
    """
    Convert an image into a binary image using thresholding.
    """

    binary_image = image > threshold

    return binary_image.astype(np.uint8)