"""
src/measurements/lesion_measurements.py

Surgical Spatial Measurement Engine for Renal Lesions.
Calculates physical volume, anisotropic bounding box extents, 3D centroid,
and minimum Euclidean computational distances from lesion boundaries to key
anatomical landmarks and vascular structures.

IMPORTANT CLINICAL GOVERNANCE & SAFETY:
These spatial measurements are strictly computational metrics derived from
segmentation masks. They do NOT represent clinically validated surgical margins,
histological margins, or operative resectability recommendations.
"""

from pathlib import Path
from typing import Any
import numpy as np
import nibabel as nib
from scipy import ndimage
from scipy.spatial import cKDTree


def calculate_lesion_volume(
    mask: np.ndarray,
    spacing: tuple[float, float, float] | list[float] | np.ndarray,
) -> dict[str, Any]:
    """
    Computes voxel-based physical volume in mm³, cm³, and mL.
    Handles arbitrary anisotropic voxel spacings (dx, dy, dz).

    Args:
        mask: 3D binary numpy array.
        spacing: Physical voxel dimensions in mm (dx, dy, dz).

    Returns:
        Dictionary with foreground voxel count, voxel volume, and calculated volumes.
    """
    if mask.ndim != 3:
        raise ValueError(f"Expected 3D mask array, got shape {mask.shape}")

    sx, sy, sz = float(spacing[0]), float(spacing[1]), float(spacing[2])
    voxel_volume_mm3 = sx * sy * sz

    foreground_voxels = int(np.sum(mask > 0))
    vol_mm3 = float(foreground_voxels * voxel_volume_mm3)
    vol_cm3 = float(vol_mm3 / 1000.0)
    vol_ml = float(vol_cm3)

    return {
        "foreground_voxels": foreground_voxels,
        "voxel_spacing_mm": [sx, sy, sz],
        "voxel_volume_mm3": round(voxel_volume_mm3, 6),
        "volume_mm3": round(vol_mm3, 4),
        "volume_cm3": round(vol_cm3, 4),
        "volume_ml": round(vol_ml, 4),
    }


def calculate_lesion_bounding_box(
    mask: np.ndarray,
    spacing: tuple[float, float, float] | list[float] | np.ndarray,
) -> dict[str, Any]:
    """
    Computes discrete voxel bounding box and true physical millimeter dimensions.

    Args:
        mask: 3D binary numpy array.
        spacing: Physical voxel dimensions in mm (dx, dy, dz).

    Returns:
        Dictionary with voxel bounds, physical dimensions (x_mm, y_mm, z_mm),
        and physical extent extents.
    """
    if mask.ndim != 3:
        raise ValueError(f"Expected 3D mask array, got shape {mask.shape}")

    indices = np.argwhere(mask > 0)
    if len(indices) == 0:
        return {
            "voxel_bounds": [[0, 0], [0, 0], [0, 0]],
            "voxel_dimensions": [0, 0, 0],
            "x_mm": 0.0,
            "y_mm": 0.0,
            "z_mm": 0.0,
            "dimensions_mm": [0.0, 0.0, 0.0],
        }

    sx, sy, sz = float(spacing[0]), float(spacing[1]), float(spacing[2])
    min_b = indices.min(axis=0)
    max_b = indices.max(axis=0)

    voxel_dims = [int(max_b[i] - min_b[i] + 1) for i in range(3)]
    dim_x_mm = round(voxel_dims[0] * sx, 3)
    dim_y_mm = round(voxel_dims[1] * sy, 3)
    dim_z_mm = round(voxel_dims[2] * sz, 3)

    return {
        "voxel_bounds": [
            [int(min_b[0]), int(max_b[0])],
            [int(min_b[1]), int(max_b[1])],
            [int(min_b[2]), int(max_b[2])],
        ],
        "voxel_dimensions": voxel_dims,
        "x_mm": dim_x_mm,
        "y_mm": dim_y_mm,
        "z_mm": dim_z_mm,
        "dimensions_mm": [dim_x_mm, dim_y_mm, dim_z_mm],
    }


def calculate_lesion_centroid(
    mask: np.ndarray,
    spacing: tuple[float, float, float] | list[float] | np.ndarray,
    affine: np.ndarray | None = None,
) -> dict[str, Any]:
    """
    Computes the 3D geometric centroid of the lesion mask.
    Returns centroid in voxel coordinates, millimeter scaled coordinates,
    and NIfTI world coordinates (if affine matrix is provided).

    Args:
        mask: 3D binary numpy array.
        spacing: Physical voxel dimensions in mm (dx, dy, dz).
        affine: Optional 4x4 affine matrix for scanner world coordinates.

    Returns:
        Dictionary with voxel_centroid, physical_centroid_mm, and world_centroid_mm.
    """
    if mask.ndim != 3:
        raise ValueError(f"Expected 3D mask array, got shape {mask.shape}")

    indices = np.argwhere(mask > 0)
    if len(indices) == 0:
        return {
            "voxel_centroid": [0.0, 0.0, 0.0],
            "physical_centroid_mm": [0.0, 0.0, 0.0],
            "world_centroid_mm": [0.0, 0.0, 0.0],
        }

    voxel_c = indices.mean(axis=0)
    sx, sy, sz = float(spacing[0]), float(spacing[1]), float(spacing[2])
    physical_c = [
        round(float(voxel_c[0] * sx), 3),
        round(float(voxel_c[1] * sy), 3),
        round(float(voxel_c[2] * sz), 3),
    ]

    result = {
        "voxel_centroid": [round(float(c), 3) for c in voxel_c],
        "physical_centroid_mm": physical_c,
    }

    if affine is not None:
        world_homo = affine @ np.array([voxel_c[0], voxel_c[1], voxel_c[2], 1.0])
        result["world_centroid_mm"] = [round(float(c), 3) for c in world_homo[:3]]
    else:
        result["world_centroid_mm"] = physical_c

    return result


def calculate_minimum_distance_to_structure(
    lesion_mask: np.ndarray,
    structure_mask: np.ndarray,
    spacing: tuple[float, float, float] | list[float] | np.ndarray,
    check_boundary_only: bool = False,
) -> float:
    """
    Computes the exact minimum physical Euclidean distance in millimeters from the
    lesion boundary to an anatomical structure using kd-tree point indexing.

    Properly weights spatial axes by physical voxel dimensions (dx, dy, dz),
    guaranteeing accurate physical metric distances for anisotropic CT scans.

    Args:
        lesion_mask: 3D binary array of the lesion.
        structure_mask: 3D binary array of the target anatomical structure.
        spacing: Physical voxel dimensions in mm (dx, dy, dz).
        check_boundary_only: If True, computes distance to the structure's surface boundary
                             (useful for measuring depth from organ capsule/parenchymal surface).

    Returns:
        Minimum physical distance in millimeters (0.0 mm if structures overlap).
    """
    if lesion_mask.shape != structure_mask.shape:
        raise ValueError(
            f"Shape mismatch: lesion {lesion_mask.shape} vs structure {structure_mask.shape}"
        )

    lesion_fg = np.argwhere(lesion_mask > 0)
    if len(lesion_fg) == 0:
        return float("inf")

    if check_boundary_only:
        # Extract outer surface boundary of structure via binary erosion
        eroded = ndimage.binary_erosion(structure_mask > 0)
        target_voxels = (structure_mask > 0) & (~eroded)
    else:
        # Direct overlap check: if lesion intersects structure, distance is 0.0 mm
        if np.any((lesion_mask > 0) & (structure_mask > 0)):
            return 0.0
        target_voxels = structure_mask > 0

    structure_fg = np.argwhere(target_voxels)
    if len(structure_fg) == 0:
        return float("inf")

    spacing_arr = np.array(spacing[:3], dtype=np.float64)
    lesion_pts_mm = lesion_fg * spacing_arr
    structure_pts_mm = structure_fg * spacing_arr

    # Build k-d tree on structure points for sub-second nearest-neighbor query
    tree = cKDTree(structure_pts_mm)
    distances, _ = tree.query(lesion_pts_mm)
    return round(float(np.min(distances)), 3)


def calculate_comprehensive_lesion_metrics(
    lesion_mask_path: str | Path,
    structures_dir: str | Path,
    host_organ: str = "kidney_left",
    vessel_organs: list[str] | None = None,
) -> dict[str, Any]:
    """
    Computes a complete set of physical spatial metrics for a lesion NIfTI file,
    including volumetric, bounding, centroid, and multi-structure clearance distances.

    Only calculates distances for anatomical structures that genuinely exist on disk;
    unsegmented structures are explicitly documented as 'unavailable'.

    Args:
        lesion_mask_path: Path to the lesion segmentation mask (.nii / .nii.gz).
        structures_dir: Directory containing anatomical segmentation masks.
        host_organ: Name of host organ (e.g. 'kidney_left' or 'kidney_right').
        vessel_organs: List of vessel structure names to evaluate.

    Returns:
        Comprehensive dictionary of computational spatial measurements.
    """
    lesion_p = Path(lesion_mask_path)
    if not lesion_p.exists():
        raise FileNotFoundError(f"Lesion mask not found: {lesion_p}")

    struct_dir = Path(structures_dir)
    lesion_img = nib.load(str(lesion_p))
    lesion_data = lesion_img.get_fdata() > 0
    spacing = tuple(float(s) for s in lesion_img.header.get_zooms()[:3])
    affine = lesion_img.affine

    # 1. Volume
    vol_metrics = calculate_lesion_volume(lesion_data, spacing)

    # 2. Bounding dimensions
    bbox_metrics = calculate_lesion_bounding_box(lesion_data, spacing)

    # 3. Centroid
    centroid_metrics = calculate_lesion_centroid(lesion_data, spacing, affine)

    # 4. Spatial distances to critical landmarks
    if vessel_organs is None:
        vessel_organs = [
            "aorta",
            "inferior_vena_cava",
            "renal_artery",
            "renal_vein",
            "renal_pelvis",
            "ureter",
        ]

    distances: dict[str, Any] = {}

    # Distance to host organ boundary (e.g. depth from renal capsule)
    host_mask_path = struct_dir / f"{host_organ}.nii.gz"
    if host_mask_path.exists():
        host_img = nib.load(str(host_mask_path))
        host_data = host_img.get_fdata() > 0
        dist_to_surface = calculate_minimum_distance_to_structure(
            lesion_data, host_data, spacing, check_boundary_only=True
        )
        is_inside_host = bool(np.all((lesion_data > 0) <= (host_data > 0)))
        distances[f"{host_organ}_surface"] = {
            "status": "available",
            "minimum_distance_mm": dist_to_surface,
            "is_within_organ_parenchyma": is_inside_host,
            "description": f"Computational minimum distance to {host_organ} outer parenchymal boundary",
        }
    else:
        distances[f"{host_organ}_surface"] = {
            "status": "unavailable",
            "minimum_distance_mm": None,
            "description": f"Host organ mask '{host_organ}.nii.gz' not found on disk",
        }

    # Distances to vascular and collecting structures
    for st_name in vessel_organs:
        # Check potential filenames
        candidates = [
            struct_dir / f"{st_name}.nii.gz",
            struct_dir / f"{st_name}_{host_organ.split('_')[-1]}.nii.gz",
        ]
        found_path = None
        for c in candidates:
            if c.exists():
                found_path = c
                break

        if found_path is not None:
            st_img = nib.load(str(found_path))
            st_data = st_img.get_fdata() > 0
            if np.sum(st_data) > 0:
                min_dist = calculate_minimum_distance_to_structure(
                    lesion_data, st_data, spacing, check_boundary_only=False
                )
                distances[st_name] = {
                    "status": "available",
                    "minimum_distance_mm": min_dist,
                    "source_mask": found_path.name,
                    "description": f"Model-derived minimum Euclidean distance to {st_name}",
                }
            else:
                distances[st_name] = {
                    "status": "unavailable",
                    "minimum_distance_mm": None,
                    "description": f"Mask '{found_path.name}' is empty (0 foreground voxels)",
                }
        else:
            distances[st_name] = {
                "status": "unavailable",
                "minimum_distance_mm": None,
                "description": f"Anatomical mask for '{st_name}' not available in segmentation output",
            }

    return {
        "lesion_id": lesion_p.stem.replace(".nii", ""),
        "mask_path": str(lesion_p),
        "voxel_spacing_mm": list(spacing),
        "volume": vol_metrics,
        "bounding_box": bbox_metrics,
        "centroid": centroid_metrics,
        "computational_distances": distances,
        "safety_disclaimer": (
            "All spatial metrics are computational estimates derived from CT segmentation masks. "
            "They do not constitute clinically verified surgical margins or operative recommendations."
        ),
    }
