import cv2
from pathlib import Path

import matplotlib.pyplot as plt

from src.loaders.nifti_loader import load_nifti
from src.visualization.ct_viewer import show_ct_viewer
from src.preprocessing.normalization import min_max_normalize
from src.preprocessing.histogram import show_histogram
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
from src.visualization.comparison import compare_images
from src.preprocessing.roi import crop_roi
from src.utils.image_saver import save_image


def main():

    scan_path = Path("datasets/raw/ct/ct_15mm_defaced.nii")

    image = load_nifti(scan_path)

    ct_array = image.get_fdata()

    # Normalize
    normalized_ct = min_max_normalize(ct_array)

    # Gaussian Filter
    filtered_ct = apply_gaussian_filter(normalized_ct)

    # Threshold
    binary_ct = apply_threshold(
        filtered_ct,
        threshold=0.20,
    )

    # Morphological Closing
    closed_ct = apply_closing(binary_ct)

    # Keep Largest Connected Component
    largest_ct = keep_largest_component(closed_ct)

    # Sobel Edge Detection
    edge_ct = apply_sobel_filter(
        largest_ct,
    )

    # Middle Slice
    slice_index = ct_array.shape[2] // 2

    # Canny Edge Detection
    canny_ct = apply_canny_filter(
        largest_ct[:, :, slice_index],
    )

    # Contour Detection
    contours = find_contours(
        largest_ct[:, :, slice_index],
    )
    
    analyze_contours(
        contours,
    )
    
    largest_contour = get_largest_contour(
        contours,
    )

    print("\nLargest Contour")

    print(
        "Area:",
        cv2.contourArea(largest_contour),
    )

    # Draw Contours
    contour_image = draw_contours(
        normalized_ct[:, :, slice_index],
        contours,
    )
    
    bounding_box_image = draw_bounding_box(
        normalized_ct[:, :, slice_index],
        largest_contour,
    )
    
    roi_image = crop_roi(
        normalized_ct[:, :, slice_index],
        largest_contour,
    )

    # Compare preprocessing pipeline
    compare_images(
        normalized_ct,
        filtered_ct,
        binary_ct,
        closed_ct,
        largest_ct,
        edge_ct,
        slice_index,
    )

    # Display Canny Result
    plt.figure(figsize=(6, 6))
    plt.imshow(
        canny_ct,
        cmap="gray",
    )
    plt.title("Canny Edge Detection")
    plt.axis("off")
    plt.show()

    # Display Contour Result
    plt.figure(figsize=(6, 6))
    plt.imshow(contour_image)
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
    
    save_image(
        roi_image,
        "outputs/roi/cropped_patient.png",
    )

    # Optional Visualizations
    # show_histogram(normalized_ct)
    # show_ct_viewer(ct_array)


if __name__ == "__main__":
    main()