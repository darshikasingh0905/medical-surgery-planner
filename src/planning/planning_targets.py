"""
src/planning/planning_targets.py

Data models and schemas for Preoperative Planning Targets and Annotations.

Provides a unified representation for:
1. Computational model-predicted findings (e.g., KiTS23 renal cyst/tumor segmentations)
2. Registered anatomical structures (e.g., kidney parenchyma, vascular trunks)
3. User-created planning reference points (custom markers created on MPR or 3D views)

CLINICAL GOVERNANCE NOTICE:
This module represents computational spatial coordinates and organizational metadata.
It does NOT constitute an autonomous surgical plan, clinical diagnostic recommendation,
or validated surgical margin.
"""

from enum import Enum
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field, field_validator


class TargetType(str, Enum):
    LESION = "lesion"
    ANATOMY = "anatomy"
    CUSTOM_POINT = "custom_point"


class TargetSource(str, Enum):
    MODEL = "model"
    USER = "user"


class PlanningTarget(BaseModel):
    """
    Unified representation of a surgical planning target or annotation.
    Can originate from automated AI segmentation ('model') or clinician input ('user').
    """
    target_id: str = Field(..., description="Unique identifier for the planning target")
    target_type: TargetType = Field(..., description="Type of target: lesion, anatomy, or custom_point")
    label: str = Field(..., description="Human-readable label for the target")
    source: TargetSource = Field(..., description="Origin of the target: 'model' or 'user'")
    voxel_coordinate: list[int] = Field(..., description="3D integer voxel coordinates [x, y, z]")
    physical_coordinate: list[float] = Field(..., description="Origin-relative physical mm coordinates [x, y, z]")
    lesion_id: str | None = Field(default=None, description="Associated lesion ID if applicable (e.g. cyst_left)")
    structure_id: str | None = Field(default=None, description="Associated anatomical structure ID if applicable")
    notes: str | None = Field(default=None, description="Clinical or planning notes")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 timestamp")
    
    # Optional metadata preserved for computational model findings
    volume_ml: float | None = Field(default=None, description="Volume in milliliters if applicable")
    dimensions_mm: list[float] | None = Field(default=None, description="Bounding box dimensions in mm [dx, dy, dz]")
    computational_interpretation: str | None = Field(default=None, description="Model provenance description")
    host_organ: str | None = Field(default=None, description="Host organ identifier if applicable")

    @field_validator("voxel_coordinate")
    @classmethod
    def validate_voxel_coord(cls, v: list[int]) -> list[int]:
        if len(v) != 3:
            raise ValueError("voxel_coordinate must have exactly 3 integers [x, y, z]")
        return [int(round(coord)) for coord in v]

    @field_validator("physical_coordinate")
    @classmethod
    def validate_physical_coord(cls, v: list[float]) -> list[float]:
        if len(v) != 3:
            raise ValueError("physical_coordinate must have exactly 3 floats [x, y, z]")
        return [round(float(coord), 3) for coord in v]


class AnnotationCreateRequest(BaseModel):
    """Request payload for creating a new user-defined planning annotation."""
    label: str = Field(default="Planning Point", min_length=1, max_length=120)
    target_type: TargetType = Field(default=TargetType.CUSTOM_POINT)
    voxel_coordinate: list[int] = Field(..., description="Integer voxel coordinates [x, y, z]")
    physical_coordinate: list[float] | None = Field(default=None, description="Optional physical mm coordinates")
    notes: str | None = Field(default=None, max_length=1000)
    structure_id: str | None = Field(default=None)
    lesion_id: str | None = Field(default=None)

    @field_validator("voxel_coordinate")
    @classmethod
    def validate_coord(cls, v: list[int]) -> list[int]:
        if len(v) != 3:
            raise ValueError("voxel_coordinate must contain exactly 3 components [x, y, z]")
        return [int(c) for c in v]


class AnnotationUpdateRequest(BaseModel):
    """Request payload for updating an existing user annotation."""
    label: str | None = Field(default=None, min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)
    voxel_coordinate: list[int] | None = Field(default=None)
    physical_coordinate: list[float] | None = Field(default=None)

    @field_validator("voxel_coordinate")
    @classmethod
    def validate_coord(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            if len(v) != 3:
                raise ValueError("voxel_coordinate must contain exactly 3 components [x, y, z]")
            return [int(c) for c in v]
        return None


class FromLesionRequest(BaseModel):
    """Optional request payload for annotating an existing lesion."""
    label: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class PlanningTargetsResponse(BaseModel):
    """Response envelope for listing planning targets."""
    case_id: str
    total_targets: int
    model_findings_count: int
    user_annotations_count: int
    targets: list[PlanningTarget]
    safety_disclaimer: str = (
        "Planning markers and computational findings are visualization and organization tools for "
        "research and educational review. They do not constitute autonomous surgical recommendations or clinical diagnoses."
    )
