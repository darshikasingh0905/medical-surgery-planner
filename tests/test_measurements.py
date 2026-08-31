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

if __name__ == '__main__':
    unittest.main()
