import matplotlib.pyplot as plt
import numpy as np


def compare_images(
    original: np.ndarray,
    filtered: np.ndarray,
    binary: np.ndarray,
    closed: np.ndarray,
    largest: np.ndarray,
    slice_index: int,
) -> None:
    """
    Display preprocessing stages side by side.
    """

    fig, axes = plt.subplots(1, 5, figsize=(24, 6))

    images = [
        original,
        filtered,
        binary,
        closed,
        largest,
    ]

    titles = [
        "Original",
        "Gaussian",
        "Threshold",
        "Closing",
        "Largest Component",
    ]

    for ax, image, title in zip(axes, images, titles):

        ax.imshow(
            image[:, :, slice_index],
            cmap="gray",
        )

        ax.set_title(title)
        ax.axis("off")

    plt.tight_layout()
    plt.show()