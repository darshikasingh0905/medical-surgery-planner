import numpy as np


def apply_window(
    slice_data: np.ndarray,
    window_width: float,
    window_level: float,
) -> np.ndarray:
    """
    Apply CT Window Width and Window Level.
    """

    lower = window_level - (window_width / 2)

    upper = window_level + (window_width / 2)

    return np.clip(slice_data, lower, upper)