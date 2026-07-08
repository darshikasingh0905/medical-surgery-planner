import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider

from src.preprocessing.windowing import apply_window


def show_ct_viewer(ct_array: np.ndarray) -> None:
    """
    Interactive CT Slice Viewer with keyboard, mouse,
    and CT window presets.
    """

    total_slices = ct_array.shape[2]

    # ---------------- Viewer State ---------------- #

    current_slice = [total_slices // 2]

    current_window = ["Soft Tissue"]

    window_width = [400]
    window_level = [40]

    # Window presets
    WINDOW_PRESETS = {
        "b": ("Bone", 2000, 500),
        "g": ("Lung", 1500, -600),
        "t": ("Soft Tissue", 400, 40),
    }

    # ---------------------------------------------- #

    # Initial windowed slice
    windowed_slice = apply_window(
        ct_array[:, :, current_slice[0]],
        window_width[0],
        window_level[0],
    )

    fig, ax = plt.subplots(figsize=(6, 6))
    plt.subplots_adjust(bottom=0.18)

    image = ax.imshow(
        windowed_slice,
        cmap="gray",
    )

    ax.axis("off")

    slider_ax = plt.axes([0.2, 0.05, 0.6, 0.03])

    slider = Slider(
        ax=slider_ax,
        label="Slice",
        valmin=0,
        valmax=total_slices - 1,
        valinit=current_slice[0],
        valstep=1,
    )

    def update_display(slice_index: int) -> None:
        """
        Update the displayed CT slice.
        """

        windowed_slice = apply_window(
            ct_array[:, :, slice_index],
            window_width[0],
            window_level[0],
        )

        image.set_data(windowed_slice)

        ax.set_title(
            f"{current_window[0]} | "
            f"Slice {slice_index + 1}/{total_slices} | "
            f"WW: {window_width[0]} | "
            f"WL: {window_level[0]}"
        )

        fig.canvas.draw_idle()

    def update_slider(value):
        """
        Handle slider movement.
        """

        current_slice[0] = int(slider.val)
        update_display(current_slice[0])

    def on_key(event):
        """
        Handle keyboard navigation and window presets.
        """

        key = event.key.lower()

        # Next Slice
        if key == "right":

            if current_slice[0] < total_slices - 1:
                current_slice[0] += 1
                slider.set_val(current_slice[0])

        # Previous Slice
        elif key == "left":

            if current_slice[0] > 0:
                current_slice[0] -= 1
                slider.set_val(current_slice[0])

        # Window Presets
        elif key in WINDOW_PRESETS:

            window_name, ww, wl = WINDOW_PRESETS[key]

            current_window[0] = window_name
            window_width[0] = ww
            window_level[0] = wl

            update_display(current_slice[0])

    def on_scroll(event):
        """
        Handle mouse wheel navigation.
        """

        if event.button == "up":

            if current_slice[0] < total_slices - 1:
                current_slice[0] += 1
                slider.set_val(current_slice[0])

        elif event.button == "down":

            if current_slice[0] > 0:
                current_slice[0] -= 1
                slider.set_val(current_slice[0])

    slider.on_changed(update_slider)

    fig.canvas.mpl_connect("key_press_event", on_key)
    fig.canvas.mpl_connect("scroll_event", on_scroll)

    update_display(current_slice[0])

    print("\n========== CT Viewer Controls ==========")
    print("← / →        : Previous / Next Slice")
    print("Mouse Wheel  : Scroll Through Slices")
    print("B            : Bone Window")
    print("G            : Lung Window")
    print("T            : Soft Tissue Window")
    print("========================================\n")

    plt.show()