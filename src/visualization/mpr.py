"""
src/visualization/mpr.py

Multi-Planar Reconstruction (MPR) Engine for Preoperative Planning.
Provides orthogonal slicing (Axial, Coronal, Sagittal) of 3D CT volumes,
radiological orientation alignment, window/level intensity mapping,
coordinate transformations between voxel, physical, world, and display coordinate spaces,
and synchronized crosshair calculation.

CLINICAL GOVERNANCE NOTICE:
This module provides computational visualization for educational and research use.
It is NOT a diagnostic medical device or clinical navigation system.
"""

from pathlib import Path
from typing import Any
import io
import nibabel as nib
import numpy as np
from PIL import Image

from src.preprocessing.windowing import apply_window

# Canonical window/level presets
WINDOW_PRESETS: dict[str, dict[str, float | str]] = {
    "soft_tissue": {"name": "Soft Tissue", "ww": 400.0, "wl": 40.0},
    "bone": {"name": "Bone", "ww": 2000.0, "wl": 500.0},
    "lung": {"name": "Lung", "ww": 1500.0, "wl": -600.0},
    "kidney": {"name": "Kidney Parenchyma", "ww": 350.0, "wl": 50.0},
}


def clamp_coordinates(
    coord: tuple[float | int, float | int, float | int] | list[float | int] | np.ndarray,
    shape: tuple[int, int, int],
) -> list[int]:
    """
    Safely clamps integer voxel coordinates within volume boundaries [0, dim - 1].
    """
    x = int(np.clip(int(round(coord[0])), 0, shape[0] - 1))
    y = int(np.clip(int(round(coord[1])), 0, shape[1] - 1))
    z = int(np.clip(int(round(coord[2])), 0, shape[2] - 1))
    return [x, y, z]


def voxel_to_world(affine: np.ndarray, voxel_coord: tuple | list | np.ndarray) -> list[float]:
    """
    Transforms voxel coordinate [vx, vy, vz] to NIfTI scanner world coordinates [wx, wy, wz] mm
    using the 4x4 affine matrix: [wx, wy, wz, 1]^T = Affine @ [vx, vy, vz, 1]^T.
    """
    v_homo = np.array([voxel_coord[0], voxel_coord[1], voxel_coord[2], 1.0], dtype=np.float64)
    w_homo = affine @ v_homo
    return [round(float(w_homo[0]), 3), round(float(w_homo[1]), 3), round(float(w_homo[2]), 3)]


def world_to_voxel(affine: np.ndarray, world_coord: tuple | list | np.ndarray) -> list[int]:
    """
    Transforms NIfTI scanner world coordinates [wx, wy, wz] mm to integer voxel indices
    using the inverse affine matrix: Voxel = round(Affine^(-1) @ World).
    """
    inv_affine = np.linalg.inv(affine)
    w_homo = np.array([world_coord[0], world_coord[1], world_coord[2], 1.0], dtype=np.float64)
    v_homo = inv_affine @ w_homo
    return [int(round(v_homo[0])), int(round(v_homo[1])), int(round(v_homo[2]))]


def voxel_to_physical(
    spacing: tuple[float, float, float] | list[float] | np.ndarray,
    voxel_coord: tuple | list | np.ndarray,
) -> list[float]:
    """
    Transforms voxel coordinates to origin-relative physical millimeter coordinates:
    p = [x * sx, y * sy, z * sz].
    Matches the Marching Cubes mesh reconstruction space.
    """
    return [
        round(float(voxel_coord[0] * spacing[0]), 3),
        round(float(voxel_coord[1] * spacing[1]), 3),
        round(float(voxel_coord[2] * spacing[2]), 3),
    ]


def physical_to_voxel(
    spacing: tuple[float, float, float] | list[float] | np.ndarray,
    physical_coord: tuple | list | np.ndarray,
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


def get_plane_dimensions(shape: tuple[int, int, int], plane: str) -> dict[str, int]:
    """
    Returns plane dimensions and total slice count for a given volume shape (Nx, Ny, Nz).
    Plane orientations:
    - axial: slices along Z (dim 2). Display shape = (Ny, Nx) -> height: Ny, width: Nx
    - coronal: slices along Y (dim 1). Display shape = (Nz, Nx) -> height: Nz, width: Nx
    - sagittal: slices along X (dim 0). Display shape = (Nz, Ny) -> height: Nz, width: Ny
    """
    plane_lower = plane.lower()
    nx, ny, nz = shape

    if plane_lower == "axial":
        return {"total_slices": nz, "height": ny, "width": nx, "slice_axis": 2}
    elif plane_lower == "coronal":
        return {"total_slices": ny, "height": nz, "width": nx, "slice_axis": 1}
    elif plane_lower == "sagittal":
        return {"total_slices": nx, "height": nz, "width": ny, "slice_axis": 0}
    else:
        raise ValueError(f"Invalid plane: '{plane}'. Supported: 'axial', 'coronal', 'sagittal'")


def get_axial_slice(volume: np.ndarray, index: int) -> np.ndarray:
    """
    Extracts an axial 2D slice from 3D volume at Z-index.
    Oriented for standard radiological display:
    - Rows: Anterior (top) to Posterior (bottom)
    - Columns: Patient Right (left) to Patient Left (right)
    Output shape: (Ny, Nx).
    """
    nz = volume.shape[2]
    clamped_z = int(np.clip(index, 0, nz - 1))
    # volume is (X, Y, Z).
    # X: Left (0) to Right (Nx-1). Y: Posterior (0) to Anterior (Ny-1).
    # To have row 0 = Anterior and col 0 = Patient Right:
    return volume[::-1, ::-1, clamped_z].T


def get_coronal_slice(volume: np.ndarray, index: int) -> np.ndarray:
    """
    Extracts a coronal 2D slice from 3D volume at Y-index.
    Oriented for standard radiological display:
    - Rows: Superior (top) to Inferior (bottom)
    - Columns: Patient Right (left) to Patient Left (right)
    Output shape: (Nz, Nx).
    """
    ny = volume.shape[1]
    clamped_y = int(np.clip(index, 0, ny - 1))
    # volume is (X, Y, Z).
    # Fixing y gives (X, Z).
    # To have row 0 = Superior (Z max) and col 0 = Patient Right (X max):
    return volume[::-1, clamped_y, ::-1].T


def get_sagittal_slice(volume: np.ndarray, index: int) -> np.ndarray:
    """
    Extracts a sagittal 2D slice from 3D volume at X-index.
    Oriented for standard radiological display:
    - Rows: Superior (top) to Inferior (bottom)
    - Columns: Anterior (left) to Posterior (right)
    Output shape: (Nz, Ny).
    """
    nx = volume.shape[0]
    clamped_x = int(np.clip(index, 0, nx - 1))
    # volume is (X, Y, Z).
    # Fixing x gives (Y, Z).
    # To have row 0 = Superior (Z max) and col 0 = Anterior (Y max):
    return volume[clamped_x, ::-1, ::-1].T


def extract_plane_slice(volume: np.ndarray, plane: str, index: int) -> np.ndarray:
    """
    Extracts a 2D slice along the requested orthogonal anatomical plane.
    """
    plane_lower = plane.lower()
    if plane_lower == "axial":
        return get_axial_slice(volume, index)
    elif plane_lower == "coronal":
        return get_coronal_slice(volume, index)
    elif plane_lower == "sagittal":
        return get_sagittal_slice(volume, index)
    else:
        raise ValueError(f"Invalid plane: '{plane}'. Supported: 'axial', 'coronal', 'sagittal'")


def apply_window_to_slice(
    slice_data: np.ndarray,
    window_width: float = 400.0,
    window_level: float = 40.0,
) -> np.ndarray:
    """
    Applies Hounsfield Unit Window Width (WW) and Window Level (WL) and
    linearly maps intensities to uint8 [0, 255].
    """
    ww = max(float(window_width), 1.0)
    wl = float(window_level)
    lower = wl - (ww / 2.0)
    upper = wl + (ww / 2.0)

    clipped = np.clip(slice_data, lower, upper)
    norm = ((clipped - lower) / (upper - lower) * 255.0).astype(np.uint8)
    return norm


def encode_slice_to_png(
    slice_u8: np.ndarray,
    mask_u8: np.ndarray | None = None,
) -> bytes:
    """
    Encodes a 2D uint8 slice into PNG byte stream.
    If mask_u8 is provided and contains foreground pixels, blends a cyan overlay
    (RGB [0, 229, 255]) to visually highlight the genuine lesion.
    """
    if mask_u8 is not None and np.any(mask_u8 > 0):
        # Convert grayscale to RGB
        rgb = np.stack([slice_u8, slice_u8, slice_u8], axis=-1)
        fg_mask = mask_u8 > 0

        # Blend cyan overlay: 60% CT + 40% cyan [0, 229, 255]
        overlay_color = np.array([0, 229, 255], dtype=np.float32)
        base_color = rgb[fg_mask].astype(np.float32)
        blended = (0.55 * base_color + 0.45 * overlay_color).astype(np.uint8)
        rgb[fg_mask] = blended

        img = Image.fromarray(rgb, mode="RGB")
    else:
        img = Image.fromarray(slice_u8, mode="L")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def voxel_to_display_crosshair(
    voxel_coord: tuple[int, int, int] | list[int] | np.ndarray,
    shape: tuple[int, int, int],
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
    nx, ny, nz = shape
    x, y, z = clamp_coordinates(voxel_coord, shape)

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
    current_voxel: tuple[int, int, int] | list[int],
    shape: tuple[int, int, int],
) -> list[int]:
    """
    Transforms user click at 2D display position (col, row) on a specific plane
    back to 3D voxel coordinates [x, y, z], preserving the fixed axis value.
    """
    nx, ny, nz = shape
    x, y, z = clamp_coordinates(current_voxel, shape)
    plane_lower = plane.lower()

    if plane_lower == "axial":
        # Clicked in axial plane: updates x and y, z remains current axial slice
        new_x = (nx - 1) - int(col)
        new_y = (ny - 1) - int(row)
        return clamp_coordinates([new_x, new_y, z], shape)
    elif plane_lower == "coronal":
        # Clicked in coronal plane: updates x and z, y remains current coronal slice
        new_x = (nx - 1) - int(col)
        new_z = (nz - 1) - int(row)
        return clamp_coordinates([new_x, y, new_z], shape)
    elif plane_lower == "sagittal":
        # Clicked in sagittal plane: updates y and z, x remains current sagittal slice
        new_y = (ny - 1) - int(col)
        new_z = (nz - 1) - int(row)
        return clamp_coordinates([x, new_y, new_z], shape)
    else:
        raise ValueError(f"Invalid plane: '{plane}'")


# =====================================================================
# In-Memory Cached Volume Manager
# =====================================================================

class MPRVolumeManager:
    """
    Manages loading and memory caching of CT volumes and lesion masks
    for ultra-fast sub-millisecond MPR slice extraction.
    """

    def __init__(self):
        self._cache: dict[str, dict[str, Any]] = {}

    def get_case_ct_path(self, case_id: str) -> Path | None:
        """Resolves path to original CT NIfTI file for a given case."""
        case_dir = Path("outputs/cases") / case_id
        if not case_dir.is_dir():
            return None

        input_dir = case_dir / "input"
        if input_dir.is_dir():
            files = list(input_dir.glob("*.nii*"))
            if files:
                return files[0]

        # Fallback to datasets/raw/ct
        fallback = Path("datasets/raw/ct/ct_15mm_defaced.nii")
        if fallback.is_file():
            return fallback

        return None

    def get_case_lesion_path(self, case_id: str, lesion_id: str = "cyst_left") -> Path | None:
        """Resolves path to lesion segmentation mask."""
        case_dir = Path("outputs/cases") / case_id
        cand = case_dir / "lesions" / f"{lesion_id}.nii.gz"
        if cand.is_file():
            return cand
        cand_alt = case_dir / "lesions" / f"{lesion_id}.nii"
        if cand_alt.is_file():
            return cand_alt
        return None

    def load_case_volume(self, case_id: str) -> dict[str, Any]:
        """
        Retrieves cached CT volume and metadata, or loads from disk.
        """
        if case_id in self._cache:
            return self._cache[case_id]

        ct_path = self.get_case_ct_path(case_id)
        if ct_path is None or not ct_path.is_file():
            raise FileNotFoundError(f"CT volume not found for case '{case_id}'")

        img = nib.load(str(ct_path))
        data = np.asarray(img.dataobj, dtype=np.float32)
        spacing = tuple(float(s) for s in img.header.get_zooms()[:3])
        affine = img.affine
        shape = tuple(int(s) for s in data.shape)

        # Attempt to load primary lesion mask if available
        lesion_path = self.get_case_lesion_path(case_id)
        lesion_data = None
        if lesion_path is not None:
            try:
                l_img = nib.load(str(lesion_path))
                lesion_data = np.asarray(l_img.dataobj > 0, dtype=np.uint8)
            except Exception:
                lesion_data = None

        cached_entry = {
            "volume": data,
            "shape": shape,
            "voxel_spacing": spacing,
            "affine": affine,
            "orientation": list(nib.aff2axcodes(affine)),
            "intensity_min": float(np.min(data)),
            "intensity_max": float(np.max(data)),
            "ct_path": str(ct_path),
            "lesion_mask": lesion_data,
        }

        self._cache[case_id] = cached_entry
        return cached_entry

    def get_metadata(self, case_id: str) -> dict[str, Any]:
        """Returns metadata required by the frontend MPR viewer."""
        entry = self.load_case_volume(case_id)
        shape = entry["shape"]
        spacing = entry["voxel_spacing"]
        affine = entry["affine"]

        # Calculate default initial cursor (volume center)
        default_voxel = [shape[0] // 2, shape[1] // 2, shape[2] // 2]
        default_world = voxel_to_world(affine, default_voxel)
        default_phys = voxel_to_physical(spacing, default_voxel)

        return {
            "case_id": case_id,
            "shape": list(shape),
            "voxel_spacing_mm": list(spacing),
            "orientation": entry["orientation"],
            "intensity_range": [entry["intensity_min"], entry["intensity_max"]],
            "affine": entry["affine"].tolist(),
            "planes": {
                "axial": get_plane_dimensions(shape, "axial"),
                "coronal": get_plane_dimensions(shape, "coronal"),
                "sagittal": get_plane_dimensions(shape, "sagittal"),
            },
            "presets": WINDOW_PRESETS,
            "default_cursor": {
                "voxel": default_voxel,
                "world_mm": default_world,
                "physical_mm": default_phys,
            },
        }

    def get_slice_bytes(
        self,
        case_id: str,
        plane: str,
        index: int,
        window_width: float = 400.0,
        window_level: float = 40.0,
        overlay_lesion: bool = True,
    ) -> bytes:
        """
        Extracts, windows, and encodes a 2D slice as a PNG byte buffer.
        """
        entry = self.load_case_volume(case_id)
        volume = entry["volume"]
        slice_data = extract_plane_slice(volume, plane, index)
        slice_u8 = apply_window_to_slice(slice_data, window_width, window_level)

        mask_u8 = None
        if overlay_lesion and entry["lesion_mask"] is not None:
            mask_u8 = extract_plane_slice(entry["lesion_mask"], plane, index)

        return encode_slice_to_png(slice_u8, mask_u8)


# Singleton instance
mpr_manager = MPRVolumeManager()
