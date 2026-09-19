"""
src/planning/measurement_service.py

Preoperative Measurement & Surgical Geometry Service.

Orchestrates quantitative physical Euclidean distance calculations between:
  1. User-defined points (point-to-point)
  2. Computational planning targets (target-to-target)
  3. Planning targets and registered anatomical structures (target-to-structure)
  4. Registered anatomical structure pairs (structure-to-structure)

Distances are always calculated in physical millimeters using anisotropic voxel
spacing — never raw voxel-index units.

Persistence: atomic JSON to outputs/cases/<case_id>/planning/measurements.json
Isolation:   Completely separate from annotations.json (see annotations.py).

CLINICAL GOVERNANCE & SAFETY NOTICE:
All computed values represent geometric distances in CT coordinate space derived
from segmented masks or user-selected voxel coordinates.  They do NOT constitute:
  - Autonomous surgical recommendations
  - Clinically verified margins or clearances
  - Operative treatment decisions or resection trajectories
Use standardised terminology: "computational distance", "model-predicted lesion",
"planning annotation".  Never use: "safe margin", "recommended clearance",
"optimal route".
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from src.api.utils.case_manager import case_exists, get_case_path
from src.measurements.spatial_relationships import calculate_mask_pair_spatial_relationship
from src.planning.measurement_models import (
    Measurement,
    MeasurementSource,
    MeasurementType,
    MeasurementsResponse,
    PointToPointRequest,
    StructureToStructureRequest,
    TargetToStructureRequest,
    TargetToTargetRequest,
)
from src.visualization.mpr import mpr_manager, physical_to_voxel, voxel_to_physical


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _euclidean_mm(p1: list[float], p2: list[float]) -> float:
    """Return the physical Euclidean distance (mm) between two 3-D points."""
    return round(math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2))), 3)


def _new_measurement_id() -> str:
    return f"meas_{uuid.uuid4().hex[:8]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# MeasurementService
# ---------------------------------------------------------------------------

class MeasurementService:
    """
    Manages creation, retrieval, and deletion of preoperative geometric measurements.

    Thread-safety: atomic write via .tmp rename safe for single-worker ASGI server.
    """

    # -- Persistence helpers ------------------------------------------------

    def _get_planning_dir(self, case_id: str) -> Path:
        planning_dir = get_case_path(case_id) / "planning"
        planning_dir.mkdir(parents=True, exist_ok=True)
        return planning_dir

    def _get_measurements_file(self, case_id: str) -> Path:
        return self._get_planning_dir(case_id) / "measurements.json"

    def _load_raw(self, case_id: str) -> dict[str, Any]:
        path = self._get_measurements_file(case_id)
        if not path.is_file():
            return {"case_id": case_id, "measurements": []}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict) or "measurements" not in data:
                    return {"case_id": case_id, "measurements": []}
                return data
        except Exception:
            return {"case_id": case_id, "measurements": []}

    def _save_raw(self, case_id: str, data: dict[str, Any]) -> None:
        path = self._get_measurements_file(case_id)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(path)

    # -- Volume metadata ----------------------------------------------------

    def _get_volume_meta(
        self, case_id: str
    ) -> tuple[tuple[int, int, int], tuple[float, float, float]]:
        try:
            meta = mpr_manager.get_metadata(case_id)
            shape = tuple(int(s) for s in meta["shape"])
            spacing = tuple(float(s) for s in meta["voxel_spacing_mm"])
            return shape, spacing
        except Exception:
            return (512, 512, 512), (1.5, 1.5, 1.5)

    def _validate_voxel_bounds(self, case_id: str, voxel: list[int]) -> None:
        shape, _ = self._get_volume_meta(case_id)
        x, y, z = voxel
        nx, ny, nz = shape
        if not (0 <= x < nx and 0 <= y < ny and 0 <= z < nz):
            raise ValueError(
                f"Voxel coordinate [{x}, {y}, {z}] is out of bounds "
                f"for volume shape {list(shape)}."
            )

    # -- Resolve planning target physical coordinate ------------------------

    def _resolve_target_physical(self, case_id: str, target_id: str) -> list[float]:
        """
        Returns physical coordinate (mm) for a planning target.
        Searches model lesion targets first, then user annotations.
        """
        from src.planning.annotations import annotation_service

        targets = annotation_service.get_all_planning_targets(case_id)
        for t in targets:
            if t.target_id == target_id:
                if t.physical_coordinate and len(t.physical_coordinate) == 3:
                    return [float(c) for c in t.physical_coordinate]
                if t.voxel_coordinate:
                    _, spacing = self._get_volume_meta(case_id)
                    return voxel_to_physical(spacing, t.voxel_coordinate)
        raise FileNotFoundError(
            f"Planning target '{target_id}' not found in case '{case_id}'."
        )

    # -- Resolve anatomical structure mask path -----------------------------

    def _resolve_structure_mask(self, case_id: str, structure_id: str) -> Path:
        """Resolves the NIfTI mask path for a registered anatomical structure."""
        case_dir = get_case_path(case_id)
        seg_dir = case_dir / "segmentation"

        for suffix in (".nii.gz", ".nii"):
            candidate = seg_dir / f"{structure_id}{suffix}"
            if candidate.is_file():
                return candidate

        raise FileNotFoundError(
            f"Segmentation mask for structure '{structure_id}' not found in case "
            f"'{case_id}'. Expected at: {seg_dir / structure_id}.nii.gz"
        )

    # -- Point distance calculation -----------------------------------------

    def calculate_physical_point_distance(
        self, p1: list[float], p2: list[float]
    ) -> float:
        """
        Compute physical Euclidean distance (mm) between two physical coordinate
        points.  Input coordinates must be in physical mm space
        (origin-relative: voxel_index * spacing).
        """
        return _euclidean_mm(p1, p2)

    # -- CRUD ---------------------------------------------------------------

    def list_measurements(self, case_id: str) -> list[Measurement]:
        """Returns all measurements for a case, ordered by creation time."""
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")
        raw = self._load_raw(case_id)
        result: list[Measurement] = []
        for item in raw.get("measurements", []):
            try:
                result.append(Measurement(**item))
            except Exception:
                continue
        return result

    def get_measurement(self, case_id: str, measurement_id: str) -> Measurement | None:
        """Retrieve a single measurement by ID."""
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")
        for m in self.list_measurements(case_id):
            if m.measurement_id == measurement_id:
                return m
        return None

    def delete_measurement(self, case_id: str, measurement_id: str) -> bool:
        """Delete a measurement by ID.  Returns True if found and deleted."""
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")
        raw = self._load_raw(case_id)
        before = len(raw["measurements"])
        raw["measurements"] = [
            m for m in raw["measurements"]
            if m.get("measurement_id") != measurement_id
        ]
        if len(raw["measurements"]) < before:
            self._save_raw(case_id, raw)
            return True
        return False

    def _persist_measurement(self, case_id: str, m: Measurement) -> Measurement:
        """Append a measurement to the case file atomically."""
        raw = self._load_raw(case_id)
        raw["measurements"].append(m.model_dump())
        self._save_raw(case_id, raw)
        return m

    # -- Measurement creation -----------------------------------------------

    def create_point_to_point_measurement(
        self, case_id: str, req: PointToPointRequest
    ) -> Measurement:
        """
        Create a measurement between two user-selected voxel coordinates.
        Physical distance = Euclidean norm of (end_voxel - start_voxel) * spacing.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        self._validate_voxel_bounds(case_id, req.start_voxel)
        self._validate_voxel_bounds(case_id, req.end_voxel)

        _, spacing = self._get_volume_meta(case_id)
        start_phys = voxel_to_physical(spacing, req.start_voxel)
        end_phys = voxel_to_physical(spacing, req.end_voxel)
        dist_mm = self.calculate_physical_point_distance(start_phys, end_phys)

        existing = self.list_measurements(case_id)
        label = req.label or f"Point-to-Point Measurement {len(existing) + 1}"

        m = Measurement(
            measurement_id=_new_measurement_id(),
            case_id=case_id,
            measurement_type=MeasurementType.POINT_TO_POINT,
            label=label,
            source=MeasurementSource.USER,
            start_voxel=req.start_voxel,
            end_voxel=req.end_voxel,
            start_physical=start_phys,
            end_physical=end_phys,
            distance_mm=dist_mm,
            distance_cm=round(dist_mm / 10.0, 4),
            overlap=None,
            notes=req.notes,
            created_at=_now_iso(),
        )
        return self._persist_measurement(case_id, m)

    def create_target_to_target_measurement(
        self, case_id: str, req: TargetToTargetRequest
    ) -> Measurement:
        """
        Compute distance between two existing planning targets.
        Distance calculated in physical mm space via target centroid coordinates.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        src_phys = self._resolve_target_physical(case_id, req.source_target_id)
        tgt_phys = self._resolve_target_physical(case_id, req.target_target_id)

        _, spacing = self._get_volume_meta(case_id)
        src_vox = physical_to_voxel(spacing, src_phys)
        tgt_vox = physical_to_voxel(spacing, tgt_phys)

        dist_mm = self.calculate_physical_point_distance(src_phys, tgt_phys)
        label = req.label or (
            f"Target to Target: {req.source_target_id} to {req.target_target_id}"
        )

        m = Measurement(
            measurement_id=_new_measurement_id(),
            case_id=case_id,
            measurement_type=MeasurementType.TARGET_TO_TARGET,
            label=label,
            source=MeasurementSource.COMPUTATIONAL,
            source_target_id=req.source_target_id,
            target_target_id=req.target_target_id,
            start_voxel=src_vox,
            end_voxel=tgt_vox,
            start_physical=src_phys,
            end_physical=tgt_phys,
            distance_mm=dist_mm,
            distance_cm=round(dist_mm / 10.0, 4),
            overlap=None,
            notes=req.notes,
            created_at=_now_iso(),
        )
        return self._persist_measurement(case_id, m)

    def create_target_to_structure_measurement(
        self, case_id: str, req: TargetToStructureRequest
    ) -> Measurement:
        """
        Compute distance from a planning target centroid to the nearest voxel of
        an anatomical structure mask using cKDTree in physical mm space.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        target_phys = self._resolve_target_physical(case_id, req.target_id)
        mask_path = self._resolve_structure_mask(case_id, req.structure_id)

        img = nib.load(str(mask_path))
        structure_data = (img.get_fdata() > 0).astype(np.uint8)
        spacing = tuple(float(s) for s in img.header.get_zooms()[:3])

        _, vol_spacing = self._get_volume_meta(case_id)
        target_vox = physical_to_voxel(vol_spacing, target_phys)

        shape = structure_data.shape
        cx = max(0, min(target_vox[0], shape[0] - 1))
        cy = max(0, min(target_vox[1], shape[1] - 1))
        cz = max(0, min(target_vox[2], shape[2] - 1))

        # Represent the target as a single-voxel mask to reuse cKDTree utility
        point_mask = np.zeros(shape, dtype=np.uint8)
        point_mask[cx, cy, cz] = 1

        rel = calculate_mask_pair_spatial_relationship(
            point_mask, structure_data, spacing
        )

        if not rel["available"]:
            raise ValueError(
                f"Structure '{req.structure_id}' has no foreground voxels — "
                "cannot calculate computational distance."
            )

        dist_mm = rel["distance_mm"] if rel["distance_mm"] is not None else 0.0
        overlap = rel.get("overlap", False)

        label = req.label or (
            f"Target to Structure: {req.target_id} to {req.structure_id}"
        )

        m = Measurement(
            measurement_id=_new_measurement_id(),
            case_id=case_id,
            measurement_type=MeasurementType.TARGET_TO_STRUCTURE,
            label=label,
            source=MeasurementSource.COMPUTATIONAL,
            source_target_id=req.target_id,
            target_structure_id=req.structure_id,
            start_voxel=[cx, cy, cz],
            end_voxel=None,
            start_physical=target_phys,
            end_physical=None,
            distance_mm=dist_mm,
            distance_cm=round(dist_mm / 10.0, 4),
            overlap=overlap,
            notes=req.notes,
            created_at=_now_iso(),
        )
        return self._persist_measurement(case_id, m)

    def create_structure_to_structure_measurement(
        self, case_id: str, req: StructureToStructureRequest
    ) -> Measurement:
        """
        Compute minimum physical distance between two anatomical structure masks
        using cKDTree nearest-neighbour query in physical mm space.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        src_path = self._resolve_structure_mask(case_id, req.source_structure_id)
        tgt_path = self._resolve_structure_mask(case_id, req.target_structure_id)

        src_img = nib.load(str(src_path))
        src_data = (src_img.get_fdata() > 0).astype(np.uint8)
        spacing = tuple(float(s) for s in src_img.header.get_zooms()[:3])

        tgt_img = nib.load(str(tgt_path))
        tgt_data = (tgt_img.get_fdata() > 0).astype(np.uint8)

        if src_data.shape != tgt_data.shape:
            raise ValueError(
                f"Shape mismatch between '{req.source_structure_id}' "
                f"({src_data.shape}) and '{req.target_structure_id}' "
                f"({tgt_data.shape}). Cannot compute inter-structure distance."
            )

        rel = calculate_mask_pair_spatial_relationship(src_data, tgt_data, spacing)

        if not rel["available"]:
            raise ValueError(
                "One or both structures have no foreground voxels — "
                "cannot calculate computational distance."
            )

        dist_mm = rel["distance_mm"] if rel["distance_mm"] is not None else 0.0
        overlap = rel.get("overlap", False)

        label = req.label or (
            f"Structure to Structure: {req.source_structure_id} to "
            f"{req.target_structure_id}"
        )

        m = Measurement(
            measurement_id=_new_measurement_id(),
            case_id=case_id,
            measurement_type=MeasurementType.STRUCTURE_TO_STRUCTURE,
            label=label,
            source=MeasurementSource.COMPUTATIONAL,
            source_structure_id=req.source_structure_id,
            target_structure_id=req.target_structure_id,
            start_voxel=None,
            end_voxel=None,
            start_physical=None,
            end_physical=None,
            distance_mm=dist_mm,
            distance_cm=round(dist_mm / 10.0, 4),
            overlap=overlap,
            notes=req.notes,
            created_at=_now_iso(),
        )
        return self._persist_measurement(case_id, m)

    def build_measurements_response(self, case_id: str) -> MeasurementsResponse:
        """Return the full MeasurementsResponse envelope for a case."""
        measurements = self.list_measurements(case_id)
        return MeasurementsResponse(
            case_id=case_id,
            total_measurements=len(measurements),
            measurements=measurements,
        )


# Singleton instance consistent with annotation_service pattern
measurement_service = MeasurementService()
