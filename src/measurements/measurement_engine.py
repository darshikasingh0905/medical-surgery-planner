import argparse
import math
import os

import nibabel as nib
import numpy as np
import pyvista as pv

def calculate_mask_volume(mask_path):
    """
    Calculate volume from a NIfTI segmentation mask.
    """
    if not os.path.exists(mask_path):
        raise FileNotFoundError(f"Mask file not found: {mask_path}")
        
    img = nib.load(mask_path)
    data = img.get_fdata()
    header = img.header
    spacing = header.get_zooms()
    
    # We expect 3D volume, get the first 3 spacing values
    voxel_volume = spacing[0] * spacing[1] * spacing[2]
    
    # Binarize and count
    foreground_voxels = np.sum(data > 0)
    
    vol_mm3 = foreground_voxels * voxel_volume
    vol_cm3 = vol_mm3 / 1000.0
    vol_ml = vol_cm3
    
    return {
        "foreground_voxels": int(foreground_voxels),
        "voxel_spacing": spacing[:3],
        "voxel_volume": voxel_volume,
        "volume_mm3": vol_mm3,
        "volume_cm3": vol_cm3,
        "volume_ml": vol_ml
    }

def calculate_mesh_volume(mesh_path):
    """
    Calculate volume from an OBJ mesh using PyVista.
    """
    if not os.path.exists(mesh_path):
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")
        
    mesh = pv.read(mesh_path)
    
    # Calculate volume using PyVista
    vol_mm3 = mesh.volume
    vol_cm3 = vol_mm3 / 1000.0
    vol_ml = vol_cm3
    
    return {
        "is_manifold": mesh.is_manifold,
        "volume_mm3": vol_mm3,
        "volume_cm3": vol_cm3,
        "volume_ml": vol_ml
    }

def calculate_bounding_box(mesh_path):
    """
    Calculate bounding box dimensions of a mesh.
    """
    if not os.path.exists(mesh_path):
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")
        
    mesh = pv.read(mesh_path)
    bounds = mesh.bounds  # xmin, xmax, ymin, ymax, zmin, zmax
    
    x_dim = bounds[1] - bounds[0]
    y_dim = bounds[3] - bounds[2]
    z_dim = bounds[5] - bounds[4]
    
    return {
        "x_mm": x_dim,
        "y_mm": y_dim,
        "z_mm": z_dim,
        "bounds": bounds
    }

def compare_volumes(mask_vol_mm3, mesh_vol_mm3):
    """
    Compare mask and mesh volumes.
    """
    abs_diff = abs(mesh_vol_mm3 - mask_vol_mm3)
    pct_diff = (abs_diff / mask_vol_mm3) * 100.0 if mask_vol_mm3 > 0 else 0.0
    
    return {
        "absolute_difference_mm3": abs_diff,
        "absolute_difference_cm3": abs_diff / 1000.0,
        "percentage_difference": pct_diff
    }

def calculate_distance(p1, p2):
    """
    Calculate Euclidean distance between two 3D points.
    """
    dist = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)
    return dist

def main():
    parser = argparse.ArgumentParser(description="Anatomical Measurements Engine")
    parser.add_argument("--data-dir", default="outputs", help="Base output directory")
    args = parser.parse_args()
    
    organs = ['liver', 'heart', 'aorta', 'kidney_left']
    
    print("==================================================")
    print("ANATOMICAL MEASUREMENTS")
    print("==================================================")
    
    for organ in organs:
        mask_path = os.path.join(args.data_dir, "segmentations", f"{organ}.nii.gz")
        mesh_path = os.path.join(args.data_dir, "meshes", f"{organ}.obj")
        
        try:
            mask_data = calculate_mask_volume(mask_path)
            mesh_data = calculate_mesh_volume(mesh_path)
            bbox_data = calculate_bounding_box(mesh_path)
            comp_data = compare_volumes(mask_data["volume_mm3"], mesh_data["volume_mm3"])
            
            print(f"\nOrgan: {organ.capitalize()}")
            print(f"\nForeground voxels: {mask_data['foreground_voxels']}")
            print(f"Voxel spacing: {mask_data['voxel_spacing']}")
            print(f"Mask volume: {mask_data['volume_mm3']:.2f} mm³")
            print(f"Mask volume: {mask_data['volume_cm3']:.2f} cm³")
            print(f"Mask volume: {mask_data['volume_ml']:.2f} mL")
            print()
            print(f"Mesh volume: {mesh_data['volume_mm3']:.2f} mm³")
            print(f"Mesh volume: {mesh_data['volume_cm3']:.2f} cm³")
            print(f"Mesh volume: {mesh_data['volume_ml']:.2f} mL")
            print()
            print(f"Absolute difference: {comp_data['absolute_difference_cm3']:.2f} cm³")
            print(f"Percentage difference: {comp_data['percentage_difference']:.2f} %")
            print()
            print("Bounding box:")
            print(f"X: {bbox_data['x_mm']:.2f} mm")
            print(f"Y: {bbox_data['y_mm']:.2f} mm")
            print(f"Z: {bbox_data['z_mm']:.2f} mm")
            print("\n==================================================")
            
        except Exception as e:
            print(f"\nOrgan: {organ.capitalize()}")
            print(f"Error processing {organ}: {e}")
            print("\n==================================================")

if __name__ == "__main__":
    main()
