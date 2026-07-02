from pathlib import Path

from src.loaders.nifti_loader import load_nifti


def main():
    scan_path = Path("datasets/raw/ct/ct_15mm_defaced.nii")
    image = load_nifti(scan_path)

    print("CT scan loaded successfully!")
    print(f"Image Type: {type(image)}")
    print(f"Shape: {image.shape}")


if __name__ == "__main__":
    main()