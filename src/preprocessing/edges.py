import numpy as np
from scipy import ndimage


def apply_sobel_filter(ct_array: np.ndarray) -> np.ndarray:
    """
    Apply Sobel Edge Detection.
    """

    sobel_x = ndimage.sobel(
        ct_array,
        axis=0,
    )

    sobel_y = ndimage.sobel(
        ct_array,
        axis=1,
    )

    edge_image = np.hypot(
        sobel_x,
        sobel_y,
    )

    return edge_image