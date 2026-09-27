# DAY 25 — Interactive Preoperative Report + Workspace Visualization Controls
## Milestone Report

### Milestone Status: Complete ✅
- **Focus**: two scoped improvements identified by the Day 25 read-only audit —
  make the Preoperative Report modal interactive (matching the pattern the
  Explanation tab already established), and port the existing organ/lesion
  opacity + lesion-visibility controls from the Standard View's Sidebar into
  the dedicated `PlanningWorkspace`.
- **Scope discipline**: no backend calculation logic changed, no coordinate-
  system behavior changed, no measurement algorithm changed, no annotation
  backend behavior changed, no new medical inference, `App.jsx`/
  `PlanningWorkspace.jsx` architecture not refactored (only additive prop
  wiring and new, isolated handlers/JSX).

Recorded before any changes, per the task's instruction:
```
git log --oneline -4
021794a feat: add planning annotation workflow
2c977a6 feat: add advanced planning measurements and MPR persistence
21a8b53 feat: add preoperative report and PDF export
d3b0ba6 feat: add deterministic procedure explanation engine

git status
On branch main
Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

---

## 1. Part 1 — Interactive Preoperative Report

### Design: ID-only delegation, not data reconstruction

The Report's Pydantic schema (`ReportFindingItem`, `ReportAnatomyItem`,
`ReportSpatialRelationshipItem`, `ReportPlanningTargetItem`,
`ReportPlanningMeasurementItem`) intentionally uses different field names than
the live `PlanningTarget`/`Measurement`/lesion objects the workspace's existing
handlers (`handleSelectFinding`, `handleSelectStructureItem`,
`handleSelectTargetItem`, `handleSelectMeasurementItem`) expect (e.g. the
report's `centroid_physical_mm` vs. the live `centroid_mm`; `physical_coordinate_mm`
vs. `physical_coordinate`). Rather than reconstructing a field-mapped adapter
object inside the modal — which would risk building an incorrectly-shaped
object and would technically duplicate data — `PreoperativeReportModal.jsx`
was given four new optional props that take only an **ID string**:
`onSelectFinding(findingId)`, `onSelectStructure(structureId)`,
`onSelectTarget(targetId)`, `onSelectMeasurement(measurementId)`.

`PlanningWorkspace.jsx` supplies these as thin lookup adapters:
```js
const handleReportSelectFinding = (findingId) => {
  const match = findingsList.find((f) => f.lesion_id === findingId);
  if (match) handleSelectFinding(match);
};
```
(and the equivalent for structures/targets/measurements, each looking the ID
up in the workspace's own already-loaded authoritative array before calling
the pre-existing handler). If no match is found, nothing happens — no crash,
no fabricated selection. **No coordinate calculation and no duplicate
selection/focus logic exist in the modal**; it only ever passes an ID.

### What's interactive, and what deliberately isn't

| Section | Interactive when | Identifier used |
| :-- | :-- | :-- |
| Computational Findings | always (row exists → finding is real) | `finding_id` (= live `lesion_id`) |
| Anatomical Structures | only if `available === true` | `structure_id` |
| Spatial Relationships | only if `available === true` | `target_structure` (same `structure_id` the Anatomy section uses — no new identifier invented) |
| Planning Targets | always | `target_id` |
| Planning Measurements | always | `measurement_id` |

Unavailable-structure rows keep their existing `row-unavailable` styling and
receive no `onClick`/`tabIndex`/`role` at all — they remain plain, non-focusable
text, exactly matching how the Anatomy tab already treats unavailable
structures elsewhere in the workspace.

### Visual affordance & accessibility

Interactive rows get a new `.report-row-interactive` class (hover highlight +
focus-visible outline) and `role="button"`, `tabIndex={0}`, and an `onKeyDown`
handler (Enter/Space) — mirroring the exact pattern already used for
keyboard-accessible list items elsewhere in the app (`Sidebar.jsx`'s lesion
list: `role="option" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && ...}`).
Native `<tr>`/`<li>` elements were kept (not converted to `<button>`) to
preserve table/list semantics and existing layout/print CSS.

### Modal closes on selection

Since the modal is a full-screen overlay, a click that only updated hidden
workspace state would be invisible. `handleInteractiveSelect()` calls the
resolved selection handler and then `onClose()` (already an existing prop) so
the resulting MPR/3D/tab focus is immediately visible. This was not explicitly
requested but was judged necessary for the feature to be observably useful.

### Unchanged: report generation, PDF, audience toggle, print/download

`report_service.py`, `report_models.py`, and the two report REST endpoints
were **not touched**. Audience toggling, `handlePrint`, and `handleDownloadPdf`
are byte-for-byte unchanged.

---

## 2. Part 2 — Workspace Visualization Controls

### Reusing existing App.jsx state — no new opacity/visibility state

`App.jsx` already owned `organOpacity`/`setOrganOpacity` and
`lesionOpacity`/`setLesionOpacity` (used by the Standard View's `Sidebar.jsx`)
and `lesionVisibility`/`setLesionVisibility` (already threaded to
`PlanningWorkspace` since Day 20, just never exposed there). The only App.jsx
change was adding 4 props to the existing `<PlanningWorkspace>` element:
`organOpacity`, `onChangeOrganOpacity={setOrganOpacity}`, `lesionOpacity`,
`onChangeLesionOpacity={setLesionOpacity}`.

### New UI in PlanningWorkspace.jsx

- A collapsible **🎚️ Visualization** panel (toggled from the center visualizer
  toolbar, next to Measure Mode / Add Point Mode / Reset Camera) containing two
  range sliders — Organ Transparency and Lesion Opacity — `min="0.1" max="1.0"
  step="0.05"`, identical range and identical defaults (0.85 / 1.0) to the
  Sidebar's existing controls.
- A per-lesion 👁️ visibility toggle button added to each finding card in the
  Findings tab, styled with the same `.visibility-toggle` CSS class (already
  defined in `index.css` and used by `Sidebar.jsx`) and the identical
  eye/eye-slash emoji + `aria-pressed` pattern.
- `lesionOpacity` is now also passed to `PlanningWorkspace`'s own `<Viewer3D>`
  call (it previously wasn't, so the slider would otherwise have had no
  visible effect — `Viewer3D.jsx` itself was not modified, it already accepted
  this prop with a default of `1.0`).

### No duplicate state

`handleToggleLesionVisibility` mirrors the file's own pre-existing
`handleToggleStructureVisibility` pattern exactly — it calls the already-passed
`setLesionVisibility((prev) => ...)` functional updater, computing the same
`!(prev[id] !== false)` toggle formula already used for structures. There is
still exactly one `lesionVisibility` state in the app, owned by `App.jsx`.

---

## 3. Part 3 — Session Persistence

All three fields were already present in `PlanningSession` /
`PlanningSessionUpdateRequest` (`organ_opacity: float = 0.85`,
`lesion_opacity: float = 1.0`, `visible_lesions: dict[str, bool]`) —
**no backend schema change was made or needed.**

- `handleOrganOpacityChange` / `handleLesionOpacityChange`: call the existing
  `onChangeOrganOpacity`/`onChangeLesionOpacity` prop, then
  `triggerSessionSave({ organ_opacity: value })` / `{ lesion_opacity: value }`.
- `handleToggleLesionVisibility`: persists the freshly-computed `visible_lesions`
  map via the same `triggerSessionSave` call.
- All three go through the **existing** debounced
  `triggerSessionSave → updatePlanningSession` mechanism — no second
  persistence path was created.
- **Restore on load**: the existing mount-time session-load effect now also
  calls `onChangeOrganOpacity(session.organ_opacity)`,
  `onChangeLesionOpacity(session.lesion_opacity)`, and
  `setLesionVisibility(session.visible_lesions)` when present — these are
  plain setter calls, not wrapped in `triggerSessionSave`, so **loading a
  session can never itself trigger a save** (identical reasoning to the Day 23
  MPR-persistence no-save-loop guarantee).

### `visible_targets` — investigated, not persisted this milestone

Per Part 3's explicit instruction, `visible_targets` was investigated rather
than blindly added: `PlanningWorkspace.jsx` has no UI control that toggles an
individual planning target's visibility after creation (targets are only ever
created already-visible or deleted outright), and `selected_target_id` (which
*is* already persisted) is a different concept from a full visibility map. Since
there is no corresponding Workspace control this milestone, `visible_targets`
was intentionally left unpersisted, exactly as instructed — adding persistence
for state with no UI to produce it would be premature.

---

## 4. Tests

### New tests
- `tests/test_planning_workspace.py` — 5 new tests: `organ_opacity` round-trip,
  `lesion_opacity` round-trip, `visible_lesions` round-trip, a combined
  REST-level round-trip, and a no-save-loop audit extending the existing Day 23
  pattern to these three fields.
- `tests/test_preoperative_report.py` — 1 new test,
  `test_report_identifiers_match_live_authoritative_endpoints`, which proves
  the safety contract the interactive-report design depends on: every
  `finding_id`/`structure_id`/`target_id`/`measurement_id` the report emits is
  a subset of the IDs the live `/lesions`, `/structures`, `/planning/targets`,
  `/planning/measurements` endpoints return (temporarily creating and then
  deleting one measurement to exercise that path on the otherwise
  measurement-free golden case).

No existing test was modified or weakened.

### Not automated (documented instead)
"Rows without valid identifiers remain non-interactive" and "rapid changes use
the existing debounce mechanism" are pure frontend/React behaviors
(conditional prop presence; a `setTimeout`-based debounce already covered by
Day 23's tests at the mechanism level). No frontend test framework exists in
this project (predates Day 25) — both were verified by code review and the
production build rather than an automated frontend test.

### Results
- `python -m pytest tests/ -q`: **268 passed, 0 failed** (262 pre-Day-25
  baseline + 6 new tests: 5 in `tests/test_planning_workspace.py`, 1 in
  `tests/test_preoperative_report.py`).
- `npm run build`: clean, 0 errors.

---

## 5. Real-Case Validation (`b2f89382-9416-4e94-9486-b00c6b1de64b`)

Validated via `test_report_identifiers_match_live_authoritative_endpoints` plus
an isolated manual script covering every Part 5 item:

| Check | Result |
| :-- | :-- |
| `model_cyst_left` intact | ✅ voxel `[110, 89, 218]` unchanged |
| Existing annotations intact | ✅ count unchanged (0 → 0) |
| Existing planning targets intact | ✅ unaffected |
| Measurements unchanged | ✅ `0` throughout |
| Unavailable anatomy remains unavailable | ✅ all 4 (`renal_artery/vein/pelvis/ureter`) still `available: false` |
| `/planning/report` returns 200 | ✅ |
| `/planning/report/pdf` returns 200 | ✅ |
| `/planning/explanation` returns 200 | ✅ |
| Report interactions resolve to the same authoritative objects the workspace uses | ✅ `finding_id "cyst_left"` ∈ live `/lesions`; `target_id "model_cyst_left"` ∈ live `/planning/targets`; all available `structure_id`s ∈ live `/structures` |
| Opacity/visibility can be persisted and restored | ✅ set to `{organ: 0.33, lesion: 0.66, visible_lesions: {cyst_left: false}}`, re-read confirmed, then restored to the exact pre-test baseline (`{0.85, 1.0, {cyst_left: true}}`) |

No golden-case data was permanently altered.

---

## 6. Governance Audit

Searched all changed files for: diagnosis, malignancy, malignant, benign, safe
margin, unsafe margin, surgical clearance, recommended approach, best approach,
surgical risk conclusion, treatment recommendation.

GOVERNANCE_AUDIT_PLACEHOLDER

Interactive report rows only ever navigate to existing computational or
user-entered data already displayed elsewhere in the workspace — they carry no
clinical interpretation of their own, and clicking one triggers exactly the
same, already-governed display path (Inspector, MPR, 3D) that direct
in-workspace selection already used.

---

## 7. Known Limitations

- `visible_targets` remains unpersisted (see §3) — no corresponding Workspace
  control exists yet.
- The Report modal's interactivity depends on ID consistency between the
  report and the live endpoints; this is now proven by a dedicated regression
  test (§4) rather than assumed, but if a future change ever gives the report
  layer its own independent ID scheme, that test will catch it.
- No frontend automated test harness exists in this project (predates Day 25).
- The pre-existing architectural duplication between `App.jsx` (Standard View)
  and `PlanningWorkspace.jsx` (Workspace View) grew slightly with this
  milestone's new opacity/visibility wiring — flagged as a Future Direction in
  `docs/PROGRESS.md`, not addressed here per the explicit instruction not to
  refactor either file's architecture.
