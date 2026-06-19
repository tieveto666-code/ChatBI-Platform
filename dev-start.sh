#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$ROOT_DIR/backend/data/uploads" \
  "$ROOT_DIR/backend/data/file_dbs" \
  "$ROOT_DIR/backend/data/logs"

echo "Starting ChatBI backend on http://localhost:8000"
(
  cd "$ROOT_DIR/backend"
  python3 seed.py
  uvicorn main:app --reload --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

echo "Starting ChatBI frontend on http://localhost:5173"
(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --host 127.0.0.1 --port 5173
) &
FRONTEND_PID=$!

trap 'kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true' INT TERM EXIT
wait
