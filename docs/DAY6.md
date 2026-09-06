# Day 6: FastAPI Backend Bridge

## Overview

On Day 6, we implemented the initial FastAPI backend to serve as the bridge between the React frontend and the Python medical-imaging pipeline. Up until this point, the frontend was relying on static files directly copied into its `public/` directory. The new backend establishes a structured REST API that will eventually handle file uploads, trigger the segmentation pipeline, and serve the resulting 3D meshes and measurement data back to the frontend.

## Why FastAPI?

FastAPI was chosen for several reasons:
- **Performance**: It's one of the fastest Python frameworks available, built on Starlette and Pydantic.
- **Validation**: It uses Python type hints and Pydantic for automatic data validation, ensuring the frontend sends the correct data.
- **Documentation**: It automatically generates interactive API documentation (Swagger UI).
- **Asynchronous**: It natively supports asynchronous endpoints (`async def`), which is crucial for handling long-running tasks like medical image segmentation (TotalSegmentator) without blocking the main thread.

## Architecture & REST APIs

REST (Representational State Transfer) APIs provide a standard way for our separate frontend (React) and backend (Python) applications to communicate over HTTP. The backend exposes endpoints (URLs) that the frontend can call to upload scans, check status, and retrieve results. 

This decoupling ensures that:
- The React application focuses solely on user interface and 3D visualization.
- The Python backend securely manages the complex dependencies required for medical imaging (PyTorch, nibabel, TotalSegmentator).

## Case Management

### Case IDs
Every uploaded scan receives a unique **Case ID** (a UUID). This is essential because:
1. It prevents file name collisions if multiple patients have scans named `scan.nii.gz`.
2. It allows us to group all related files (input scan, segmentation masks, generated meshes, measurement reports) under a single, traceable identifier.

### Storage Structure
Uploaded scans and their subsequent outputs are stored in `outputs/cases/<case_id>/`. The structure is designed for scalability:
```
outputs/
    cases/
        <case_id>/
            input/          # Original uploaded scan
            segmentation/   # Masks from TotalSegmentator
            meshes/         # Generated OBJ/GLTF files
            measurements/   # Calculated volumes/dimensions
```
*Note: The `outputs/` directory is Git-ignored because it contains large, dynamically generated, and potentially sensitive data.*

## Current API Endpoints

- `GET /api/health`: Verifies the backend is running.
- `POST /api/cases/upload`: Accepts `.nii` or `.nii.gz` files, generates a Case ID, and saves the file.
- `GET /api/cases/{case_id}`: Retrieves the status and basic information of a specific case.

## What is Intentionally NOT Implemented Yet

To maintain a reliable development process, the following features are intentionally delayed:
- **Automatic Pipeline Execution**: Uploading a scan does *not* yet trigger TotalSegmentator. We first need a reliable API layer. Next, we will connect the existing Day 1-4 pipeline to this API.
- **Tumor Detection**: This requires a specialized model and will be added later in the project.
- **AI Chatbot**: The LLM integration for patient explanations will be implemented as a separate feature once the core medical pipeline is complete.

## Next Steps
The next major step will be to connect the uploaded scans to our existing pipeline:
1. Upload scan via API -> Returns Case ID.
2. Trigger a background task to run TotalSegmentator on `outputs/cases/<case_id>/input/scan.nii.gz`.
3. Save resulting masks to `outputs/cases/<case_id>/segmentation/`.
4. Trigger mesh generation -> Save to `outputs/cases/<case_id>/meshes/`.
5. Trigger measurements -> Save to `outputs/cases/<case_id>/measurements/`.
6. Update case status so frontend can poll and display the results.
