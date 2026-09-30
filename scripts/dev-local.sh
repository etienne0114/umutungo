#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"
API_PID=""
STARTED_API=0

cleanup() {
  if [[ "$STARTED_API" -eq 1 && -n "$API_PID" ]]; then
    kill "$API_PID" 2>/dev/null || true
    wait "$API_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

if curl --fail --silent --show-error --max-time 2 \
  http://127.0.0.1:8000/health >/dev/null 2>&1; then
  printf 'Using the existing API at http://127.0.0.1:8000\n'
else
  if [[ -x "$ROOT_DIR/.venv/bin/uvicorn" ]]; then
    UVICORN="$ROOT_DIR/.venv/bin/uvicorn"
  elif command -v uvicorn >/dev/null 2>&1; then
    UVICORN="$(command -v uvicorn)"
  else
    printf 'Uvicorn is missing. Install apps/api dependencies or activate its Python environment.\n' >&2
    exit 1
  fi

  cd "$API_DIR"
  "$UVICORN" govasset_api.main:app --reload --host 127.0.0.1 --port 8000 &
  API_PID=$!
  STARTED_API=1

  ready=0
  for _ in $(seq 1 30); do
    if curl --fail --silent --show-error --max-time 2 \
      http://127.0.0.1:8000/health >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 1
  done
  if [[ "$ready" -ne 1 ]]; then
    printf 'The local API did not become healthy at http://127.0.0.1:8000/health.\n' >&2
    exit 1
  fi
fi

if curl --fail --silent --show-error --max-time 2 \
  http://127.0.0.1:3000/ 2>/dev/null | grep -qi 'Umutungo'; then
  printf 'The Umutungo frontend is already running at http://localhost:3000\n'
  exit 0
fi

cd "$WEB_DIR"
npm run dev:web
