from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from .supabase_client import get_supabase_client
except ImportError:
    from supabase_client import get_supabase_client

logger = logging.getLogger("uvicorn.error")

JsonClassifier = Callable[[str], Tuple[Optional[int], Optional[str]]]
_FileRow = Dict[str, Any]


def _structure_flag_to_bool(flag: Optional[int]) -> Optional[bool]:
    if flag is None:
        return None
    return bool(flag)


def _normalize_file_row(row: _FileRow) -> _FileRow:
    """Convert Supabase column naming to the response shape expected by the UI."""
    upload_date = row.get("upload_date") or row.get("uploadDate")
    if isinstance(upload_date, datetime):
        upload_date = upload_date.isoformat()

    structure_ok = row.get("structure_ok")
    if isinstance(structure_ok, bool):
        normalized_structure = 1 if structure_ok else 0
    else:
        normalized_structure = structure_ok

    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "size": row.get("size"),
        "uploadDate": upload_date,
        "type": row.get("file_type") or row.get("type"),
        "path": row.get("rel_path") or row.get("path"),
        "structure_ok": normalized_structure,
        "category": row.get("category"),
        "checksum": row.get("checksum"),
        "created_by": row.get("created_by"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _upsert_file_metadata(
    *,
    name: str,
    size: int,
    rel_path: str,
    file_type: str,
    created_by: str,
    structure_ok: Optional[bool] = None,
    category: Optional[str] = None,
    upload_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Store or refresh file metadata inside Supabase Postgres."""
    client = get_supabase_client()
    payload = {
        "name": name,
        "size": size,
        "upload_date": upload_date or datetime.utcnow().isoformat(),
        "file_type": file_type,
        "rel_path": rel_path,
        "structure_ok": structure_ok,
        "category": category,
        "created_by": created_by,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    response = (
        client.table("files")
        .select("id")
        .eq("rel_path", rel_path)
        .eq("created_by", created_by)
        .limit(1)
        .execute()
    )
    if response.data:
        file_id = response.data[0]["id"]
        write_response = client.table("files").update(payload).eq("id", file_id).execute()
        row = write_response.data[0] if write_response.data else {**payload, "id": file_id}
    else:
        write_response = client.table("files").insert(payload).execute()
        row = write_response.data[0] if write_response.data else payload

    return _normalize_file_row(row)


def _upsert_file_record(
    *args: Any,
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Legacy helper: upsert metadata from a local file path (dev fallback)."""
    if len(args) == 3:
        path, backend_dir, classify_func = args
    elif len(args) == 4:
        _, path, backend_dir, classify_func = args
    else:
        raise TypeError(
            "_upsert_file_record expected (path, backend_dir, classify_func)"
            " or (db_path, path, backend_dir, classify_func)"
        )

    if not created_by:
        raise ValueError("created_by is required when saving file metadata")

    stat = os.stat(path)
    name = os.path.basename(path)
    size = stat.st_size
    upload_date = datetime.fromtimestamp(stat.st_mtime).isoformat()
    file_type = os.path.splitext(path)[1].lstrip(".").lower() or "unknown"
    rel_path = os.path.relpath(path, backend_dir).replace("\\", "/")

    struct_flag, category = classify_func(path)
    return _upsert_file_metadata(
        name=name,
        size=size,
        rel_path=rel_path,
        file_type=file_type,
        created_by=created_by,
        structure_ok=_structure_flag_to_bool(struct_flag),
        category=category,
        upload_date=upload_date,
    )


def _delete_file_record(*args: Any, user_id: Optional[str] = None) -> None:
    if len(args) == 1:
        name = args[0]
    elif len(args) == 2:
        _, name = args
    else:
        raise TypeError("_delete_file_record expected name or (db_path, name)")
    if not user_id:
        raise ValueError("user_id is required when deleting file metadata")

    client = get_supabase_client()
    client.table("files").delete().eq("name", name).eq("created_by", user_id).execute()


def _delete_file_record_by_id(file_id: int, user_id: str) -> None:
    client = get_supabase_client()
    client.table("files").delete().eq("id", file_id).eq("created_by", user_id).execute()


def _list_files_db(user_id: str) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    response = (
        client.table("files")
        .select("*")
        .eq("created_by", user_id)
        .order("name")
        .execute()
    )
    return [_normalize_file_row(row) for row in (response.data or [])]


def _get_file_record_by_id(file_id: int, user_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    response = (
        client.table("files")
        .select("*")
        .eq("id", file_id)
        .eq("created_by", user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return _normalize_file_row(response.data[0])


def _get_file_by_name_or_relpath(identifier: str, user_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    response = (
        client.table("files")
        .select("*")
        .eq("name", identifier)
        .eq("created_by", user_id)
        .limit(1)
        .execute()
    )
    if response.data:
        return _normalize_file_row(response.data[0])

    response = (
        client.table("files")
        .select("*")
        .eq("rel_path", identifier)
        .eq("created_by", user_id)
        .limit(1)
        .execute()
    )
    if response.data:
        return _normalize_file_row(response.data[0])

    storage_key = identifier if identifier.startswith(f"{user_id}/") else f"{user_id}/{identifier.lstrip('/')}"
    response = (
        client.table("files")
        .select("*")
        .eq("rel_path", storage_key)
        .eq("created_by", user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return _normalize_file_row(response.data[0])


def _delete_files_with_prefix(prefix: str, user_id: str) -> int:
    """Delete file rows owned by the user whose rel_path starts with the prefix."""
    client = get_supabase_client()
    selector = (
        client.table("files")
        .select("id")
        .eq("created_by", user_id)
        .like("rel_path", f"{prefix}%")
    )
    preview = selector.execute()
    ids = [row["id"] for row in (preview.data or [])]
    if not ids:
        return 0
    client.table("files").delete().in_("id", ids).execute()
    return len(ids)


def _set_structure_flag(file_id: int, value: bool, user_id: str) -> None:
    client = get_supabase_client()
    client.table("files").update({"structure_ok": value}).eq("id", file_id).eq(
        "created_by", user_id
    ).execute()
