from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import os
import json
from typing import Optional

from file_utils import _safe_path
from config import FILES_ROOT

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/{discussion_file:path}")
def get_users(discussion_file: Optional[str] = None):
    """Return the users metadata from a discussion file."""

    def _load_users_from_file(full_path: str):
        if not os.path.exists(full_path):
            return None
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get('users'), list):
                return data.get('users')
        except Exception:
            return None
        return None

    if not discussion_file:
        raise HTTPException(status_code=400, detail="A discussion_file path must be provided")

    try:
        full = _safe_path(FILES_ROOT, discussion_file)
    except HTTPException:
        raise

    users = _load_users_from_file(full)
    if users is None:
        if not os.path.exists(full):
            raise HTTPException(status_code=404, detail="Discussion file not found")
        raise HTTPException(status_code=404, detail="Provided discussion file does not contain a 'users' array")

    return JSONResponse(content={"users": users})
