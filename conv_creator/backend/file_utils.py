import os
import json
from typing import Optional, Tuple, Any

def valid_node(node: Any) -> bool:
    """Recursively validate a node in the discussion tree."""
    if not isinstance(node, dict):
        return False
    for k in ('id', 'speaker', 'text', 'children'):
        if k not in node:
            return False
    if not isinstance(node.get('id'), str):
        return False
    if not isinstance(node.get('speaker'), str):
        return False
    if not isinstance(node.get('text'), str):
        return False
    if not isinstance(node.get('children'), list):
        return False
    for ch in node.get('children'):
        if not valid_node(ch):
            return False
    return True

def _classify_file(full_path: str) -> Tuple[Optional[int], Optional[str]]:
    """Classify a JSON file and return structure_ok and category.

    Returns:
        struct_flag: 1 = valid tree/draft, 0 = invalid, None = skipped/non-json
        category: 'discussion' | 'draft' | 'invalid' | None
    """
    if not full_path.lower().endswith('.json'):
        return None, None
    try:
        with open(full_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        return 0, 'invalid'

    # detect draft: has fileRef, users, tree, discussion
    if isinstance(data, dict) and all(k in data for k in ('fileRef', 'users', 'tree', 'discussion')):
        # validate tree and discussion minimally
        tree_ok = isinstance(data.get('tree'), dict) and valid_node(data['tree'])
        discussion_ok = isinstance(data.get('discussion'), list)
        if tree_ok and discussion_ok:
            return 1, 'draft'
        return 0, 'invalid'

    # detect discussion tree file: top-level users + tree
    if isinstance(data, dict) and all(k in data for k in ('users', 'tree')):
        tree_ok = isinstance(data.get('tree'), dict) and valid_node(data['tree'])
        users_ok = isinstance(data.get('users'), list)
        if tree_ok and users_ok:
            return 1, 'discussion'
        return 0, 'invalid'

    # fallback: invalid
    return 0, 'invalid'

def _safe_path(files_root: str, rel_path: str) -> str:
    """Return a safe absolute path inside FILES_ROOT for the given relative path.

    Prevents path traversal. Accepts nested relative paths like 'graphics/img.png'.
    Absolute paths are rejected.
    """
    from fastapi import HTTPException
    if os.path.isabs(rel_path):
        raise HTTPException(status_code=400, detail="Absolute paths are not allowed")
    # normalize and join against FILES_ROOT
    full = os.path.normpath(os.path.join(files_root, rel_path))
    files_root_norm = os.path.normpath(files_root)
    # ensure the resulting path is inside FILES_ROOT
    if not (full == files_root_norm or full.startswith(files_root_norm + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid or unsafe path")
    return full

def _resolve_stored_relpath(relpath: str, backend_dir: str, files_root: str) -> str:
    """Resolve a stored DB relpath to an absolute path inside FILES_ROOT.

    DB rows historically stored values like 'files_root/..' or paths relative to FILES_ROOT.
    This helper tries several interpretations and returns an absolute path (not guaranteed to exist).
    """
    if relpath is None:
        return ''
    rp = str(relpath)
    # strip leading 'files_root/' if present and prefer resolving relative to FILES_ROOT
    prefix = os.path.normpath('files_root') + os.sep
    if rp.startswith(prefix):
        stripped = rp[len(prefix):]
        candidate = os.path.normpath(os.path.join(files_root, stripped))
        return candidate
    # fallback: if stored path looks like an absolute path under BACKEND_DIR, join with BACKEND_DIR
    candidate_backend = os.path.normpath(os.path.join(backend_dir, rp))
    if os.path.exists(candidate_backend):
        return candidate_backend
    # final fallback: interpret as path under FILES_ROOT
    return os.path.normpath(os.path.join(files_root, rp))

def _atomic_write_json(full_path: str, data: Any, ensure_ascii: bool = False) -> None:
    """Write JSON to disk atomically (write to temp file then replace).

    Raises the original exception on failure. Caller may wrap in HTTPException.
    """
    tmp = full_path + '.tmp'
    try:
        # ensure parent dir exists
        parent = os.path.dirname(full_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(tmp, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=2, ensure_ascii=ensure_ascii)
        os.replace(tmp, full_path)
    except Exception:
        # best-effort cleanup of tmp file
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        raise