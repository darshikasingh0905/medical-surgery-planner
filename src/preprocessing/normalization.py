import numpy as np


def min_max_normalize(image: np.ndarray) -> np.ndarray:
    """
    Normalize an image to the range [0, 1]
    using Min-Max Normalization.
    """

    min_value = np.min(image)
    max_value = np.max(image)

    normalized_image = (
        image - min_value
    ) / (
        max_value - min_value
    )

    return normalized_image

