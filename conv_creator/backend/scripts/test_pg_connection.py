import os
import sys

# Allow running the script directly via `python scripts/test_pg_connection.py`
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from pg_connection import get_pg_connection


if __name__ == "__main__":
    with get_pg_connection() as conn, conn.cursor() as cur:
        cur.execute("select current_user, now()")
        print(cur.fetchone())
