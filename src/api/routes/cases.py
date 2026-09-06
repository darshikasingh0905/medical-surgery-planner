from fastapi import APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks
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
    ALLOWED_ORGANS = {'liver', 'heart', 'aorta', 'kidney_left'}
    
    if organ not in ALLOWED_ORGANS:
        raise HTTPException(status_code=400, detail=f"Invalid organ. Allowed: {', '.join(ALLOWED_ORGANS)}")
        
    if not case_exists(case_id):
        raise HTTPException(status_code=404, detail="Case not found")
        
    mesh_path = get_case_path(case_id) / "meshes" / f"{organ}.obj"
    
    if not mesh_path.exists():
        raise HTTPException(status_code=404, detail=f"Mesh not found for {organ}")
        
    return FileResponse(path=mesh_path, filename=f"{organ}.obj", media_type="text/plain")
