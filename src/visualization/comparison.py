import matplotlib.pyplot as plt
import numpy as np


def compare_images(
    original: np.ndarray,
    filtered: np.ndarray,
    binary: np.ndarray,
    slice_index: int,
) -> None:
    """
    Display original, filtered, and thresholded CT slices.
    """

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    axes[0].imshow(original[:, :, slice_index], cmap="gray")
    axes[0].set_title("Original")
    axes[0].axis("off")

    axes[1].imshow(filtered[:, :, slice_index], cmap="gray")
    axes[1].set_title("Gaussian Filter")
    axes[1].axis("off")

    axes[2].imshow(binary[:, :, slice_index], cmap="gray")
    axes[2].set_title("Thresholded")
    axes[2].axis("off")

    plt.tight_layout()
    plt.show()