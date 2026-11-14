"""Start an isolated CytoZoe server for end-to-end tests.

Usage: python scripts/e2e_server.py --port 8010 [--fresh] [--empty]
Data lives in runtime/e2e-<port>/ (test-only, gitignored). --fresh wipes it first; --empty skips import
(used to exercise the NO_DATA state). Requires the pinned raw files in data/raw unless --empty.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8010)
    p.add_argument("--fresh", action="store_true")
    p.add_argument("--empty", action="store_true")
    args = p.parse_args()
    data_dir = ROOT / "runtime" / f"e2e-{args.port}"
    if args.fresh and data_dir.exists():
        shutil.rmtree(data_dir)
    os.environ["CYTOZOE_DATA_DIR"] = str(data_dir)
    from app import db
    from app.services import importer

    db.migrate()
    if not args.empty:
        for name in ("LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv", "radlab_DosTel1_2022-03-01.csv"):
            importer.import_bytes((ROOT / "data" / "raw" / name).read_bytes())
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
