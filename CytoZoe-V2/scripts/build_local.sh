#!/usr/bin/env bash
# One-time local setup after dependencies are installed: verify data, import it, build the frontend.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== verify source files"; $PY scripts/verify_data.py --strict
echo "== import into local SQLite"; $PY scripts/import_data.py --all
echo "== typecheck + build frontend"; (cd frontend && npm run typecheck && npm run build)
echo "done. Start with scripts/start.sh"
