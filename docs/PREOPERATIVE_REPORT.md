# Preoperative Case Planning Report & Export Layer — Architecture & Specification

## 1. Overview & Clinical Governance

The **Preoperative Case Planning Report** (Day 22) is a presentation and export layer that
consolidates every existing, already-validated computational planning subsystem — case
metadata, KiTS23 model findings, the anatomical structure registry, spatial-relationship
distances, planning targets, preoperative measurements, planning session notes, and the
Day 21 Procedure Explanation engine — into a single structured document, available as
JSON or as a downloadable A4 PDF.

It performs **zero new calculation**. Every value in the report is read from an existing
authoritative service (`PlanningSummaryService`, `ProcedureExplanationService`) and
re-presented; the report layer never re-derives, estimates, or infers a number that
those services did not already compute.

> [!IMPORTANT]
> **Clinical Governance Notice**: This report is a research and educational prototype
> output. It does **NOT**:
> - provide a clinical diagnosis
> - assess malignancy or benign status
> - determine histological staging or TNM classification
> - recommend a surgical procedure or operative approach
> - determine surgical risk or feasibility
> - substitute for medical specialist consultation or clinical records
>
> All computational findings require verification by a qualified medical professional
> before any clinical decision-making.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Planning Workspace                      │
│         (3D Viewer + MPR Viewer + Explanation Tab)            │
└──────────────────────────────▲───────────────────────────────┘
                               │ Opens modal
┌──────────────────────────────┴───────────────────────────────┐
│         PreoperativeReportModal.jsx (Frontend Panel)         │
│  - Audience toggle: Technical vs. General                    │
│  - Full on-screen rendering of all 15 report sections        │
│  - Browser print (@media print) + native PDF download        │
└──────────────────────────────▲───────────────────────────────┘
                               │ REST API
┌──────────────────────────────┴───────────────────────────────┐
│                  FastAPI Router (cases.py)                    │
│  GET /api/cases/{case_id}/planning/report                    │
│  GET /api/cases/{case_id}/planning/report/pdf                 │
└──────────────────────────────▲───────────────────────────────┘
                               │
┌──────────────────────────────┴───────────────────────────────┐
│         PreoperativeReportService (report_service.py)        │
│  - generate_report(): aggregates PlanningSummaryService +    │
│    ProcedureExplanationService into a PreoperativeReport      │
│  - generate_report_pdf(): renders that report via             │
│    build_pdf_document() (ReportLab Platypus, A4)               │
└──────────────────────────────▲───────────────────────────────┘
                               │
┌──────────────────────────────┴───────────────────────────────┐
│        PreoperativeReport Pydantic Models (report_models.py) │
│  15 sections — see §3                                        │
└────────────────────────────────────────────────────────────────┘
```

**Zero-duplication principle**: `PreoperativeReportService.generate_report()` never
touches segmentation masks, NIfTI volumes, or measurement math directly — it only calls
`planning_summary_service.get_planning_summary()` and
`procedure_explanation_service.generate_explanation()` and reshapes their output into
the report schema.

---

## 3. Report Sections (`src/planning/report_models.py`)

| # | Section | Model | Source Service |
| :-- | :-- | :-- | :-- |
| 1 | Report metadata | `ReportMetadata` | generated at request time |
| 2 | Case overview | `ReportCaseOverview` | `PlanningSummaryService` |
| 3 | Imaging information | `ReportImagingInfo` | `PlanningSummaryService` (`mpr_manager`) |
| 4 | Computational findings | `ReportFindingItem` | `ProcedureExplanationService` (KiTS23) |
| 5 | Anatomical structures | `ReportAnatomyItem` | `ProcedureExplanationService` (`structure_registry`) |
| 6 | Spatial relationships | `ReportSpatialRelationshipItem` | `ProcedureExplanationService` (`spatial_relationships`) |
| 7 | Lesion measurements | `ReportLesionMeasurementItem` | `PlanningSummaryService` (`lesion_measurements`) |
| 8 | Planning targets | `ReportPlanningTargetItem` | `PlanningSummaryService` (`annotation_service`) |
| 9 | Planning measurements | `ReportPlanningMeasurementItem` | `PlanningSummaryService` (`measurement_service`) |
| 10 | Planning session notes | `ReportPlanningSessionNotes` | `PlanningSummaryService` (`planning_session_service`) |
| 11 | Procedural context | `ReportProceduralContextItem` | `ProcedureExplanationService` (Day 21) |
| 12 | Clinical review items | `ReportClinicalReviewItem` | `ProcedureExplanationService` (Day 21) |
| 13 | System limitations | `ReportLimitationItem` | `ProcedureExplanationService` (Day 21) |
| 14 | Provenance / audit trail | `ReportProvenance` | both services + deterministic hash |
| 15 | Governance notice | `ReportGovernance` | static policy statement |

The root `PreoperativeReport` model composes all 15 sections. Field names are stable
and match exactly what the JSON API returns — see the model source for the authoritative
field list (do not guess field names from the PDF renderer; always check
`report_models.py` directly, since JSON and PDF consume the same object).

---

## 4. REST API

### `GET /api/cases/{case_id}/planning/report?audience=technical|general`
Returns the full `PreoperativeReport` JSON payload.
- `200 OK` — valid report
- `404 Not Found` — case does not exist
- `422 Unprocessable Entity` — `audience` is not `technical` or `general`

### `GET /api/cases/{case_id}/planning/report/pdf?audience=technical|general`
Returns the same report compiled into an A4 PDF (`application/pdf`,
`Content-Disposition: attachment; filename="preoperative_report_<case8>.pdf"`),
via `PreoperativeReportService.generate_report_pdf()` → `build_pdf_document()`
(ReportLab Platypus, two-pass `NumberedCanvas` for running headers/footers and
"Page X of Y").
- Same status codes as the JSON endpoint.

Both endpoints are implemented in `src/api/routes/cases.py` under the
"DAY 22 — Preoperative Case Planning Report Endpoints" section.

---

## 5. Audience Modes

Both `generate_report()` and the PDF export accept `audience`:
- **`technical`** (default): full voxel/physical metrics, standard anatomical and
  radiological terminology, algorithm/provenance detail.
- **`general`**: plain-language summaries reusing the Day 21
  `ProcedureExplanationService` general-audience text, while all quantitative tables
  (findings, spatial relationships, anatomy registry) remain numerically identical —
  only prose framing changes, never the underlying values.

---

## 6. Provenance & Determinism

`ReportProvenance.deterministic_hash` is a SHA-256 (truncated to 16 hex chars) over the
report's *substantive* payload — `case_id`, `computational_findings`,
`spatial_relationships`, and `planning_targets` — with `source_type` fields excluded.
Two calls to `generate_report()` for the same case/audience always yield the same hash,
which is asserted in `tests/test_preoperative_report.py::
test_report_service_deterministic_substantive_payload`.

The hash intentionally excludes `planning_session_notes` and `planning_measurements`,
since those reflect live, mutable session state (a clinician can edit notes or add/delete
a measurement between two report requests); only the model-inference/spatial/target
facts that should not change between requests for the same case are hashed.

---

## 7. Frontend (`frontend/src/PreoperativeReportModal.jsx`)

- Opened via the **📄 Preoperative Report** button in `PlanningWorkspace.jsx`.
- Audience toggle (Technical / General) re-fetches the JSON report.
- **Print Report** uses the browser's native print dialog against a `@media print`
  stylesheet scoped to `#printable-report-area`.
- **Download PDF** calls the `/planning/report/pdf` endpoint and saves the returned
  blob as `preoperative_report_<case8>.pdf`.
- Renders all 15 sections with explicit provenance tags
  (`model_inference` / `derived_computation` / `user_annotation` /
  `explanatory_context` / `mandatory_clinical_review` / `system_limitation` /
  `audit_trail` / `governance_policy`) so the reader always knows whether a value came
  from a model, a geometric computation, or a human annotation.

---

## 8. Planning-Measurement Empty-State Behavior

The golden validation case (`b2f89382-9416-4e94-9486-b00c6b1de64b`) intentionally has
**zero** persisted planning measurements — this is the correct, expected state, not
missing data. See `docs/DAY22.md` §"Planning-Measurement Decision" for the full
rationale. Both the JSON payload (`planning_measurements: []`) and the PDF
("No user measurements recorded.") represent this empty state explicitly rather than
omitting the section or fabricating a placeholder value.

---

## 9. Known Limitations

- The PDF is single-pass content generation per request (no caching); repeated
  downloads regenerate the document from live case data each time.
- `ReportImagingInfo.orientation` and other free-form scan metadata are passed through
  as reported by `PlanningSummaryService` / `mpr_manager` and are not independently
  re-validated by the report layer.
- Report generation depends on the case having completed the full pipeline (findings,
  anatomy registry, spatial relationships); a case with a failed or partial pipeline
  will surface whatever partial data those upstream services already tolerate (empty
  lists, `available: false` items), not a report-layer-specific error path.
