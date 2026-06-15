#!/usr/bin/env bash
# Run backend and frontend dev servers together (local development).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "▶ Starting backend (http://localhost:8000)…"
(
  cd "$ROOT/backend"
  [ -d .venv ] || python -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -q -r requirements.txt
  uvicorn app.main:app --reload --port 8000
) &
BACKEND_PID=$!

echo "▶ Starting frontend (http://localhost:5173)…"
(
  cd "$ROOT/frontend"
  npm install
  npm run dev
) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT
wait
