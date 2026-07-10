#!/usr/bin/env python3
"""Apply the app schema to Supabase Postgres.

Reads DATABASE_IPv4_URL (direct Postgres connection string) from .env and
runs the SQL migrations idempotently.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(ROOT_DIR / ".env")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS public.files (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          text NOT NULL UNIQUE,
    size          bigint,
    upload_date   timestamptz NOT NULL DEFAULT now(),
    file_type     text,
    rel_path      text,
    structure_ok  boolean,
    category      text,
    checksum      text,
    created_by    uuid REFERENCES auth.users(id),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS files_category_idx ON public.files (category);
CREATE INDEX IF NOT EXISTS files_rel_path_idx ON public.files (rel_path);
CREATE INDEX IF NOT EXISTS files_created_by_idx ON public.files (created_by);

ALTER TABLE public.files DROP CONSTRAINT IF EXISTS files_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS files_rel_path_unique ON public.files (rel_path);

CREATE TABLE IF NOT EXISTS public.user_settings (
    user_id     uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    api_key     text,
    model       text,
    provider    text NOT NULL DEFAULT 'groq',
    annotation_schema jsonb,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS provider text NOT NULL DEFAULT 'groq';

ALTER TABLE public.user_settings
ADD COLUMN IF NOT EXISTS annotation_schema jsonb;
"""


def main() -> int:
    database_url = os.getenv("DATABASE_IPv4_URL") or os.getenv("DATABASE_URL")
    if not database_url or database_url.startswith("https://"):
        print(
            "ERROR: Set DATABASE_IPv4_URL in .env to the direct Postgres connection string.\n"
            "       Supabase dashboard → Project Settings → Database → Connection string (URI).\n"
            "       It must match SUPABASE_URL (same project ref).",
            file=sys.stderr,
        )
        return 1

    supabase_url = os.getenv("SUPABASE_URL", "")
    if "zezxniwahhbdkbjttxio" in database_url and "kjeyivmpaqigkqzcsgui" in supabase_url:
        print(
            "ERROR: DATABASE_IPv4_URL points to the old project (zezxniwahhbdkbjttxio)\n"
            "       but SUPABASE_URL is the new project (kjeyivmpaqigkqzcsgui).\n"
            "       Update DATABASE_IPv4_URL with the new project's Postgres URI.",
            file=sys.stderr,
        )
        return 1

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 is required. Install backend requirements first.", file=sys.stderr)
        return 1

    print("Connecting to Postgres…")
    with psycopg2.connect(database_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('files', 'user_settings')
                ORDER BY table_name
                """
            )
            tables = [row[0] for row in cur.fetchall()]

    print("Tables ready:", ", ".join(tables))
    if len(tables) == 2:
        print("Database setup complete.")
        return 0

    print("WARNING: expected files and user_settings tables.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
