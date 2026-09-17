# SURGICAL METRICS — Technical Reference

## Overview

This document describes the computational spatial measurement methodology used in the AI-Assisted Preoperative Planning System prototype for renal lesion analysis.

> ⚠️ **Clinical Governance**: All metrics in this system are strictly computational estimates derived from CT image segmentation masks. They do not represent clinically validated surgical margins, histological findings, intraoperative clearances, or operative resectability recommendations. All outputs require review by a qualified medical professional.

---

## Measurement Functions

### 1. Physical Volume

**Function:** `calculate_lesion_volume(mask, spacing)`

**Method:** Voxel-counting with anisotropic spacing correction.

```
volume_mm³ = foreground_voxels × (dx × dy × dz)
volume_mL  = volume_mm³ / 1000
```

Where `dx, dy, dz` are physical voxel dimensions in millimeters from the NIfTI header `pixdim` field.

**Handles:** Anisotropic CT voxels (e.g., 1.5 × 1.5 × 5.0 mm), ensures physical accuracy regardless of acquisition protocol.

---

### 2. Anisotropic Bounding Box

**Function:** `calculate_lesion_bounding_box(mask, spacing)`

**Method:**
1. Find minimum and maximum voxel indices along each axis using `np.argwhere`
2. Compute physical dimension as `(max_idx − min_idx + 1) × spacing_axis`

```
dim_x_mm = (max_x − min_x + 1) × dx
dim_y_mm = (max_y − min_y + 1) × dy
dim_z_mm = (max_z − min_z + 1) × dz
```

**Handles empty masks:** Returns zero dimensions without error.

---

### 3. 3D Centroid

**Function:** `calculate_lesion_centroid(mask, spacing, affine)`

**Method:** Geometric centroid of foreground voxels.

```
voxel_centroid   = mean(argwhere(mask > 0), axis=0)
physical_centroid = voxel_centroid × [dx, dy, dz]  (mm)
world_centroid    = affine @ [vx, vy, vz, 1]        (RAS mm, if affine provided)
```

**World coordinates** use the NIfTI affine matrix (rotation + translation) to compute scanner-space RAS coordinates, enabling registration with surgical navigation systems.

---

### 4. Minimum Euclidean Distance to Anatomical Structures

**Function:** `calculate_minimum_distance_to_structure(lesion_mask, structure_mask, spacing, check_boundary_only)`

**Method:** Physical k-d tree nearest-neighbor query.

#### Algorithm

```python
# Convert voxel coordinates to physical mm (anisotropic-aware)
lesion_pts_mm    = argwhere(lesion > 0) × spacing
structure_pts_mm = argwhere(structure > 0) × spacing

# Build spatial index on structure
tree = cKDTree(structure_pts_mm)

# Query minimum distance
distances, _ = tree.query(lesion_pts_mm)
min_distance_mm = min(distances)
```

**Complexity:** O(n log m) where n = lesion voxels, m = structure voxels. Typically < 0.4 seconds for CT volumes.

**Boundary-only mode** (`check_boundary_only=True`):
- Used for organ capsule/parenchymal surface distances
- Extracts organ surface: `surface = organ_mask & ~binary_erosion(organ_mask)`
- Computes distance to this surface rather than the organ interior

#### Overlap Handling
- If lesion and structure share foreground voxels → returns `0.0 mm` immediately (short-circuit, no k-d tree needed)
- Used for checking intra-parenchymal vs. extra-parenchymal lesion position

---

### 5. Comprehensive Lesion Metrics

**Function:** `calculate_comprehensive_lesion_metrics(lesion_mask_path, structures_dir, host_organ, vessel_organs)`

Combines all above functions into a single dict:

```
{
  "lesion_id": str,
  "mask_path": str,
  "voxel_spacing_mm": [dx, dy, dz],
  "volume": { foreground_voxels, voxel_volume_mm3, volume_mm3, volume_cm3, volume_ml },
  "bounding_box": { voxel_bounds, voxel_dimensions, x_mm, y_mm, z_mm, dimensions_mm },
  "centroid": { voxel_centroid, physical_centroid_mm, world_centroid_mm },
  "computational_distances": {
    "{host_organ}_surface": { status, minimum_distance_mm, is_within_organ_parenchyma, description },
    "{vessel}": { status, minimum_distance_mm, source_mask, description }
    ...
  },
  "safety_disclaimer": str
}
```

---

## Distance Metric Interpretation Table

| Distance Key | What it measures | check_boundary_only |
|---|---|---|
| `kidney_left_surface` | Minimum distance from lesion to left kidney outer parenchymal surface (capsule) | `True` |
| `aorta` | Minimum distance from any lesion voxel to any aortic voxel | `False` |
| `inferior_vena_cava` | Minimum distance from any lesion voxel to IVC | `False` |
| `renal_artery` | Not available (not segmented by standard TotalSegmentator) | — |

> **Important:** A distance of `3.354 mm` to `kidney_left_surface` means the computational minimum distance from the lesion boundary voxels to the computed kidney parenchymal surface is 3.354 mm. This is **not** a histological or surgical margin. It is a model-derived spatial estimate only.

---

## Terminology Policy

The following terms are **prohibited** in all outputs, API responses, and UI labels:

| ❌ Prohibited | ✅ Required Replacement |
|---|---|
| "safe margin" | "computational minimum distance" |
| "resectable" | omit — not determined by this system |
| "surgical clearance" | omit — not determined by this system |
| "benign" | "model-predicted cyst-class" |
| "confirmed tumor" | "model-predicted tumor-class" |
| "diagnosed" | omit — not a diagnostic system |

---

## Structures and Segmentation Availability

Segmentation availability depends on the TotalSegmentator model configuration used. Standard 104-organ model output:

| Structure | Available | Notes |
|---|---|---|
| `kidney_left` | ✅ | 70,496 voxels in reference case |
| `kidney_right` | ✅ | 60,416 voxels |
| `aorta` | ✅ | 53,732 voxels |
| `inferior_vena_cava` | ✅ | 21,580 voxels |
| `iliac_artery_left` | ✅ | |
| `iliac_artery_right` | ✅ | |
| `renal_artery` | ❌ | Not in standard 104-organ set |
| `renal_vein` | ❌ | Not in standard 104-organ set |
| `renal_pelvis` | ❌ | Not in standard 104-organ set |
| `ureter` | ❌ | Not in standard 104-organ set |

The measurement engine marks unavailable structures as `"status": "unavailable"` and **never fabricates masks**.

---

## Validated Result — Reference Case

Case: `b2f89382-9416-4e94-9486-b00c6b1de64b`
Lesion: `cyst_left.nii.gz` (KiTS2023 nnU-Net v2 class-3 prediction)

| Metric | Value |
|---|---|
| Volume | 0.3071 mL |
| Dimensions | 7.5 × 9.0 × 9.0 mm |
| World centroid | [-60.203, 86.533, 180.863] mm (RAS) |
| Distance to kidney capsule | 3.354 mm (fully within parenchyma) |
| Distance to aorta | 54.104 mm |
| Distance to IVC | 90.337 mm |
| Computation time (distances) | < 0.4 seconds |

---

## API Reference

### GET `/api/cases/{case_id}/lesions`

Response (200 OK — completed case with cached lesions):
```json
{
  "case_id": "string",
  "total_lesions": 1,
  "lesions": [ { ... lesion object ... } ],
  "disclaimer": "Computational metrics for decision support only..."
}
```

Response (200 OK — completed case, no lesions):
```json
{ "case_id": "...", "total_lesions": 0, "lesions": [], "disclaimer": "..." }
```

Response (400 Bad Request — case not completed):
```json
{ "detail": "Results not ready. Case status: processing" }
```

### GET `/api/cases/{case_id}/lesions/{lesion_id}`

Response (200 OK):
```json
{ "lesion_id": "cyst_left", "class_label": 3, "volume_ml": 0.3071, ... }
```

Response (404 Not Found):
```json
{ "detail": "Lesion 'tumor_left' not found in case results." }
```

---

## Implementation Files

| File | Role |
|---|---|
| `src/measurements/lesion_measurements.py` | Core spatial measurement engine |
| `src/api/routes/cases.py` | `/lesions` API endpoints |
| `outputs/.../measurements/lesions.json` | Cached lesion payload |
| `outputs/.../lesions/cyst_left.nii.gz` | Real KiTS2023 model prediction |
| `outputs/.../meshes/cyst_left.obj` | OBJ mesh (146 vertices, 288 faces) |
| `tests/test_measurements.py::TestLesionMeasurements` | Unit tests (5 tests) |
| `tests/test_api.py` | API endpoint tests (3 new tests) |
