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

def _value_is_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def _message_entry_has_content(entry: dict) -> bool:
    values = entry.get('values')
    if isinstance(values, dict):
        return any(_value_is_nonempty(v) for v in values.values())

    return bool(
        entry.get('labels')
        or (isinstance(entry.get('note'), str) and entry.get('note', '').strip())
        or entry.get('rating') is not None
    )


def _annotation_status_from_json(data: Any) -> Optional[str]:
    """Return annotation workflow status when the file contains annotation data."""
    if not isinstance(data, dict):
        return None

    annotations = data.get('annotations')
    if not isinstance(annotations, dict):
        return None

    status = annotations.get('status')
    if status not in ('in_progress', 'completed'):
        return None

    messages = annotations.get('messages')
    has_message_annotations = isinstance(messages, list) and any(
        _message_entry_has_content(entry)
        for entry in messages
        if isinstance(entry, dict)
    )

    conversation_values = annotations.get('conversationValues')
    has_conversation_values = isinstance(conversation_values, dict) and any(
        _value_is_nonempty(value)
        for value in conversation_values.values()
    )
    has_overall_note = isinstance(annotations.get('overallNote'), str) and annotations['overallNote'].strip()
    has_overall_note = has_overall_note or (
        isinstance(conversation_values, dict)
        and isinstance(conversation_values.get('overallNote'), str)
        and conversation_values['overallNote'].strip()
    )

    if status == 'completed' or has_message_annotations or has_overall_note:
        return status
    return None


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