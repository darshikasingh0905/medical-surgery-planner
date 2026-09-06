import os
import uuid
import shutil
import json
from pathlib import Path

# Assuming outputs directory is at the root of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CASES_DIR = OUTPUTS_DIR / "cases"

def generate_case_id() -> str:
    """Generate a unique UUID for a new case."""
    return str(uuid.uuid4())

def init_case_directory(case_id: str, filename: str) -> Path:
    """
    Initialize the directory structure for a new case and create case.json.
    
    Structure:
    outputs/cases/<case_id>/
        input/
        segmentation/
        meshes/
        measurements/
        case.json
    """
    case_path = CASES_DIR / case_id
    
    # Create subdirectories
    (case_path / "input").mkdir(parents=True, exist_ok=True)
    (case_path / "segmentation").mkdir(parents=True, exist_ok=True)
    (case_path / "meshes").mkdir(parents=True, exist_ok=True)
    (case_path / "measurements").mkdir(parents=True, exist_ok=True)
    
    # Initialize case.json
    case_info = {
        "case_id": case_id,
        "filename": filename,
        "status": "uploaded"
    }
    with open(case_path / "case.json", "w") as f:
        json.dump(case_info, f, indent=4)
        
    return case_path

def get_case_path(case_id: str) -> Path:
    """Get the path to an existing case directory."""
    return CASES_DIR / case_id

def case_exists(case_id: str) -> bool:
    """Check if a case directory exists."""
    return get_case_path(case_id).is_dir()

def get_case_info(case_id: str) -> dict:
    """Retrieve basic info about a case from case.json."""
    if not case_exists(case_id):
        return None
        
    case_json_path = get_case_path(case_id) / "case.json"
    if not case_json_path.exists():
        # Fallback for manually created or older cases
        input_dir = get_case_path(case_id) / "input"
        files = list(input_dir.glob("*"))
        filename = files[0].name if files else None
        return {
            "case_id": case_id,
            "filename": filename,
            "status": "uploaded" if filename else "created"
        }
        
    with open(case_json_path, "r") as f:
        return json.load(f)

def update_case_status(case_id: str, status: str, error: str = None, results: dict = None):
    """Update the status of a case in case.json."""
    if not case_exists(case_id):
        return
        
    case_info = get_case_info(case_id)
    if not case_info:
        return
        
    case_info["status"] = status
    if error is not None:
        case_info["error"] = error
    if results is not None:
        case_info["results"] = results
        
    case_json_path = get_case_path(case_id) / "case.json"
    with open(case_json_path, "w") as f:
        json.dump(case_info, f, indent=4)
