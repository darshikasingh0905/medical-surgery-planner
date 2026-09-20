"""
src/geometry/coordinate_system.py

Centralized Coordinate Transformation and Spatial Registration Engine.
Unifies transformations across all coordinate spaces in the AI-Assisted Preoperative Planning System:
  1. Voxel Space [x, y, z] (3D array indices)
  2. Physical / Spacing Space [px, py, pz] mm (Origin-relative, Marching Cubes & local mesh vertices)
  3. Scanner World / RAS Space [wx, wy, wz] mm (NIfTI affine transformation)
  4. MPR Display Space (u, v) (Axial, Coronal, Sagittal radiological projection planes)
  5. Three.js Scene Space [X_3d, Y_3d, Z_3d] (Camera and visualization frame)

CLINICAL GOVERNANCE & SAFETY NOTICE:
All transformations establish computational spatial consistency only.
They do NOT constitute:
  - Clinical registration accuracy
  - Surgical navigation accuracy
  - Clinical-grade localization
  - Validated surgical positioning or guidance
This module is part of an educational and research prototype. Not validated for clinical use.
"""

from typing import Sequence
import math
import numpy as np


def clamp_coordinates(
    coord: Sequence[float | int] | np.ndarray,
    shape: tuple[int, int, int] | Sequence[int],
) -> list[int]:
    """
    Safely clamps integer voxel coordinates within volume boundaries [0, dim - 1].
    """
    x = int(np.clip(int(round(coord[0])), 0, int(shape[0]) - 1))
    y = int(np.clip(int(round(coord[1])), 0, int(shape[1]) - 1))
    z = int(np.clip(int(round(coord[2])), 0, int(shape[2]) - 1))
    return [x, y, z]


def voxel_to_world(
    affine: np.ndarray | Sequence[Sequence[float]],
    voxel_coord: Sequence[float | int] | np.ndarray,
) -> list[float]:
    """
    Transforms voxel coordinate [vx, vy, vz] to NIfTI scanner world coordinates [wx, wy, wz] mm
    using the 4x4 affine matrix:
        [wx, wy, wz, 1]^T = Affine @ [vx, vy, vz, 1]^T.
    """
    aff = np.asarray(affine, dtype=np.float64)
    v_homo = np.array([voxel_coord[0], voxel_coord[1], voxel_coord[2], 1.0], dtype=np.float64)
    w_homo = aff @ v_homo
    return [round(float(w_homo[0]), 3), round(float(w_homo[1]), 3), round(float(w_homo[2]), 3)]


def world_to_voxel(
    affine: np.ndarray | Sequence[Sequence[float]],
    world_coord: Sequence[float | int] | np.ndarray,
) -> list[int]:
    """
    Transforms NIfTI scanner world coordinates [wx, wy, wz] mm to integer voxel indices
    using the inverse affine matrix:
        Voxel = round(Affine^(-1) @ World).
    """
    aff = np.asarray(affine, dtype=np.float64)
    inv_affine = np.linalg.inv(aff)
    w_homo = np.array([world_coord[0], world_coord[1], world_coord[2], 1.0], dtype=np.float64)
    v_homo = inv_affine @ w_homo
    return [int(round(v_homo[0])), int(round(v_homo[1])), int(round(v_homo[2]))]


def voxel_to_physical(
    spacing: tuple[float, float, float] | Sequence[float] | np.ndarray,
    voxel_coord: Sequence[float | int] | np.ndarray,
) -> list[float]:
    """
    Transforms voxel coordinates to origin-relative physical millimeter coordinates:
        p = [vx * sx, vy * sy, vz * sz].
    Matches the Marching Cubes mesh reconstruction space and Three.js local mesh coordinates.
    """
    return [
        round(float(voxel_coord[0] * spacing[0]), 3),
        round(float(voxel_coord[1] * spacing[1]), 3),
        round(float(voxel_coord[2] * spacing[2]), 3),
    ]


def physical_to_voxel(
    spacing: tuple[float, float, float] | Sequence[float] | np.ndarray,
    physical_coord: Sequence[float | int] | np.ndarray,
) -> list[int]:
    """
    Transforms origin-relative physical millimeter coordinates back to integer voxel coordinates:
        v = round(p / s).
    """
    return [
        int(round(physical_coord[0] / spacing[0])),
        int(round(physical_coord[1] / spacing[1])),
        int(round(physical_coord[2] / spacing[2])),
    ]


def calculate_physical_distance(
    p1: Sequence[float | int] | np.ndarray,
    p2: Sequence[float | int] | np.ndarray,
) -> float:
    """
    Computes Euclidean distance in physical millimeters between two 3D points.
    Input coordinates must already be in physical mm units (or spacing-scaled).
    """
    return round(
        math.sqrt(
            (float(p2[0]) - float(p1[0])) ** 2
            + (float(p2[1]) - float(p1[1])) ** 2
            + (float(p2[2]) - float(p1[2])) ** 2
        ),
        3,
    )


def get_plane_dimensions(
    shape: tuple[int, int, int] | Sequence[int],
    plane: str,
) -> dict[str, int]:
    """
    Returns plane dimensions and total slice count for a given volume shape (Nx, Ny, Nz).
    Plane orientations:
    - axial: slices along Z (dim 2). Display shape = (Ny, Nx) -> height: Ny, width: Nx
    - coronal: slices along Y (dim 1). Display shape = (Nz, Nx) -> height: Nz, width: Nx
    - sagittal: slices along X (dim 0). Display shape = (Nz, Ny) -> height: Nz, width: Ny
    """
    plane_lower = plane.lower()
    nx, ny, nz = int(shape[0]), int(shape[1]), int(shape[2])

    if plane_lower == "axial":
        return {"total_slices": nz, "height": ny, "width": nx, "slice_axis": 2}
    elif plane_lower == "coronal":
        return {"total_slices": ny, "height": nz, "width": nx, "slice_axis": 1}
    elif plane_lower == "sagittal":
        return {"total_slices": nx, "height": nz, "width": ny, "slice_axis": 0}
    else:
        raise ValueError(f"Invalid plane: '{plane}'. Supported: 'axial', 'coronal', 'sagittal'")


def voxel_to_display_crosshair(
    voxel_coord: tuple[int, int, int] | Sequence[int] | np.ndarray,
    shape: tuple[int, int, int] | Sequence[int],
) -> dict[str, dict[str, int]]:
    """
    Transforms 3D voxel coordinate [x, y, z] to 2D display coordinates (col, row)
    for each of the three radiological views.
    Returns:
    {
        "axial": {"col": u, "row": v, "slice_index": z},
        "coronal": {"col": u, "row": v, "slice_index": y},
        "sagittal": {"col": u, "row": v, "slice_index": x}
    }
    """
    nx, ny, nz = int(shape[0]), int(shape[1]), int(shape[2])
    x, y, z = clamp_coordinates(voxel_coord, (nx, ny, nz))

    return {
        "axial": {
            "col": (nx - 1) - x,
            "row": (ny - 1) - y,
            "slice_index": z,
        },
        "coronal": {
            "col": (nx - 1) - x,
            "row": (nz - 1) - z,
            "slice_index": y,
        },
        "sagittal": {
            "col": (ny - 1) - y,
            "row": (nz - 1) - z,
            "slice_index": x,
        },
    }


def display_to_voxel_crosshair(
    plane: str,
    col: int,
    row: int,
    current_voxel: tuple[int, int, int] | Sequence[int],
    shape: tuple[int, int, int] | Sequence[int],
) -> list[int]:
    """
    Transforms user click at 2D display position (col, row) on a specific plane
    back to 3D voxel coordinates [x, y, z], preserving the fixed slice axis value.
    """
    nx, ny, nz = int(shape[0]), int(shape[1]), int(shape[2])
    x, y, z = clamp_coordinates(current_voxel, (nx, ny, nz))
    plane_lower = plane.lower()

    if plane_lower == "axial":
        # Clicked in axial plane: updates x and y, z remains current axial slice
        new_x = (nx - 1) - int(col)
        new_y = (ny - 1) - int(row)
        return clamp_coordinates([new_x, new_y, z], (nx, ny, nz))
    elif plane_lower == "coronal":
        # Clicked in coronal plane: updates x and z, y remains current coronal slice
        new_x = (nx - 1) - int(col)
        new_z = (nz - 1) - int(row)
        return clamp_coordinates([new_x, y, new_z], (nx, ny, nz))
    elif plane_lower == "sagittal":
        # Clicked in sagittal plane: updates y and z, x remains current sagittal slice
        new_y = (ny - 1) - int(col)
        new_z = (nz - 1) - int(row)
        return clamp_coordinates([x, new_y, new_z], (nx, ny, nz))
    else:
        raise ValueError(f"Invalid plane: '{plane}'. Supported: 'axial', 'coronal', 'sagittal'")
