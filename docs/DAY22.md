# DAY 22 — Preoperative Case Planning Report & PDF Export Layer
## Milestone Report: Finish & Validate the Report/Export Layer

### Milestone Status: Complete ✅
- **Focus**: Finish and validate the Preoperative Case Planning Report + PDF Export
  layer that was already scaffolded (models, service, endpoints, frontend modal) but
  had an unfinished PDF renderer and a mismatched test expectation.
- **Scope discipline**: No changes to the lesion inference pipeline, TotalSegmentator
  pipeline, coordinate system, MPR implementation, planning measurements/targets
  services, or Day 21 procedure explanation behavior. All fixes are contained to the
  Day 22 report layer itself.

---

## 1. Starting State (carried over from prior session's inspection)

The working tree already contained (uncommitted): `src/planning/report_models.py`,
`src/planning/report_service.py`, the two `/planning/report` and `/planning/report/pdf`
FastAPI endpoints, `frontend/src/PreoperativeReportModal.jsx`, and
`tests/test_preoperative_report.py`. Running the full suite showed **243 passed, 3
failed**:

1. `test_api_get_report_pdf_200` / `test_api_get_report_pdf_general_200` — both 500.
2. `test_real_case_numerical_fidelity` — failed on an empty `planning_measurements` list.

---

## 2. Task 1 — PDF Builder Field Audit & Fix

`build_pdf_document()` in `report_service.py` was written against an earlier draft of
the report schema and never updated when `report_models.py` was finalized. The JSON
path (`generate_report()`) and the frontend modal both already used the correct,
current field names — only the PDF renderer had drifted. A complete field-by-field
audit (every attribute access in `build_pdf_document()` cross-checked against the
actual Pydantic models) found **12 distinct stale field references**, all now fixed:

| Location | Before (broken) | After (fixed) |
| :-- | :-- | :-- |
| Page header/footer (`NumberedCanvas`) | `report.metadata.audience` | `report.metadata.target_audience` |
| Page footer | `report.metadata.generated_at` | `report.metadata.generated_at_utc` |
| Title meta line | `report.metadata.audience` | `report.metadata.target_audience` |
| Case overview table | `report.case_overview.processing_status` | `report.case_overview.status` |
| Case overview table | `img.voxel_spacing_mm` | `img.spacing_mm` |
| Findings table | `f.model_class` | `f.class_name` |
| Findings table | `f.dimensions_mm` | `f.bounding_box_mm` |
| Spatial relationships table | `r.distance_mm` | `r.min_distance_mm` |
| Spatial relationships table | `r.overlap` | `r.overlap_detected` |
| Spatial relationships table | `r.target_id` | `r.target_structure` |
| Planning targets text | `t.source` | `t.provenance` (formatted `MODEL INFERENCE` / `USER ANNOTATION`) |
| Planning targets text | `t.physical_coordinate` | `t.physical_coordinate_mm` |
| Planning measurements text | `m.value_mm` / `m.value_cm` | `m.length_mm` / `m.length_cm` |
| Session notes | `report.planning_session_notes.planning_notes` | `report.planning_session_notes.content` (None-safe) |
| Limitations table | `report.limitations` | `report.system_limitations` |

**Not changed**: the field reads inside `generate_report()` (e.g. `f.model_class`,
`r.distance_mm`, `r.overlap`, `t.source`, `session.planning_notes`) that translate
*from* the Day 20/21 source models (`ComputationalFinding`, `RelationshipItem`,
`PlanningTarget`, `PlanningSession`) *into* the Report models — those are correct by
design (a schema-mapping layer, not a bug) and were independently verified against
`src/planning/procedure_explanation.py` and `src/planning/planning_targets.py` before
being left untouched. No Report model field was renamed to accommodate the PDF
builder — only the builder was corrected to match the existing, working JSON schema.

---

## 3. Task 2 — Planning-Measurement Decision

**Question**: does the golden validation case
(`b2f89382-9416-4e94-9486-b00c6b1de64b`) genuinely need a planning measurement, or is
an empty list the correct state?

**Finding**: `outputs/cases/b2f89382-9416-4e94-9486-b00c6b1de64b/planning/measurements.json`
holds `{"measurements": []}`. Investigating why led to
`tests/test_planning_measurements.py::test_real_case_measurements_integration` (an
existing, already-committed Day 18 test), which explicitly:
1. Creates a point-to-point measurement on this exact real case through the
   authoritative `MeasurementService` API, then
2. **Deletes it immediately** — with the comment *"Cleanup created measurement to
   leave real case pristine."*

This is a deliberate, pre-existing project convention: the golden case is kept in a
**pristine, zero-planning-measurement reference state**. Seeding a permanent
measurement to satisfy the Day 22 test would have:
- contradicted that established convention,
- constituted exactly the kind of fabricated/artificial test data the task
  explicitly prohibited, and
- been fragile against any future run of the Day 18 test (which only ever restores
  the case to zero measurements, never to "one").

**Decision**: the empty `planning_measurements` list is the correct, authoritative
state. `tests/test_preoperative_report.py::test_real_case_numerical_fidelity` was
updated to assert `report.planning_measurements == []` (an explicit empty-state
check, with a comment pointing back to this decision) instead of asserting `>= 1`.
No fixture data was fabricated or seeded.

---

## 4. Task 3 — Test Results

**Full regression suite** (`python -m pytest tests/ -q`):
```
246 passed, 7 warnings in 298.01s (0:04:58)
```
0 failed. This is the complete backend suite (lesions, measurements, planning, MPR,
coordinate system, procedure explanation, and the Day 22 report layer) — not just the
new tests.

**Day 22 suite** (`python -m pytest tests/test_preoperative_report.py -v`):
```
25 passed, 4 warnings in 184.32s (0:03:04)
```
All model-instantiation, service, JSON-API, PDF-API, governance, and real-case
fidelity tests pass.

---

## 5. Task 4 — Real Golden Case Validation

Validated directly against the FastAPI app (in-process `TestClient`, no server
process needed) for `b2f89382-9416-4e94-9486-b00c6b1de64b`:

| Check | Result |
| :-- | :-- |
| `GET .../planning/report?audience=technical` | `200 OK` |
| `GET .../planning/report?audience=general` | `200 OK` |
| `GET .../planning/report/pdf?audience=technical` | `200 OK`, `application/pdf` |
| `GET .../planning/report/pdf?audience=general` | `200 OK`, `application/pdf` |
| PDF starts with `%PDF-` | ✅ (`%PDF-1.4`) |
| PDF terminates correctly | ✅ (`%%EOF` present) |
| Computational finding present | ✅ `cyst_left` |
| Class terminology correct | ✅ `class_name: "cyst"` (model-predicted, not diagnosed) |
| Volume | ✅ `0.3071 mL` |
| Host structure | ✅ `kidney_left` |
| Centroid voxel / physical | ✅ `[110, 89, 218]` / `[164.868, 133.104, 327.363]` mm |
| Bounding box | ✅ `[7.5, 9.0, 9.0]` mm |
| Available anatomy | ✅ `kidney_left`, `kidney_right`, `aorta`, `inferior_vena_cava`, adrenal glands — all `available: true` |
| Unavailable anatomy not fabricated | ✅ `renal_artery`, `renal_vein`, `renal_pelvis`, `ureter` all `available: false`, `voxel_count: 0`, explicit real unavailability reasons |
| Spatial relationships | ✅ sourced from `spatial_relationships.py` via `ProcedureExplanationService`; `kidney_left` → `overlap_detected: true`, `0.0 mm` |
| Planning targets | ✅ `model_cyst_left` at voxel `[110, 89, 218]`, sourced from `annotation_service` |
| Planning measurements | ✅ authoritatively empty (`[]`) — see §3 decision |
| Procedural context | ✅ 6 items, sourced from Day 21 `ProcedureExplanationService` |
| Clinical review items | ✅ 8 non-computational review categories (`diagnosis`, `pathology`, `staging`, `operative_approach`, `feasibility`, `segmentation`, `imaging`, `model`) |
| Limitations & provenance | ✅ 7 limitations; provenance identifies `PreoperativeReportService`, `PlanningSummaryService`, `ProcedureExplanationService`, TotalSegmentator v2, KiTS23 |
| Governance/disclaimer | ✅ "Research Prototype — Educational Use Only" + 6 mandatory rules present in both JSON and PDF |
| Deterministic hash | ✅ identical (`d8799975a54e6c27`) across independent process runs — confirms `generate_report()` is stable for unchanged findings/relationships/targets |

**Note on test isolation**: an initial validation pass was run *concurrently* with the
full background regression suite and observed a different `planning_session_notes`
value between two nearly-simultaneous requests. This was a pre-existing test-isolation
characteristic (a Day 20 workspace test mutates the shared, git-ignored
`planning_session.json` for this same real case) — not a Day 22 defect, and not
something in scope to change. A second, isolated validation pass (run with no other
test process touching the case) produced the results tabulated above and is the
authoritative one. The report's `deterministic_hash` deliberately excludes session
notes and planning measurements from its hash input for exactly this reason (see
`docs/PREOPERATIVE_REPORT.md` §6).

---

## 6. Task 5 — PDF Content / Governance Audit

Extracted text from both generated PDFs (`pypdf`, installed transiently for this
audit only — not added to `requirements.txt`) and scanned for prohibited terms:
diagnosis, malignancy/benign determinations, cancer exclusion, staging, surgical
recommendations, "best approach", "safe distance"/"safe margin", clinical risk
thresholds, unsupported anatomy, unsupported measurements.

Every hit for `diagnosis`, `staging`, and `safe margin` was inspected in context and
is a **negation/disclaimer**, e.g.:
- *"This system does not establish a diagnosis."*
- *"Oncologic staging cannot be determined from computational imaging segmentation."*
- *"They do NOT represent surgical clearance, safe margins, or operative planes."*

No affirmative diagnostic, malignancy, staging, or surgical-recommendation claim was
found in either audience's PDF. Unavailable anatomy (renal artery/vein/pelvis/ureter)
is reported as unavailable with a real technical reason, never fabricated. Result:
**clean** — the report remains a computational/research/educational document.

---

## 7. Task 6 — Frontend Build

```
cd frontend && npm run build
```
```
✓ 580 modules transformed.
✓ built in ~500ms
```
0 errors. The pre-existing chunk-size warning (single JS bundle > 500 kB) is
unchanged and unrelated to Day 22.

---

## 8. Known Limitations (carried into `docs/PREOPERATIVE_REPORT.md` §9)

- PDF generation is uncached; each request regenerates the document from live data.
- The report layer does not independently re-validate upstream scan metadata
  (dimensions, orientation, HU range) — it trusts `PlanningSummaryService`.
- `planning_session_notes` and `planning_measurements` reflect live, mutable session
  state and are intentionally excluded from the provenance `deterministic_hash`.
- No new capability limitation was introduced by this milestone; all Day 22 fixes are
  confined to `report_service.py`'s PDF renderer and one test assertion.

---

## 9. Files Touched

- `src/planning/report_service.py` — `build_pdf_document()` field-reference fixes only.
- `tests/test_preoperative_report.py` — one assertion + docstring updated (planning-
  measurement empty-state expectation).
- `docs/DAY22.md` (new, this file), `docs/PREOPERATIVE_REPORT.md` (new),
  `docs/PROGRESS.md` (updated).

No changes to `report_models.py`, the FastAPI routes, the frontend modal, or any
non-Day-22 subsystem.
