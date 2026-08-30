# Day 3 - Interactive 3D Anatomical Viewer

## 1. Objective
Build an interactive 3D anatomy viewer to validate and display the generated Wavefront `.obj` meshes from Day 2. The viewer must render multiple anatomical structures in the same 3D scene, assign distinct colors to each organ, and provide interactive camera controls (pan, zoom, rotate).

## 2. Starting Inputs
- **Generated `.obj` meshes:** We used the meshes created in Day 2 (`liver.obj`, `heart.obj`, `aorta.obj`, `kidney_left.obj`).
- **Python Environment:** The virtual environment (`.\venv`) already had standard dependencies, plus the recently installed `pyvista` and `vtk` libraries.

## 3. Why PyVista/VTK Was Selected
While the final goal for Day 5 is a React/Three.js web frontend, building a web app directly is complex and time-consuming. We need a fast, reliable, and native way to visually validate that our generated `.obj` meshes are anatomically correct and properly aligned. 
**VTK (Visualization Toolkit)** is the gold standard for scientific 3D rendering. **PyVista** is a streamlined, Pythonic wrapper around VTK that allows us to create interactive 3D plots with minimal boilerplate code. It easily handles large polygon counts typical of medical meshes.

## 4. How OBJ Meshes Are Loaded
We used `pv.read(file_path)` from PyVista. Under the hood, this utilizes VTK's Wavefront OBJ reader to parse the text file into a `pv.PolyData` object. `PolyData` represents surface geometry, consisting of points (vertices) and cells (faces/triangles).

## 5. What Is a Mesh Actor?
In 3D graphics (and specifically in VTK), there is a separation between the *data* and its *visual representation*. 
- The **Mapper** processes the geometry data.
- The **Actor** is the entity that actually exists in the scene. The Actor holds properties like color, opacity, position, and shading (e.g., smooth vs. flat). When we call `plotter.add_mesh()`, PyVista automatically creates both a Mapper and an Actor for us.

## 6. How the 3D Scene Works
The `pv.Plotter` object acts as the renderer and the window. We configure it with a black background (standard for medical imaging software) and add our meshes to it. The Plotter manages the render loop and the user interface window.

## 7. Camera and Interaction
By default, `pv.Plotter` attaches an interactive camera to the scene. 
- **Left-click + Drag:** Rotates the camera around the focal point.
- **Right-click + Drag / Scroll Wheel:** Zooms the camera in and out.
- **Middle-click + Drag (or Shift + Left-click):** Pans the camera.
We also added `plotter.add_axes()` which places a persistent XYZ coordinate widget in the corner to help maintain spatial orientation.

## 8. Organ Visualization
To make the scene comprehensible, we assigned specific colors to each organ via an `ORGAN_COLORS` dictionary:
- Liver: Dark Red
- Heart: Salmon
- Aorta: Red
- Left Kidney: Yellow

We enabled `smooth_shading=True`, which calculates vertex normals to make the jagged triangles appear as a smooth continuous surface, crucial for biological tissue representation.

## 9. Testing Results
The script was tested using the `--test-mode` flag.
- **Liver:** 91,064 points, Dimensions 226.50 x 217.50 x 228.00 mm
- **Heart:** 36,218 points, Dimensions 178.50 x 121.50 x 89.25 mm
- **Aorta:** 18,724 points, Dimensions 64.50 x 133.50 x 296.25 mm
- **Kidney:** 18,272 points, Dimensions 84.00 x 75.00 x 114.00 mm
The point counts and physical dimensions match our Day 2 calculations exactly. All 4 meshes loaded seamlessly.

## 10. Dependencies Added
- `pyvista`
- `vtk` (was previously installed as a TotalSegmentator dependency, but is now explicitly required by our visualization module).

## 11. Limitations
- **Local Application Only:** This viewer runs as a local desktop window. It cannot be shared via a web browser.
- **No Advanced Shaders:** We are using basic solid colors. Medical viewers often use transparency (opacity) or volume rendering, which we kept simple for this MVP.
- **No Measurement Tools:** The viewer currently only displays the organs. Interactive measurement tools (like distance rulers) are not yet implemented.

## 12. What Was Learned
- **3D Graphics Architecture:** The separation of mesh data (`PolyData`), rendering components (Mappers), and visual entities (Actors).
- **Rapid Prototyping:** How to use PyVista to instantly visualize geometric data without setting up a complex game engine or web framework.
- **Validation:** Confirming that the physical coordinate scaling applied during Day 2 (using NIfTI voxel spacing) successfully aligned all independent organs correctly in a shared 3D coordinate space.

## 13. Next Step
Proceed to **Day 4: Measurements**. We will programmatically calculate organ volumes (using the closed mesh volumes or voxel counts) and potentially basic anatomical distances, laying the groundwork for the analytical portion of the preoperative planner.
