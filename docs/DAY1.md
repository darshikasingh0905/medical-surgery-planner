# Day 1: AI Segmentation Pipeline

## Objective
Integrate TotalSegmentator to process a CT scan and generate 3D NIfTI masks for anatomical structures, transitioning from the experimental custom U-Net to a production-ready MVP pipeline.

## What We Implemented
1. **Environment Setup:** Successfully updated `requirements.txt` manually to include `TotalSegmentator`, `torch`, `torchvision`, `torchaudio`, and `opencv-python`. These were installed via pip into the existing `venv`.
2. **Segmentation Module:** Created `src/segmentation/ai_segmenter.py` which utilizes the `totalsegmentator` Python API. It reads the test CT, executes in `fast=True` mode, and saves outputs to the `outputs/segmentations/` directory.
3. **Execution & Testing:** Ran the segmenter on `datasets/raw/ct/ct_15mm_defaced.nii`. The process completed successfully on the CPU, downloading the pre-trained weights and performing the inference.

## Files Created/Modified
- `requirements.txt` (Modified: Appended dependencies)
- `src/segmentation/ai_segmenter.py` (New: The execution module)
- `outputs/segmentations/*.nii.gz` (New: 117 generated masks)

## Commands Executed
**Installation:**
```bash
.\venv\Scripts\pip install TotalSegmentator torch torchvision torchaudio opencv-python
```

**Execution:**
```bash
python -m src.segmentation.ai_segmenter
```

## Actual Output
The script successfully extracted 117 individual organ masks from the CT scan.
```
outputs/
└── segmentations/
    ├── adrenal_gland_left.nii.gz
    ├── adrenal_gland_right.nii.gz
    ├── aorta.nii.gz
    ├── atrial_appendage_left.nii.gz
    ├── autochthon_left.nii.gz
    └── ... (112 more structures)
```
The total inference time on the CPU (including model download and resampling) was approximately 3.5 minutes.

## What I Need to Understand
- **Why Pre-trained Models?** Why we chose TotalSegmentator over training our custom U-Net from scratch (time, resources, dataset size).
- **NIfTI Format:** How 3D medical images are stored and how masks map to the original CT scan voxels.
- **Python API Integration:** How to call complex external AI tools from within a Python script.
- **CPU Limitations:** The trade-off between speed and accuracy when running AI models on a CPU (using the `fast=True` mode).

## Next Step
Proceeding to Day 2: Processing the generated segmentation masks (e.g., `liver.nii.gz`, `kidney_left.nii.gz`) to extract 3D meshes using surface reconstruction techniques (marching cubes).
