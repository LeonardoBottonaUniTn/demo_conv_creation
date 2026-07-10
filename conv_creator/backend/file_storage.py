"""Supabase Storage helpers for per-user file content."""
from __future__ import annotations

import mimetypes
import os
import re
from typing import Any, Dict, List, Optional

try:
    from .supabase_client import get_supabase_service_client
except ImportError:
    from supabase_client import get_supabase_service_client

STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "user-files").strip() or "user-files"
ALLOWED_UPLOAD_EXTS = {".json", ".pkl", ".csv"}


def normalize_user_rel_path(*parts: str) -> str:
    """Build a safe relative path inside a user's storage prefix."""
    raw = "/".join(part.strip("/\\") for part in parts if part and str(part).strip())
    if not raw:
        return ""
    normalized = os.path.normpath(raw.replace("\\", "/"))
    if normalized in (".", "..") or normalized.startswith("../") or "/../" in normalized:
        raise ValueError("Invalid or unsafe path")
    return normalized.replace("\\", "/")


def storage_key(user_id: str, rel_path: str = "") -> str:
    rel = normalize_user_rel_path(rel_path) if rel_path else ""
    return f"{user_id}/{rel}" if rel else user_id


def storage_key_from_record(rel_path: str, user_id: str) -> str:
    """Resolve a DB rel_path value to the object key inside the bucket."""
    if not rel_path:
        raise ValueError("Missing storage path")
    rp = str(rel_path).replace("\\", "/")
    legacy_prefix = f"files_root/users/{user_id}/"
    if rp.startswith(legacy_prefix):
        rp = rp[len(legacy_prefix) :]
    elif rp.startswith("files_root/"):
        rp = rp[len("files_root/") :]
    if rp.startswith(f"{user_id}/"):
        return normalize_user_rel_path(rp) if "/" in rp else rp
    if "/" not in rp and not rp.startswith(user_id):
        return storage_key(user_id, rp)
    return rp.lstrip("/")


def public_path_from_storage_key(storage_object_key: str, user_id: str) -> str:
    prefix = f"{user_id}/"
    if storage_object_key.startswith(prefix):
        return storage_object_key[len(prefix) :]
    return storage_object_key


def db_rel_path(user_id: str, rel_path: str) -> str:
    """Canonical metadata path stored in Postgres."""
    return storage_key(user_id, rel_path)


def _bucket():
    return get_supabase_service_client().storage.from_(STORAGE_BUCKET)


def _content_type(filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    if guessed:
        return guessed
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".json":
        return "application/json"
    return "application/octet-stream"


def upload_bytes(user_id: str, rel_path: str, data: bytes, *, filename: Optional[str] = None) -> str:
    key = storage_key(user_id, rel_path)
    name = filename or os.path.basename(key)
    _bucket().upload(
        key,
        data,
        file_options={
            "content-type": _content_type(name),
            "upsert": "true",
        },
    )
    return key


def download_bytes(storage_object_key: str) -> bytes:
    return _bucket().download(storage_object_key)


def delete_object(storage_object_key: str) -> None:
    _bucket().remove([storage_object_key])


def move_object(source_key: str, dest_key: str) -> None:
    _bucket().move(source_key, dest_key)


def object_exists(storage_object_key: str) -> bool:
    return bool(_bucket().exists(storage_object_key))


def list_objects(user_id: str, prefix: str = "") -> List[Dict[str, Any]]:
    """List files and folders under the user's prefix."""
    rel = normalize_user_rel_path(prefix) if prefix else ""
    search_prefix = storage_key(user_id, rel)
    if search_prefix and not search_prefix.endswith("/"):
        search_prefix = f"{search_prefix}/"
    response = _bucket().list(search_prefix or f"{user_id}/")
    return response or []


def walk_user_files(user_id: str, prefix: str = "") -> List[str]:
    """Return storage object keys for all files under a prefix."""
    rel_prefix = normalize_user_rel_path(prefix) if prefix else ""
    base = storage_key(user_id, rel_prefix)
    search_prefix = f"{base}/" if base else f"{user_id}/"
    keys: List[str] = []

    def _walk(current_prefix: str) -> None:
        for item in _bucket().list(current_prefix):
            name = item.get("name") or item.get("id") or ""
            if not name:
                continue
            item_id = item.get("id") or name
            metadata = item.get("metadata") or {}
            if metadata or re.search(r"\.[A-Za-z0-9]+$", name):
                keys.append(f"{current_prefix}{name}".rstrip("/"))
                continue
            nested_prefix = f"{current_prefix}{name}/"
            _walk(nested_prefix)

    _walk(search_prefix)
    return keys


def list_folder_names(user_id: str, prefix: str = "") -> List[str]:
    rel = normalize_user_rel_path(prefix) if prefix else ""
    search_prefix = storage_key(user_id, rel)
    if search_prefix and not search_prefix.endswith("/"):
        search_prefix = f"{search_prefix}/"
    folders: List[str] = []
    for item in _bucket().list(search_prefix or f"{user_id}/"):
        name = item.get("name") or item.get("id") or ""
        metadata = item.get("metadata") or {}
        if name and not metadata and not re.search(r"\.[A-Za-z0-9]+$", name):
            folder_rel = normalize_user_rel_path(rel, name) if rel else name
            folders.append(folder_rel)
    return sorted(folders)


def list_all_folder_names(user_id: str) -> List[str]:
    """Return every folder path under the user's storage prefix."""
    folders: List[str] = []

    def _walk(prefix: str) -> None:
        for name in list_folder_names(user_id, prefix):
            folders.append(name)
            _walk(name)

    _walk("")
    return sorted(folders)


def delete_prefix(user_id: str, prefix: str) -> int:
    rel = normalize_user_rel_path(prefix) if prefix else ""
    keys = walk_user_files(user_id, rel)
    if not keys:
        return 0
    _bucket().remove(keys)
    return len(keys)
