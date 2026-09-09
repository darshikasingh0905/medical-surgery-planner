# Day 7: Live Frontend ↔ Backend Integration

## Overview

Day 7 connects the existing React/Vite frontend to the live FastAPI backend, replacing all static hardcoded data with real pipeline results. After this milestone, a user can upload a CT scan through the browser, watch the backend pipeline process it, and view real 3D anatomical meshes with live measurements — no static files, no hardcoded values.

The backend pipeline (TotalSegmentator, mesh generation, measurement engine, FastAPI routes) was completed in Days 1–6 and is **not modified** in Day 7.

---

## Architecture

```
Browser (React/Vite :5173)
    │
    │  /api/* proxied by Vite dev server
    ▼
FastAPI (:8000)
    ├── POST /api/cases/upload      ← receives .nii/.nii.gz file
    ├── GET  /api/cases/{id}        ← status polling
    ├── GET  /api/cases/{id}/results ← organ measurements
    ├── GET  /api/cases/{id}/meshes/{organ} ← OBJ mesh files
    └── GET  /api/health            ← connectivity check
```

The Vite dev server is configured with a proxy (`/api → http://127.0.0.1:8000`) so the React app uses relative URLs. This eliminates CORS issues in development and means mesh URLs work directly in `useLoader` without any extra configuration.

---

## Files Created / Modified

### New Files

| File | Purpose |
|---|---|
| `frontend/src/api.js` | Centralized API client — all `fetch()` calls live here |
| `frontend/src/UploadPanel.jsx` | CT scan upload UI with drag-and-drop |
| `frontend/src/StatusPanel.jsx` | Processing status display during pipeline execution |
| `docs/DAY7.md` | This document |

### Modified Files

| File | What Changed |
|---|---|
| `frontend/vite.config.js` | Added `server.proxy` to forward `/api` to `:8000` |
| `frontend/src/data.js` | Removed hardcoded `file`, `volume`, `dimensions`; kept `id`, `name`, `color` |
| `frontend/src/App.jsx` | Full state machine, health check, upload handler, polling, results fetch |
| `frontend/src/Viewer3D.jsx` | Accepts `meshUrls` prop; per-organ `ErrorBoundary`; no static paths |
| `frontend/src/InfoPanel.jsx` | Accepts `organResults` from backend; graceful fallback to "Not available" |
| `frontend/src/Sidebar.jsx` | Added ARIA attributes, "New Scan" reset button in footer |
| `frontend/src/index.css` | Additive: upload/status screen styles, header improvements |

### Unchanged

- All Python files under `src/`
- `src/api/main.py`, `src/api/routes/cases.py`
- `src/pipeline/`, `src/segmentation/`, `src/mesh/`, `src/measurements/`
- `tests/`

---

## Upload Flow

```
1. User selects .nii or .nii.gz file via file picker or drag-and-drop
2. Client validates extension (client-side, before fetch)
3. POST /api/cases/upload  (multipart/form-data, field name: "file")
   ← { case_id, filename, status: "uploaded" }
4. caseId stored in React state
5. Polling begins immediately (2-second interval)
```

### File Validation (Client-Side)
- Extension must end with `.nii` or `.nii.gz`
- File must be selected before upload button becomes active
- Backend also validates — client-side check provides faster feedback only

---

## API Client (`api.js`)

All communication with the backend goes through `frontend/src/api.js`. No `fetch()` calls exist directly in components.

### Functions

```js
healthCheck()          // GET /api/health
uploadCase(file)       // POST /api/cases/upload
getCaseStatus(caseId)  // GET /api/cases/{case_id}
getCaseResults(caseId) // GET /api/cases/{case_id}/results
getMeshUrl(caseId, org) // Returns relative URL string (no fetch)
```

### Error Handling
- Network failures → `"Cannot reach the backend server…"` (never exposes stack traces)
- Non-2xx responses → `body.detail` from FastAPI or generic HTTP error
- All errors are plain `Error` objects with user-facing messages

---

## Application State Machine

```
initial ──(upload)──► uploading ──(success)──► processing ──(completed)──► completed
                           │                        │
                      (failure)               (failed)
                           │                        │
                           └────────► failed ◄──────┘
                                          │
                                     (onReset)
                                          │
                                       initial
```

| State | UI Shown | Description |
|---|---|---|
| `initial` | `UploadPanel` | Awaiting file selection |
| `uploading` | `StatusPanel` | File being sent to backend |
| `processing` | `StatusPanel` | Backend pipeline running; polling active |
| `completed` | `Viewer3D` + `Sidebar` + `InfoPanel` | Results ready |
| `failed` | `StatusPanel` (error) | Upload or pipeline error |

---

## Polling

After a successful upload, the frontend polls `GET /api/cases/{case_id}` every **2 seconds** using `setInterval`.

- First poll fires **immediately** (no 2s wait on first check)
- Polling **stops** when status is `completed` or `failed`
- Interval is **cleared on component unmount** via `useEffect` cleanup
- Network errors during polling are logged to console but do not crash the app or stop polling

### Status → UI Mapping

| Backend `status` | StatusPanel message |
|---|---|
| `uploaded` | "Scan received. Queued for processing…" |
| `processing` | "Processing scan… Generating 3D anatomical models…" |
| `completed` | (polling stops; Viewer3D appears) |
| `failed` | "Processing failed." + `data.error` |

> **No fake percentages** are shown. Progress indicators are derived from the actual `status` field only.

---

## Result Retrieval

When polling returns `status === "completed"`:
1. Polling stops
2. `GET /api/cases/{case_id}/results` is called
3. Response shape: `{ case_id, status, organs: { liver: {...}, heart: {...}, ... } }`
4. `organs` is stored in React state and passed to `InfoPanel` via `organResults` prop

If the results fetch fails (network or 500 error), the viewer still shows meshes and `InfoPanel` shows "Not available" for all fields — the app does not crash.

---

## Dynamic Mesh Loading

Mesh URLs are built dynamically using `getMeshUrl(caseId, organ)` which returns:
```
/api/cases/<case_id>/meshes/<organ>
```

These relative URLs are passed to Three.js `useLoader(OBJLoader, url)` via the `meshUrls` prop of `Viewer3D`.

### Supported Organs
| Key | Display Name |
|---|---|
| `liver` | Liver |
| `heart` | Heart |
| `aorta` | Aorta |
| `kidney_left` | Left Kidney |

### Graceful Degradation
Each organ is wrapped in a `OrganErrorBoundary`. If one mesh fails to load (404, malformed OBJ, network error), that organ is silently skipped — the remaining 3 organs continue to render.

Static files in `frontend/public/meshes/` are **not used** by the live workflow. They can remain for reference.

---

## Measurements (InfoPanel)

`InfoPanel` receives `organResults` from the backend for the selected organ.

Expected measurement fields:

| Field | Display Label | Fallback |
|---|---|---|
| `mask_volume_ml` | Mask Volume | "Not available" |
| `mesh_volume_ml` | Mesh Volume | "Not available" |
| `bounding_box` | Bounding Box | "Not available" |

The bounding box formatter handles multiple key shapes from the measurement engine:
- `{ x_mm, y_mm, z_mm }`
- `{ width_mm, height_mm, depth_mm }`
- `{ x, y, z }`
- fallback: `JSON.stringify(bbox)`

---

## Health Check

On application mount, `healthCheck()` is called to `GET /api/health`.

- **Backend online** → Green "Backend connected" indicator in the header
- **Backend offline** → Red "Backend offline" indicator (non-blocking)
- The app loads regardless; the indicator is purely informational

---

## Error Handling Summary

| Scenario | Handled |
|---|---|
| Wrong file type selected | Client-side: drop zone ignores, button stays disabled |
| Empty file selection | Upload button disabled |
| Backend unreachable on upload | Error shown in UploadPanel, state resets to `initial` |
| Backend returns 4xx/5xx | User-friendly message from `body.detail` |
| Polling network error | Logged to console; polling continues |
| Processing failed (backend) | `StatusPanel` shows error + "Try Again" button |
| Mesh 404 | `OrganErrorBoundary` catches silently; rest of scene intact |
| Results fetch fails | `InfoPanel` shows "Not available" for all fields |
| No organ selected | `InfoPanel` shows "Select an organ" prompt |

---

## How to Run

### Prerequisites
- Python venv with all requirements installed
- Node.js with `npm`

### Start Backend
```powershell
# From project root
.\.venv\Scripts\activate
python -m uvicorn src.api.main:app --reload
```
Backend will be available at `http://127.0.0.1:8000`.
Swagger docs: `http://127.0.0.1:8000/docs`

### Start Frontend
```powershell
cd frontend
npm run dev
```
Frontend will be available at `http://localhost:5173`.

### Build (Production)
```powershell
cd frontend
npm run build
```
Output goes to `frontend/dist/`.

---

## Manual End-to-End Test Checklist

1. ☐ Start FastAPI (`uvicorn src.api.main:app --reload`)
2. ☐ Start React (`npm run dev`)
3. ☐ Open `http://localhost:5173` — upload screen appears
4. ☐ "Backend connected" indicator visible in header
5. ☐ Select a `.nii.gz` CT scan → filename shown in drop zone
6. ☐ Click "Begin Analysis" → status transitions to "Uploading…"
7. ☐ Case ID appears in status card
8. ☐ Status transitions: "Queued" → "Processing"
9. ☐ Status transitions to "Analysis complete" (completed)
10. ☐ 3D viewer appears with organ meshes
11. ☐ Toggle organ visibility buttons work
12. ☐ Select "Liver" → InfoPanel shows backend measurements
13. ☐ Select "Heart" → InfoPanel measurements update
14. ☐ Rotate / zoom / pan the model
15. ☐ Click "New Scan" → returns to upload screen

---

## Known Limitations

1. **Polling only** — No WebSocket/SSE push. The frontend must poll every 2s. For single-user MVP this is acceptable.
2. **4 organs only** — TotalSegmentator produces 117 masks. Only liver, heart, aorta, kidney_left are meshed.
3. **Single-process backend** — `BackgroundTasks` runs in the same process. Not suitable for multi-user production load.
4. **No upload progress** — `POST /api/cases/upload` does not stream progress. Large files show "Uploading…" until complete.
5. **No persistent case list** — Refreshing the page loses the case ID. Cases are still accessible on disk via the backend.
6. **Mesh cache** — `useLoader` caches OBJ by URL. Uploading a new scan with the same organ names uses the new case_id URL so caching is not an issue.

---

## Medical Safety Disclaimer

This system is an **AI-assisted preoperative planning prototype** intended for research and educational use only.

All outputs — including segmentation masks, 3D meshes, and volumetric measurements — are **computational estimates and decision-support information**. They require clinical review by a qualified medical professional before any clinical use.

This system:
- Does **not** provide autonomous diagnosis
- Does **not** provide autonomous surgical planning  
- Is **not** clinically validated
- Is **not** a replacement for a surgeon or radiologist

---

## Next Milestones (Not Implemented in Day 7)

- Tumor detection
- LLM-powered surgical planning assistant
- PDF report generation
- DICOM format support
- WebSocket push notifications
- Support for all 117 TotalSegmentator organs
- Multi-user / distributed task queue
