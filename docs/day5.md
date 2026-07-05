
---

# Day 5 - Metadata Extraction and Data Modeling

## Objective

Build a professional metadata extraction module for NIfTI CT scans and design a structured data model for storing scan information.

## Completed Tasks

* Learned the purpose and advantages of Python `@dataclass`.
* Understood the difference between dictionaries and data classes.
* Designed the `ScanMetadata` class for storing scan metadata.
* Implemented the `extract_metadata()` function.
* Extracted important metadata from the CT scan:

  * Shape
  * Voxel Spacing
  * Data Type
  * Affine Matrix
* Built a clean pipeline from `load_nifti()` to `extract_metadata()`.
* Customized the `ScanMetadata` object's output using the `__repr__()` method.
* Improved metadata formatting by converting NumPy data types into native Python types.

## What I Learned

* How `@dataclass` automatically generates `__init__()`, `__repr__()`, and `__eq__()`.
* Why production applications use custom data models instead of dictionaries.
* The importance of metadata in medical imaging.
* The purpose of the affine matrix in mapping voxel coordinates to real-world patient coordinates.
* The software engineering principle of storing source data while computing derived values when needed.
* How to override Python's default object representation using `__repr__()`.

## Current Status

The project can successfully load a real CT scan, extract its essential metadata, and represent it using a clean, structured `ScanMetadata` object. The metadata pipeline is complete and ready for image visualization.

## Git Commit

```
Implement ScanMetadata dataclass and metadata extraction pipeline
```

## Next Goal

Load the CT scan as a 3D NumPy array, understand image orientation and slicing, and display the first CT slice using Matplotlib.

---


