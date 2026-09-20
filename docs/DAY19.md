# DAY 19 — Coordinate System & Spatial Registration Audit
## Fast-Track Hardening Milestone Report

### Milestone Status: Complete ✅
- **Previous Backend Test Suite**: 166 passed
- **New Tests Added**: 23 focused spatial registration tests
- **Total Backend Tests**: 189 passed (`189 passed, 7 warnings in 22.82s`)
- **Frontend Build**: 0 errors (`built in 768ms`)
- **Git State**: No commits or pushes made (clean working tree adherence)

---

## 1. Executive Summary

Day 19 was executed as a focused technical audit and hardening milestone to verify computational spatial consistency across the entire coordinate transformation pipeline:
$$\text{NIfTI Voxel} \longleftrightarrow \text{Physical Space} \longleftrightarrow \text{Scanner World (RAS)} \longleftrightarrow \text{MPR Display Space} \longleftrightarrow \text{Three.js 3D Scene Space}$$

The objective was achieved:
- A point selected at an anatomical location on MPR corresponds to the same anatomical location in 3D scene space.
- Planning targets and measurement endpoints in 3D correspond to the exact voxel and world locations on 2D MPR slices.
- Terminology was sanitized to avoid conflating origin-relative physical spacing millimeters with scanner world RAS millimeters.

---

## 2. Complete Phase Execution Summary

### Phase 0 — Complete Code Audit
Audited all coordinate handling across backend (`src/visualization/mpr.py`, `src/measurements/`, `src/planning/`, `src/mesh/mesh_generator.py`) and frontend (`frontend/src/MPRViewer.jsx`, `frontend/src/Viewer3D.jsx`, `frontend/src/App.jsx`, `frontend/src/InfoPanel.jsx`).

### Phase 1 — Five Coordinate Spaces Identified & Formalized
1. **Voxel Space**: 3D integer indices $[x, y, z]$ into the CT volume array $(293, 293, 344)$.
2. **Physical / Spacing Space**: Origin-relative mm $[x \cdot s_x, y \cdot s_y, z \cdot s_z]$.
3. **NIfTI Scanner World Space**: 4x4 affine-transformed coordinates in scanner RAS space.
4. **MPR Display Space**: 2D display pixels $(u, v)$ across Axial, Coronal, and Sagittal planes.
5. **Three.js Scene Space**: Visualized 3D coordinates under `<group rotation={[-Math.PI / 2, 0, 0]}>` inside `<Center>`.

### Phase 2 — Critical RAS/World Terminology Audit
- Discovered and fixed: In `frontend/src/InfoPanel.jsx` line 373, `target.physical_coordinate` was labeled as `Physical Coordinates (RAS)`. Changed to `Physical Coordinates (mm)`.
- Discovered and fixed: In `src/measurements/lesion_measurements.py` line 157, `world_centroid_mm` defaulted to `physical_c` when `affine is None`. Changed to `world_centroid_mm = None` when affine is unavailable.

### Phase 3 — Real NIfTI CT Affine Validation
Inspected `datasets/raw/ct/ct_15mm_defaced.nii`:
- Dimensions: $(293, 293, 344)$
- Zooms: $(1.5, 1.5, 1.5)$ mm
- Affine Matrix:
  $$\mathbf{A} = \begin{bmatrix} 1.5 & 0.0 & 0.0 & -225.071 \\ 0.0 & 1.5 & 0.0 & -46.571 \\ 0.0 & 0.0 & 1.5 & -146.500 \\ 0.0 & 0.0 & 0.0 & 1.0 \end{bmatrix}$$
- Orientation (`nib.aff2axcodes`): `('R', 'A', 'S')`
- Analysis: $\mathbf{R}$ is purely diagonal (`diag([1.5, 1.5, 1.5])`). No rotation, no obliquity, no axis flips. World coordinates relate to physical coordinates by a constant translation: $\mathbf{w} = \mathbf{p} + \mathbf{T}$, where $\mathbf{T} = [-225.071, -46.571, -146.500]$ mm.

### Phase 4 — Roundtrip Transformations
- Voxel $\to$ World $\to$ Voxel: Roundtrip recovers origin $[0, 0, 0]$, center $[146, 146, 172]$, corner $[292, 292, 343]$, and lesion centroid $[110, 89, 218]$ with **zero integer error**.
- Inversion precision: $\|\mathbf{v} - \mathbf{A}^{-1}\mathbf{A}\mathbf{v}\| < 10^{-12}$ mm.
- Physical distance with anisotropic spacing $(0.8, 0.8, 2.5)$ mm verified: strictly scales slice thickness, avoiding naive voxel Euclidean calculation.

### Phase 5 — MPR Coordinate Validation
Verified analytical projection and inverse projection formulas across all planes:
- **Axial**: $u = (N_x - 1) - x, v = (N_y - 1) - y \iff x = (N_x - 1) - u, y = (N_y - 1) - v$
- **Coronal**: $u = (N_x - 1) - x, v = (N_z - 1) - z \iff x = (N_x - 1) - u, z = (N_z - 1) - v$
- **Sagittal**: $u = (N_y - 1) - y, v = (N_z - 1) - z \iff y = (N_y - 1) - u, z = (N_z - 1) - v$
Display $\leftrightarrow$ voxel projections are exact inverses.

### Phase 6 — 3D Mesh Coordinate Audit
In `src/mesh/mesh_generator.py`:
- `skimage.measure.marching_cubes(mask, level=0.5, spacing=spacing)` automatically scales vertex output to physical mm.
- In `frontend/src/Viewer3D.jsx`: meshes, planning markers, and measurement 3D lines are rendered inside `<group rotation={[-Math.PI / 2, 0, 0]}>` inside `<Center>`.
- Rotation rotates $+Z$ (Superior) to $+Y$ (Three.js Up) and $+Y$ (Anterior) to $-Z$ (Towards camera/front).
- Mesh vertices, planning markers, and measurement endpoints share the exact same physical coordinates.

### Phase 7 — Real KiTS23 Lesion Registration Check
Case `b2f89382-9416-4e94-9486-b00c6b1de64b` finding `model_cyst_left`:
- Voxel Centroid: $[110, 89, 218]$
- Physical Centroid: $[164.868, 133.104, 327.363]$ mm
- World Centroid: $[-60.071, 86.929, 180.500]$ mm
- 3D Mesh Vertex Mean (`cyst_left.obj`): $[164.908, 133.058, 327.432]$ mm
- Surface vs Voxel Error: $0.0914$ mm (discretization error well within sub-0.1 mm).
- MPR Display: Slice 218 on Axial (Col 182, Row 203), Slice 89 on Coronal, Slice 110 on Sagittal.

### Phase 8 & 9 — Planning Point & Measurement Endpoint Validation
- MPR clicks correctly convert to voxel $\to$ physical coordinates $\to$ 3D markers at the exact anatomical site.
- Point-to-point measurement calculates Euclidean distance in physical millimeters using anisotropic spacing, and 3D measurement lines connect the intended anatomical endpoints.

### Phase 10 & 11 — Centralized Coordinate Engine
Created `src/geometry/coordinate_system.py` providing unified, well-typed coordinate transformations. Re-exported in `src/visualization/mpr.py` for 100% backward compatibility.

### Phase 12 — Testing
All 189 tests passing (166 previous + 23 new). Frontend builds with 0 errors.

### Phase 13 & 14 — Real Case Validation & Documentation
Generated computational spatial consistency report and comprehensive documentation in `docs/COORDINATE_SYSTEM.md` and `docs/DAY19.md`.

---

## 3. Medical Governance Statement

All audit verifications establish **computational spatial consistency** within an educational and research prototype. They do **not** imply clinical registration accuracy, surgical navigation accuracy, or validated operative guidance.
