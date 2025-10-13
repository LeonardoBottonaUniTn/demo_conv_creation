from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import sqlite3
import shutil
from typing import List
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
                path TEXT
            )
            '''
        )
    else:
        # If table exists, check columns. If it has no 'id' column, perform migration.
        cur.execute("PRAGMA table_info(files)")
        cols = [r[1] for r in cur.fetchall()]
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
                    path TEXT
                )
                '''
            )
            # copy data from old files to new (if columns exist)
            # attempt to copy known columns; ignore failures
            try:
                cur.execute("INSERT INTO files_new(name, size, uploadDate, type, path) SELECT name, size, uploadDate, type, path FROM files")
            except Exception:
                # fallback: copy only names if other columns missing
                try:
                    cur.execute("INSERT INTO files_new(name) SELECT name FROM files")
                except Exception:
                    pass
            cur.execute("DROP TABLE files")
            cur.execute("ALTER TABLE files_new RENAME TO files")
    conn.commit()
    conn.close()


def _upsert_file_record(path: str) -> dict:
    stat = os.stat(path)
    name = os.path.basename(path)
    size = stat.st_size
    uploadDate = datetime.fromtimestamp(stat.st_mtime).isoformat()
    ftype = os.path.splitext(path)[1].lstrip('.').lower() or 'unknown'
    relpath = os.path.relpath(path, BACKEND_DIR)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO files(name, size, uploadDate, type, path) VALUES (?, ?, ?, ?, ?)'
        ' ON CONFLICT(name) DO UPDATE SET size=excluded.size, uploadDate=excluded.uploadDate, type=excluded.type, path=excluded.path',
        (name, size, uploadDate, ftype, relpath),
    )
    conn.commit()
    # fetch id and return full record
    cur.execute('SELECT id, name, size, uploadDate, type, path FROM files WHERE name = ?', (name,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "size": row[2], "uploadDate": row[3], "type": row[4], "path": row[5]}
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
    cur.execute('SELECT id, name, size, uploadDate, type, path FROM files')
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "size": r[2], "uploadDate": r[3], "type": r[4], "path": r[5]} for r in rows
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
            # normalize stored path and compare prefix
            folder_prefix = os.path.normpath(os.path.join('files_root', folder))
            filtered = [r for r in rows if os.path.normpath(r['path']).startswith(folder_prefix)]
            return filtered
        return rows

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


@app.get('/api/files/id/{file_id}')
def get_file_by_id(file_id: int):
    """Return file metadata or JSON content when targeting by numeric id."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT name, path FROM files WHERE id = ?', (file_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail='File not found')
    # row -> (name, path)
    relpath = row[1]
    # construct absolute path and ensure it's inside FILES_ROOT
    full = os.path.normpath(os.path.join(BACKEND_DIR, relpath))
    files_root_norm = os.path.normpath(FILES_ROOT)
    if not (full == files_root_norm or full.startswith(files_root_norm + os.sep)):
        raise HTTPException(status_code=400, detail='Invalid file path stored in DB')
    if not os.path.exists(full):
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
    full = os.path.normpath(os.path.join(BACKEND_DIR, relpath))
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
    rec = _upsert_file_record(dest)
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
