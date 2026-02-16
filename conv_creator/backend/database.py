import sqlite3
import os
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

# Assuming BACKEND_DIR and DB_PATH are defined elsewhere, but for now, let's pass them or define here
# For simplicity, let's define DB_PATH here, but ideally pass it.

def get_db_path(backend_dir: str) -> str:
    return os.path.join(backend_dir, 'db.sqlite3')

def _init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
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
                    structure_ok INTEGER,
                    category TEXT
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
                    structure_ok INTEGER,
                    category TEXT
                )
                '''
            )
            # copy data from old files to new (if columns exist)
            # attempt multiple strategies to preserve existing columns; fall back safely
            try:
                # try to copy structure_ok and category if they exist in old table
                cur.execute("INSERT INTO files_new(name, size, uploadDate, type, path, structure_ok, category) SELECT name, size, uploadDate, type, path, structure_ok, category FROM files")
            except Exception:
                try:
                    # copy data and set structure_ok/category default to NULL
                    cur.execute("INSERT INTO files_new(name, size, uploadDate, type, path, structure_ok, category) SELECT name, size, uploadDate, type, path, NULL, NULL FROM files")
                except Exception:
                    # fallback: copy only names (set others NULL)
                    try:
                        cur.execute("INSERT INTO files_new(name, structure_ok, category) SELECT name, NULL, NULL FROM files")
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
            # ensure category column exists
            if 'category' not in cols:
                try:
                    cur.execute("ALTER TABLE files ADD COLUMN category TEXT")
                except Exception:
                    pass
    conn.commit()
    conn.close()

def _upsert_file_record(db_path: str, path: str, backend_dir: str, classify_func) -> dict:
    import os
    stat = os.stat(path)
    name = os.path.basename(path)
    size = stat.st_size
    uploadDate = datetime.fromtimestamp(stat.st_mtime).isoformat()
    ftype = os.path.splitext(path)[1].lstrip('.').lower() or 'unknown'
    relpath = os.path.relpath(path, backend_dir)

    # classify JSON files and compute structure_ok for JSON files:
    # struct_flag: 1 = valid tree/draft, 0 = invalid, None = skipped/non-json
    # category: 'discussion' | 'draft' | 'invalid' | None
    struct_flag, category = classify_func(path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO files(name, size, uploadDate, type, path, structure_ok, category) VALUES (?, ?, ?, ?, ?, ?, ?)' 
        ' ON CONFLICT(name) DO UPDATE SET size=excluded.size, uploadDate=excluded.uploadDate, type=excluded.type, path=excluded.path, structure_ok=excluded.structure_ok, category=excluded.category',
        (name, size, uploadDate, ftype, relpath, struct_flag, category),
    )
    conn.commit()
    # fetch id and return full record
    cur.execute('SELECT id, name, size, uploadDate, type, path, structure_ok, category FROM files WHERE name = ?', (name,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "size": row[2], "uploadDate": row[3], "type": row[4], "path": row[5], "structure_ok": row[6], "category": row[7]}
    return {"name": name, "size": size, "uploadDate": uploadDate, "type": ftype, "path": relpath, "category": category}

def _delete_file_record(db_path: str, name: str) -> None:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('DELETE FROM files WHERE name = ?', (name,))
    conn.commit()
    conn.close()

def _list_files_db(db_path: str) -> List[dict]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('SELECT id, name, size, uploadDate, type, path, structure_ok, category FROM files')
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "size": r[2], "uploadDate": r[3], "type": r[4], "path": r[5], "structure_ok": r[6], "category": r[7]} for r in rows
    ]