import cv2
import numpy as np


def crop_roi(
    image: np.ndarray,
    contour,
) -> np.ndarray:
    """
    Crop the Region of Interest using
    the bounding box of the contour.
    """

    x, y, w, h = cv2.boundingRect(
        contour,
    )

    roi = image[
        y:y + h,
        x:x + w,
    ]

    return roi