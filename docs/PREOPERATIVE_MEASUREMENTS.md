# Preoperative Measurement & 3D Surgical Geometry Guide

## 1. Overview & Clinical Governance

The Preoperative Measurement and Surgical Geometry subsystem provides quantitative physical Euclidean distance measurement tools for research, educational, and preoperative planning workflows.

> [!IMPORTANT]
> **Clinical Governance Notice**:
> This software is an educational and research prototype. Preoperative geometric measurements and computational distances represent physical Euclidean measurements between segmented structures or user-selected points. They do **NOT** represent:
> - Autonomous surgical recommendations
> - Clinically verified margins or clearances
> - Recommended resection planes or optimal needle trajectories
> - Surgical decision-making or definitive operative advice
>
> Standardized terminology must be adhered to at all times:
> - **Permitted**: "computational distance", "physical Euclidean measurement", "computational minimum distance", "model-predicted lesion".
> - **Strictly Prohibited**: "safe margin", "recommended clearance", "optimal resection route", "safe resection corridor".

---

## 2. Coordinate Spaces & Geometric Conversions

The system maintains strict mathematical rigor across coordinate representations:

### Coordinate Definitions
1. **Voxel Coordinate Space $[x, y, z]$**:
   Integer grid indices within $[0..N_x-1, 0..N_y-1, 0..N_z-1]$. Drives 2D MPR slice extraction and display crosshairs.
2. **Physical Coordinate Space (Mesh Space in mm)**:
   $$p = [x \cdot s_x, \; y \cdot s_y, \; z \cdot s_z]$$
   where $[s_x, s_y, s_z]$ is the anisotropic voxel spacing obtained from the NIfTI header zooms.
   - Marching Cubes mesh vertices from `skimage.measure.marching_cubes` scale grid steps by voxel spacing but do not apply gantry table translations.
   - In Three.js, meshes and measurements are placed inside a parent group rotated by $[-\pi/2, 0, 0]$:
     $$p_{\text{three}} = [p_x, \; p_z, \; -p_y]$$
3. **Physical Euclidean Distance**:
   $$d(p_1, p_2) = \sqrt{(x_2 - x_1)^2 s_x^2 + (y_2 - y_1)^2 s_y^2 + (z_2 - z_1)^2 s_z^2}$$
   Distances are strictly invariant under rigid affine translation and rotation.

---

## 3. Measurement Types

| Measurement Type | Description | Source | Start / End Entities |
| :--- | :--- | :--- | :--- |
| `point_to_point` | Distance between two user-selected CT voxels | `user` | `start_voxel`, `end_voxel` |
| `target_to_target` | Distance between centroids of two surgical planning targets | `computational` | `source_target_id`, `target_target_id` |
| `target_to_structure` | Minimum distance from a planning target to an anatomical structure mask | `computational` | `source_target_id`, `target_structure_id` |
| `structure_to_structure` | Minimum distance between two anatomical structure masks | `computational` | `source_structure_id`, `target_structure_id` |

---

## 4. REST API Specification

### 1. List Measurements
- **Method**: `GET /api/cases/{case_id}/planning/measurements`
- **Response**: `200 OK`
```json
{
  "case_id": "b2f89382-9416-4e94-9486-b00c6b1de64b",
  "total_measurements": 1,
  "measurements": [
    {
      "measurement_id": "meas_a1b2c3d4",
      "case_id": "b2f89382-9416-4e94-9486-b00c6b1de64b",
      "measurement_type": "point_to_point",
      "label": "Point-to-Point Measurement 1",
      "source": "user",
      "start_voxel": [100, 120, 150],
      "end_voxel": [110, 120, 150],
      "start_physical": [78.12, 93.75, 450.0],
      "end_physical": [85.94, 93.75, 450.0],
      "distance_mm": 7.81,
      "distance_cm": 0.781,
      "overlap": null,
      "notes": null,
      "created_at": "2026-09-19T14:30:00Z"
    }
  ],
  "safety_disclaimer": "All measurements are computational geometric distances derived from CT coordinate space..."
}
```

### 2. Create Point-to-Point Measurement
- **Method**: `POST /api/cases/{case_id}/planning/measurements`
- **Payload**:
```json
{
  "start_voxel": [100, 120, 150],
  "end_voxel": [110, 120, 150],
  "label": "Cortex to Lesion Distance",
  "notes": "Measured on axial slice 150"
}
```
- **Response**: `201 Created`

### 3. Create Target-to-Target Measurement
- **Method**: `POST /api/cases/{case_id}/planning/measurements/from-targets`
- **Payload**:
```json
{
  "source_target_id": "model_cyst_left",
  "target_target_id": "ann_entry_point",
  "label": "Trajectory to Lesion"
}
```

### 4. Create Target-to-Structure Measurement
- **Method**: `POST /api/cases/{case_id}/planning/measurements/to-structure`
- **Payload**:
```json
{
  "target_id": "model_cyst_left",
  "structure_id": "aorta",
  "label": "Lesion to Aorta"
}
```

### 5. Create Structure-to-Structure Measurement
- **Method**: `POST /api/cases/{case_id}/planning/measurements/structure-to-structure`
- **Payload**:
```json
{
  "source_structure_id": "kidney_left",
  "target_structure_id": "aorta"
}
```

### 6. Delete Measurement
- **Method**: `DELETE /api/cases/{case_id}/planning/measurements/{measurement_id}`
- **Response**: `200 OK`
```json
{
  "status": "deleted",
  "measurement_id": "meas_a1b2c3d4",
  "case_id": "b2f89382-9416-4e94-9486-b00c6b1de64b"
}
```
*Note: Deletion of measurements is strictly isolated and does not modify planning annotations or image segmentations.*

---

## 5. Frontend User Experience

1. **Two-Step Measurement Picking**:
   - In Planning View, clicking **"📐 Measure Distance"** engages measurement mode (and automatically disengages annotation mode to prevent misclicks).
   - An MPR banner guides the user: *"Click Point A on any CT slice to begin."*
   - Once Point A is clicked, crosshairs sync and the banner updates: *"Point A selected. Now click Point B to complete the measurement."*
   - Once Point B is clicked, the measurement is created via backend calculation and added to the sidebar and 3D viewer.
2. **3D Interactive Line & Endpoints**:
   - Rendered as emerald/amber spheres and connecting 3D cylinder.
   - Clicking the line or sidebar card focuses both the 2D MPR crosshairs and the 3D camera onto the measurement midpoint.
3. **InfoPanel Detail**:
   - Shows high-contrast hero distance readout in both millimeters and centimeters.
   - Details exact voxel coordinates, origin-relative physical coordinates, overlap status, and the mandatory clinical disclaimer.
