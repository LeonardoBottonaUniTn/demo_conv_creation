import os
import logging

# Backend directory path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Files root directory
FILES_ROOT = os.path.join(BACKEND_DIR, 'files_root')
if not os.path.exists(FILES_ROOT):
    os.makedirs(FILES_ROOT, exist_ok=True)

# Database path
DB_PATH = os.path.join(BACKEND_DIR, 'db.sqlite3')

# Allowed origins for CORS
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Logger
logger = logging.getLogger('uvicorn.error')
