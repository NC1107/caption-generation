#!/usr/bin/env bash
# Run the backend (autoreload) and the Vite dev server together for local hacking.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  echo "No .venv found — run 'make install' first." >&2
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

( cd backend && DATA_DIR=../data exec uvicorn app.main:app --reload --port 8000 ) &
BACKEND_PID=$!
trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT

cd frontend && npm run dev
