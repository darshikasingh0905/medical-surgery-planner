"""
src/geometry/__init__.py

Centralized coordinate spaces and spatial geometry package.
"""

from src.geometry.coordinate_system import (
    clamp_coordinates,
    voxel_to_world,
    world_to_voxel,
    voxel_to_physical,
    physical_to_voxel,
    voxel_to_display_crosshair,
    display_to_voxel_crosshair,
    get_plane_dimensions,
    calculate_physical_distance,
)

__all__ = [
    "clamp_coordinates",
    "voxel_to_world",
    "world_to_voxel",
    "voxel_to_physical",
    "physical_to_voxel",
    "voxel_to_display_crosshair",
    "display_to_voxel_crosshair",
    "get_plane_dimensions",
    "calculate_physical_distance",
]
