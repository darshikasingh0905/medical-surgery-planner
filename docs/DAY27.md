# DAY 27 — Case History / Resume Existing Case
## Milestone Report

### Milestone Status: Complete ✅
- **Focus**: expose a discoverable, read-only case-history listing so a user
  can find and resume a previously processed case without already knowing
  its UUID — the highest-value gap identified by the Day 27 readiness audit.
- **Scope discipline**: no database, no new persistence layer, no
  `case.json` schema change, no case deletion/renaming, no authentication,
  no changes to segmentation/measurement/coordinate/planning/report logic,
  no App.jsx/PlanningWorkspace.jsx architecture changes.

Baseline recorded before any changes:
```
git log --oneline -1
05b9c7d feat: embed CT views in preoperative report PDF

git status
On branch main. Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

---

## 1. Problem

Direct inspection confirmed: `src/api/routes/cases.py` had ~30 endpoints, every
one requiring an already-known `case_id`; `case_manager.py` had no listing
function; `frontend/src/UploadPanel.jsx` (the only pre-upload screen) had no
path to reopen an existing case. Three real cases already existed on disk
(`outputs/cases/`) with no way to discover any of them except by already
knowing the UUID — directly undercutting the product's purpose as a
workspace meant to be revisited across sessions.

## 2. Current Architecture Reused

- `case_manager.py`'s existing `get_case_info()` (including its missing-
  `case.json` fallback that scans `input/` for a filename) is called
  directly by the new listing function — not reimplemented.
- `App.jsx`'s existing `startPolling()` — the exact same function the
  successful-upload path already calls — is reused verbatim for resuming a
  case; it already correctly handles a case that is already `completed` or
  `failed` on its first poll tick.
- The existing route/service separation pattern (`cases.py` routes call into
  `case_manager.py`, never touching the filesystem directly) is preserved.

## 3. Backend Changes

### `src/api/utils/case_manager.py`
- `_get_case_last_modified(case_id)` — returns `case.json`'s own mtime
  (rewritten whenever status changes) if present, else the case directory's
  mtime. Read-only (`Path.stat()` only).
- `list_cases()` — iterates `CASES_DIR` subdirectories, calls the existing
  `get_case_info()` per case, attaches `last_modified`, sorts most-recent-
  first. Each case is wrapped in its own `try/except`: a malformed/unreadable
  case (e.g. corrupt `case.json`) is skipped, never aborting the whole
  listing. No file is created, modified, or deleted anywhere in this
  function — confirmed by direct testing (§6).

### `src/api/routes/cases.py`
- Two new Pydantic models: `CaseSummary` (`case_id`, `filename: str | None`,
  `status`, `last_modified`) and `CaseListResponse` (`cases: list[CaseSummary]`).
- One new route: `GET /api/cases` → `get_case_list()`, calling
  `case_manager.list_cases()` and wrapping the result in the response model.
  All existing routes are byte-for-byte unchanged.

## 4. Frontend Changes

- `frontend/src/api.js`: `getCaseList()` — a one-line `apiFetch('/cases')`
  helper, matching every other function in the file exactly.
- `frontend/src/UploadPanel.jsx`: a new "📂 Resume a Previous Case" section
  rendered below the existing upload card. Fetches the case list on mount;
  handles loading, empty, and error states explicitly; renders each case's
  filename, a color-coded status badge, and a formatted last-modified date;
  each row has a **Resume** button calling `onResumeCase(case_id)`. The
  existing upload dropzone, file validation, and disclaimer are untouched.
- `frontend/src/App.jsx`: new `handleResumeCase(caseId)` — sets `caseId`,
  sets `appState('processing')`, and calls the **existing** `startPolling()`
  — the identical function `handleUpload`'s success branch already calls.
  No second polling/case-loading implementation was written. Wired to
  `UploadPanel` via a new `onResumeCase` prop.

## 5. API Contract

```
GET /api/cases

200 OK
{
  "cases": [
    {
      "case_id": "b2f89382-9416-4e94-9486-b00c6b1de64b",
      "filename": "ct_15mm_defaced.nii",
      "status": "completed",
      "last_modified": "2026-09-17T13:04:48.763015+00:00"
    },
    ...
  ]
}
```
Sorted most-recently-modified first. Read-only; no other endpoint's
request/response shape was changed.

## 6. Tests

7 new tests added to `tests/test_api.py` (13 pre-existing tests untouched):
`test_list_cases_empty`, `test_list_cases_multiple_and_sorting` (covers
multiple valid cases + a completed case + a failed case + sort order),
`test_list_cases_missing_case_json_fallback`,
`test_list_cases_malformed_case_json_is_skipped_not_fatal` (a genuinely
corrupt `case.json` is skipped, not fatal to the request),
`test_list_cases_is_read_only` (byte-for-byte content and mtime unchanged
before/after), `test_list_cases_response_shape`, and
`test_real_case_appears_in_case_list` (non-destructive, real golden case).

### Results
- `python -m pytest tests/test_api.py -v`: **20 passed, 0 failed** (13
  pre-existing + 7 new).
- `python -m pytest tests/ -q`: **286 passed, 0 failed** (736.96s) — 279
  pre-Day-27 baseline + 7 new, all in `tests/test_api.py`.
- `cd frontend && npm run build`: clean, 0 errors (run twice — once after
  implementation, once again after full-suite validation — identical result
  both times).

## 7. Real-Case Validation (`b2f89382-9416-4e94-9486-b00c6b1de64b`)

Run only after the full pytest suite finished, to avoid the shared-fixture
race observed in earlier milestones.

**`GET /api/cases` — golden case entry:**
```json
{
  "case_id": "b2f89382-9416-4e94-9486-b00c6b1de64b",
  "filename": "ct_15mm_defaced.nii",
  "status": "completed",
  "last_modified": "2026-09-17T13:04:48.763015+00:00"
}
```
`case_id`, `filename`, `status`, and `last_modified` all correct.

**Mixed real on-disk situation** (exactly the 3 cases observed during the
Day 25/27 audits — no synthetic data used):

| case_id | on-disk condition | returned status | 
| :-- | :-- | :-- |
| `b2f89382-...` | `case.json` present, `completed` | `completed` |
| `edf7b02c-...` | `case.json` present, `failed` (historic error) | `failed` |
| `2f799aac-...` | **no `case.json` at all** | `uploaded` (via `get_case_info()`'s existing input/-scan fallback) |

All three returned in a single `200 OK` response — no crash, no case skipped.

**Ordering**: API order (`b2f89382 → edf7b02c → 2f799aac`) matches an
independent sort of the same response by `last_modified` descending —
confirmed identical.

**Read-only confirmation**: two consecutive `GET /api/cases` calls produced
byte-identical JSON (SHA-256 `fed2a7f7...` both times).

**Golden-case file integrity** — explicit before/after comparison across the
entire real-case validation run:
```
measurements.json: content identical, mtime identical (2026-09-29 21:29:11)
annotations.json:  content identical, mtime identical (2026-09-29 21:21:30)
case.json:         content identical, mtime identical (2026-09-17 18:34:48 —
                    unchanged since long before this session, confirming
                    case.json is never rewritten by listing or by any
                    endpoint exercised here)
```
`model_cyst_left` voxel `[110, 89, 218]` unchanged; measurements/annotations
counts unchanged (0/0); session_id present and unaffected.

**Existing endpoint regression** (golden case): `GET /{case_id}` → 200,
`GET /{case_id}/results` → 200, `GET /{case_id}/lesions` → 200,
`GET /planning/report?audience=technical` → 200,
`GET /planning/explanation?audience=technical` → 200. All unaffected by the
Day 27 change.

**Resume code-path verification** (frontend runtime testing not available in
this environment — verified by direct code inspection instead):
```
UploadPanel "Resume" button
  → onClick calls onResumeCase(c.case_id)                      [UploadPanel.jsx]
  → App.jsx's handleResumeCase(resumeCaseId)                   [App.jsx]
       sets caseId, sets appState('processing')
       calls startPolling(resumeCaseId)                        <- the SAME
                                                                    function
                                                                    object
                                                                    handleUpload's
                                                                    success
                                                                    branch
                                                                    already
                                                                    calls
  → startPolling's poll() immediately calls getCaseStatus(id)  [App.jsx, unchanged]
  → data.status === 'completed' branch (pre-existing, unmodified)
       fetches results/structures/lesions/MPR metadata/planning
       targets/measurements exactly as a fresh upload's completion does
```
No second polling implementation exists anywhere in this chain — confirmed
by reading `handleResumeCase` and `handleUpload` side by side: both are
`useCallback`s with `[startPolling]` as their only dependency, calling the
identical `startPolling` closure.

## 8. Governance / Safety Note

`GET /api/cases` returns only filename, processing status, and a filesystem
timestamp — no clinical content, no findings, no measurements, no
interpretation of any kind. No new clinical claim is possible in a case
listing. Resuming a case reaches the exact same, already-governed workspace
state a fresh upload would; no new code path bypasses any existing
disclaimer or governance boundary.

**Scan result**: grepped all 9 changed files
(`src/api/utils/case_manager.py`, `src/api/routes/cases.py`,
`frontend/src/api.js`, `frontend/src/UploadPanel.jsx`, `frontend/src/App.jsx`,
`frontend/src/index.css`, `tests/test_api.py`, `docs/DAY27.md`,
`docs/PROGRESS.md`) for: diagnosis, malignancy, malignant, benign, safe
margin, unsafe margin, surgical clearance, recommended approach, best
approach, surgical risk conclusion, treatment recommendation. Every hit found
was pre-existing, unmodified text from before Day 27 (relocated only by
unrelated insertions elsewhere in the same files — e.g. the pre-existing
disclaimer sentence in `UploadPanel.jsx`, pre-existing docstrings in
`api.js`/`cases.py`, pre-existing sections of `PROGRESS.md`). **Zero
occurrences in any genuinely new Day 27 code** — the case-history feature
itself (filenames, statuses, timestamps) has no surface for clinical
language at all. **Result: clean.**

## 9. Limitations

- `last_modified` is a filesystem-derived proxy (via `case.json`'s own
  mtime), not a dedicated stored timestamp — `case.json`'s schema was
  deliberately not changed to add one, per the task's explicit boundary.
- No pagination — acceptable at current case volumes; would need revisiting
  if the case count grows very large.
- No case deletion, renaming, search, or filtering — explicitly out of scope
  for this milestone.
- A case whose directory exists but has neither `input/` files nor a
  `case.json` (a fully empty case directory) would list with
  `filename: null` and `status: "created"` per `get_case_info()`'s existing
  fallback — not a new behavior, just newly visible.

## 10. Files Changed

- `src/api/utils/case_manager.py` (modified)
- `src/api/routes/cases.py` (modified)
- `frontend/src/api.js` (modified)
- `frontend/src/UploadPanel.jsx` (modified)
- `frontend/src/App.jsx` (modified)
- `frontend/src/index.css` (modified)
- `tests/test_api.py` (modified)
- `docs/DAY27.md` (new)
- `docs/PROGRESS.md` (modified)
