"""
src/measurements/spatial_relationships.py

Computational Spatial Relationships Engine for Preoperative Anatomy.
Calculates physical minimum Euclidean distances and volumetric overlap between
model-predicted lesion segmentations and surrounding anatomical structures.

CLINICAL GOVERNANCE & SAFETY NOTICE:
All calculated distances are computational measurements derived from segmented masks.
They do NOT constitute validated surgical clearance, margins, or operative recommendations.
Terminology strictly adheres to "computational minimum distance" and "model-derived spatial relationship".
Never infer resectability, operative safety, or clinical margins from these values.
"""

from pathlib import Path
from typing import Any
import nibabel as nib
import numpy as np
from scipy.spatial import cKDTree

from src.anatomy.structure_registry import (
    STRUCTURE_CATALOG,
    inspect_case_structures,
    resolve_case_paths,
)


def calculate_mask_pair_spatial_relationship(
    lesion_mask: np.ndarray,
    structure_mask: np.ndarray | None,
    spacing: tuple[float, float, float] | list[float] | np.ndarray,
) -> dict[str, Any]:
    """
    Computes computational spatial relationship between a lesion mask and an anatomical structure mask.
    Strictly accounts for anisotropic voxel spacing (dx, dy, dz) in physical millimeters.

    Rules:
    - If structure_mask is None or has 0 foreground voxels:
        available = False, distance_mm = None, overlap = None
    - If masks intersect (overlap):
        available = True, distance_mm = 0.0, overlap = True
    - If separated:
        available = True, distance_mm = min Euclidean distance in mm, overlap = False

    Args:
        lesion_mask: 3D binary numpy array for the lesion.
        structure_mask: 3D binary numpy array for the anatomical structure (or None).
        spacing: Physical voxel dimensions in mm [dx, dy, dz].

    Returns:
        Dictionary containing available, distance_mm, overlap, and voxel statistics.
    """
    if lesion_mask.ndim != 3:
        raise ValueError(f"Expected 3D lesion mask, got shape {lesion_mask.shape}")

    lesion_fg = np.argwhere(lesion_mask > 0)
    if len(lesion_fg) == 0:
        return {
            "available": True if structure_mask is not None else False,
            "overlap": False if structure_mask is not None else None,
            "overlap_voxel_count": 0,
            "distance_mm": None,
            "computational_minimum_distance_mm": None,
            "note": "Lesion mask contains 0 foreground voxels",
        }

    if structure_mask is None:
        return {
            "available": False,
            "overlap": None,
            "overlap_voxel_count": 0,
            "distance_mm": None,
            "computational_minimum_distance_mm": None,
            "note": "Target structure mask not provided",
        }

    if structure_mask.shape != lesion_mask.shape:
        raise ValueError(
            f"Shape mismatch: lesion {lesion_mask.shape} vs structure {structure_mask.shape}"
        )

    structure_fg = np.argwhere(structure_mask > 0)
    if len(structure_fg) == 0:
        return {
            "available": False,
            "overlap": None,
            "overlap_voxel_count": 0,
            "distance_mm": None,
            "computational_minimum_distance_mm": None,
            "note": "Target structure mask contains 0 foreground voxels",
        }

    # Direct overlap check
    overlap_voxels = int(np.sum((lesion_mask > 0) & (structure_mask > 0)))
    if overlap_voxels > 0:
        return {
            "available": True,
            "overlap": True,
            "overlap_voxel_count": overlap_voxels,
            "distance_mm": 0.0,
            "computational_minimum_distance_mm": 0.0,
            "note": "Masks overlap spatially",
        }

    # Physical distance computation with anisotropic voxel spacing
    spacing_arr = np.array(spacing[:3], dtype=np.float64)
    lesion_pts_mm = lesion_fg * spacing_arr
    structure_pts_mm = structure_fg * spacing_arr

    # Build k-d tree on anatomical structure points for fast nearest-neighbor query
    tree = cKDTree(structure_pts_mm)
    distances, _ = tree.query(lesion_pts_mm)
    min_dist_mm = round(float(np.min(distances)), 3)

    return {
        "available": True,
        "overlap": False,
        "overlap_voxel_count": 0,
        "distance_mm": min_dist_mm,
        "computational_minimum_distance_mm": min_dist_mm,
        "note": "Computational minimum Euclidean distance",
    }


def compute_lesion_spatial_relationships(
    lesion_mask_path: str | Path,
    case_dir_or_id: str | Path | None = None,
    structure_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Computes spatial relationships between a lesion mask and all registered anatomical structures
    for a given case.

    Inspects actual NIfTI masks on disk. Unavailable structures are explicitly returned
    with available=False, distance_mm=None, overlap=None, and a clear explanation.

    Args:
        lesion_mask_path: Path to the lesion NIfTI file (.nii / .nii.gz).
        case_dir_or_id: Case UUID or directory path.
        structure_ids: Optional list of specific structure IDs to evaluate.
                       If None, evaluates all structures in the STRUCTURE_CATALOG.

    Returns:
        Structured dictionary of relationships, availability, and safety disclaimer.
    """
    lesion_p = Path(lesion_mask_path)
    if not lesion_p.exists():
        raise FileNotFoundError(f"Lesion mask not found: {lesion_p}")

    lesion_img = nib.load(str(lesion_p))
    lesion_data = lesion_img.get_fdata() > 0
    spacing = tuple(float(s) for s in lesion_img.header.get_zooms()[:3])

    # Audit structures for this case
    case_structs = inspect_case_structures(case_dir_or_id)
    target_ids = structure_ids or list(STRUCTURE_CATALOG.keys())

    relationships = []
    available_count = 0
    unavailable_count = 0
    overlap_count = 0

    for st_id in target_ids:
        defn = STRUCTURE_CATALOG.get(st_id)
        struct_meta = case_structs.get(st_id)

        display_name = defn["display_name"] if defn else st_id.replace("_", " ").title()
        category = defn["category"] if defn else "other"
        mesh_available = struct_meta.get("mesh_available", False) if struct_meta else False

        if struct_meta and struct_meta["available"] and struct_meta["mask_path"]:
            mask_path = Path(struct_meta["mask_path"])
            try:
                st_img = nib.load(str(mask_path))
                st_data = st_img.get_fdata() > 0
                rel_metrics = calculate_mask_pair_spatial_relationship(
                    lesion_data, st_data, spacing
                )

                is_avail = rel_metrics["available"]
                overlap = rel_metrics["overlap"]
                dist = rel_metrics["distance_mm"]

                if is_avail:
                    available_count += 1
                    if overlap:
                        overlap_count += 1
                else:
                    unavailable_count += 1

                relationships.append({
                    "structure_id": st_id,
                    "display_name": display_name,
                    "category": category,
                    "available": is_avail,
                    "distance_mm": dist,
                    "computational_minimum_distance_mm": dist,
                    "overlap": overlap,
                    "overlap_voxel_count": rel_metrics["overlap_voxel_count"],
                    "mesh_available": mesh_available,
                    "status_reason": None if is_avail else rel_metrics.get("note"),
                })
            except Exception as e:
                unavailable_count += 1
                relationships.append({
                    "structure_id": st_id,
                    "display_name": display_name,
                    "category": category,
                    "available": False,
                    "distance_mm": None,
                    "computational_minimum_distance_mm": None,
                    "overlap": None,
                    "overlap_voxel_count": 0,
                    "mesh_available": mesh_available,
                    "status_reason": f"Error processing mask: {str(e)}",
                })
        else:
            unavailable_count += 1
            reason = struct_meta["status_reason"] if struct_meta else "Structure not segmented"
            relationships.append({
                "structure_id": st_id,
                "display_name": display_name,
                "category": category,
                "available": False,
                "distance_mm": None,
                "computational_minimum_distance_mm": None,
                "overlap": None,
                "overlap_voxel_count": 0,
                "mesh_available": False,
                "status_reason": reason,
            })

    lesion_id = lesion_p.name.split(".")[0]

    return {
        "lesion_id": lesion_id,
        "voxel_spacing_mm": list(spacing),
        "relationships": relationships,
        "summary": {
            "total_structures_evaluated": len(relationships),
            "available_structures_count": available_count,
            "unavailable_structures_count": unavailable_count,
            "overlapping_structures_count": overlap_count,
        },
        "safety_disclaimer": (
            "Distances are computational minimum Euclidean measurements derived from segmented masks "
            "and are not validated surgical clearance measurements. Clinical interpretation required."
        ),
    }
