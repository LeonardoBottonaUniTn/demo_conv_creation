from fastapi import APIRouter, HTTPException, UploadFile, File, Form
import os
from typing import Optional

from database import _upsert_file_record
from file_utils import _classify_file, _safe_path
from config import DB_PATH, FILES_ROOT, BACKEND_DIR

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), path: Optional[str] = Form(None)):
    """Upload a file into the backend directory. Overwrites if name exists."""
    if os.path.basename(file.filename) != file.filename:
        raise HTTPException(status_code=400, detail="Invalid upload filename")
    filename = file.filename
    if path:
        folder_full = _safe_path(FILES_ROOT, path)
        os.makedirs(folder_full, exist_ok=True)
        dest = os.path.join(folder_full, filename)
    else:
        dest = os.path.join(FILES_ROOT, filename)
    try:
        with open(dest, 'wb') as out:
            content = await file.read()
            out.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    
    rec = _upsert_file_record(DB_PATH, dest, BACKEND_DIR, _classify_file)
    if path:
        try:
            folder_full = os.path.normpath(folder_full)
            for name in os.listdir(folder_full):
                full = os.path.join(folder_full, name)
                if os.path.isfile(full) and os.path.splitext(name)[1].lower() in {'.json', '.pkl', '.csv'}:
                    _upsert_file_record(DB_PATH, full, BACKEND_DIR, _classify_file)
        except Exception:
            pass
    return {"message": "Uploaded", "file": rec}
