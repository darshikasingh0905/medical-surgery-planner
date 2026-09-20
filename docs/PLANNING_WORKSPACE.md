# Preoperative Planning Workspace Architecture

> **Governance Statement**: The workspace aggregates computational imaging outputs, measurements,
> anatomical relationships, and user-entered planning information. It does not determine surgical
> risk or recommend an operative approach.


The **Preoperative Planning Workspace** is a unified, product-facing workstation interface designed for AI-assisted preoperative surgical planning. It integrates multimodal case data into a single coherent environment:
- **Case & Patient Context**: Metadata, scan dimensions, voxel spacing, and acquisition parameters.
- **Model-Predicted Findings**: Segmentations from KiTS23-trained models (`model_cyst_left`), volumes, and morphological properties.
- **Relevant Anatomical Structures**: Interactive structure catalog with segmentation status, mesh rendering, and color coding.
- **Spatial Relationships & Clearances**: Real-time computational distance fields between lesions and critical structures (e.g., renal vein, renal artery, aorta, IVC).
- **Preoperative Planning Targets**: 3D and MPR cross-referenced surgical markers.
- **Preoperative Measurements**: Linear distances, margins, volumes, and geometric clearances.
- **Synchronized Visualizers**: Dual-mode viewport hosting synchronized 3D Three.js anatomical scene and multi-planar reformatting (MPR) axial/coronal/sagittal slices.
- **Persistent Planning Session State**: Surgical approach annotations, complexity notes, access trajectories, risk checklist, and user-editable planning notes persisted atomically.

> **CRITICAL MEDICAL DISCLAIMER**:
> This software is an educational and research prototype for computational preoperative visualization and planning support. It does NOT make autonomous surgical decisions, prescribe an operative approach, diagnose malignancy, determine oncologic staging, or claim clinical validity. All computational metrics and candidate classifications must be verified by certified clinicians.

---

## 2. System Architecture

```
+-------------------------------------------------------------------------------+
|                             FastAPI Backend                                  |
|                                                                               |
|  +--------------------------------+   +-------------------------------------+  |
|  |     PlanningSessionService     |   |       PlanningSummaryService        |  |
|  |  - Atomic session persistence  |   |  - Read-only data aggregator        |  |
|  |  - JSON schema validation      |   |  - Scan, Anatomy, Findings, Rel.    |  |
|  |  - Graceful corrupt recovery   |   |  - Targets, Measurements, Session   |  |
|  +--------------------------------+   +-------------------------------------+  |
|                  |                                       |                    |
|  Outputs: outputs/cases/<id>/planning/planning_session.json                   |
+-------------------------------------------------------------------------------+
                                      |  REST API
                                      v
+-------------------------------------------------------------------------------+
|                             React Frontend                                    |
|                                                                               |
|  +-------------------------------------------------------------------------+  |
|  | Workspace Header: Case ID, Status, Spacing, Modality, Quick Presets     |  |
|  +-------------------------------------------------------------------------+  |
|  | Left Column          | Center Column             | Right Column         |  |
|  | (Clinical Context)   | (Synchronized Viewers)    | (Inspector & Targets)|  |
|  |                      |                           |                      |  |
|  | - Findings List      | - 3D Anatomy (Three.js)   | - Finding Inspector  |  |
|  | - Anatomy Registry   | - 2D MPR (Ax/Cor/Sag)     | - Targets List       |  |
|  | - Spatial Distances  | - Split / Maximized Mode  | - Measurements List  |  |
|  | - Planning Session   | - Crosshair Sync          | - Risk Assessment    |  |
|  |   Notes & Risk Tags  | - Slice Sliders           | - Export Plan        |  |
|  +-------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------+
```

---

## 3. Backend Endpoints

### 1. `GET /api/cases/{case_id}/planning/summary`
Returns the consolidated planning aggregate:
```json
{
  "case_id": "b2f89382-9416-4e94-9486-b00c6b1de64b",
  "status": "ready",
  "scan_info": {
    "shape": [293, 293, 344],
    "voxel_spacing_mm": [1.5, 1.5, 1.5],
    "orientation": ["R", "A", "S"]
  },
  "findings": [
    {
      "lesion_id": "cyst_left",
      "class_name": "cyst",
      "volume_ml": 0.3071,
      "dimensions_mm": [8.5, 9.2, 7.8],
      "host_organ": "kidney_left"
    }
  ],
  "anatomy": [...],
  "spatial_relationships": [...],
  "targets": [...],
  "measurements": [...],
  "session": { ... },
  "safety_disclaimer": "..."
}
```

### 2. `GET /api/cases/{case_id}/planning/session`
Retrieves current user planning session state or returns a default session if uninitialized.

### 3. `PUT /api/cases/{case_id}/planning/session`
Updates session state partially or completely using atomic JSON file replacement (`planning_session.json.tmp` -> `planning_session.json`).

### 4. `POST /api/cases/{case_id}/planning/session/reset`
Resets the session state back to clean defaults for the case.

---

## 4. Frontend Component Breakdown

1. **`PlanningWorkspace.jsx`**:
   - Workstation shell managing viewport mode (`split`, `3d`, `mpr`), active finding selection, target crosshair navigation, and session debounced auto-saving.
2. **`Viewer3D.jsx`**:
   - WebGL Three.js renderer displaying segmented organ meshes, lesion volumes, target markers, and slice clipping planes.
3. **`MPRViewer.jsx`**:
   - High-performance canvas-based multiplanar reformatted orthogonal slices with synchronized coordinate crosshairs.
4. **`PlanningSessionPanel`**:
   - Integrated tab inside the workspace for setting planned approach, target anatomy, risk factors, and freeform clinical notes.
