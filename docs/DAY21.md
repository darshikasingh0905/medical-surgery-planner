# DAY 21 — Preoperative Procedure Explanation Engine
## Milestone Report: Structured, Traceable Preoperative Procedure Explanation

### Milestone Status: Complete ✅
- **Focus**: Structured, deterministic procedural explanation transforming computational imaging outputs into traceable clinical context.
- **Safety Boundary**: Strict adherence to research and educational prototype constraints.
  - Zero autonomous medical diagnoses
  - Zero malignancy or staging determinations
  - Zero surgical procedure or operative approach recommendations
  - Full provenance and source traceability
- **Architecture**: Modular Pydantic schemas, deterministic aggregation service, dual REST endpoints, interactive React panel with audience adaptation, and dedicated test coverage.

---

## 1. Executive Summary & Clinical Governance Boundary

Day 21 delivers the **Preoperative Procedure Explanation Engine**, designed to bridge the gap between low-level computational outputs (segmentation masks, Euclidean distance matrices, voxel coordinates) and readable, structured clinical explanations—without overstepping medical device boundaries.

### Strict Governance Policy
This system operates under the following product and safety boundaries:
1. **Research & Educational Prototype Only**: The output does not constitute medical advice or clinical decision-making.
2. **Deterministic Data Transformation**: All explanations are synthesized deterministically from existing validated case metadata and segmentations. No non-deterministic generative LLMs are used for clinical claims.
3. **Audience Adaptation**: Provides distinct representation layers:
   - **Technical View**: Detailed voxel/physical metrics, standard anatomical terminology, algorithm provenance, and explicit limitation registries.
   - **General View**: Plain-language summaries, patient-accessible explanations of imaging findings, and transparent declarations of non-diagnostic scope.
4. **Mandatory Clinical Review Items**: Explicit enumeration of clinical variables that **cannot** be computed by CT segmentations and require human clinician/urologist evaluation (e.g., histology/pathology, microvascular invasion, surgical risk assessment).

---

## 2. Architecture & Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Planning Workspace                     │
│   (3D Viewer + MPR Viewer + Workspace Selection State)      │
└──────────────────────────────▲──────────────────────────────┘
                               │ Interactive Focus & Highlights
┌──────────────────────────────┴──────────────────────────────┐
│            ProcedureExplanation.jsx (Frontend Panel)         │
│  - Audience Switcher: Technical vs. General                 │
│  - 10 Structured Sections: Overview, Finding, Location,     │
│    Anatomy, Spatial Rels, Measurements, Targets, Context,   │
│    Clinical Review, Limitations                             │
│  - Interactive Source Provenance Drawer                     │
└──────────────────────────────▲──────────────────────────────┘
                               │ REST API
┌──────────────────────────────┴──────────────────────────────┐
│                  FastAPI Router (cases.py)                  │
│  - GET /api/cases/{case_id}/planning/explanation            │
│  - GET /api/cases/{case_id}/planning/explanation/provenance  │
└──────────────────────────────▲──────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────┐
│     ProcedureExplanationService (Deterministic Engine)      │
│  - Aggregates CaseOverview, ComputationalFindings,          │
│    Verified Anatomy, Spatial Distances, & Measurements      │
│  - Transforms to Technical or General Audience representations│
│  - Appends Clinical Review & System Limitation Registries   │
└──────────────────────────────▲──────────────────────────────┘
                               │
┌──────────────────────────────┴──────────────────────────────┐
│          ProcedureExplanation Models (Pydantic)             │
│  (CaseOverview, ComputationalFinding, AnatomyItem,          │
│   RelationshipItem, MeasurementItem, PlanningTargetItem,    │
│   GeneralProceduralContext, ClinicalReviewItem,             │
│   LimitationItem, ExplanationProvenance)                    │
└─────────────────────────────────────────────────────────────┘
```

### 1. Data Models (`src/planning/procedure_explanation.py`)
- **`CaseOverview`**: CT dimensions, isotropic voxel spacing (mm), acquisition orientation, modality, and Hounsfield Unit dynamic range.
- **`ComputationalFinding`**: Machine learning model inference findings (KiTS23 classes), voxel and physical centroid, estimated volume (mL), bounding box dimensions, and host organ.
- **`AnatomyItem`**: Anatomical structures segmented by TotalSegmentator with explicit `available: bool` flags verifying actual file presence on disk.
- **`RelationshipItem`**: Surface-to-surface physical minimum distances with strict disclaimer that distances do not represent surgical margins.
- **`MeasurementItem`**: User- and tool-derived physical distance annotations.
- **`PlanningTargetItem`**: Surgical landmark reference points (both model-derived and surgeon-annotated).
- **`GeneralProceduralContext`**: General, educational background on anatomical procedures (e.g., nephron-sparing partial nephrectomy principles) clearly marked as non-patient-specific.
- **`ClinicalReviewItem`**: Structured checklist of diagnostic and surgical elements requiring physician assessment.
- **`LimitationItem`**: Technical boundaries (slice resolution, segmentation artifact potential, absence of contrast phase timing).
- **`ExplanationProvenance`**: Full chain of custody for algorithms, pipelines, and registries.

### 2. Service Layer (`src/planning/procedure_explanation_service.py`)
- Synthesizes findings using existing `case_processor`, `planning_summary_service`, and anatomical registries.
- Formats text dynamically based on the requested `audience` parameter (`technical` vs `general`).
- Validates disk presence of NIfTI segmentation masks before reporting structure availability.

### 3. REST API Endpoints (`src/api/routes/cases.py`)
- `GET /api/cases/{case_id}/planning/explanation?audience=technical|general`
  - Returns complete, validated `ProcedureExplanation` payload.
- `GET /api/cases/{case_id}/planning/explanation/provenance`
  - Returns pipeline metadata and model provenance details.

### 4. Frontend UI Panel (`frontend/src/ProcedureExplanation.jsx`)
- Interactive sidebar tab within `PlanningWorkspace.jsx`.
- Real-time audience switching between Technical and General modes.
- Cross-component synchronization: clicking findings, structures, measurements, or targets focuses the 3D visualizer and centers the 2D MPR viewer on the target coordinates.
- Collapsible provenance drawer detailing source pipelines.

---

## 3. Verification & Test Suite

The engine was tested against verified real case data:
- Model unit tests validating all Pydantic schemas.
- Service tests validating audience switching, provenance generation, and clinical review item requirements.
- Integration tests verifying FastAPI endpoint status codes (200 OK for valid cases, 404 for missing cases).
- Frontend production build verification with zero syntax or bundling errors.
