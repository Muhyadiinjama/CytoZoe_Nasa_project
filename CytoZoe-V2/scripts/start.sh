#!/usr/bin/env bash
# Start the local service on http://127.0.0.1:8000 (loopback only). Ctrl+C to stop.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
[ -f frontend/dist/index.html ] || { echo "Frontend not built: run scripts/build_local.sh first"; exit 1; }
$PY scripts/import_data.py --all >/dev/null || echo "note: data import reported a problem (see scripts/import_data.py --all)"
echo "CytoZoe: http://127.0.0.1:${CYTOZOE_PORT:-8000}/overview"
exec $PY -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port "${CYTOZOE_PORT:-8000}"
