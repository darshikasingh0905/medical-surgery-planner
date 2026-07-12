import cv2
import numpy as np


def find_contours(
    binary_slice: np.ndarray,
):
    """
    Detect contours in a binary image.
    """

    image_uint8 = (
        binary_slice * 255
    ).astype(np.uint8)

    contours, _ = cv2.findContours(
        image_uint8,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    return contours

def draw_contours(
    image: np.ndarray,
    contours,
) -> np.ndarray:
    """
    Draw contours on an image.
    """

    image_uint8 = (
        image * 255
    ).astype(np.uint8)

    image_bgr = cv2.cvtColor(
        image_uint8,
        cv2.COLOR_GRAY2BGR,
    )

    cv2.drawContours(
        image_bgr,
        contours,
        -1,
        (0, 255, 0),
        2,
    )

    return image_bgr