#!/usr/bin/env bash
# One command: start the backend in DEMO mode, seed a demo farmer, start the frontend, open the browser.   Usage: make demo   (Ctrl-C stops everything)
# DEMO mode shows the OTP on screen and activates unverified scheme drafts. Never use with real farmers.
# STATUS: written, NOT run in the build environment (no FastAPI/Docker/network there). Run it once before demo day.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
export ENV=dev ALLOW_UNVERIFIED=1 SECRET_KEY=${SECRET_KEY:-$($PY -c "import secrets;print(secrets.token_urlsafe(48))")}
$PY -c "import fastapi, sqlalchemy, uvicorn" 2>/dev/null || { echo "Missing backend packages. Run: pip install -r backend/requirements.txt"; exit 1; }
[ -d frontend/node_modules ] || (cd frontend && npm install --no-audit --no-fund)

PIDS=(); trap 'kill "${PIDS[@]}" 2>/dev/null || true' EXIT INT TERM
(cd backend && exec $PY -m uvicorn app.main:app --port 8000) & PIDS+=($!)
wait_for() { for _ in $(seq 1 60); do $PY - "$1" <<'P' && return 0 || sleep 0.5
import sys, urllib.request
try: urllib.request.urlopen(sys.argv[1], timeout=2); sys.exit(0)
except Exception: sys.exit(1)
P
done; echo "Timed out waiting for $1"; return 1; }
wait_for http://localhost:8000/healthz
$PY backend/scripts/seed_demo.py
(cd frontend && exec npm run dev -- --port 5173) & PIDS+=($!)
wait_for http://localhost:5173/
URL=http://localhost:5173/
echo; echo "Demo ready: $URL   (log in with phone ${DEMO_PHONE:-9876543210}; the OTP shows on screen)"
(command -v xdg-open >/dev/null && xdg-open "$URL") || (command -v open >/dev/null && open "$URL") || true
wait
