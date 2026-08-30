# Technical Reference: 3D Mesh Generation

## Architecture & Data Flow
**Flow:** NIfTI Mask (`.nii.gz`) → Voxel Array + Spacing Metadata → Marching Cubes Algorithm → Raw Vertices/Faces → `.obj` File Export.

**Separation of Concerns:** 
Mesh generation is strictly isolated in `src/mesh/mesh_generator.py`. It does not rely on PyTorch or the segmentation engine. It simply expects binary 3D grids and converts them to geometry.

## Terminology
- **Voxel:** A 3D pixel. The smallest unit of volume in a medical scan.
- **Voxel Spacing (Zoom):** The physical dimension (in millimeters) that a single voxel represents in the X, Y, and Z axes.
- **Segmentation Mask:** A volumetric representation where each voxel is assigned a value (usually 0 for background, 1 for foreground) indicating the presence of a specific anatomical structure.
- **Isosurface:** A 3D surface representing points of a constant value (e.g., 0.5) within a volume of space.
- **Vertices:** The 3D coordinate points (X, Y, Z) that define the corners of the geometry.
- **Faces (Polygons):** The triangles connecting the vertices to form a solid surface.

## Marching Cubes Algorithm
The Marching Cubes algorithm (implemented via `skimage.measure.marching_cubes`) is the industry standard for extracting polygonal meshes from scalar fields.
1. The algorithm creates a logical cube consisting of 8 neighboring voxels.
2. It determines which corners of the cube are "inside" the target object (value > 0.5) and which are "outside".
3. Based on the configuration of inside/outside corners (there are 256 possible cases), it generates the appropriate triangles that intersect the cube.
4. It repeats this ("marches") across the entire voxel grid.

## Coordinate & Spacing Handling
In medical imaging, indices in a numpy array do not map 1:1 to physical millimeters. If a mask has a shape of `(300, 300, 300)` and a voxel spacing of `(1.5, 1.5, 1.5) mm`, the physical size of the volume is `450 x 450 x 450 mm`.
When calling `marching_cubes`, the `spacing` parameter is explicitly passed. The algorithm automatically scales the generated vertex coordinates by these factors, guaranteeing that the resulting `.obj` mesh is in standard millimeters.

## Mesh Formats (.obj)
The Wavefront `.obj` format was chosen because:
1. It is universally supported by almost all 3D software and WebGL libraries (Three.js).
2. It is a simple, human-readable text format.
3. It requires no specialized third-party dependencies to export.

**Format Structure:**
```
v [x] [y] [z]  # Defines a vertex
...
f [v1] [v2] [v3]  # Defines a face (1-indexed based on vertex list)
```

## API / Function Reference
- `load_mask(mask_path)`: Loads `.nii.gz` via NiBabel. Returns `(binary_numpy_array, spacing_tuple)`.
- `generate_mesh_from_mask(mask_data, spacing)`: Executes Marching Cubes. Returns `(vertices, faces)`.
- `save_mesh_as_obj(filepath, verts, faces)`: Manually constructs and writes the `.obj` file.

## CLI Usage
Execute the script as a python module from the root directory:
```bash
python -m src.mesh.mesh_generator --organs liver heart aorta kidney_left
```
**Optional Arguments:**
- `--input-dir`: Target a different segmentations folder.
- `--output-dir`: Target a different output folder.

## Troubleshooting & Common Errors
- **Empty Meshes / No Foreground Voxels:** Caused by requesting an organ that TotalSegmentator couldn't find in the scan. The script safely catches this and skips generation.
- **Tiny Meshes:** If you forget to pass the `spacing` parameter to Marching Cubes, your meshes will be generated in "voxel coordinates" rather than physical millimeters, making them significantly smaller than reality.
- **Memory Errors:** High-resolution masks can generate millions of polygons, exhausting RAM. For MVP purposes, TotalSegmentator's `fast=True` mode keeps the voxel count manageable.

## Design Decisions
1. **No Mesh Smoothing:** Left out to avoid introducing heavy dependencies like `trimesh` or `open3d` and to ensure rapid execution. 
2. **Text-based OBJ Writer:** Implemented manually to avoid adding bloat. `scikit-image` doesn't have a native mesh exporter, and we didn't need a massive library just to write a text file.
