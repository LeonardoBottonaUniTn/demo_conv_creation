from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
import os
import json
import shutil
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from database import (
    _delete_file_record,
    _get_file_by_name_or_relpath,
    _get_file_record_by_id,
    _list_files_db,
    _upsert_file_record,
)
from file_utils import _classify_file, _safe_path, _resolve_stored_relpath, _atomic_write_json
from config import FILES_ROOT, BACKEND_DIR

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("")
def list_files(folder: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available files from the Supabase metadata table.

    If folder is provided it filters results to that subfolder (relative to files_root).
    If DB is empty it will scan FILES_ROOT (or the provided folder) to populate the DB.
    """
    rows = _list_files_db()
    
    def fill_defaults(file_row):
        # Always set type to 'json' if missing or None
        if not file_row.get('type'):
            file_row['type'] = 'json'
        # If uploadDate is missing or None, use file creation time
        if not file_row.get('uploadDate'):
            file_path = file_row.get('path')
            if file_path and os.path.exists(file_path):
                ts = os.path.getctime(file_path)
                file_row['uploadDate'] = datetime.fromtimestamp(ts).isoformat()
            else:
                file_row['uploadDate'] = datetime.now().isoformat()
        return file_row
    
    if rows:
        if folder:
            folder_prefix = os.path.normpath(os.path.join(os.path.basename(FILES_ROOT), folder))
            def in_folder(relpath: str) -> bool:
                rp = os.path.normpath(relpath)
                if rp == folder_prefix:
                    return True
                return rp.startswith(folder_prefix + os.sep)

            filtered = [fill_defaults(r) for r in rows if in_folder(r['path'])]
            return filtered

        top_level = []
        for r in rows:
            rp = os.path.normpath(r.get('path', ''))
            prefix = os.path.normpath(os.path.basename(FILES_ROOT)) + os.sep
            if rp.startswith(prefix):
                rel = rp[len(prefix):]
            else:
                rel = rp
            if rel and os.sep not in rel:
                top_level.append(fill_defaults(r))
        return top_level

    # fallback: walk FILES_ROOT and populate DB (respect folder if provided)
    allowed_exts = {'.json', '.pkl', '.csv'}
    entries = []
    if folder:
        start = _safe_path(FILES_ROOT, folder)
        for root, _, files in os.walk(start):
            for name in files:
                if os.path.splitext(name)[1].lower() in allowed_exts:
                    full = os.path.join(root, name)
                    rec = _upsert_file_record(full, BACKEND_DIR, _classify_file)
                    entries.append(rec)
    else:
        for root, _, files in os.walk(FILES_ROOT):
            for name in files:
                if os.path.splitext(name)[1].lower() in allowed_exts:
                    full = os.path.join(root, name)
                    rec = _upsert_file_record(full, BACKEND_DIR, _classify_file)
                    entries.append(rec)
    return entries


@router.get('/id/{file_id}')
def get_file_by_id(file_id: int, download: bool = False):
    """Return file metadata or JSON content when targeting by numeric id."""
    logger = logging.getLogger('uvicorn.error')
    row = _get_file_record_by_id(file_id)
    if not row:
        raise HTTPException(status_code=404, detail='File not found')
    relpath = row['path']
    full = _resolve_stored_relpath(relpath, BACKEND_DIR, FILES_ROOT)
    files_root_norm = os.path.normpath(FILES_ROOT)
    if not (full == files_root_norm or full.startswith(files_root_norm + os.sep)):
        raise HTTPException(status_code=400, detail='Invalid file path stored in DB')
    if not os.path.exists(full):
        logger.error(f"get_file_by_id: resolved full path does not exist: {full}")
        raise HTTPException(status_code=404, detail='File not found')
    
    if download:
        return FileResponse(full, media_type='application/octet-stream', filename=os.path.basename(full))

    ext = os.path.splitext(full)[1].lower()
    if ext == '.json':
        with open(full, 'r', encoding='utf-8') as f:
            try:
                return JSONResponse(content=json.load(f))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to parse JSON: {e}")
    elif ext == '.pkl':
        return {"message": "This is a Python pickle file. Use the download endpoint to retrieve it or process it on the server."}
    else:
        return FileResponse(full, media_type='application/octet-stream', filename=os.path.basename(full))


@router.get("/{filename:path}")
def get_file(filename: str, download: bool = False):
    """Return file content for JSON files, a message for PKL, otherwise provide a download."""
    try:
        full = _safe_path(FILES_ROOT, filename)
    except HTTPException:
        raise

    if not os.path.exists(full):
        record = _get_file_by_name_or_relpath(filename)
        if record:
            relpath = record.get('path')
            try:
                candidate = _resolve_stored_relpath(relpath, BACKEND_DIR, FILES_ROOT)
            except Exception:
                candidate = None
            files_root_norm = os.path.normpath(FILES_ROOT)
            if candidate and (candidate == files_root_norm or candidate.startswith(files_root_norm + os.sep)) and os.path.exists(candidate):
                full = candidate
            else:
                raise HTTPException(status_code=404, detail="File not found")
        else:
            raise HTTPException(status_code=404, detail="File not found")

    if download:
        return FileResponse(full, media_type='application/octet-stream', filename=os.path.basename(full))

    ext = os.path.splitext(filename)[1].lower()
    if ext == '.json':
        with open(full, 'r', encoding='utf-8') as f:
            try:
                return JSONResponse(content=json.load(f))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to parse JSON: {e}")
    elif ext == '.pkl':
        return {"message": "This is a Python pickle file. Use the download endpoint to retrieve it or process it on the server."}
    else:
        return FileResponse(full, media_type='application/octet-stream', filename=filename)


@router.patch('/id/{file_id}')
async def save_changes_file_by_id(file_id: int, request: Request):
    """Save changes to a JSON file identified by numeric id."""
    row = _get_file_record_by_id(file_id)
    if not row:
        raise HTTPException(status_code=404, detail='File not found')
    name = row['name']
    relpath = row['path']
    full = _resolve_stored_relpath(relpath, BACKEND_DIR, FILES_ROOT)
    logger = logging.getLogger('uvicorn.error')
    logger.info(f"save_changes_file_by_id: id={file_id} name={name} relpath={relpath} resolved_full={full}")
    files_root_norm = os.path.normpath(FILES_ROOT)
    if not (full == files_root_norm or full.startswith(files_root_norm + os.sep)):
        raise HTTPException(status_code=400, detail='Invalid file path stored in DB')
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail='File not found')
    if not os.path.isfile(full):
        raise HTTPException(status_code=400, detail='Target is not a file')
    ext = os.path.splitext(full)[1].lower()
    if ext != '.json':
        raise HTTPException(status_code=400, detail='Only JSON files can be modified via this endpoint')
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Invalid JSON body: {e}')
    try:
        _atomic_write_json(full, data)
    except Exception as e:
        logger.error(f"save_changes_file_by_id: failed to write {full}: {e}")
        raise HTTPException(status_code=500, detail=f'Failed to save JSON file: {e}')
    rec = _upsert_file_record(full, BACKEND_DIR, _classify_file)
    return {"message": "Saved", "file": rec}


@router.patch('/{filename:path}')
async def save_changes_file_by_name(filename: str, request: Request):
    """Save changes to a JSON file identified by filename (relative to files_root)."""
    logger = logging.getLogger('uvicorn.error')
    try:
        full = _safe_path(FILES_ROOT, filename)
    except HTTPException:
        logger.error(f"save_changes_file_by_name: unsafe path requested: {filename}")
        raise

    if os.path.isdir(full):
        raise HTTPException(status_code=400, detail='Target is a directory')

    ext = os.path.splitext(full)[1].lower()
    if ext != '.json':
        raise HTTPException(status_code=400, detail='Only JSON files can be modified via this endpoint')

    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"save_changes_file_by_name: invalid JSON for {filename}: {e}")
        raise HTTPException(status_code=400, detail=f'Invalid JSON body: {e}')

    users = body.get('users') if isinstance(body, dict) else None

    if os.path.exists(full):
        try:
            with open(full, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            raise HTTPException(status_code=400, detail='Target exists but is not valid JSON')
        if isinstance(data, dict):
            if users is not None:
                data['users'] = users
                to_write = data
            else:
                if isinstance(body, dict):
                    to_write = body
                else:
                    raise HTTPException(status_code=400, detail='Nothing to write')
        else:
            raise HTTPException(status_code=400, detail='Target JSON is not an object; cannot insert users')
    else:
        if not isinstance(users, list):
            raise HTTPException(status_code=400, detail='Target does not exist; provide a "users" array to create it')
        to_write = {'users': users}

    try:
        logger.info(f"save_changes_file_by_name: writing to {full} (exists={os.path.exists(full)}) size={len(json.dumps(to_write)) if to_write is not None else 0}")
        _atomic_write_json(full, to_write)
    except Exception as e:
        logger.error(f"save_changes_file_by_name: failed to write {full}: {e}")
        raise HTTPException(status_code=500, detail=f'Failed to save JSON file: {e}')

    rec = _upsert_file_record(full, BACKEND_DIR, _classify_file)
    return {"message": "Saved", "file": rec}


@router.delete('/id/{file_id}')
def delete_file_by_id(file_id: int):
    row = _get_file_record_by_id(file_id)
    if not row:
        raise HTTPException(status_code=404, detail='File not found')
    name = row['name']
    relpath = row['path']
    full = _resolve_stored_relpath(relpath, BACKEND_DIR, FILES_ROOT)
    if os.path.exists(full):
        try:
            os.remove(full)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to remove file: {e}')
    _delete_file_record(name)
    return {"message": "Deleted", "file": name, "id": file_id}


@router.delete("/{filename:path}")
def delete_file(filename: str):
    full = _safe_path(FILES_ROOT, filename)
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(full)
    rel = os.path.relpath(full, BACKEND_DIR)
    record = _get_file_by_name_or_relpath(rel) or _get_file_by_name_or_relpath(os.path.basename(filename))
    file_id = record['id'] if record else None
    try:
        _delete_file_record(os.path.basename(filename))
    except Exception:
        pass
    return {"message": "Deleted", "file": filename, "id": file_id}


@router.post('/migrate-files')
def migrate_files():
    """Scan backend directory for allowed files and populate/update the Supabase metadata table."""
    allowed_exts = {'.json', '.pkl', '.csv'}
    entries = []
    for root, _, files in os.walk(FILES_ROOT):
        for name in files:
            if os.path.splitext(name)[1].lower() in allowed_exts:
                full = os.path.join(root, name)
                rec = _upsert_file_record(full, BACKEND_DIR, _classify_file)
                entries.append(rec)
    return {"migrated": len(entries), "files": entries}


@router.post('/save-draft/{filename:path}')
async def save_draft_file(filename: str, request: Request):
    """Create a new draft JSON file under FILES_ROOT with the provided filename."""
    logger = logging.getLogger('uvicorn.error')
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"save_draft_file: invalid JSON body for {filename}: {e}")
        raise HTTPException(status_code=400, detail=f'Invalid JSON body: {e}')

    payload = body.get('payload') if isinstance(body, dict) else None
    if payload is None:
        raise HTTPException(status_code=400, detail='Missing "payload" in request body')

    if not filename.lower().endswith('.json'):
        filename = filename + '.json'

    try:
        rel = filename
        full = _safe_path(FILES_ROOT, rel)
    except HTTPException as e:
        logger.error(f"save_draft_file: unsafe filename requested: {filename}")
        raise

    if os.path.isdir(full):
        raise HTTPException(status_code=400, detail='Target filename resolves to a directory')

    try:
        _atomic_write_json(full, payload, ensure_ascii=False)
    except Exception as e:
        logger.error(f"save_draft_file: failed to write {full}: {e}")
        raise HTTPException(status_code=500, detail=f'Failed to write draft file: {e}')

    try:
                rec = _upsert_file_record(full, BACKEND_DIR, _classify_file)
    except Exception:
        rec = None

    return {"message": "Draft saved", "file": rec or os.path.basename(full)}


@router.post('/move')
def move_files_endpoint(data: dict):
    """Move files listed in `targets` to the `dest` folder (relative to files_root)."""
    targets = data.get('targets') if isinstance(data, dict) else None
    dest = data.get('dest') if isinstance(data, dict) else ''
    if not targets or not isinstance(targets, list):
        raise HTTPException(status_code=400, detail='Missing or invalid targets')

    try:
        dest_full = _safe_path(FILES_ROOT, dest) if dest else FILES_ROOT
    except HTTPException as e:
        raise e

    os.makedirs(dest_full, exist_ok=True)
    moved = []
    errors = []

    for t in targets:
        record = None
        try:
            tid = int(t)
            record = _get_file_record_by_id(tid)
        except (TypeError, ValueError):
            record = None
        if not record:
            record = _get_file_by_name_or_relpath(str(t))

        if not record:
            errors.append({'target': t, 'error': 'not found in DB'})
            continue

        name = record['name']
        relpath = record['path']

        try:
            src_full = _resolve_stored_relpath(relpath, BACKEND_DIR, FILES_ROOT)
        except Exception:
            errors.append({'target': t, 'error': 'invalid stored path'})
            continue

        files_root_norm = os.path.normpath(FILES_ROOT)
        if not (src_full == files_root_norm or src_full.startswith(files_root_norm + os.sep)):
            errors.append({'target': t, 'error': 'invalid stored path'})
            continue
        if not os.path.exists(src_full):
            errors.append({'target': t, 'error': 'source file missing'})
            continue

        dest_full_path = os.path.join(dest_full, os.path.basename(src_full))
        try:
            if os.path.exists(dest_full_path):
                os.remove(dest_full_path)
            shutil.move(src_full, dest_full_path)
            rec = _upsert_file_record(dest_full_path, BACKEND_DIR, _classify_file)
            moved.append({'target': t, 'moved_to': rec.get('path'), 'id': rec.get('id')})
        except Exception as e:
            errors.append({'target': t, 'error': str(e)})
    return {'moved': moved, 'errors': errors}
