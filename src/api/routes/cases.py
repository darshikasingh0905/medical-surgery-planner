from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
import shutil
import os

from src.api.utils.case_manager import generate_case_id, init_case_directory, get_case_info

router = APIRouter(prefix="/api/cases", tags=["cases"])

class CaseResponse(BaseModel):
    case_id: str
    filename: str
    status: str

ALLOWED_EXTENSIONS = {".nii", ".nii.gz"}

def is_allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension."""
    return any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)

@router.post("/upload", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def upload_case(file: UploadFile = File(...)):
    """
    Upload a NIfTI scan.
    Generates a unique case ID and saves the file to the case's input directory.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    case_id = generate_case_id()
    case_path = init_case_directory(case_id)
    
    input_dir = case_path / "input"
    file_path = input_dir / file.filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    finally:
        file.file.close()
        
    return CaseResponse(
        case_id=case_id,
        filename=file.filename,
        status="uploaded"
    )

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case_status(case_id: str):
    """
    Retrieve basic information about an existing case.
    """
    case_info = get_case_info(case_id)
    
    if not case_info:
        raise HTTPException(status_code=404, detail="Case not found")
        
    return CaseResponse(**case_info)
