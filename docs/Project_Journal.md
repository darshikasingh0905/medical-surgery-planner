# AI-Assisted Preoperative Planning System

## Project Development Journal

This journal documents the major milestones achieved during the development of the AI-Assisted Preoperative Planning System. Instead of recording daily progress, the project is organized into milestones that represent significant stages of development.

---

# Milestone 1 – Project Foundation ✅

## Objectives
- Set up the development environment and project structure.
- Understand the basics of medical imaging.
- Load and inspect CT scan data.

## Achievements
- Created the project folder structure and initialized the Git repository.
- Configured the Python virtual environment and project dependencies.
- Learned the fundamentals of CT imaging and the NIfTI file format.
- Downloaded and organized an anonymized CT dataset.
- Implemented a reusable NIfTI loader using NiBabel.
- Successfully loaded CT scans into the application.
- Extracted scan metadata, including image dimensions, voxel spacing, affine matrix, and data type.
- Created a `ScanMetadata` dataclass for structured metadata representation.

## Outcome
The project can reliably load medical CT scans and extract all essential metadata required for subsequent image processing tasks.

---

# Milestone 2 – Medical Image Visualization ✅

## Objectives
Develop an interactive CT viewer capable of visualizing medical images in a way similar to professional radiology software.

## Achievements
- Converted CT scans into 3D NumPy arrays.
- Displayed axial CT slices using Matplotlib.
- Built an interactive CT slice viewer with slider navigation.
- Added keyboard navigation using the left and right arrow keys.
- Implemented mouse wheel scrolling for slice navigation.
- Learned and implemented CT Window Width (WW) and Window Level (WL).
- Added professional CT window presets for Bone, Lung, and Soft Tissue visualization.
- Displayed real-time viewer information, including slice number, window width, and window level.
- Refactored the visualization module into reusable and maintainable components.

## Outcome
The application now includes an interactive CT viewer capable of navigating through medical scans while applying clinically relevant CT window presets.

---

# Milestone 3 – Medical Image Preprocessing ✅

## Objectives
Prepare CT images for future AI-based segmentation by implementing a classical medical image preprocessing pipeline.

## Achievements
- Implemented Min-Max normalization to scale voxel intensities.
- Visualized CT intensity distributions using histograms.
- Applied Gaussian filtering for image noise reduction.
- Implemented threshold-based segmentation.
- Built image comparison utilities for preprocessing evaluation.
- Implemented morphological operations:
  - Dilation
  - Erosion
  - Opening
  - Closing
- Implemented connected component analysis.
- Added largest connected component extraction to remove segmentation noise.
- Extended the visualization pipeline to compare each preprocessing stage side by side.

## Outcome
The project now includes a complete preprocessing pipeline capable of producing cleaner binary segmentation masks that are suitable for classical computer vision algorithms and future deep learning models.

---


# Milestone 4 – Classical Image Segmentation Classical Image Processing & ROI Extraction ✅

## Objectives
Build a complete classical medical image processing pipeline capable of extracting the patient's region of interest (ROI) from CT scans and preparing the data for future AI-based organ segmentation and surgical planning.

## Achievements

### Edge Detection
- Implemented Sobel edge detection using SciPy.
- Detected intensity gradients within CT slices.
- Visualized anatomical boundaries.
- Implemented OpenCV Canny edge detection.
- Applied Canny edge detection on the middle CT slice.
- Compared Sobel and Canny edge detection results.
- Observed thinner, cleaner, and more accurate edges using Canny.

### Contour Detection
- Implemented contour detection using OpenCV `findContours()`.
- Detected connected anatomical boundaries.
- Drew contours over the original CT slice for visualization.

### Contour Analysis
- Calculated the total number of detected contours.
- Computed contour area for each detected object.
- Computed contour perimeter for each detected object.
- Identified the largest contour representing the patient's body.

### ROI Localization
- Computed the bounding rectangle using `cv2.boundingRect()`.
- Visualized the patient's Region of Interest (ROI).
- Cropped the CT image using the detected bounding box.
- Removed unnecessary background surrounding the patient.

### Image Export
- Implemented a reusable image saving utility.
- Automatically saved the extracted ROI into the project output directory.

## Challenges
- Understood the differences between Sobel and Canny edge detection.
- Learned that OpenCV Canny operates only on 2D images rather than full 3D CT volumes.
- Worked with contour hierarchies and largest contour extraction.
- Understood coordinate-based image cropping using bounding rectangles.

## Key Learnings
- Difference between edge detection and image segmentation.
- Importance of contour analysis in medical image processing.
- ROI extraction reduces unnecessary computation before AI segmentation.
- Classical computer vision techniques provide strong preprocessing for deep learning models.

## Outcome
The project now includes a complete classical image processing pipeline capable of detecting anatomical boundaries, extracting the patient's body, localizing the Region of Interest (ROI), and preparing medical images for future AI-based organ segmentation.

---

# Milestone 5 – AI-Based Organ Segmentation ⏳

### Planned Features
- U-Net
- MONAI
- Organ Segmentation
- Tumor Segmentation
- Segmentation Evaluation

---

# Milestone 6 – 3D Reconstruction ⏳

### Planned Features
- Marching Cubes
- Mesh Generation
- STL / OBJ Export
- Interactive 3D Visualization

---

# Milestone 7 – AI-Assisted Surgical Planning ⏳

### Planned Features
- LLM Integration
- Anatomical Explanation
- Surgical Planning Assistance
- Interactive Surgical Reports

---