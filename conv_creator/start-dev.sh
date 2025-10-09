#!/usr/bin/env bash
set -euo pipefail

# start-dev.sh
# Starts the backend (uvicorn) and the frontend (Vite) for development.
# Usage: ./start-dev.sh

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

cd "$ROOT_DIR"

echo "Starting development environment..."

# Activate venv if present
if [ -f "$BACKEND_DIR/venv/bin/activate" ]; then
  echo "Activating backend venv..."
  # shellcheck disable=SC1090
  source "$BACKEND_DIR/venv/bin/activate"
fi

# Helper to find uvicorn
find_uvicorn() {
  if command -v uvicorn >/dev/null 2>&1; then
    command -v uvicorn
  elif [ -x "$BACKEND_DIR/venv/bin/uvicorn" ]; then
    echo "$BACKEND_DIR/venv/bin/uvicorn"
  else
    return 1
  fi
}

UVICORN_BIN=""
if ! UVICORN_BIN="$(find_uvicorn)"; then
  echo "ERROR: uvicorn not found. Activate the backend venv or install uvicorn in it." >&2
  exit 1
fi

# Start backend
echo "Starting backend (uvicorn)..."
"$UVICORN_BIN" main:app --reload --host 127.0.0.1 --port 8000 --root-path "" &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

cleanup() {
  echo "Stopping development environment..."
  if ps -p "$BACKEND_PID" >/dev/null 2>&1; then
    echo "Killing backend (PID $BACKEND_PID)"
    kill "$BACKEND_PID" || true
  fi
  # allow frontend dev server to shut down normally (it will be in foreground)
}

trap cleanup EXIT INT TERM

# Start frontend
if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm not found. Please install Node.js and npm." >&2
  exit 1
fi

cd "$FRONTEND_DIR"

# Allow overriding API base; Vite picks up env vars prefixed with VITE_
: "${VITE_API_BASE:=http://127.0.0.1:8000}"
export VITE_API_BASE

echo "Starting frontend (npm run dev) with VITE_API_BASE=$VITE_API_BASE..."
npm run dev

# When npm dev exits, cleanup will run via trap
