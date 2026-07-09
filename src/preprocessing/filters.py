import numpy as np
from scipy.ndimage import gaussian_filter


def apply_gaussian_filter(
    image: np.ndarray,
    sigma: float = 1.0,
) -> np.ndarray:
    """
    Apply Gaussian smoothing to reduce image noise.
    """

    filtered_image = gaussian_filter(
        image,
        sigma=sigma,
    )

    return filtered_image