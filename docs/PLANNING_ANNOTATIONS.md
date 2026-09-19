# Preoperative Surgical Target Annotation & Planning Marker Layer

## 1. Overview & Architectural Scope

The **Planning Marker & Target Annotation Layer** provides a unified computational representation for spatial targets in preoperative surgical analysis. It bridges two distinct categories of surgical interest:
1. **Computational Model Findings (`source: "model"`)**: Automatically exposed from upstream inference pipelines (such as KiTS23 renal lesion segmentation `cyst_left`), carrying provenance, volumetric calculations, and parenchymal boundary distances.
2. **User-Defined Planning Annotations (`source: "user"`)**: Clinician- or researcher-created reference markers placed directly on 2D Multi-Planar Reconstruction (Axial, Coronal, Sagittal) slices or 3D mesh views.

```
                  ┌──────────────────────────────────────────────┐
                  │              CT Scan Volume                  │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   ┌───────────────────────────┐                   ┌───────────────────────────┐
   │ TotalSegmentator Anatomy  │                   │ KiTS23 Lesion Inference   │
   │ (Parenchyma, Aorta, IVC)  │                   │ (cyst_left, tumor_left)   │
   └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                 │                                               │
                 │                                               ▼
                 │                               ┌───────────────────────────┐
                 │                               │ Model Planning Targets    │
                 │                               │ (source: "model")         │
                 │                               └───────────────┬───────────┘
                 │                                               │
                 ▼                                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Unified Planning Target Registry                         │
│                    (src/planning/planning_targets.py)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  • target_id, target_type, label, source, voxel_coord, physical_coord       │
│  • lesion_id, structure_id, notes, created_at, volume_ml, dimensions_mm    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
│   MPR Viewer    │           │  3D Three.js    │           │ Planning Target │
│ (Crosshair Sync)│           │ (Physical Mesh) │           │     Sidebar     │
└─────────────────┘           └─────────────────┘           └─────────────────┘
```

---

## 2. Clinical Governance & Safety Boundaries

> [!CAUTION]
> **Educational and Research Prototype Notice**:
> This software is an engineering research prototype designed to demonstrate multi-modal anatomical visualization and computational target registration.
>
> 1. **Not an Autonomous Surgical System**: Planning markers and targets do NOT infer safe resection margins, surgical access trajectories, or clinical resectability.
> 2. **Standardized Terminology**: All automated detections are strictly identified as "model-predicted cyst-class segmentations" or "model-predicted lesions". Terms such as "confirmed cancer", "safe margin", or "optimal resection line" are strictly avoided.
> 3. **Clinical Review Mandatory**: All coordinates and measurements are purely geometric approximations derived from discretized CT voxels and require direct clinical validation.

---

## 3. Coordinate Systems & Dual Space Representation

To ensure sub-millimeter registration across 2D orthogonal radiological slices and 3D surface meshes, each planning target stores both:
1. **Voxel Coordinate (`[x, y, z]` integer)**:
   - Index in the 3D CT matrix: $0 \le x < N_x$, $0 \le y < N_y$, $0 \le z < N_z$.
   - Drives slice selection ($z$ for Axial, $y$ for Coronal, $x$ for Sagittal) and 2D pixel crosshairs.
2. **Physical Coordinate (`[x_{mm}, y_{mm}, z_{mm}]` float)**:
   - Origin-relative millimeter coordinates in patient space:
     $$p = [x \cdot s_x, \; y \cdot s_y, \; z \cdot s_z]$$
   - Matches the continuous Marching Cubes 3D surface mesh vertex coordinate system.

### Transformations Between Coordinate Frames:

| Source Space | Target Space | Formula | Module Reference |
| :--- | :--- | :--- | :--- |
| Voxel $[x, y, z]$ | Physical mm $[x_p, y_p, z_p]$ | $[x \cdot s_x, y \cdot s_y, z \cdot s_z]$ | `src.visualization.mpr.voxel_to_physical` |
| Physical mm $[x_p, y_p, z_p]$ | Voxel $[x, y, z]$ | $[\text{round}(x_p / s_x), \text{round}(y_p / s_y), \text{round}(z_p / s_z)]$ | `src.visualization.mpr.physical_to_voxel` |
| Voxel $[x, y, z]$ | Axial Display $(u, v)$ | $u = (N_x - 1) - x, \quad v = (N_y - 1) - y$ | `voxel_to_display_crosshair("axial")` |
| Axial Display $(u, v)$ | Voxel $[x, y, z]$ | $x = (N_x - 1) - u, \quad y = (N_y - 1) - v, \quad z = \text{slice}$ | `display_to_voxel_crosshair("axial")` |
| Voxel $[x, y, z]$ | Coronal Display $(u, v)$ | $u = (N_x - 1) - x, \quad v = (N_z - 1) - z$ | `voxel_to_display_crosshair("coronal")` |
| Voxel $[x, y, z]$ | Sagittal Display $(u, v)$ | $u = (N_y - 1) - y, \quad v = (N_z - 1) - z$ | `voxel_to_display_crosshair("sagittal")` |
| Physical $[x, y, z]$ | Three.js Scene $(X, Y, Z)$ | Group rotation $[-\pi/2, 0, 0] \implies [x, z, -y]$ | `Viewer3D.jsx` scene orientation |

---

## 4. REST API Specification

All planning endpoints are nested under `/api/cases/{case_id}/planning`:

### `GET /api/cases/{case_id}/planning/targets`
Retrieves all active targets (model findings + user annotations).
- **Response**:
```json
{
  "case_id": "b2f89382-9416-4e94-9486-b00c6b1de64b",
  "total_targets": 2,
  "model_findings_count": 1,
  "user_annotations_count": 1,
  "targets": [
    {
      "target_id": "model_cyst_left",
      "target_type": "lesion",
      "label": "Model-predicted cyst-class segmentation (KiTS23 class 3)",
      "source": "model",
      "voxel_coordinate": [110, 89, 218],
      "physical_coordinate": [164.868, 133.104, 327.363],
      "lesion_id": "cyst_left",
      "structure_id": "kidney_left",
      "volume_ml": 0.3071,
      "dimensions_mm": [7.5, 9.0, 9.0],
      "computational_interpretation": "Model-predicted cyst-class segmentation (KiTS23 class 3)",
      "host_organ": "kidney_left",
      "created_at": "2026-09-19T10:45:00Z"
    }
  ],
  "safety_disclaimer": "..."
}
```

### `GET /api/cases/{case_id}/planning/annotations`
Retrieves user-created annotations only.

### `POST /api/cases/{case_id}/planning/annotations`
Creates a user annotation with volume bounds checking.
- **Request Body**:
```json
{
  "label": "Biopsy Entry Trajectory",
  "target_type": "custom_point",
  "voxel_coordinate": [100, 110, 120],
  "notes": "Planning reference marker"
}
```
- **Status**: `201 Created` (or `400 Bad Request` if coordinates are out-of-bounds).

### `PUT /api/cases/{case_id}/planning/annotations/{annotation_id}`
Updates label, notes, or coordinates of an existing user annotation.

### `DELETE /api/cases/{case_id}/planning/annotations/{annotation_id}`
Permanently deletes a user annotation.

### `POST /api/cases/{case_id}/planning/annotations/from-lesion/{lesion_id}`
Creates a user-focused planning annotation anchored to the exact centroid of an existing model-predicted lesion finding.

---

## 5. Persistence Architecture

User annotations are persisted inside the case directory:
`outputs/cases/<case_id>/planning/annotations.json`

- **Schema Isolation**: Stored independently of raw input NIfTI scans and segmentation masks, eliminating risks of overwriting or modifying original imaging data.
- **Atomic File Writing**: Written via temporary `.tmp` files and atomic rename to prevent corruption during concurrent requests or power interruption.
- **Persistence Across Sessions**: When a case is reloaded, the backend re-hydrates user annotations and merges them with automated model findings.

---

## 6. Interactive UX & Synchronization

1. **Click-to-Annotate Mode**:
   - Explicit toggle prevents accidental point placement during standard crosshair navigation.
   - Active banner indicates: `Annotation Mode Active: Click on any CT slice to place a surgical planning reference point.`
2. **Cross-Plane Projection**:
   - Markers render on the slice corresponding to their coordinate. If the user scrolls within $\pm 2$ slices, the marker remains visible with proportional opacity decay.
3. **Synchronized 3D Camera & MPR Jump**:
   - Clicking `Focus` (🎯) on any target in the sidebar simultaneously pans the 3D camera to target coordinates and jumps the MPR slices ($vz, vy, vx$) directly to the target center.
