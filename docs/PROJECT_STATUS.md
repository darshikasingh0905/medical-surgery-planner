    # Project Status & Execution Plan

    ## Current Architecture
    The project currently follows a procedural script-based architecture driven by `main.py`. The script orchestrates the data pipeline: loading the NIfTI scan, applying various image preprocessing techniques (normalization, filtering, morphological operations), contour detection, Region of Interest (ROI) extraction, and visualizing the results. The codebase is cleanly separated into functional modules within the `src/` directory.

    ## Existing Modules & What They Do
    - **`src/loaders/`**: Handles loading of medical imaging formats (e.g., NIfTI) using `nibabel` and extracting metadata.
    - **`src/models/`**: Currently empty/placeholder for future model definitions.
    - **`src/preprocessing/`**: Contains scripts for image processing tasks such as filtering (Gaussian, Canny, Sobel), histogram analysis, morphological operations (closing), thresholding, normalization, and ROI cropping.
    - **`src/segmentation/`**: Contains a custom experimental U-Net implementation built in PyTorch (Encoder, Decoder, Bottleneck, CNN blocks).
    - **`src/training/`**: Scripts for training the U-Net model, including custom datasets, loss functions (BCEWithLogitsLoss), and backpropagation logic.
    - **`src/utils/`**: Utility functions like `image_saver.py` for standard operations.
    - **`src/visualization/`**: Contains a 2D CT Viewer and tools to compare different stages of image processing.

    ## Current Dependencies
    **In `requirements.txt`:**
    - `numpy`
    - `matplotlib`
    - `nibabel`

    **Additional Observed Dependencies (Imported but might need installation/verification):**
    - `cv2` (OpenCV, used in `main.py`)
    - `torch` (PyTorch, used in `src/segmentation` and `src/training`)

    ## What Has Been Completed
    - Project structure setup.
    - Loading of `.nii` files and array extraction.
    - A functional 2D CT slice viewer with interactive capabilities.
    - Image preprocessing pipeline (normalization, Gaussian filtering, morphological closing, thresholding).
    - Edge and contour detection (Canny, Sobel, bounding box).
    - Full custom U-Net architecture code (intended for experimental/learning purposes).

    ## What Is Incomplete
    - Integration of a practical, pre-trained segmentation engine (TotalSegmentator).
    - 3D anatomical reconstruction from segmentation masks (meshes).
    - Interactive 3D viewer (Three.js/VTK).
    - Volumetric and spatial measurements of organs.
    - Full-stack integration (FastAPI backend + React frontend).
    - Final UI and documentation polish.

    ## What Should NOT Be Changed
    - Do **not** delete the U-Net implementation in `src/segmentation/` and `src/training/`. This is kept for learning and experimental purposes.
    - Existing modular structure and functional separation should remain intact.
    - Avoid modifying the initial preprocessing pipeline used for educational exploration unless required for the main workflow.

    ## 6-Day Implementation Plan
    - **Day 1**: Integrate TotalSegmentator. Transition from the experimental U-Net to the practical AI segmentation pipeline to generate anatomical masks from the CT scan. Update dependencies.
    - **Day 2**: Process segmentation masks to generate 3D meshes (e.g., using marching cubes via scikit-image or VTK).
    - **Day 3**: Build an interactive 3D anatomy viewer for the generated meshes.
    - **Day 4**: Implement measurement logic (organ volumes, basic anatomical distances).
    - **Day 5**: Setup FastAPI backend and basic React frontend integration.
    - **Day 6**: Complete system integration, test end-to-end workflow, add final documentation, UI polish, and necessary medical disclaimers.

    ## Current Entry Points
    - `main.py`: The primary script to run the existing image preprocessing and visualization pipeline.

    ## How to Run the Project
    1. Activate the Python virtual environment: `.\venv\Scripts\activate` (Windows)
    2. Ensure dependencies are installed (e.g., `pip install -r requirements.txt`)
    3. Run the main script: `python main.py`
