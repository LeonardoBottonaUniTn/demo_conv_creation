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
if [ -f "$BACKEND_DIR/backend_env/bin/activate" ]; then
  echo "Activating backend venv..."
  # shellcheck disable=SC1090
  source "$BACKEND_DIR/backend_env/bin/activate"
fi

# Find a Python interpreter that can run the uvicorn module, prefer the venv's python
# This avoids executing the venv wrapper script (backend_env/bin/uvicorn) which may have
# a broken shebang on some macOS setups when path lengths or environments change.
USE_UVICORN_MODULE=0
PYTHON_BIN=""
UVICORN_BIN=""

if [ -x "$BACKEND_DIR/backend_env/bin/python" ]; then
  # Prefer venv python if it can run uvicorn as a module
  if "$BACKEND_DIR/backend_env/bin/python" -m uvicorn --version >/dev/null 2>&1; then
    PYTHON_BIN="$BACKEND_DIR/backend_env/bin/python"
    USE_UVICORN_MODULE=1
  fi
fi

if [ "$USE_UVICORN_MODULE" -eq 0 ]; then
  # Fall back to uvicorn executable in PATH
  if command -v uvicorn >/dev/null 2>&1; then
    UVICORN_BIN="$(command -v uvicorn)"
  else
    # Fall back to system python3 -m uvicorn if available
    if command -v python3 >/dev/null 2>&1 && python3 -m uvicorn --version >/dev/null 2>&1; then
      PYTHON_BIN="$(command -v python3)"
      USE_UVICORN_MODULE=1
    else
      echo "ERROR: uvicorn not found. Activate the backend venv or install uvicorn in it." >&2
      exit 1
    fi
  fi
fi

# Start backend
echo "Starting backend (uvicorn)..."
# The FastAPI app lives in backend/main.py, run uvicorn with the module path backend.main:app
if [ "$USE_UVICORN_MODULE" -eq 1 ]; then
  "$PYTHON_BIN" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 --root-path "" &
else
  "$UVICORN_BIN" backend.main:app --reload --host 127.0.0.1 --port 8000 --root-path "" &
fi
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
