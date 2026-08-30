# Technical Reference: 3D Viewer (PyVista/VTK)

## Overview
The `anatomy_viewer.py` module is a lightweight, Python-native 3D visualization tool. It serves as a diagnostic and validation viewer for the 3D meshes generated from medical segmentation masks. It relies on PyVista, which acts as a simplified interface to the powerful VTK (Visualization Toolkit) backend.

## File Architecture
- `src/visualization/anatomy_viewer.py`: The main script executable via CLI.

## Core Concepts
### 1. `pv.PolyData`
This is PyVista's fundamental object for representing surface meshes. It stores `points` (an N x 3 array of XYZ coordinates) and `faces` (connectivity arrays defining how points form triangles).

### 2. `pv.Plotter`
The Plotter manages the rendering window, the scene graph, and user interactions. 
Calling `plotter.show()` triggers the VTK render loop, opening a desktop window.

### 3. Actors and Mappers
When `plotter.add_mesh(mesh)` is called, PyVista automatically:
1. Creates a VTK Mapper to process the geometry for rendering.
2. Creates a VTK Actor to represent the object in the scene.
3. Attaches material properties (color, lighting, smooth shading) to the Actor.

### 4. Smooth Shading
Medical meshes extracted via Marching Cubes are highly jagged due to the underlying voxel grid. Enabling `smooth_shading=True` in `add_mesh` calculates surface normals at the vertices rather than the faces, resulting in interpolated Gouraud shading across the polygons. This makes the mesh look smooth and organic without needing to physically alter the geometry.

## API Reference
- `load_mesh(Path)`: Uses `pv.read()` to parse `.obj` files into `PolyData`.
- `create_scene()`: Instantiates the `pv.Plotter` with a black background and coordinate axes.
- `add_organ(plotter, mesh, name, color)`: Adds the PolyData to the scene with assigned aesthetics.
- `print_mesh_stats(organ_name, mesh)`: Extracts `mesh.n_points`, `mesh.n_cells`, and `mesh.bounds` for validation.

## Command Line Usage
The viewer is designed to be run from the root directory:

**Interactive Mode (Default):**
```bash
python -m src.visualization.anatomy_viewer
```
*Loads the default organs (liver, heart, aorta, kidney_left) and opens the 3D window.*

**Test Mode:**
```bash
python -m src.visualization.anatomy_viewer --test-mode
```
*Loads the meshes, prints structural statistics to the console, renders a frame off-screen, and exits immediately. Useful for automated validation.*

## Interactive Controls
- **Rotate:** Left Click + Drag
- **Pan:** Middle Click + Drag (or Shift + Left Click + Drag)
- **Zoom:** Right Click + Drag (or Scroll Wheel)

## Bounding Box & Dimensions
The `mesh.bounds` property returns a tuple of 6 values: `(X_min, X_max, Y_min, Y_max, Z_min, Z_max)`.
Physical dimensions are calculated by subtracting the minimums from the maximums for each axis. Because our meshes were scaled by the NIfTI voxel spacing during generation, these dimensions represent true physical millimeters.
