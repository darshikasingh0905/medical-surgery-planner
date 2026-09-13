# Day 11: KiTS21/KiTS23 Checkpoint Verification & Architecture Reconstruction

## 1. Executive Summary

Day 11 advances the **AI-Assisted Preoperative Planning System** through rigorous verification, forensic inspection, and architectural integration of renal lesion segmentation models (KiTS21 and KiTS23).

### Medical Engineering & Ethics Compliance
- **No Fake Predictions**: The system refuses to fabricate tumor predictions or output heuristic blobs.
- **Strict Provenance Verification**: Candidate checkpoint files, plans, and weight tensors are inspected for provenance, training configuration, and layer compatibility before execution.
- **Non-Certification Disclosure**: This system is a research prototype developed for educational and surgical planning assistance. It is **NOT clinically validated** and **NOT certified as a medical device**. All computational segmentations require expert urological review.
- **Architectural Integrity**: Existing multi-organ TotalSegmentator pipelines, measurement engines, and REST endpoints remain completely untouched and backward-compatible.

---

## 2. Forensic Inspection of Available Checkpoints (`weights/kits21/`)

A forensic analysis of the checkpoint artifacts in `weights/kits21/` was conducted to establish exact provenance, framework version, and compatibility.

### 2.1 Inspection of `weights/kits21/plans.pkl`

The `plans.pkl` artifact contains the preprocessed training metadata generated during nnU-Net dataset fingerprinting:
- **Framework Version**: nnU-Net v1 (`Task135_KiTS2021`)
- **Number of Classes**: 3 foreground classes (`all_classes: [1, 2, 3]`)
  - Label 1: Kidney Parenchyma
  - Label 2: Kidney Tumor (Mass)
  - Label 3: Kidney Cyst
- **Foreground Intensity Statistics (`intensityproperties`)**:
  - `mean`: **104.94 HU**
  - `sd`: **75.30 HU**
  - `percentile_00_5`: **-62.0 HU**
  - `percentile_99_5`: **310.0 HU**
  - `median`: **103.0 HU**
  - `mn` / `mx`: **-1012.0 HU / 3071.0 HU**

These exact statistical parameters were extracted and codified directly into the pipeline's preprocessing module.

### 2.2 Forensic Analysis of `weights/kits21/model_final_checkpoint.model.pkl`

- **Object Type**: `collections.OrderedDict`
- **Class Reference**: `<class 'nnunet.training.network_training.nnUNetTrainerV2.nnUNetTrainerV2'>`
- **Framework Diagnosis**: This file is an **nnU-Net v1 checkpoint header**.
  - nnU-Net v1 serialized model definitions via Python's `pickle` by storing references to `nnunet.training.network_training.nnUNetTrainerV2`.
  - Deserializing this pickle requires installing the deprecated, legacy `nnunet` v1 package.
  - In modern PyTorch / Python 3.12 environments, attempting to unpickle legacy trainer classes introduces runtime errors and security vulnerabilities.
  - Furthermore, `model_final_checkpoint.model.pkl` contains the trainer metadata, while raw weights are split across `.model` and `.tmp` files.
- **Guardrail Action**: The inference loader explicitly detects `.pkl` files and rejects them with a descriptive explanation when configured with `model_type='nnunetv2_checkpoint'`, instructing the operator on how v1 vs v2 checkpoints differ.

---

## 3. nnU-Net v2 Architecture Reconstruction (`dynamic_network_architectures`)

Modern nnU-Net (v2) packages save self-contained `.pth` PyTorch dictionaries that embed `init_args`, `plans`, and `network_weights`. To execute inference **without requiring the heavy full nnUNet framework**, we built a dedicated lightweight architecture reconstructor:

### `_build_nnunetv2_network_from_checkpoint` in `src/lesions/lesion_inference.py`

1. **Self-Contained Dependency**: Uses `dynamic_network_architectures`, a lightweight, clean neural network library that nnUNetv2 relies on.
2. **Dynamic Instantiation**:
   - Parses `checkpoint['init_args']['plans']['configurations'][configuration]`
   - Extracts network hyperparameters:
     - `UNet_class_name`: `PlainConvUNet` or `ResidualEncoderUNet`
     - `UNet_base_num_features`: typically 32
     - `n_conv_per_stage_encoder` & `n_conv_per_stage_decoder`
     - `pool_op_kernel_sizes` (strides) & `conv_kernel_sizes`
     - `unet_max_num_features`
     - `num_classes`: Total output channels (including background channel 0)
3. **Weight Loading & Mode**:
   - Automatically loads `checkpoint['network_weights']` into the instantiated network.
   - Puts the model into `.eval()` mode and moves it to the target device (CPU / CUDA).

---

## 4. Preprocessing Implementation: `preprocess_ct_roi_nnunet_zscore`

To strictly mirror the KiTS21/KiTS23 nnU-Net preprocessing pipeline, we implemented `preprocess_ct_roi_nnunet_zscore`:

$$\text{ROI}_{\text{clipped}} = \text{clip}(\text{ROI}_{\text{HU}}, -62.0, 310.0)$$

$$\text{ROI}_{\text{normalized}} = \frac{\text{ROI}_{\text{clipped}} - 104.94}{75.30 + \epsilon}$$

### Key Features:
- Validates 3D array input dimensionality.
- Returns normalized `float32` volume and comprehensive metadata dictionary.
- Tested against exact bounds: values at 104.94 HU map to 0.0, -200 HU clips to -62.0 HU normalized, and 500 HU clips to 310.0 HU normalized.

---

## 5. Inference Engine Enhancements (`LesionInferenceEngine`)

The `LesionInferenceEngine` was enhanced with:
- **`nnunetv2_checkpoint` Support**: Seamlessly loads self-contained `.pth` nnUNetv2 checkpoints.
- **Checkpoint Metadata Tracking**: Stores `trainer_name`, `current_epoch`, and `configuration` in `get_model_info()`.
- **Property & Method Aliases**:
  - `engine.is_loaded`: Alias for `engine.is_configured`.
  - `engine.predict_lesion_probabilities`: Alias for `engine.predict`.
- **Safety Error Handling**:
  - Catches corrupted or non-dictionary files.
  - Catches missing required keys (`network_weights`, `init_args`).
  - Detects legacy v1 `.pkl` files and provides instructive error messages.

---

## 6. Verification & Automated Test Suite

A comprehensive test suite was added to `tests/test_lesions.py`:

| Test Name | Verification Focus | Result |
| :--- | :--- | :--- |
| `test_preprocess_ct_roi_nnunet_zscore` | Verifies clipping and z-score math against plans.pkl stats | **PASSED** |
| `test_preprocess_ct_roi_nnunet_zscore_invalid_dimensions` | Verifies 3D dimension assertion | **PASSED** |
| `test_kits21_plans_pkl_inspection` | Inspects real `weights/kits21/plans.pkl` foreground stats | **PASSED** |
| `test_kits21_v1_checkpoint_incompatibility_detection` | Verifies graceful rejection of v1 `.pkl` checkpoint | **PASSED** |
| `test_nnunetv2_checkpoint_missing_keys` | Verifies error handling when checkpoint missing required keys | **PASSED** |
| `test_nnunetv2_checkpoint_non_dict_corrupted` | Verifies handling of non-dict corrupted checkpoint files | **PASSED** |
| `test_build_nnunetv2_network_from_synthetic_checkpoint` | Tests `PlainConvUNet` instantiation and forward pass | **PASSED** |
| `test_nnunetv2_checkpoint_inference_engine_execution` | Tests full end-to-end load & inference on 3D ROI | **PASSED** |
| `test_unsupported_model_type_rejection` | Verifies rejection of unknown model types | **PASSED** |
| `test_real_kits_checkpoint_inference` | Verifies real checkpoint execution without synthetic fallback | **SKIPPED (Cleanly)** |

### Test Suite Execution Summary:
- **Lesion Pipeline Tests (`tests/test_lesions.py`)**: 22 passed, 1 skipped.
- **Whole Repository Tests (`tests/`)**: 37 passed, 1 skipped (100% pass rate).

---

## 7. REAL CHECKPOINT STATUS

**BLOCKED — only architecture/synthetic checkpoint verification is complete; a verified trained checkpoint has not yet been successfully executed.**

### Checkpoint Audit Details:
- **Exact Checkpoint Path**: `weights/kits21/model_final_checkpoint.tmp` (accompanied by `weights/kits21/model_final_checkpoint.model.pkl` and `weights/kits21/plans.pkl`).
- **Exact Provenance**: KiTS21 challenge baseline (`Task135_KiTS2021`, fold 0, trained by Fabian Isensee / DKFZ using legacy `nnUNetTrainerV2`).
- **Model Architecture**: 3D Fullres `PlainConvUNet` (nnU-Net v1/v2 architecture with deep supervision disabled during inference).
- **Label Mapping**:
  - Label 0: Background
  - Label 1: Kidney Parenchyma
  - Label 2: Kidney Tumor (Mass)
  - Label 3: Kidney Cyst
- **Preprocessing Requirements**:
  - Intensity clipping: `[-62.0, 310.0]` HU
  - Z-Score Normalization: `(x - 104.94) / 75.30`
- **Inference Result**:
  - **BLOCKED**: The weights file `weights/kits21/model_final_checkpoint.tmp` is an incomplete/truncated download fragment (120.26 MB) missing its zip central directory (`PK\x05\x06`). PyTorch raises `RuntimeError: PytorchStreamReader failed reading zip archive: failed finding central directory`.
  - The companion file `weights/kits21/model_final_checkpoint.model.pkl` is a 143 KB trainer configuration header referencing `nnunet.training.network_training.nnUNetTrainerV2` and contains zero parameter weights.
- **Limitations & Guardrail Compliance**:
  - In accordance with medical ethics and project safety constraints, no fake or synthetic tumor predictions were substituted.
  - Day 11 architecture reconstruction and checkpoint infrastructure are verified, but real renal lesion inference remains blocked pending a complete, verified trained checkpoint.

---

## 8. Critical Stop Condition & Day 12 Status

Because there is no complete, verified trained KiTS checkpoint on disk:
- **Day 12 IS CURRENTLY BLOCKED.**
- We do **NOT** proceed to Day 12 tumor mesh extraction.
- We do **NOT** create a tumor mesh from synthetic or randomized outputs.
- We do **NOT** create surgical distance metrics from unverified output.
- We do **NOT** claim tumor detection is clinically working.

**Current Official Status**:
> *Day 11 architecture and checkpoint infrastructure are verified, but real renal lesion inference remains blocked pending a verified trained checkpoint.*
