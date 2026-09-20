"""
src/planning/planning_session.py

Planning Session Model & Persistence Service for Preoperative Surgical Planning.

Manages user-created planning session state (view mode, selections, cursor,
visibility, opacities, and planning notes).
State is strictly separated from clinical and computational truth.

Persists atomically to:
    outputs/cases/<case_id>/planning/planning_session.json

CLINICAL GOVERNANCE NOTICE:
Planning session state represents user interaction and review configuration for
research and educational preoperative exploration. It does NOT constitute an
autonomous surgical recommendation, validated operative plan, or clinical diagnosis.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid
from pydantic import BaseModel, Field, field_validator

from src.api.utils.case_manager import case_exists, get_case_path


class PlanningSession(BaseModel):
    """
    Lightweight state representation of a user's active planning session.
    References existing objects by ID rather than duplicating underlying datasets.
    """
    case_id: str = Field(..., description="Unique case UUID")
    session_id: str = Field(..., description="Unique session UUID")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of creation",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of last update",
    )

    # Active selections
    selected_target_id: str | None = Field(default=None, description="Currently selected planning target ID")
    selected_lesion_id: str | None = Field(default=None, description="Currently selected model finding ID")
    selected_structure_id: str | None = Field(default=None, description="Currently selected anatomical structure ID")
    selected_measurement_id: str | None = Field(default=None, description="Currently selected measurement ID")

    # Visualization & View State
    view_mode: str = Field(default="3d", description="Visualization layout: '3d', 'mpr', or 'split'")
    selected_mpr_plane: str = Field(default="axial", description="Active orthogonal plane: 'axial', 'coronal', 'sagittal'")
    voxel_cursor: list[int] = Field(default=[146, 146, 172], description="Synchronized 3D voxel coordinate [x, y, z]")

    # Layer Visibilities (ID -> bool)
    visible_structures: dict[str, bool] = Field(default_factory=dict, description="Visibility per anatomical structure")
    visible_lesions: dict[str, bool] = Field(default_factory=dict, description="Visibility per lesion/finding")
    visible_targets: dict[str, bool] = Field(default_factory=dict, description="Visibility per planning marker")

    # Opacities
    structure_opacities: dict[str, float] = Field(default_factory=dict, description="Custom opacity per structure")
    organ_opacity: float = Field(default=0.85, description="Global organ opacity [0.0 - 1.0]")
    lesion_opacity: float = Field(default=1.0, description="Global lesion opacity [0.0 - 1.0]")

    # MPR Window/Level Presets & Toggles
    mpr_window_preset: str = Field(default="soft_tissue", description="Window preset name")
    mpr_window_width: float = Field(default=400.0, description="Window Width (HU)")
    mpr_window_level: float = Field(default=40.0, description="Window Level (HU)")
    mpr_show_lesion_overlay: bool = Field(default=True, description="Whether genuine lesion mask is overlaid in 2D")
    mpr_show_crosshairs: bool = True
    mpr_show_planning_markers: bool = True

    # User Planning Notes
    planning_notes: str = Field(
        default="",
        description="Free-form user research/planning notes. Not autonomous surgical recommendations.",
    )

    @field_validator("voxel_cursor")
    @classmethod
    def validate_cursor(cls, v: list[int]) -> list[int]:
        if len(v) != 3:
            raise ValueError("voxel_cursor must have exactly 3 integers [x, y, z]")
        return [int(round(c)) for c in v]

    @field_validator("view_mode")
    @classmethod
    def validate_view(cls, v: str) -> str:
        allowed = {"3d", "mpr", "split"}
        if v.lower() not in allowed:
            raise ValueError(f"Invalid view_mode '{v}'. Allowed: {allowed}")
        return v.lower()


class PlanningSessionUpdateRequest(BaseModel):
    """
    Request payload for updating an existing planning session.
    All fields are optional to allow partial updates.
    """
    selected_target_id: str | None = None
    selected_lesion_id: str | None = None
    selected_structure_id: str | None = None
    selected_measurement_id: str | None = None
    view_mode: str | None = None
    selected_mpr_plane: str | None = None
    voxel_cursor: list[int] | None = None
    visible_structures: dict[str, bool] | None = None
    visible_lesions: dict[str, bool] | None = None
    visible_targets: dict[str, bool] | None = None
    structure_opacities: dict[str, float] | None = None
    organ_opacity: float | None = None
    lesion_opacity: float | None = None
    mpr_window_preset: str | None = None
    mpr_window_width: float | None = None
    mpr_window_level: float | None = None
    mpr_show_lesion_overlay: bool | None = None
    mpr_show_crosshairs: bool | None = None
    mpr_show_planning_markers: bool | None = None
    planning_notes: str | None = None

    @field_validator("voxel_cursor")
    @classmethod
    def validate_cursor(cls, v: list[int] | None) -> list[int] | None:
        if v is not None:
            if len(v) != 3:
                raise ValueError("voxel_cursor must contain exactly 3 integers [x, y, z]")
            return [int(round(c)) for c in v]
        return None


class PlanningSessionService:
    """
    Manages persistence and retrieval of surgical planning sessions.
    Atomic write via .tmp rename protects session state from corruption.
    """

    def _get_planning_dir(self, case_id: str) -> Path:
        """Resolves outputs/cases/<case_id>/planning directory."""
        case_dir = get_case_path(case_id)
        pdir = case_dir / "planning"
        pdir.mkdir(parents=True, exist_ok=True)
        return pdir

    def _get_session_file(self, case_id: str) -> Path:
        """Resolves path to planning_session.json."""
        return self._get_planning_dir(case_id) / "planning_session.json"

    def _get_default_cursor(self, case_id: str) -> list[int]:
        """Retrieves volume center voxel cursor or safe default."""
        try:
            from src.visualization.mpr import mpr_manager
            meta = mpr_manager.get_metadata(case_id)
            shape = meta.get("shape", [293, 293, 344])
            return [shape[0] // 2, shape[1] // 2, shape[2] // 2]
        except Exception:
            return [146, 146, 172]

    def create_default_session(self, case_id: str) -> PlanningSession:
        """Constructs a clean default planning session for a case."""
        cursor = self._get_default_cursor(case_id)
        now_iso = datetime.now(timezone.utc).isoformat()
        session_id = f"session_{uuid.uuid4().hex[:8]}"

        # Attempt to auto-select genuine model lesion if present
        default_lesion = None
        try:
            case_dir = get_case_path(case_id)
            lesions_json = case_dir / "measurements" / "lesions.json"
            if lesions_json.is_file():
                with open(lesions_json, "r", encoding="utf-8") as f:
                    ldata = json.load(f)
                    lesions = ldata.get("lesions", [])
                    if lesions:
                        default_lesion = lesions[0].get("lesion_id")
        except Exception:
            default_lesion = None

        return PlanningSession(
            case_id=case_id,
            session_id=session_id,
            created_at=now_iso,
            updated_at=now_iso,
            selected_lesion_id=default_lesion,
            selected_target_id=f"model_{default_lesion}" if default_lesion else None,
            view_mode="3d",
            selected_mpr_plane="axial",
            voxel_cursor=cursor,
            visible_structures={},
            visible_lesions={default_lesion: True} if default_lesion else {},
            visible_targets={f"model_{default_lesion}": True} if default_lesion else {},
            structure_opacities={},
            organ_opacity=0.85,
            lesion_opacity=1.0,
            planning_notes="",
        )

    def get_session(self, case_id: str) -> PlanningSession:
        """
        Retrieves the persistent planning session for a case.
        If no session exists or file is corrupt, initializes a default session.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        sfile = self._get_session_file(case_id)
        if not sfile.is_file():
            session = self.create_default_session(case_id)
            self.save_session(case_id, session)
            return session

        try:
            with open(sfile, "r", encoding="utf-8") as f:
                data = json.load(f)
                return PlanningSession(**data)
        except Exception:
            # Graceful recovery for empty or corrupt file
            session = self.create_default_session(case_id)
            self.save_session(case_id, session)
            return session

    def save_session(self, case_id: str, session: PlanningSession) -> None:
        """
        Atomically saves planning session state to planning_session.json.
        """
        sfile = self._get_session_file(case_id)
        temp_file = sfile.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(session.model_dump(), f, indent=2)
        temp_file.replace(sfile)

    def update_session(
        self, case_id: str, updates: PlanningSessionUpdateRequest | dict[str, Any]
    ) -> PlanningSession:
        """
        Applies partial updates to the active session and persists atomically.
        """
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")

        session = self.get_session(case_id)
        update_dict = updates.model_dump(exclude_unset=True) if isinstance(updates, PlanningSessionUpdateRequest) else updates

        current_data = session.model_dump()
        for k, v in update_dict.items():
            if v is not None and k in current_data:
                current_data[k] = v

        current_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated_session = PlanningSession(**current_data)
        self.save_session(case_id, updated_session)
        return updated_session

    def reset_session(self, case_id: str) -> PlanningSession:
        """Resets the planning session for a case back to defaults."""
        if not case_exists(case_id):
            raise FileNotFoundError(f"Case '{case_id}' does not exist.")
        session = self.create_default_session(case_id)
        self.save_session(case_id, session)
        return session


# Singleton instance
planning_session_service = PlanningSessionService()
