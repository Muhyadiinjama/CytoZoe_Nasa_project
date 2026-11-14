"""Verify staged raw NASA files against the pinned manifest and the documented schemas.

Usage: python scripts/verify_data.py [--strict]
--strict exits non-zero on any hash mismatch, missing file or schema problem.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.engines import quality  # noqa: E402
from app.errors import AppError  # noqa: E402

RAW = ROOT / "data" / "raw"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    entries = json.loads((ROOT / "data" / "manifests" / "sources.json").read_text(encoding="utf-8"))["datasets"]
    problems = 0
    for e in entries:
        path = RAW / e["file_name"]
        if not path.exists():
            print(f"[MISSING] {e['id']}: {path.name} — run scripts/fetch_data.py --dataset {e['fetch_key']}")
            problems += 1
            continue
        raw = path.read_bytes()
        sha = quality.sha256_bytes(raw)
        ok = sha == e["expected_sha256"]
        print(f"[{'HASH OK' if ok else 'HASH CHANGED'}] {e['id']}: {len(raw)} bytes sha256={sha}")
        if not ok:
            problems += 1
        try:
            if e["kind"] == "HEALTH_CMP":
                rep = quality.parse_cmp(raw)["report"]
                print(f"    samples={rep['samples']} participants={','.join(rep['participants'])} "
                      f"visits={','.join(rep['visits'])} selected_values={rep['nonmissing_values']}/{rep['selected_observations']} "
                      f"issues={len(rep['issues'])}")
            else:
                rep = quality.parse_radlab(raw)["report"]
                print(f"    raw_rows={rep['raw_rows']} unique_timestamps={rep['unique_timestamps']} "
                      f"conflict_groups={len(rep['conflict_groups'])} quarantined_rows={rep['quarantined_rows']} "
                      f"accepted_rows={rep['accepted_rows']} first={rep['first_timestamp']} last={rep['last_timestamp']}")
                for g in rep["conflict_groups"]:
                    print(f"      conflict {g['timestamp']}: " + ", ".join(f"row {r['source_row']}={r['rate_raw']}" for r in g["rows"]))
        except AppError as exc:
            print(f"    [SCHEMA] {exc.code}: {exc.message}")
            problems += 1
    if problems:
        print(f"{problems} problem(s) found.")
    return 1 if (problems and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
