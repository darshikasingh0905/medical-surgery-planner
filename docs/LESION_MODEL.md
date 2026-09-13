# Renal Lesion Model & Checkpoint Verification Specification

## Overview

This document tracks the technical audit, provenance verification, checkpoint status, and architecture requirements for the renal lesion / tumor detection and segmentation subsystem of the **AI-Assisted Preoperative Planning System**.

---

## REAL CHECKPOINT STATUS

**BLOCKED — only architecture/synthetic checkpoint verification is complete; a verified trained checkpoint has not yet been successfully executed.**

---

## 1. Checkpoint Audit & Inventory

### Directory: `weights/kits21/`

| File Name | Size | Extension | SHA-256 Hash | Framework | Status / Contents |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `plans.pkl` | 143,080 bytes (0.14 MB) | `.pkl` | `d15d46664240f0a9056ef1320e00df46fbd866ea94323a98e47b3e9eff1f4e39` | nnU-Net v1 (`Task135_KiTS2021`) | **Metadata Only**: Dataset intensity properties, original voxel spacing, stage configuration. Contains 0 neural network weights. |
| `model_final_checkpoint.model.pkl` | 143,564 bytes (0.14 MB) | `.pkl` | `9f6f0d03dcbe0a67a2e5894f2f10ea6b0f58dd5de5348b3c6a7b6c0e1bede0b2` | nnU-Net v1 (`nnUNetTrainerV2`) | **Trainer Header Only**: Serialized `OrderedDict` with trainer init parameters and class pointer `<class 'nnunet...nnUNetTrainerV2'>`. Contains 0 neural network weights. |
| `model_final_checkpoint.tmp` | 126,103,534 bytes (120.26 MB) | `.tmp` | `a3f1d533e79251ea1921b992da67ca53681b82eb57c5ecc7b93364a66bfdac63` | PyTorch Zipfile / nnU-Net v1 | **Corrupted / Truncated**: Incomplete download fragment. Missing the zip central directory record (`PK\x05\x06`). PyTorch raises `failed finding central directory`. |

---

## 2. Checkpoint Details & Provenance

- **Exact Checkpoint Path**: `weights/kits21/model_final_checkpoint.tmp`
- **Exact Provenance**:
  - Challenge: Kidney and Kidney Tumor Segmentation Challenge 2021 (KiTS21)
  - Dataset: `Task135_KiTS2021` (300 contrast-enhanced abdominal CT scans)
  - Trained by: DKFZ / Fabian Isensee via `nnUNetTrainerV2` (nnU-Net v1)
- **Model Architecture**:
  - 3D Full-Resolution U-Net (`PlainConvUNet`)
  - Encoder stages: 5
  - Base features: 32 (max 320)
  - Strides: `[[1, 1, 1], [2, 2, 2], [2, 2, 2], [2, 2, 2], [2, 2, 2]]`
  - Normalization: InstanceNorm3d (`affine=True, eps=1e-5`)
  - Activation: LeakyReLU (`inplace=True`)
- **Output Classes & Label Mapping**:
  - Label 0: Background
  - Label 1: Kidney Parenchyma
  - Label 2: Kidney Tumor (Mass)
  - Label 3: Kidney Cyst
- **Preprocessing Requirements (Verified from `plans.pkl`)**:
  - Intensity clipping: `[-62.0, 310.0]` HU
  - Z-Score Normalization: `(x - 104.94) / 75.30`
  - Spatial resampling: Median dataset spacing ($\approx 0.78 \times 0.78 \times 1.6\text{ mm}$)
- **Inference Result**:
  - Attempting to load `model_final_checkpoint.tmp` fails with:
    `RuntimeError: PytorchStreamReader failed reading zip archive: failed finding central directory.`
  - The download was interrupted at 120.26 MB before the zip archive table was written.
  - Attempting to load `model_final_checkpoint.model.pkl` with `nnunetv2_checkpoint` is rejected cleanly by the engine because it is a legacy v1 `.pkl` trainer configuration without weight tensors.

---

## 3. External Source Investigation & Access Barriers (Day 12)

- **Zenodo Official Baseline (`Task135_KiTS2021.zip`)**:
  - The authoritative challenge distribution by Fabian Isensee / DKFZ (`https://zenodo.org/records/5126443/files/Task135_KiTS2021.zip`).
  - Access is currently blocked with `HTTP 403 Forbidden` due to IP rate-limiting ("unusual traffic from your network", reference `0daeec0fcea1e08e21d90becb9356690`).
  - This explains the truncated local file `model_final_checkpoint.tmp` (120 MB), where the stream was interrupted prior to writing the ZIP central directory.
- **MONAI Model Zoo (`MONAI/renalStructures_UNEST_segmentation`)**:
  - Evaluated via Hugging Face Hub metadata. Segments normal structures (cortex, medulla, pelvicalyceal system), not tumors. Incompatible under Rule 2 & 3.
- **MONAI Model Zoo (`MONAI/renalStructures_CECT_segmentation`)**:
  - Requires aligned multi-phase CT (arterial + venous phases), incompatible with standard single-phase uploads.
- **Community Repositories (`KagglingFace/nnUNet-KiTS19-3d-lowres-50epochs`)**:
  - KiTS19 binary low-res model trained by an independent user; fails provenance and architecture requirements for KiTS21 full-res segmentation.

---

## 4. Structured Facts, Assumptions & Limitations

### Verified Facts
1. The local file `weights/kits21/model_final_checkpoint.tmp` is truncated at 120.26 MB and cannot be deserialized by PyTorch.
2. The local file `weights/kits21/model_final_checkpoint.model.pkl` is an nnU-Net v1 trainer header with zero neural network weight parameters.
3. The local file `weights/kits21/plans.pkl` contains genuine KiTS21 training metadata and intensity statistics (mean 104.94, std 75.30, clip [-62, 310]).
4. The inference engine architecture reconstructor (`_build_nnunetv2_network_from_checkpoint`) functions properly with valid dictionary checkpoints.
5. All 37 functional unit tests pass, and the real-checkpoint test skips cleanly without synthetic substitution.

### External Source Information
1. The official KiTS21 baseline is hosted on Zenodo under DOI `10.5281/zenodo.5126443`.
2. Accessing the Zenodo file endpoint returns `HTTP 403 Forbidden` from this environment.

### Assumptions
1. We assume no external network proxy or VPN is currently configured to bypass Zenodo's IP block.
2. We assume the operator will need to manually place an uncorrupted, verified KiTS checkpoint into `weights/kits21/` to unblock inference.

### Limitations
1. Without a valid, complete trained checkpoint, real CT lesion inference cannot run.
2. Production cases will continue to segment normal organs safely via TotalSegmentator, but will NOT generate lesion masks until unblocked.

---

## 5. Medical Safety & Critical Stop Condition

- **Zero Fake Predictions**: In accordance with medical engineering guardrails, this system will NEVER substitute random, heuristic, or synthetic predictions into production patient cases.
- **Research Prototype Only**: This software is not certified as a medical device and is not clinically validated for diagnostic, prognostic, or treatment planning decisions.
- **Unblocking Requirement**: Real lesion inference will remain **BLOCKED** until a verified, complete, uncorrupted trained checkpoint (e.g. KiTS21 or KiTS23 `.pth` checkpoint) is downloaded and verified.
