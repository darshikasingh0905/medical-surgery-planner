# Research Notes

This document contains concise notes on important concepts learned during the development of the AI-Assisted Preoperative Planning System.

---

# NIfTI

## What is it?
NIfTI (Neuroimaging Informatics Technology Initiative) is a standard file format used to store 3D medical imaging data such as CT and MRI scans.

## Why is it used?
- Stores complete 3D volumes.
- Preserves voxel spacing and orientation.
- Widely used in medical imaging research.

---

# NiBabel

## What is it?
A Python library used to read and write medical imaging formats such as NIfTI.

## Key Functions
- `nib.load()` – Loads a NIfTI file.
- `get_fdata()` – Returns voxel data as a NumPy array.

---

# CT Volume

A CT scan is represented as a 3D NumPy array.

Dimensions:
- X → Width
- Y → Height
- Z → Number of slices

Example:

Shape = (293, 293, 344)

This means:
- Width = 293
- Height = 293
- Total slices = 344

---

# CT Windowing

## Purpose
Windowing improves visualization by displaying only a selected range of Hounsfield Units.

## Presets
- Bone Window
- Lung Window
- Soft Tissue Window

---

# Min-Max Normalization

## Purpose
Scales image intensity values between 0 and 1.

## Formula

Normalized = (x − min) / (max − min)

## Benefits
- Standardizes intensity values.
- Improves preprocessing consistency.

---

# Gaussian Filter

## Purpose
Reduces image noise while preserving important anatomical structures.

## Applications
- Image denoising
- Preprocessing before segmentation

---

# Thresholding

## Purpose
Converts a grayscale image into a binary image.

Pixels above the threshold become white.

Pixels below the threshold become black.

---

# Morphological Operations

## Dilation
Expands white regions.

## Erosion
Shrinks white regions.

## Opening
Removes small white noise.

## Closing
Fills small holes inside objects.

---

# Connected Component Analysis

## Purpose
Identifies separate connected objects in a binary image.

## Largest Connected Component

Keeps only the largest connected object while removing small isolated regions.

Commonly used to remove segmentation noise before further processing.

## Sobel Edge Detection
- Detects image intensity gradients.
- Produces thicker edges.
- Useful for identifying anatomical boundaries.
- Sensitive to image noise.

## Canny Edge Detection
- Multi-stage edge detection algorithm.
- Produces thin and well-localized edges.
- Includes Gaussian smoothing, non-maximum suppression, and hysteresis thresholding.
- More robust than Sobel for medical image preprocessing.

## Contour Detection
- Uses OpenCV's `findContours()` to identify connected boundaries.
- Represents anatomical structures as connected curves.
- Enables quantitative measurements such as area and perimeter.

## Contour Analysis
- Measured contour area and perimeter.
- Selected the largest contour corresponding to the patient's body.
- Demonstrated how contour-based analysis can localize anatomical regions.

## Bounding Box Localization
- Computed axis-aligned bounding boxes using `cv2.boundingRect()`.
- Used bounding boxes to localize the patient's Region of Interest (ROI).

## ROI Extraction
- Cropped CT slices using the bounding box.
- Reduced unnecessary background.
- Prepared images for future AI segmentation models.

## Key Takeaways
- Edge detection highlights boundaries but does not perform segmentation.
- Contours convert edge pixels into meaningful anatomical objects.
- ROI extraction reduces computational cost and improves downstream processing.
- Classical computer vision forms an effective preprocessing stage before deep learning.