#!/usr/bin/env sh
# Quick check against a running local server (default http://127.0.0.1:8000).
set -eu
BASE="${1:-http://127.0.0.1:8000}"
curl -fsS "$BASE/api/status" >/dev/null && echo "status OK"
curl -fsS "$BASE/api/health?participant=C001&sample=L-3" | grep -q '"ABOVE_SUPPLIED_UPPER_BOUND"' && echo "C001 L-3 creatinine flag OK"
curl -fsS "$BASE/api/environment" | grep -q '"raw_rows":1202' && echo "DosTel1 1,202 raw rows OK"
curl -fsS "$BASE/" | grep -q '<div id="root">' && echo "SPA served OK"
