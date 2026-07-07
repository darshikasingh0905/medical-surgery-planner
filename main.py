from pathlib import Path

from src.loaders.nifti_loader import load_nifti
from src.visualization.ct_viewer import show_ct_viewer


def main():

    scan_path = Path("datasets/raw/ct/ct_15mm_defaced.nii")

    image = load_nifti(scan_path)

    ct_array = image.get_fdata()

    show_ct_viewer(ct_array)


if __name__ == "__main__":
    main()