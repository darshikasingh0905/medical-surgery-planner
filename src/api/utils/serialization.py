"""
Serialization utilities for converting NumPy types to JSON-compatible Python types.

The measurement engine and NIfTI loaders produce NumPy scalars (float32, float64,
int32, int64, etc.) and arrays. Python's built-in json module cannot serialize these.
This module provides a custom JSON encoder that converts them at the serialization
boundary without modifying the mathematical pipeline.
"""
import json
import numpy as np


class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles NumPy types."""
    
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def sanitize_for_json(obj):
    """
    Recursively convert NumPy types in a nested structure to native Python types.
    
    Handles dicts, lists, tuples, and scalar NumPy values.
    Does NOT change numerical meaning — only converts types.
    """
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj
