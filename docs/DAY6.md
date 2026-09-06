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

## Next Steps (Phase 1)
The next major step will be to connect the uploaded scans to our existing pipeline:
1. Upload scan via API -> Returns Case ID.
2. Trigger a background task to run TotalSegmentator on `outputs/cases/<case_id>/input/scan.nii.gz`.
3. Save resulting masks to `outputs/cases/<case_id>/segmentation/`.
4. Trigger mesh generation -> Save to `outputs/cases/<case_id>/meshes/`.
5. Trigger measurements -> Save to `outputs/cases/<case_id>/measurements/`.
6. Update case status so frontend can poll and display the results.

---

## Phase 2: Pipeline Integration

### Overview
Phase 2 connects the FastAPI upload endpoint to the **existing** Day 1–4 Python medical-imaging pipeline. Uploading a CT/MRI scan now automatically triggers background processing that runs TotalSegmentator segmentation, Marching Cubes mesh generation, and the measurement engine — all without blocking the HTTP response.

### Background Processing
TotalSegmentator is computationally expensive and must **not** run synchronously inside the upload request. We use FastAPI's built-in `BackgroundTasks` mechanism:

1. The upload endpoint saves the file and returns the `case_id` immediately.
2. A background task calls `process_case_background(case_id)` which orchestrates the full pipeline.
3. The frontend can poll `GET /api/cases/{case_id}` to track progress.

No external infrastructure (Celery, Redis, Docker) is needed for this MVP.

### Case Status Lifecycle
Each case transitions through the following states, persisted in `outputs/cases/<case_id>/case.json`:

```
uploaded → processing → completed
                      → failed (with error message)
```

| Status | Meaning |
|--------|---------|
| `uploaded` | File saved, background processing queued |
| `processing` | Pipeline is running (segmentation, mesh gen, measurements) |
| `completed` | All outputs generated successfully |
| `failed` | An error occurred; `error` field contains a description |

### Processing Flow
```
POST /api/cases/upload
    ↓
Save file → Create case.json (status: uploaded)
    ↓
Queue background task → Return case_id immediately
    ↓
Background:
    1. Update status → "processing"
    2. Run TotalSegmentator → outputs/cases/<id>/segmentation/
    3. Run Marching Cubes for [liver, heart, aorta, kidney_left] → outputs/cases/<id>/meshes/
    4. Run measurement engine → outputs/cases/<id>/measurements/results.json
    5. Update status → "completed" (or "failed")
```

### Output Directory Structure
```
outputs/cases/<case_id>/
    case.json               # Status and metadata
    input/
        scan.nii.gz         # Original uploaded scan
    segmentation/
        liver.nii.gz        # 117 TotalSegmentator masks
        heart.nii.gz
        aorta.nii.gz
        kidney_left.nii.gz
        ...
    meshes/
        liver.obj           # Marching Cubes OBJ meshes
        heart.obj
        aorta.obj
        kidney_left.obj
    measurements/
        results.json        # Structured measurement data
```

### API Endpoints (Updated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/cases/upload` | Upload scan, triggers background processing |
| `GET` | `/api/cases/{case_id}` | Case status with results summary |
| `GET` | `/api/cases/{case_id}/results` | Detailed measurement data per organ |
| `GET` | `/api/cases/{case_id}/meshes/{organ}` | Download generated OBJ mesh file |

### Existing Modules Reused
The following Day 1–4 modules are called directly by the pipeline orchestrator — **none were rewritten**:

- `src.segmentation.ai_segmenter.run_segmentation()` — TotalSegmentator wrapper
- `src.mesh.mesh_generator.process_organ()` — Marching Cubes mesh extraction
- `src.measurements.measurement_engine.calculate_mask_volume()` — Mask-based volume
- `src.measurements.measurement_engine.calculate_mesh_volume()` — Mesh-based volume
- `src.measurements.measurement_engine.calculate_bounding_box()` — Bounding box dimensions
- `src.measurements.measurement_engine.compare_volumes()` — Volume comparison

### Testing
- **Automated**: 9 tests covering health, upload, status, results, meshes, and error cases — all pass with mocked pipeline.
- **Manual**: Real pipeline test with existing CT scan verifies end-to-end flow.

### Known Limitations
- Background processing uses in-process threads (not a distributed task queue). Only suitable for single-user MVP.
- Only 4 organs are meshed (liver, heart, aorta, kidney_left). TotalSegmentator produces 117 masks.
- No WebSocket/SSE push notifications — frontend must poll for status.
- Tumor detection is **not** part of this phase.

### Medical Safety Disclaimer
This system is an **AI-assisted preoperative planning prototype**. All outputs are **decision-support information requiring clinical review** by qualified medical professionals. It does not provide autonomous diagnosis or surgical planning.
