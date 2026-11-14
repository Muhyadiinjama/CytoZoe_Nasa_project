#!/usr/bin/env sh
# CytoZoe one-time setup (macOS / Linux). Network is needed only for this step.
set -eu
cd "$(dirname "$0")/.."

[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e './backend[dev]'

(cd frontend && npm ci && npm run build)

.venv/bin/python scripts/fetch_data.py --all
.venv/bin/python scripts/verify_data.py --strict
.venv/bin/python scripts/import_data.py --all
echo "Setup complete. Start with: sh scripts/start.sh  ->  http://127.0.0.1:8000"
