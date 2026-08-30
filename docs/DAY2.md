# Day 2 - 3D Anatomical Mesh Reconstruction

## 1. Objective
Convert TotalSegmentator's 3D anatomical segmentation masks into 3D surface meshes suitable for interactive rendering and physical measurement. We aim to translate volumetric mask data into polygonal surfaces using the Marching Cubes algorithm while preserving correct physical coordinates.

## 2. What We Started With
At the start of Day 2, we had a fully segmented CT volume. The TotalSegmentator model had produced 117 individual anatomical segmentation masks in NIfTI (`.nii.gz`) format. NIfTI files store the image as a 3D grid of voxels along with metadata (the affine matrix and voxel dimensions) that map the grid to real-world physical space.

## 3. What Is a Segmentation Mask?
Unlike an original CT scan where every voxel has a continuous intensity value (measured in Hounsfield Units) corresponding to tissue density, a **segmentation mask** is a simplified map. It typically consists of binary values (0s and 1s). For example, in the `liver.nii.gz` mask, a voxel value of 1 means "this voxel is part of the liver" (foreground) and 0 means "this voxel is not part of the liver" (background).

## 4. Why Convert Masks to Meshes?
A segmentation mask is a **volumetric** representation (a solid 3D grid of blocks). While useful for mathematical operations (like calculating total volume by counting voxels), it is very expensive to render directly in a web browser using WebGL/Three.js. By converting the mask to a **surface mesh** (a hollow shell made of triangles), we vastly reduce the data size and create a format natively supported by standard 3D engines, allowing for smooth, interactive 3D visualization.

## 5. What Is Marching Cubes?
Marching Cubes is an algorithm used to extract a polygonal mesh (an **isosurface**) from a 3D scalar field (our grid of voxels). Conceptually, the algorithm "marches" a hypothetical cube through the voxel grid. At each step, it looks at the 8 corners of the cube. Based on whether each corner is inside (value=1) or outside (value=0) the anatomical structure, the algorithm determines how the surface intersects the cube. It then places **vertices** (points) at the intersections and connects them into **triangles** (faces) to form a continuous skin around the organ.

## 6. Understanding Voxel Spacing
A voxel is a 3D pixel. If a CT scanner captures an image where each voxel represents 1mm x 1mm x 1mm of physical space, the spacing is `(1, 1, 1)`. If we run Marching Cubes assuming a spacing of `(1, 1, 1)`, a mesh that spans 10 voxels will be exactly 10 units wide.

However, our CT scan was taken with a voxel spacing of `(1.5, 1.5, 1.5)`. This means each voxel represents 1.5 millimeters of real physical distance. If we ignore this and use `(1, 1, 1)`, the resulting mesh will be shrunken. By explicitly passing `spacing=(1.5, 1.5, 1.5)` into the algorithm, the resulting vertex coordinates are correctly scaled to millimeters, meaning physical distances measured on the mesh will match the real-world organ.

## 7. NIfTI Metadata Used
To handle the spacing correctly, we extracted metadata directly from the NIfTI header:
- **Shape:** The physical dimensions of the grid array, e.g., `(293, 293, 344)`.
- **Zooms / Voxel Spacing:** The size of each voxel in mm, retrieved via `img.header.get_zooms()`. For our scan, it returned `(1.5, 1.5, 1.5)`.
- *(Note on Affine Matrix)*: NIfTI files also contain an affine matrix which defines the exact rotation, scaling, and translation relative to the scanner's isocenter. For this MVP, extracting the scaling (zooms) is sufficient to generate physically accurate bounding boxes.

## 8. Code Architecture
We created a cleanly isolated module for this task to adhere to good engineering practices.
- `src/mesh/mesh_generator.py`: The core script that loads NIfTI files, runs the `skimage` Marching Cubes algorithm, and exports standard `.obj` files.
- `outputs/meshes/`: The directory where the finalized 3D meshes are saved (excluded from Git).

## 9. Important Functions
### `load_mask(mask_path)`
- **Input:** A `Path` object pointing to a `.nii.gz` mask.
- **Output:** A binary NumPy array and a tuple representing voxel spacing.
- **Purpose:** Safely loads the NIfTI file, binarizes the mask (values > 0.5 become 1), and extracts the zooms.

### `generate_mesh_from_mask(mask_data, spacing)`
- **Input:** The binary voxel array and the spacing tuple.
- **Output:** A list of `verts` (vertex coordinates) and `faces` (triangles).
- **Purpose:** Executes `skimage.measure.marching_cubes` at an isosurface `level` of 0.5, using the `spacing` parameter to ensure physical coordinates.

### `save_mesh_as_obj(filepath, verts, faces)`
- **Input:** The output file path, vertices, and faces.
- **Output:** None (Writes a file).
- **Purpose:** Manually formats and writes a Wavefront `.obj` file. This format is ubiquitous, text-based, and easy to parse later in Three.js without requiring bulky 3D export libraries.

## 10. Actual Experiment
We tested the generator on four key anatomical structures.

**Liver**
- Mask shape: (293, 293, 344)
- Voxel spacing: (1.5, 1.5, 1.5) mm
- Foreground voxels: 753,016
- Vertices: 91,064
- Faces: 182,152
- Bounding Box: Min [131.25, 104.25, 254.25], Max [357.75, 321.75, 482.25]
- Dimensions (mm): 226.50 x 217.50 x 228.00
- Runtime: 1.78 seconds

**Heart**
- Foreground voxels: 215,220
- Vertices: 36,218
- Faces: 72,134
- Dimensions (mm): 178.50 x 121.50 x 89.25
- Runtime: 1.42 seconds

**Aorta**
- Foreground voxels: 53,732
- Vertices: 18,724
- Faces: 37,266
- Dimensions (mm): 64.50 x 133.50 x 296.25
- Runtime: 1.35 seconds

**Left Kidney**
- Foreground voxels: 70,496
- Vertices: 18,272
- Faces: 36,540
- Dimensions (mm): 84.00 x 75.00 x 114.00
- Runtime: 1.30 seconds

## 11. Results
Mesh generation was extremely successful. The script ran rapidly (under 2 seconds per organ) and exported valid Wavefront `.obj` files that accurately reflect the physical dimensions of the organs.

## 12. Validation
We verified the meshes by explicitly printing the bounding box dimensions during execution. For example, a liver dimension of ~22cm and an aorta length of ~30cm aligns perfectly with human anatomical expectations, proving that our voxel spacing multiplier worked correctly. 

## 13. What I Learned
### Technical Skills
- **Modular Design:** Isolating the mesh generation logic from the AI segmentation logic keeps the codebase maintainable and testable.
- **CLI Design:** Using Python's `argparse` to allow batch processing of specific organs (e.g., `--organs liver heart`).
- **File Handling:** Utilizing standard, dependency-free text writing to generate `.obj` files, avoiding bloat.
- **Debugging & Validation:** Proactively calculating bounding boxes to ensure transformations didn't result in miniature or microscopic meshes.

### Medical Imaging Concepts
- **Voxel to Surface:** Understanding the fundamental difference between volumetric grids (masks) and boundary representations (meshes).
- **Physical Spacing:** The crucial importance of multiplying array indices by the scanner's voxel dimensions to reconstruct real-world measurements.
- **Isosurfaces:** The mathematical concept of finding a boundary threshold (0.5) to draw the skin of an organ.

## 16. Day 2 Limitations
- **No Smoothing/Decimation:** The Marching Cubes algorithm generates a very dense "stair-stepped" mesh. Without Laplacian smoothing or decimation, the meshes might look slightly blocky and contain a high polygon count. This was skipped to keep the MVP simple.
- **Coordinate Transformations:** We only used the zoom/scaling from the affine matrix. We did not apply full rotational transforms to align the meshes to a specific coordinate system (like RAS or LPS), which is acceptable for isolated 3D viewing but might require adjustments if merging with other modalities.
- **No Volume Calculations:** We know the bounding box, but exact physical volume is not calculated here (saved for Day 4).

## 17. Next Step
With the `.obj` meshes successfully generated, Day 3 will focus on building an interactive 3D anatomy viewer to render these meshes natively in a browser/window context.
