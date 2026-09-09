# Day 9: Renal Lesion Pipeline Foundation

## 1. Overview & Objectives

Day 9 establishes the **lesion pipeline foundation** for the AI Medical Surgery Planner. Following the architectural decisions from Day 8 (KiTS renal tumor target, MONAI 3D SegResNet/DynUNet model family), Day 9 implements the complete engineering scaffolding required to extract anatomical regions of interest (ROI), preprocess volumetric CT arrays, enforce model safety contracts, postprocess prediction arrays, and re-embed binary lesion masks back into the patient's original CT coordinate space.

### Core Medical Engineering Governance
- **No fake tumor detectors**: No hardcoded lesion locations or mock bounding boxes masquerading as AI outputs.
- **No ungrounded predictions**: The inference engine strictly halts and raises an explicit error when validated model weights are not configured.
- **No fabricated masks**: Synthetic arrays are restricted exclusively to isolated unit tests and are never saved to `outputs/cases/`.
- **Preservation of existing pipeline**: Days 1–8 functionality (TotalSegmentator, Marching Cubes, FastAPI routes, React/Three.js frontend) remains 100% operational and regression-free.

---

## 2. Software Architecture Implemented

The `src/lesions/` subsystem provides modular, decoupled interfaces ready for future validated deep learning model weights:

```
src/lesions/
├── __init__.py            # Clean exports for ROI extraction, inference, and postprocessing
├── roi_extractor.py       # Kidney ROI bounding box extractor with physical margin expansion
├── lesion_inference.py    # Preprocessing transforms & LesionInferenceEngine safety abstraction
└── postprocessing.py      # Binarization, connected component filtering, original-space re-embedding
```

---

## 3. Detailed Component Implementations

### 3.1 Region of Interest (ROI) Extraction (`roi_extractor.py`)

The extractor leverages the anatomical prior provided by TotalSegmentator (`kidney_left.nii.gz` or `kidney_right.nii.gz`) to extract a tight, physically expanded bounding box around the target organ:

1. **Load Volumes**: Loads both the original CT scan and the segmented kidney mask using NiBabel.
2. **Foreground Localization**: Computes minimum and maximum voxel coordinates enclosing all non-zero mask voxels:
   $$\mathbf{b}_{\min} = \min_{i} \mathbf{v}_i, \quad \mathbf{b}_{\max} = \max_{i} \mathbf{v}_i$$
3. **Physical Margin Calculation**: Rather than arbitrary voxel padding, the expansion margin is specified in true physical millimeters (default: $20.0\text{ mm}$). Voxel padding is calculated per axis to accommodate anisotropic voxel spacing $(s_x, s_y, s_z)$:
   $$\text{pad}_i = \left\lceil \frac{\text{margin}_{\text{mm}}}{s_i} \right\rceil$$
4. **Boundary Clamping**: Expands bounds and strictly clamps to the scan dimensions $[0, D_i - 1]$ to prevent index overflow on peripheral anatomies.
5. **Affine Transformation Recovery**: Computes the true physical affine for the cropped ROI volume:
   $$\mathbf{A}_{\text{ROI}} = \mathbf{A}_{\text{orig}} \cdot \begin{bmatrix} \mathbf{I}_{3 \times 3} & \mathbf{b}_{\min} \\ \mathbf{0}^T & 1 \end{bmatrix}$$
6. **Metadata Persistence**: Records complete spatial tracking information (`source_image_shape`, `source_voxel_spacing`, `original_affine`, `roi_affine`, `roi_slices`, `physical_margin_mm`, `voxel_padding`).

### 3.2 Preprocessing Pipeline (`lesion_inference.py`)

Provides standardized medical image intensity transformations while preserving spatial dimensions:
- **Hounsfield Unit (HU) Windowing**: Soft tissue and renal parenchymal attenuation window:
  $$I_{\text{clipped}} = \text{clip}(I, -150\text{ HU}, 250\text{ HU})$$
- **Intensity Normalization**:
  - `minmax`: Scales intensities to $[0.0, 1.0]$ via $(I - \text{min}) / (\text{max} - \text{min})$.
  - `zscore`: Standardizes intensities to zero mean and unit variance.
- **Transformation Tracking**: Returns a metadata dictionary detailing clipping boundaries, input/output shapes, and dynamic range.

### 3.3 Model Inference Abstraction & Safety Enforcer (`lesion_inference.py`)

Defines `LesionModelConfig` and `LesionInferenceEngine`:
- Configurable parameters: `model_path`, `model_type` (default: `"monai_segresnet"`), `device` (`"cpu"` or `"cuda"`), `patch_size` ($96 \times 96 \times 96$), and `sliding_window_overlap` ($0.5$).
- **Safety Stop**: `predict(ct_roi, metadata)` verifies that `model_path` points to a verified, existing checkpoint. If missing, it immediately raises:
  ```python
  RuntimeError("Validated lesion model weights are not configured. The system will not generate ungrounded or synthetic tumor predictions.")
  ```
- **Guaranteed No-Hallucination**: The engine never generates mock probabilities, fake bounding boxes, or synthetic lesions when unconfigured.

### 3.4 Postprocessing & Original-Space Mapping (`postprocessing.py`)

Prepares future model outputs for 3D meshing and clinical inspection:
1. **Probability Binarization**: Cutoff thresholding (default: $p \ge 0.50$).
2. **Connected Component Filtering**: 3D connected-component analysis ($26$-connectivity) via `scipy.ndimage.label`. Spurious noise clusters below a volume threshold (default: $50\text{ voxels}$ / $\approx 0.1\text{ cm}^3$) are automatically eliminated.
3. **Coordinate Re-Embedding (`embed_roi_in_original_space`)**: Uses the recorded `roi_slices` to embed the cropped binary mask back into a zero-initialized volume of identical dimensions to the original whole-body CT scan.
4. **Affine Alignment (`save_original_space_mask`)**: Writes the full mask with the original CT scan's affine matrix, guaranteeing 1:1 voxel alignment with organ masks and DICOM patient coordinates.
5. **Lesion Metadata (`create_lesion_metadata`)**: Generates structured metadata containing voxel count, physical volume ($\text{mm}^3$, $\text{cm}^3$, $\text{mL}$), bounding box physical dimensions ($\text{mm}$), centroid $(X, Y, Z)$, model provenance, and mandatory medical disclaimers.

---

## 4. Planned Case Storage Structure

When a validated model is integrated, case outputs will adhere to this structured layout:

```
outputs/cases/<case_id>/
├── case.json
├── input/
│   └── scan.nii.gz                     # Original patient CT
├── segmentation/                       # TotalSegmentator masks
│   ├── kidney_left.nii.gz
│   └── liver.nii.gz
├── lesions/                            # Lesion subsystem
│   ├── roi/                            # Cropped ROI package
│   │   ├── kidney_left_ct.nii.gz
│   │   ├── kidney_left_mask.nii.gz
│   │   └── roi_metadata.json
│   ├── kidney_tumor_left.nii.gz        # Full patient-space binary mask
│   └── lesion_metadata.json            # Objective measurements & provenance
└── meshes/
    ├── kidney_left.obj
    └── kidney_tumor_left.obj           # 3D lesion surface mesh
```

---

## 5. Verification & Testing

A comprehensive unit test suite was implemented in `tests/test_lesions.py`. All tests use isolated, synthetic in-memory fixtures:

| Test Case | Purpose | Result |
|---|---|---|
| `test_roi_bounding_box_and_metadata` | Validates mask containment and metadata correctness | **PASS** |
| `test_physical_margin_voxel_conversion` | Validates physical mm conversion to anisotropic voxel padding | **PASS** |
| `test_roi_boundary_clamping` | Validates clamping when organ lies on scan boundary | **PASS** |
| `test_save_roi_package` | Validates writing ROI files and JSON metadata to disk | **PASS** |
| `test_preprocessing_windowing_and_normalization` | Validates [-150, 250] HU clipping and [0, 1] normalization | **PASS** |
| `test_inference_engine_unconfigured_safety` | **Safety Check**: Confirms RuntimeError when weights are absent | **PASS** |
| `test_postprocessing_connected_components` | Confirms small noise artifacts are removed, valid clusters kept | **PASS** |
| `test_inverse_roi_mapping_to_original_space` | Validates exact voxel coordinate recovery in original space | **PASS** |
| `test_create_lesion_metadata` | Validates physical volume, centroid, and disclaimer generation | **PASS** |

### Complete Test Suite Execution
```powershell
python -m pytest tests/ -v
# 24 passed, 4 warnings in 4.70s
```
- Existing API tests: 10/10 passed.
- Existing measurement tests: 5/5 passed.
- New lesion foundation tests: 9/9 passed.

---

## 6. Current Status & Blockers

### Implemented Software
- ROI extraction with physical millimeter padding and anisotropic voxel handling.
- Coordinate preservation and affine transformation mathematics.
- Preprocessing windowing and normalization transforms.
- Safe inference engine abstraction.
- Connected component postprocessing and noise removal.
- Inverse mapping back into original patient space.
- Structured lesion metadata generation.

### Blocked on Future Model Weights
- **Actual Lesion Predictions**: The system does not yet run model inference because certified KiTS-compatible pretrained weights (e.g. MONAI Model Zoo SegResNet or trained nnU-Net checkpoint) have not yet been downloaded, verified, and configured.

---

## 7. Medical Safety & Disclaimer

> [!CAUTION]
> **AI-Assisted Preoperative Planning Prototype**:
> This software is an experimental research prototype for preoperative surgical planning and anatomical visualization.
> 1. It is **NOT** a medical diagnostic device.
> 2. It does **NOT** detect cancer, diagnose malignancy, or replace histological biopsy.
> 3. Algorithmic outputs, segmentation masks, and geometric measurements require clinical verification by a board-certified radiologist, urologist, or attending surgeon prior to any clinical decision.
