# Project Progress Report: AI-Assisted Preoperative Planning System

**Document Version:** 1.1  
**Last Updated:** September 2026 (Day 13 Completed)  
**Target Repository:** `medical-surgery-planner`  
**Current Status:** Full-Stack Functional Prototype Active | Genuine KiTS2023 Model Active | Real CT Inference Executed | 41/41 Tests Passed

---

## 1. Executive Summary

The **AI-Assisted Preoperative Planning System** is an end-to-end medical imaging and surgical planning platform. It transforms raw 3D Computed Tomography (CT) scans in NIfTI format (`.nii` / `.nii.gz`) into interactive 3D anatomical reconstructions, quantitative organ volume and clearance metrics, and specialized lesion analysis pipelines for surgical decision support.

The system emphasizes **clinical safety, deterministic reproducibility, and strict medical AI governance**. Synthetic or heuristic lesion predictions are strictly barred from clinical patient records.

---

## 2. High-Level Progress & Capability Matrix

| Subsystem / Capability | Implementation Status | Primary Tech Stack | Key Output Artifacts |
| :--- | :---: | :--- | :--- |
| **NIfTI Data Ingestion & Metadata** | **Completed** | `nibabel`, `numpy` | `ScanMetadata` (spacing, affine, dimensions) |
| **2D Slice Viewer & HU Windowing** | **Completed** | `matplotlib`, `cv2` | Axial viewer with Soft Tissue, Bone, Lung presets |
| **Classical CV & ROI Preprocessing** | **Completed** | `scipy.ndimage`, `cv2` | Gaussian filtering, Canny edges, body ROI cropping |
| **Multi-Organ AI Segmentation** | **Completed** | TotalSegmentator / `ai_segmenter.py` | Multi-class label masks (kidneys, liver, aorta, spleen, etc.) |
| **3D Anatomical Mesh Reconstruction** | **Completed** | `scikit-image`, `trimesh` | Smoothed, decimated `.obj` anatomical meshes |
| **Desktop 3D Interactive Viewer** | **Completed** | `pyvista`, `vtk` | Multi-actor 3D rendering with opacity & clipping |
| **Quantitative Measurements** | **Completed** | `scipy.spatial`, `numpy` | Volumes ($cm^3$), 3D bounding boxes (mm), organ distances |
| **Web 3D Interactive Viewer** | **Completed** | React 18, Three.js, R3F | Client-side 3D rendering, organ toggles, orbital controls |
| **FastAPI Backend REST Bridge** | **Completed** | FastAPI, `uvicorn`, BackgroundTasks | Async upload, task polling, mesh streaming, JSON metrics |
| **Full-Stack End-to-End Integration** | **Completed** | Vite + React $\leftrightarrow$ FastAPI | Live CT upload $\to$ background processing $\to$ 3D visualizer |
| **Renal Lesion Pipeline (KiTS)** | **Completed** | PyTorch, `dynamic_network_architectures` | Bounding ROI, HU windowing/z-score, inverse coordinate mapping |
| **Model Weights Verification (KiTS23)** | **Completed & Active** | KiTS23 2nd-place nnU-Net v2 | 1001 epochs, 88.62M params, 4 classes, 0 missing keys |
| **Automated Verification Suite** | **Active (100% Pass)** | `pytest` (41 tests) | 41 passed, 0 skipped, 0 failed |

---

## 3. Chronological Milestone & Day-by-Day Breakdown

### Phase A: Foundational Medical Imaging & Classical CV (Milestones 1–4)

* **Milestone 1 — Medical Imaging Foundations**:
  * Established project structure, virtual environment, and dependency management.
  * Implemented `src/loaders/nii_loader.py` to ingest 3D CT volumes and extract orientation matrices, affine transforms, and physical voxel spacings.
  * Created structured `ScanMetadata` dataclass for downstream validation.

* **Milestone 2 — 2D Interactive CT Viewer & Hounsfield Windowing**:
  * Implemented slice-by-slice axial navigation with keyboard arrows and mouse wheel scrolling.
  * Formulated clinically accurate Hounsfield Unit (HU) windowing functions (`window_transform`) with standard radiology presets:
    * Soft Tissue: $W: 400, L: 50$
    * Bone: $W: 1800, L: 400$
    * Lung: $W: 1500, L: -600$

* **Milestone 3 — Classical Image Filtering & Morphology**:
  * Implemented Min-Max intensity normalization and histogram analysis.
  * Built noise-reduction pipelines via Gaussian filtering, morphological operations (dilation, erosion, opening, closing), and connected component labeling to extract foreground body mass.

* **Milestone 4 — Edge Detection, Contours & Patient ROI Localization**:
  * Compared Sobel gradient filtering against OpenCV Canny edge detection.
  * Implemented contour detection and contour hierarchy analysis (`cv2.findContours`).
  * Automated bounding rectangle calculation (`cv2.boundingRect`) to isolate patient anatomy from empty scanner air, reducing unnecessary downstream computational load.

---

### Phase B: Modern 3D Reconstruction & Interactive Visualization (Days 1–5)

* **Day 1 — Multi-Organ AI Segmentation Engine**:
  * Integrated modern deep learning segmentation pipeline (`src/segmentation/ai_segmenter.py`) replacing experimental toy prototypes.
  * Created clean interfaces to invoke multi-organ segmentation (Kidneys, Liver, Spleen, Aorta, IVC, Pancreas) yielding anatomically separated binary masks.

* **Day 2 — 3D Anatomical Mesh Reconstruction**:
  * Created `src/mesh/mesh_generator.py` converting discrete voxel masks into continuous 3D triangle surfaces using the **Marching Cubes** algorithm (`skimage.measure.marching_cubes`).
  * Applied spatial voxel scaling matrix matching patient physical coordinates (in millimeters).
  * Incorporated Laplacian smoothing and quadric decimation via `trimesh` to generate clean, lightweight Wavefront `.obj` meshes for real-time graphics engines.

* **Day 3 — Desktop 3D Anatomy Viewer**:
  * Created `src/visualization/mesh_viewer.py` using PyVista/VTK.
  * Enabled multi-organ mesh display with anatomically tailored color palettes (Kidney: red/brown, Liver: dark amber, Spleen: purple, Aorta: bright red).
  * Implemented opacity sliders, organ visibility toggles, interactive camera rotation, and anatomical cross-section clipping planes.

* **Day 4 — Quantitative Anatomical Measurements**:
  * Developed `src/measurements/measurer.py` for physical metrics extraction:
    * **Volume ($cm^3$ / mL)**: Computed both via voxel-counting ($N \times V_x \times V_y \times V_z$) and surface mesh divergence theorem.
    * **3D Bounding Dimensions**: Calculated physical extents ($X, Y, Z$ in mm) along anatomical axes (Left-Right, Anterior-Posterior, Superior-Inferior).
    * **Spatial Euclidean Clearances**: Minimum distance between anatomical structures (e.g., tumor to renal artery/aorta).

* **Day 5 — Web-Based 3D Visualizer (Three.js & React)**:
  * Built a browser-based visualization application under `frontend/` utilizing Vite, React 18, Three.js, and `@react-three/fiber`.
  * Integrated OrbitControls, ambient/directional lighting, dynamic OBJ loading, and interactive organ visibility and transparency controls in a dark-mode clinical UI.

---

### Phase C: Full-Stack Integration & Case Processing (Days 6–7)

* **Day 6 — FastAPI Backend Bridge & Case Processor**:
  * Built asynchronous REST API (`src/api/app.py`) powered by FastAPI.
  * Implemented `src/pipeline/case_processor.py` orchestrating end-to-end case pipelines (Upload $\to$ Preprocess $\to$ AI Segment $\to$ Generate Meshes $\to$ Extract Measurements).
  * Structured filesystem storage under `outputs/cases/<case_id>/`:
    * `scan.nii.gz` (raw scan)
    * `meshes/<organ>.obj` (3D models)
    * `measurements.json` (computed clinical metrics)
    * `status.json` (progress state)
  * Endpoints implemented:
    * `POST /api/upload`: CT scan upload with MIME & extension validation.
    * `GET /api/case/{id}/status`: Real-time status polling (`processing`, `ready`, `failed`).
    * `GET /api/case/{id}/results`: JSON payload of metadata and organ measurements.
    * `GET /api/case/{id}/mesh/{organ}`: Direct streaming of `.obj` files to frontend.

* **Day 7 — Live Frontend-Backend Integration**:
  * Connected React frontend to FastAPI backend (`frontend/src/services/api.js`).
  * Created state-driven UI managing upload progress, background polling, and automated 3D mesh loading upon case readiness.
  * Added error boundaries, toast alerts, client-side validation, and measurement sidebars.

---

### Phase D: Specialized Renal Lesion Detection & nnU-Net Infrastructure (Days 8–12)

* **Day 8 — Tumor/Lesion Detection Research & Clinical Architecture**:
  * Researched public benchmarks (KiTS21/KiTS23, LiTS, MSD). Selected **Renal Tumors (KiTS)** as initial primary target due to clinical significance in nephron-sparing partial nephrectomies.
  * Established the **Two-Stage Cascade Architecture**: Stage 1 (TotalSegmentator) segments kidneys; Stage 2 crops renal bounding box and predicts parenchyma vs. tumor vs. cyst.
  * Formulated strict medical AI safety governance: zero tolerance for synthetic masks or hallucinated lesions.

* **Day 9 — Renal Lesion Pipeline Foundation**:
  * Implemented `src/lesions/roi_extractor.py`: Isolates kidney bounding boxes with configurable physical safety margins (default: 15 mm).
  * Implemented `src/lesions/lesion_inference.py`: Preprocessing with standard soft-tissue windowing and physical normalization; `LesionInferenceEngine` abstraction.
  * Implemented `src/lesions/postprocessing.py`: Connected-component filtering and coordinate inverse mapping to reconstruct cropped lesion masks back into the patient's global 3D NIfTI coordinate space.
  * Established 24 automated unit tests verifying coordinate integrity and boundary clamping.

* **Day 10 — Validated Model Engine & Safety Configuration**:
  * Evaluated official candidate models: KiTS21 nnU-Net, MONAI CECT, MONAI UNEST.
  * Configured dynamic environment loading via `LESION_MODEL_PATH` and `LESION_MODEL_TYPE`.
  * Enforced strict safety enforcer: pipeline refuses execution and throws explicit errors if model weights are unconfigured, avoiding unverified fallbacks.
  * Expanded test suite to 28 passing tests.

* **Day 11 — KiTS21/KiTS23 Architecture Reconstruction & Forensic Audit**:
  * Reconstructed exact `PlainConvUNet` architecture via `dynamic_network_architectures` matching KiTS21 nnU-Net v2 specifications.
  * Implemented `preprocess_ct_roi_nnunet_zscore` matching KiTS21 foreground statistics (clip `[-62.0, 310.0]` HU, mean `104.94`, std `75.30`).
  * Inspected local `weights/kits21/` files:
    * `plans.pkl`: Verified nnU-Net v1 plans structure.
    * `model_final_checkpoint.model.pkl`: Identified as v1 trainer metadata header, not neural network weights.
  * Automated test suite expanded to 38 tests (37 passing, 1 skipped).

* **Day 12 — Genuine KiTS Checkpoint Audit & Acquisition Investigation**:
  * Conducted forensic byte-level inspection of `weights/kits21/model_final_checkpoint.tmp` (120.26 MB). Identified truncated zip archive missing central directory (`PK\x05\x06`).
  * Traced origin to Zenodo Record 5126443 (`Task135_KiTS2021.zip`, 221.7 MB compressed / 238.25 MB uncompressed).
  * Diagnosed access barrier: Zenodo automated firewall returns HTTP 403 Forbidden ("Access to this resource has been restricted due to unusual traffic from your network").
  * **Strict Safety Stop Condition Triggered**: Per clinical engineering rules, Day 12 safely halted. No fake weights were created, no synthetic lesion masks were written, and unit tests cleanly skip real inference until an intact checkpoint is mounted.

* **Day 13 — KiTS2023 Checkpoint Verification, Real CT Inference & 3D Lesion Reconstruction**:
  * Extracted and verified complete 1.39 GB `pretrained_models.tar.xz` from the KiTS2023 2nd-place challenge team (`khuhm/KiTS23-2nd-place`, Springer LNCS proceedings).
  * Forensically verified `weights/kits23/checkpoint_final.pth` (250,183,291 bytes, SHA-256: `0bff109e2ba5a9764e12028d338b66107518a881a8ba39746102d8fd8708fa58`):
    * 1001 training epochs, 88.62M total checkpoint parameters (31.20M inference parameters).
    * Architecture: 6-stage `PlainConvUNet` via `dynamic_network_architectures` (0 missing keys, 0 unexpected keys).
    * 4-class label mapping: 0=background, 1=kidney, 2=tumor, 3=cyst.
  * Executed genuine CPU inference on the project's real patient CT scan (`datasets/raw/ct/ct_15mm_defaced.nii`, $293 \times 293 \times 344$):
    * Sub-2-second CPU inference: Left kidney in 1.825s, Right kidney in 1.802s.
    * Tumor mass probability $< 1.0\%$ across both kidneys (0 confident tumor voxels; negative finding recorded truthfully with zero synthetic fabrication).
    * Benign renal cyst detected on left kidney (91 voxels, 0.3071 mL, max probability 99.89%).
  * Reconstructed physical 3D surface mesh (`cyst_left.obj`, 146 vertices, 288 faces) using Marching Cubes and embedded full-space NIfTI mask (`cyst_left.nii.gz`).
  * Stored provenance audit payload (`provenance.json`).
  * All 41 unit tests in `pytest tests/ -v` pass cleanly (100% passing, 0 skipped, 0 failed).

---

## 4. Codebase & Directory Structure

```text
medical-surgery-planner/
├── docs/                        # Complete technical and daily documentation
│   ├── DAY1.md ... DAY13.md     # Daily milestone execution logs
│   ├── PROJECT_STATUS.md        # Architecture & execution summary
│   ├── PROGRESS.md              # Consolidated project progress report (This Document)
│   ├── 3D_VIEWER.md             # Desktop viewer design
│   ├── API_ARCHITECTURE.md      # FastAPI backend specifications
│   ├── MEASUREMENTS.md          # Volumetric and geometric calculation theory
│   ├── MESH_GENERATION.md       # Marching cubes & surface extraction docs
│   ├── TUMOR_DETECTION.md       # Renal tumor benchmark & architecture analysis
│   └── WEB_VIEWER.md            # React + Three.js frontend specifications
├── frontend/                    # Web application (Vite + React + Three.js)
│   ├── src/
│   │   ├── components/          # Canvas3D, ControlsPanel, InfoPanel, UploadModal
│   │   ├── services/            # api.js (Axios REST client)
│   │   ├── App.jsx              # Main dashboard state machine
│   │   └── main.jsx             # Entry point
│   └── package.json             # Frontend dependencies
├── outputs/cases/               # Case outputs & processed patient data
│   └── b2f89382-9416-4e94-9486-b00c6b1de64b/
│       ├── lesions/             # cyst_left.nii.gz, provenance.json
│       └── meshes/              # liver, heart, aorta, kidney_left, cyst_left.obj
├── src/                         # Python backend and processing core
│   ├── api/                     # FastAPI application & route endpoints
│   ├── lesions/                 # Specialized KiTS renal lesion pipeline
│   │   ├── roi_extractor.py     # Physical-margin 3D bounding box extraction
│   │   ├── lesion_inference.py  # nnU-Net v2 network builder & preprocessing
│   │   └── postprocessing.py    # Connected components & coordinate inverse mapping
│   ├── loaders/                 # NIfTI CT scan ingestion (`nii_loader.py`)
│   ├── measurements/            # Organ & tumor measurement engine (`measurer.py`)
│   ├── mesh/                    # Marching cubes & OBJ surface generation (`mesh_generator.py`)
│   ├── pipeline/                # End-to-end case orchestration (`case_processor.py`)
│   ├── preprocessing/           # Classical HU windowing, filtering, and contours
│   ├── segmentation/            # AI segmentation integration (`ai_segmenter.py`)
│   └── visualization/           # Desktop PyVista/VTK viewer (`mesh_viewer.py`)
├── tests/                       # Automated test suite
│   ├── test_api.py              # API endpoint & serialization tests
│   ├── test_lesions.py          # ROI, normalization, coordinate mapping & network tests
│   └── test_measurements.py     # Volume & geometric clearance tests
├── weights/                     # Pretrained neural network checkpoints
│   ├── kits21/                  # Legacy KiTS21 plans & audit artifacts
│   └── kits23/                  # Verified KiTS23 3D fullres checkpoint & plans
└── requirements.txt             # Backend Python dependencies
```

---

## 5. Verification & Test Suite Status

The project maintains a comprehensive automated testing suite executed via `pytest`:

```powershell
python -m pytest tests/ -v
```

* **Total Tests Collected:** 41
* **Passed:** 41 (100% pass rate)
* **Skipped:** 0
* **Failed:** 0

### Validated Areas:
1. **API Endpoints**: Health checks, upload validation, status transitions, JSON serialization of NumPy types, multi-organ and lesion mesh streaming.
2. **Measurement Calculations**: Mask volume vs. mesh volume equivalence, 3D bounding box correctness, Euclidean distance calculations.
3. **Lesion Pipeline**:
   - Voxel-to-physical margin conversion.
   - Volume boundary clamping (no out-of-bounds indexing).
   - Windowing and z-score intensity normalization (`preprocess_ct_roi_nnunet_zscore`).
   - Dynamic downsampling-aware spatial padding (InstanceNorm3d 6-stage protection).
   - Multiclass probability output (`predict_all_probabilities`) and argmax discrete classification (`predict_classes`).
   - Connected component noise removal and full 3D inverse coordinate mapping back into original CT space.
   - Real trained KiTS2023 checkpoint loading and CPU forward-pass execution.

---

## 6. Active Blockers & Next Immediate Steps

### Active Blockers:
* **None**: Model checkpoint verified, extracted, loaded, and operating at sub-2-second CPU latency.

### Next Immediate Steps (Day 14):
1. **Surgical Clearance Calculation Engine**:
   - Compute minimum 3D Euclidean distances between detected lesion boundaries (tumor/cyst) and critical vascular structures (aorta, renal artery, renal vein) and renal pelvis.
2. **Interactive 3D Lesion Visualization**:
   - Update React/Three.js frontend controls to render detected lesion meshes with clinical shader transparency (translucent amber for tumor, cyan/blue for cyst).
   - Display real-time surgical clearance metrics directly in the InfoPanel.

---

## 7. Medical Safety & Clinical Governance

* **Investigational Use Only**: This software is an engineering prototype designed for research and educational preoperative planning. It is not FDA/CE cleared as a primary diagnostic device.
* **Human-in-the-Loop Review**: All segmentations, 3D meshes, and quantitative measurements must be verified by a board-certified radiologist or surgical specialist before any operative procedure.
* **Zero-Hallucination Policy**: The system strictly prohibits synthetic, heuristic, or dummy masks in patient files when neural network inference is unavailable.
