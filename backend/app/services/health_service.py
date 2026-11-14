"""Builds canonical health evidence objects from imported OSD-575 rows using E2."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..engines import health
from ..engines.quality import CMP_MARKERS, MARKER_NAMES, PREFLIGHT_VISITS, VISITS, cmp_columns
from ..errors import AppError, bad_request, not_found
from . import reviews

EVIDENCE_SCHEMA = "1.0"
EVIDENCE_PREFIX = "osd575-cmp"
MARKER_ORDER = [stem for stem, _, _ in CMP_MARKERS]

HEALTH_LIMITATIONS = [
    "Historical Inspiration4 research sample — not live astronaut monitoring.",
    "Seven sparse blood draws per participant; not continuous vital-sign monitoring.",
    "Not a diagnosis. Supplied ranges are the laboratory reference bounds recorded in the source file.",
    "Four anonymised participants: not a clinical validation cohort.",
    "Not matched to the ISS DosTel1 radiation record; the two case studies cannot be paired.",
]
STRENGTH = "DIRECT_RESEARCH_MEASUREMENT_WITH_DESCRIPTIVE_COMPARISON"


def visit_label(visit: str) -> str:
    phase = VISITS[visit]["phase"]
    return f"{visit} · {'Preflight' if phase == 'PREFLIGHT' else 'Postflight'}"


def dataset_row(conn: sqlite3.Connection) -> sqlite3.Row:
    return verified_dataset(conn, "HEALTH_CMP", "OSD-575 health")


def verified_dataset(conn: sqlite3.Connection, kind: str, label: str) -> sqlite3.Row:
    """NASA-only endpoints serve a dataset only when its provenance is NASA_PINNED_VERIFIED."""
    row = conn.execute("SELECT * FROM datasets WHERE kind = ?", (kind,)).fetchone()
    if row is None:
        raise AppError(404, "NO_DATA", f"The {label} dataset has not been imported yet. "
                       "Run the documented setup (scripts/fetch_data.py then scripts/import_data.py).")
    if "provenance" in row.keys() and row["provenance"] != "NASA_PINNED_VERIFIED":
        raise AppError(409, "SOURCE_HASH_MISMATCH",
                       f"The loaded {label} data is not a registered verified NASA snapshot, so it is not shown. "
                       "Re-import the pinned file (scripts/import_data.py --allow-new-version).",
                       {"dataset_id": row["id"], "provenance": row["provenance"]})
    return row


def participants(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    dataset_row(conn)
    rows = conn.execute(
        """SELECT DISTINCT participant_id, sample_id, visit, phase, relative_day, visit_order
           FROM health_observations ORDER BY participant_id, visit_order"""
    ).fetchall()
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        p = out.setdefault(r["participant_id"], {"participant_id": r["participant_id"], "samples": []})
        p["samples"].append({
            "sample_id": r["sample_id"], "visit": r["visit"], "phase": r["phase"],
            "relative_day": r["relative_day"], "visit_order": r["visit_order"], "label": visit_label(r["visit"]),
        })
    return list(out.values())


def _validate(conn, participant: str, visit: str | None = None, marker: str | None = None) -> None:
    exists = conn.execute(
        "SELECT 1 FROM health_observations WHERE participant_id = ? LIMIT 1", (participant,)
    ).fetchone()
    if not exists:
        raise not_found("Participant", participant=participant[:20])
    if visit is not None and visit not in VISITS:
        raise not_found("Visit", visit=visit[:20])
    if marker is not None and marker not in MARKER_NAMES:
        raise bad_request("UNSUPPORTED_MARKER", "Marker must be one of the five selected markers.",
                          allowed=MARKER_ORDER)


def _marker_rows(conn, participant: str, marker: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM health_observations WHERE participant_id = ? AND marker = ? ORDER BY visit_order",
        (participant, marker),
    ).fetchall()


def _source_block(ds: sqlite3.Row, obs: sqlite3.Row) -> dict[str, Any]:
    unit = obs["source_unit"]
    value_col, low_col, high_col = cmp_columns(obs["marker"], unit)
    return {
        "dataset_id": ds["id"], "title": ds["title"], "provider": ds["provider"], "file_name": ds["file_name"],
        "sha256": ds["sha256"], "provenance": ds["provenance"] if "provenance" in ds.keys() else None,
        "source_row": obs["source_row"], "file_line": obs["source_row"] + 1,
        "sample_name": obs["sample_id"],
        "source_columns": {"value": value_col, "range_min": low_col, "range_max": high_col},
        "raw_value": obs["value_raw"], "source_unit": unit,
        "source_url": ds["source_url"], "download_url": ds["download_url"],
        "fetched_at": ds["fetched_at"], "imported_at": ds["imported_at"],
        "license_note": ds["license_note"], "citation": ds["citation"],
    }


def build_evidence(conn: sqlite3.Connection, participant: str, visit: str, marker: str,
                   include_review: bool = True) -> dict[str, Any]:
    ds = dataset_row(conn)
    _validate(conn, participant, visit, marker)
    rows = _marker_rows(conn, participant, marker)
    obs = next((r for r in rows if r["visit"] == visit), None)
    if obs is None:
        raise not_found("Sample", participant=participant, visit=visit)
    pre = [r for r in rows if r["visit"] in PREFLIGHT_VISITS]
    base = health.baseline(r["value"] for r in pre)
    cmp = health.compare(obs["value"], base["value"] if base else None)
    status = health.range_status(obs["value"], obs["range_low"], obs["range_high"])
    evidence_id = f"{EVIDENCE_PREFIX}:{obs['sample_id']}:{marker}"
    is_pre = obs["phase"] == "PREFLIGHT"
    evidence = {
        "schema_version": EVIDENCE_SCHEMA,
        "evidence_id": evidence_id,
        "kind": "HEALTH_OBSERVATION",
        "case": "health",
        "title": f"{MARKER_NAMES[marker]} · {participant} · {visit}",
        "source": _source_block(ds, obs),
        "context": {
            "participant_id": participant, "sample_id": obs["sample_id"], "phase": obs["phase"], "visit": visit,
            "visit_label": visit_label(visit), "relative_day": obs["relative_day"],
            "relative_day_reference": "days before launch" if is_pre else "days after return",
        },
        "measurement": {
            "marker": marker, "marker_name": MARKER_NAMES[marker], "value": obs["value"], "unit": obs["unit"],
            "range_low": obs["range_low"], "range_high": obs["range_high"], "range_status": status,
            "needs_review": health.needs_review(status),
        },
        "comparison": {
            "method": "retrospective_preflight_arithmetic_mean",
            "baseline": base["value"] if base else None,
            "n": base["n"] if base else len([r for r in pre if r["value"] is not None]),
            "baseline_available": base is not None,
            "baseline_values": [
                {"visit": r["visit"], "sample_id": r["sample_id"], "value": r["value"], "source_row": r["source_row"]}
                for r in pre
            ],
            "includes_selected_sample": is_pre and obs["value"] is not None,
            "delta": cmp["delta"], "percent_delta": cmp["percent_delta"],
            "rule_version": health.RULE_VERSION,
            "formulas": {
                "baseline": "B = mean of available preflight values (L-92, L-44, L-3) for this participant and marker; requires n ≥ 2",
                "delta": "Δ = x − B",
                "percent_delta": "%Δ = 100 × (x − B) / B, only when B ≠ 0",
                "range_status": "outside only if x < supplied lower bound or x > supplied upper bound; equal to a bound is within",
            },
        },
        "evidence_strength": STRENGTH,
        "limitations": HEALTH_LIMITATIONS,
    }
    if include_review:
        evidence["review"] = reviews.review_state(conn, evidence_id)
    return evidence


def parse_evidence_id(evidence_id: str) -> tuple[str, str, str]:
    try:
        prefix, sample_id, marker = evidence_id.split(":")
    except ValueError as exc:
        raise not_found("Evidence", evidence_id=evidence_id[:80]) from exc
    from ..engines.quality import SAMPLE_RE
    match = SAMPLE_RE.match(sample_id)
    if prefix != EVIDENCE_PREFIX or not match or marker not in MARKER_NAMES:
        raise not_found("Evidence", evidence_id=evidence_id[:80])
    return match.group(1), match.group(2), marker


def overview(conn: sqlite3.Connection, participant: str, visit: str) -> dict[str, Any]:
    ds = dataset_row(conn)
    _validate(conn, participant, visit)
    cards = [build_evidence(conn, participant, visit, m) for m in MARKER_ORDER]
    to_review = [c for c in cards if c["measurement"]["needs_review"]]
    counts = {s: 0 for s in reviews.STATUSES}
    for r in conn.execute(
        "SELECT status, COUNT(*) AS n FROM reviews WHERE case_kind = 'health' AND participant_id = ? GROUP BY status",
        (participant,),
    ):
        counts[r["status"]] = r["n"]
    quality = json.loads(ds["quality_json"])
    return {
        "participant_id": participant,
        "visit": visit,
        "visit_label": visit_label(visit),
        "cards": cards,
        "to_review": [c["evidence_id"] for c in to_review],
        "participant_review_counts": counts,
        "dataset": {
            "id": ds["id"], "title": ds["title"], "sha256": ds["sha256"], "samples": quality.get("samples"),
            "participants": len(quality.get("participants", [])), "visits": quality.get("visits"),
            "nonmissing_values": quality.get("nonmissing_values"),
        },
    }


def replay(conn: sqlite3.Connection, participant: str) -> dict[str, Any]:
    """Visit-by-visit replay using only information available at each visit (prospective baseline).

    Unlike the retrospective baseline used elsewhere, frame k's baseline uses only preflight visits strictly
    BEFORE visit k (no temporal leakage: the value being compared never contributes to its own baseline).
    State transition: after frame k is revealed, its preflight value becomes available to frames > k.
    Replay is read-only: it never writes to the database.
    """
    dataset_row(conn)
    _validate(conn, participant)
    rows = conn.execute(
        "SELECT * FROM health_observations WHERE participant_id = ? ORDER BY visit_order", (participant,)
    ).fetchall()
    visits = sorted({r["visit"] for r in rows}, key=lambda v: VISITS[v]["order"])
    frames = []
    baseline_announced = False
    for k, visit in enumerate(visits):
        seen_pre = [v for v in visits[:k] if v in PREFLIGHT_VISITS]  # strictly earlier visits only
        cards, events = [], []
        phase = VISITS[visit]["phase"]
        events.append({"kind": "sample", "text": f"New historical sample: {visit_label(visit)} ({abs(VISITS[visit]['relative_day'])} {'days before launch' if phase == 'PREFLIGHT' else 'days after return'})."})
        for marker in MARKER_ORDER:
            mrows = [r for r in rows if r["marker"] == marker]
            obs = next(r for r in mrows if r["visit"] == visit)
            base = health.baseline(r["value"] for r in mrows if r["visit"] in seen_pre)
            cmp = health.compare(obs["value"], base["value"] if base else None)
            status = health.range_status(obs["value"], obs["range_low"], obs["range_high"])
            cards.append({
                "evidence_id": f"{EVIDENCE_PREFIX}:{obs['sample_id']}:{marker}", "marker": marker,
                "marker_name": MARKER_NAMES[marker], "value": obs["value"], "unit": obs["unit"],
                "range_low": obs["range_low"], "range_high": obs["range_high"], "range_status": status,
                "needs_review": health.needs_review(status),
                "baseline_so_far": base["value"] if base else None, "n_so_far": base["n"] if base else len(
                    [r for r in mrows if r["visit"] in seen_pre and r["value"] is not None]),
                "delta": cmp["delta"], "percent_delta": cmp["percent_delta"], "source_row": obs["source_row"],
            })
            if health.needs_review(status):
                bound = obs["range_high"] if status == health.ABOVE else obs["range_low"]
                side = "above the supplied upper" if status == health.ABOVE else "below the supplied lower"
                events.append({"kind": "flag", "marker": marker, "evidence_id": cards[-1]["evidence_id"],
                               "text": f"{MARKER_NAMES[marker]} {obs['value']:g} {obs['unit']} is {side} bound {bound:g} {obs['unit']}. Needs review — not a diagnosis."})
        if not baseline_announced and len(seen_pre) >= 2:
            baseline_announced = True
            events.append({"kind": "baseline", "text": f"Personal baseline available from {len(seen_pre)} earlier preflight samples ({', '.join(seen_pre)})."})
        frames.append({"visit": visit, "visit_label": visit_label(visit), "phase": phase, "visit_order": VISITS[visit]["order"],
                       "baseline_context": "PROSPECTIVE_PRIOR_PREFLIGHT", "baseline_visits": seen_pre,
                       "cards": cards, "events": events})
    return {"participant_id": participant, "mode": "HISTORICAL_REPLAY",
            "label": "Historical replay · each step shows only what was known before that visit · not live",
            "baseline_method": "prospective mean of preflight visits strictly before the replayed visit (requires n ≥ 2)",
            "rule_version": health.RULE_VERSION, "frames": frames}


def trend(conn: sqlite3.Connection, participant: str, marker: str) -> dict[str, Any]:
    dataset_row(conn)
    _validate(conn, participant, marker=marker)
    rows = _marker_rows(conn, participant, marker)
    pre = [r for r in rows if r["visit"] in PREFLIGHT_VISITS]
    base = health.baseline(r["value"] for r in pre)
    bounds = {(r["range_low"], r["range_high"]) for r in rows}
    points = []
    for r in rows:
        status = health.range_status(r["value"], r["range_low"], r["range_high"])
        points.append({
            "evidence_id": f"{EVIDENCE_PREFIX}:{r['sample_id']}:{marker}",
            "sample_id": r["sample_id"], "visit": r["visit"], "visit_label": visit_label(r["visit"]),
            "phase": r["phase"], "visit_order": r["visit_order"], "relative_day": r["relative_day"],
            "value": r["value"], "range_low": r["range_low"], "range_high": r["range_high"],
            "range_status": status, "needs_review": health.needs_review(status), "source_row": r["source_row"],
        })
    consistent = len(bounds) == 1
    only = next(iter(bounds)) if consistent else (None, None)
    return {
        "participant_id": participant, "marker": marker, "marker_name": MARKER_NAMES[marker],
        "unit": rows[0]["unit"] if rows else None,
        "points": points,
        "baseline": {"value": base["value"] if base else None, "n": base["n"] if base else 0,
                     "available": base is not None, "method": "retrospective_preflight_arithmetic_mean",
                     "visits": list(PREFLIGHT_VISITS)},
        "bounds_consistent": consistent,
        "range_low": only[0], "range_high": only[1],
        "x_axis_note": "Categorical visit order. Visits are not equally spaced in time; L = days before launch, R = days after return.",
        "rule_version": health.RULE_VERSION,
    }
