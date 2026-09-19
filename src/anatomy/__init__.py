"""
src/anatomy/__init__.py

Anatomical structure registry and metadata management for surgical planning.
"""

from src.anatomy.structure_registry import (
    STRUCTURE_CATALOG,
    get_structure_definitions,
    get_available_structures,
    get_structure_metadata,
    get_structure_mask_path,
    is_structure_available,
    inspect_case_structures,
)

__all__ = [
    "STRUCTURE_CATALOG",
    "get_structure_definitions",
    "get_available_structures",
    "get_structure_metadata",
    "get_structure_mask_path",
    "is_structure_available",
    "inspect_case_structures",
]
