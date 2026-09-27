# DAY 24 — Planning Annotation & Finding Integration
## Milestone Report

### Milestone Status: Complete ✅
- **Focus**: Expose already-implemented, already-tested backend annotation
  capability (`updatePlanningAnnotation`, `createAnnotationFromLesion`,
  `getPlanningAnnotations`) in `PlanningWorkspace`, which previously never
  called any of them.
- **Scope discipline**: no backend calculation logic changed, no coordinate
  math added to React, no new schema fields, no diagnosis/malignancy/margin
  language introduced, golden case left in its exact pre-test state.

---

## 1. Part 1 — Annotation Capability Audit (before any coding)

### Models (`src/planning/planning_targets.py`)
- `PlanningTarget` — unified target/annotation representation; `source` is
  `TargetSource.MODEL` or `TargetSource.USER`; `target_type` is `lesion`,
  `anatomy`, or `custom_point`. Carries `voxel_coordinate`, `physical_coordinate`,
  `lesion_id`, `structure_id`, `notes`, plus model-only metadata
  (`volume_ml`, `dimensions_mm`, `computational_interpretation`, `host_organ`).
- `AnnotationCreateRequest` — `label`, `target_type`, `voxel_coordinate`
  (required), optional `physical_coordinate`, `notes`, `structure_id`, `lesion_id`.
- `AnnotationUpdateRequest` — **all fields optional**: `label`, `notes`,
  `voxel_coordinate`, `physical_coordinate`. Backend already supports
  coordinate edits too, but Day 24 only exposes `label`/`notes` in the UI
  (see §6 "Not implemented").
- `FromLesionRequest` — optional `label`, `notes` override for the
  from-lesion flow.
- `PlanningTargetsResponse` — envelope for the combined model+user list.

### Service (`src/planning/annotations.py` — `AnnotationService`)
- `create_user_annotation` — validates voxel bounds against the real volume
  shape, resolves physical coordinate via `voxel_to_physical` if not supplied,
  persists to `annotations.json`. Always stamps `source=TargetSource.USER`.
- `update_user_annotation` — **partial update**: only overwrites fields present
  in the request; returns `None` (→ 404 at the route) if the ID doesn't exist.
- `delete_user_annotation`, `list_user_annotations`, `get_user_annotation`.
- `create_annotation_from_lesion(case_id, lesion_id, label=None, notes=None)` —
  resolves the lesion's centroid from `lesions.json` (or recomputes from the
  mask if the JSON entry is missing), converts to voxel via
  `physical_to_voxel`, and calls `create_user_annotation` with
  `target_type=LESION`, `lesion_id=lesion_id`. **Stores `source=USER`** — i.e.
  it is a user-authored reference *to* a model finding, not a model object
  itself. Raises `FileNotFoundError` for an unknown lesion.
- `get_model_lesion_targets` / `get_all_planning_targets` — synthesizes
  `model_<lesion_id>` targets on the fly from `lesions.json` (never persisted
  to `annotations.json`), then concatenates with user annotations.
- **No deduplication**: nothing in `create_annotation_from_lesion` checks
  whether an annotation already exists for that `lesion_id` — confirmed by
  code inspection and by a new characterization test (§4).

### REST endpoints (`src/api/routes/cases.py`, unchanged, already existed)
`GET /planning/targets` (combined), `GET /planning/annotations` (user-only),
`POST /planning/annotations`, `PUT /planning/annotations/{id}`,
`DELETE /planning/annotations/{id}`, `POST /planning/annotations/from-lesion/{lesion_id}`.

### Frontend, before Day 24
`frontend/src/api.js` already had `updatePlanningAnnotation`,
`createAnnotationFromLesion`, `getPlanningAnnotations`, `getPlanningTargets` as
thin wrappers — but grep confirmed **zero** call sites for the first three
anywhere in `frontend/src/*.jsx`. `PlanningWorkspace.jsx` already used
`createPlanningAnnotation` (custom-point creation via MPR click) and
`deletePlanningAnnotation` (Day 17), and already distinguished model vs. user
targets visually (cyan vs. amber dot, `MODEL`/`USER` badge) — that distinction
needed no new work, only reuse.

### What was missing from the UI (confirmed gap)
1. No way to edit an existing user annotation's label/notes.
2. No way to create an annotation from a model finding (`createAnnotationFromLesion`
   unused).
3. No separate "user annotations only" view (`getPlanningAnnotations` unused) —
   judged **not required**: the existing combined "Planning Targets" list
   already shows both, correctly badged; adding a redundant second list would
   be scope creep. `getPlanningAnnotations` remains unused after Day 24 (see
   §6, Limitations).

---

## 2. Part 2 — Planning Annotations UI

Implemented entirely inside `frontend/src/PlanningWorkspace.jsx`'s existing
"Selected Object Inspector" card:

- When `selectedTarget.source === 'user'`, an **✏️ Edit** button appears next
  to the existing `USER`/`MODEL` provenance badge (badge itself untouched).
- Clicking it swaps the read-only title for an inline form: a `label` text
  input and a `notes` textarea, pre-filled from the selected annotation.
  Loading (`Saving…`), error (inline `adv-meas-error`, reused from Day 23),
  and disabled-while-saving states are all handled.
- **Save** calls `updatePlanningAnnotation(caseId, target_id, { label, notes })`
  — only these two fields are ever sent; coordinates are never touched.
- After a successful save, `getPlanningTargets(caseId)` re-fetches the
  authoritative combined list, `setPlanningTargets(list)` replaces state, and
  `handleSelectTargetItem(match)` re-selects the (now updated) item — the same
  function that already drives MPR cursor + 3D camera focus, so selection
  behavior is unchanged and automatically stays synchronized.
- **Guard against stale edits** (Part 4: "do not silently overwrite another
  annotation"): a `useEffect` watches `selectedTarget` and cancels any
  in-progress edit the moment the user selects something else, so a save can
  never target the wrong ID.
- Editing is only ever offered for `source === 'user'` items — model targets
  (`model_<lesion_id>`) have no button, since they are not persisted in
  `annotations.json` and `updatePlanningAnnotation` would 404 against one.

---

## 3. Part 3 — Lesion → Planning Annotation

Each card in the "Model-Predicted Findings" tab now shows one of two buttons:

- **📌 Create Annotation** (default) — calls
  `createAnnotationFromLesion(caseId, lesion_id)` with no extra payload (the
  backend fills in a sensible default label/notes from the lesion's own
  `computational_interpretation`/`volume_ml`). On success: refresh via
  `getPlanningTargets()`, then `handleSelectTargetItem()` selects/focuses the
  new annotation.
- **📌 View Annotation** — shown instead, whenever
  `planningTargets.some(t => t.source === 'user' && t.lesion_id === f.lesion_id)`
  is already true. Clicking it just selects the existing annotation. This is
  the "prevent duplicate creation" requirement — implemented entirely in the
  frontend, since the backend has enough information (the combined target
  list) for the UI to check, and the task explicitly says not to expand
  backend scope for this.
- The underlying lesion result (`lesions.json`) is never written to — verified
  by a new test that snapshots the file before/after (§4).
- No coordinates or measurements are recomputed in React — the created
  annotation's voxel/physical coordinates come directly from the API response.

---

## 4. Part 6 — Tests

### New tests (`tests/test_planning.py`, appended — nothing existing modified)
1. `test_update_annotation_partial_preserves_other_fields` — a `{label, notes}`-only
   update leaves `target_id`, `source`, `target_type`, `voxel_coordinate`,
   `physical_coordinate` byte-for-byte unchanged.
2. `test_update_nonexistent_annotation_returns_404` — invalid annotation ID → 404.
3. `test_annotation_from_lesion_preserves_provenance_and_does_not_modify_lesion_data` —
   asserts `source == "user"`, `lesion_id` preserved, and `lesions.json` is
   byte-identical before/after.
4. `test_duplicate_annotation_from_same_lesion_is_a_ui_guard_not_a_backend_rule` —
   characterizes existing (unmodified) backend behavior: two
   `create_annotation_from_lesion` calls for the same lesion succeed with two
   distinct IDs. Documents exactly why the UI-side check in §3 exists.
5. `test_real_case_annotation_lifecycle_golden_case_protection` — full
   create-from-lesion → update → delete cycle against
   `b2f89382-9416-4e94-9486-b00c6b1de64b`, asserting the golden cyst's known
   coordinates, then restoring the case's annotation count to its pre-test
   baseline and re-verifying the model target and unavailable-anatomy set are
   untouched.

No existing test was modified, weakened, or deleted.

### Results
- `python -m pytest tests/ -q`: **262 passed, 0 failed** (257 pre-Day-24
  baseline + 5 new tests, all in `tests/test_planning.py`).
- `npm run build`: clean, 0 errors.

---

## 5. Part 7 — Real Case Validation (`b2f89382-9416-4e94-9486-b00c6b1de64b`)

Covered by `test_real_case_annotation_lifecycle_golden_case_protection` plus a
manual isolated check of the endpoints Part 7 explicitly lists:

| Check | Result |
| :-- | :-- |
| `model_cyst_left` target intact | ✅ voxel `[110, 89, 218]` unchanged |
| Existing planning target(s) intact | ✅ unaffected by transient annotation create/update/delete |
| Existing measurements unchanged | ✅ isolated storage (`measurements.json` untouched by annotation ops) |
| Unavailable anatomy remains unavailable | ✅ `renal_artery/vein/pelvis/ureter` still `available: false` |
| Annotation create/update only via authoritative APIs | ✅ `POST .../from-lesion/{id}`, `PUT .../{id}` |
| Temporary annotation data removed afterward | ✅ deleted in `finally`; annotation count restored to pre-test baseline |
| `/planning/explanation` still works | ✅ `200 OK` |
| `/planning/report` + `/planning/report/pdf` still work | ✅ both `200 OK`, PDF starts with `%PDF-` |

No golden-case data was permanently altered.

---

## 6. Part 8 — Governance Audit

Searched all changed files for: diagnosis, malignancy, malignant, benign, safe
margin, unsafe margin, surgical clearance, recommended approach, best approach,
surgical risk conclusion, treatment recommendation.

- Every hit is either pre-existing text untouched by this milestone, a
  disclaimer reused verbatim (`"Does not constitute surgical margins or
  clinical assessment"` — already present since Day 23, only rendered in the
  new UI it happens to sit near), a negative-case governance test, or this
  documentation describing the audit itself.
- No new clinical inference, diagnosis, or recommendation text was introduced.
- Model-predicted findings remain labeled `source: "model"`; an annotation
  derived from one is explicitly `source: "user"` — the annotation is a
  *reference to* a model finding, never re-labeled as a model output itself.
- User-entered fields (`label`, `notes`) remain plain user-editable strings;
  nothing auto-populates them with generated clinical text beyond the existing,
  pre-Day-24 default label/notes convention already used by
  `create_annotation_from_lesion`.

---

## 7. Known Limitations

- **Duplicate-annotation prevention is a frontend-only guard** (see §3, §4) —
  the backend `create_annotation_from_lesion` does not itself reject a second
  annotation for the same lesion. Per the task's explicit instruction, backend
  scope was not expanded to add this; it is listed as a Future Direction in
  `docs/PROGRESS.md`.
- **Coordinate editing is not exposed in the UI.** `AnnotationUpdateRequest`
  supports `voxel_coordinate`/`physical_coordinate`, but Part 4 asked for "at
  minimum" label/notes and explicitly warned against adding new schema fields
  or unnecessary scope — a coordinate-editing UI would need a coordinate-pick
  interaction not requested here, so it was left out.
- **`getPlanningAnnotations` (user-only list) remains unused.** Its data is a
  strict subset of what `getPlanningTargets` (already used everywhere) already
  returns with clearer model/user badging in one place; adding a second,
  redundant list view was judged out of scope.
- No frontend automated test harness exists in this project (predates Day 24);
  the new UI was validated via a clean production build and the backend
  contract tests it depends on.
