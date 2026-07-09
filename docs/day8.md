
---

# Day 8 - Building an Interactive CT Viewer with Windowing

## Objective

Transform the basic CT slice viewer into an interactive medical image viewer by adding professional navigation controls and CT windowing functionality similar to radiology software.

## Completed Tasks

* Enhanced the CT viewer with keyboard navigation using the left and right arrow keys.
* Added mouse wheel support for smooth scrolling through CT slices.
* Introduced a shared viewer state to manage the current slice and window settings.
* Learned and implemented CT Window Width (WW) and Window Level (WL).
* Created a reusable `apply_window()` preprocessing function.
* Organized image preprocessing into a dedicated `preprocessing` module.
* Implemented professional CT window presets:

  * Bone Window
  * Lung Window
  * Soft Tissue Window
* Added dynamic viewer information displaying:

  * Current window preset
  * Current slice number
  * Window Width
  * Window Level
* Refactored repetitive code using a `WINDOW_PRESETS` dictionary for cleaner and more maintainable implementation.
* Added keyboard shortcuts and an on-screen help guide printed in the terminal.

## What I Learned

* CT scans store Hounsfield Unit (HU) values, which require windowing for proper visualization.
* Window Width controls the range of visible intensity values.
* Window Level determines the center of the displayed intensity range.
* Different tissues require different window settings for optimal visualization.
* Medical imaging viewers use event-driven programming to respond to user interactions.
* Shared application state simplifies communication between sliders, keyboard events, and mouse events.
* Refactoring repeated logic into reusable data structures improves code maintainability and scalability.
* Professional medical imaging software separates image preprocessing from visualization, making the system modular and easier to extend.

## Current Status

The project now includes a fully interactive CT viewer capable of navigating through all CT slices using multiple input methods while dynamically applying professional CT window presets. The visualization module now closely resembles the functionality of basic medical imaging software used in clinical environments.

## Git Commit

```text
Add CT window presets and advanced viewer controls
```

## Next Goal

Build the Medical Image Preprocessing Pipeline by implementing image normalization, noise reduction, histogram analysis, and thresholding techniques to prepare CT scans for AI-based organ and tumor segmentation.

---