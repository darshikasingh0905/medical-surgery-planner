# Day 13: KiTS2023 Checkpoint Verification, Real CT Inference & Lesion 3D Reconstruction

## 1. Objective

The objective of Day 13 is to forensically audit, verify, and execute a genuine, complete, provenance-verified KiTS neural network checkpoint for renal lesion detection; execute real CPU inference on the project's patient CT dataset; generate genuine lesion segmentation masks and 3D surface meshes; and maintain strict medical AI safety governance with zero synthetic or fabricated predictions.

---

## 2. Model Source & Provenance

- **Challenge / Task**: Kidney and Kidney Tumor Segmentation Challenge 2023 (KiTS2023 / `Dataset500_KiTS2023`).
- **Source Repository**: `khuhm/KiTS23-2nd-place` (Official release by the KiTS2023 2nd-place winning team).
- **Peer-Reviewed Reference**: Springer LNCS KiTS2023 Challenge Proceedings (DOI: [10.1007/978-3-031-54806-2_2](https://doi.org/10.1007/978-3-031-54806-2_2)).
- **Target Distribution**: `pretrained_models.tar.xz` containing 3D full-resolution nnU-Net v2 weights trained for 1001 epochs over 489 abdominal CT training cases.

---

## 3. Archive Integrity & Extraction Verification

- **Archive Path**: `weights/tmp_download/pretrained_models.tar.xz`
- **File Size**: 1,495,108,424 bytes (1.39 GB)
- **Archive SHA-256 Hash**: `590a65415333b5ffba462b68b89ecc129bb075b57f8eb14c61a382ea845e477e`
- **Decompression Verification**: Decompressed via `bsdtar` directly to disk without errors (Exit Code 0).
- **Target Checkpoint Extracted**: `weights/kits23/checkpoint_final.pth` (and `checkpoint_best.pth`).

---

## 4. Forensic Checkpoint Verification

| Property | Value / Verification Finding |
| :--- | :--- |
| **File Path** | `weights/kits23/checkpoint_final.pth` |
| **File Size** | 250,183,291 bytes (238.59 MB) |
| **SHA-256 Hash** | `0bff109e2ba5a9764e12028d338b66107518a881a8ba39746102d8fd8708fa58` |
| **nnU-Net Version** | nnU-Net v2 (`nnUNetTrainer`, `dynamic_network_architectures`) |
| **Configuration** | `3d_fullres` |
| **Training Epochs** | 1001 epochs completed (`current_epoch: 1001`) |
| **Deserialization** | Deserialized successfully on CPU with PyTorch |
| **State Dict Matching** | **0 missing keys, 0 unexpected keys** against instantiated `PlainConvUNet` |
| **Input Channels** | 1 (Single-phase CT) |
| **Output Classes** | 4 output channels |

---

## 5. Model Architecture & Parameters

- **Backbone**: `PlainConvUNet` with 6 hierarchical encoder stages.
- **Encoder Stages**: `n_conv_per_stage_encoder = [2, 2, 2, 2, 2, 2]`
- **Decoder Stages**: `n_conv_per_stage_decoder = [2, 2, 2, 2, 2]`
- **Strides**: `[[1, 1, 1], [2, 2, 2], [2, 2, 2], [2, 2, 2], [2, 2, 2], [2, 2, 2]]` (Total spatial downsampling factor: $2^5 = 32$)
- **Base Features**: 32 (capped at 320 at deep bottleneck)
- **Normalization & Activation**: `InstanceNorm3d(affine=True, eps=1e-5)` and `LeakyReLU(inplace=True)`
- **Parameter Count**:
  - **Full Training Checkpoint**: 88,622,004 parameters (includes multi-stage deep supervision heads)
  - **Inference Network**: 31,197,204 parameters (`deep_supervision=False`)

---

## 6. Class & Label Mapping

Derived from embedded `dataset.json`:
- **Class 0**: `background`
- **Class 1**: `kidney` (Normal renal parenchyma)
- **Class 2**: `tumor` (Solid malignant renal mass)
- **Class 3**: `cyst` (Fluid-filled renal cyst)

*Crucial Engineering Finding*: The model explicitly separates kidney parenchyma (1), tumor mass (2), and cyst (3). In the inference engine, class 2 is mapped to tumor probabilities and class 3 to cyst probabilities.

---

## 7. Preprocessing & Normalization Requirements

Derived from embedded `plans.json` (`configurations['3d_fullres']`):
- **Intensity Scheme**: `CTNormalization`
- **Intensity Clipping**: `[-58.0, 302.0]` HU (0.5th to 99.5th percentiles of foreground dataset)
- **Z-Score Normalization**: $(x - 103.136) / 73.343$
- **Spatial Padding Constraint**: PlainConvUNet 6-stage downsampling requires spatial input dimensions to be divisible by 32 and $\ge 64$ to prevent InstanceNorm3d variance collapse at the bottleneck. The engine automatically pads ROIs with edge background values and unpads after inference.

---

## 8. Real CT Inference Execution

- **Patient Scan**: `datasets/raw/ct/ct_15mm_defaced.nii`
- **Volume Dimensions**: $293 \times 293 \times 344$ voxels
- **Voxel Spacing**: $1.5 \times 1.5 \times 1.5$ mm (isotropic)
- **Inference Device**: CPU
- **ROI Strategy**: Kidney bounding boxes extracted via `roi_extractor.py` using TotalSegmentator masks expanded by 20.0 mm physical safety margins.

### Left Kidney Inference
- **ROI Shape**: $(84, 78, 104)$ voxels
- **Padded Inference Tensor**: $1 \times 1 \times 96 \times 96 \times 128$
- **Inference Time**: **1.825 seconds**
- **Logit / Probability Statistics**:
  - Background (0): Mean prob 0.8772
  - Kidney Parenchyma (1): Max prob 0.9999, mean 0.1226, 84,390 argmax voxels
  - Tumor Mass (2): Max prob 0.00996 (< 1.0%), mean $6.2 \times 10^{-5}$, **0 voxels**
  - Renal Cyst (3): Max prob 0.9989 (99.89%), mean $1.35 \times 10^{-4}$, **91 confident voxels** ($0.3071\text{ mL}$)

### Right Kidney Inference
- **ROI Shape**: $(76, 70, 100)$ voxels
- **Padded Inference Tensor**: $1 \times 1 \times 96 \times 96 \times 128$
- **Inference Time**: **1.802 seconds**
- **Logit / Probability Statistics**:
  - Kidney Parenchyma (1): Max prob 0.9960, mean 0.1214, 67,953 argmax voxels
  - Tumor Mass (2): Max prob 0.00514 (< 0.5%), mean $8.6 \times 10^{-5}$, **0 voxels**
  - Renal Cyst (3): Max prob 0.00043, **0 voxels**

---

## 9. Computational Interpretation & Model Prediction Reporting

In accordance with strict clinical AI governance:
- **No Tumor-Class Segmentation**: No tumor-class (class 2) voxels exceeded the configured segmentation threshold (0.50) in this inference; max tumor probability across both kidneys was $< 1.0\%$.
- **Zero Fabrication**: No synthetic tumor mask was created or forced into the patient case.
- **Model-Predicted Cyst-Class Segmentation**: A 91-voxel ($0.3071\text{ mL}$) cluster was segmented with class-3 (cyst) probability $> 99.8\%$ (mean cluster probability $93.7\%$). This represents a computational segmentation of the KiTS23 cyst label, not a clinical or histological confirmation of benign pathology.

---

## 10. 3D Lesion Reconstruction & Generated Artifacts

- **Provenance Metadata**: `outputs/cases/b2f89382-9416-4e94-9486-b00c6b1de64b/lesions/provenance.json`
- **NIfTI Cyst Mask**: `outputs/cases/b2f89382-9416-4e94-9486-b00c6b1de64b/lesions/cyst_left.nii.gz` (Embedded into original full $293 \times 293 \times 344$ CT coordinate space)
- **3D Surface Mesh**: `outputs/cases/b2f89382-9416-4e94-9486-b00c6b1de64b/meshes/cyst_left.obj` (146 vertices, 288 faces, generated via Marching Cubes with physical millimeter scaling)
- **Case Descriptor**: Updated `case.json` to include `"cyst_left"` in active meshes.

---

## 11. Automated Test Suite Results

Ran complete pytest test suite:
```powershell
python -m pytest tests/ -v
```

- **Total Tests Collected**: 41
- **Passed**: 41 (100%)
- **Failed**: 0
- **Skipped**: 0

### New Tests Added in Day 13:
1. `test_kits23_checkpoint_loading_and_metadata`: Validates loading, metadata, parameter count, and 4-class label mappings.
2. `test_kits23_multiclass_inference_probabilities`: Validates forward-pass probabilities, softmax distribution (sum = 1.0), and argmax prediction.
3. `test_lesion_physical_volume_and_mesh_reconstruction`: Validates physical volume conversion ($cm^3$/mL) and Marching Cubes mesh vertex generation.

---

## 12. Medical Safety & Clinical Governance Statement

- **Investigational Prototype Only**: This software is not certified as a primary diagnostic device or autonomous surgical planner.
- **Clinical Review Required**: All automated anatomical meshes and lesion segmentations require verification by a board-certified radiologist or surgeon.
- **Integrity Guarantee**: The platform never fabricates lesions or simulates confidence. A negative prediction is recorded truthfully.

---

## 13. Remaining Blockers & Next Immediate Step

- **Blockers**: None for model inference. The genuine KiTS2023 checkpoint is verified, loaded, and operating at sub-2-second CPU latency.
- **Next Immediate Step (Day 14)**: Implement surgical clearance metrics (Euclidean distance from detected lesions to renal artery, renal vein, and renal pelvis) and integrate live 3D cyst/tumor visualization into the React/Three.js frontend controls.
