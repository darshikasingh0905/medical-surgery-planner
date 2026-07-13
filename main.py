from pathlib import Path

import cv2
import matplotlib.pyplot as plt

from src.loaders.nifti_loader import load_nifti

from src.preprocessing.normalization import min_max_normalize
from src.preprocessing.filters import apply_gaussian_filter
from src.preprocessing.thresholding import apply_threshold
from src.preprocessing.morphology import (
    apply_closing,
    keep_largest_component,
)
from src.preprocessing.edges import apply_sobel_filter
from src.preprocessing.canny import apply_canny_filter
from src.preprocessing.contours import (
    find_contours,
    draw_contours,
    analyze_contours,
    get_largest_contour,
    draw_bounding_box,
)
from src.preprocessing.roi import crop_roi

from src.utils.image_saver import save_image

from src.visualization.comparison import compare_images
from src.visualization.ct_viewer import show_ct_viewer
from src.preprocessing.histogram import show_histogram


def main():

    # --------------------------------------------------
    # Load CT Scan
    # --------------------------------------------------
    scan_path = Path("datasets/raw/ct/ct_15mm_defaced.nii")

    image = load_nifti(scan_path)
    ct_array = image.get_fdata()

    slice_index = ct_array.shape[2] // 2

    # --------------------------------------------------
    # Preprocessing
    # --------------------------------------------------
    normalized_ct = min_max_normalize(ct_array)

    filtered_ct = apply_gaussian_filter(
        normalized_ct,
    )

    binary_ct = apply_threshold(
        filtered_ct,
        threshold=0.20,
    )

    closed_ct = apply_closing(
        binary_ct,
    )

    largest_ct = keep_largest_component(
        closed_ct,
    )

    # --------------------------------------------------
    # Edge Detection
    # --------------------------------------------------
    edge_ct = apply_sobel_filter(
        largest_ct,
    )

    canny_ct = apply_canny_filter(
        largest_ct[:, :, slice_index],
    )

    # --------------------------------------------------
    # Contour Detection
    # --------------------------------------------------
    contours = find_contours(
        largest_ct[:, :, slice_index],
    )

    # Uncomment for debugging
    # analyze_contours(contours)

    largest_contour = get_largest_contour(
        contours,
    )

    contour_image = draw_contours(
        normalized_ct[:, :, slice_index],
        contours,
    )

    bounding_box_image = draw_bounding_box(
        normalized_ct[:, :, slice_index],
        largest_contour,
    )

    # --------------------------------------------------
    # Region of Interest (ROI)
    # --------------------------------------------------
    roi_image = crop_roi(
        normalized_ct[:, :, slice_index],
        largest_contour,
    )

    save_image(
        roi_image,
        "outputs/roi/cropped_patient.png",
    )

    # --------------------------------------------------
    # Visualizations
    # --------------------------------------------------
    compare_images(
        normalized_ct,
        filtered_ct,
        binary_ct,
        closed_ct,
        largest_ct,
        edge_ct,
        slice_index,
    )

    plt.figure(figsize=(6, 6))
    plt.imshow(
        canny_ct,
        cmap="gray",
    )
    plt.title("Canny Edge Detection")
    plt.axis("off")
    plt.show()

    plt.figure(figsize=(6, 6))
    plt.imshow(
        contour_image,
    )
    plt.title("Detected Contours")
    plt.axis("off")
    plt.show()

    plt.figure(figsize=(6, 6))
    plt.imshow(
        bounding_box_image,
    )
    plt.title("Bounding Box")
    plt.axis("off")
    plt.show()

    plt.figure(figsize=(6, 6))
    plt.imshow(
        roi_image,
        cmap="gray",
    )
    plt.title("Cropped ROI")
    plt.axis("off")
    plt.show()

    # --------------------------------------------------
    # Optional Visualizations
    # --------------------------------------------------
    # show_histogram(normalized_ct)
    # show_ct_viewer(ct_array)


if __name__ == "__main__":
    main()