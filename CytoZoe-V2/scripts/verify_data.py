#!/usr/bin/env python3
"""Check data/raw against the manifest: SHA-256 and the expected counts from parsing.

    python scripts/verify_data.py           # report
    python scripts/verify_data.py --strict  # non-zero exit on any mismatch
"""
from __future__ import annotations

import argparse
import sys

from _common import RAW, manifest, sha256_file
from app.engines import ingest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    problems = 0
    for d in manifest():
        p = RAW / d["file_name"]
        if not p.exists():
            print(f"MISSING {p.name}: run scripts/fetch_data.py --dataset {d['key']} or copy it into data/raw/")
            problems += 1
            continue
        sha = sha256_file(p)
        ok_sha = sha == d["sha256"]
        print(f"{p.name}: sha256 {'OK' if ok_sha else 'DIFFERENT (' + sha + ')'}")
        problems += 0 if ok_sha else 1
        data = p.read_bytes()
        e = d["expected"]
        if d["kind"] == "HEALTH_CMP":
            q = ingest.parse_health_csv(data, p.name).quality
            checks = {"rows": (q["rows"], e["rows"]), "participants": (q["participants"], e["participants"]),
                      "visits": (q["visits"], e["visits"]), "nonmissing": (q["nonmissing_total"], e["nonmissing_selected_values"]),
                      "bom": (data.startswith(b"\xef\xbb\xbf"), e["utf8_bom"])}
        else:
            q = ingest.parse_radiation_csv(data, p.name).quality
            pi = q["per_instrument"]["DosTel1"]
            checks = {"raw_rows": (pi["raw_rows"], e["raw_rows"]), "unique_timestamps": (pi["unique_timestamps"], e["unique_timestamps"]),
                      "conflict_groups": ([c["source_timestamp"][11:] for c in q["conflict_groups"]], e["conflict_groups"]),
                      "quarantined": (pi["quarantined_rows"], e["quarantined_rows"]), "accepted": (pi["accepted_rows"], e["accepted_rows"])}
        for k, (got, want) in checks.items():
            ok = got == want
            problems += 0 if ok else 1
            print(f"  {k}: {'OK' if ok else 'MISMATCH'} (found {got}{'' if ok else ', expected ' + str(want)})")
    print("verify:", "all checks passed" if not problems else f"{problems} problem(s)")
    return 1 if (problems and a.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
