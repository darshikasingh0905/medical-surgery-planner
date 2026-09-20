# Coordinate System & Spatial Registration Architecture

## Clinical Governance & Safety Disclaimer

> [!IMPORTANT]
> **RESEARCH AND EDUCATIONAL PROTOTYPE ONLY**  
> All coordinate transformations, spatial metrics, and registrations documented in this system establish **computational spatial consistency** across software representations.  
> They do **NOT** constitute:
> - Clinical registration accuracy
> - Surgical navigation accuracy
> - Clinical-grade anatomical localization
> - Validated surgical guidance or positioning
> - Treatment planning clearance or margin safety  
> This system is strictly an educational visualization and research exploration prototype and is **not validated for clinical use**.

---

## 1. Overview of Coordinate Spaces

The Medical Surgery Planner operates across five distinct mathematical coordinate spaces. Explicitly distinguishing these spaces is critical to prevent conflation between scanner world coordinates, spacing-scaled physical space, and screen display projections.

```
       ┌────────────────────────┐
       │   Voxel Space (3D)     │  [x, y, z] integer indices
       └───────────┬────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
┌──────────────────┐  ┌───────────────────────┐
│ Physical Space   │  │ Scanner World Space   │
│ [px, py, pz] mm  │  │ [wx, wy, wz] mm (RAS) │
│ (Spacing-Scaled) │  │ (Affine Transformed)  │
└────────┬─────────┘  └───────────────────────┘
         │
         ├───────────────────────────────────────────┐
         ▼                                           ▼
┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│ MPR Display Space (2D)          │   │ Three.js Scene Space (3D)       │
│ (u, v) per orthogonal plane     │   │ [X_3d, Y_3d, Z_3d] mm           │
│ Axial, Coronal, Sagittal        │   │ Meshes, Markers & Lines         │
└─────────────────────────────────┘   └─────────────────────────────────┘
```

---

## 2. Mathematical Formulations of the 5 Spaces

### A. Voxel / Index Space
- **Units**: Integer indices (voxels)
- **Variables**: $[v_x, v_y, v_z]$ where $0 \le v_x < N_x$, $0 \le v_y < N_y$, $0 \le v_z < N_z$.
- **Real CT Case Dimensions**: $(293, 293, 344)$
- **Axis Order & Orientation**:
  - Axis 0 ($v_x$): Patient Left $\to$ Right (in RAS orientation)
  - Axis 1 ($v_y$): Patient Posterior $\to$ Anterior
  - Axis 2 ($v_z$): Patient Inferior $\to$ Superior (feet to head)
- **Origin**: $[0, 0, 0]$ represents the corner voxel of the 3D volume array.

### B. Physical / Spacing Space
- **Units**: Millimeters (mm)
- **Definition**: Origin-relative coordinates scaled by voxel spacing $[s_x, s_y, s_z]$:
  $$\mathbf{p} = \begin{bmatrix} p_x \\ p_y \\ p_z \end{bmatrix} = \begin{bmatrix} v_x \cdot s_x \\ v_y \cdot s_y \\ v_z \cdot s_z \end{bmatrix}$$
- **Inverse Transformation**:
  $$\mathbf{v} = \text{round}\left( \begin{bmatrix} p_x / s_x \\ p_y / s_y \\ p_z / s_z \end{bmatrix} \right)$$
- **Role**:
  - Ground truth space for Marching Cubes 3D surface mesh generation (`skimage.measure.marching_cubes(mask, level=0.5, spacing=spacing)`).
  - Local vertex coordinates of exported OBJ meshes.
  - Calculation space for all Euclidean distances, minimum structure clearances, and bounding box dimensions.
  - Coordinate system of `PlanningTarget.physical_coordinate` and `Measurement.start_physical` / `end_physical`.

### C. NIfTI Scanner World Space (RAS)
- **Units**: Millimeters (mm)
- **Definition**: Defined relative to the scanner physical isocenter via the $4 \times 4$ homogeneous affine matrix $\mathbf{A}$:
  $$\begin{bmatrix} w_x \\ w_y \\ w_z \\ 1 \end{bmatrix} = \mathbf{A} \begin{bmatrix} v_x \\ v_y \\ v_z \\ 1 \end{bmatrix} = \begin{bmatrix} R_{00} & R_{01} & R_{02} & T_x \\ R_{10} & R_{11} & R_{12} & T_y \\ R_{20} & R_{21} & R_{22} & T_z \\ 0 & 0 & 0 & 1 \end{bmatrix} \begin{bmatrix} v_x \\ v_y \\ v_z \\ 1 \end{bmatrix}$$
- **Inverse Transformation**:
  $$\begin{bmatrix} v_x \\ v_y \\ v_z \\ 1 \end{bmatrix} = \text{round}\left( \mathbf{A}^{-1} \begin{bmatrix} w_x \\ w_y \\ w_z \\ 1 \end{bmatrix} \right)$$
- **Real CT Affine Matrix** (`datasets/raw/ct/ct_15mm_defaced.nii`):
  $$\mathbf{A} = \begin{bmatrix} 1.5 & 0.0 & 0.0 & -225.071 \\ 0.0 & 1.5 & 0.0 & -46.571 \\ 0.0 & 0.0 & 1.5 & -146.500 \\ 0.0 & 0.0 & 0.0 & 1.0 \end{bmatrix}$$
- **Orientation (`nib.aff2axcodes`)**: `('R', 'A', 'S')` (Right, Anterior, Superior).
- **Properties**:
  - The $3 \times 3$ rotation matrix $\mathbf{R} = \text{diag}(1.5, 1.5, 1.5)$ is purely diagonal with positive scaling.
  - There is **no axis inversion, rotation, or obliquity**.
  - Direct relationship to physical space:
    $$\mathbf{w} = \mathbf{p} + \mathbf{T}, \quad \mathbf{T} = \begin{bmatrix} -225.071 \\ -46.571 \\ -146.500 \end{bmatrix} \text{ mm}$$
  - Because $\mathbf{T}$ is a pure constant translation, inter-point distances in Physical Space and Scanner World Space are identical:
    $$\|\mathbf{w}_B - \mathbf{w}_A\| = \|\mathbf{p}_B - \mathbf{p}_A\|$$

### D. MPR Display Space (2D Orthogonal Projections)
- **Units**: Pixels $(u, v)$ with origin $(0, 0)$ at the top-left of each displayed image.
- **Radiological Display Standards**:
  - **Axial** (Slice index $z = v_z$, shape $N_y \times N_x$):
    - Top: Anterior ($v_y = N_y - 1$)
    - Bottom: Posterior ($v_y = 0$)
    - Left: Patient Right ($v_x = N_x - 1$)
    - Right: Patient Left ($v_x = 0$)
    - Mapping:
      $$u = (N_x - 1) - v_x, \quad v = (N_y - 1) - v_y$$
    - Inverse:
      $$v_x = (N_x - 1) - u, \quad v_y = (N_y - 1) - v$$
  - **Coronal** (Slice index $y = v_y$, shape $N_z \times N_x$):
    - Top: Superior ($v_z = N_z - 1$)
    - Bottom: Inferior ($v_z = 0$)
    - Left: Patient Right ($v_x = N_x - 1$)
    - Right: Patient Left ($v_x = 0$)
    - Mapping:
      $$u = (N_x - 1) - v_x, \quad v = (N_z - 1) - v_z$$
    - Inverse:
      $$v_x = (N_x - 1) - u, \quad v_z = (N_z - 1) - v$$
  - **Sagittal** (Slice index $x = v_x$, shape $N_z \times N_y$):
    - Top: Superior ($v_z = N_z - 1$)
    - Bottom: Inferior ($v_z = 0$)
    - Left: Anterior ($v_y = N_y - 1$)
    - Right: Posterior ($v_y = 0$)
    - Mapping:
      $$u = (N_y - 1) - v_y, \quad v = (N_z - 1) - v_z$$
    - Inverse:
      $$v_y = (N_y - 1) - u, \quad v_z = (N_z - 1) - v$$

### E. Three.js Scene Space (3D Visualization)
- **Units**: Scene units ($1 \text{ unit} = 1.0 \text{ mm}$).
- **Scene Hierarchy**:
  In `Viewer3D.jsx`, all 3D entities are rendered within:
  ```jsx
  <Center>
    <group rotation={[-Math.PI / 2, 0, 0]}>
      {/* OrganMesh */}
      {/* LesionMesh */}
      {/* PlanningMarker3D */}
      {/* Measurement3D */}
    </group>
  </Center>
  ```
- **Local Group Frame**: Identical to **Physical Space** $[p_x, p_y, p_z]$ mm.
- **Rotation $R_x(-\pi/2)$**:
  Rotates medical coordinates to standard WebGL/Three.js camera convention (+Y is Up):
  $$\begin{bmatrix} X_{3D} \\ Y_{3D} \\ Z_{3D} \end{bmatrix} = \begin{bmatrix} 1 & 0 & 0 \\ 0 & 0 & 1 \\ 0 & -1 & 0 \end{bmatrix} \begin{bmatrix} p_x \\ p_y \\ p_z \end{bmatrix} = \begin{bmatrix} p_x \\ p_z \\ -p_y \end{bmatrix}$$
  - $X_{3D} = p_x$ (Patient Right)
  - $Y_{3D} = p_z$ (Patient Superior $\to$ Up in Three.js)
  - $Z_{3D} = -p_y$ (Patient Anterior $\to$ Towards viewer)
- **`<Center>` Wrapper**: Auto-centers the collective bounding box at $(0, 0, 0)$ for optimal camera orbiting without modifying the relative alignment between meshes, planning markers, and measurement lines.

---

## 3. Centralized Coordinate Module (`src/geometry/coordinate_system.py`)

All coordinate conversions are centralized in `src/geometry/coordinate_system.py` and re-exported by `src/visualization/mpr.py` for 100% backward compatibility:

```python
from src.geometry.coordinate_system import (
    clamp_coordinates,
    voxel_to_world,
    world_to_voxel,
    voxel_to_physical,
    physical_to_voxel,
    calculate_physical_distance,
    voxel_to_display_crosshair,
    display_to_voxel_crosshair,
    get_plane_dimensions,
)
```

---

## 4. Computational Spatial Consistency Validation

### Real KiTS23 Case: `b2f89382-9416-4e94-9486-b00c6b1de64b`
CT Scan: `datasets/raw/ct/ct_15mm_defaced.nii` | Dimensions: $(293, 293, 344)$ | Spacing: $(1.5, 1.5, 1.5)$ mm

| Entity | Voxel Space $[x, y, z]$ | Physical Space $[px, py, pz]$ mm | Scanner World (RAS) mm | MPR 2D Location | 3D Scene $[X, Y, Z]$ | Discrepancy / Tolerance |
|---|---|---|---|---|---|---|
| **Origin Voxel** | $[0, 0, 0]$ | $[0.0, 0.0, 0.0]$ | $[-225.071, -46.571, -146.500]$ | Ax: (292, 292), Sl 0 | $[0.0, 0.0, 0.0]$ | $0.0$ voxels (exact) |
| **Center Voxel** | $[146, 146, 172]$ | $[219.0, 219.0, 258.0]$ | $[-6.071, 172.429, 111.500]$ | Ax: (146, 146), Sl 172 | $[219.0, 258.0, -219.0]$ | $0.0$ voxels (exact) |
| **Max Corner** | $[292, 292, 343]$ | $[438.0, 438.0, 514.5]$ | $[212.929, 391.429, 368.000]$ | Ax: (0, 0), Sl 343 | $[438.0, 514.5, -438.0]$ | $0.0$ voxels (exact) |
| **Lesion Centroid** (`model_cyst_left`) | $[110, 89, 218]$ | $[164.868, 133.104, 327.363]$ | $[-60.071, 86.929, 180.500]$ | Ax: (182, 203), Sl 218<br>Cor: (182, 125), Sl 89<br>Sag: (203, 125), Sl 110 | $[164.868, 327.363, -133.104]$ | $0.0$ voxels roundtrip |
| **3D Mesh Vertex Mean** (`cyst_left.obj`) | — | $[164.908, 133.058, 327.432]$ | — | — | $[164.908, 327.432, -133.058]$ | $0.0914 \text{ mm}$ vs mask |
| **Planning Marker 3D** | $[110, 89, 218]$ | $[164.868, 133.104, 327.363]$ | — | Ax: (182, 203), Sl 218 | Coincides with mesh center | $< 0.1 \text{ mm}$ |
| **Measurement Line** (Lesion $\to$ Center) | Start: $[110, 89, 218]$<br>End: $[146, 146, 172]$ | Start: $[165.0, 133.5, 327.0]$<br>End: $[219.0, 219.0, 258.0]$ | — | Rendered at endpoints on MPR | 3D line connects endpoints | Distance: $122.422 \text{ mm}$ ($12.242 \text{ cm}$) |

---

## 5. Roundtrip Tolerances & Benchmarks

| Transformation Pipeline | Tolerance | Observed Result | Status |
|---|---|---|---|
| **Voxel $\to$ World $\to$ Voxel** | $0$ voxels after round | $0$ discrepancy | PASS |
| **Affine Matrix Inversion Precision** | $< 10^{-10}$ mm | $< 10^{-12}$ mm | PASS |
| **Voxel $\to$ Physical $\to$ Voxel** | $0$ voxels after round | $0$ discrepancy | PASS |
| **Anisotropic Spacing Distance** | $< 10^{-3}$ mm | $0.000$ mm discrepancy | PASS |
| **MPR Forward $\leftrightarrow$ Inverse Projections** | $0$ pixels | Exact mathematical inverse | PASS |
| **Marching Cubes Surface vs Voxel Centroid** | $< 0.15$ mm | $0.0914$ mm (discretization error) | PASS |
| **Planning Target $\leftrightarrow$ 3D Marker Placement** | $< 0.1$ mm | Exactly coincident in physical space | PASS |

---

## 6. Known System Limitations

1. **Rigid Scanner World Alignment**:
   The current real KiTS CT affine matrix is identity-like with diagonal scaling and translation. If oblique non-orthogonal CT volumes with off-diagonal shear matrices are loaded, slice extraction in `mpr.py` reslices along the voxel grid axes rather than oblique scanner coordinates.
2. **Surface Discretization Gap**:
   Marching cubes generates isosurfaces at level $0.5$. There is an inherent sub-voxel difference ($\approx 0.09 \text{ mm}$ in $1.5 \text{ mm}$ voxels) between the binary voxel center of mass and the triangular surface mesh centroid.
3. **No Patient Movement Tracking**:
   The coordinates assume a single rigid static preoperative CT volume. Intraoperative organ deformation, respiratory motion, and patient positioning changes are not modeled.
