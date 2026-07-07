import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider


def show_ct_viewer(ct_array: np.ndarray) -> None:
    """
    Interactive CT Slice Viewer.

    Args:
        ct_array: 3D CT volume.
    """

    current_slice = ct_array.shape[2] // 2

    fig, ax = plt.subplots(figsize=(6, 6))

    plt.subplots_adjust(bottom=0.18)

    image = ax.imshow(
        ct_array[:, :, current_slice],
        cmap="gray"
    )

    ax.set_title(f"CT Slice {current_slice}")
    ax.axis("off")

    slider_ax = plt.axes([0.2, 0.05, 0.6, 0.03])

    slider = Slider(
        ax=slider_ax,
        label="Slice",
        valmin=0,
        valmax=ct_array.shape[2] - 1,
        valinit=current_slice,
        valstep=1,
    )

    def update(value):
        slice_index = int(slider.val)

        image.set_data(ct_array[:, :, slice_index])

        ax.set_title(f"CT Slice {slice_index}")

        fig.canvas.draw_idle()

    slider.on_changed(update)

    plt.show()