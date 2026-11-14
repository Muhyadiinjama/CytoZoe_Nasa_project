"""Reviews: idempotent create per finding, optimistic versioned updates, append-only event trail."""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from ..db import Database, dumps, utcnow
from .evidence import find_evidence
from .store import Store

STATUSES = ("OPEN", "FOLLOW_UP_REQUESTED", "REVIEWED")


class ReviewError(Exception):
    def __init__(self, code: str, message: str, status: int, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code, self.message, self.status, self.details = code, message, status, details or {}


def _row(r: Any) -> dict[str, Any]:
    d = dict(r)
    ev = json.loads(d.pop("evidence_json"))
    d["evidence"] = ev
    d["case"] = ev.get("case")
    ctx = ev.get("context", {})
    d["participant_id"] = ctx.get("participant_id")
    d["instrument_id"] = ctx.get("instrument_id")
    d["title"] = review_title(ev)
    return d


def review_title(ev: dict[str, Any]) -> str:
    if ev["kind"] == "HEALTH_OBSERVATION":
        m, x = ev["measurement"], ev["context"]
        words = {"ABOVE_SUPPLIED_UPPER_BOUND": "outside supplied range (above)", "BELOW_SUPPLIED_LOWER_BOUND": "outside supplied range (below)",
                 "WITHIN_SUPPLIED_RANGE": "within supplied range", "ONE_SIDED_COMPARISON": "one-sided comparison",
                 "UNKNOWN": "no supplied range", "NOT_ASSESSABLE": "not assessable"}[m["range_status"]]
        return f"{m['label']} {x['participant_id']} {x['visit']}: {words}"
    return ev["title"]


SELECT = ("SELECT r.*, f.kind AS finding_kind, f.evidence_json, f.dataset_id, f.rule_version FROM reviews r "
          "JOIN findings f ON f.id = r.finding_id")


class Reviews:
    def __init__(self, db: Database, store: Store):
        self.db, self.store = db, store

    def create(self, evidence_id: str) -> tuple[dict[str, Any], bool]:
        with self.db.read() as con:
            ex = con.execute(SELECT + " WHERE r.finding_id = ?", (evidence_id,)).fetchone()
        if ex:
            return _row(ex), False
        ev = find_evidence(self.store, evidence_id)  # raises EvidenceNotFound
        now = utcnow()
        with self.db.tx() as con:
            if con.execute("SELECT 1 FROM reviews WHERE finding_id = ?", (evidence_id,)).fetchone():
                created = False  # lost a race with an identical request: still one review
            else:
                con.execute("INSERT OR IGNORE INTO findings(id,kind,observation_id,dataset_id,rule_version,evidence_json,created_at) VALUES (?,?,?,?,?,?,?)",
                            (evidence_id, ev["kind"], ev.get("observation_id"), ev["source"]["dataset_id"],
                             ev.get("comparison", {}).get("rule_version") or ev.get("rule_version"), dumps(ev), now))
                cur = con.execute("INSERT INTO reviews(finding_id,status,note,follow_up_date,created_at,updated_at,version) VALUES (?, 'OPEN', '', NULL, ?, ?, 1)",
                                  (evidence_id, now, now))
                con.execute("INSERT INTO review_events(review_id,action,before_json,after_json,timestamp) VALUES (?,?,?,?,?)",
                            (cur.lastrowid, "CREATED", None, dumps({"status": "OPEN"}), now))
                created = True
        with self.db.read() as con:
            return _row(con.execute(SELECT + " WHERE r.finding_id = ?", (evidence_id,)).fetchone()), created

    def update(self, review_id: int, version: int, status: str | None, note: str | None, follow_up_date: str | None,
               set_date: bool) -> dict[str, Any]:
        if status is not None and status not in STATUSES:
            raise ReviewError("VALIDATION_ERROR", "Unknown status.", 422, {"allowed": list(STATUSES)})
        if note is not None and len(note) > 4000:
            raise ReviewError("VALIDATION_ERROR", "Notes are limited to 4,000 characters.", 422)
        if set_date and follow_up_date:
            try:
                date.fromisoformat(follow_up_date)
            except ValueError as e:
                raise ReviewError("VALIDATION_ERROR", "Follow-up date must be YYYY-MM-DD.", 422) from e
        with self.db.tx() as con:
            r = con.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
            if not r:
                raise ReviewError("NOT_FOUND", "Review not found.", 404)
            if r["version"] != version:
                raise ReviewError("VERSION_CONFLICT", "This review was changed since you opened it. Your draft is kept; reload the latest version and reapply it.", 409,
                                  {"current_version": r["version"], "current": {"status": r["status"], "note": r["note"], "follow_up_date": r["follow_up_date"], "updated_at": r["updated_at"]}})
            before = {"status": r["status"], "note": r["note"], "follow_up_date": r["follow_up_date"]}
            after = dict(before)
            if status is not None:
                after["status"] = status
            if note is not None:
                after["note"] = note
            if set_date:
                after["follow_up_date"] = follow_up_date or None
            now = utcnow()
            con.execute("UPDATE reviews SET status=?, note=?, follow_up_date=?, updated_at=?, version=version+1 WHERE id=? AND version=?",
                        (after["status"], after["note"], after["follow_up_date"], now, review_id, version))
            con.execute("INSERT INTO review_events(review_id,action,before_json,after_json,timestamp) VALUES (?,?,?,?,?)",
                        (review_id, "UPDATED", dumps(before), dumps(after), now))
        return self.get(review_id)

    def get(self, review_id: int) -> dict[str, Any]:
        with self.db.read() as con:
            r = con.execute(SELECT + " WHERE r.id = ?", (review_id,)).fetchone()
            if not r:
                raise ReviewError("NOT_FOUND", "Review not found.", 404)
            ev = [dict(e) for e in con.execute("SELECT * FROM review_events WHERE review_id=? ORDER BY id", (review_id,))]
        d = _row(r)
        for e in ev:
            e["before"] = json.loads(e.pop("before_json")) if e["before_json"] else None
            e["after"] = json.loads(e.pop("after_json")) if e["after_json"] else None
        d["events"] = ev
        return d

    def by_finding(self) -> dict[str, dict[str, Any]]:
        with self.db.read() as con:
            return {r["finding_id"]: {"id": r["id"], "status": r["status"], "version": r["version"], "updated_at": r["updated_at"]}
                    for r in con.execute("SELECT id, finding_id, status, version, updated_at FROM reviews")}

    def list(self, case: str | None = None, status: str | None = None, participant: str | None = None,
             limit: int = 200, offset: int = 0) -> dict[str, Any]:
        with self.db.read() as con:
            rows = [_row(r) for r in con.execute(SELECT + " ORDER BY r.updated_at DESC, r.id DESC")]
        if case:
            rows = [r for r in rows if r["case"] == case]
        if status:
            rows = [r for r in rows if r["status"] == status]
        if participant:
            rows = [r for r in rows if r["participant_id"] == participant]
        total = len(rows)
        return {"total": total, "items": rows[offset: offset + limit], "limit": limit, "offset": offset}
