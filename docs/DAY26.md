# DAY 26 — Preoperative Report Imaging (Embedded CT Slice Views)
## Milestone Report

### Milestone Status: Complete ✅
- **Focus**: embed authoritative CT slice imagery (axial/coronal/sagittal) into
  the existing Preoperative Report PDF, per the Day 25 readiness audit's
  highest-value recommendation.
- **Scope discipline**: backend-only, single-function change surface
  (`build_pdf_document()` plus one new private helper it calls); no schema,
  API contract, frontend, segmentation, measurement, or session-persistence
  change of any kind.

Recorded before any changes:
```
git log --oneline -1
b0303fd feat: improve planning workspace visualization and report navigation

git status
On branch main. Your branch is up to date with 'origin/main'.
nothing to commit, working tree clean
```

---

## 1. Implementation

### Reused, not duplicated

The new imaging section calls the exact same function the live MPR viewer
already uses:
```python
mpr_manager.get_slice_bytes(case_id, plane, index,
                             window_width=400.0, window_level=40.0,
                             overlay_lesion=True)
```
No CT loading, HU windowing, lesion-mask overlay, or PNG encoding logic was
reimplemented — `build_pdf_document()` only calls this existing function and
wraps the returned PNG bytes in a ReportLab `Image` flowable.

### Deterministic centering (`_resolve_report_center_voxel`)

A new module-level function in `report_service.py` (used only by
`build_pdf_document()`; `generate_report()` is untouched) implements the exact
fallback chain specified:
1. Primary computational finding's `centroid_voxel`, if present.
2. Else the first planning target's `voxel_coordinate`.
3. Else the CT volume center, computed from `report.imaging_info.dimensions`.
4. Else `None` with an explanatory message — never a fabricated voxel.

### Three fixed-parameter views

For each of `axial` (Z-index), `coronal` (Y-index), `sagittal` (X-index) —
matching the same index convention already used throughout `mpr.py` and
`MPRViewer.jsx` — one slice is rendered at the resolved center voxel using the
system's standard soft-tissue window (WW 400 / WL 40) with
`overlay_lesion=True`. Each embedded image is captioned:
*"**{Plane}** — Slice {index} — WW 400/WL 40 — computational visualization
only"*, and the section intro states the voxel used and its source (finding /
target / volume-center) plus *"Computational visualization only — not a
diagnostic annotation."*

Images are sized proportionally (not stretched) from the CT volume's actual
per-plane pixel dimensions, capped at 150pt on the longer edge.

### Graceful degradation, never fabrication

Each plane's rendering call is individually wrapped in `try/except`. If it
fails, that one plane is replaced with a text note ("*{Plane} imagery
unavailable.*" / "Not generated: {reason}") — matching the report's existing
graceful-degradation style (e.g. "No computational findings detected for this
case."). No placeholder or synthetic image is ever substituted, and a failure
in one plane does not prevent the other two (or the rest of the report) from
being generated.

### Section placement

Inserted as new **Section 3 — "Preoperative Imaging Reference Views [DERIVED
COMPUTATION]"**, immediately after Computational Findings. All following
section numbers were shifted by one (Spatial Relationships is now 4, Anatomy
Registry 5, Planning Targets & Measurements 6, Session Notes 7, Clinical
Review 8, Limitations & Provenance 9) — a cosmetic renumbering only.

### What was deliberately not changed

- `generate_report()` — untouched.
- `report_models.py` (`PreoperativeReport` schema) — untouched; verified by a
  new test that the top-level field set is exactly the pre-existing 15
  sections.
- Both REST endpoints (`/planning/report`, `/planning/report/pdf`) — untouched.
- All frontend code — untouched (the existing Download PDF / Print buttons
  automatically produce the richer document).
- Segmentation, measurement calculation, and planning-session logic — untouched.

---

## 2. Tests

13 new tests added to `tests/test_preoperative_report.py` (nothing existing
modified or weakened):

**Pure logic (`_resolve_report_center_voxel`, no I/O):**
- Prefers finding centroid over planning target when both exist.
- Falls back to planning target when no finding centroid exists.
- Falls back to CT volume center when neither exists.
- Returns `(None, message)` — never a fabricated voxel — when no imaging
  dimensions exist either.

**PDF embedding contract (mocked `mpr_manager.get_slice_bytes`, no golden-case
dependency):**
- Verifies all 3 planes are requested, in the correct order, each with
  `window_width=400.0`, `window_level=40.0`, `overlay_lesion=True`, and the
  correct per-plane index derived from a known voxel (`[110, 89, 218]` →
  axial=218, coronal=89, sagittal=110) — and that exactly 3 images end up
  embedded in the resulting PDF.
- Volume-center fallback (no finding, no target) still produces a valid PDF
  with exactly 3 embedded images.
- A slice-generation failure produces a valid PDF with **zero** embedded
  images (graceful degradation) rather than crashing or fabricating imagery.

**Real-case (golden case, both audiences):**
- Technical and general PDFs both return 200, are valid PDFs, embed exactly 3
  images, and are meaningfully larger than the pre-Day-26 text-only baseline.
- JSON `PreoperativeReport` field set is unchanged (still exactly the 15
  original top-level sections) and the golden finding's `centroid_voxel`
  remains `[110, 89, 218]`.
- `/planning/explanation` remains unaffected (200 OK).

### Verifying embedded images without a new dependency

Per the task's explicit preference, `pypdf` was **not** added to
`requirements.txt`. Instead, tests count occurrences of the literal
`b"/Subtype /Image"` marker in the raw PDF bytes — ReportLab always emits this
exact marker once per embedded image XObject, so a count of 3 is a precise,
dependency-free proof that exactly 3 images were embedded. (One subtlety
discovered while writing these tests: ReportLab deduplicates byte-identical
embedded images into a single shared XObject — the mocked tests therefore
return distinct pixel content per plane so three *genuinely distinct* renders
are exercised, matching what happens with real, non-identical CT slices.)

### Results
- `python -m pytest tests/ -q`: **279 passed, 0 failed** (400.72s) — 268
  pre-Day-26 baseline + 11 new tests, all in `tests/test_preoperative_report.py`.
- `npm run build`: clean, 0 errors (no frontend files touched by this milestone).

---

## 3. Real-Case Verification (`b2f89382-9416-4e94-9486-b00c6b1de64b`)

Run only after the full pytest suite completed, to avoid the shared-fixture
race observed in earlier milestones.

| Check | Technical | General |
| :-- | :-- | :-- |
| `GET .../planning/report/pdf` status | 200 | 200 |
| `Content-Type` | `application/pdf` | `application/pdf` |
| Starts `%PDF-` | ✅ | ✅ |
| Contains `%%EOF` | ✅ | ✅ |
| PDF size | 210,694 bytes | 210,796 bytes |
| Embedded `/Subtype /Image` count | **3** | **3** |

**Center voxel resolution**: `_resolve_report_center_voxel()` called directly
on the real report returned `[110, 89, 218]`, source
`"Centered on model-predicted finding 'cyst_left'"` — exactly the known golden
cyst centroid.

**Plane/parameter verification** (spy wrapping the real, unmocked
`mpr_manager.get_slice_bytes`, so the actual production code path was
exercised, not a stand-in):
```
axial    -> index 218, WW 400.0, WL 40.0, overlay_lesion=True
coronal  -> index  89, WW 400.0, WL 40.0, overlay_lesion=True
sagittal -> index 110, WW 400.0, WL 40.0, overlay_lesion=True
```
All 3 calls used `case_id = b2f89382-9416-4e94-9486-b00c6b1de64b`. This
confirms: exactly 3 planes (axial/coronal/sagittal), each at the index derived
from voxel `[110, 89, 218]` (x=110→sagittal, y=89→coronal, z=218→axial),
soft-tissue window (WW 400 / WL 40), lesion overlay enabled — precisely the
Day 26 specification, with no fabricated imagery.

**Endpoint checks** (both audiences): `/planning/report` → 200/200,
`/planning/explanation` → 200/200.

**Schema/data integrity**:
- JSON report top-level fields exactly match the pre-existing 15-section set
  (`metadata`, `case_overview`, `imaging_info`, `computational_findings`,
  `anatomical_structures`, `spatial_relationships`, `lesion_measurements`,
  `planning_targets`, `planning_measurements`, `planning_session_notes`,
  `procedural_context`, `clinical_review_items`, `system_limitations`,
  `provenance`, `governance`) — unchanged.
- `model_cyst_left` planning target voxel: `[110, 89, 218]` — unchanged.
- `renal_artery`/`renal_vein`/`renal_pelvis`/`ureter` all still
  `available: false` — unchanged.
- Measurements: `0` (unchanged from baseline).
- Annotations: `0` (unchanged from baseline).

**Golden-case file integrity** — explicit before/after comparison:
```
measurements.json (before) == {"case_id": "b2f89382-...", "measurements": []}
measurements.json (after)  == {"case_id": "b2f89382-...", "measurements": []}
annotations.json  (before) == {"case_id": "b2f89382-...", "annotations": []}
annotations.json  (after)  == {"case_id": "b2f89382-...", "annotations": []}
```
Content is textually identical, and both files' filesystem modification
timestamps (23:42:38 / 23:38:04) predate the real-case verification script's
execution — confirming the verification's read-only calls (report/PDF/
explanation generation) never wrote to either file. No golden-case data was
mutated.

---

## 4. Governance Audit

Searched all changed files (`docs/DAY26.md`, `docs/PROGRESS.md`,
`src/planning/report_service.py`, `tests/test_preoperative_report.py`) for:
diagnosis, malignancy, malignant, benign, safe margin, unsafe margin,
surgical clearance, recommended approach, best approach, surgical risk
conclusion, treatment recommendation.

Every hit was individually inspected. All are one of:
- Pre-existing, unmodified text (the module docstring's "DOES NOT... provide
  a clinical diagnosis / assess malignancy... determine surgical risk" list;
  the existing PDF footer "Not for Primary Diagnostic Use"; the pre-existing
  "They do NOT represent surgical clearance, safe margins..." spatial-
  relationships disclaimer; unrelated earlier-day content in
  `docs/PROGRESS.md`).
- An existing negative-case governance test (`test_no_prohibited_clinical_conclusions`)
  and its unmodified fixture disclaimer string — untouched by Day 26.
- This milestone's own new negation-framed disclaimer text: *"Computational
  visualization only — not a diagnostic annotation."*
- This documentation describing the audit itself.

**Result: clean. No new affirmative clinical claim, diagnosis, malignancy
determination, staging, surgical recommendation, or risk conclusion was
introduced anywhere in the Day 26 change.**

Every embedded-image caption and section intro carries the same
"computational visualization only — not a diagnostic annotation" framing
already established elsewhere in the report; no new clinical interpretation
of the imagery is offered anywhere.

---

## 5. Known Limitations

- Image resolution is capped at 150pt on the longer edge for print-friendly
  layout — not intended as a diagnostic-quality viewer, consistent with the
  report's existing "not for primary diagnostic use" framing.
- If a case has multiple computational findings, only the **primary** (first)
  finding's centroid is used — matching the report's existing convention
  elsewhere of treating `computational_findings[0]` as primary.
- PDF file size grows meaningfully (from ~9–10 KB to ~200+ KB for the golden
  case) — acceptable for a research prototype, not yet optimized (e.g. no
  JPEG re-encoding or DPI tuning).
- `pypdf` remains uninstalled/unused in this project; if a future milestone
  needs actual text/image content extraction (not just presence-counting),
  it will need to be added deliberately at that time.
