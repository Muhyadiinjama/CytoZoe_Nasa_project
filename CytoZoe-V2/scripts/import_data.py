#!/usr/bin/env python3
"""Import the staged source files into the local SQLite database (atomic, idempotent by hash).

    python scripts/import_data.py --all
Uses CYTOZOE_DATA_DIR (default: runtime/). The running app does not need to be stopped.
"""
from __future__ import annotations

import argparse
import sys

from _common import RAW, manifest
from app.config import load_settings
from app.db import Database
from app.engines.ingest import DataError
from app.services.store import Store


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="import every dataset in the manifest")
    ap.add_argument("--dataset", choices=[d["key"] for d in manifest()])
    a = ap.parse_args()
    s = load_settings()
    store = Store(Database(s.db_path))
    todo = manifest() if a.all or not a.dataset else [d for d in manifest() if d["key"] == a.dataset]
    rc = 0
    for d in todo:
        p = RAW / d["file_name"]
        if not p.exists():
            print(f"MISSING {p}: run scripts/fetch_data.py first")
            rc = 1
            continue
        try:
            rep = store.import_file(d["kind"], p.read_bytes(), p.name)
        except DataError as e:
            print(f"FAILED {p.name}: {e.code} {e.message} {e.details}")
            rc = 1
            continue
        print(f"{rep['status']}: {p.name} -> {rep['dataset_id']} (db {s.db_path})")
    return rc


if __name__ == "__main__":
    sys.exit(main())
