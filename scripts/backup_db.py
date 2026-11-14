"""Consistent local backup / restore of the CytoZoe SQLite database (reviews, notes, imported data).

  python scripts/backup_db.py                 # -> runtime/backups/cytozoe-<UTC timestamp>.sqlite
  python scripts/backup_db.py --restore FILE  # stop the server first; current DB is backed up before restore

Uses SQLite's online backup API, so it is safe while the server is running (WAL mode). Backups stay in
runtime/ (gitignored) because they contain private review notes.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import config  # noqa: E402


def _unique(dest_dir: Path, prefix: str) -> Path:
    """Microsecond timestamp + counter: a backup file is never overwritten (a same-second collision once
    caused the pre-restore safety copy to replace the very backup being restored)."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    dest, n = dest_dir / f"{prefix}-{stamp}.sqlite", 1
    while dest.exists():
        dest, n = dest_dir / f"{prefix}-{stamp}-{n}.sqlite", n + 1
    return dest


def backup(dest_dir: Path, prefix: str = "cytozoe") -> Path:
    src = config.db_path()
    if not src.exists():
        raise SystemExit(f"No database at {src}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = _unique(dest_dir, prefix)
    with sqlite3.connect(src) as s, sqlite3.connect(dest) as d:
        s.backup(d)
    with sqlite3.connect(dest) as d:
        ok = d.execute("PRAGMA integrity_check").fetchone()[0]
        reviews = d.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] if d.execute(
            "SELECT 1 FROM sqlite_master WHERE name='reviews'").fetchone() else 0
    print(f"Backup written: {dest}  integrity={ok}  reviews={reviews}")
    return dest


def restore(file: Path) -> None:
    if not file.exists():
        raise SystemExit(f"Backup not found: {file}")
    with sqlite3.connect(file) as b:
        if b.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise SystemExit("Backup failed integrity_check; not restoring.")
    dest = config.db_path()
    if file.resolve() == dest.resolve():
        raise SystemExit("The backup file is the live database itself; choose a file from runtime/backups/.")
    if dest.exists():
        backup(dest.parent / "backups", prefix="pre-restore")  # safety copy of the current state first
    with sqlite3.connect(file) as s, sqlite3.connect(dest) as d:
        s.backup(d)
    print(f"Restored {file} -> {dest}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--restore", type=Path)
    a = ap.parse_args()
    if a.restore:
        restore(a.restore)
    else:
        backup(config.data_dir() / "backups")


if __name__ == "__main__":
    main()
