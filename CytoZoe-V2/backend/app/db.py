"""SQLite access: WAL mode, foreign keys, tracked migrations, short transactions."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def dumps(obj: Any) -> str:
    # allow_nan=False: JSON must never contain NaN/Infinity
    return json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


class Database:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)  # explicit BEGIN/COMMIT below
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("PRAGMA synchronous = NORMAL")
        return con

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        con = self._connect()
        try:
            yield con
        finally:
            con.close()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        """One atomic write transaction. Any exception rolls everything back."""
        con = self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
        finally:
            con.close()

    def migrate(self) -> None:
        con = self._connect()
        try:
            con.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
            done = {r["name"] for r in con.execute("SELECT name FROM schema_migrations")}
            for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
                if f.name in done:
                    continue
                con.execute("BEGIN IMMEDIATE")
                try:
                    for stmt in _split_sql(f.read_text(encoding="utf-8")):
                        con.execute(stmt)
                    con.execute("INSERT INTO schema_migrations(name, applied_at) VALUES (?, ?)", (f.name, utcnow()))
                    con.execute("COMMIT")
                except BaseException:
                    con.execute("ROLLBACK")
                    raise
        finally:
            con.close()

    def status(self) -> dict[str, Any]:
        try:
            with self.read() as con:
                applied = [r["name"] for r in con.execute("SELECT name FROM schema_migrations ORDER BY name")]
                con.execute("SELECT 1").fetchone()
            return {"ok": True, "migrations": applied}
        except sqlite3.Error as e:  # pragma: no cover - surfaced to UI as DB status
            return {"ok": False, "error": type(e).__name__}


def _split_sql(text: str) -> list[str]:
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("--")]
    out, buf = [], []
    for ln in lines:
        buf.append(ln.split("--")[0] if "--" in ln and "'" not in ln.split("--")[0] else ln)
        if ln.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        out.append(tail)
    return out
