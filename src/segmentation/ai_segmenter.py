import os
import sys
from pathlib import Path
import nibabel as nib
from totalsegmentator.python_api import totalsegmentator

def run_segmentation(
    input_path: str = "datasets/raw/ct/ct_15mm_defaced.nii",
    output_dir: str = "outputs/segmentations",
    fast_mode: bool = True
):
    """
    Runs TotalSegmentator on the given CT scan and saves the outputs.
    Uses fast_mode=True by default for CPU MVP feasibility.
    """
    input_file = Path(input_path)
    out_dir = Path(output_dir)

    print(f"--- Starting AI Segmentation ---")
    print(f"Input file: {input_file}")
    print(f"Output directory: {out_dir}")
    print(f"Fast mode enabled: {fast_mode} (crucial for CPU runtime)")

    if not input_file.exists():
        print(f"[ERROR] Input file not found at {input_file}", file=sys.stderr)
        return False

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        print("[INFO] Loading NIfTI image...")
        img = nib.load(input_file)
        
        print(f"[INFO] Image shape: {img.shape}")
        
        # TotalSegmentator will automatically detect CPU/GPU and run accordingly.
        print("[INFO] Running TotalSegmentator. This may take a few minutes on CPU...")
        
        # By providing output_dir, TotalSegmentator will save the multiple masks there.
        # fast=True lowers the resolution slightly for massive speedup.
        totalsegmentator(
            input_file, 
            output_dir, 
            fast=fast_mode
        )
        
        print("[INFO] TotalSegmentator completed successfully.")
        
        # Verification
        output_files = list(out_dir.glob("*.nii.gz"))
        if len(output_files) == 0:
            print("[ERROR] TotalSegmentator ran but no output files were generated.", file=sys.stderr)
            return False
            
        print(f"[SUCCESS] Generated {len(output_files)} segmentation masks in {out_dir}")
        print("First few masks generated:")
        for f in output_files[:5]:
            print(f"  - {f.name}")
            
        return True

    except Exception as e:
        print(f"[ERROR] An error occurred during segmentation: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = run_segmentation()
    if not success:
        sys.exit(1)
