# Day 15 — Preoperative Anatomy Relationships + Interactive Planning View

**Document Version:** 1.0  
**Date:** September 2026  
**Status:** Complete (65/65 tests passing, frontend builds with zero errors)

---

## 1. Executive Summary

Day 15 transitions the 3D viewer into a dedicated **Preoperative Planning Interface**. In this layer, the system audits genuine anatomical segmentation masks on disk, computes physical millimeter Euclidean spatial relationships between segmented lesions and surrounding anatomical structures, and provides interactive planning controls without fabricating non-existent anatomy or modifying underlying segmentation data.

### Critical Safety Rule & Terminology
This system is an **educational and research prototype**. It is **NOT** a diagnostic or autonomous surgical system.
The system strictly adheres to the following computational terminology:
- **"Computational spatial relationship"**
- **"Model-derived minimum Euclidean distance"**
- **"Segmented anatomical structure"**
- **"Available in this case"** vs **"Not available in this case"**
- **"Requires clinical interpretation"**

The application strictly avoids diagnostic or surgical judgment language (e.g., "safe to operate", "resectable", "surgical clearance", "benign", "malignant").

---

## 2. Anatomical Structure Audit

A comprehensive inspection was performed across the default TotalSegmentator 117-class segmentation outputs for genuine case `b2f89382-9416-4e94-9486-b00c6b1de64b` and `outputs/segmentations/`.

### Structures Audited in Renal Planning Catalog

| Structure ID | Display Name | Category | Available in Case? | Foreground Voxels | Mesh Available (.obj) | Status Details |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| `kidney_left` | Left Kidney | Organ | **Yes** | 70,496 | **Yes** | Host organ for cyst |
| `kidney_right` | Right Kidney | Organ | **Yes** | 60,416 | **Yes** | Contralateral kidney |
| `aorta` | Abdominal Aorta | Vascular | **Yes** | 53,732 | **Yes** | Major arterial trunk |
| `inferior_vena_cava`| Inferior Vena Cava | Vascular | **Yes** | 21,580 | **Yes** | Major venous trunk |
| `adrenal_gland_left`| Left Adrenal Gland | Endocrine | **Yes** | 2,536 | **Yes** | Ipsilateral adrenal gland |
| `adrenal_gland_right`| Right Adrenal Gland | Endocrine | **Yes** | 1,864 | **Yes** | Contralateral adrenal gland |
| `renal_artery` | Renal Artery | Vascular | **No** | 0 | **No** | Requires specialized vascular sub-segmentation model |
| `renal_vein` | Renal Vein | Vascular | **No** | 0 | **No** | Requires specialized vascular sub-segmentation model |
| `renal_pelvis` | Renal Pelvis | Collecting System | **No** | 0 | **No** | Requires pyelocaliceal sub-segmentation model |
| `ureter` | Ureter | Collecting System | **No** | 0 | **No** | Requires specialized ureteral sub-segmentation model |

**No fake structures were invented.** Unavailable structures are explicitly cataloged and reported as `Not available in this case`.

---

## 3. Physical Distance & Spatial Relationship Methodology

### Engine Implementation: `src/measurements/spatial_relationships.py`

Spatial measurements are calculated from genuine 3D NIfTI segmentation masks using anisotropic voxel spacings $(dx, dy, dz)$:

1. **Voxel Coordinate Scaling**:
   Voxel indices $(i, j, k)$ are transformed to physical space:
   $$\vec{P}_{mm} = [i \cdot dx, \, j \cdot dy, \, k \cdot dz]$$
   where for case `b2f89382-9416-4e94-9486-b00c6b1de64b`, $dx = 1.5\text{ mm}, dy = 1.5\text{ mm}, dz = 1.5\text{ mm}$.

2. **Spatial Overlap Detection**:
   $$\text{Overlap} = \sum (\text{Lesion} > 0 \;\land\; \text{Structure} > 0) > 0$$
   If masks overlap, the computational minimum distance is defined as:
   $$\text{distance\_mm} = 0.0\text{ mm}$$

3. **Sub-second Minimum Distance via $k$-d Tree**:
   When masks do not overlap, a $k$-d tree (`scipy.spatial.cKDTree`) is constructed on the physical coordinates of the anatomical structure:
   $$d_{min} = \min_{\vec{p} \in \text{Lesion}} \left( \min_{\vec{q} \in \text{Structure}} \|\vec{p} - \vec{q}\|_2 \right)$$
   Query execution runs in $< 50\text{ ms}$.

4. **Unavailable Structures Handling**:
   When an anatomical structure mask does not exist or contains 0 foreground voxels:
   - `available = False`
   - `distance_mm = None`
   - `overlap = None`
   - `status_reason = "<Reason why model did not segment this structure>"`

---

## 4. Real-Case Validation: `b2f89382-9416-4e94-9486-b00c6b1de64b`

On the genuine KiTS23 model-predicted cyst (`cyst_left`, 91 foreground voxels, $0.3071\text{ mL}$):

| Anatomical Structure | Availability | Computational Min Distance | Overlap | Clinical Governance Note |
| :--- | :---: | :---: | :---: | :--- |
| **Left Kidney** | Available | **0.00 mm** | **Yes** | Lesion is embedded in left renal parenchyma |
| **Left Adrenal Gland**| Available | **39.83 mm** | **No** | Ipsilateral clearance |
| **Abdominal Aorta** | Available | **54.10 mm** | **No** | Distance to major arterial trunk |
| **Inferior Vena Cava**| Available | **90.34 mm** | **No** | Distance to major venous trunk |
| **Right Kidney** | Available | **91.92 mm** | **No** | Distance to contralateral kidney |
| **Right Adrenal Gland**| Available | **98.17 mm** | **No** | Contralateral clearance |
| **Renal Artery** | Not available | — | — | Not present in 117-class CT segmentation |
| **Renal Vein** | Not available | — | — | Not present in 117-class CT segmentation |
| **Renal Pelvis** | Not available | — | — | Not present in 117-class CT segmentation |
| **Ureter** | Not available | — | — | Not present in 117-class CT segmentation |

---

## 5. API Enhancements

### New Endpoints in `src/api/routes/cases.py`:
1. `GET /api/cases/{case_id}/structures`:
   Returns machine-readable audit of all registered anatomical structures with availability, mask paths, and mesh status.
2. `GET /api/cases/{case_id}/lesions/{lesion_id}/relationships`:
   Returns computational spatial relationships between that lesion and all registered structures. Caches results to `measurements/relationships_{lesion_id}.json`.
3. `GET /api/cases/{case_id}/meshes/{organ}`:
   Expanded `ALLOWED_ORGANS` to serve `inferior_vena_cava.obj`, `kidney_right.obj`, `adrenal_gland_left.obj`, and `adrenal_gland_right.obj`.

---

## 6. Frontend & Preoperative Planning Interface

### 1. View Mode Switcher
- Dedicated toggle in the sidebar: **Normal View** vs **Planning View**.
- Header and sidebar display clear badges and subheadings:
  *"Preoperative Planning View — Computational visualization for research/educational use. Clinical interpretation required."*

### 2. Anatomical Structure Controls
- In Planning View, the Sidebar renders the **Anatomical Structures** section.
- For available structures: visibility toggle (👁️/👁️‍🗨️), category badge, and camera focus button (🎯).
- For unavailable structures: rendered disabled with an explicit notice: *"Not available in this case"*.

### 3. Spatial Relationships Table in `InfoPanel.jsx`
- Detailed matrix displaying Structure, Availability, Computational Minimum Distance, and Overlap.
- Mandatory safety disclaimer note appended beneath table.

### 4. Case Planning Summary Panel
- Summarizes computational facts: Target, Detected Class, Volume, Primary Organ, Available Anatomy count, Unavailable Anatomy count, and Required Clinical Review note.

### 5. Enhanced 3D Viewer & Camera Controls
- Dynamically loads available structure meshes (`inferior_vena_cava.obj`, `kidney_right.obj`, etc.).
- Smooth camera focusing derived from genuine mesh bounding box centers and lesion centroids.
- In-viewport HUD with floating **Reset View** (🔄) button.
- Structure visual emphasis / highlighting on selection with non-selected organ dimming.

---

## 7. Verification & Automated Tests

- **Unit Tests (`pytest tests/ -v`)**: **65/65 passing** (16 new Day 15 tests added, all 49 existing tests preserved).
- **Frontend Build (`npm run build`)**: Vite production bundle compiled in **528 ms** with 0 errors.
- **End-to-End Real Case Script (`python -m scripts.validate_day15`)**: All assertions passed on case `b2f89382-9416-4e94-9486-b00c6b1de64b`.
