from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import sqlite3
from typing import List
from datetime import datetime

app = FastAPI()

# Configuration
BACKEND_DIR = os.path.dirname(__file__)  # this file lives in the backend/ folder
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

# Optionally mount a static route for direct downloads (keeps API separate)
app.mount("/static-backend", StaticFiles(directory=BACKEND_DIR), name="static-backend")


def _safe_filename(filename: str) -> str:
    # prevent path traversal
    if os.path.basename(filename) != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return filename


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
def list_files() -> List[dict]:
    """List available files from the SQLite metadata table. If the table is empty, fallback to scanning the directory."""
    rows = _list_files_db()
    if rows:
        return rows

    # fallback: scan directory and populate DB
    allowed_exts = {'.json', '.pkl', '.csv'}
    entries = []
    for name in os.listdir(BACKEND_DIR):
        full = os.path.join(BACKEND_DIR, name)
        if os.path.isfile(full) and os.path.splitext(name)[1].lower() in allowed_exts:
            rec = _upsert_file_record(full)
            entries.append(rec)
    return entries


@app.get("/api/files/{filename}")
def get_file(filename: str):
    """Return file content for JSON files, a message for PKL, otherwise provide a download.

    Frontend can use this to preview JSON, download binaries, or receive a helpful message for pickle files.
    """
    _safe_filename(filename)
    full = os.path.join(BACKEND_DIR, filename)
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
    filename = row[0]
    # reuse existing filename-based logic
    return get_file(filename)


@app.delete('/api/files/id/{file_id}')
def delete_file_by_id(file_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT name FROM files WHERE id = ?', (file_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail='File not found')
    filename = row[0]
    # remove file from disk
    full = os.path.join(BACKEND_DIR, filename)
    if os.path.exists(full):
        try:
            os.remove(full)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f'Failed to remove file: {e}')
    # remove db record
    _delete_file_record(filename)
    return {"message": "Deleted", "file": filename, "id": file_id}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file into the backend directory. Overwrites if name exists."""
    filename = _safe_filename(file.filename)
    dest = os.path.join(BACKEND_DIR, filename)
    try:
        with open(dest, 'wb') as out:
            content = await file.read()
            out.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    # update DB record
    rec = _upsert_file_record(dest)
    return {"message": "Uploaded", "file": rec}


@app.delete("/api/files/{filename}")
def delete_file(filename: str):
    _safe_filename(filename)
    full = os.path.join(BACKEND_DIR, filename)
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(full)
    # delete DB record if present, return id if available
    try:
        # fetch id first
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('SELECT id FROM files WHERE name = ?', (filename,))
        row = cur.fetchone()
        file_id = row[0] if row else None
        conn.close()
        _delete_file_record(filename)
    except Exception:
        file_id = None
    return {"message": "Deleted", "file": filename, "id": file_id}


@app.post('/api/migrate-files')
def migrate_files():
    """Scan backend directory for allowed files and populate/update the SQLite metadata table."""
    allowed_exts = {'.json', '.pkl', '.csv'}
    entries = []
    for name in os.listdir(BACKEND_DIR):
        full = os.path.join(BACKEND_DIR, name)
        if os.path.isfile(full) and os.path.splitext(name)[1].lower() in allowed_exts:
            rec = _upsert_file_record(full)
            entries.append(rec)
    return {"migrated": len(entries), "files": entries}


@app.get("/api/discussion")
def get_discussion():
    """Return the discussion data (bp_130_0_d3.json) so the frontend can fetch it via API."""
    path = os.path.join(BACKEND_DIR, 'bp_130_0_d3.json')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Discussion file not found")
    with open(path, 'r', encoding='utf-8') as f:
        return JSONResponse(content=json.load(f))


@app.get("/api/users")
def get_users():
    """Return the users metadata (bp_130_users.json)"""
    path = os.path.join(BACKEND_DIR, 'bp_130_users.json')
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Users file not found")
    with open(path, 'r', encoding='utf-8') as f:
        return JSONResponse(content=json.load(f))
