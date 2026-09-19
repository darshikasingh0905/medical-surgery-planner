from fastapi import APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil
import os
import json

from src.api.utils.case_manager import generate_case_id, init_case_directory, get_case_info, get_case_path, case_exists
from src.pipeline.case_processor import process_case_background

router = APIRouter(prefix="/api/cases", tags=["cases"])

class CaseResponse(BaseModel):
    case_id: str
    filename: str
    status: str
    error: str | None = None
    results: dict | None = None

ALLOWED_EXTENSIONS = {".nii", ".nii.gz"}

def is_allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension."""
    return any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)

@router.post("/upload", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def upload_case(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload a NIfTI scan.
    Generates a unique case ID and saves the file to the case's input directory.
    Triggers background processing.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    case_id = generate_case_id()
    case_path = init_case_directory(case_id, file.filename)
    
    input_dir = case_path / "input"
    file_path = input_dir / file.filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    finally:
        file.file.close()
        
    # Queue the background processing
    background_tasks.add_task(process_case_background, case_id)
        
    return CaseResponse(
        case_id=case_id,
        filename=file.filename,
        status="uploaded"
    )

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case_status(case_id: str):
    """
    Retrieve information about an existing case including processing status.
    """
    case_info = get_case_info(case_id)
    
    if not case_info:
        raise HTTPException(status_code=404, detail="Case not found")
        
    return CaseResponse(**case_info)

@router.get("/{case_id}/results")
async def get_case_results(case_id: str):
    """
    Retrieve structured measurement results for a completed case.
    """
    if not case_exists(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
        
    case_info = get_case_info(case_id)
    if case_info.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Results not ready. Case status is '{case_info.get('status')}'")
        
    results_path = get_case_path(case_id) / "measurements" / "results.json"
    if not results_path.exists():
        raise HTTPException(status_code=404, detail="Results file not found for this case")
        
    with open(results_path, "r") as f:
        data = json.load(f)
        
    return {
        "case_id": case_id,
        "status": "completed",
        "organs": data
    }

@router.get("/{case_id}/meshes/{organ}")
async def get_case_mesh(case_id: str, organ: str):
    """
    Serve a generated 3D mesh (.obj) for a specific case and organ.
    """
    ALLOWED_ORGANS = {
        'liver', 'heart', 'aorta', 'kidney_left', 'kidney_right',
        'cyst_left', 'cyst_right', 'tumor_left', 'tumor_right',
        'inferior_vena_cava', 'adrenal_gland_left', 'adrenal_gland_right'
    }
    
    if organ not in ALLOWED_ORGANS:
        raise HTTPException(status_code=400, detail=f"Invalid organ. Allowed: {', '.join(sorted(ALLOWED_ORGANS))}")
        
    if not case_exists(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
        
    mesh_path = get_case_path(case_id) / "meshes" / f"{organ}.obj"
    
    if not mesh_path.exists():
        raise HTTPException(status_code=404, detail=f"Mesh not found for {organ}")
        
    return FileResponse(path=mesh_path, filename=f"{organ}.obj", media_type="text/plain")



@router.get("/{case_id}/lesions")
async def get_case_lesions(case_id: str):
    """
    Retrieve structured lesion measurements and clearance metrics for a completed case.
    """
    if not case_exists(case_id):
        raise HTTPException(status_code=404, detail="Case not found")

    case_info = get_case_info(case_id)
    if case_info.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Results not ready. Case status is '{case_info.get('status')}'")

    case_path = get_case_path(case_id)
    lesions_json_path = case_path / "measurements" / "lesions.json"

    # If lesions.json already exists on disk, return it
    if lesions_json_path.exists():
        with open(lesions_json_path, "r") as f:
            data = json.load(f)
        return data

    # Otherwise, check if lesion masks exist in lesions/ directory and compute
    lesions_dir = case_path / "lesions"
    if lesions_dir.exists():
        from src.measurements.lesion_measurements import calculate_comprehensive_lesion_metrics
        struct_dir = case_path / "segmentation"
        lesion_files = list(lesions_dir.glob("*.nii.gz"))

        detected_lesions = []
        for lf in lesion_files:
            host = "kidney_left" if "left" in lf.name else "kidney_right"
            try:
                metrics = calculate_comprehensive_lesion_metrics(lf, struct_dir, host_organ=host)
                mesh_name = metrics["lesion_id"]
                detected_lesions.append({
                    "lesion_id": mesh_name,
                    "class_name": "tumor" if "tumor" in mesh_name else "cyst",
                    "host_organ": host,
                    "computational_interpretation": (
                        "Model-predicted tumor-class segmentation" if "tumor" in mesh_name
                        else "Model-predicted cyst-class segmentation"
                    ),
                    "volume_ml": metrics["volume"]["volume_ml"],
                    "dimensions_mm": metrics["bounding_box"]["dimensions_mm"],
                    "centroid_mm": metrics["centroid"]["physical_centroid_mm"],
                    "voxel_count": metrics["volume"]["foreground_voxels"],
                    "computational_distances": metrics["computational_distances"],
                    "mesh_available": (case_path / "meshes" / f"{mesh_name}.obj").exists(),
                    "mesh_name": mesh_name,
                    "provenance_file": "lesions/provenance.json"
                })
            except Exception:
                continue

        payload = {
            "case_id": case_id,
            "total_lesions": len(detected_lesions),
            "lesions": detected_lesions,
            "safety_disclaimer": (
                "All spatial metrics are computational estimates derived from CT segmentation masks. "
                "They do not constitute clinically verified surgical margins or operative recommendations."
            )
        }
        lesions_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lesions_json_path, "w") as f:
            json.dump(payload, f, indent=2)
        return payload

    return {
        "case_id": case_id,
        "total_lesions": 0,
        "lesions": [],
        "safety_disclaimer": "No lesion masks were segmented for this case."
    }


@router.get("/{case_id}/lesions/{lesion_id}")
async def get_specific_lesion(case_id: str, lesion_id: str):
    """
    Retrieve detailed metrics for a specific lesion by its lesion ID.
    """
    lesions_data = await get_case_lesions(case_id)
    for lesion in lesions_data.get("lesions", []):
        if lesion.get("lesion_id") == lesion_id:
            return lesion
    raise HTTPException(status_code=404, detail=f"Lesion '{lesion_id}' not found in case '{case_id}'")


@router.get("/{case_id}/structures")
async def get_case_anatomical_structures(case_id: str):
    """
    Retrieve machine-readable audit of anatomical structures for this case,
    including availability on disk, mask paths, mesh availability, and status explanations.
    """
    if not case_exists(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
        
    case_path = get_case_path(case_id)
    from src.anatomy.structure_registry import inspect_case_structures
    structures_dict = inspect_case_structures(case_path)
    return {
        "case_id": case_id,
        "structures": list(structures_dict.values())
    }


@router.get("/{case_id}/lesions/{lesion_id}/relationships")
async def get_lesion_spatial_relationships(case_id: str, lesion_id: str):
    """
    Retrieve computational spatial relationships between a specific lesion and
    registered anatomical structures for a completed case.
    """
    if not case_exists(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
        
    case_info = get_case_info(case_id)
    if case_info.get("status") != "completed":
        raise HTTPException(status_code=400, detail=f"Results not ready. Case status is '{case_info.get('status')}'")
        
    case_path = get_case_path(case_id)
    cache_path = case_path / "measurements" / f"relationships_{lesion_id}.json"
    if cache_path.exists():
        with open(cache_path, "r") as f:
            data = json.load(f)
        return data
        
    # Check if lesion mask exists
    lesion_mask_path = case_path / "lesions" / f"{lesion_id}.nii.gz"
    if not lesion_mask_path.exists():
        candidates = list((case_path / "lesions").glob(f"{lesion_id}*.nii*"))
        if candidates:
            lesion_mask_path = candidates[0]
        else:
            raise HTTPException(status_code=404, detail=f"Lesion '{lesion_id}' not found in case '{case_id}'")
            
    from src.measurements.spatial_relationships import compute_lesion_spatial_relationships
    payload = compute_lesion_spatial_relationships(lesion_mask_path, case_path)
    payload["case_id"] = case_id
    payload["lesion_id"] = lesion_id
    
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w") as f:
        json.dump(payload, f, indent=2)
        
    return payload


@router.get("/{case_id}/mpr")
async def get_case_mpr_metadata(case_id: str):
    """
    Retrieve volume metadata and plane dimensions for Multi-Planar Reconstruction (MPR).
    """
    if not case_exists(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
        
    from src.visualization.mpr import mpr_manager
    try:
        metadata = mpr_manager.get_metadata(case_id)
        return metadata
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load CT volume metadata: {str(e)}")


@router.get("/{case_id}/mpr/slice/{plane}/{index}")
async def get_case_mpr_slice(
    case_id: str,
    plane: str,
    index: int,
    ww: float = 400.0,
    wl: float = 40.0,
    overlay_lesion: bool = True
):
    """
    Retrieve an orthogonal 2D CT slice rendered with specified Window Width (ww)
    and Window Level (wl) as an optimized PNG image.
    """
    if not case_exists(case_id):
        raise HTTPException(status_code=404, detail="Case not found")

    plane_lower = plane.lower()
    if plane_lower not in {"axial", "coronal", "sagittal"}:
        raise HTTPException(status_code=400, detail=f"Invalid plane '{plane}'. Allowed: 'axial', 'coronal', 'sagittal'")

    from src.visualization.mpr import mpr_manager
    try:
        meta = mpr_manager.get_metadata(case_id)
        plane_info = meta["planes"].get(plane_lower)
        total_slices = plane_info["total_slices"]
        if index < 0 or index >= total_slices:
            raise HTTPException(
                status_code=400,
                detail=f"Slice index {index} out of range for plane '{plane}' (0 to {total_slices - 1})"
            )

        png_bytes = mpr_manager.get_slice_bytes(
            case_id=case_id,
            plane=plane_lower,
            index=index,
            window_width=ww,
            window_level=wl,
            overlay_lesion=overlay_lesion
        )
        return Response(
            content=png_bytes,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting slice: {str(e)}")



