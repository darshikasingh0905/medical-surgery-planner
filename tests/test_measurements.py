import os
import unittest
from src.measurements.measurement_engine import (
    calculate_mask_volume,
    calculate_mesh_volume,
    calculate_bounding_box,
    calculate_distance,
    compare_volumes
)

class TestMeasurements(unittest.TestCase):

    def setUp(self):
        self.data_dir = "outputs"
        self.organ = "liver"
        self.mask_path = os.path.join(self.data_dir, "segmentations", f"{self.organ}.nii.gz")
        self.mesh_path = os.path.join(self.data_dir, "meshes", f"{self.organ}.obj")
        
        if not os.path.exists(self.mask_path):
            self.skipTest(f"Mask {self.mask_path} not found")
        if not os.path.exists(self.mesh_path):
            self.skipTest(f"Mesh {self.mesh_path} not found")

    def test_mask_volume(self):
        data = calculate_mask_volume(self.mask_path)
        self.assertGreater(data["volume_mm3"], 0)
        self.assertGreater(data["foreground_voxels"], 0)
        self.assertEqual(len(data["voxel_spacing"]), 3)
        self.assertGreater(data["voxel_volume"], 0)
        self.assertAlmostEqual(data["volume_cm3"], data["volume_ml"])
        
    def test_mesh_volume(self):
        data = calculate_mesh_volume(self.mesh_path)
        self.assertGreater(data["volume_mm3"], 0)
        self.assertAlmostEqual(data["volume_cm3"], data["volume_ml"])
        
    def test_bounding_box(self):
        data = calculate_bounding_box(self.mesh_path)
        self.assertGreater(data["x_mm"], 0)
        self.assertGreater(data["y_mm"], 0)
        self.assertGreater(data["z_mm"], 0)
        self.assertEqual(len(data["bounds"]), 6)
        
    def test_compare_volumes(self):
        mask_vol = 1500000.0
        mesh_vol = 1450000.0
        comp = compare_volumes(mask_vol, mesh_vol)
        self.assertAlmostEqual(comp["absolute_difference_mm3"], 50000.0)
        self.assertAlmostEqual(comp["percentage_difference"], (50000.0 / 1500000.0) * 100)
        
    def test_distance(self):
        p1 = (0, 0, 0)
        p2 = (3, 4, 0)
        dist = calculate_distance(p1, p2)
        self.assertAlmostEqual(dist, 5.0)


class TestLesionMeasurements(unittest.TestCase):
    """Unit tests for Day 14 surgical spatial measurement engine."""

    def test_lesion_volume_isotropic_and_anisotropic(self):
        import numpy as np
        from src.measurements.lesion_measurements import calculate_lesion_volume

        # 10x10x10 cube = 1000 voxels
        mask = np.zeros((20, 20, 20), dtype=np.uint8)
        mask[5:15, 5:15, 5:15] = 1

        # Isotropic 1.5mm spacing -> voxel volume = 3.375 mm³
        res_iso = calculate_lesion_volume(mask, (1.5, 1.5, 1.5))
        self.assertEqual(res_iso["foreground_voxels"], 1000)
        self.assertAlmostEqual(res_iso["voxel_volume_mm3"], 3.375)
        self.assertAlmostEqual(res_iso["volume_mm3"], 3375.0)
        self.assertAlmostEqual(res_iso["volume_ml"], 3.375)

        # Anisotropic (1.0, 2.0, 3.0) spacing -> voxel volume = 6.0 mm³
        res_aniso = calculate_lesion_volume(mask, (1.0, 2.0, 3.0))
        self.assertEqual(res_aniso["foreground_voxels"], 1000)
        self.assertAlmostEqual(res_aniso["voxel_volume_mm3"], 6.0)
        self.assertAlmostEqual(res_aniso["volume_mm3"], 6000.0)
        self.assertAlmostEqual(res_aniso["volume_ml"], 6.0)

    def test_lesion_bounding_box_and_empty(self):
        import numpy as np
        from src.measurements.lesion_measurements import calculate_lesion_bounding_box

        # 4x6x8 voxels
        mask = np.zeros((30, 30, 30), dtype=np.uint8)
        mask[10:14, 10:16, 10:18] = 1

        res = calculate_lesion_bounding_box(mask, (1.5, 2.0, 2.5))
        self.assertEqual(res["voxel_dimensions"], [4, 6, 8])
        self.assertAlmostEqual(res["x_mm"], 4 * 1.5)
        self.assertAlmostEqual(res["y_mm"], 6 * 2.0)
        self.assertAlmostEqual(res["z_mm"], 8 * 2.5)

        # Empty mask
        empty_mask = np.zeros((10, 10, 10), dtype=np.uint8)
        res_empty = calculate_lesion_bounding_box(empty_mask, (1.0, 1.0, 1.0))
        self.assertEqual(res_empty["voxel_dimensions"], [0, 0, 0])
        self.assertEqual(res_empty["dimensions_mm"], [0.0, 0.0, 0.0])

    def test_lesion_centroid(self):
        import numpy as np
        from src.measurements.lesion_measurements import calculate_lesion_centroid

        mask = np.zeros((20, 20, 20), dtype=np.uint8)
        # Single voxel at (10, 12, 14)
        mask[10, 12, 14] = 1

        affine = np.diag([2.0, 2.0, 2.0, 1.0])
        affine[0, 3] = 100.0

        res = calculate_lesion_centroid(mask, (2.0, 2.0, 2.0), affine=affine)
        self.assertEqual(res["voxel_centroid"], [10.0, 12.0, 14.0])
        self.assertEqual(res["physical_centroid_mm"], [20.0, 24.0, 28.0])
        self.assertEqual(res["world_centroid_mm"], [120.0, 24.0, 28.0])

    def test_minimum_distance_physical_euclidean(self):
        import numpy as np
        from src.measurements.lesion_measurements import calculate_minimum_distance_to_structure

        lesion = np.zeros((50, 50, 50), dtype=np.uint8)
        structure = np.zeros((50, 50, 50), dtype=np.uint8)

        # Lesion voxel at (10, 10, 10)
        lesion[10, 10, 10] = 1
        # Structure voxel at (13, 14, 10) -> delta = (3, 4, 0)
        structure[13, 14, 10] = 1

        # Isotropic 1.0 mm: distance = sqrt(3^2 + 4^2) = 5.0 mm
        dist_iso = calculate_minimum_distance_to_structure(lesion, structure, (1.0, 1.0, 1.0))
        self.assertAlmostEqual(dist_iso, 5.0)

        # Anisotropic (2.0, 1.0, 1.0) -> delta mm = (6, 4, 0) -> dist = sqrt(36 + 16) = sqrt(52) = 7.211 mm
        dist_aniso = calculate_minimum_distance_to_structure(lesion, structure, (2.0, 1.0, 1.0))
        self.assertAlmostEqual(dist_aniso, 7.211, places=3)

        # Overlapping masks should yield 0.0 mm
        dist_overlap = calculate_minimum_distance_to_structure(lesion, lesion, (1.0, 1.0, 1.0))
        self.assertEqual(dist_overlap, 0.0)

    def test_comprehensive_metrics_synthetic(self, tmp_path_factory=None):
        import tempfile
        from pathlib import Path
        import numpy as np
        import nibabel as nib
        from src.measurements.lesion_measurements import calculate_comprehensive_lesion_metrics

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            seg_dir = tmp_path / "segmentation"
            seg_dir.mkdir()

            # Create synthetic kidney mask (box [10:30, 10:30, 10:30])
            kidney_arr = np.zeros((50, 50, 50), dtype=np.uint8)
            kidney_arr[10:30, 10:30, 10:30] = 1
            affine = np.eye(4)
            nib.save(nib.Nifti1Image(kidney_arr, affine), seg_dir / "kidney_left.nii.gz")

            # Create synthetic cyst mask inside kidney [15:20, 15:20, 15:20]
            cyst_arr = np.zeros((50, 50, 50), dtype=np.uint8)
            cyst_arr[15:20, 15:20, 15:20] = 1
            cyst_path = tmp_path / "cyst_left.nii.gz"
            nib.save(nib.Nifti1Image(cyst_arr, affine), cyst_path)

            metrics = calculate_comprehensive_lesion_metrics(
                lesion_mask_path=cyst_path,
                structures_dir=seg_dir,
                host_organ="kidney_left",
                vessel_organs=["aorta", "renal_artery"]
            )

            self.assertEqual(metrics["lesion_id"], "cyst_left")
            self.assertEqual(metrics["volume"]["foreground_voxels"], 125)
            self.assertTrue(metrics["computational_distances"]["kidney_left_surface"]["is_within_organ_parenchyma"])
            # Renal artery and aorta do not exist -> marked unavailable
            self.assertEqual(metrics["computational_distances"]["aorta"]["status"], "unavailable")
            self.assertEqual(metrics["computational_distances"]["renal_artery"]["status"], "unavailable")


if __name__ == '__main__':
    unittest.main()
