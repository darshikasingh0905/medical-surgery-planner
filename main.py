from pathlib import Path

from src.loaders.nifti_loader import load_nifti
from src.visualization.ct_viewer import show_ct_viewer
from src.preprocessing.normalization import min_max_normalize
from src.preprocessing.histogram import show_histogram
from src.preprocessing.filters import apply_gaussian_filter
from src.preprocessing.thresholding import apply_threshold
from src.visualization.comparison import compare_images
from src.preprocessing.morphology import (
    apply_closing,
    keep_largest_component,
)
from src.preprocessing.edges import apply_sobel_filter


def main():

    scan_path = Path("datasets/raw/ct/ct_15mm_defaced.nii")

    image = load_nifti(scan_path)

    ct_array = image.get_fdata()

    # Normalize
    normalized_ct = min_max_normalize(ct_array)

    # Apply Gaussian Filter
    filtered_ct = apply_gaussian_filter(normalized_ct)

    # Apply Threshold
    binary_ct = apply_threshold(
        filtered_ct,
        threshold=0.20,
    )
    
    closed_ct = apply_closing(binary_ct)
    
    largest_ct = keep_largest_component(closed_ct)
    
    edge_ct = apply_sobel_filter(
        largest_ct,
    )

    # Middle Slice
    slice_index = ct_array.shape[2] // 2

    # Compare Images
    compare_images(
        normalized_ct,
        filtered_ct,
        binary_ct,
        closed_ct,
        largest_ct,
        edge_ct,
        slice_index,
    )

    # Uncomment if you want to use these
    # show_histogram(normalized_ct)
    # show_ct_viewer(ct_array)


if __name__ == "__main__":
    main()