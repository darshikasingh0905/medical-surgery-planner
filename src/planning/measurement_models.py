"""
src/planning/measurement_models.py

Data models and schemas for Preoperative Measurements & Surgical Geometry.

Represents quantitative physical Euclidean distances between:
1. User-defined points (point-to-point / user lines)
2. Computational planning targets (target-to-target)
3. Targets and anatomical structures (target-to-structure)
4. Anatomical structures (structure-to-structure)

CLINICAL GOVERNANCE & SAFETY NOTICE:
All values represent computational geometric measurements derived from CT voxel coordinates
and segmented masks. They do NOT constitute autonomous surgical plans, clinical treatment decisions,
safe surgical margins, or recommended resection trajectories.
"""

from enum import Enum
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field, field_validator


class MeasurementType(str, Enum):
    POINT_TO_POINT = "point_to_point"
    TARGET_TO_TARGET = "target_to_target"
    TARGET_TO_STRUCTURE = "target_to_structure"
    STRUCTURE_TO_STRUCTURE = "structure_to_structure"
    USER_LINE = "user_line"


class MeasurementSource(str, Enum):
    COMPUTATIONAL = "computational"
    USER = "user"


class Measurement(BaseModel):
    """
    Unified representation of a 3D preoperative geometric measurement.
    """
    measurement_id: str = Field(..., description="Unique identifier (e.g. meas_1a2b3c4d)")
    case_id: str = Field(..., description="Associated case UUID")
    measurement_type: MeasurementType = Field(..., description="Type of measurement")
    label: str = Field(..., description="Human-readable label for the measurement")
    source: MeasurementSource = Field(..., description="Origin: 'computational' or 'user'")
    
    # Associated target / structure identifiers if applicable
    source_target_id: str | None = Field(default=None, description="Source planning target ID")
    target_target_id: str | None = Field(default=None, description="Target planning target ID")
    source_structure_id: str | None = Field(default=None, description="Source anatomical structure ID")
    target_structure_id: str | None = Field(default=None, description="Target anatomical structure ID")

    # Spatial coordinates
    start_voxel: list[int] | None = Field(default=None, description="Starting voxel index [x, y, z]")
    end_voxel: list[int] | None = Field(default=None, description="Ending voxel index [x, y, z]")
    start_physical: list[float] | None = Field(default=None, description="Starting physical mm [x, y, z]")
    end_physical: list[float] | None = Field(default=None, description="Ending physical mm [x, y, z]")

    # Calculated physical distance metrics
    distance_mm: float = Field(..., description="Physical Euclidean distance in millimeters")
    distance_cm: float = Field(..., description="Physical Euclidean distance in centimeters")
    overlap: bool | None = Field(default=None, description="True if structure/target masks spatially intersect")
    
    notes: str | None = Field(default=None, description="User or procedural planning notes")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp"
    )
    safety_disclaimer: str = Field(
        default=(
            "Geometric measurement only. This value represents physical distance in CT space and "
            "does not constitute a clinical surgical margin, recommended clearance, or operative decision."
        ),
        description="Mandatory medical governance disclaimer"
    )

    @field_validator("start_voxel", "end_voxel")
    @classmethod
    def validate_voxel(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            if len(v) != 3:
                raise ValueError("Voxel coordinates must have exactly 3 components [x, y, z]")
            return [int(round(c)) for c in v]
        return None

    @field_validator("start_physical", "end_physical")
    @classmethod
    def validate_physical(cls, v: list[float] | None) -> list[float] | None:
        if v is not None:
            if len(v) != 3:
                raise ValueError("Physical coordinates must have exactly 3 components [x, y, z]")
            return [round(float(c), 3) for c in v]
        return None


class PointToPointRequest(BaseModel):
    """Request payload for creating a point-to-point measurement on CT slices."""
    start_voxel: list[int] = Field(..., description="Start voxel coordinates [x, y, z]")
    end_voxel: list[int] = Field(..., description="End voxel coordinates [x, y, z]")
    label: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("start_voxel", "end_voxel")
    @classmethod
    def validate_coord(cls, v: list[int]) -> list[int]:
        if len(v) != 3:
            raise ValueError("Voxel coordinate must contain exactly 3 integers [x, y, z]")
        return [int(c) for c in v]


class TargetToTargetRequest(BaseModel):
    """Request payload for measuring distance between two existing planning targets."""
    source_target_id: str = Field(..., description="Source target ID (e.g. model_cyst_left)")
    target_target_id: str = Field(..., description="Destination target ID (e.g. ann_1a2b3c4d)")
    label: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class TargetToStructureRequest(BaseModel):
    """Request payload for measuring distance between a planning target and an anatomical structure."""
    target_id: str = Field(..., description="Planning target ID")
    structure_id: str = Field(..., description="Registered anatomical structure ID (e.g. aorta, kidney_left)")
    label: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class StructureToStructureRequest(BaseModel):
    """Request payload for measuring distance between two registered anatomical structures."""
    source_structure_id: str = Field(..., description="Source anatomical structure ID")
    target_structure_id: str = Field(..., description="Destination anatomical structure ID")
    label: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class MeasurementsResponse(BaseModel):
    """Response envelope for listing planning measurements."""
    case_id: str
    total_measurements: int
    measurements: list[Measurement]
    safety_disclaimer: str = (
        "All measurements are computational geometric distances derived from CT coordinate space. "
        "They do not constitute clinically verified surgical margins, recommended clearances, or operative decisions."
    )
