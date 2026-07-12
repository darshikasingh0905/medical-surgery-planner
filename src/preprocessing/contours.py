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


def analyze_contours(
    contours,
) -> None:
    """
    Print information about detected contours.
    """

    print("\n===== Contour Analysis =====")

    print(f"Total Contours: {len(contours)}")

    for i, contour in enumerate(contours):

        area = cv2.contourArea(contour)

        perimeter = cv2.arcLength(
            contour,
            True,
        )

        print(f"\nContour {i + 1}")

        print(f"Area: {area:.2f}")

        print(f"Perimeter: {perimeter:.2f}")


def get_largest_contour(
    contours,
):
    """
    Return the contour with the largest area.
    """

    largest = max(
        contours,
        key=cv2.contourArea,
    )

    return largest

def draw_bounding_box(
    image: np.ndarray,
    contour,
) -> np.ndarray:
    """
    Draw a bounding box around a contour.
    """

    image_uint8 = (
        image * 255
    ).astype(np.uint8)

    image_bgr = cv2.cvtColor(
        image_uint8,
        cv2.COLOR_GRAY2BGR,
    )

    x, y, w, h = cv2.boundingRect(
        contour,
    )

    cv2.rectangle(
        image_bgr,
        (x, y),
        (x + w, y + h),
        (255, 0, 0),
        2,
    )

    return image_bgr