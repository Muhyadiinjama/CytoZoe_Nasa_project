"""Readiness diagnostics: one place that decides whether the local service can serve trusted results."""
from __future__ import annotations

import os
import sqlite3
from typing import Any

from .. import config, db
from ..sources import manifest

# Startup problems recorded by create_app (e.g. a corrupt database) so liveness still answers.
STARTUP: dict[str, str | None] = {"error_code": None, "error_message": None}


def _check(name: str, ok: bool, code: str, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": ok, "code": None if ok else code, "detail": detail}


def readiness() -> dict[str, Any]:
    """Ordered checks; the first failing check sets `state`. Never raises."""
    checks: list[dict[str, Any]] = []
    if STARTUP["error_code"]:
        checks.append(_check("database", False, STARTUP["error_code"], STARTUP["error_message"] or ""))
        return {"ready": False, "state": STARTUP["error_code"], "checks": checks}
    try:
        with db.session() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            rows = conn.execute("SELECT id, kind, sha256, provenance FROM datasets").fetchall() \
                if _has_column(conn, "datasets", "provenance") else \
                [dict(r) | {"provenance": None} for r in conn.execute("SELECT id, kind, sha256 FROM datasets")]
    except sqlite3.Error:
        checks.append(_check("database", False, "DATABASE_UNAVAILABLE", "The local SQLite database cannot be opened or read."))
        return {"ready": False, "state": "DATABASE_UNAVAILABLE", "checks": checks}
    checks.append(_check("database", True, "", "SQLite reachable"))
    latest = db.schema_version()
    checks.append(_check("migrations", version == latest, "MIGRATION_PENDING",
                         f"schema version {version} of {latest}"))
    pinned = {e["kind"]: e for e in manifest()["datasets"]}
    by_kind = {r["kind"]: r for r in rows}
    for kind, entry in pinned.items():
        row = by_kind.get(kind)
        if row is None:
            checks.append(_check(f"dataset:{entry['id']}", False, "DATASET_NOT_IMPORTED",
                                 "Not imported. Run: python scripts/import_data.py --all"))
        elif row["sha256"] not in _accepted(entry) or (row["provenance"] not in (None, "NASA_PINNED_VERIFIED")):
            checks.append(_check(f"dataset:{entry['id']}", False, "SOURCE_HASH_MISMATCH",
                                 "Loaded bytes are not a registered verified NASA snapshot."))
        else:
            checks.append(_check(f"dataset:{entry['id']}", True, "", f"verified {row['sha256'][:12]}…"))
    require_ui = os.environ.get("CYTOZOE_REQUIRE_FRONTEND", "0") == "1"
    built = (config.FRONTEND_DIST / "index.html").exists()
    checks.append(_check("frontend_build", built or not require_ui, "FRONTEND_NOT_BUILT",
                         "built" if built else "frontend/dist missing (run: npm run build)"))
    failed = next((c for c in checks if not c["ok"]), None)
    return {"ready": failed is None, "state": "READY" if failed is None else failed["code"], "checks": checks}


def _accepted(entry: dict[str, Any]) -> set[str]:
    return {entry["expected_sha256"], *entry.get("accepted_sha256", [])}


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(r[1] == column for r in conn.execute(f"PRAGMA table_info({table})"))
