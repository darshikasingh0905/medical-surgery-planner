# Tumor and Lesion Detection: Research & Technical Architecture

## 1. Executive Summary

This document defines the technical problem, dataset selection, algorithmic framework, integration architecture, and medical safety governance for incorporating abnormality (tumor/lesion) detection and segmentation into the **AI Medical Surgery Planner**.

Currently (Days 1–7), the platform performs multi-organ anatomical segmentation from CT scans using TotalSegmentator, generates 3D surface meshes (Marching Cubes), calculates geometric metrics, and renders them interactively in a React + Three.js web application.

This document establishes the blueprint for Day 8 and beyond. In accordance with strict medical engineering standards:
- **No fake tumor detectors** are created.
- **No ungrounded models** are trained without certified benchmark datasets.
- **No synthetic tumor masks** are generated.
- **No clinical diagnostic claims** are made.

---

## 2. Technical Problem Definition

In computer-assisted radiology and surgical planning, automated analysis of pathological tissue spans four distinct technical tasks. Distinguishing these tasks is essential to avoid architectural errors and false clinical claims.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MEDICAL IMAGING AI TAXONOMY                           │
├──────────────────────────┬──────────────────────────────────────────────────┤
│ 1. Organ Segmentation    │ Macro-anatomical boundaries of normal organs     │
│                          │ (e.g., liver, left kidney, aorta)                │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 2. Lesion Detection      │ Spatial presence identification                  │
│                          │ (e.g., bounding box: "lesion at [x,y,z]")        │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 3. Lesion Segmentation   │ Voxel-level boundary delineation                 │
│                          │ (e.g., exact 3D shape of pathological mass)      │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ 4. Lesion Classification │ Pathological grading & histopathology prediction │
│                          │ (e.g., benign cyst vs. clear-cell RCC)           │
└──────────────────────────┴──────────────────────────────────────────────────┘
```

### 2.1 Detailed Task Distinctions

1. **Organ Segmentation (Macro-Anatomy)**:
   - **Definition**: Delineates normal anatomical structures with consistent morphology, predictable contrast uptake, and strong spatial priors relative to the skeleton.
   - **Supported by Current System**: **Yes**. TotalSegmentator v1/v2 segments 117 anatomical structures (organs, bones, vessels, muscles) directly from whole-body CT.
   - **Role in Pipeline**: Provides the structural framework and spatial reference (ROI) for all subsequent analyses.

2. **Tumor / Lesion Detection**:
   - **Definition**: Identifies the presence and coarse localization of abnormal tissue within an organ, typically outputting a 3D bounding box, centroid coordinate, or slice-level confidence score.
   - **Supported by Current System**: **No**. TotalSegmentator does not perform generalized internal lesion screening or nodule detection across organs in standard mode.
   - **Role in Pipeline**: Acts as an optional region-proposal filter to trigger detailed segmentation.

3. **Tumor / Lesion Segmentation**:
   - **Definition**: Produces a voxel-level binary or multi-class mask separating viable tumor tissue, necrotic regions, and fluid-filled cysts from healthy surrounding organ parenchyma.
   - **Supported by Current System**: **No**. Requires dedicated deep learning models trained on contrast-enhanced CT scans with radiologist-verified pathological contours.
   - **Role in Pipeline**: Directly generates the 3D surface mesh (`.obj`) and enables physical volume, margin, and clearance calculations for surgical resection.

4. **Tumor Classification & Characterization**:
   - **Definition**: Predicts histological subtype (e.g., clear-cell vs. papillary renal cell carcinoma), staging (TNM classification), or malignancy grade from radiomic features or deep embeddings.
   - **Supported by Current System**: **Out of Scope**. Automated malignancy grading requires clinical biopsy correlation and extensive clinical validation. Our platform strictly focuses on **morphological and geometric surgical planning**, not automated pathological diagnosis.

---

## 3. Public Dataset Investigation & Comparative Analysis

To train or integrate an abnormality segmentation subsystem, we investigated candidate public datasets from medical imaging challenges and repositories (The Cancer Imaging Archive - TCIA, Grand Challenge, Medical Segmentation Decathlon - MSD).

### 3.1 Candidate Dataset Comparison Matrix

| Feature | Option A: KiTS (Kidney Tumor) | Option B: LiTS (Liver Tumor) | Option C: MSD Lung (Task 06) | Option D: BraTS (Brain Tumor) |
|---|---|---|---|---|
| **Benchmark** | **KiTS19 / KiTS21 / KiTS23** | **LiTS 2017** | **MSD Task 06 (Lung)** | **BraTS 2021 / 2023** |
| **Modality** | Contrast-Enhanced Abdominal CT | Contrast-Enhanced Abdominal CT | Thoracic CT | Multi-parametric MRI (T1, T1c, T2, FLAIR) |
| **Target Anatomy** | Kidneys (Left & Right) | Liver | Lungs & Mediastinum | Brain parenchyma |
| **Pathology** | Renal masses, cysts, RCC | Hepatocellular carcinoma (HCC), metastases | Non-small cell lung cancer (NSCLC) | Glioblastoma, astrocytoma |
| **Annotation Classes** | Kidney parenchyma, renal tumor, renal cyst | Liver, liver lesions | Pulmonary nodule / lung tumor | Enhancing tumor, necrotic core, edema |
| **Sample Size** | 300 (KiTS19) to 489 (KiTS23) scans | 201 CT scans (131 train, 70 test) | 96 CT scans (64 train, 32 test) | 1,251 multi-parametric MRI scans |
| **File Format** | NIfTI (`.nii.gz`) | NIfTI (`.nii.gz`) | NIfTI (`.nii.gz`) | NIfTI (`.nii.gz`) |
| **Voxel Spacing** | Variable axial: 0.5–5.0 mm; in-plane: ~0.8 mm | Variable axial: 0.45–5.0 mm; in-plane: ~0.7 mm | Variable slice thickness | Standardized 1.0 mm isotropic |
| **Access & License** | Open research (CC-BY-NC-SA 4.0 / Grand Challenge) | Open research (TCIA / Grand Challenge) | Open research (CC-BY-SA 4.0) | Open research (TCIA) |
| **Compatibility with Current Pipeline** | **Exceptional (100% match)** | High (100% match) | Moderate (CT, but thoracic focus) | **Low** (MRI requires new loader/preprocessing) |
| **Surgical Relevance** | Nephron-sparing partial nephrectomy planning | Segmental hepatectomy & ablation planning | Video-assisted thoracoscopic surgery | Craniotomy & neuronavigation |

---

## 4. Selection of Initial Target: Renal Tumor (KiTS Benchmark)

### 4.1 Recommendation

We recommend **Renal Tumors (Kidney Masses) based on the KiTS (Kidney and Kidney Tumor Segmentation) benchmark** as the primary target for initial implementation.

### 4.2 Detailed Rationale

1. **Perfect Synergy with Existing TotalSegmentator Output (ROI Prior)**:
   - TotalSegmentator already generates high-fidelity anatomical masks for `kidney_left.nii.gz` and `kidney_right.nii.gz`.
   - By using the kidney mask as a **bounding spatial prior**, the tumor detector only needs to evaluate the cropped renal region-of-interest (ROI).
   - This eliminates false-positive detections in unrelated organs (bowel, spleen, liver) and reduces computational volume by **>90%** (from $512 \times 512 \times 500$ down to approximately $160 \times 160 \times 160$).

2. **Clear Multi-Class Differentiation (Tumor vs. Cyst)**:
   - In kidney CT analysis, distinguishing solid masses from benign fluid-filled cysts is a major practical challenge.
   - KiTS21/23 provides separate, radiologist-verified ground-truth annotations for:
     - Label 1: Normal kidney parenchyma
     - Label 2: Solid tumor / mass
     - Label 3: Fluid cyst
   - This provides structured labels suitable for partial nephrectomy planning.

3. **High Clinical Utility for 3D Surgical Planning**:
   - Urological surgeons evaluate kidney tumors using the **R.E.N.A.L. Nephrometry Score**:
     - **R** (Radius / maximal tumor diameter)
     - **E** (Exophytic / endophytic properties — how deep into the kidney the tumor lies)
     - **N** (Nearness to the renal collecting system or renal sinus)
     - **A** (Anterior / posterior location)
     - **L** (Location relative to the upper/lower polar lines)
   - Visualizing the 3D spatial relationship between the translucent kidney parenchyma and the opaque tumor mass directly supports preoperative surgical planning.

4. **Standardized NIfTI Format**:
   - KiTS uses standard NIfTI (`.nii.gz`) format with DICOM physical affine transformations, natively matching our `ai_segmenter.py`, `mesh_generator.py`, and `measurement_engine.py`.

---

## 5. Model Approaches & Technical Comparison

### 5.1 Evaluated Architecture Paradigms

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      EVALUATED SEGMENTATION PARADIGMS                       │
├─────────────────────────┬─────────────────────────┬─────────────────────────┤
│ Architecture            │ Strengths               │ Limitations             │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ 2D Slice-by-Slice CNN   │ • Fast training         │ • Loses 3D z-axis       │
│ (Standard 2D U-Net)     │ • Low GPU VRAM usage    │   continuity            │
│                         │ • High in-plane res     │ • Severe step-artifacts │
│                         │                         │   in 3D Marching Cubes  │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ 3D Volumetric U-Net     │ • True 3D context       │ • High GPU memory       │
│ (Vanilla 3D U-Net)      │ • Smooth 3D surface     │   demand                │
│                         │   reconstruction        │ • Requires patch-based  │
│                         │ • Preserves voxel ratio │   sliding window        │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ nnU-Net                 │ • State-of-the-art Dice │ • Complex multi-stage   │
│ (Self-configuring)      │   scores across KiTS    │   training harness      │
│                         │ • Robust heuristics     │ • Heavy inference chain │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ MONAI SegResNet /       │ • PyTorch native        │ • Requires tuned        │
│ DynUNet (Pretrained)    │ • Pretrained weights    │   intensity transforms  │
│                         │   available in Model Zoo│   for specific phases   │
│                         │ • Clean modular pipeline│                         │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

### 5.2 Recommended Implementation Approach

For our research prototype, the recommended approach is a **MONAI-based 3D SegResNet / DynUNet model** using an **ROI-anchored inference strategy**:

1. **Why not 2D CNN?**: Marching Cubes generates jagged, disjointed surface meshes from 2D slice-by-slice segmentations due to inter-slice discontinuity. Surgical 3D planning requires true 3D spatial coherence.
2. **Why MONAI SegResNet?**:
   - Directly integrates with PyTorch and medical imaging arrays.
   - Provides standardized sliding-window 3D patch inference with Gaussian blending to eliminate boundary seams.
   - Pretrained weights trained on KiTS are openly accessible in the research community for academic inference.

---

## 6. End-to-End Inference Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  PROPOSED LESION DETECTION & MESH PIPELINE                  │
└─────────────────────────────────────────────────────────────────────────────┘

    CT Scan (.nii.gz)
          │
          ▼
┌──────────────────┐
│ TotalSegmentator │  (FastAPI background task)
└──────────────────┘
          │
          ├──► kidney_left.nii.gz & kidney_right.nii.gz
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. ROI EXTRACTION (src/lesions/roi_extractor.py)                            │
│    • Locate bounding box of segmented kidney in physical space              │
│    • Expand bounding box by +20 mm isotropic margin (captures exophytic)    │
│    • Crop original CT scan to the expanded bounding box                     │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. PREPROCESSING & INTENSITY WINDOWING                                      │
│    • Resample ROI to isotropic spacing (1.5 × 1.5 × 1.5 mm)                 │
│    • Window Hounsfield Units: [-150, 250] HU (soft tissue/parenchyma)       │
│    • Normalize intensity: (HU - mean) / std or min-max to [0, 1]           │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. MODEL INFERENCE (src/lesions/detector.py)                                │
│    • 3D SegResNet sliding window inference (patch size: 128³ or 96³)        │
│    • Overlap: 50% with Gaussian blending weights                            │
│    • Output: Multi-channel voxel logits (Background, Normal, Tumor, Cyst)   │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. POSTPROCESSING & SPATIAL RE-ALIGNMENT                                    │
│    • Softmax probability thresholding (p > 0.50)                            │
│    • Connected component analysis: discard clusters < 0.1 cm³ (noise)       │
│    • Invert ROI cropping: re-embed into full-scan coordinate matrix         │
│    • Save lesion binary mask: outputs/cases/<id>/lesions/kidney_tumor.nii.gz│
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ├──► Marching Cubes: outputs/cases/<id>/meshes/kidney_tumor.obj
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. MEASUREMENT ENGINE (src/measurements/)                                   │
│    • Lesion volume (cm³), bounding box (mm), longest diameter (RECIST)      │
│    • Parenchymal clearance margin (minimum distance to renal capsule)       │
│    • Distance to renal vascular pedicle (from aorta/inferior vena cava)     │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
    React 3D Viewer (Translucent Kidney + Opaque Vivid Red Lesion)
```

---

## 7. Integration Architecture & Storage Structure

The lesion detection subsystem must integrate cleanly into the existing pipeline without modifying or breaking existing modules (`ai_segmenter.py`, `mesh_generator.py`, `measurement_engine.py`, `cases.py`).

### 7.1 Proposed File Hierarchy

```
outputs/cases/<case_id>/
├── case.json                      # Case metadata & status
├── input/
│   └── scan.nii.gz                # Original uploaded CT scan
├── segmentation/                  # TotalSegmentator anatomical masks
│   ├── aorta.nii.gz
│   ├── heart.nii.gz
│   ├── kidney_left.nii.gz
│   ├── kidney_right.nii.gz
│   └── liver.nii.gz
├── lesions/                       # NEW: Dedicated lesion outputs
│   ├── kidney_tumor_left.nii.gz   # Binary lesion mask
│   ├── kidney_tumor_prob.nii.gz   # Probability heatmap (optional)
│   └── lesion_metadata.json       # Detection metadata & confidence
├── meshes/                        # 3D Wavefront OBJ models
│   ├── aorta.obj
│   ├── heart.obj
│   ├── kidney_left.obj
│   ├── kidney_right.obj
│   ├── kidney_tumor_left.obj      # NEW: Lesion 3D surface mesh
│   └── liver.obj
└── measurements/
    └── results.json               # Combined anatomical & lesion metrics
```

### 7.2 Non-Breaking Execution Flow

In `src/pipeline/case_processor.py`:
1. Execute `run_segmentation()` (TotalSegmentator) $\rightarrow$ generates organ masks.
2. Execute `process_organ()` for standard organs $\rightarrow$ generates organ OBJ meshes.
3. Check if target organ (e.g. `kidney_left.nii.gz` or `kidney_right.nii.gz`) was detected:
   - If present, execute `detect_lesions(case_id, organ="kidney")`.
   - If a lesion mask is produced, call `generate_mesh_from_mask()` to output `kidney_tumor_left.obj`.
4. Calculate standard organ measurements + lesion measurements $\rightarrow$ save into `measurements/results.json`.
5. Update case status to `"completed"`.

If lesion detection fails or finds no lesion, the case status remains `"completed"` with standard anatomical results intact.

---

## 8. Lesion Measurements & Surgical Metrics

### 8.1 Computational Geometric Metrics

The measurement engine will calculate the following purely mathematical properties:

1. **Physical Volume**:
   $$V_{\text{mask}} = N_{\text{voxels}} \times (s_x \times s_y \times s_z) \quad [\text{mm}^3, \text{cm}^3, \text{mL}]$$
2. **Bounding Box Dimensions**:
   $$D_x = x_{\max} - x_{\min}, \quad D_y = y_{\max} - y_{\min}, \quad D_z = z_{\max} - z_{\min} \quad [\text{mm}]$$
3. **Longest 3D Diameter (RECIST 1.1 Proxy)**:
   - Maximum Euclidean distance between any two vertices on the lesion surface mesh:
     $$D_{\max} = \max_{u, v \in \mathcal{V}} \|u - v\|_2 \quad [\text{mm}]$$
4. **Centroid Coordinates**:
   $$\bar{C} = \frac{1}{N} \sum_{i=1}^N \mathbf{v}_i \quad [X, Y, Z \text{ in patient physical space mm}]$$
5. **Parenchymal Margin (Surgical Clearance)**:
   - Minimum Euclidean distance from the tumor mesh surface to the host organ boundary:
     $$d_{\text{margin}} = \min_{p \in \mathcal{M}_{\text{tumor}}, \, q \in \mathcal{M}_{\text{organ}}} \|p - q\|_2 \quad [\text{mm}]$$
6. **Endophytic vs. Exophytic Ratio**:
   - Percentage of lesion volume enclosed inside the organ parenchyma vs. protruding exteriorly:
     $$\text{Exophytic \%} = \frac{V_{\text{lesion}} - V_{\text{lesion} \cap \text{organ}}}{V_{\text{lesion}}} \times 100\%$$

### 8.2 Boundary Between Computation and Clinical Interpretation

| Metric / Output | Computational Reality (What We Provide) | Forbidden Clinical Claim (What We NEVER State) |
|---|---|---|
| **Volume & Size** | "$V = 24.3\text{ cm}^3$, $D_{\max} = 38.2\text{ mm}$" | "Stage T1a / T1b Renal Cell Carcinoma" |
| **Parenchymal Depth** | "65% of volume internal to renal capsule" | "Exophytic tumor suitable for partial nephrectomy" |
| **Vascular Distance** | "$12.4\text{ mm}$ distance to left renal vein" | "Safe surgical margin without hilum involvement" |
| **Tissue Intensity** | "Mean CT attenuation = $42\text{ HU}$" | "Confirmed solid neoplasm / ruled out simple cyst" |

---

## 9. 3D Web Visualization Design

In the Three.js viewer (`frontend/src/Viewer3D.jsx`):

### 9.1 Visual Rendering Strategy

```
  ┌────────────────────────────────────────────────────────────┐
  │                 3D SURGICAL SCENE COMPOSITION              │
  ├────────────────────────────────────────────────────────────┤
  │                                                            │
  │     (░░░░░░░░░░░░░░░░░░░░░░░)   <-- Normal Kidney Mesh     │
  │     (░░░░░░░░░░░░░░░░░░░░░░░)       Material: Translucent  │
  │     (░░░░░░░┌────────┐░░░░░░)       Opacity: 0.35          │
  │     (░░░░░░░│ ██████ │░░░░░░)       Color: Gold (#FFD700)  │
  │     (░░░░░░░│ ██████ │░░░░░░)       Wireframe: Optional    │
  │     (░░░░░░░└────────┘░░░░░░)                              │
  │     (░░░░░░░░░░░░░░░░░░░░░░░)   <-- Lesion Mesh Overlay    │
  │     (░░░░░░░░░░░░░░░░░░░░░░░)       Material: Solid Opaque │
  │                                     Opacity: 1.0           │
  │                                     Color: Vivid Red       │
  │                                            (#DC2626)       │
  │                                     Glow: Subtle Emissive  │
  └────────────────────────────────────────────────────────────┘
```

1. **Translucent Host Organ**:
   - The host organ (e.g., Left Kidney) is automatically rendered with transparency (`opacity: 0.35`, `transparent: true`, `depthWrite: false`) when a lesion is present.
   - This allows the surgeon to visualize internal tumors directly inside the parenchymal volume.
2. **Vivid High-Contrast Lesion Mesh**:
   - Rendered in solid, high-visibility crimson (`#DC2626`) or amber (`#F97316`) with subtle specular highlights.
3. **Independent UI Toggle**:
   - In `frontend/src/Sidebar.jsx`, the lesion appears with an independent visibility toggle under a dedicated "Pathology / Lesions" section.
4. **Bounding Box & Focus Controls**:
   - Clicking the lesion focuses the 3D camera onto the tumor centroid and outlines its bounding box in a subtle dashed wireframe.

---

## 10. API Specification (Future Endpoints)

The following endpoints are designed for future implementation (Day 9+) and preserve backwards compatibility:

### 10.1 Endpoint Specifications

#### 1. `GET /api/cases/{case_id}/lesions`
- **Description**: Returns all detected lesions, localization coordinates, and status.
- **Response**:
  ```json
  {
    "case_id": "case_abc123",
    "lesions_detected": 1,
    "lesions": [
      {
        "id": "kidney_tumor_left",
        "organ": "kidney_left",
        "type": "renal_mass",
        "confidence": 0.88,
        "mesh_available": true,
        "measurements": {
          "volume_cm3": 24.3,
          "max_diameter_mm": 38.2,
          "margin_to_capsule_mm": 2.1,
          "centroid": [-42.1, -128.5, 84.3]
        }
      }
    ]
  }
  ```

#### 2. `GET /api/cases/{case_id}/meshes/lesion/{lesion_id}`
- **Description**: Serves the 3D surface mesh (`.obj`) of the specified lesion.
- **Response**: `text/plain` stream of Wavefront OBJ data.

#### 3. Extended `GET /api/cases/{case_id}/results`
- **Description**: Backwards-compatible extension of the existing results payload:
  ```json
  {
    "case_id": "case_abc123",
    "status": "completed",
    "organs": { ... },
    "lesions": { ... }
  }
  ```

---

## 11. Medical Safety & Ethical Governance

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STRICT MEDICAL DISCLAIMER                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Non-Diagnostic Prototype: This software is an AI-assisted preoperative  │
│    planning research prototype. It is NOT a medical device and is NOT       │
│    certified for diagnostic or treatment use.                               │
│                                                                             │
│ 2. Algorithmic Nature: All detected lesion boundaries, volumes, and         │
│    spatial metrics are generated algorithmically and are subject to         │
│    imaging artifacts, contrast phase variability, and segmentation errors. │
│                                                                             │
│ 3. Mandatory Human Review: All outputs MUST be reviewed and verified by a   │
│    qualified radiologist, urologist, or board-certified surgeon prior to    │
│    any clinical decision.                                                   │
│                                                                             │
│ 4. No Histopathological Claims: The system cannot confirm or rule out       │
│    malignancy, cancer staging, or histological subtypes.                    │
└─────────────────────────────────────────────────────────────────────────────┘
```
