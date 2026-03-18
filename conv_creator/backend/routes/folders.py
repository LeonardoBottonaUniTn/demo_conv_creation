from fastapi import APIRouter, HTTPException
import os
import shutil

from database import _delete_files_with_prefix
from file_utils import _safe_path
from config import FILES_ROOT

router = APIRouter(prefix="/api/folders", tags=["folders"])


@router.get('')
def list_folders():
    """Return all folders under files_root as relative paths."""
    results = []
    for root, dirs, _ in os.walk(FILES_ROOT):
        for d in dirs:
            full = os.path.join(root, d)
            rel = os.path.relpath(full, FILES_ROOT)
            results.append(rel)
    return {"folders": sorted(results)}


@router.post('')
def create_folder(data: dict):
    """Create a folder under files_root. Expects JSON body {path: 'a/b'}"""
    target = data.get('path') if isinstance(data, dict) else None
    if not target:
        raise HTTPException(status_code=400, detail='Missing path')
    full = _safe_path(FILES_ROOT, target)
    try:
        os.makedirs(full, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to create folder: {e}')
    return {"created": True, "path": target}


@router.delete('/{folder_path:path}')
def delete_folder(folder_path: str):
    """Delete a folder under files_root and remove corresponding DB records."""
    if not folder_path or folder_path in ('.', '/'):
        raise HTTPException(status_code=400, detail='Cannot delete root folder')
    full = _safe_path(FILES_ROOT, folder_path)
    if not os.path.isdir(full):
        raise HTTPException(status_code=404, detail='Folder not found')

    try:
        shutil.rmtree(full)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to remove folder: {e}')

    relprefix = os.path.normpath(os.path.join('files_root', folder_path))
    removed = _delete_files_with_prefix(relprefix)

    return {"deleted": True, "path": folder_path, "db_files_removed": removed}
