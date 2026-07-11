import cv2
import numpy as np


def apply_canny_filter(
    ct_slice: np.ndarray,
) -> np.ndarray:
    """
    Apply Canny Edge Detection to a single CT slice.
    """

    image_uint8 = (
        ct_slice * 255
    ).astype(np.uint8)

    edges = cv2.Canny(
        image_uint8,
        threshold1=50,
        threshold2=150,
    )

    return edges