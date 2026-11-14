#!/usr/bin/env sh
# Start CytoZoe on loopback only (macOS / Linux). Works with the internet disconnected.
cd "$(dirname "$0")/.."
echo "CytoZoe running at http://127.0.0.1:8000  (Ctrl+C to stop)"
exec .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
