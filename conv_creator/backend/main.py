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
auth_scheme = HTTPBearer(auto_error=False)

# LLM configuration (available model choices for the UI and defaults)
AVAILABLE_LLM_MODELS: List[str] = [
    "meta-llama/llama-4-maverick-17b-128e-instruct",
]
DEFAULT_LLM_MODEL: str = AVAILABLE_LLM_MODELS[0]




def _require_supabase_key(env_var: str) -> str:
    value = os.getenv(env_var)
    if not value:
        raise RuntimeError(f"Environment variable {env_var} must be set for Supabase integration")
    return value


def _build_supabase_auth_headers(*, use_service: bool = False) -> Dict[str, str]:
    key = _require_supabase_key("SUPABASE_SERVICE_ROLE_KEY" if use_service else "DATABASE_ANON_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


async def _supabase_auth_post(path: str, payload: Dict[str, Any], *, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    url = f"{SUPABASE_AUTH_URL}{path}"
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
        raise HTTPException(status_code=response.status_code, detail=detail)
    return response.json()


def _decode_supabase_token(token: str) -> Dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header") from exc

    kid = header.get("kid")
    jwks = get_jwks()
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


def _get_user_settings(user_id: str) -> Optional[Dict[str, Any]]:
    client = get_supabase_client()
    response = (
        client.table("user_settings")
        .select("api_key, model, created_at, updated_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if response.error:
        logger.error("Failed to load user settings for %s: %s", user_id, response.error)
        raise HTTPException(status_code=500, detail="Failed to load user settings")
    if not response.data:
        return None
    return response.data[0]


def _upsert_user_settings(user_id: str, api_key: Optional[str], model: Optional[str]) -> None:
    client = get_supabase_client()
    payload = {
        "user_id": user_id,
        "api_key": api_key,
        "model": model,
        "updated_at": datetime.utcnow().isoformat(),
    }
    response = client.table("user_settings").upsert(payload, on_conflict="user_id").execute()
    if response.error:
        logger.error("Failed to upsert user settings for %s: %s", user_id, response.error)
        raise HTTPException(status_code=500, detail="Failed to update user settings")


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


def _classify_file(full_path: str) -> Tuple[Optional[int], Optional[str]]:
    if not full_path.lower().endswith('.json'):
        return None, None
    try:
        with open(full_path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception:
        return 0, 'invalid'

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


def _upsert_file_record(path: str, *, created_by: Optional[str] = None) -> Dict[str, Any]:
    try:
        return supabase_upsert_file_record(
            path,
            BACKEND_DIR,
            _classify_file,
            created_by=created_by,
        )
    except RuntimeError as exc:
        logger.error("Failed to upsert metadata for %s: %s", path, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _delete_file_record(name: str) -> None:
    try:
        supabase_delete_file_record(name)
    except RuntimeError as exc:
        logger.error("Failed to delete metadata for %s: %s", name, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _list_files_db() -> List[Dict[str, Any]]:
    try:
        return supabase_list_files_db()
    except RuntimeError as exc:
        logger.error("Failed to list files: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _load_file_record(identifier: Any) -> Optional[Dict[str, Any]]:
    """Fetch a file record by numeric id or stored name/path."""
    try:
        file_id = int(identifier)
    except (TypeError, ValueError):
        file_id = None

    try:
        if file_id is not None:
            return _get_file_record_by_id(file_id)
        return _get_file_by_name_or_relpath(str(identifier))
    except RuntimeError as exc:
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
    model = (settings or {}).get("model") or DEFAULT_LLM_MODEL
    if model not in AVAILABLE_LLM_MODELS:
        model = DEFAULT_LLM_MODEL
    has_api_key = bool((settings or {}).get("api_key"))
    return {
        "model": model,
        "hasApiKey": has_api_key,
        "availableModels": AVAILABLE_LLM_MODELS,
    }


@app.post("/api/settings")
async def update_settings(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Update the current user's LLM API key and preferred model.

    Expects JSON body with optional keys:
      - apiKey: string (empty string clears the stored key)
      - model: string (one of AVAILABLE_LLM_MODELS)
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    api_key_raw = body.get("apiKey")
    model_raw = body.get("model")

    api_key: Optional[str]
    if api_key_raw is None:
        # None means: keep existing key as-is
        existing = _get_user_settings(current_user["id"]) or {}
        api_key = existing.get("api_key")
    else:
        # Empty string explicitly clears the stored key
        api_key = api_key_raw.strip() or None

    model: Optional[str]
    if model_raw is None:
        existing = _get_user_settings(current_user["id"]) or {}
        model = existing.get("model") or DEFAULT_LLM_MODEL
    else:
        model = str(model_raw).strip() or DEFAULT_LLM_MODEL

    if model not in AVAILABLE_LLM_MODELS:
        raise HTTPException(status_code=400, detail="Unsupported model selection")

    _upsert_user_settings(current_user["id"], api_key, model)

    return {
        "success": True,
        "model": model,
        "hasApiKey": bool(api_key),
    }


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
def list_files(folder: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available files from the Supabase metadata table.

    If folder is provided it filters results to that subfolder (relative to files_root).
    If DB is empty it will scan FILES_ROOT (or the provided folder) to populate the DB.
    """
    import os
    from datetime import datetime
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
            folder_prefix = os.path.normpath(os.path.join('files_root', folder))
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
            prefix = os.path.normpath('files_root') + os.sep
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
        start = _safe_path(folder)
        for root, _, files in os.walk(start):
            for name in files:
                if os.path.splitext(name)[1].lower() in allowed_exts:
                    full = os.path.join(root, name)
                    rec = _upsert_file_record(full)
                    entries.append(rec)
    else:
        for root, _, files in os.walk(FILES_ROOT):
            for name in files:
                if os.path.splitext(name)[1].lower() in allowed_exts:
                    full = os.path.join(root, name)
                    rec = _upsert_file_record(full)
                    entries.append(rec)
    return entries


@app.get('/api/files/id/{file_id}')
def get_file_by_id(file_id: int, download: bool = False):
    """Return file metadata or JSON content when targeting by numeric id."""
    try:
        record = _get_file_record_by_id(file_id)
    except RuntimeError as exc:
        logger.error("Failed to load Supabase metadata for id=%s: %s", file_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not record:
        raise HTTPException(status_code=404, detail='File not found')

    relpath = record.get('path') or record.get('rel_path')
    full = _resolve_stored_relpath(relpath)
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


@app.get("/api/files/{filename:path}")
def get_file(filename: str, download: bool = False):
    """Return file content for JSON files, a message for PKL, otherwise provide a download.

    Frontend can use this to preview JSON, download binaries, or receive a helpful message for pickle files.
    """
    # First, try to resolve the filename as a path under FILES_ROOT
    try:
        full = _safe_path(filename)
    except HTTPException:
        # propagate safety errors
        raise

    # If the safe-resolved path doesn't exist, attempt to locate the file by name
    # in the DB (files may live in subfolders created by the app and the UI may
    # request them by filename only).
    if not os.path.exists(full):
        try:
            row = _get_file_by_name_or_relpath(filename)
        except RuntimeError as exc:
            logger.error("Failed to resolve %s via Supabase metadata: %s", filename, exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        if row:
            relpath = row.get('path') or row.get('rel_path')
            try:
                candidate = _resolve_stored_relpath(relpath)
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
        # Pickle files cannot be safely deserialized in the browser; provide a helpful message
        return {"message": "This is a Python pickle file. Use the download endpoint to retrieve it or process it on the server."}
    else:
        # For other files, return raw file for download
        return FileResponse(full, media_type='application/octet-stream', filename=filename)
    

@app.patch('/api/files/id/{file_id}')
async def save_changes_file_by_id(file_id: int, request: Request):
    """Save changes to a JSON file identified by numeric id."""
    record = _load_file_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail='File not found')
    name = record.get('name')
    relpath = record.get('path') or record.get('rel_path')
    # Resolve stored path robustly (support legacy entries)
    full = _resolve_stored_relpath(relpath)
    logger = logging.getLogger('uvicorn.error')
    logger.info(f"save_changes_file_by_id: id={file_id} name={name} relpath={relpath} resolved_full={full}")
    # Ensure resolved path is inside FILES_ROOT (protect against legacy/absolute paths)
    files_root_norm = os.path.normpath(FILES_ROOT)
    if not (full == files_root_norm or full.startswith(files_root_norm + os.sep)):
        raise HTTPException(status_code=400, detail='Invalid file path stored in DB')
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail='File not found')
    # Reject directories — we must operate on files only
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
    # update DB record (e.g., uploadDate)
    rec = _upsert_file_record(full)
    return {"message": "Saved", "file": rec}


@app.patch('/api/files/{filename:path}')
async def save_changes_file_by_name(filename: str, request: Request):
    """Save changes to a JSON file identified by filename (relative to files_root).

    Behaviour:
    - The filename is resolved safely inside `FILES_ROOT` using `_safe_path` (prevents traversal).
    - If the target exists and is a JSON object, the endpoint will replace its top-level
      'users' key when a 'users' array is provided in the request body. If no 'users' key
      is present in the body, the entire body may be written (use with care).
    - If the target does not exist, the endpoint will create a new JSON file of the form
      {"users": [...]} when the caller provides a 'users' array.
    - Only JSON files are allowed for modification via this endpoint.
    """
    logger = logging.getLogger('uvicorn.error')
    try:
        full = _safe_path(filename)
    except HTTPException:
        logger.error(f"save_changes_file_by_name: unsafe path requested: {filename}")
        raise

    # Ensure we operate on a file (not a directory)
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

    # Determine what to write
    if os.path.exists(full):
        # If file exists, try to parse it and merge/replace 'users'
        try:
            with open(full, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            # avoid clobbering non-JSON content
            raise HTTPException(status_code=400, detail='Target exists but is not valid JSON')
        if isinstance(data, dict):
            if users is not None:
                data['users'] = users
                to_write = data
            else:
                # No users key provided: interpret request as full-replace of object
                if isinstance(body, dict):
                    to_write = body
                else:
                    raise HTTPException(status_code=400, detail='Nothing to write')
        else:
            raise HTTPException(status_code=400, detail='Target JSON is not an object; cannot insert users')
    else:
        # File doesn't exist: require 'users' array to create a sensible file
        if not isinstance(users, list):
            raise HTTPException(status_code=400, detail='Target does not exist; provide a "users" array to create it')
        to_write = {'users': users}

    try:
        logger.info(f"save_changes_file_by_name: writing to {full} (exists={os.path.exists(full)}) size={len(json.dumps(to_write)) if to_write is not None else 0}")
        _atomic_write_json(full, to_write)
    except Exception as e:
        logger.error(f"save_changes_file_by_name: failed to write {full}: {e}")
        raise HTTPException(status_code=500, detail=f'Failed to save JSON file: {e}')

    rec = _upsert_file_record(full)
    return {"message": "Saved", "file": rec}


@app.delete('/api/files/id/{file_id}')
def delete_file_by_id(file_id: int):
    record = _load_file_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail='File not found')
    name = record.get('name') or str(file_id)
    relpath = record.get('path') or record.get('rel_path')
    # Resolve stored path robustly (support legacy entries)
    full = _resolve_stored_relpath(relpath)
    if os.path.exists(full):
        try:
            os.remove(full)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to remove file: {e}')
    _delete_file_record(name)
    return {"message": "Deleted", "file": name, "id": file_id}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), path: Optional[str] = Form(None)):
    """Upload a file into the backend directory. Overwrites if name exists."""
    # For uploads we only accept a single filename (no nested paths within file.filename)
    if os.path.basename(file.filename) != file.filename:
        raise HTTPException(status_code=400, detail="Invalid upload filename")
    filename = file.filename
    if path:
        # ensure the folder is safe and exists (create if missing)
        folder_full = _safe_path(path)
        os.makedirs(folder_full, exist_ok=True)
        dest = os.path.join(folder_full, filename)
    else:
        dest = os.path.join(FILES_ROOT, filename)
    try:
        with open(dest, 'wb') as out:
            content = await file.read()
            out.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    # update DB record
    # Update DB record for the uploaded file and scan the containing folder so
    # newly uploaded files inside nested folders are all processed.
    rec = _upsert_file_record(dest)
    # If a folder was provided, also scan other files in the same folder to
    # ensure the DB is up-to-date for that directory.
    if path:
        try:
            folder_full = os.path.normpath(folder_full)
            for name in os.listdir(folder_full):
                full = os.path.join(folder_full, name)
                if os.path.isfile(full) and os.path.splitext(name)[1].lower() in {'.json', '.pkl', '.csv'}:
                    _upsert_file_record(full)
        except Exception:
            # non-fatal: we've already updated the uploaded file record; ignore folder-scan errors
            pass
    return {"message": "Uploaded", "file": rec}


@app.delete("/api/files/{filename:path}")
def delete_file(filename: str):
    # allow deleting nested files under files_root
    full = _safe_path(filename)
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(full)

    record = None
    rel_identifier = os.path.relpath(full, BACKEND_DIR)
    try:
        record = _load_file_record(rel_identifier)
        if not record:
            record = _load_file_record(os.path.basename(filename))
    except HTTPException:
        raise
    except Exception:
        record = None

    file_id = record.get('id') if record else None
    try:
        _delete_file_record(os.path.basename(filename))
    except HTTPException as exc:
        # If Supabase deletion fails we should inform the caller
        raise exc
    except Exception as exc:
        logger.error("Failed to delete Supabase metadata for %s: %s", filename, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"message": "Deleted", "file": filename, "id": file_id}


@app.post('/api/migrate-files')
def migrate_files():
    """Scan backend directory for allowed files and populate/update the Supabase metadata table."""
    allowed_exts = {'.json', '.pkl', '.csv'}
    entries = []
    for root, _, files in os.walk(FILES_ROOT):
        for name in files:
            if os.path.splitext(name)[1].lower() in allowed_exts:
                full = os.path.join(root, name)
                rec = _upsert_file_record(full)
                entries.append(rec)
    return {"migrated": len(entries), "files": entries}


@app.post('/api/files/save-draft/{filename:path}')
async def save_draft_file(filename: str, request: Request):
    """Create a new draft JSON file under FILES_ROOT with the provided filename.

    Expects a JSON body like: { "payload": { ... } }
    The filename is interpreted as a relative path inside files_root. If the
    provided filename has no .json extension, ".json" will be appended.
    """
    logger = logging.getLogger('uvicorn.error')
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"save_draft_file: invalid JSON body for {filename}: {e}")
        raise HTTPException(status_code=400, detail=f'Invalid JSON body: {e}')

    payload = body.get('payload') if isinstance(body, dict) else None
    if payload is None:
        raise HTTPException(status_code=400, detail='Missing "payload" in request body')

    # Ensure filename ends with .json
    if not filename.lower().endswith('.json'):
        filename = filename + '.json'

    # Save under files_root; use _safe_path to avoid traversal
    try:
        rel = filename
        full = _safe_path(rel)
    except HTTPException as e:
        logger.error(f"save_draft_file: unsafe filename requested: {filename}")
        raise

    # If target exists and is a directory, error
    if os.path.isdir(full):
        raise HTTPException(status_code=400, detail='Target filename resolves to a directory')

    try:
        _atomic_write_json(full, payload, ensure_ascii=False)
    except Exception as e:
        logger.error(f"save_draft_file: failed to write {full}: {e}")
        raise HTTPException(status_code=500, detail=f'Failed to write draft file: {e}')

    # Update DB record for the new file
    try:
        rec = _upsert_file_record(full)
    except Exception:
        rec = None

    return {"message": "Draft saved", "file": rec or os.path.basename(full)}


@app.post('/api/files/move')
def move_files_endpoint(data: dict):
    """Move files listed in `targets` to the `dest` folder (relative to files_root).

    Accepts JSON body: { targets: [...], dest: 'path' }
    Targets can be numeric ids (int or string digits) or stored names/paths.
    """
    targets = data.get('targets') if isinstance(data, dict) else None
    dest = data.get('dest') if isinstance(data, dict) else ''
    if not targets or not isinstance(targets, list):
        raise HTTPException(status_code=400, detail='Missing or invalid targets')

    # destination folder (empty means root)
    try:
        dest_full = _safe_path(dest) if dest else FILES_ROOT
    except HTTPException as e:
        raise e

    os.makedirs(dest_full, exist_ok=True)

    moved = []
    errors = []

    for t in targets:
        try:
            record = _load_file_record(t)
        except HTTPException as exc:
            errors.append({'target': t, 'error': exc.detail})
            continue
        except Exception as exc:
            errors.append({'target': t, 'error': str(exc)})
            continue

        if not record:
            errors.append({'target': t, 'error': 'not found in DB'})
            continue

        relpath = record.get('path') or record.get('rel_path') or record.get('name')
        try:
            src_full = _resolve_stored_relpath(relpath)
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
            rec = _upsert_file_record(dest_full_path, created_by=record.get('created_by'))
            moved.append({'target': t, 'moved_to': rec.get('path'), 'id': rec.get('id')})
        except Exception as e:
            errors.append({'target': t, 'error': str(e)})

    return {'moved': moved, 'errors': errors}


@app.get('/api/folders')
def list_folders():
    """Return all folders under files_root as relative paths."""
    results = []
    for root, dirs, _ in os.walk(FILES_ROOT):
        for d in dirs:
            full = os.path.join(root, d)
            rel = os.path.relpath(full, FILES_ROOT)
            results.append(rel)
    return {"folders": sorted(results)}


@app.post('/api/folders')
def create_folder(data: dict):
    """Create a folder under files_root. Expects JSON body {path: 'a/b'}"""
    target = data.get('path') if isinstance(data, dict) else None
    if not target:
        raise HTTPException(status_code=400, detail='Missing path')
    # create folder safely
    full = _safe_path(target)
    try:
        os.makedirs(full, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to create folder: {e}')
    return {"created": True, "path": target}


@app.delete('/api/folders/{folder_path:path}')
def delete_folder(folder_path: str):
    """Delete a folder under files_root and remove corresponding DB records.

    The folder_path is relative to files_root (e.g., 'graphics' or 'a/b').
    Deleting the root (empty path) is not allowed.
    """
    if not folder_path or folder_path in ('.', '/'):
        raise HTTPException(status_code=400, detail='Cannot delete root folder')
    # resolve safe path and ensure it's a dir inside FILES_ROOT
    full = _safe_path(folder_path)
    if not os.path.isdir(full):
        raise HTTPException(status_code=404, detail='Folder not found')

    # Attempt to remove directory tree first
    try:
        shutil.rmtree(full)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to remove folder: {e}')

    # Remove Supabase records for files that lived under this folder
    relprefix = os.path.normpath(os.path.join('files_root', folder_path))
    try:
        removed = _delete_files_with_prefix(relprefix)
    except RuntimeError as exc:
        logger.error("Failed to delete Supabase rows for prefix %s: %s", relprefix, exc)
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
    """Check if LLM module can be loaded"""
    try:
        # Test that we can call the function
        test_result = transform_discussion_json([{"id": 1, "text": "test"}])
        return {"status": "ok", "message": "LLM module loaded and callable"}
    except Exception as e:
        import traceback
        logging.error(f"LLM health check failed: {e}\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@app.post('/api/llm/generate-bio')
async def api_generate_bio(request: Request):
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
        bio = generate_user_bio(existing_bio, messages)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # bubble up LLM/API errors as a 502 to indicate upstream dependency failure
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")

    return JSONResponse({"success": True, "bio": bio})


@app.post('/api/llm/rewrite-message')
async def api_rewrite_message(request: Request):
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
        rewritten = generate_message_rewrite(
            message,
            speaker_profile=speaker_profile,
            messages_in_chat=chat_msgs,
            temperament=temperament,
            style=style,
            length=length,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # treat upstream LLM errors as 502
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")

    return JSONResponse({"success": True, "rewritten": rewritten})


@app.post("/api/files/fix/{file_id}/preview")
async def preview_file_fix(file_id: int):
    """
    Preview the LLM-suggested fix without applying it.
    Returns both the original and fixed data for user review.
    """
    record = _load_file_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")

    name = record.get('name') or str(file_id)
    rel_path = record.get('path') or record.get('rel_path') or name

    if rel_path.startswith('files_root/'):
        rel_path = rel_path[len('files_root/'):]

    full_path = os.path.join(FILES_ROOT, rel_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"File not found at path: {rel_path}")
    
    # Read the current file
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"File is not valid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")
    
    # Transform using LLM
    try:
        fixed_data = transform_discussion_json(input_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM transformation failed: {str(e)}")
    
    # Return both versions for comparison
    return {
        "success": True,
        "file_id": file_id,
        "file_name": name,
        "original": input_data,
        "fixed": fixed_data,
        "changes_count": len(fixed_data) if isinstance(fixed_data, list) else 1
    }


@app.post("/api/files/fix/{file_id}/apply")
async def apply_file_fix(file_id: int, request: Request):
    body = await request.json()
    fixed_data = body.get("fixed_data")
    overwrite = body.get("overwrite", False)
    # Defensive: if fixed_data is a string, try to parse it as JSON
    import json
    if isinstance(fixed_data, str):
        try:
            fixed_data = json.loads(fixed_data)
        except Exception:
            pass
    """
    Apply the LLM-suggested fix after user confirmation.
    Creates a backup before overwriting the original file.
    """
    record = _load_file_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"File with id {file_id} not found")

    name = record.get('name') or str(file_id)
    rel_path = record.get('path') or record.get('rel_path') or name

    if rel_path.startswith('files_root/'):
        rel_path = rel_path[len('files_root/'):]

    full_path = os.path.join(FILES_ROOT, rel_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"File not found at path: {rel_path}")
    
    backup_path = None
    backup_created = False
    new_file_id = file_id
    if overwrite:
        # Create backup of original file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = full_path + f'.backup_{timestamp}'
        try:
            shutil.copy2(full_path, backup_path)
            backup_created = True
        except Exception as e:
            logging.warning(f"Could not create backup: {e}")
        # Save the fixed file (overwrite)
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(fixed_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # Restore from backup if save failed
            if backup_created:
                shutil.copy2(backup_path, full_path)
            raise HTTPException(status_code=500, detail=f"Error saving fixed file: {str(e)}")
        try:
            _set_structure_flag(file_id, True)
        except RuntimeError as exc:
            logger.error("Failed to update structure flag for %s: %s", file_id, exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    else:
        # Save as new file with _fix suffix
        base, ext = os.path.splitext(name)
        new_name = f"{base}_fix{ext}"
        new_rel_path = os.path.join(os.path.dirname(rel_path), new_name) if os.path.dirname(rel_path) else new_name
        new_full_path = os.path.join(FILES_ROOT, new_rel_path)
        try:
            # Only write an empty object if fixed_data is truly empty or None
            to_write = fixed_data if fixed_data not in (None, "", []) else {}
            with open(new_full_path, 'w', encoding='utf-8') as f:
                json.dump(to_write, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error saving fixed file: {str(e)}")
        rec = _upsert_file_record(new_full_path)
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
async def delete_backup_file(request: dict):
    """
    Delete a backup file created during the fix process.
    Only deletes files with .backup_ in their name for safety.
    """
    backup_path = request.get("backup_path")
    
    if not backup_path:
        raise HTTPException(status_code=400, detail="backup_path is required")
    
    # Security check: ensure it's actually a backup file
    if ".backup_" not in backup_path:
        raise HTTPException(status_code=400, detail="Only backup files can be deleted through this endpoint")
    
    # Ensure it's within our FILES_ROOT directory
    abs_backup_path = os.path.abspath(backup_path)
    abs_files_root = os.path.abspath(FILES_ROOT)
    
    if not abs_backup_path.startswith(abs_files_root):
        raise HTTPException(status_code=403, detail="Cannot delete files outside of files_root")
    
    # Delete the backup file
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


