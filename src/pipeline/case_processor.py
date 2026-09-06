import os
import json
from pathlib import Path

from src.api.utils.case_manager import get_case_path, update_case_status
from src.segmentation.ai_segmenter import run_segmentation
from src.mesh.mesh_generator import process_organ
from src.measurements.measurement_engine import calculate_mask_volume, calculate_mesh_volume, calculate_bounding_box, compare_volumes

ORGANS_TO_PROCESS = ['liver', 'heart', 'aorta', 'kidney_left']

def process_case_background(case_id: str):
    """
    Background task to process an uploaded scan.
    Runs TotalSegmentator, generates meshes, and computes measurements.
    """
    case_path = get_case_path(case_id)
    if not case_path.exists():
        return
        
    case_info = None
    with open(case_path / "case.json", "r") as f:
        case_info = json.load(f)
        
    if not case_info:
        return

    update_case_status(case_id, status="processing")
    
    input_scan_path = case_path / "input" / case_info["filename"]
    segmentations_dir = case_path / "segmentation"
    meshes_dir = case_path / "meshes"
    measurements_dir = case_path / "measurements"
    
    try:
        # 1. Segmentation
        success = run_segmentation(
            input_path=str(input_scan_path),
            output_dir=str(segmentations_dir),
            fast_mode=True
        )
        if not success:
            raise Exception("TotalSegmentator failed to run or produced no output.")
            
        results_payload = {
            "segmentation": True,
            "meshes": [],
            "measurements": True
        }
        
        # 2. Meshes
        for organ in ORGANS_TO_PROCESS:
            if process_organ(organ, segmentations_dir, meshes_dir):
                results_payload["meshes"].append(organ)
                
        # 3. Measurements
        measurements_results = {}
        for organ in ORGANS_TO_PROCESS:
            mask_path = segmentations_dir / f"{organ}.nii.gz"
            mesh_path = meshes_dir / f"{organ}.obj"
            
            organ_results = {}
            if mask_path.exists():
                try:
                    organ_results["mask_volume"] = calculate_mask_volume(str(mask_path))
                except Exception as e:
                    print(f"Error calculating mask volume for {organ}: {e}")
            
            if mesh_path.exists():
                try:
                    organ_results["mesh_volume"] = calculate_mesh_volume(str(mesh_path))
                    organ_results["bounding_box"] = calculate_bounding_box(str(mesh_path))
                except Exception as e:
                    print(f"Error calculating mesh volume for {organ}: {e}")
                    
            if "mask_volume" in organ_results and "mesh_volume" in organ_results:
                try:
                    organ_results["comparison"] = compare_volumes(
                        organ_results["mask_volume"]["volume_mm3"], 
                        organ_results["mesh_volume"]["volume_mm3"]
                    )
                except Exception as e:
                    print(f"Error comparing volumes for {organ}: {e}")
                    
            measurements_results[organ] = organ_results
            
        # Save measurement results
        with open(measurements_dir / "results.json", "w") as f:
            json.dump(measurements_results, f, indent=4)
            
        # Update case status
        update_case_status(case_id, status="completed", results=results_payload)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_case_status(case_id, status="failed", error=str(e))
