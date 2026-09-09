# Day 8: Tumor / Lesion Detection Research & Architecture

## Overview & Objective

Day 8 focuses on the research, feasibility analysis, and architectural design for integrating **tumor and lesion detection/segmentation** into the AI Medical Surgery Planner.

### Guiding Engineering Principles for Day 8
- **No fake tumor detectors**: No hardcoded coordinates, mock bounding boxes, or synthetic heuristics masquerading as AI models.
- **No ungrounded training**: No training on arbitrary or unannotated scans without certified benchmark annotations.
- **No synthetic tumor masks**: No fabricating masks to simulate successful pipeline runs.
- **No clinical diagnostic claims**: The platform is explicitly positioned as an AI-assisted preoperative planning research prototype.
- **Zero modification to existing pipeline**: The existing working pipeline (TotalSegmentator $\rightarrow$ Marching Cubes $\rightarrow$ Measurements $\rightarrow$ FastAPI $\rightarrow$ React/Three.js) remains intact.

---

## Investigation Performed

We inspected the active codebase to evaluate how an abnormality-detection subsystem can be incorporated without breaking existing functionality:
- `src/segmentation/ai_segmenter.py`: Manages TotalSegmentator execution. TotalSegmentator produces standard anatomical structures (117 classes), but does not perform intra-organ parenchymal tumor segmentation.
- `src/pipeline/case_processor.py`: Orchestrates background execution per case. Supports modular post-segmentation hooks.
- `src/mesh/mesh_generator.py`: Converts binary NIfTI volumes into physically scaled Wavefront `.obj` meshes via Marching Cubes.
- `src/measurements/measurement_engine.py`: Computes physical volumes, bounding boxes, and comparisons.
- `src/api/routes/cases.py`: Exposes upload, status polling, results, and mesh serving endpoints.
- `frontend/src/`: React + Three.js viewer with per-organ materials, visibility toggles, and measurement cards.

---

## Technical Problem Definition

We established the clear boundary between four medical imaging tasks:
1. **Organ Segmentation (Macro-Anatomy)**: Delineating healthy anatomical boundaries (e.g., kidneys, liver, aorta). *Supported by current TotalSegmentator pipeline.*
2. **Tumor / Lesion Detection**: Identifying the presence and coarse localization of abnormal tissue (e.g., bounding box proposal). *Not supported by default TotalSegmentator.*
3. **Tumor / Lesion Segmentation**: Voxel-level delineation of pathological tissue (separating tumor, cyst, necrosis, and parenchyma). *Target subsystem designed today.*
4. **Tumor Classification**: Predicting histological subtypes, malignancy grade, or staging. *Out of scope; requires biopsy correlation and clinical validation.*

---

## Public Dataset Comparative Analysis

We conducted a structured comparison of candidate public benchmark datasets:

| Metric | KiTS (Kidney Tumor) | LiTS (Liver Tumor) | MSD Lung (Task 06) | BraTS (Brain Tumor) |
|---|---|---|---|---|
| **Challenge** | KiTS19 / KiTS21 / KiTS23 | LiTS 2017 (MICCAI) | Medical Segmentation Decathlon | BraTS 2021 / 2023 |
| **Modality** | Contrast-Enhanced Abdominal CT | Contrast-Enhanced Abdominal CT | Thoracic CT | Multi-parametric MRI |
| **Anatomy** | Kidneys (Left & Right) | Liver | Lungs & Mediastinum | Brain |
| **Pathology** | Renal masses, cysts, RCC | Hepatocellular carcinoma, metastases | Non-small cell lung cancer | Glioblastoma |
| **Annotations** | 3D Voxel masks (Parenchyma, Tumor, Cyst) | 3D Voxel masks (Liver, Lesion) | 3D Voxel masks (Lung nodule) | 3D Voxel masks (Sub-regions) |
| **Sample Size** | 300 to 489 CT scans | 201 CT scans | 96 CT scans | 1,251 MRI cases |
| **Format** | NIfTI (`.nii.gz`) | NIfTI (`.nii.gz`) | NIfTI (`.nii.gz`) | NIfTI (`.nii.gz`) |
| **License** | Open Research (CC-BY-NC-SA 4.0) | Open Research (TCIA) | Open Research (CC-BY-SA 4.0) | Open Research (TCIA) |
| **Pipeline Compatibility** | **100% (Native Match)** | High | Moderate | Low (MRI Modality Mismatch) |

---

## Selected Initial Target: Renal Tumors (KiTS)

### Recommendation: **Renal Tumors (Kidney Masses) via the KiTS Benchmark**

### Justification:
1. **Direct Synergy with TotalSegmentator**: TotalSegmentator already outputs `kidney_left.nii.gz` and `kidney_right.nii.gz`. Using these masks as an **anatomical prior** allows cropping directly to the kidney region-of-interest (ROI), cutting computational volume by over 90% and completely eliminating false-positive detections in other organs.
2. **Multi-Class Ground Truth**: KiTS annotates normal kidney parenchyma, solid tumor, and fluid-filled cysts separately, preventing confusion between benign cysts and solid renal neoplasms.
3. **High Preoperative Value**: 3D spatial relationships (tumor depth, margin to renal capsule, proximity to renal hilum) directly correspond to established surgical planning metrics (e.g., R.E.N.A.L. Nephrometry score for partial nephrectomy).
4. **Data Format**: Standard NIfTI CT scans matching our existing pipeline.

---

## Recommended Model Architecture

### Evaluated Approaches:
- **2D Slice-by-Slice CNN**: Fast but produces severe slice-to-slice boundary steps, leading to jagged 3D surface meshes in Marching Cubes.
- **3D Volumetric U-Net**: True 3D spatial continuity, but computationally intensive.
- **nnU-Net**: Benchmark-winning accuracy across KiTS, but complex self-configuring training setup.
- **MONAI 3D SegResNet / DynUNet (Recommended)**: Modern PyTorch-based medical deep learning architecture with sliding-window 3D inference, Gaussian blending, and openly available research weights trained on KiTS.

### Proposed Inference Pipeline:
1. **Input**: Full CT scan (`.nii.gz`) + TotalSegmentator kidney mask (`kidney_left.nii.gz` / `kidney_right.nii.gz`).
2. **ROI Extraction**: Crop CT volume to the kidney bounding box + 20 mm safety margin.
3. **Preprocessing**: Resample to isotropic spacing (1.5 mm), window intensities to [-150, 250] HU, normalize intensity.
4. **Model Inference**: Sliding-window 3D patch inference with Gaussian overlap blending.
5. **Postprocessing**: Probability thresholding ($p > 0.50$), connected component noise filtering ($< 0.1\text{ cm}^3$ discarded), spatial coordinate re-projection into original CT affine space.
6. **Mesh Generation**: Marching Cubes outputs `kidney_tumor.obj`.

---

## Integration Architecture & File Hierarchy

The lesion subsystem integrates as an isolated, non-breaking stage in `src/pipeline/case_processor.py`:

```
outputs/cases/<case_id>/
├── case.json
├── input/
│   └── scan.nii.gz
├── segmentation/                  # TotalSegmentator anatomical masks
│   ├── kidney_left.nii.gz
│   └── liver.nii.gz
├── lesions/                       # Dedicated lesion outputs
│   ├── kidney_tumor_left.nii.gz   # Binary lesion mask
│   └── lesion_metadata.json       # Detection metadata
├── meshes/                        # 3D Wavefront OBJ models
│   ├── kidney_left.obj
│   └── kidney_tumor_left.obj      # Lesion 3D surface mesh
└── measurements/
    └── results.json               # Combined anatomical & lesion metrics
```

---

## Lesion Measurements vs. Clinical Interpretation

The system calculates objective geometric measurements without making unauthorized clinical diagnostic claims:

| Computational Measurement | Mathematical Basis | Clinical Boundaries |
|---|---|---|
| **Lesion Volume** | Voxel count $\times$ physical voxel volume ($\text{cm}^3$) | Purely geometric; does NOT determine tumor stage or aggressiveness. |
| **Max 3D Diameter** | Maximum Euclidean distance between surface mesh vertices ($\text{mm}$) | Computational proxy for RECIST 1.1; requires radiologist verification. |
| **Parenchymal Margin** | Minimum distance between tumor mesh and renal capsule ($\text{mm}$) | Geometric distance; does NOT guarantee negative surgical margins. |
| **Endophytic / Exophytic Ratio** | Internal vs. external volume distribution (%) | Morphological index; does NOT replace surgeon's operative judgment. |

---

## 3D Visualization Design (React + Three.js)

- **Translucent Host Organ**: Left/Right Kidney rendered with `opacity: 0.35`, `transparent: true`, allowing internal viewing of the tumor.
- **Vivid Opaque Lesion**: Rendered in solid crimson (`#DC2626`) with subtle specular highlights.
- **Independent Sidebar Toggle**: Toggleable separately from the parent kidney.
- **Measurement Card**: Displays lesion metrics (volume, diameter, margins) with explicit safety disclaimers in `InfoPanel.jsx`.

---

## Proposed API Endpoints (For Day 9+)

- `GET /api/cases/{case_id}/lesions`: Summary of detected lesions, coordinates, and volumes.
- `GET /api/cases/{case_id}/meshes/lesion/{lesion_id}`: Serves the lesion 3D surface mesh (`.obj`).
- Extended `GET /api/cases/{case_id}/results`: Augmented with an optional `"lesions"` object.

---

## Limitations

1. **Contrast Phase Sensitivity**: Renal lesion detection is most accurate on contrast-enhanced CT (corticomedullary / nephrographic phases). Non-contrast CT scans yield lower soft-tissue contrast between normal parenchyma and isodense renal neoplasms.
2. **Small Lesion Boundary Uncertainty**: Lesions $< 10\text{ mm}$ are subject to partial volume averaging and higher segmentation variance.
3. **No In-Vivo Biopsy Replacement**: Imaging morphology cannot distinguish benign oncocytoma or fat-poor angiomyolipoma from malignant renal cell carcinoma without tissue histopathology.

---

## Medical Safety Considerations

1. **System Classification**: AI-assisted preoperative planning research prototype.
2. **Non-Diagnostic**: The system does not diagnose, treat, or stage cancer.
3. **Mandatory Human Oversight**: All algorithmic findings, meshes, and geometric measurements must be reviewed and validated by a board-certified radiologist or surgeon before clinical consideration.

---

## Day 9 Roadmap

- **Step 1**: Implement `src/lesions/roi_extractor.py` to extract and preprocess the target organ ROI from CT scans.
- **Step 2**: Integrate model inference using verified benchmark weights or MONAI bundle.
- **Step 3**: Connect lesion mask output to `mesh_generator.py` and `measurement_engine.py`.
- **Step 4**: Expose lesion API endpoints in FastAPI.
- **Step 5**: Update React frontend with lesion rendering material, visibility toggle, and measurement display.
