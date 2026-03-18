from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from supabase_client import get_supabase_client

logger = logging.getLogger("uvicorn.error")

JsonClassifier = Callable[[str], Tuple[Optional[int], Optional[str]]]
_FileRow = Dict[str, Any]


def get_db_path(backend_dir: str) -> str:
    """Legacy helper kept for compatibility.

    The SQLite database is no longer used, but some callers still invoke this
    function while we phase out the old import sites. Returning the historical
    path keeps those callers from breaking while making it obvious that the
    value is unused.
    """
    return os.path.join(backend_dir, "db.sqlite3")


def _init_db(_: str) -> None:
    """Supabase manages the schema; nothing to initialize locally."""
    logger.info("Supabase is now the source of truth for file metadata; skipping local DB init.")


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


def _upsert_file_record(
    *args: Any,
    created_by: Optional[str] = None,
) -> Dict[str, Any]:
    """Store or refresh file metadata inside Supabase."""
    if len(args) == 3:
        path, backend_dir, classify_func = args
    elif len(args) == 4:
        # Legacy signature included an unused DB path as the first argument.
        _, path, backend_dir, classify_func = args
    else:
        raise TypeError(
            "_upsert_file_record expected (path, backend_dir, classify_func)"
            " or (db_path, path, backend_dir, classify_func)"
        )

    client = get_supabase_client()

    stat = os.stat(path)
    name = os.path.basename(path)
    size = stat.st_size
    upload_date = datetime.fromtimestamp(stat.st_mtime).isoformat()
    file_type = os.path.splitext(path)[1].lstrip(".").lower() or "unknown"
    rel_path = os.path.relpath(path, backend_dir)

    struct_flag, category = classify_func(path)
    payload = {
        "name": name,
        "size": size,
        "upload_date": upload_date,
        "file_type": file_type,
        "rel_path": rel_path,
        "structure_ok": _structure_flag_to_bool(struct_flag),
        "category": category,
        "created_by": created_by,
    }

    # Remove keys with None so Supabase defaults/nullable columns behave normally.
    payload = {k: v for k, v in payload.items() if v is not None}

    response = client.table("files").upsert(payload, on_conflict="name").select("*").execute()
    if response.error:
        raise RuntimeError(f"Failed to upsert file metadata for {name}: {response.error}")

    row = response.data[0] if response.data else payload
    return _normalize_file_row(row)


def _delete_file_record(*args: Any) -> None:
    if len(args) == 1:
        name = args[0]
    elif len(args) == 2:
        _, name = args
    else:
        raise TypeError("_delete_file_record expected name or (db_path, name)")
    client = get_supabase_client()
    response = client.table("files").delete().eq("name", name).execute()
    if response.error:
        raise RuntimeError(f"Failed to delete file metadata for {name}: {response.error}")

def _list_files_db(*_args: Any) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    response = client.table("files").select("*").order("name").execute()
    if response.error:
        raise RuntimeError(f"Failed to fetch file metadata: {response.error}")
    return [_normalize_file_row(row) for row in response.data]


def _get_file_record_by_id(file_id: int) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    response = (
        client.table("files").select("*").eq("id", file_id).limit(1).execute()
    )
    if response.error:
        raise RuntimeError(f"Failed to fetch file id={file_id}: {response.error}")
    if not response.data:
        return None
    return _normalize_file_row(response.data[0])


def _get_file_by_name_or_relpath(identifier: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    # Try by name first.
    response = client.table("files").select("*").eq("name", identifier).limit(1).execute()
    if response.error:
        raise RuntimeError(
            f"Failed to fetch file by identifier '{identifier}': {response.error}"
        )
    if response.data:
        return _normalize_file_row(response.data[0])

    response = (
        client.table("files").select("*").eq("rel_path", identifier).limit(1).execute()
    )
    if response.error:
        raise RuntimeError(
            f"Failed to fetch file by identifier '{identifier}': {response.error}"
        )
    if not response.data:
        return None
    return _normalize_file_row(response.data[0])


def _delete_files_with_prefix(prefix: str) -> int:
    """Delete all file rows whose stored rel_path starts with the prefix."""
    client = get_supabase_client()
    selector = client.table("files").select("id").like("rel_path", f"{prefix}%")
    preview = selector.execute()
    if preview.error:
        raise RuntimeError(f"Failed to preview files for deletion: {preview.error}")
    ids = [row["id"] for row in preview.data]
    if not ids:
        return 0
    response = client.table("files").delete().in_("id", ids).execute()
    if response.error:
        raise RuntimeError(f"Failed to delete files for prefix {prefix}: {response.error}")
    return len(ids)


def _set_structure_flag(file_id: int, value: bool) -> None:
    client = get_supabase_client()
    response = client.table("files").update({"structure_ok": value}).eq("id", file_id).execute()
    if response.error:
        raise RuntimeError(
            f"Failed to update structure flag for file {file_id}: {response.error}"
        )
