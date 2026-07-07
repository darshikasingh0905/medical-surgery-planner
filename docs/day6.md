
---

# Day 6 - Understanding CT Image Data and Visualizing Medical Images

## Objective

Understand how CT scans are stored as 3D NumPy arrays, learn NumPy slicing for medical images, and display the first CT slice from a real NIfTI scan.

## Completed Tasks

* Learned how `image.get_fdata()` extracts the voxel data from a `Nifti1Image`.
* Understood the difference between a `Nifti1Image` object and the underlying image data.
* Learned why `get_fdata()` returns floating-point data (`float64`).
* Explored the concept of `numpy.memmap` and why NiBabel uses memory mapping for large medical images.
* Understood the structure of a 3D CT volume using the `(X, Y, Z)` dimensions.
* Learned NumPy slicing to extract individual CT slices.
* Displayed the first axial CT slice using Matplotlib.
* Improved the visualization by displaying the middle CT slice for better anatomical representation.
* Interpreted basic CT image features such as air, soft tissue, and bone using Hounsfield Units.

## What I Learned

* A NIfTI file stores a complete 3D medical volume rather than a single image.
* `image.get_fdata()` returns the actual voxel intensity values as a NumPy array.
* CT scans are represented as 3D arrays where:

  * X → Width
  * Y → Height
  * Z → Number of slices
* `:` in NumPy slicing means "select all values along that axis."
* `ct_array[:, :, slice_number]` extracts a complete axial CT slice.
* Memory mapping (`numpy.memmap`) allows large medical images to be accessed efficiently without loading the entire scan into RAM.
* CT scans are displayed in grayscale because each voxel stores a single Hounsfield Unit value representing tissue density rather than RGB color information.

## Current Status

The project can now successfully load a real CT scan, extract the voxel data as a 3D NumPy array, access individual slices, and display medical images using Matplotlib. The core image loading and visualization pipeline is complete.

## Git Commit

```text
Visualize CT slices from 3D medical volume
```

## Next Goal

Build an interactive CT Slice Viewer that allows scrolling through all slices of the CT scan, similar to professional medical imaging software such as 3D Slicer and RadiAnt.

---



