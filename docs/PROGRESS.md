# Project Progress Report: AI-Assisted Preoperative Planning System

**Document Version:** 1.6  
**Last Updated:** September 2026 (Day 18 Completed)  
**Target Repository:** `medical-surgery-planner`  
**Current Status:** Full-Stack Preoperative Planning Interface Active | Multi-Planar Reconstruction (MPR) Synchronized | Surgical Planning Markers Active | Preoperative Measurement & 3D Surgical Geometry Layer Active | Genuine KiTS2023 Model Active | Real CT Inference Validated | 166/166 Backend Tests Passed | Vite Build Clean (0 errors)


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
| **Surgical Spatial Metrics Engine** | **Completed** | `scipy.spatial.cKDTree`, `nibabel` | Physical volume, bounding box, centroid, min Euclidean distances (mm) |
| **Live 3D Lesion Visualization** | **Completed** | React 18, Three.js, R3F | Lesion mesh rendering, opacity slider, focus camera, distances in InfoPanel |
| **Lesion REST API Endpoints** | **Completed** | FastAPI | `GET /lesions`, `GET /lesions/{id}` with cached + dynamic metrics |
| **Multi-Planar Reconstruction (MPR)** | **Completed** | NumPy, Pillow, FastAPI | Sub-millisecond Axial/Coronal/Sagittal streaming, HU windowing, synchronized crosshairs |
| **Planning Markers & Annotation Layer**| **Completed** | FastAPI, React, Three.js | Unified target model, atomic JSON persistence, 2D/3D synchronized markers, click-to-annotate UX |
| **Automated Verification Suite** | **Active (100% Pass)** | `pytest` (152 tests) | 152 passed, 0 skipped, 0 failed |

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
    * No tumor-class voxels exceeded the segmentation threshold (0.50) across either kidney ROI (max probability < 1.0%; zero synthetic fabrication).
    * Model-predicted cyst-class segmentation in left kidney (91 voxels, 0.3071 mL, max class-3 probability 99.89%, mean 93.7%).
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

## 6. Day 14 Milestone — Surgical Spatial Metrics + Live Lesion 3D Visualization

### Completed:

#### Surgical Spatial Measurement Engine (`src/measurements/lesion_measurements.py`)
- `calculate_lesion_volume`: Physical volume (mm³, cm³, mL) for anisotropic voxels
- `calculate_lesion_bounding_box`: Physical X/Y/Z extent in mm
- `calculate_lesion_centroid`: Voxel, physical, and RAS world centroids
- `calculate_minimum_distance_to_structure`: Exact physical Euclidean distance via `scipy.spatial.cKDTree` in < 0.4 seconds
- Full comprehensive metrics function with graceful unavailable-structure handling

#### Validated on Real KiTS2023 Inference Output
| Metric | Value |
|---|---|
| Volume | 0.3071 mL |
| Dimensions | 7.5 × 9.0 × 9.0 mm |
| Distance to kidney_left capsule | 3.354 mm (inside parenchyma) |
| Distance to aorta | 54.104 mm |
| Distance to IVC | 90.337 mm |

#### REST API (`/lesions` endpoints in `src/api/routes/cases.py`)
- `GET /api/cases/{case_id}/lesions` — returns cached or dynamically computed lesion metrics
- `GET /api/cases/{case_id}/lesions/{lesion_id}` — returns single lesion (404 if not found)

#### React/Three.js Frontend
- `LesionMesh` component with LESION_VISUAL_CONFIG (cyan cyst, amber tumor)
- Lesion panel in Sidebar with visibility toggle and focus 🎯 button
- Opacity slider in header for lesion mesh transparency
- Camera animation on focus (60-frame smooth transition to lesion centroid)
- Host kidney dims to 20% opacity in focus mode
- InfoPanel extended with lesion spatial distances panel

#### Test Suite Expanded: 49/49 passing
- `TestLesionMeasurements`: 5 unit tests (volume, bbox, centroid, distance, comprehensive)
- `test_api.py`: 3 new tests (lesions not-ready, empty, cached results)

### Documentation
- [`docs/DAY14.md`](DAY14.md) — Full Day 14 implementation report
- [`docs/SURGICAL_METRICS.md`](SURGICAL_METRICS.md) — Technical reference for spatial metrics

---

## 7. Day 15 Milestone — Preoperative Anatomy Relationships + Interactive Planning View

### Completed:

#### Anatomical Structure Registry (`src/anatomy/structure_registry.py`)
- Machine-readable structure catalog for renal and abdominal preoperative planning
- Genuine disk-based audit: `inspect_case_structures`, `get_available_structures`, `get_structure_metadata`
- Explicit reporting for unsegmented anatomy: `renal_artery`, `renal_vein`, `renal_pelvis`, `ureter` reported as unavailable with clear explanations (no fake anatomy)
- Available structures verified with true voxel counts and mesh availability: `kidney_left`, `kidney_right`, `aorta`, `inferior_vena_cava`, `adrenal_gland_left`, `adrenal_gland_right`

#### Spatial Relationships Engine (`src/measurements/spatial_relationships.py`)
- `calculate_mask_pair_spatial_relationship`: Computes exact minimum physical Euclidean distance with anisotropic voxel spacing ($dx, dy, dz$)
- Spatial overlap detection: sets `distance_mm = 0.0` and `overlap = True` when masks intersect
- Fast sub-second $k$-d tree nearest-neighbor calculation
- Graceful handling of unsegmented/missing masks: `available = False, distance_mm = None, overlap = None`
- Validated on real case `b2f89382-9416-4e94-9486-b00c6b1de64b` cyst:
  - Left Kidney: 0.00 mm (overlapping)
  - Abdominal Aorta: 54.10 mm
  - Inferior Vena Cava: 90.34 mm
  - Right Kidney: 91.92 mm
  - Left Adrenal Gland: 39.83 mm

#### REST API Enhancements (`src/api/routes/cases.py`)
- `GET /api/cases/{case_id}/structures`: Machine-readable audit of available/unavailable structures
- `GET /api/cases/{case_id}/lesions/{lesion_id}/relationships`: Computational spatial relationships matrix
- `GET /api/cases/{case_id}/meshes/{organ}`: Expanded to serve `inferior_vena_cava`, `kidney_right`, and adrenal meshes

#### Interactive Planning View UI (React 18 / Three.js / R3F)
- View mode switcher: **Normal View** vs **Preoperative Planning View**
- Planning View sidebar with **Anatomical Structures** section:
  - Visibility toggles and focus camera buttons for available structures
  - Explicit disabled notice for unavailable structures (no fake controls)
- Organ transparency and lesion opacity sliders
- Enhanced 3D Viewer (`Viewer3D.jsx`):
  - Dynamic loading of all available structure meshes
  - Structure highlighting and camera focus derived from true mesh bounding box centers
  - In-viewport HUD with floating **Reset View** (🔄) button
- Extended InfoPanel (`InfoPanel.jsx`):
  - Structured **Spatial Relationships** table with Structure, Availability, Min Distance, and Overlap
  - **Case Planning Summary** panel summarizing target, class, volume, organ, and anatomy counts
  - Strict computational governance disclaimers

#### Verification & Test Suite: 65/65 Passing
- Added `tests/test_day15_planning.py` with 16 comprehensive unit tests covering structure registry, anisotropic physical distances, overlap detection, missing mask handling, and API endpoints
- All 49 existing tests continue passing (65 total)
- Frontend production build (`npm run build`) passes cleanly with zero errors

### Documentation
- [`docs/DAY15.md`](DAY15.md) — Full Day 15 milestone report
- [`docs/PREOPERATIVE_PLANNING.md`](PREOPERATIVE_PLANNING.md) — Technical methodology and clinical governance
- [`docs/DAY16.md`](DAY16.md) — Full Day 16 Multi-Planar Reconstruction (MPR) report
- [`docs/DAY17.md`](DAY17.md) — Full Day 17 Surgical Target Annotation & Planning Marker report
- [`docs/PLANNING_ANNOTATIONS.md`](PLANNING_ANNOTATIONS.md) — Planning targets architecture & governance
- [`docs/DAY18.md`](DAY18.md) — Full Day 18 Preoperative Measurement & 3D Surgical Geometry report
- [`docs/PREOPERATIVE_MEASUREMENTS.md`](PREOPERATIVE_MEASUREMENTS.md) — Preoperative geometry calculation & clinical safety guide

---

## 8. Day 18 Milestone: Preoperative Measurement & 3D Surgical Geometry

- **Architecture**: Complete quantitative physical Euclidean distance measurement layer between user points, surgical planning targets, and registered anatomical structure boundaries.
- **Backend Service**: `MeasurementService` in `src/planning/measurement_service.py` with anisotropic voxel spacing calculation, boundary validation, and isolated atomic persistence to `outputs/cases/<case_id>/planning/measurements.json`.
- **FastAPI Endpoints**: 6 dedicated REST endpoints under `/api/cases/{case_id}/planning/measurements`.
- **2D/3D Synchronization**: Two-step MPR slice click workflow (Point A → Point B) with interactive banners, 3D line & endpoint sphere rendering in Three.js, camera navigation, and InfoPanel hero distance display.
- **Quality Assurance**: 166/166 automated backend tests passing (100%), 14 new Day 18 tests, and Vite frontend build 100% clean with 0 errors.

---

## 9. Active Blockers & Next Steps

### Active Blockers:
* **None**

### Future Directions:
1. Automated PDF surgical planning case report generation with embedded MPR slice captures and quantitative clearance tables
2. Multi-point surgical polyline / resection boundary estimation and curved-planar reformation (CPR)
3. Specialized vascular sub-segmentation integration (e.g. TotalSegmentator tissue/vessel models)

---

## 8. Medical Safety & Clinical Governance

* **Investigational Use Only**: This software is an engineering prototype designed for research and educational preoperative planning. It is not FDA/CE cleared as a primary diagnostic device.
* **Human-in-the-Loop Review**: All segmentations, 3D meshes, and quantitative measurements must be verified by a board-certified radiologist or surgical specialist before any operative procedure.
* **Zero-Hallucination Policy**: The system strictly prohibits synthetic, heuristic, or dummy masks in patient files when neural network inference is unavailable.
* **Computational Terminology Policy**: All distances are labeled as "computational minimum distance" or "model-derived spatial distance". Terms such as "safe margin", "resectable", or "surgical clearance" are prohibited in all outputs.
