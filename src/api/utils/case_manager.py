import os
import uuid
import shutil
from pathlib import Path

# Assuming outputs directory is at the root of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CASES_DIR = OUTPUTS_DIR / "cases"

def generate_case_id() -> str:
    """Generate a unique UUID for a new case."""
    return str(uuid.uuid4())

def init_case_directory(case_id: str) -> Path:
    """
    Initialize the directory structure for a new case.
    
    Structure:
    outputs/cases/<case_id>/
        input/
        segmentation/
        meshes/
        measurements/
    """
    case_path = CASES_DIR / case_id
    
    # Create subdirectories
    (case_path / "input").mkdir(parents=True, exist_ok=True)
    (case_path / "segmentation").mkdir(parents=True, exist_ok=True)
    (case_path / "meshes").mkdir(parents=True, exist_ok=True)
    (case_path / "measurements").mkdir(parents=True, exist_ok=True)
    
    return case_path

def get_case_path(case_id: str) -> Path:
    """Get the path to an existing case directory."""
    return CASES_DIR / case_id

def case_exists(case_id: str) -> bool:
    """Check if a case directory exists."""
    return get_case_path(case_id).is_dir()

def get_case_info(case_id: str) -> dict:
    """Retrieve basic info about a case."""
    if not case_exists(case_id):
        return None
        
    case_path = get_case_path(case_id)
    input_dir = case_path / "input"
    
    # Find the uploaded file in the input directory
    files = list(input_dir.glob("*"))
    filename = files[0].name if files else None
    
    return {
        "case_id": case_id,
        "filename": filename,
        "status": "uploaded" if filename else "created"
    }
