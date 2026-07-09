import matplotlib.pyplot as plt
import numpy as np


def show_histogram(image: np.ndarray) -> None:
    """
    Display the intensity histogram of an image.
    """

    plt.figure(figsize=(8, 5))

    plt.hist(
        image.ravel(),
        bins=100,
    )

    plt.title("Image Intensity Histogram")
    plt.xlabel("Normalized Intensity")
    plt.ylabel("Number of Voxels")

    plt.grid(True)

    plt.show()