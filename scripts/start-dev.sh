#!/usr/bin/env sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
[ -f "$ROOT/.env" ] || cp "$ROOT/.env.example" "$ROOT/.env"
PYTHON="$ROOT/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON=python3
cd "$ROOT/backend" && "$PYTHON" -m uvicorn main:app --reload --port 8000 &
cd "$ROOT/security" && npm install && npm run dev &
cd "$ROOT/frontend" && npm install && npm run dev &
wait