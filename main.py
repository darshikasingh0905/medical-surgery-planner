from pathlib import Path

from src.loaders.nifti_loader import load_nifti
from src.loaders.metadata import extract_metadata


def main():
    scan_path = Path("datasets/raw/ct/ct_15mm_defaced.nii")

    image = load_nifti(scan_path)

    metadata = extract_metadata(image)

    print(metadata)


if __name__ == "__main__":
    main()