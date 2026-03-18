#!/usr/bin/env python3
"""Legacy helper kept for documentation purposes.

Historically this script patched up paths inside the local SQLite database.
The backend now stores all metadata in Supabase, so there is nothing left to
normalize locally. The script prints a short notice and exits successfully so
existing automation does not break but developers are nudged toward the new
workflow.
"""

import sys

NOTICE = (
    "Supabase manages file metadata now; backend/normalize_paths.py is obsolete.\n"
    "Run the app to sync files via Supabase instead of touching the old SQLite DB."
)


def main() -> None:
    sys.stdout.write(NOTICE + "\n")


if __name__ == "__main__":
    main()
