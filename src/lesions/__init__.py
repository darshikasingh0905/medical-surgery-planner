"""
src/lesions/__init__.py

Renal lesion pipeline foundation package.
Provides modular components for ROI extraction, preprocessing,
model abstraction, and spatial postprocessing for future validated model integration.
"""

from src.lesions.roi_extractor import (
    extract_kidney_roi,
    save_roi_package,
)
from src.lesions.lesion_inference import (
    preprocess_ct_roi,
    LesionModelConfig,
    LesionInferenceEngine,
)
from src.lesions.postprocessing import (
    postprocess_lesion_mask,
    embed_roi_in_original_space,
    create_lesion_metadata,
    save_original_space_mask,
)

__all__ = [
    "extract_kidney_roi",
    "save_roi_package",
    "preprocess_ct_roi",
    "LesionModelConfig",
    "LesionInferenceEngine",
    "postprocess_lesion_mask",
    "embed_roi_in_original_space",
    "create_lesion_metadata",
    "save_original_space_mask",
]
