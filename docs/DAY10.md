# Day 10: Validated Renal Lesion Model Verification & Integration

## 1. Executive Summary

Day 10 investigates, documents, and prepares the model integration tier for the renal lesion detection/segmentation subsystem of the **AI Medical Surgery Planner**.

Following the medical safety mandates established in Days 8 and 9:
- **No fake tumor predictions** are made.
- **No synthetic tumor masks** are saved to production cases.
- **No unverified arbitrary weights** from unknown internet sources are downloaded or bundled into the repository.
- **Strict Stop Condition Enforced**: Production case processing continues to execute multi-organ segmentation safely. Because certified single-phase KiTS model weights are not packaged by default in standard Python packages (and require specialized downloading from external scientific repositories such as Zenodo or MONAI Model Zoo), the pipeline enforces strict safety: `LesionInferenceEngine` will NOT generate fabricated masks in production cases until an officially verified checkpoint is mounted and configured via environment variables.

---

## 2. Investigation of Candidate Model Sources (Phase 2)

We performed structured provenance and verification research on potential pretrained models for renal tumor segmentation:

### Candidate 1: nnU-Net Task135_KiTS2021 (DKFZ / KiTS21)
1. **Model Name**: `Task135_KiTS2021` (nnU-Net 3d_fullres)
2. **Architecture**: 3D Full-Resolution U-Net with instance normalization, leaky ReLU, and deep supervision.
3. **Dataset Used**: KiTS21 (Kidney and Kidney Tumor Segmentation Challenge 2021).
4. **Dataset Version**: KiTS21 release (300 contrast-enhanced abdominal CT scans).
5. **Training Task**: Semantic segmentation of kidney parenchyma, renal masses/tumors, and renal cysts.
6. **Input Modality**: Contrast-enhanced abdominal CT (single phase, NIfTI).
7. **Input Preprocessing**: Foreground percentile clipping (0.5 to 99.5) and z-score normalization.
8. **Required Voxel Spacing**: Resampled to median dataset spacing ($\approx 0.78 \times 0.78 \times 1.6\text{ mm}$).
9. **Input Dimensions / Patch Size**: $128 \times 128 \times 128$ sliding window.
10. **Output Labels**:
    - Label 0: Background
    - Label 1: Kidney Parenchyma
    - Label 2: Kidney Tumor (Mass)
    - Label 3: Kidney Cyst
11. **Label Meanings**: Differentiates solid neoplasm from benign fluid cyst and normal tissue.
12. **Number of Classes**: 4
13. **Expected Intensity Preprocessing**: Dataset-specific foreground z-score.
14. **Kidney ROI Cropping Used**: Full abdominal scan input.
15. **Expects Full CT or ROI**: Full CT scan.
16. **Checkpoint Availability**: Zenodo repository (DOI: 10.5281/zenodo.5126443).
17. **License**: Apache 2.0 / CC-BY-NC-SA 4.0.
18. **Source URL**: https://doi.org/10.5281/zenodo.5126443 and https://github.com/MIC-DKFZ/nnUNet.
19. **Publication**: Isensee et al., "nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation", *Nature Methods* 2021; Heller et al., "The KiTS21 Challenge", 2021.
20. **Known Limitations**: Requires nnU-Net v1 legacy runtime; multi-fold ensemble checkpoint is large (~1.5 GB); CPU inference takes >10 minutes per scan without GPU acceleration.

---

### Candidate 2: MONAI Model Zoo `renalStructures_CECT_segmentation`
1. **Model Name**: `renalStructures_CECT_segmentation` (v0.2.0)
2. **Architecture**: 3D UNet with residual connections.
3. **Dataset Used**: Multi-center contrast-enhanced renal cohort.
4. **Dataset Version**: 2022 release.
5. **Training Task**: Renal vascular, parenchymal, and pathological segmentation.
6. **Input Modality**: Multi-phase contrast-enhanced CT (arterial, venous, and excretory phases).
7. **Input Preprocessing**: Resampling to $1.0\text{ mm}$ isotropic, clipping to [-150, 250] HU, min-max scaling to [0, 1].
8. **Required Voxel Spacing**: $1.0 \times 1.0 \times 1.0\text{ mm}$.
9. **Input Dimensions / Patch Size**: $96 \times 96 \times 96$.
10. **Output Labels**:
    - Label 0: Background
    - Label 1: Renal Artery
    - Label 2: Renal Vein
    - Label 3: Ureter
    - Label 4: Kidney Parenchyma
    - Label 5: Renal Cyst
    - Label 6: Renal Tumor
11. **Label Meanings**: Multi-class renal vascular and lesion taxonomy.
12. **Number of Classes**: 7
13. **Expected Intensity Preprocessing**: Multi-channel phase alignment.
14. **Kidney ROI Cropping Used**: Trained on aligned multi-phase volumes.
15. **Expects Full CT or ROI**: Multi-phase CT volume.
16. **Checkpoint Availability**: MONAI Model Zoo / Hugging Face (`MONAI/renalStructures_CECT_segmentation`).
17. **License**: Apache 2.0.
18. **Source URL**: https://project-monai.github.io/model-zoo.html.
19. **Publication**: MONAI Model Zoo Official Release.
20. **Known Limitations**: **Critical Modality Mismatch**: Requires multi-phase aligned CT (arterial + venous phases). Incompatible with standard single-phase uploads without co-registration preprocessing.

---

### Candidate 3: MONAI KiTS Auto3DSeg / SegResNet
1. **Model Name**: `MONAI SegResNet KiTS Baseline`
2. **Architecture**: SegResNet (Encoder-Decoder with residual building blocks).
3. **Dataset Used**: KiTS23 (Kidney Tumor Segmentation 2023).
4. **Dataset Version**: KiTS23 release (489 CT scans).
5. **Training Task**: Semantic segmentation of kidney and tumor.
6. **Input Modality**: Single-phase portal venous / nephrographic contrast CT.
7. **Input Preprocessing**: Intensity clipping [-150, 250] HU, spacing resampled to $1.5\text{ mm}$ isotropic.
8. **Required Voxel Spacing**: $1.5 \times 1.5 \times 1.5\text{ mm}$.
9. **Input Dimensions / Patch Size**: $96 \times 96 \times 96$ or $128 \times 128 \times 128$.
10. **Output Labels**: Label 0 = Background/Normal, Label 1 = Renal Tumor.
11. **Label Meanings**: Binary tumor localization.
12. **Number of Classes**: 2
13. **Expected Intensity Preprocessing**: Soft tissue windowing [-150, 250] HU.
14. **Kidney ROI Cropping Used**: Fully compatible with renal ROI cropping.
15. **Expects Full CT or ROI**: ROI-compatible.
16. **Checkpoint Availability**: Trained via MONAI Auto3DSeg recipe; requires external weights download.
17. **License**: Apache 2.0.
18. **Source URL**: https://github.com/neheller/kits23.
19. **Publication**: Heller et al., "The KiTS23 Challenge", 2023.
20. **Known Limitations**: Must be mounted manually; not bundled in base PyPI dependencies.

---

## 3. Selected Model Strategy (Phase 3)

We select **Candidate 3 (MONAI SegResNet / TorchScript KiTS Architecture)** as the primary target for integration because:
1. It operates directly on **single-phase CT** (unlike the multi-phase requirement of `renalStructures_CECT_segmentation`).
2. Its input directly matches our Day 9 `roi_extractor.py` and `preprocess_ct_roi()` output ($[-150, 250]\text{ HU}$, isotropic spacing).
3. It can be loaded directly via PyTorch (`torch.jit.load` or `torch.load`) without requiring legacy nnU-Net v1 framework dependencies.

---

## 4. Configuration & Loading Implementation (Phases 4 & 5)

We updated `src/lesions/lesion_inference.py` to support portable, environment-driven configuration without hardcoded file paths:

### Environment Variables
- `LESION_MODEL_PATH`: Absolute or relative path to the `.pt` / `.pth` checkpoint.
- `LESION_MODEL_TYPE`: `torch_script` (default), `torch_state_dict`, or `monai_segresnet`.
- `LESION_DEVICE`: `cpu` or `cuda` (defaults to auto-detecting CUDA availability with graceful CPU fallback).

### Loading & Safety Logic in `LesionInferenceEngine`
1. **Validation on Startup**:
   - If `model_path` is configured, verifies that the file exists and is a valid file. Raises `FileNotFoundError` if the file is missing.
   - If the checkpoint is corrupted or cannot be deserialized, raises `RuntimeError`.
2. **Graceful Device Fallback**: If `cuda` is requested on a CPU-only environment, logs a clear warning and falls back to `cpu`.
3. **Strict Stop Condition**:
   - If `model_path` is unset, `is_configured` returns `False`.
   - Any attempt to call `predict()` raises:
     ```
     RuntimeError: Validated lesion model weights are not configured. The system will not generate ungrounded or synthetic tumor predictions.
     ```
   - No mock predictions, random masks, or synthetic heuristics are ever returned.

---

## 5. Software Verification & Unit Tests (Phase 9)

We expanded the unit test suite in `tests/test_lesions.py` to 13 test cases (28 total across the project):

| Test Name | Verification Objective | Result |
|---|---|---|
| `test_inference_engine_unconfigured_safety` | Safety: Unconfigured engine raises explicit RuntimeError | **PASS** |
| `test_checkpoint_path_not_found` | Error handling: Non-existent file raises FileNotFoundError | **PASS** |
| `test_invalid_checkpoint_loading_failure` | Error handling: Corrupt checkpoint raises RuntimeError | **PASS** |
| `test_env_configuration` | Config: `from_env()` correctly reads environment variables | **PASS** |
| `test_torch_script_model_loading_and_execution` | Execution: TorchScript module loads and returns probabilities in [0.0, 1.0] | **PASS** |
| `test_roi_bounding_box_and_metadata` | ROI: Bounding box containment and metadata integrity | **PASS** |
| `test_physical_margin_voxel_conversion` | Geometry: Millimeter margin to anisotropic voxel padding | **PASS** |
| `test_roi_boundary_clamping` | Geometry: Border clamping at image boundaries | **PASS** |
| `test_save_roi_package` | Storage: Package directory creation and NIfTI saving | **PASS** |
| `test_preprocessing_windowing_and_normalization` | Transforms: [-150, 250] HU clipping and min-max scaling | **PASS** |
| `test_postprocessing_connected_components` | Postprocessing: Noise removal (< 50 voxels discarded) | **PASS** |
| `test_inverse_roi_mapping_to_original_space` | Inversion: Exact recovery in original patient space | **PASS** |
| `test_create_lesion_metadata` | Metrics: Physical volume and clinical disclaimer formatting | **PASS** |

### Test Suite Execution
```powershell
python -m pytest tests/ -v
# 28 passed, 7 warnings in 12.16s
```

---

## 6. Categorization of Knowledge

### Verified Facts
- TotalSegmentator segments kidneys (`kidney_left.nii.gz`, `kidney_right.nii.gz`) but does not perform parenchymal tumor segmentation.
- KiTS21 / KiTS23 are the authoritative open benchmarks for CT renal tumor segmentation.
- MONAI's `renalStructures_CECT_segmentation` requires multi-phase CT and is incompatible with single-phase uploads.
- The repository does not currently bundle large binary model weights.
- `LesionInferenceEngine` successfully enforces the stop condition and safely prevents synthetic predictions.

### Project Assumptions
- Uploaded CT scans are contrast-enhanced abdominal CT scans where renal parenchyma and lesions exhibit attenuation differences.
- High-end GPUs may not be present in local developer workstations, necessitating CPU inference feasibility.

### Future Work
- Source or train certified KiTS SegResNet weights and place in a dedicated `weights/` directory.
- Mount model path via `LESION_MODEL_PATH` in production environments.
- Integrate Marching Cubes meshing for the lesion mask (`kidney_tumor_left.obj`).
- Expose `/api/cases/{case_id}/lesions` endpoints in FastAPI.

---

## 7. Medical Safety Disclaimer

> [!CAUTION]
> **Research Prototype Only**:
> This platform is an experimental, non-clinical research prototype for AI-assisted preoperative surgical planning.
> 1. It is **NOT** a diagnostic device and has **NOT** been validated for clinical diagnostic use.
> 2. It does **NOT** detect cancer, diagnose malignancy, or stage renal cell carcinoma.
> 3. All outputs require mandatory review and verification by a board-certified physician or surgeon.
