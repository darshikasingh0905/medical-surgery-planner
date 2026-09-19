"""
src/anatomy/structure_registry.py

Machine-readable Anatomical Structure Registry for Preoperative Planning.
Maintains canonical definitions for renal and abdominal structures relevant
to surgical visualization and computational spatial relationships.

Inspects actual segmentation masks on disk to verify availability without
fabricating non-existent structures or placeholder geometry.

CLINICAL GOVERNANCE NOTICE:
This module provides computational structure metadata and file mapping for research
and educational visualization. It does not infer surgical clearance or clinical operative approach.
"""

from pathlib import Path
from typing import Any
import nibabel as nib
import numpy as np

# Canonical definition of structures relevant to renal preoperative planning
STRUCTURE_CATALOG: dict[str, dict[str, Any]] = {
    "kidney_left": {
        "structure_id": "kidney_left",
        "display_name": "Left Kidney",
        "category": "organ",
        "default_filename": "kidney_left.nii.gz",
        "candidate_filenames": ["kidney_left.nii.gz"],
        "default_color": "#E5A93C",
        "description": "Primary left renal parenchyma",
        "unavailable_explanation": "Left kidney mask not found in segmentation outputs",
    },
    "kidney_right": {
        "structure_id": "kidney_right",
        "display_name": "Right Kidney",
        "category": "organ",
        "default_filename": "kidney_right.nii.gz",
        "candidate_filenames": ["kidney_right.nii.gz"],
        "default_color": "#D48828",
        "description": "Contralateral right renal parenchyma",
        "unavailable_explanation": "Right kidney mask not found in segmentation outputs",
    },
    "aorta": {
        "structure_id": "aorta",
        "display_name": "Abdominal Aorta",
        "category": "vascular",
        "default_filename": "aorta.nii.gz",
        "candidate_filenames": ["aorta.nii.gz"],
        "default_color": "#FF6347",
        "description": "Major arterial vascular trunk",
        "unavailable_explanation": "Aortic mask not found in segmentation outputs",
    },
    "inferior_vena_cava": {
        "structure_id": "inferior_vena_cava",
        "display_name": "Inferior Vena Cava",
        "category": "vascular",
        "default_filename": "inferior_vena_cava.nii.gz",
        "candidate_filenames": ["inferior_vena_cava.nii.gz", "ivc.nii.gz"],
        "default_color": "#3B82F6",
        "description": "Major venous vascular trunk",
        "unavailable_explanation": "Inferior vena cava mask not found in segmentation outputs",
    },
    "renal_artery": {
        "structure_id": "renal_artery",
        "display_name": "Renal Artery",
        "category": "vascular",
        "default_filename": "renal_artery.nii.gz",
        "candidate_filenames": [
            "renal_artery.nii.gz",
            "renal_artery_left.nii.gz",
            "renal_artery_right.nii.gz",
        ],
        "default_color": "#EF4444",
        "description": "Renal arterial branch",
        "unavailable_explanation": "Specialized vascular sub-segmentation model not present in standard 117-class CT segmentation",
    },
    "renal_vein": {
        "structure_id": "renal_vein",
        "display_name": "Renal Vein",
        "category": "vascular",
        "default_filename": "renal_vein.nii.gz",
        "candidate_filenames": [
            "renal_vein.nii.gz",
            "renal_vein_left.nii.gz",
            "renal_vein_right.nii.gz",
        ],
        "default_color": "#60A5FA",
        "description": "Renal venous drainage",
        "unavailable_explanation": "Specialized vascular sub-segmentation model not present in standard 117-class CT segmentation",
    },
    "renal_pelvis": {
        "structure_id": "renal_pelvis",
        "display_name": "Renal Pelvis",
        "category": "collecting_system",
        "default_filename": "renal_pelvis.nii.gz",
        "candidate_filenames": [
            "renal_pelvis.nii.gz",
            "renal_pelvis_left.nii.gz",
            "renal_pelvis_right.nii.gz",
        ],
        "default_color": "#F59E0B",
        "description": "Renal urinary collecting pelvis",
        "unavailable_explanation": "Specialized pyelocaliceal collecting system model not present in standard 117-class CT segmentation",
    },
    "ureter": {
        "structure_id": "ureter",
        "display_name": "Ureter",
        "category": "collecting_system",
        "default_filename": "ureter.nii.gz",
        "candidate_filenames": [
            "ureter.nii.gz",
            "ureter_left.nii.gz",
            "ureter_right.nii.gz",
        ],
        "default_color": "#FCD34D",
        "description": "Urinary conduit to bladder",
        "unavailable_explanation": "Specialized ureteral sub-segmentation model not present in standard 117-class CT segmentation",
    },
    "adrenal_gland_left": {
        "structure_id": "adrenal_gland_left",
        "display_name": "Left Adrenal Gland",
        "category": "endocrine",
        "default_filename": "adrenal_gland_left.nii.gz",
        "candidate_filenames": ["adrenal_gland_left.nii.gz"],
        "default_color": "#D97706",
        "description": "Ipsilateral left adrenal gland",
        "unavailable_explanation": "Left adrenal gland mask not found in segmentation outputs",
    },
    "adrenal_gland_right": {
        "structure_id": "adrenal_gland_right",
        "display_name": "Right Adrenal Gland",
        "category": "endocrine",
        "default_filename": "adrenal_gland_right.nii.gz",
        "candidate_filenames": ["adrenal_gland_right.nii.gz"],
        "default_color": "#B45309",
        "description": "Contralateral right adrenal gland",
        "unavailable_explanation": "Right adrenal gland mask not found in segmentation outputs",
    },
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CASES_DIR = PROJECT_ROOT / "outputs" / "cases"
DEFAULT_SEGMENTATIONS_DIR = PROJECT_ROOT / "outputs" / "segmentations"
DEFAULT_MESHES_DIR = PROJECT_ROOT / "outputs" / "meshes"


def resolve_case_paths(case_dir_or_id: str | Path | None = None) -> tuple[Path, Path]:
    """
    Resolves the segmentation and meshes directory paths for a given case or default outputs.
    """
    if case_dir_or_id is None:
        return DEFAULT_SEGMENTATIONS_DIR, DEFAULT_MESHES_DIR

    p = Path(case_dir_or_id)
    if p.is_dir():
        # Passed an existing directory directly
        seg_dir = p / "segmentation" if (p / "segmentation").is_dir() else p
        mesh_dir = p / "meshes" if (p / "meshes").is_dir() else p
        return seg_dir, mesh_dir

    # Passed a case UUID
    case_path = DEFAULT_CASES_DIR / str(case_dir_or_id)
    if case_path.is_dir():
        seg_dir = case_path / "segmentation"
        mesh_dir = case_path / "meshes"
        return seg_dir, mesh_dir

    # Fallback to direct path or default
    return DEFAULT_SEGMENTATIONS_DIR, DEFAULT_MESHES_DIR


def get_structure_definitions() -> dict[str, dict[str, Any]]:
    """Returns static canonical catalog definitions."""
    return STRUCTURE_CATALOG


def inspect_case_structures(
    case_dir_or_id: str | Path | None = None,
    verify_voxels: bool = True,
) -> dict[str, dict[str, Any]]:
    """
    Audits the case segmentation and mesh directories against the structure catalog.
    Returns a machine-readable dictionary indicating for each structure:
    - availability status
    - mask file path (if available)
    - mesh availability (if .obj exists)
    - voxel count (if verified)
    - reason (if unavailable)
    """
    seg_dir, mesh_dir = resolve_case_paths(case_dir_or_id)
    results = {}

    for struct_id, defn in STRUCTURE_CATALOG.items():
        found_mask_path: Path | None = None
        for candidate in defn["candidate_filenames"]:
            cand_p = seg_dir / candidate
            if cand_p.is_file():
                found_mask_path = cand_p
                break

        is_avail = False
        voxel_count = 0
        unavail_reason = defn["unavailable_explanation"]

        if found_mask_path is not None:
            if verify_voxels:
                try:
                    img = nib.load(str(found_mask_path))
                    data = img.get_fdata()
                    voxel_count = int(np.sum(data > 0))
                    if voxel_count > 0:
                        is_avail = True
                        unavail_reason = None
                    else:
                        is_avail = False
                        unavail_reason = f"Mask file '{found_mask_path.name}' contains 0 foreground voxels"
                except Exception as e:
                    is_avail = False
                    unavail_reason = f"Error reading mask '{found_mask_path.name}': {str(e)}"
            else:
                is_avail = True
                unavail_reason = None

        mesh_file = mesh_dir / f"{struct_id}.obj"
        has_mesh = mesh_file.is_file()

        results[struct_id] = {
            "structure_id": struct_id,
            "display_name": defn["display_name"],
            "category": defn["category"],
            "available": is_avail,
            "mask_path": str(found_mask_path) if is_avail and found_mask_path else None,
            "mask_filename": found_mask_path.name if found_mask_path else None,
            "mesh_available": has_mesh,
            "mesh_filename": f"{struct_id}.obj" if has_mesh else None,
            "voxel_count": voxel_count if is_avail else 0,
            "color": defn["default_color"],
            "description": defn["description"],
            "status_reason": unavail_reason,
        }

    return results


def get_available_structures(
    case_dir_or_id: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Returns only structures that genuinely exist and have foreground voxels."""
    all_structs = inspect_case_structures(case_dir_or_id)
    return {k: v for k, v in all_structs.items() if v["available"]}


def get_structure_metadata(
    structure_id: str,
    case_dir_or_id: str | Path | None = None,
) -> dict[str, Any] | None:
    """Returns metadata for a specific structure in a case, or None if unknown structure_id."""
    if structure_id not in STRUCTURE_CATALOG:
        return None
    all_structs = inspect_case_structures(case_dir_or_id)
    return all_structs.get(structure_id)


def get_structure_mask_path(
    structure_id: str,
    case_dir_or_id: str | Path | None = None,
) -> Path | None:
    """Returns the Path to the structure mask if available, or None."""
    meta = get_structure_metadata(structure_id, case_dir_or_id)
    if meta and meta["available"] and meta["mask_path"]:
        return Path(meta["mask_path"])
    return None


def is_structure_available(
    structure_id: str,
    case_dir_or_id: str | Path | None = None,
) -> bool:
    """Checks whether a structure is genuinely available in the specified case."""
    meta = get_structure_metadata(structure_id, case_dir_or_id)
    return bool(meta and meta["available"])
