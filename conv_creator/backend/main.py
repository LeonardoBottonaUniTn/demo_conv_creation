from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import sqlite3
import shutil
from typing import List
import logging
from datetime import datetime

app = FastAPI()

# Configuration
BACKEND_DIR = os.path.dirname(__file__)  # this file lives in the backend/ folder
FILES_ROOT = os.path.join(BACKEND_DIR, 'files_root')
if not os.path.exists(FILES_ROOT):
    os.makedirs(FILES_ROOT, exist_ok=True)
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Use the existing sqlite DB in the backend folder if present
DB_PATH = os.path.join(BACKEND_DIR, 'db.sqlite3')


def _init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # If files table doesn't exist, create it with an autoincrement id and unique name.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute(
            '''
            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                    size INTEGER,
                    uploadDate TEXT,
                    type TEXT,
                    path TEXT,
                    structure_ok INTEGER
            )
            '''
        )
    else:
        # If table exists, check columns. If it has no 'id' column, perform migration.
        cur.execute("PRAGMA table_info(files)")
        cols = [r[1] for r in cur.fetchall()]
        # If table lacks expected columns, migrate safely.
        if 'id' not in cols:
            # create new table with desired schema
            cur.execute(
                '''
                CREATE TABLE files_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    size INTEGER,
                    uploadDate TEXT,
                    type TEXT,
                    path TEXT,
                    structure_ok INTEGER
                )
                '''
            )
            # copy data from old files to new (if columns exist)
            # attempt multiple strategies to preserve existing columns; fall back safely
            try:
                # try to copy structure_ok if it exists in old table
                cur.execute("INSERT INTO files_new(name, size, uploadDate, type, path, structure_ok) SELECT name, size, uploadDate, type, path, structure_ok FROM files")
            except Exception:
                try:
                    # copy data and set structure_ok default to NULL
                    cur.execute("INSERT INTO files_new(name, size, uploadDate, type, path, structure_ok) SELECT name, size, uploadDate, type, path, NULL FROM files")
                except Exception:
                    # fallback: copy only names (set others NULL)
                    try:
                        cur.execute("INSERT INTO files_new(name, structure_ok) SELECT name, NULL FROM files")
                    except Exception:
                        pass
            cur.execute("DROP TABLE files")
            cur.execute("ALTER TABLE files_new RENAME TO files")
        else:
            # If 'structure_ok' column is missing on an otherwise normal table,
            # add it in-place using ALTER TABLE so we don't need to recreate data.
            if 'structure_ok' not in cols:
                try:
                    cur.execute("ALTER TABLE files ADD COLUMN structure_ok INTEGER")
                except Exception:
                    # best-effort: if ALTER fails, leave table as-is; app will handle missing column errors elsewhere
                    pass
    conn.commit()
    conn.close()


def _upsert_file_record(path: str) -> dict:
    stat = os.stat(path)
    name = os.path.basename(path)
    size = stat.st_size
    uploadDate = datetime.fromtimestamp(stat.st_mtime).isoformat()
    ftype = os.path.splitext(path)[1].lstrip('.').lower() or 'unknown'
    relpath = os.path.relpath(path, BACKEND_DIR)

    # compute structure_ok for JSON files: 1 = ok, 0 = invalid, NULL = skipped (e.g., user files)
    def _check_structure_file(full_path: str) -> int | None:
        # skip if not JSON
        if not full_path.lower().endswith('.json'):
            return None
        # skip user files/folders
        parts = os.path.normpath(full_path).split(os.sep)
        if any(p.lower() == 'user' for p in parts):
            return None
        try:
            with open(full_path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            return 0

        def valid_node(node: any) -> bool:
            if not isinstance(node, dict):
                return False
            # required keys
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

        if isinstance(data, list):
            return 1 if all(valid_node(el) for el in data) else 0
        else:
            return 1 if valid_node(data) else 0

    struct_flag = _check_structure_file(path)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO files(name, size, uploadDate, type, path, structure_ok) VALUES (?, ?, ?, ?, ?, ?)'
        ' ON CONFLICT(name) DO UPDATE SET size=excluded.size, uploadDate=excluded.uploadDate, type=excluded.type, path=excluded.path, structure_ok=excluded.structure_ok',
        (name, size, uploadDate, ftype, relpath, struct_flag),
    )
    conn.commit()
    # fetch id and return full record
    cur.execute('SELECT id, name, size, uploadDate, type, path, structure_ok FROM files WHERE name = ?', (name,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "size": row[2], "uploadDate": row[3], "type": row[4], "path": row[5], "structure_ok": row[6]}
    return {"name": name, "size": size, "uploadDate": uploadDate, "type": ftype, "path": relpath}


def _delete_file_record(name: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('DELETE FROM files WHERE name = ?', (name,))
    conn.commit()
    conn.close()


def _list_files_db() -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, name, size, uploadDate, type, path, structure_ok FROM files')
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "size": r[2], "uploadDate": r[3], "type": r[4], "path": r[5], "structure_ok": r[6]} for r in rows
    ]


# initialize DB on startup
_init_db()

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


def _file_metadata(path: str) -> dict:
    stat = os.stat(path)
    return {
        "name": os.path.basename(path),
        "size": stat.st_size,
        "uploadDate": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "type": os.path.splitext(path)[1].lstrip('.').lower() or 'unknown',
        "path": os.path.relpath(path, BACKEND_DIR),
    }


@app.get("/api/files")
def list_files(folder: str | None = None) -> List[dict]:
    """List available files from the SQLite metadata table.

    If folder is provided it filters results to that subfolder (relative to files_root).
    If DB is empty it will scan FILES_ROOT (or the provided folder) to populate the DB.
    """
    rows = _list_files_db()
    if rows:
        if folder:
            # normalize stored path and compare prefix carefully.
            # Require the folder prefix to represent a directory boundary so that
            # filenames that merely start with the folder name (e.g. 'bp_130_0.json')
            # are not considered inside 'bp_130'. We accept files whose stored path
            # equals the folder prefix (if it's a file representing the folder) or
            # starts with folder_prefix + os.sep.
            folder_prefix = os.path.normpath(os.path.join('files_root', folder))
            def in_folder(relpath: str) -> bool:
                rp = os.path.normpath(relpath)
                if rp == folder_prefix:
                    return True
                return rp.startswith(folder_prefix + os.sep)

            filtered = [r for r in rows if in_folder(r['path'])]
            return filtered

        # No folder provided: return only top-level files (those directly under files_root).
        top_level = []
        for r in rows:
            rp = os.path.normpath(r.get('path', ''))
            # strip leading files_root/ if present
            prefix = os.path.normpath('files_root') + os.sep
            if rp.startswith(prefix):
                rel = rp[len(prefix):]
            else:
                rel = rp
            if rel and os.sep not in rel:
                top_level.append(r)
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
def get_file_by_id(file_id: int):
    """Return file metadata or JSON content when targeting by numeric id."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT name, path FROM files WHERE id = ?', (file_id,))
    row = cur.fetchone()
    conn.close()
    # Debug: log DB lookup results to help diagnose missing files
    logger = logging.getLogger('uvicorn.error')
    logger.error(f"get_file_by_id: lookup id={file_id} -> row={row}, DB_PATH={DB_PATH}")
    if not row:
        raise HTTPException(status_code=404, detail='File not found')
    # row -> (name, path)
    relpath = row[1]
    # Resolve stored path robustly using helper (handles 'files_root/..' and legacy forms)
    full = _resolve_stored_relpath(relpath)
    files_root_norm = os.path.normpath(FILES_ROOT)
    if not (full == files_root_norm or full.startswith(files_root_norm + os.sep)):
        raise HTTPException(status_code=400, detail='Invalid file path stored in DB')
    if not os.path.exists(full):
        logger.error(f"get_file_by_id: resolved full path does not exist: {full}")
        raise HTTPException(status_code=404, detail='File not found')
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
def get_file(filename: str):
    """Return file content for JSON files, a message for PKL, otherwise provide a download.

    Frontend can use this to preview JSON, download binaries, or receive a helpful message for pickle files.
    """
    full = _safe_path(filename)
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="File not found")

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


@app.delete('/api/files/id/{file_id}')
def delete_file_by_id(file_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT name, path FROM files WHERE id = ?', (file_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail='File not found')
    name = row[0]
    relpath = row[1]
    # Resolve stored path robustly (support legacy entries)
    full = _resolve_stored_relpath(relpath)
    if os.path.exists(full):
        try:
            os.remove(full)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to remove file: {e}')
    # remove db record
    _delete_file_record(name)
    return {"message": "Deleted", "file": name, "id": file_id}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), path: str | None = Form(None)):
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
    # delete DB record if present, return id if available
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        rel = os.path.relpath(full, BACKEND_DIR)
        cur.execute('SELECT id FROM files WHERE path = ?', (rel,))
        row = cur.fetchone()
        if not row:
            cur.execute('SELECT id FROM files WHERE name = ?', (os.path.basename(filename),))
            row = cur.fetchone()
        file_id = row[0] if row else None
        conn.close()
        # delete by name to keep compatibility
        _delete_file_record(os.path.basename(filename))
    except Exception:
        file_id = None
    return {"message": "Deleted", "file": filename, "id": file_id}


@app.post('/api/migrate-files')
def migrate_files():
    """Scan backend directory for allowed files and populate/update the SQLite metadata table."""
    allowed_exts = {'.json', '.pkl', '.csv'}
    entries = []
    for root, _, files in os.walk(FILES_ROOT):
        for name in files:
            if os.path.splitext(name)[1].lower() in allowed_exts:
                full = os.path.join(root, name)
                rec = _upsert_file_record(full)
                entries.append(rec)
    return {"migrated": len(entries), "files": entries}


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

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    moved = []
    errors = []

    for t in targets:
        # resolve target to stored path and name
        row = None
        try:
            tid = int(t)
            cur.execute('SELECT name, path FROM files WHERE id = ?', (tid,))
            row = cur.fetchone()
        except Exception:
            # try by path or name
            cur.execute('SELECT id, name, path FROM files WHERE path = ? OR name = ?', (t, os.path.basename(str(t))))
            row = cur.fetchone()

        if not row:
            errors.append({'target': t, 'error': 'not found in DB'})
            continue

        # row may be (name,path) or (id,name,path)
        if len(row) == 2:
            name, relpath = row
        else:
            _, name, relpath = row

        # Resolve stored path robustly. Newer records store a path relative to BACKEND_DIR
        # (e.g. 'files_root/..'), older/legacy records may store just the filename or a
        # path relative to FILES_ROOT. Try both interpretations.
        try:
            src_full = _resolve_stored_relpath(relpath)
        except Exception:
            errors.append({'target': t, 'error': 'invalid stored path'})
            continue

        # ensure the resolved file is inside FILES_ROOT
        files_root_norm = os.path.normpath(FILES_ROOT)
        if not (src_full == files_root_norm or src_full.startswith(files_root_norm + os.sep)):
            errors.append({'target': t, 'error': 'invalid stored path'})
            continue
        if not os.path.exists(src_full):
            errors.append({'target': t, 'error': 'source file missing'})
            continue

        dest_full_path = os.path.join(dest_full, os.path.basename(src_full))
        try:
            # overwrite if exists
            if os.path.exists(dest_full_path):
                os.remove(dest_full_path)
            shutil.move(src_full, dest_full_path)
            # update DB record for new path
            rec = _upsert_file_record(dest_full_path)
            moved.append({'target': t, 'moved_to': rec.get('path'), 'id': rec.get('id')})
        except Exception as e:
            errors.append({'target': t, 'error': str(e)})

    conn.close()
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

    # Remove DB records for files that lived under this folder
    relprefix = os.path.normpath(os.path.join('files_root', folder_path))
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM files WHERE path LIKE ?", (relprefix + '%',))
    removed = cur.rowcount
    conn.commit()
    conn.close()

    return {"deleted": True, "path": folder_path, "db_files_removed": removed}


@app.get("/api/discussion")
def get_discussion():
    """Return the discussion data (bp_130_0_d3.json) so the frontend can fetch it via API."""
    path = os.path.join(FILES_ROOT, 'bp_130_0_d3.json')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Discussion file not found")
    with open(path, 'r', encoding='utf-8') as f:
        return JSONResponse(content=json.load(f))


@app.get("/api/users")
def get_users():
    """Return the users metadata (bp_130_users.json)"""
    path = os.path.join(FILES_ROOT, 'bp_130_users.json')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Users file not found")
    with open(path, 'r', encoding='utf-8') as f:
        return JSONResponse(content=json.load(f))
