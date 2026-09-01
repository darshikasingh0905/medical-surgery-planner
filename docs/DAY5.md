# Day 5: Web Application Layer

## Overview
On Day 5, we transitioned the Medical Surgery Planner from a desktop-only Python visualization pipeline (using PyVista/VTK) to a modern, browser-based React application using Three.js. This lays the foundation for building the full web application layer without introducing the complexities of a backend API or authentication just yet.

## Architecture & Technology Stack
- **React**: For UI state management, components, and layout.
- **Vite**: For blazing-fast frontend bundling and development.
- **Three.js & React Three Fiber (R3F)**: Provides declarative 3D rendering in the browser, replacing PyVista.
- **Drei**: Helpful utilities for R3F, specifically providing the `OrbitControls` and `GizmoHelper`.

## Why Move to Three.js?
While PyVista is excellent for rapid prototyping and validation of VTK data within a Python pipeline, building a production-grade clinical application requires:
1. **Accessibility**: Doctors and surgeons should be able to view cases through a standard web browser without installing Python or specific desktop dependencies.
2. **Custom UI/UX**: Web technologies like React and CSS offer infinitely more flexibility for creating professional, clean, and dynamic medical interfaces compared to PyVista's basic Qt/Tkinter integrations.
3. **Integration**: A web frontend naturally integrates with standard backend architectures (e.g., FastAPI) and cloud deployment platforms.

## Asset Loading & Data Strategy
Because the `.obj` meshes generated on Day 2 are currently git-ignored in the `outputs/meshes/` directory (to avoid bloating the repository with large binaries), we adopted a clean local development approach:
- The OBJ files were copied into the Vite application's `public/meshes/` directory.
- This allows them to be served locally as static assets and loaded via Three.js's `OBJLoader`.
- The measurement values (Volume, Dimensions) computed on Day 4 were exported into a static data file (`src/data.js`) for immediate use, decoupling the frontend from a live Python backend for now.

## Features Implemented
- **3D Viewer (`Viewer3D.jsx`)**: Loads all four organs simultaneously with appropriate colors and materials (smooth shading with `computeVertexNormals`).
- **Interactive Controls**: Users can pan, orbit, and zoom using standard mouse controls. An XYZ orientation helper is included.
- **Organ Selection & Visibility (`Sidebar.jsx`)**: Users can toggle the visibility of individual organs (Liver, Heart, Aorta, Left Kidney) to focus on specific anatomy, and select an organ to see its details.
- **Measurement Display (`InfoPanel.jsx`)**: Displays the Day 4 mask-based computational estimates for volume and bounding box dimensions.
- **Responsive Layout**: Designed with a clean, clinical aesthetic using CSS variables, ensuring the 3D canvas correctly resizes with the window.

## Testing Performed
- Started the React dev server successfully (`npm run dev`).
- Verified zero console errors in the browser.
- All four OBJ meshes loaded correctly and appear in the same coordinate space.
- Verified orbit, zoom, and pan functionalities.
- Confirmed that toggling visibility updates the scene instantly.
- Verified that selecting an organ correctly updates the Info panel with Day 4 measurements.
- Executed `npm run build` to confirm the production build completes successfully.

## Limitations
- **No Backend**: Measurement values are currently hardcoded in `data.js`. A real backend (e.g., FastAPI) will be needed to serve dynamic patient data and meshes.
- **Asset Duplication**: Copying meshes to the `public` folder is a temporary solution for frontend development; eventually, these will likely be served by an API or object storage (S3).
- **Lighting/Materials**: Basic `meshStandardMaterial` is used. Medical applications often require more advanced shaders (e.g., subsurface scattering or transparency for vessels).
