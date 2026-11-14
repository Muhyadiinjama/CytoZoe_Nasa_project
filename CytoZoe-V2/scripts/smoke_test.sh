#!/usr/bin/env bash
# Starts the service on a temporary database, checks the core API story, stops it. Exit 0 = pass.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}; PORT=${SMOKE_PORT:-8799}
export CYTOZOE_DATA_DIR="$(mktemp -d)"
$PY scripts/import_data.py --all >/dev/null
$PY -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $PORT --log-level warning & PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT
for i in $(seq 1 60); do curl -sf "http://127.0.0.1:$PORT/api/status" >/dev/null && break; sleep 0.25; done
B="http://127.0.0.1:$PORT"
$PY - "$B" <<'PYEOF'
import json, sys, urllib.request
B = sys.argv[1]
def call(m, p, body=None):
    r = urllib.request.Request(B + p, data=json.dumps(body).encode() if body is not None else None, method=m, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r) as resp: return json.loads(resp.read())
h = call("GET", "/api/health?participant=C001&sample=L-3")
c = next(x for x in h["cards"] if x["measurement"]["marker"] == "creatinine")
assert c["measurement"]["value"] == 1.37 and c["measurement"]["range_status"] == "ABOVE_SUPPLIED_UPPER_BOUND"
assert abs(c["comparison"]["baseline"] - 1.2366667) < 1e-6
r = call("POST", "/api/reviews", {"evidence_id": c["evidence_id"]})
r = call("PATCH", f"/api/reviews/{r['id']}", {"version": r["version"], "status": "FOLLOW_UP_REQUESTED", "note": "smoke test note"})
e = call("GET", "/api/environment")
assert e["quality"]["raw_rows"] == 1202 and e["quality"]["conflict_groups"] == 4
p = call("GET", "/api/export?format=json")
assert p["health"]["reviews"][0]["note"] == "smoke test note"
print("smoke test: PASS")
PYEOF
