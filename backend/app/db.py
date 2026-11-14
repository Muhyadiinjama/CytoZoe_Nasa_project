"""SQLite access with versioned, tracked SQL migrations (PRAGMA user_version)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from . import config


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _migrations() -> list[tuple[int, str]]:
    items = []
    for path in sorted(config.MIGRATIONS_DIR.glob("*.sql")):
        items.append((int(path.name.split("_", 1)[0]), path.read_text(encoding="utf-8")))
    return items


def schema_version() -> int:
    migrations = _migrations()
    return migrations[-1][0] if migrations else 0


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.db_path(), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def migrate() -> int:
    conn = connect()
    try:
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        for number, sql in _migrations():
            if number <= current:
                continue
            conn.execute("BEGIN")
            try:
                for statement in [s for s in sql.split(";\n") if s.strip()]:
                    conn.execute(statement)
                conn.execute(f"PRAGMA user_version = {int(number)}")
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            current = number
        return current
    finally:
        conn.close()


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
