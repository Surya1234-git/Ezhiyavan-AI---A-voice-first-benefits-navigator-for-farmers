#!/usr/bin/env bash
# Runs every check that CAN run in this environment and says plainly which ones were SKIPPED and why (with the exact command to run elsewhere).
# Exit code is non-zero only if a check that actually ran failed.
cd "$(dirname "$0")/.."
PASS=(); FAIL=(); SKIP=()
step() { local name="$1"; shift; echo; echo "=== $name"; if "$@"; then PASS+=("$name"); else FAIL+=("$name"); fi; }
skip() { SKIP+=("$1  [$2]"); echo; echo "=== $1: SKIPPED ($2)"; }
PY=${PYTHON:-python3}

step "static name check (import-order and undefined names)" $PY scripts/check_names.py backend/app/*.py backend/scripts/*.py backend/eval/*.py backend/tests*.py
step "backend unit tests (engine, extraction, governance, privacy, rule corrections)" bash -c "cd backend && $PY -m unittest tests.py tests_new.py"
step "extraction benchmark (SYNTHETIC cases)" bash -c "cd backend && $PY eval/run_eval.py"

if $PY -c "import fastapi, sqlalchemy, httpx, pytest" 2>/dev/null; then
  step "backend API tests (tests_api.py)" bash -c "cd backend && $PY -m pytest tests_api.py -q"
else skip "backend API tests" "needs FastAPI/SQLAlchemy/httpx/pytest. Run: pip install -r backend/requirements.txt httpx pytest && (cd backend && pytest tests_api.py -q)"; fi

if [ -x frontend/node_modules/.bin/vite ]; then step "frontend type-check and production build" bash -c "cd frontend && npm run build"
else skip "frontend type-check and build" "run: cd frontend && npm install && npm run build"; fi

ESB=$(realpath "${ESBUILD:-frontend/node_modules/.bin/esbuild}" 2>/dev/null || echo /nonexistent)
if [ -x "$ESB" ] && [ -d frontend/node_modules/react ] && $PY -c "import playwright" 2>/dev/null; then
  OUT=$(mktemp -d)
  step "browser journey, MOCKED API (real Chromium)" bash -c "cd frontend && $ESB src/main.tsx --bundle --outdir=$OUT --entry-names=bundle --jsx=automatic --loader:.css=css --minify --define:process.env.NODE_ENV='\"production\"' >/dev/null && cp public/* $OUT/ && $PY e2e/farmer_journey.py $OUT"
else skip "browser journey (mocked API)" "needs frontend/node_modules, esbuild and Playwright. Run: cd frontend && npm install && pip install playwright && playwright install chromium && re-run make test"; fi

skip "real-backend browser journeys (real_backend_journey.py, verified_farmer_journey.py)" "need a running backend (FastAPI). Run: make demo-backend in one shell, then python frontend/e2e/real_backend_journey.py"
skip "docker compose" "Docker is not available here. Run: docker compose up --build"

echo; echo "================ SUMMARY"
printf 'PASSED  (%d): %s\n' "${#PASS[@]}" "$(IFS='; '; echo "${PASS[*]}")"
printf 'FAILED  (%d): %s\n' "${#FAIL[@]}" "$(IFS='; '; echo "${FAIL[*]}")"
printf 'SKIPPED (%d):\n' "${#SKIP[@]}"; for s in "${SKIP[@]}"; do echo "   - $s"; done
[ ${#FAIL[@]} -eq 0 ]
