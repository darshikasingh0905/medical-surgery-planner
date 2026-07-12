from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def save_image(
    image: np.ndarray,
    output_path: str,
) -> None:
    """
    Save an image to disk.
    """

    output = Path(output_path)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.imsave(
        output,
        image,
        cmap="gray",
    )

    print(f"Image saved to: {output}")