from pathlib import Path

import matplotlib.pyplot as plt

from src.loaders.nifti_loader import load_nifti


def main():
    scan_path = Path("datasets/raw/ct/ct_15mm_defaced.nii")

    image = load_nifti(scan_path)

    ct_array = image.get_fdata()

    middle_slice = ct_array[:, :, ct_array.shape[2] // 2]

    plt.imshow(middle_slice, cmap="gray")
    plt.title("Middle CT Slice")
    plt.axis("off")
    plt.show()


if __name__ == "__main__":
    main()