"""Import staged raw NASA files into the local SQLite database (atomic, idempotent).

Usage: python scripts/import_data.py --all [--allow-new-version]
Honours CYTOZOE_DATA_DIR (default: <repo>/runtime).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config, db  # noqa: E402
from app.errors import AppError  # noqa: E402
from app.services import importer  # noqa: E402

RAW = ROOT / "data" / "raw"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="import every dataset in the manifest")
    parser.add_argument("--dataset", action="append", default=[], help="fetch key to import")
    parser.add_argument("--allow-new-version", action="store_true",
                        help="deliberately replace a loaded dataset with different source bytes")
    args = parser.parse_args()
    entries = json.loads((ROOT / "data" / "manifests" / "sources.json").read_text(encoding="utf-8"))["datasets"]
    chosen = entries if args.all else [e for e in entries if e["fetch_key"] in args.dataset]
    if not chosen:
        parser.error("choose --all or --dataset KEY")
    db.migrate()
    print(f"Database: {config.db_path()}")
    code = 0
    for e in chosen:
        path = RAW / e["file_name"]
        if not path.exists():
            print(f"[MISSING] {e['id']}: run scripts/fetch_data.py --dataset {e['fetch_key']} first.")
            code = 2
            continue
        fetched_at = None
        meta = RAW / f"{e['fetch_key']}.fetch.json"
        if meta.exists():
            fetched_at = json.loads(meta.read_text(encoding="utf-8")).get("fetched_at")
        try:
            result = importer.import_bytes(path.read_bytes(), fetched_at=fetched_at,
                                           allow_new_version=args.allow_new_version)
        except AppError as exc:
            print(f"[FAILED] {e['id']}: {exc.code} — {exc.message}")
            code = 1
            continue
        rep = result["report"]
        counts = (f"samples={rep['samples']} observations={rep['selected_observations']} values={rep['nonmissing_values']}"
                  if e["kind"] == "HEALTH_CMP" else
                  f"raw_rows={rep['raw_rows']} accepted={rep['accepted_rows']} quarantined={rep['quarantined_rows']} "
                  f"conflict_groups={len(rep['conflict_groups'])}")
        print(f"[{result['status']}] {e['id']} sha256={result['sha256'][:16]}… {counts}")
    return code


if __name__ == "__main__":
    sys.exit(main())
