import os
import uuid
import shutil
import json
from datetime import datetime, timezone
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


def _get_case_last_modified(case_id: str) -> float:
    """
    Returns the most meaningful available last-modified epoch timestamp for a
    case: case.json's own mtime (rewritten whenever status changes) if it
    exists, otherwise the case directory's own mtime as a fallback.
    """
    case_json_path = get_case_path(case_id) / "case.json"
    try:
        if case_json_path.is_file():
            return case_json_path.stat().st_mtime
        return get_case_path(case_id).stat().st_mtime
    except OSError:
        return 0.0


def list_cases() -> list[dict]:
    """
    Read-only listing of every case directory under CASES_DIR, most recently
    modified first.

    Reuses get_case_info() for its existing filename/status fallback
    semantics (including the missing-case.json fallback) rather than
    duplicating that logic. Never creates, modifies, or deletes any case
    file. A single malformed/unreadable case directory is skipped rather
    than aborting the entire listing.
    """
    if not CASES_DIR.is_dir():
        return []

    cases: list[dict] = []
    for entry in CASES_DIR.iterdir():
        if not entry.is_dir():
            continue
        case_id = entry.name
        try:
            info = get_case_info(case_id) or {}
            last_modified_ts = _get_case_last_modified(case_id)
            cases.append({
                "case_id": case_id,
                "filename": info.get("filename"),
                "status": info.get("status") or "unknown",
                "last_modified": datetime.fromtimestamp(
                    last_modified_ts, tz=timezone.utc
                ).isoformat(),
                "_sort_ts": last_modified_ts,
            })
        except Exception:
            # Do not let one malformed/unreadable case directory break the
            # entire listing.
            continue

    cases.sort(key=lambda c: c["_sort_ts"], reverse=True)
    for c in cases:
        del c["_sort_ts"]
    return cases


def delete_case(case_id: str) -> bool:
    """
    Permanently deletes a case's entire directory (input scan, segmentation,
    meshes, measurements, lesions, planning session/targets/annotations/
    measurements — everything under outputs/cases/<case_id>/).

    Destructive and irreversible; only ever touches the single named case's
    own directory, never any other case. The caller (route layer) is
    responsible for any user confirmation before invoking this.

    Returns True if the case existed and was deleted, False if it did not
    exist (the caller should treat that as "not found", not an error).
    """
    case_path = get_case_path(case_id)
    if not case_path.is_dir():
        return False
    shutil.rmtree(case_path)
    return True
