from fastapi import APIRouter, HTTPException, Request
import os
import json
import shutil
import logging
from datetime import datetime

from database import _get_file_record_by_id, _set_structure_flag, _upsert_file_record
from file_utils import _classify_file
from scripts.llm_calls import transform_discussion_json
from config import FILES_ROOT, BACKEND_DIR

router = APIRouter(prefix="/api/files/fix", tags=["fix"])


@router.post("/{file_id}/preview")
async def preview_file_fix(file_id: int):
    """Preview the LLM-suggested fix without applying it."""
    row = _get_file_record_by_id(file_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")
    name = row['name']
    rel_path = row['path']

    if rel_path.startswith('files_root/'):
        rel_path = rel_path[len('files_root/'):]

    full_path = os.path.join(FILES_ROOT, rel_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"File not found at path: {rel_path}")
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"File is not valid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
    
    try:
        fixed_data = transform_discussion_json(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM transformation failed: {str(e)}")
    
    return {
        "success": True,
        "file_id": file_id,
        "file_name": name,
        "original": input_data,
        "fixed": fixed_data,
        "changes_count": len(fixed_data) if isinstance(fixed_data, list) else 1
    }


@router.post("/{file_id}/apply")
async def apply_file_fix(file_id: int, request: Request):
    """Apply the LLM-suggested fix after user confirmation."""
    body = await request.json()
    fixed_data = body.get("fixed_data")
    overwrite = body.get("overwrite", False)
    
    if isinstance(fixed_data, str):
        try:
            fixed_data = json.loads(fixed_data)
        except Exception:
            pass
    
    row = _get_file_record_by_id(file_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")
    
    name = row['name']
    rel_path = row['path']
    
    if rel_path.startswith('files_root/'):
        rel_path = rel_path[len('files_root/') :]
    
    full_path = os.path.join(FILES_ROOT, rel_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"File not found at path: {rel_path}")
    
    backup_path = None
    backup_created = False
    new_file_id = file_id
    
    if overwrite:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = full_path + f'.backup_{timestamp}'
        try:
            shutil.copy2(full_path, backup_path)
            backup_created = True
        except Exception as e:
            logging.warning(f"Could not create backup: {e}")
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(fixed_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if backup_created:
                shutil.copy2(backup_path, full_path)
            raise HTTPException(status_code=500, detail=f"Error saving fixed file: {str(e)}")
        
        try:
            _set_structure_flag(file_id, True)
        except Exception as exc:
            logging.warning(f"Failed to update structure flag in Supabase: {exc}")
    else:
        base, ext = os.path.splitext(name)
        new_name = f"{base}_fix{ext}"
        new_rel_path = os.path.join(os.path.dirname(rel_path), new_name) if os.path.dirname(rel_path) else new_name
        new_full_path = os.path.join(FILES_ROOT, new_rel_path)
        
        try:
            to_write = fixed_data if fixed_data not in (None, "", []) else {}
            with open(new_full_path, 'w', encoding='utf-8') as f:
                json.dump(to_write, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving fixed file: {str(e)}")
        
        rec = _upsert_file_record(new_full_path, BACKEND_DIR, _classify_file)
        new_file_id = rec.get('id', file_id)
    
    return {
        "success": True,
        "message": "File successfully fixed and saved",
        "file_id": new_file_id,
        "backup_path": backup_path,
        "backup_created": backup_created,
        "overwrite": overwrite
    }


@router.post("/delete-backup")
async def delete_backup_file(request: dict):
    """Delete a backup file created during the fix process."""
    backup_path = request.get("backup_path")
    
    if not backup_path:
        raise HTTPException(status_code=400, detail="backup_path is required")
    
    if ".backup_" not in backup_path:
        raise HTTPException(status_code=400, detail="Only backup files can be deleted through this endpoint")
    
    abs_backup_path = os.path.abspath(backup_path)
    abs_files_root = os.path.abspath(FILES_ROOT)
    
    if not abs_backup_path.startswith(abs_files_root):
        raise HTTPException(status_code=403, detail="Cannot delete files outside of files_root")
    
    try:
        if os.path.exists(backup_path):
            os.remove(backup_path)
            logging.info(f"Deleted backup file: {backup_path}")
            return {"success": True, "message": f"Backup file deleted: {backup_path}"}
        else:
            raise HTTPException(status_code=404, detail="Backup file not found")
    except Exception as e:
        logging.error(f"Failed to delete backup: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting backup: {str(e)}")
