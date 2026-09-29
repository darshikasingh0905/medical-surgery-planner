# DAY 28 — Case Deletion
## Milestone Report

### Milestone Status: Validated — Ready for Commit ✅
- **Objective**: close the loop opened by Day 27's case-history feature —
  a user can now *see* every case on disk (including failed uploads and
  orphaned/incomplete entries) but had no way to remove any of them. Case
  deletion was explicitly flagged as the natural next step in
  `docs/PROGRESS.md`'s own Future Directions list after Day 27.
- **Scope discipline**: backend-only new capability (one function, one
  route) plus a thin, non-duplicating frontend wiring layer. No database, no
  authentication, no new persistence layer, no `case.json` schema change, no
  changes to segmentation/measurement/coordinate/planning/report/explanation
  logic, no second polling or case-loading implementation.

Baseline recorded before any changes:
```
git log --oneline -3
83c985a feat: add case history and resume workflow
05b9c7d feat: embed CT views in preoperative report PDF
b0303fd feat: improve planning workspace visualization and report navigation

git status
On branch main. Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean

HEAD == origin/main == 83c985a
```

---

## 1. Problem / Gap Addressed

Direct inspection of the real `outputs/cases/` directory (already observed
during the Day 25/27 audits) shows exactly the kind of clutter a case-history
list without deletion accumulates: a completed golden case, a `failed`
historic case, and a case with no `case.json` at all. Once a user can *see*
this list (Day 27), the absence of any way to remove unwanted entries is a
direct, visible usability gap in the same feature — not a separate, unrelated
concern. No other capability considered (audience persistence for the
Explanation/Report modals, the vestigial unused `user_line` measurement enum
value, `visible_targets` persistence) was as clearly justified, as low-risk,
or as directly tied to a feature already shipped this week.

`USER_LINE` was specifically checked and ruled out: it exists only as an
enum value in `MeasurementType` with label mappings in `InfoPanel.jsx`/
`Sidebar.jsx` — there is no service method or route anywhere that ever
creates a measurement with this type. It is dead/unreachable code, not a
usable-but-hidden capability, so "completing" it would mean inventing new
behavior rather than exposing existing behavior — out of scope for this
milestone's selection criteria.

## 2. Implementation

### Backend: `src/api/utils/case_manager.py`
- `delete_case(case_id: str) -> bool` — resolves the case's directory via
  the existing `get_case_path()`, and if it exists, removes it entirely with
  `shutil.rmtree` (already imported at module level; no new dependency).
  Returns `False` (not an exception) for a nonexistent case, letting the
  route layer translate that into a clean 404. Touches only the single named
  case's own directory.

### Backend: `src/api/routes/cases.py`
- New route `DELETE /{case_id}` → `delete_case_endpoint()`. Calls
  `case_manager.delete_case()`, raises `404` if it returned `False`,
  otherwise returns `{"status": "deleted", "case_id": case_id}` — matching
  the exact existing response shape already used by
  `DELETE /planning/annotations/{id}` and
  `DELETE /planning/measurements/{id}`, so no new response-model pattern was
  introduced.
- `list_cases`/`delete_case` added to the existing import line from
  `case_manager` — no new import statements added beyond that.

### Frontend
- `frontend/src/api.js`: `deleteCase(caseId)` — a one-line
  `apiFetch(..., { method: 'DELETE' })` helper, matching every other
  function in the file exactly.
- `frontend/src/App.jsx`: `handleDeleteCase(targetCaseId)` — a thin
  `useCallback` wrapper around `deleteCase()`. No `caseId`/`appState`
  changes: `UploadPanel` (where deletion is offered) is only ever rendered
  while `appState === 'initial'`, so there is no "currently active case" to
  reconcile — the currently-open case can never be the one being deleted
  from this screen.
- `frontend/src/UploadPanel.jsx`: each case-history row's existing "Resume"
  button is now paired with a 🗑️ delete button. Clicking it opens a
  `window.confirm()` dialog naming the case's filename (never fabricated —
  echoes only the filename/case_id already displayed); on confirmation it
  calls `onDeleteCase(case_id)` and, on success, removes that entry from the
  already-owned local `caseList` state (no full refetch needed, though the
  list would also be correct on the next natural reload). Loading
  (`deletingCaseId`) and error (`deleteError`) states are handled explicitly
  and shown inline, following the exact pattern already established for
  `loadingCases`/`casesError` in the same component.
- `frontend/src/index.css`: `.case-history-actions` (flex wrapper for the
  now-two per-row buttons) and `.btn-delete-case` (red-tinted, following the
  same visual language as `.btn-resume-case`).

## 3. API Contract

```
DELETE /api/cases/{case_id}

200 OK
{ "status": "deleted", "case_id": "<uuid>" }

404 Not Found
{ "detail": "Case '<uuid>' not found" }
```
No other endpoint's request/response shape was changed.

## 4. Persistence Behavior

Deletion is a direct filesystem operation (`shutil.rmtree` on the case's own
directory) — there is no separate persistence layer, index, or cache to keep
in sync. The existing `GET /api/cases` listing (Day 27) reflects a deletion
immediately and correctly because it always re-scans the directory live; no
caching or state invalidation logic was needed or added.

## 5. Tests

7 new tests added to `tests/test_api.py` (all 20 pre-existing tests
untouched). **Every test in this section operates exclusively on a
monkeypatched, pytest-managed `tmp_path` `CASES_DIR` — none of them ever call
`DELETE` against the real `outputs/cases/` directory or the golden case.**

- `test_delete_case_success` — 200, directory fully removed.
- `test_delete_case_not_found` — 404 for a nonexistent case_id.
- `test_delete_case_removes_all_associated_data` — a case seeded with nested
  `planning/`, `lesions/`, `segmentation/` files is fully removed, not just
  `case.json`.
- `test_delete_case_does_not_affect_other_cases` — deleting one case leaves
  a second case's `case.json` byte-identical and mtime-identical.
- `test_deleted_case_no_longer_appears_in_list` — `GET /api/cases`
  immediately reflects the deletion.
- `test_delete_case_double_delete_returns_404` — deleting twice: 200 then a
  clean 404, not a crash.
- `test_golden_case_untouched_after_deletion_test_battery` — an explicit
  regression safety net: after the entire delete-test battery above has run,
  re-verifies (via the real, unpatched `outputs/cases/` directory) that the
  golden case still exists, is still `completed`, and its
  `model_cyst_left` target is still at voxel `[110, 89, 218]`.

### Results
- `python -m pytest tests/test_api.py -v`: **27 passed, 0 failed** (20
  pre-existing + 7 new).
- `python -m pytest tests/ -q` (full suite): **293 passed, 0 failed, 0
  skipped, 7 warnings, in 833.95s (0:13:53)**. 293 = 286 pre-existing (per
  `docs/PROGRESS.md` §2 before this milestone) + 7 new Day 28 tests. All 7
  warnings are pre-existing library deprecation notices (`httpx`/Starlette
  `TestClient`, SWIG `__module__` attributes, `torch.jit.load`/
  `torch.jit.script` deprecations) — none originate from Day 28 code.
- `cd frontend && npm run build`: **succeeded, exit code 0** — `vite v8.2.2`,
  580 modules transformed, built in 822ms, 0 compilation errors. One
  pre-existing informational warning about the main JS chunk exceeding 500 kB
  (`1,260.15 kB`, unrelated to Day 28 — no new imports or dependencies were
  added by this milestone).

## 6. Real Golden-Case Validation (`b2f89382-9416-4e94-9486-b00c6b1de64b`)

All checks below were performed **read-only** (GET requests / direct
filesystem stat, never DELETE) against the real case directory, via an
in-process `TestClient`. Every check was re-run a second time after the full
293-test battery completed, to confirm nothing in that run touched the
golden case.

| Check | Result |
| :--- | :--- |
| `GET /api/cases` includes the golden case | ✅ 200, present, `status: completed`, `filename: ct_15mm_defaced.nii` |
| `GET /api/cases/{id}` | ✅ 200, `status: completed`, `filename: ct_15mm_defaced.nii` |
| `GET /api/cases/{id}/results` | ✅ 200 |
| `GET /api/cases/{id}/lesions` | ✅ 200 |
| `GET /api/cases/{id}/planning/targets` | ✅ 200 — `model_cyst_left`, voxel `[110, 89, 218]`, `volume_ml: 0.3071`, unchanged |
| `GET /api/cases/{id}/planning/measurements` | ✅ 200, `total_measurements: 0` (pristine baseline — unchanged from all prior milestones; see `docs/DAY22.md` §3) |
| `GET /api/cases/{id}/planning/annotations` | ✅ 200, `total_annotations: 0` (pristine, unchanged) |
| `GET /api/cases/{id}/planning/session` | ✅ 200. Confirmed **read-only**: `planning_session.json`'s on-disk mtime was identical (`23:01:12`, pre-dating this milestone's work) both before and after two separate GET calls and after the full 293-test suite run — `PlanningSessionService.get_session()` only writes when the session file is missing or corrupt, and this case's session file was present and valid throughout. |
| `GET /api/cases/{id}/planning/report` | ✅ 200, full 8+ section JSON payload |
| `GET /api/cases/{id}/planning/explanation` | ✅ 200, full JSON payload |
| `GET /api/cases/{id}/planning/report/pdf` | ✅ 200, `content-type: application/pdf`, 210,696 bytes |
| Golden case directory | ✅ still present at `outputs/cases/b2f89382-9416-4e94-9486-b00c6b1de64b/` |

No DELETE request was ever issued against this case_id, at any point in this
milestone's implementation or validation.

## 7. Governance / Safety Note

`DELETE /api/cases/{case_id}` and every piece of code that supports it
operate purely on filename/status/case_id metadata and raw filesystem
paths — there is no clinical content anywhere in this feature's surface, and
no new clinical claim is possible. The frontend's confirmation dialog names
only the case's own already-displayed filename/case_id, never inventing or
inferring any clinical metadata about the scan.

A scan of every added line (`git diff` restricted to `+` lines) across all
seven genuinely changed Day 28 source/test files
(`src/api/utils/case_manager.py`, `src/api/routes/cases.py`,
`frontend/src/api.js`, `frontend/src/App.jsx`, `frontend/src/UploadPanel.jsx`,
`frontend/src/index.css`, `tests/test_api.py`) for prohibited clinical
terminology (`diagnos*`, `malignan*`, `benign`, `cancer`, `tumor stag*`,
`safe margin`, `surgical clearance`, `recommended approach`,
`treatment plan`, `clinical decision`, `prognosis`, `biopsy result`) returned
**zero matches**. This is expected and correct: the entire Day 28 feature
surface is filesystem/metadata CRUD (case_id, filename, status, directory
existence) with no path that touches lesion findings, measurements, or
clinical text at all.

## 8. `git diff --check` / File Scope / Git State

- `git diff --check`: run twice. Before the `docs/PROGRESS.md` edit: exit
  code 0, no output, across the 7 source/test files. After the
  `docs/PROGRESS.md` edit: exit code 2, flagging 2 lines —
  `docs/PROGRESS.md:3` and `:4` ("trailing whitespace") — both are the
  document's own version/date header lines, which already carried a
  trailing double-space (the standard Markdown hard-line-break convention)
  in the original file before this edit; this change only updated the
  version number and date text on those same two lines, so no *new* kind of
  whitespace issue was introduced, only the same pre-existing convention
  re-flagged because the lines were touched (identical to the pattern
  `docs/DAY22.md`–`docs/DAY27.md` already documented for prior days'
  `PROGRESS.md` edits). (`git status`/`git diff` also emit pre-existing
  LF→CRLF autocrlf warnings on every touched file; those are Git
  line-ending notices, not diff-check errors.)
- Exact file scope — `git status --short` / `git diff --name-only`:
  ```
  M frontend/src/App.jsx
  M frontend/src/UploadPanel.jsx
  M frontend/src/api.js
  M frontend/src/index.css
  M src/api/routes/cases.py
  M src/api/utils/case_manager.py
  M tests/test_api.py
  ?? docs/DAY28.md
  ```
  `docs/PROGRESS.md` is modified as part of finishing this milestone's
  documentation (see §7 above). No other file is touched — this matches
  exactly the expected Day 28 scope, with no unrelated/unexpected files.
- Git state: `HEAD` = `83c985a0de8809e451c91d10c66b383212ddbe63`, identical to
  `origin/main` (the Day 27 commit). Nothing is staged
  (`git diff --cached --stat` is empty). No Day 28 commit exists. No push has
  occurred.

## 9. Limitations

- No "undo" or trash/recovery mechanism — deletion is immediate and
  permanent by design, matching the task's explicit scope (no new
  persistence layer, no database).
- No bulk/multi-select deletion — one case at a time, matching the existing
  one-row-at-a-time interaction pattern already used for Resume.
- No audit log of deletions — out of scope; this is a single-user research
  prototype with no authentication layer.
- The confirmation step is a native `window.confirm()` dialog rather than a
  custom in-app modal — a deliberate minimal-footprint choice consistent
  with "do not introduce unnecessary refactors/infrastructure."

## 10. Explicit Non-Goals

- Did **not** implement case renaming.
- Did **not** implement bulk case deletion or pagination for the case list.
- Did **not** touch the `USER_LINE` measurement type (confirmed dead code,
  not a real gap — see §1).
- Did **not** add authentication/authorization around who may delete a case.
- Did **not** change `case.json`'s schema.
- Did **not** modify any segmentation, measurement, coordinate, planning,
  report, or explanation logic.

## 11. Final Status

All required validation items passed:

- ✅ Full `pytest tests/ -q`: 293 passed, 0 failed, 0 skipped.
- ✅ `npm run build`: succeeded, 0 compilation errors.
- ✅ Golden case (`b2f89382-9416-4e94-9486-b00c6b1de64b`) confirmed intact
  before, during, and after the full validation battery — status, filename,
  target voxel `[110, 89, 218]`, volume `0.3071 mL`, measurements (0),
  annotations (0), and planning session all unchanged; never targeted by
  DELETE.
- ✅ Delete-API test battery (6 tests) passed, entirely on `tmp_path`
  fixtures.
- ✅ All existing golden-case endpoints (`results`, `lesions`, `planning/
  targets`, `planning/measurements`, `planning/annotations`,
  `planning/session`, `planning/report`, `planning/explanation`,
  `planning/report/pdf`) remain functional.
- ✅ Frontend delete code path traced end-to-end with no duplicate
  case-management state machine.
- ✅ `docs/DAY28.md` and `docs/PROGRESS.md` complete, zero placeholders.
- ✅ Governance scan clean — zero prohibited clinical terminology introduced.
- ✅ `git diff --check` — no new whitespace/conflict issues (2 flagged
  lines are the pre-existing Markdown trailing-double-space convention on
  `docs/PROGRESS.md`'s own header, re-flagged only because this milestone
  touched those lines' text — see §8).
- ✅ File scope matches exactly the expected Day 28 set; no unrelated files
  touched.
- ✅ Nothing staged; `HEAD` still `83c985a` = `origin/main`; no Day 28 commit
  or push has occurred.

**READY FOR COMMIT**
