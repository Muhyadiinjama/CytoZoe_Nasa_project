"""Persistent reviews with optimistic versioning and a local audit trail.

Status is an administrative workflow state, not the subject's medical status. The evidence object is
frozen into `findings` when a review is first created so later recomputation never rewrites past reports.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from .. import db
from ..errors import AppError, not_found

STATUSES = ("OPEN", "FOLLOW_UP_REQUESTED", "REVIEWED")


def _public(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"], "finding_id": row["finding_id"], "case": row["case_kind"],
        "participant_id": row["participant_id"], "instrument_id": row["instrument_id"], "title": row["title"],
        "status": row["status"], "note": row["note"], "follow_up_date": row["follow_up_date"],
        "created_at": row["created_at"], "updated_at": row["updated_at"], "version": row["version"],
    }


def review_state(conn: sqlite3.Connection, finding_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM reviews WHERE finding_id = ?", (finding_id,)).fetchone()
    return _public(row) if row else None


def _snapshot(review: dict[str, Any]) -> dict[str, Any]:
    return {k: review[k] for k in ("status", "note", "follow_up_date", "version")}


def create(conn: sqlite3.Connection, finding_id: str, status: str, note: str,
           follow_up_date: str | None) -> tuple[dict[str, Any], bool]:
    from .evidence import resolve  # local import avoids a cycle

    existing = review_state(conn, finding_id)
    if existing:
        return existing, False
    evidence = resolve(conn, finding_id, include_review=False)
    is_health = evidence["case"] == "health"
    now = db.utc_now()
    review_id = str(uuid.uuid4())
    with db.transaction(conn):
        if review_state(conn, finding_id):  # lost a race: stay idempotent
            pass
        else:
            conn.execute(
                """INSERT OR IGNORE INTO findings (id, kind, observation_id, dataset_id, dataset_sha256,
                       rule_version, evidence_json, created_at) VALUES (?,?,?,?,?,?,?,?)""",
                (finding_id, evidence["kind"], finding_id if is_health else None, evidence["source"]["dataset_id"],
                 evidence["source"]["sha256"], evidence["comparison"]["rule_version"], json.dumps(evidence), now),
            )
            conn.execute(
                """INSERT INTO reviews (id, finding_id, case_kind, participant_id, instrument_id, title, status,
                       note, follow_up_date, created_at, updated_at, version) VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""",
                (review_id, finding_id, evidence["case"],
                 evidence["context"]["participant_id"] if is_health else None,
                 None if is_health else evidence["context"]["instrument_id"],
                 evidence["title"], status, note, follow_up_date, now, now),
            )
            created = review_state(conn, finding_id)
            conn.execute(
                "INSERT INTO review_events (review_id, action, before_json, after_json, timestamp) VALUES (?,?,?,?,?)",
                (review_id, "CREATED", None, json.dumps(_snapshot(created)), now),
            )
    result = review_state(conn, finding_id)
    return result, result["id"] == review_id


def patch(conn: sqlite3.Connection, review_id: str, expected_version: int, changes: dict[str, Any]) -> dict[str, Any]:
    with db.transaction(conn):
        row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        if row is None:
            raise not_found("Review", review_id=review_id[:40])
        current = _public(row)
        if current["version"] != expected_version:
            raise AppError(409, "VERSION_CONFLICT",
                           "This review was changed elsewhere since you opened it. Your draft was kept.",
                           {"current": current, "expected_version": expected_version})
        updated = {**current, **{k: v for k, v in changes.items() if k in ("status", "note", "follow_up_date")}}
        if _snapshot(updated) == _snapshot(current):
            return current
        now = db.utc_now()
        conn.execute(
            "UPDATE reviews SET status=?, note=?, follow_up_date=?, updated_at=?, version=version+1 WHERE id=? AND version=?",
            (updated["status"], updated["note"], updated["follow_up_date"], now, review_id, expected_version),
        )
        after = _public(conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone())
        action = "STATUS_CHANGED" if after["status"] != current["status"] else "UPDATED"
        conn.execute(
            "INSERT INTO review_events (review_id, action, before_json, after_json, timestamp) VALUES (?,?,?,?,?)",
            (review_id, action, json.dumps(_snapshot(current)), json.dumps(_snapshot(after)), now),
        )
    return after


def events(conn: sqlite3.Connection, review_id: str) -> list[dict[str, Any]]:
    return [
        {"id": r["id"], "action": r["action"], "before": json.loads(r["before_json"]) if r["before_json"] else None,
         "after": json.loads(r["after_json"]), "timestamp": r["timestamp"]}
        for r in conn.execute("SELECT * FROM review_events WHERE review_id = ? ORDER BY id", (review_id,))
    ]


def get(conn: sqlite3.Connection, review_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT r.*, f.evidence_json, f.dataset_sha256, f.rule_version FROM reviews r JOIN findings f ON f.id = r.finding_id WHERE r.id = ?",
        (review_id,),
    ).fetchone()
    if row is None:
        raise not_found("Review", review_id=review_id[:40])
    return {**_public(row), "evidence_snapshot": json.loads(row["evidence_json"]),
            "dataset_sha256": row["dataset_sha256"], "rule_version": row["rule_version"],
            "events": events(conn, review_id)}


def list_reviews(conn: sqlite3.Connection, case: str | None, status: str | None, participant: str | None,
                 page: int, page_size: int) -> dict[str, Any]:
    where, args = [], []
    if case:
        where.append("case_kind = ?")
        args.append(case)
    if status:
        where.append("status = ?")
        args.append(status)
    if participant:
        where.append("participant_id = ?")
        args.append(participant)
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM reviews {clause}", args).fetchone()[0]
    rows = conn.execute(
        f"SELECT * FROM reviews {clause} ORDER BY updated_at DESC, id LIMIT ? OFFSET ?",
        [*args, page_size, (page - 1) * page_size],
    ).fetchall()
    return {"items": [_public(r) for r in rows], "total": total, "page": page, "page_size": page_size}


def all_full(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    ids = [r["id"] for r in conn.execute("SELECT id FROM reviews ORDER BY case_kind, created_at, id")]
    return [get(conn, i) for i in ids]
