# Preoperative Procedure Explanation Engine — Architecture & Specification

## 1. Overview & Clinical Safety Boundaries

The **Preoperative Procedure Explanation Engine** (Day 21) is a structured, deterministic clinical explanation subsystem for the AI-Assisted Preoperative Planning System.

It translates low-level computational findings (NIfTI segmentation masks, voxel/physical centroids, bounding boxes, Euclidean surface distance matrices, user annotations, and measurements) into a structured, transparent, and auditable procedural explanation.

### Strict Medical Safety & Product Boundaries
This system is an **educational and research prototype only**. It is governed by the following strict clinical boundaries:
- **No Medical Diagnoses**: Does not diagnose patients or declare disease status.
- **No Malignancy / Histological Staging**: Does not assess histological malignancy, invasiveness, or TNM staging.
- **No Surgical Recommendations**: Does not recommend a surgical procedure (e.g., partial vs. radical nephrectomy) or operative approach (open, laparoscopic, robotic).
- **No Feasibility or Risk Claims**: Does not claim whether surgery is safe, feasible, or clinically indicated.
- **No Autonomous Clinical Decisions**: Operates strictly under the premise that all computational outputs must be reviewed and validated by a qualified clinician/urologist.
- **Zero Generative Hallucination**: Does not use generative LLMs or non-deterministic models for clinical text generation. All explanations are synthesized deterministically from validated computational case data.

---

## 2. Core Architecture

The architecture consists of four distinct layers:

```
┌────────────────────────────────────────────────────────┐
│           PlanningWorkspace.jsx (React)                │
│    Explanation Tab (ProcedureExplanation.jsx)          │
│    - Technical View vs General View                    │
│    - Section Navigation                                │
│    - Interactive 3D / MPR View Synchronization         │
│    - Expandable Pipeline Provenance                    │
└───────────────────────────▲────────────────────────────┘
                            │ REST JSON API
┌───────────────────────────┴────────────────────────────┐
│              FastAPI Router (cases.py)                 │
│  GET /api/cases/{case_id}/planning/explanation         │
│  GET /api/cases/{case_id}/planning/explanation/provenance│
└───────────────────────────▲────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────┐
│      ProcedureExplanationService (Python Service)      │
│  - Deterministic aggregation of case data              │
│  - Multi-audience adaptation (Technical / General)     │
│  - Clinical review requirements registry               │
│  - System limitations and provenance registry          │
└───────────────────────────▲────────────────────────────┘
                            │
┌───────────────────────────┴────────────────────────────┐
│      Pydantic Data Models (procedure_explanation.py)   │
│  - CaseOverview, ComputationalFinding, AnatomyItem,    │
│    RelationshipItem, MeasurementItem, TargetItem,      │
│    GeneralProceduralContext, ClinicalReviewItem,       │
│    LimitationItem, ExplanationProvenance,              │
│    ProcedureExplanation                                │
└────────────────────────────────────────────────────────┘
```

---

## 3. Data Models (`src/planning/procedure_explanation.py`)

| Model | Purpose | Key Attributes |
| :--- | :--- | :--- |
| **`CaseOverview`** | High-level CT scan context | `case_id`, `scan_dimensions`, `voxel_spacing_mm`, `orientation`, `intensity_range_hu`, `status` |
| **`ComputationalFinding`** | ML segmentation findings | `finding_id`, `model_class`, `host_organ`, `host_organ_display`, `volume_ml`, `dimensions_mm`, `centroid_voxel`, `centroid_physical_mm`, `computational_interpretation`, `source_provenance` |
| **`AnatomyItem`** | Structure presence on disk | `structure_id`, `display_name`, `category`, `available`, `voxel_count`, `mesh_available`, `relationship_to_finding`, `unavailability_reason`, `color` |
| **`RelationshipItem`** | Minimum Euclidean distance | `source_id`, `target_id`, `target_display_name`, `distance_mm`, `overlap`, `available`, `interpretation`, `source` |
| **`MeasurementItem`** | Quantitative measurements | `measurement_id`, `measurement_type`, `label`, `value_mm`, `value_cm`, `start_voxel`, `end_voxel`, `source_service` |
| **`PlanningTargetItem`** | Target landmarks | `target_id`, `label`, `target_type`, `source`, `voxel_coordinate`, `physical_coordinate`, `linked_finding_id` |
| **`GeneralProceduralContext`** | Non-patient specific education | `items` (list of headings & descriptions), `audience`, `disclaimer` |
| **`ClinicalReviewItem`** | Things system cannot determine | `item_id`, `category` (diagnosis, pathology, staging, operative_approach, feasibility), `statement` |
| **`LimitationItem`** | Technical boundaries | `limitation_id`, `domain` (validation, segmentation, model, imaging, geometry), `description` |
| **`ExplanationProvenance`** | Audit trail & sources | `case_id`, `ct_source`, `segmentation_source`, `lesion_model_source`, `coordinate_system_source`, `generation_method` |
| **`ProcedureExplanation`** | Root container | All components above + `audience`, `generated_at`, `governance_statement` |

---

## 4. Audience Adaptation

The engine supports dynamic audience switching via the `?audience=` query parameter:

### Technical Audience (`audience=technical`)
- Uses standard anatomical, radiological, and computational terms (e.g., *voxel coordinates*, *physical isotropic spacing*, *Euclidean distance matrix*, *KiTS23 inference pipeline*).
- Explains procedural context from a technical imaging standpoint (MPR planes, HU windowing presets, mesh generation parameters).
- Details algorithm provenance and exact segmentation pipelines.

### General Audience (`audience=general`)
- Simplifies technical terminology into patient-accessible language while retaining medical precision.
- Translates finding statements (e.g., *"Computational observation: An imaging region in the Left Kidney was segmented by the algorithm as consistent with a cyst. This represents imaging analysis only and is not a clinical diagnosis."*).
- Clearly highlights the non-diagnostic and educational scope of computational imaging tools.

---

## 5. REST API Endpoints

### 1. `GET /api/cases/{case_id}/planning/explanation`
**Query Parameters:**
- `audience` (optional, default `technical`): `technical` | `general`

**Responses:**
- `200 OK`: Returns full `ProcedureExplanation` JSON object.
- `400 Bad Request`: If invalid audience value supplied.
- `404 Not Found`: If case does not exist.

### 2. `GET /api/cases/{case_id}/planning/explanation/provenance`
**Responses:**
- `200 OK`: Returns `ExplanationProvenance` object containing pipeline references, model source descriptions, and generation method.
- `404 Not Found`: If case does not exist.

---

## 6. Frontend Integration (`ProcedureExplanation.jsx`)

Integrated as the `📋 Explanation` tab in the Planning Workspace sidebar:
- **Audience Selector Buttons**: Technical vs. General modes.
- **Section Quick-Nav**:
  1. Case Overview
  2. Computational Finding
  3. Location
  4. Relevant Anatomy
  5. Spatial Relationships
  6. Measurements
  7. Planning Targets
  8. Procedural Context
  9. Clinical Review
  10. Limitations
- **Cross-Component Focus**: Clicking any finding, structure, or coordinate centers the 2D MPR viewer and highlights the structure in the 3D viewport.
- **Collapsible Provenance**: Expandable panel revealing pipeline sources, algorithm versions, and data integrity signatures.
