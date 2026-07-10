from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import sys
import json
import sqlite3
import shutil
import time
import re
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime
import httpx

from dotenv import load_dotenv
from postgrest.exceptions import APIError

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
for env_path in (os.path.join(ROOT_DIR, ".env"), os.path.join(BACKEND_DIR, ".env")):
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        break

from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

try:
    # Works when running as package import (e.g. `uvicorn backend.main:app`)
    from .supabase_client import (
        get_jwks,
        get_supabase_anon_key,
        get_supabase_client,
        get_supabase_url,
    )
except ImportError:
    # Works when running from backend dir (e.g. `uvicorn main:app`)
    from supabase_client import (
        get_jwks,
        get_supabase_anon_key,
        get_supabase_client,
        get_supabase_url,
    )

# Add backend directory to Python path so we can import scripts module
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Now we can import from scripts
from scripts.llm_calls import transform_discussion_json, generate_user_bio, generate_message_rewrite

try:
    from .database import (
        _delete_file_record as supabase_delete_file_record,
        _delete_file_record_by_id as supabase_delete_file_record_by_id,
        _delete_files_with_prefix,
        _get_file_by_name_or_relpath,
        _get_file_record_by_id,
        _list_files_db as supabase_list_files_db,
        _set_structure_flag,
        _upsert_file_metadata as supabase_upsert_file_metadata,
        _upsert_file_record as supabase_upsert_file_record,
    )
    from .file_storage import (
        ALLOWED_UPLOAD_EXTS,
        db_rel_path,
        delete_object,
        delete_prefix,
        download_bytes,
        list_all_folder_names,
        list_folder_names,
        move_object,
        normalize_user_rel_path,
        public_path_from_storage_key,
        storage_key,
        storage_key_from_record,
        upload_bytes,
        walk_user_files,
    )
except ImportError:
    from database import (
        _delete_file_record as supabase_delete_file_record,
        _delete_file_record_by_id as supabase_delete_file_record_by_id,
        _delete_files_with_prefix,
        _get_file_by_name_or_relpath,
        _get_file_record_by_id,
        _list_files_db as supabase_list_files_db,
        _set_structure_flag,
        _upsert_file_metadata as supabase_upsert_file_metadata,
        _upsert_file_record as supabase_upsert_file_record,
    )
    from file_storage import (
        ALLOWED_UPLOAD_EXTS,
        db_rel_path,
        delete_object,
        delete_prefix,
        download_bytes,
        list_all_folder_names,
        list_folder_names,
        move_object,
        normalize_user_rel_path,
        public_path_from_storage_key,
        storage_key,
        storage_key_from_record,
        upload_bytes,
        walk_user_files,
    )

# FastAPI app
app = FastAPI()

# Configuration
# Use the already computed absolute BACKEND_DIR (set earlier using
# os.path.dirname(os.path.abspath(__file__))). Avoid reassigning to
# os.path.dirname(__file__) which can be a relative path depending on
# how the application is started (this caused incorrect FILES_ROOT
# resolution and 'file not found' errors).
FILES_ROOT = os.path.join(BACKEND_DIR, 'files_root')
if not os.path.exists(FILES_ROOT):
    os.makedirs(FILES_ROOT, exist_ok=True)
    # Log when we create the folder so startup logs contain useful info
    logger = logging.getLogger('uvicorn.error')
    logger.error(f"Created FILES_ROOT directory at: {FILES_ROOT}")
else:
    logger = logging.getLogger('uvicorn.error')
    logger.info(f"Using existing FILES_ROOT: {FILES_ROOT}")
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Log resolved paths for easier debugging
logger = logging.getLogger('uvicorn.error')
logger.info(f"BACKEND_DIR={BACKEND_DIR} FILES_ROOT={FILES_ROOT}")

# Supabase Auth configuration
SUPABASE_URL = get_supabase_url()
SUPABASE_AUTH_URL = f"{SUPABASE_URL.rstrip('/')}/auth/v1"
logger.info("Supabase auth host: %s", SUPABASE_URL.replace("https://", "").replace("http://", "").split("/")[0])
auth_scheme = HTTPBearer(auto_error=False)

# LLM configuration (available model choices for the UI and defaults)
LLM_PROVIDERS: List[str] = ["groq", "openai"]
DEFAULT_LLM_PROVIDER: str = "groq"
AVAILABLE_LLM_MODELS: Dict[str, List[str]] = {
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
    ],
    "openai": [
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4o",
        "gpt-4o-mini",
    ],
}
# Map retired or renamed model IDs to current supported ones.
LEGACY_MODEL_ALIASES: Dict[str, str] = {
    "meta-llama/llama-4-maverick-17b-128e-instruct": "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768": "llama-3.3-70b-versatile",
    "gpt-4-turbo": "gpt-4.1",
    "gpt-4-turbo-2024-04-09": "gpt-4.1",
    "gpt-3.5-turbo": "gpt-4o-mini",
}
DEFAULT_LLM_MODEL_BY_PROVIDER: Dict[str, str] = {
    provider: models[0] for provider, models in AVAILABLE_LLM_MODELS.items()
}
LLM_PROVIDER_LABELS: Dict[str, str] = {
    "groq": "Groq",
    "openai": "OpenAI",
}




def _build_supabase_auth_headers(*, use_service: bool = False) -> Dict[str, str]:
    if use_service:
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY must be set for Supabase admin auth")
    else:
        key = get_supabase_anon_key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


async def _supabase_auth_post(path: str, payload: Dict[str, Any], *, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    auth_base = f"{get_supabase_url().rstrip('/')}/auth/v1"
    url = f"{auth_base}{path}"
    headers = _build_supabase_auth_headers()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, headers=headers, params=params, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Supabase auth request failed: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text
        try:
            payload_json = response.json()
            detail = (
                payload_json.get("msg")
                or payload_json.get("message")
                or payload_json.get("error_description")
                or detail
            )
        except Exception:
            pass
        if response.status_code == 429:
            detail = detail or "Too many auth attempts. Please wait a few minutes and try again."
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


def _decode_supabase_token(token: str) -> Dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header") from exc

    kid = header.get("kid")
    try:
        jwks = get_jwks()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify auth token with Supabase",
        ) from exc
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown token key")

    public_key = jwk.construct(key)
    try:
        message, encoded_sig = token.rsplit('.', 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token") from exc

    decoded_sig = base64url_decode(encoded_sig.encode('utf-8'))
    if not public_key.verify(message.encode('utf-8'), decoded_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

    claims = jwt.get_unverified_claims(token)
    exp = claims.get("exp")
    if exp and time.time() > exp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    return claims


def _build_user_from_claims(claims: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": claims.get("sub"),
        "email": claims.get("email") or (claims.get("user_metadata") or {}).get("email"),
        "role": claims.get("role"),
        "app_metadata": claims.get("app_metadata", {}),
        "user_metadata": claims.get("user_metadata", {}),
    }


DEFAULT_ANNOTATION_SCHEMA: Dict[str, Any] = {
    "version": 1,
    "messageFields": [
        {
            "id": "labels",
            "label": "Labels",
            "type": "labels",
            "options": [
                "Support",
                "Attack",
                "Question",
                "Clarification",
                "Neutral",
                "Off-topic",
            ],
        },
        {"id": "rating", "label": "Quality rating", "type": "rating"},
        {
            "id": "note",
            "label": "Notes",
            "type": "textarea",
            "placeholder": "Add notes about this turn (stance, argument type, issues…)",
        },
    ],
    "conversationFields": [
        {
            "id": "overallNote",
            "label": "Overall notes",
            "type": "textarea",
            "placeholder": "Summary, quality assessment, or remarks about the whole conversation",
        },
    ],
}


def _normalize_annotation_field(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    field_type = raw.get("type")
    valid_types = {"labels", "text", "textarea", "rating", "select", "number"}
    if field_type not in valid_types:
        return None
    field_id = str(raw.get("id") or "").strip()
    label = str(raw.get("label") or "").strip()
    if not field_id or not label:
        return None
    options = raw.get("options")
    normalized_options = (
        [str(item).strip() for item in options if str(item).strip()]
        if isinstance(options, list)
        else []
    )
    field: Dict[str, Any] = {
        "id": field_id,
        "label": label,
        "type": field_type,
    }
    if field_type in ("labels", "select"):
        field["options"] = normalized_options
    elif normalized_options:
        field["options"] = normalized_options
    placeholder = raw.get("placeholder")
    if isinstance(placeholder, str) and placeholder.strip():
        field["placeholder"] = placeholder.strip()
    if raw.get("required") is True:
        field["required"] = True
    return field


def _normalize_annotation_schema(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return json.loads(json.dumps(DEFAULT_ANNOTATION_SCHEMA))

    raw_message_fields = raw.get("messageFields")
    message_fields: List[Dict[str, Any]] = []
    if isinstance(raw_message_fields, list):
        for item in raw_message_fields:
            field = _normalize_annotation_field(item)
            if field:
                message_fields.append(field)

    raw_conversation_fields = raw.get("conversationFields")
    conversation_fields: List[Dict[str, Any]] = []
    if isinstance(raw_conversation_fields, list):
        for item in raw_conversation_fields:
            field = _normalize_annotation_field(item)
            if field:
                conversation_fields.append(field)

    if not message_fields and not conversation_fields:
        return json.loads(json.dumps(DEFAULT_ANNOTATION_SCHEMA))

    return {
        "version": 1,
        "messageFields": message_fields,
        "conversationFields": conversation_fields,
    }


_USER_SETTINGS_HAS_ANNOTATION_SCHEMA: Optional[bool] = None


def _user_settings_select_columns() -> str:
    base = "api_key, model, provider, created_at, updated_at"
    if _USER_SETTINGS_HAS_ANNOTATION_SCHEMA is not False:
        return f"{base}, annotation_schema"
    return base


def _mark_annotation_schema_unavailable() -> None:
    global _USER_SETTINGS_HAS_ANNOTATION_SCHEMA
    _USER_SETTINGS_HAS_ANNOTATION_SCHEMA = False
    logger.warning(
        "user_settings.annotation_schema column is missing. "
        "Update DATABASE_IPv4_URL to match SUPABASE_URL, then run: "
        "python backend/scripts/setup_db.py"
    )


def _is_missing_annotation_schema_error(exc: APIError) -> bool:
    message = str(getattr(exc, "message", "") or "")
    code = str(getattr(exc, "code", "") or "")
    return code == "42703" and "annotation_schema" in message


def _extract_supabase_project_ref(url: str) -> Optional[str]:
    match = re.search(r"https?://([^.]+)\.supabase\.co", url or "")
    return match.group(1) if match else None


def _extract_database_project_ref(database_url: str) -> Optional[str]:
    match = re.search(r"postgres(?:ql)?://postgres\.([^:@/]+)", database_url or "")
    return match.group(1) if match else None


def _ensure_annotation_schema_column() -> None:
    global _USER_SETTINGS_HAS_ANNOTATION_SCHEMA

    database_url = os.getenv("DATABASE_IPv4_URL") or os.getenv("DATABASE_URL")
    if not database_url or database_url.startswith("https://"):
        return

    supabase_ref = _extract_supabase_project_ref(get_supabase_url())
    db_ref = _extract_database_project_ref(database_url)
    if not supabase_ref or not db_ref or supabase_ref != db_ref:
        logger.info(
            "Skipping annotation_schema migration: DATABASE URL project (%s) != SUPABASE_URL project (%s)",
            db_ref,
            supabase_ref,
        )
        return

    try:
        import psycopg2
    except ImportError:
        logger.warning("psycopg2 not installed; cannot auto-create annotation_schema column")
        return

    try:
        with psycopg2.connect(database_url) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(
                    "ALTER TABLE public.user_settings "
                    "ADD COLUMN IF NOT EXISTS annotation_schema jsonb;"
                )
        _USER_SETTINGS_HAS_ANNOTATION_SCHEMA = True
        logger.info("Ensured user_settings.annotation_schema column exists.")
    except Exception as exc:
        logger.warning("Could not ensure annotation_schema column: %s", exc)


def _get_user_settings(user_id: str) -> Optional[Dict[str, Any]]:
    global _USER_SETTINGS_HAS_ANNOTATION_SCHEMA
    client = get_supabase_client()
    try:
        response = (
            client.table("user_settings")
            .select(_user_settings_select_columns())
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if (
            _USER_SETTINGS_HAS_ANNOTATION_SCHEMA is None
            and "annotation_schema" in _user_settings_select_columns()
        ):
            _USER_SETTINGS_HAS_ANNOTATION_SCHEMA = True
    except APIError as exc:
        if (
            _is_missing_annotation_schema_error(exc)
            and _USER_SETTINGS_HAS_ANNOTATION_SCHEMA is not False
        ):
            _mark_annotation_schema_unavailable()
            return _get_user_settings(user_id)
        raise

    if not response.data:
        return None
    return response.data[0]


def _normalize_provider(provider: Optional[str]) -> str:
    normalized = (provider or DEFAULT_LLM_PROVIDER).strip().lower()
    if normalized not in LLM_PROVIDERS:
        return DEFAULT_LLM_PROVIDER
    return normalized


def _normalize_model(provider: str, model: Optional[str]) -> str:
    provider_models = AVAILABLE_LLM_MODELS.get(provider, [])
    default_model = DEFAULT_LLM_MODEL_BY_PROVIDER[provider]
    selected = (model or default_model).strip()
    selected = LEGACY_MODEL_ALIASES.get(selected, selected)
    if selected not in provider_models:
        return default_model
    return selected


def _resolve_user_llm_settings(user_id: str) -> Dict[str, str]:
    settings = _get_user_settings(user_id) or {}
    provider = _normalize_provider(settings.get("provider"))
    api_key = (settings.get("api_key") or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="LLM API key not configured. Add one in Settings → API Settings.",
        )
    model = _normalize_model(provider, settings.get("model"))
    return {"provider": provider, "api_key": api_key, "model": model}


def _upsert_user_settings(
    user_id: str,
    api_key: Optional[str],
    model: Optional[str],
    provider: Optional[str] = None,
) -> None:
    client = get_supabase_client()
    payload = {
        "user_id": user_id,
        "api_key": api_key,
        "model": model,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if provider is not None:
        payload["provider"] = _normalize_provider(provider)
    client.table("user_settings").upsert(payload, on_conflict="user_id").execute()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
) -> Dict[str, Any]:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = _decode_supabase_token(credentials.credentials)
    user = _build_user_from_claims(claims)
    if not user.get("id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Supabase token")
    return user


def _classify_json(data: Any) -> Tuple[Optional[int], Optional[str]]:
    def valid_node(node: Any) -> bool:
        if not isinstance(node, dict):
            return False
        required = ('id', 'speaker', 'text', 'children')
        if any(key not in node for key in required):
            return False
        if not isinstance(node.get('id'), str):
            return False
        if not isinstance(node.get('speaker'), str):
            return False
        if not isinstance(node.get('text'), str):
            return False
        if not isinstance(node.get('children'), list):
            return False
        return all(valid_node(child) for child in node.get('children'))

    if isinstance(data, dict) and all(k in data for k in ('fileRef', 'users', 'tree', 'discussion')):
        tree_ok = isinstance(data.get('tree'), dict) and valid_node(data['tree'])
        discussion_ok = isinstance(data.get('discussion'), list)
        if tree_ok and discussion_ok:
            return 1, 'draft'
        return 0, 'invalid'

    if isinstance(data, dict) and all(k in data for k in ('users', 'tree')):
        tree_ok = isinstance(data.get('tree'), dict) and valid_node(data['tree'])
        users_ok = isinstance(data.get('users'), list)
        if tree_ok and users_ok:
            return 1, 'discussion'
        return 0, 'invalid'

    return 0, 'invalid'


def _classify_bytes(content: bytes, filename: str) -> Tuple[Optional[int], Optional[str]]:
    if not filename.lower().endswith('.json'):
        return None, None
    try:
        data = json.loads(content.decode('utf-8'))
    except Exception:
        return 0, 'invalid'
    return _classify_json(data)


def _classify_file(full_path: str) -> Tuple[Optional[int], Optional[str]]:
    if not full_path.lower().endswith('.json'):
        return None, None
    try:
        with open(full_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        return 0, 'invalid'
    return _classify_json(data)


def _require_user_id(current_user: Dict[str, Any]) -> str:
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")
    return user_id


def _record_storage_key(record: Dict[str, Any], user_id: str) -> str:
    raw = record.get("path") or record.get("rel_path") or record.get("name") or ""
    return storage_key_from_record(str(raw), user_id)


def _public_file_record(record: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    public = dict(record)
    key = _record_storage_key(record, user_id)
    public["path"] = public_path_from_storage_key(key, user_id)
    return public


def _annotation_status_from_bytes(content: bytes) -> Optional[str]:
    try:
        from file_utils import _annotation_status_from_json
    except ImportError:
        from .file_utils import _annotation_status_from_json

    try:
        data = json.loads(content.decode("utf-8"))
    except Exception:
        return None
    return _annotation_status_from_json(data)


def _enrich_file_record(
    record: Dict[str, Any],
    user_id: str,
    content: Optional[bytes] = None,
) -> Dict[str, Any]:
    public = _public_file_record(record, user_id)
    name = public.get("name") or ""
    if not str(name).lower().endswith(".json"):
        public["annotation_status"] = None
        return public

    try:
        payload = content if content is not None else _download_record_bytes(record, user_id)
        public["annotation_status"] = _annotation_status_from_bytes(payload)
    except Exception:
        public["annotation_status"] = None
    return public


def _upsert_storage_file(
    user_id: str,
    rel_path: str,
    content: bytes,
    *,
    filename: Optional[str] = None,
) -> Dict[str, Any]:
    name = filename or os.path.basename(normalize_user_rel_path(rel_path) or rel_path)
    try:
        object_key = upload_bytes(user_id, rel_path, content, filename=name)
    except Exception as exc:
        logger.error("Failed to upload %s for user %s: %s", rel_path, user_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    file_type = os.path.splitext(name)[1].lstrip(".").lower() or "unknown"
    struct_flag, category = _classify_bytes(content, name)
    structure_ok = bool(struct_flag) if struct_flag is not None else None
    try:
        return supabase_upsert_file_metadata(
            name=name,
            size=len(content),
            rel_path=object_key,
            file_type=file_type,
            created_by=user_id,
            structure_ok=structure_ok,
            category=category,
        )
    except Exception as exc:
        logger.error("Failed to upsert metadata for %s: %s", object_key, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _download_record_bytes(record: Dict[str, Any], user_id: str) -> bytes:
    return download_bytes(_record_storage_key(record, user_id))


def _file_content_response(content: bytes, filename: str, *, download: bool = False):
    from fastapi.responses import Response

    if download:
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{os.path.basename(filename)}"'},
        )
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".json":
        try:
            return JSONResponse(content=json.loads(content.decode("utf-8")))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Failed to parse JSON: {exc}") from exc
    if ext == ".pkl":
        return {
            "message": "This is a Python pickle file. Use the download endpoint to retrieve it or process it on the server."
        }
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{os.path.basename(filename)}"'},
    )


def _record_in_folder(record: Dict[str, Any], user_id: str, folder: Optional[str]) -> bool:
    public_path = _public_file_record(record, user_id)["path"]
    if not folder:
        return "/" not in public_path
    folder_norm = normalize_user_rel_path(folder)
    if public_path == folder_norm:
        return True
    return public_path.startswith(folder_norm + "/")


def _sync_storage_entries(user_id: str, folder: Optional[str] = None) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for object_key in walk_user_files(user_id, folder or ""):
        ext = os.path.splitext(object_key)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXTS:
            continue
        content = download_bytes(object_key)
        public_path = public_path_from_storage_key(object_key, user_id)
        rec = _upsert_storage_file(
            user_id,
            public_path,
            content,
            filename=os.path.basename(object_key),
        )
        entries.append(_enrich_file_record(rec, user_id, content))
    return entries


def _delete_file_record(name: str, *, user_id: str) -> None:
    try:
        supabase_delete_file_record(name, user_id=user_id)
    except Exception as exc:
        logger.error("Failed to delete metadata for %s: %s", name, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _delete_file_record_by_id(file_id: int, *, user_id: str) -> None:
    try:
        supabase_delete_file_record_by_id(file_id, user_id)
    except Exception as exc:
        logger.error("Failed to delete metadata id=%s: %s", file_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _list_files_db(user_id: str) -> List[Dict[str, Any]]:
    try:
        return supabase_list_files_db(user_id)
    except Exception as exc:
        logger.error("Failed to list files: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _load_file_record(identifier: Any, *, user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a file record by numeric id or stored name/path for the given user."""
    try:
        file_id = int(identifier)
    except (TypeError, ValueError):
        file_id = None

    try:
        if file_id is not None:
            return _get_file_record_by_id(file_id, user_id)
        return _get_file_by_name_or_relpath(str(identifier), user_id)
    except Exception as exc:
        logger.error("Failed to load metadata for %s: %s", identifier, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Allow frontend (Vue) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount files_root for direct static serving (useful for images/graphics)
app.mount("/files", StaticFiles(directory=FILES_ROOT), name="files")
# keep original backend static mount as well
app.mount("/static-backend", StaticFiles(directory=BACKEND_DIR), name="static-backend")


@app.on_event("startup")
async def ensure_annotation_schema_column() -> None:
    _ensure_annotation_schema_column()


def _safe_path(rel_path: str) -> str:
    """Return a safe absolute path inside FILES_ROOT for the given relative path.

    Prevents path traversal. Accepts nested relative paths like 'graphics/img.png'.
    Absolute paths are rejected.
    """
    if os.path.isabs(rel_path):
        raise HTTPException(status_code=400, detail="Absolute paths are not allowed")
    # normalize and join against FILES_ROOT
    full = os.path.normpath(os.path.join(FILES_ROOT, rel_path))
    files_root_norm = os.path.normpath(FILES_ROOT)
    # ensure the resulting path is inside FILES_ROOT
    if not (full == files_root_norm or full.startswith(files_root_norm + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid or unsafe path")
    return full


@app.post("/api/auth/register")
async def register_user(request: Request):
    """Register a new Supabase user via the backend proxy."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    email = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    payload = {"email": email, "password": password}
    supabase_response = await _supabase_auth_post("/signup", payload)
    logger.info(f"Response from Supabase signup for {email}: {supabase_response}")
    return supabase_response


@app.post("/api/auth/login")
async def login_user(request: Request):
    """Authenticate a user through Supabase and return the issued tokens."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    email = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    payload = {"email": email, "password": password}
    logger.debug(f"Attempting login for credent: {email}")
    supabase_response = await _supabase_auth_post(
        "/token",
        payload,
        params={"grant_type": "password"},
    )
    return supabase_response


@app.post("/api/auth/refresh")
async def refresh_auth_token(request: Request):
    """Exchange a Supabase refresh token for a new access token."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    refresh_token = (body.get("refresh_token") or "").strip()
    if not refresh_token:
        raise HTTPException(status_code=400, detail="refresh_token is required")

    supabase_response = await _supabase_auth_post(
        "/token",
        {"refresh_token": refresh_token},
        params={"grant_type": "refresh_token"},
    )
    return supabase_response


@app.get("/api/auth/me")
async def read_current_user(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return the currently authenticated user based on the Bearer token."""
    return {"user": current_user}


@app.get("/api/settings")
async def get_settings(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return the current user's LLM-related settings.

    The response intentionally does not include the stored API key – only a
    boolean flag is exposed so the client knows whether a key is configured.
    """
    settings = _get_user_settings(current_user["id"])
    provider = _normalize_provider((settings or {}).get("provider"))
    model = _normalize_model(provider, (settings or {}).get("model"))
    has_api_key = bool((settings or {}).get("api_key"))
    return {
        "provider": provider,
        "model": model,
        "hasApiKey": has_api_key,
        "availableModels": AVAILABLE_LLM_MODELS[provider],
        "availableProviders": [
            {"id": provider_id, "label": LLM_PROVIDER_LABELS[provider_id]}
            for provider_id in LLM_PROVIDERS
        ],
        "modelsByProvider": AVAILABLE_LLM_MODELS,
    }


@app.post("/api/settings")
async def update_settings(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Update the current user's LLM API key, provider, and preferred model.

    Expects JSON body with optional keys:
      - apiKey: string (empty string clears the stored key)
      - provider: string ("groq" or "openai")
      - model: string (one of the selected provider's available models)
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    api_key_raw = body.get("apiKey")
    model_raw = body.get("model")
    provider_raw = body.get("provider")

    existing = _get_user_settings(current_user["id"]) or {}

    provider = _normalize_provider(provider_raw if provider_raw is not None else existing.get("provider"))

    api_key: Optional[str]
    if api_key_raw is None:
        api_key = existing.get("api_key")
    else:
        api_key = api_key_raw.strip() or None

    if model_raw is None:
        model = _normalize_model(provider, existing.get("model"))
    else:
        model = _normalize_model(provider, str(model_raw).strip() or None)

    if model not in AVAILABLE_LLM_MODELS[provider]:
        raise HTTPException(status_code=400, detail="Unsupported model selection for the chosen provider")

    _upsert_user_settings(current_user["id"], api_key, model, provider)

    return {
        "success": True,
        "provider": provider,
        "model": model,
        "hasApiKey": bool(api_key),
        "availableModels": AVAILABLE_LLM_MODELS[provider],
    }


@app.get("/api/settings/annotation-schema")
async def get_annotation_schema(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return the current user's annotation field schema."""
    settings = _get_user_settings(current_user["id"]) or {}
    stored = settings.get("annotation_schema")
    schema = _normalize_annotation_schema(stored)
    return {"schema": schema}


@app.put("/api/settings/annotation-schema")
async def update_annotation_schema(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update the current user's annotation field schema."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    schema = _normalize_annotation_schema(body.get("schema"))
    if _USER_SETTINGS_HAS_ANNOTATION_SCHEMA is False:
        raise HTTPException(
            status_code=503,
            detail=(
                "Annotation schema storage is not available yet. "
                "Set DATABASE_IPv4_URL to your Supabase Postgres URI (same project as SUPABASE_URL), "
                "then run: python backend/scripts/setup_db.py"
            ),
        )

    client = get_supabase_client()
    existing = _get_user_settings(current_user["id"]) or {}
    payload = {
        "user_id": current_user["id"],
        "api_key": existing.get("api_key"),
        "model": existing.get("model"),
        "provider": _normalize_provider(existing.get("provider")),
        "annotation_schema": schema,
        "updated_at": datetime.utcnow().isoformat(),
    }
    try:
        client.table("user_settings").upsert(payload, on_conflict="user_id").execute()
    except APIError as exc:
        if _is_missing_annotation_schema_error(exc):
            _mark_annotation_schema_unavailable()
            raise HTTPException(
                status_code=503,
                detail=(
                    "Annotation schema storage is not available yet. "
                    "Set DATABASE_IPv4_URL to your Supabase Postgres URI (same project as SUPABASE_URL), "
                    "then run: python backend/scripts/setup_db.py"
                ),
            ) from exc
        raise
    return {"success": True, "schema": schema}


def _resolve_stored_relpath(relpath: str) -> str:
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
        candidate = os.path.normpath(os.path.join(FILES_ROOT, stripped))
        return candidate
    # fallback: if stored path looks like an absolute path under BACKEND_DIR, join with BACKEND_DIR
    candidate_backend = os.path.normpath(os.path.join(BACKEND_DIR, rp))
    if os.path.exists(candidate_backend):
        return candidate_backend
    # final fallback: interpret as path under FILES_ROOT
    return os.path.normpath(os.path.join(FILES_ROOT, rp))





def _atomic_write_json(full_path: str, data: any, ensure_ascii: bool = False) -> None:
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


@app.get("/api/files")
def list_files(
    folder: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """List files owned by the authenticated user."""
    user_id = _require_user_id(current_user)
    rows = _list_files_db(user_id)

    def fill_defaults(file_row: Dict[str, Any]) -> Dict[str, Any]:
        if not file_row.get("type"):
            file_row["type"] = "json"
        if not file_row.get("uploadDate"):
            file_row["uploadDate"] = datetime.now().isoformat()
        return file_row

    if rows:
        filtered = [r for r in rows if _record_in_folder(r, user_id, folder)]
        return [fill_defaults(_enrich_file_record(r, user_id)) for r in filtered]

    return _sync_storage_entries(user_id, folder)


@app.get('/api/files/id/{file_id}')
def get_file_by_id(
    file_id: int,
    download: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return file metadata or JSON content when targeting by numeric id."""
    user_id = _require_user_id(current_user)
    record = _load_file_record(file_id, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail='File not found')

    try:
        content = _download_record_bytes(record, user_id)
    except Exception as exc:
        logger.error("get_file_by_id: failed to download id=%s: %s", file_id, exc)
        raise HTTPException(status_code=404, detail='File not found') from exc

    filename = record.get("name") or str(file_id)
    return _file_content_response(content, filename, download=download)


@app.get("/api/files/{filename:path}")
def get_file(
    filename: str,
    download: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return file content for files owned by the authenticated user."""
    user_id = _require_user_id(current_user)
    record = _load_file_record(filename, user_id=user_id)
    if not record:
        try:
            object_key = storage_key(user_id, filename)
            content = download_bytes(object_key)
            return _file_content_response(content, filename, download=download)
        except Exception:
            raise HTTPException(status_code=404, detail="File not found")

    try:
        content = _download_record_bytes(record, user_id)
    except Exception as exc:
        logger.error("get_file: failed to download %s: %s", filename, exc)
        raise HTTPException(status_code=404, detail="File not found") from exc

    name = record.get("name") or filename
    return _file_content_response(content, name, download=download)


@app.patch('/api/files/id/{file_id}')
async def save_changes_file_by_id(
    file_id: int,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Save changes to a JSON file identified by numeric id."""
    user_id = _require_user_id(current_user)
    record = _load_file_record(file_id, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail='File not found')

    filename = record.get("name") or str(file_id)
    if not filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail='Only JSON files can be modified via this endpoint')

    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Invalid JSON body: {e}')

    public_path = _public_file_record(record, user_id)["path"]
    content = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    try:
        rec = _upsert_storage_file(user_id, public_path, content, filename=filename)
    except Exception as e:
        logger.error("save_changes_file_by_id: failed to upload id=%s: %s", file_id, e)
        raise HTTPException(status_code=500, detail=f'Failed to save JSON file: {e}') from e
    return {"message": "Saved", "file": _enrich_file_record(rec, user_id, content)}


@app.patch('/api/files/{filename:path}')
async def save_changes_file_by_name(
    filename: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Save changes to a JSON file identified by filename inside the user's storage."""
    user_id = _require_user_id(current_user)
    if not filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail='Only JSON files can be modified via this endpoint')

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Invalid JSON body: {e}')

    users = body.get('users') if isinstance(body, dict) else None
    record = _load_file_record(filename, user_id=user_id)

    if record:
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail='Request body must be a JSON object')
        # Legacy partial update: only replace the users array when that is the sole field.
        if set(body.keys()) == {'users'}:
            try:
                existing = json.loads(_download_record_bytes(record, user_id).decode("utf-8"))
            except Exception:
                raise HTTPException(status_code=400, detail='Target exists but is not valid JSON')
            if not isinstance(existing, dict):
                raise HTTPException(status_code=400, detail='Target JSON is not an object; cannot insert users')
            existing['users'] = users
            to_write = existing
        else:
            to_write = body
        public_path = _public_file_record(record, user_id)["path"]
    else:
        if not isinstance(users, list):
            raise HTTPException(status_code=400, detail='Target does not exist; provide a "users" array to create it')
        to_write = {'users': users}
        public_path = normalize_user_rel_path(filename)

    content = json.dumps(to_write, indent=2, ensure_ascii=False).encode("utf-8")
    try:
        rec = _upsert_storage_file(user_id, public_path, content, filename=os.path.basename(public_path))
    except Exception as e:
        logger.error("save_changes_file_by_name: failed to upload %s: %s", filename, e)
        raise HTTPException(status_code=500, detail=f'Failed to save JSON file: {e}') from e
    saved = _enrich_file_record(rec, user_id, content)
    return {"message": "Saved", "file": saved}


@app.delete('/api/files/id/{file_id}')
def delete_file_by_id(
    file_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    user_id = _require_user_id(current_user)
    record = _load_file_record(file_id, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail='File not found')
    name = record.get('name') or str(file_id)
    try:
        delete_object(_record_storage_key(record, user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to remove file: {e}') from e
    _delete_file_record_by_id(file_id, user_id=user_id)
    return {"message": "Deleted", "file": name, "id": file_id}


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    path: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Upload a file into the authenticated user's Supabase Storage area."""
    user_id = _require_user_id(current_user)
    if os.path.basename(file.filename) != file.filename:
        raise HTTPException(status_code=400, detail="Invalid upload filename")
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    rel_path = normalize_user_rel_path(path, filename) if path else filename
    try:
        content = await file.read()
        rec = _upsert_storage_file(user_id, rel_path, content, filename=filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}") from e

    if path:
        try:
            _sync_storage_entries(user_id, path)
        except Exception:
            pass
    return {"message": "Uploaded", "file": _public_file_record(rec, user_id)}


@app.delete("/api/files/{filename:path}")
def delete_file(
    filename: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    user_id = _require_user_id(current_user)
    record = _load_file_record(filename, user_id=user_id)
    if record:
        object_key = _record_storage_key(record, user_id)
        file_id = record.get("id")
        delete_name = record.get("name") or os.path.basename(filename)
    else:
        try:
            object_key = storage_key(user_id, filename)
            file_id = None
            delete_name = os.path.basename(filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        delete_object(object_key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc

    if file_id is not None:
        _delete_file_record_by_id(file_id, user_id=user_id)
    else:
        _delete_file_record(delete_name, user_id=user_id)
    return {"message": "Deleted", "file": filename, "id": file_id}


@app.post('/api/migrate-files')
def migrate_files(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Scan the authenticated user's storage bucket and populate/update metadata."""
    user_id = _require_user_id(current_user)
    entries = _sync_storage_entries(user_id)
    return {"migrated": len(entries), "files": entries}


@app.post('/api/files/save-draft/{filename:path}')
async def save_draft_file(
    filename: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new draft JSON file inside the authenticated user's storage."""
    user_id = _require_user_id(current_user)
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Invalid JSON body: {e}')

    payload = body.get('payload') if isinstance(body, dict) else None
    if payload is None:
        raise HTTPException(status_code=400, detail='Missing "payload" in request body')

    if not filename.lower().endswith('.json'):
        filename = filename + '.json'

    public_path = normalize_user_rel_path(filename)
    content = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    try:
        rec = _upsert_storage_file(user_id, public_path, content, filename=os.path.basename(public_path))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to write draft file: {e}') from e

    return {"message": "Draft saved", "file": _public_file_record(rec, user_id)}


@app.post('/api/files/move')
def move_files_endpoint(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Move files owned by the authenticated user to a destination folder."""
    user_id = _require_user_id(current_user)
    targets = data.get('targets') if isinstance(data, dict) else None
    dest = data.get('dest') if isinstance(data, dict) else ''
    if not targets or not isinstance(targets, list):
        raise HTTPException(status_code=400, detail='Missing or invalid targets')

    dest_rel = normalize_user_rel_path(dest) if dest else ""
    moved = []
    errors = []

    for t in targets:
        try:
            record = _load_file_record(t, user_id=user_id)
        except HTTPException as exc:
            errors.append({'target': t, 'error': exc.detail})
            continue
        except Exception as exc:
            errors.append({'target': t, 'error': str(exc)})
            continue

        if not record:
            errors.append({'target': t, 'error': 'not found in DB'})
            continue

        src_key = _record_storage_key(record, user_id)
        basename = os.path.basename(src_key)
        try:
            dest_public = normalize_user_rel_path(dest_rel, basename) if dest_rel else basename
            dest_key = storage_key(user_id, dest_public)
            move_object(src_key, dest_key)
            content = download_bytes(dest_key)
            rec = _upsert_storage_file(
                user_id,
                dest_public,
                content,
                filename=basename,
            )
            old_id = record.get("id")
            if old_id:
                _delete_file_record_by_id(old_id, user_id=user_id)
            moved.append({
                'target': t,
                'moved_to': _public_file_record(rec, user_id).get('path'),
                'id': rec.get('id'),
            })
        except Exception as e:
            errors.append({'target': t, 'error': str(e)})

    return {'moved': moved, 'errors': errors}


@app.get('/api/folders')
def list_folders(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Return folders inside the authenticated user's storage area."""
    user_id = _require_user_id(current_user)
    return {"folders": list_all_folder_names(user_id)}


@app.post('/api/folders')
def create_folder(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a folder inside the authenticated user's storage area."""
    user_id = _require_user_id(current_user)
    target = data.get('path') if isinstance(data, dict) else None
    if not target:
        raise HTTPException(status_code=400, detail='Missing path')
    try:
        normalize_user_rel_path(target)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"created": True, "path": target}


@app.delete('/api/folders/{folder_path:path}')
def delete_folder(
    folder_path: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a folder and its contents from the authenticated user's storage."""
    user_id = _require_user_id(current_user)
    if not folder_path or folder_path in ('.', '/'):
        raise HTTPException(status_code=400, detail='Cannot delete root folder')

    try:
        folder_norm = normalize_user_rel_path(folder_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        delete_prefix(user_id, folder_norm)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to remove folder: {e}') from e

    db_prefix = db_rel_path(user_id, folder_norm)
    try:
        removed = _delete_files_with_prefix(db_prefix, user_id)
    except RuntimeError as exc:
        logger.error("Failed to delete Supabase rows for prefix %s: %s", db_prefix, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"deleted": True, "path": folder_path, "db_files_removed": removed}


@app.get("/api/users/{discussion_file:path}")
def get_users(discussion_file: Optional[str] = None):
    """Return the users metadata.

    Priority order:
    1. If `discussion_file` param is provided, try to read that file under `files_root` and extract its "users" key.
    2. Scan `FILES_ROOT` for the first JSON file that contains a top-level "users" array and return it.
    3. Fall back to the legacy `bp_130_users.json` file (original behaviour).

    Note: do NOT use any implicit or hard-coded "default discussion" file. The endpoint
    will never attempt to load a single default discussion as a fallback.
    """

    # Helper to load users list from a JSON file path if present
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

    # Require explicit discussion file: do NOT scan or fall back to any default.
    if not discussion_file:
        raise HTTPException(status_code=400, detail="A discussion_file path must be provided")

    try:
        full = _safe_path(discussion_file)
    except HTTPException:
        # _safe_path already raises an HTTPException with appropriate status/detail
        raise

    users = _load_users_from_file(full)
    if users is None:
        if not os.path.exists(full):
            raise HTTPException(status_code=404, detail="Discussion file not found")
        # File exists but doesn't contain a top-level 'users' array
        raise HTTPException(status_code=404, detail="Provided discussion file does not contain a 'users' array")

    return JSONResponse(content={"users": users})


@app.get("/api/llm/health")
def llm_health_check():
    """Check if LLM module can be loaded."""
    return {"status": "ok", "message": "LLM module loaded", "providers": LLM_PROVIDERS}


@app.post('/api/llm/generate-bio')
async def api_generate_bio(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate a concise user biography paragraph from provided inputs.

    Expects JSON body with:
      - existing_bio: (optional) string with prior biographical description
      - messages: list of strings with the user's chat messages

    Returns JSON: { success: True, bio: <string> }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    existing_bio = body.get('existing_bio') or body.get('existing') or body.get('bio') or ""
    messages = body.get('messages') or body.get('chat_messages') or None

    if messages is None or not isinstance(messages, list):
        print("Messages format: ", type(messages)," Messages: ",messages)
        raise HTTPException(status_code=400, detail="'messages' must be provided as a list of strings")

    for i, m in enumerate(messages):
        if not isinstance(m, str):
            raise HTTPException(status_code=400, detail=f"messages[{i}] must be a string")

    try:
        llm_settings = _resolve_user_llm_settings(current_user["id"])
        bio = generate_user_bio(
            existing_bio,
            messages,
            provider=llm_settings["provider"],
            api_key=llm_settings["api_key"],
            model=llm_settings["model"],
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")

    return JSONResponse({"success": True, "bio": bio})


@app.post('/api/llm/rewrite-message')
async def api_rewrite_message(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Rewrite a single chat message using the LLM.

    Expects a JSON body with:
      - messageToRewrite: object with at least `text` (and optionally `speaker`, `addressees`)
      - treeUserMessages: optional list of strings (other messages by same speaker)
      - messagesInTheChat: optional list of strings for wider context

    Returns JSON: { success: True, rewritten: <string> }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    message = body.get('messageToRewrite') or body.get('message') or None
    speaker_profile = body.get('speakerProfile') or None
    chat_msgs = body.get('messagesInTheChat') or body.get('messages') or None
    # Optional rewriting parameters
    temperament = body.get('temperament') or None
    style = body.get('style') or None
    length = body.get('length') or None

    if message is None or not isinstance(message, dict):
        raise HTTPException(status_code=400, detail="'messageToRewrite' must be provided as an object with a 'text' field")

    text = message.get('text')
    if text is None or not isinstance(text, str):
        raise HTTPException(status_code=400, detail="message.text must be a string")

    # Validate optional arrays
    if speaker_profile is not None and not isinstance(speaker_profile, dict):
        raise HTTPException(status_code=400, detail="speakerProfile must be an object if provided")
    if chat_msgs is not None and not isinstance(chat_msgs, list):
        raise HTTPException(status_code=400, detail="messagesInTheChat must be a list of strings if provided")

    try:
        llm_settings = _resolve_user_llm_settings(current_user["id"])
        rewritten = generate_message_rewrite(
            message,
            speaker_profile=speaker_profile,
            messages_in_chat=chat_msgs,
            temperament=temperament,
            style=style,
            length=length,
            provider=llm_settings["provider"],
            api_key=llm_settings["api_key"],
            model=llm_settings["model"],
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")

    return JSONResponse({"success": True, "rewritten": rewritten})


@app.post("/api/files/fix/{file_id}/preview")
async def preview_file_fix(
    file_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Preview the LLM-suggested fix without applying it."""
    user_id = _require_user_id(current_user)
    record = _load_file_record(file_id, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")

    name = record.get('name') or str(file_id)
    try:
        content = _download_record_bytes(record, user_id)
        input_data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"File is not valid JSON: {str(e)}") from e
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}") from e

    try:
        llm_settings = _resolve_user_llm_settings(user_id)
        fixed_data = transform_discussion_json(
            input_data,
            provider=llm_settings["provider"],
            api_key=llm_settings["api_key"],
            model=llm_settings["model"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM transformation failed: {str(e)}") from e

    return {
        "success": True,
        "file_id": file_id,
        "file_name": name,
        "original": input_data,
        "fixed": fixed_data,
        "changes_count": len(fixed_data) if isinstance(fixed_data, list) else 1
    }


@app.post("/api/files/fix/{file_id}/apply")
async def apply_file_fix(
    file_id: int,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    user_id = _require_user_id(current_user)
    body = await request.json()
    fixed_data = body.get("fixed_data")
    overwrite = body.get("overwrite", False)
    if isinstance(fixed_data, str):
        try:
            fixed_data = json.loads(fixed_data)
        except Exception:
            pass
    record = _load_file_record(file_id, user_id=user_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")

    name = record.get('name') or str(file_id)
    public_path = _public_file_record(record, user_id)["path"]
    try:
        original_content = _download_record_bytes(record, user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {e}") from e

    backup_path = None
    backup_created = False
    new_file_id = file_id
    fixed_content = json.dumps(fixed_data, indent=2, ensure_ascii=False).encode("utf-8")

    if overwrite:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base, ext = os.path.splitext(public_path)
        backup_public = f"{base}.backup_{timestamp}{ext}"
        try:
            upload_bytes(user_id, backup_public, original_content, filename=os.path.basename(backup_public))
            backup_path = backup_public
            backup_created = True
        except Exception as e:
            logging.warning(f"Could not create backup: {e}")
        try:
            rec = _upsert_storage_file(user_id, public_path, fixed_content, filename=name)
        except Exception as e:
            if backup_created:
                try:
                    delete_object(storage_key(user_id, backup_public))
                except Exception:
                    pass
            raise HTTPException(status_code=500, detail=f"Error saving fixed file: {str(e)}") from e
        try:
            _set_structure_flag(file_id, True, user_id)
        except Exception as exc:
            logger.error("Failed to update structure flag for %s: %s", file_id, exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        new_file_id = rec.get("id", file_id)
    else:
        base, ext = os.path.splitext(name)
        new_name = f"{base}_fix{ext}"
        parent = os.path.dirname(public_path)
        new_public = normalize_user_rel_path(parent, new_name) if parent else new_name
        try:
            to_write = fixed_data if fixed_data not in (None, "", []) else {}
            new_content = json.dumps(to_write, indent=2, ensure_ascii=False).encode("utf-8")
            rec = _upsert_storage_file(user_id, new_public, new_content, filename=new_name)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving fixed file: {str(e)}") from e
        new_file_id = rec.get('id', file_id)

    return {
        "success": True,
        "message": "File successfully fixed and saved",
        "file_id": new_file_id,
        "backup_path": backup_path,
        "backup_created": backup_created,
        "overwrite": overwrite
    }


@app.post("/api/files/delete-backup")
async def delete_backup_file(
    request: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a backup file created during the fix process."""
    user_id = _require_user_id(current_user)
    backup_path = request.get("backup_path")

    if not backup_path:
        raise HTTPException(status_code=400, detail="backup_path is required")

    if ".backup_" not in backup_path:
        raise HTTPException(status_code=400, detail="Only backup files can be deleted through this endpoint")

    try:
        backup_public = normalize_user_rel_path(str(backup_path).lstrip("/"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if ".." in backup_public.split("/"):
        raise HTTPException(status_code=403, detail="Cannot delete files outside of your storage")

    object_key = storage_key(user_id, backup_public)
    try:
        delete_object(object_key)
        logging.info(f"Deleted backup file: {backup_public}")
        return {"success": True, "message": f"Backup file deleted: {backup_public}"}
    except Exception as e:
        logging.error(f"Failed to delete backup: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting backup: {str(e)}") from e


