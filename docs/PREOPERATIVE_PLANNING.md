# Preoperative Anatomy Planning & Spatial Measurement Methodology

**Document Version:** 1.0  
**Status:** Active  
**Component:** `src/anatomy`, `src/measurements/spatial_relationships.py`

---

## 1. Scope & Objective

The preoperative planning view in `medical-surgery-planner` transforms raw segmentation masks and deep learning lesion detections into an interactive spatial planning environment. This document outlines the physical distance methodology, registration catalog, and clinical governance protocols.

---

## 2. Computational Distance Methodology

### Anisotropic Voxel Spacing
Clinical CT scans typically feature anisotropic resolutions (e.g., in-plane $0.7\text{ mm} \times 0.7\text{ mm}$, slice thickness $1.5\text{ mm} - 3.0\text{ mm}$). Calculating distances using discrete voxel indices produces distorted, direction-dependent errors.

The spatial relationship engine:
1. Extracts all foreground voxel indices:
   $$\mathcal{V}_{lesion} = \{(i, j, k) \mid M_{lesion}[i, j, k] > 0\}$$
   $$\mathcal{V}_{struct} = \{(i, j, k) \mid M_{struct}[i, j, k] > 0\}$$
2. Scales indices by NIfTI voxel spacing vector $\vec{s} = (s_x, s_y, s_z)$:
   $$\vec{p} = (i \cdot s_x, \, j \cdot s_y, \, k \cdot s_z) \in \mathbb{R}^3$$
3. Uses balanced Euclidean $k$-d trees (`cKDTree`) to evaluate:
   $$D = \min_{\vec{p} \in \mathcal{P}_{lesion}} \min_{\vec{q} \in \mathcal{P}_{struct}} \|\vec{p} - \vec{q}\|_2$$

### Overlap Boundary Condition
If $\mathcal{V}_{lesion} \cap \mathcal{V}_{struct} \neq \emptyset$, the physical distance is strictly set to $0.0\text{ mm}$, and `overlap` is set to `True`.

---

## 3. Structure Registry Catalog

| Key | Display Name | Category | TotalSegmentator Support |
| :--- | :--- | :--- | :--- |
| `kidney_left` | Left Kidney | Organ | Standard 117-class |
| `kidney_right` | Right Kidney | Organ | Standard 117-class |
| `aorta` | Abdominal Aorta | Vascular | Standard 117-class |
| `inferior_vena_cava` | Inferior Vena Cava | Vascular | Standard 117-class |
| `adrenal_gland_left` | Left Adrenal Gland | Endocrine | Standard 117-class |
| `adrenal_gland_right`| Right Adrenal Gland | Endocrine | Standard 117-class |
| `renal_artery` | Renal Artery | Vascular | Sub-model required |
| `renal_vein` | Renal Vein | Vascular | Sub-model required |
| `renal_pelvis` | Renal Pelvis | Collecting System | Sub-model required |
| `ureter` | Ureter | Collecting System | Sub-model required |

Unavailable structures must **never** be synthesized with placeholder geometry or random values. They are reported transparently as unavailable.

---

## 4. Clinical Governance & Safety

1. **Non-Diagnostic Disclaimer**: This system does not diagnose malignancy, predict staging, or assess resectability.
2. **Deterministic Computations**: Distance metrics are strictly mathematical Euclidean clearances derived from segmentation masks.
3. **No Recommended Approach**: Incisions, resection margins, or surgical access routes must be determined solely by qualified surgeons.
