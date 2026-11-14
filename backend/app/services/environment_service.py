"""Builds the separate ISS DosTel1 environment case using E1 quality states and E3 integration."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from .. import config
from ..engines import environment
from ..errors import AppError, not_found
from . import reviews

EVIDENCE_PREFIX = "radlab-dostel1"
SUMMARY_ID = f"{EVIDENCE_PREFIX}:summary"
BREAK_STATUSES = ("DUPLICATE_CONFLICT", "INVALID_RATE", "MISSING_VALUE")

ENV_LIMITATIONS = [
    "Separate case study: ISS Columbus module sensor, 1 March 2022. Not linked to any health participant.",
    "Absorbed dose rate at the instrument — not a personal, organ or effective dose.",
    "Estimated sensor dose covers accepted intervals only; it is not a mission-certified dose.",
    "No Gy-to-Sv conversion and no comparison with NASA exposure limits.",
    "Source timestamps carry no timezone suffix and are shown exactly as exported.",
    "The 300-second gap rule is an engineering coverage assumption, not a NASA safety threshold.",
]

_cache: dict[str, dict[str, Any]] = {}


def _epoch(ts: str) -> float:
    return (datetime.fromisoformat(ts) - datetime(1970, 1, 1)).total_seconds()


def dataset_row(conn: sqlite3.Connection) -> sqlite3.Row:
    from .health_service import verified_dataset

    return verified_dataset(conn, "ENV_RADIATION", "RadLab DosTel1")


def _compute(conn: sqlite3.Connection) -> dict[str, Any]:
    ds = dataset_row(conn)
    key = f"{ds['sha256']}:{config.RADIATION_MAX_GAP_SECONDS}"
    if key in _cache:
        return _cache[key]
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM radiation_observations WHERE dataset_id = ? ORDER BY source_row", (ds["id"],))]
    for r in rows:
        r["epoch"] = _epoch(r["source_timestamp"]) if r["quality_status"] != "INVALID_TIMESTAMP" else None
    accepted = [r for r in rows if r["quality_status"] == "ACCEPTED"]
    breaks = [r["epoch"] for r in rows if r["quality_status"] in BREAK_STATUSES and r["epoch"] is not None]
    result = environment.integrate(accepted, breaks, config.RADIATION_MAX_GAP_SECONDS)
    quality = json.loads(ds["quality_json"])
    day0 = None
    if quality.get("first_timestamp"):
        first = datetime.fromisoformat(quality["first_timestamp"])
        day0 = _epoch(first.replace(hour=0, minute=0, second=0).isoformat())
    computed = {"ds": dict(ds), "rows": rows, "integration": result, "quality": quality, "day0": day0 or 0.0}
    _cache.clear()
    _cache[key] = computed
    return computed


def conflict_evidence_id(ts: str) -> str:
    return f"{EVIDENCE_PREFIX}:conflict:{ts}"


def _source(ds: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_id": ds["id"], "title": ds["title"], "provider": ds["provider"], "file_name": ds["file_name"],
        "sha256": ds["sha256"], "provenance": ds.get("provenance"), "source_url": ds["source_url"], "download_url": ds["download_url"],
        "fetched_at": ds["fetched_at"], "imported_at": ds["imported_at"], "license_note": ds["license_note"],
        "citation": ds["citation"], "instrument_id": "DosTel1", "location": "ISS Columbus module",
    }


def environment_view(conn: sqlite3.Connection) -> dict[str, Any]:
    c = _compute(conn)
    ds, integ, quality, day0 = c["ds"], c["integration"], c["quality"], c["day0"]
    segments = []
    for i, seg in enumerate(integ["segments"]):
        segments.append({
            "index": i, "start": seg[0]["source_timestamp"], "end": seg[-1]["source_timestamp"],
            "points": [{"t": p["epoch"] - day0, "ts": p["source_timestamp"], "rate": p["rate"],
                        "cumulative": p["cumulative"], "source_row": p["source_row"]} for p in seg],
        })
    excluded_events = [
        {"t": r["epoch"] - day0, "ts": r["source_timestamp"], "status": r["quality_status"], "source_row": r["source_row"]}
        for r in c["rows"] if r["quality_status"] in BREAK_STATUSES and r["epoch"] is not None
    ]
    conflicts = []
    for g in quality.get("conflict_groups", []):
        eid = conflict_evidence_id(g["timestamp"])
        conflicts.append({**g, "evidence_id": eid, "t": _epoch(g["timestamp"]) - day0,
                          "review": reviews.review_state(conn, eid)})
    span = integ["span_seconds"]
    return {
        "dataset": _source(ds),
        "case_banner": "Separate case study · ISS Columbus · DosTel1 · 1 March 2022 · Not linked to the selected health participant.",
        "unit": "µGy/hour",
        "quality": {
            "raw_rows": quality["raw_rows"], "accepted_rows": quality["accepted_rows"],
            "excluded_rows": quality["raw_rows"] - quality["accepted_rows"],
            "quarantined_conflict_rows": quality["quarantined_rows"], "status_counts": quality["status_counts"],
            "unique_timestamps": quality["unique_timestamps"], "first_timestamp": quality["first_timestamp"],
            "last_timestamp": quality["last_timestamp"],
            "observed_max_interval_seconds": quality["observed_max_interval_seconds"],
            "observed_median_interval_seconds": quality["observed_median_interval_seconds"],
            "documented_nominal_cadence_seconds": quality["documented_nominal_cadence_seconds"],
            "timestamp_semantics": quality["timestamp_semantics"],
            "conflict_groups": conflicts,
        },
        "integration": {
            "method": integ["method"], "rule_version": integ["rule_version"],
            "max_gap_seconds": integ["max_gap_seconds"], "covered_seconds": integ["covered_seconds"],
            "span_seconds": span, "coverage_ratio": integ["covered_seconds"] / span if span else None,
            "estimated_sensor_dose_uGy": integ["estimated_sensor_dose_uGy"],
            "label": "Estimated dose over covered intervals at sensor",
            "included_intervals": integ["included_intervals"],
            "excluded_intervals": [{**e, "start_t": e["start_epoch"] - day0, "end_t": e["end_epoch"] - day0}
                                   for e in integ["excluded_intervals"]],
        },
        "segments": segments,
        "excluded_events": excluded_events,
        "rows": [{"source_row": r["source_row"], "ts": r["source_timestamp"], "rate_raw": r["rate_raw"],
                  "rate": r["rate"], "status": r["quality_status"], "detail": r["quality_detail"]} for r in c["rows"]],
        "summary_evidence_id": SUMMARY_ID,
        "summary_review": reviews.review_state(conn, SUMMARY_ID),
        "limitations": ENV_LIMITATIONS,
    }


def build_evidence(conn: sqlite3.Connection, evidence_id: str, include_review: bool = True) -> dict[str, Any]:
    c = _compute(conn)
    ds, integ, quality = c["ds"], c["integration"], c["quality"]
    base = {
        "schema_version": "1.0", "evidence_id": evidence_id, "case": "environment",
        "source": _source(ds), "limitations": ENV_LIMITATIONS,
        "context": {"instrument_id": "DosTel1", "location": "ISS Columbus module", "date": "2022-03-01",
                    "participant_id": None, "linked_health_participant": None},
    }
    if evidence_id == SUMMARY_ID:
        span = integ["span_seconds"]
        evidence = {
            **base, "kind": "ENV_OBSERVATION", "title": "DosTel1 sensor-dose estimate · 1 March 2022",
            "measurement": {
                "label": "Estimated dose over covered intervals at sensor",
                "estimated_sensor_dose_uGy": integ["estimated_sensor_dose_uGy"], "unit": "µGy",
                "covered_seconds": integ["covered_seconds"], "span_seconds": span,
                "coverage_ratio": integ["covered_seconds"] / span if span else None,
                "included_intervals": integ["included_intervals"],
                "excluded_intervals": len(integ["excluded_intervals"]),
                "raw_rows": quality["raw_rows"], "accepted_rows": quality["accepted_rows"],
                "quarantined_conflict_rows": quality["quarantined_rows"],
            },
            "comparison": {
                "method": integ["method"], "rule_version": integ["rule_version"],
                "max_gap_seconds": integ["max_gap_seconds"],
                "formulas": {
                    "interval": "dose_i = ((r_i + r_j) / 2) × (t_j − t_i) / 3600   [µGy/hour × s → µGy]",
                    "inclusion": "0 < Δt ≤ 300 s and no excluded/quarantined source event strictly inside the interval",
                    "total": "Sum of included intervals only; no extrapolation before the first or after the last record",
                },
            },
            "evidence_strength": "DIRECT_SENSOR_MEASUREMENT_WITH_APPROXIMATE_INTEGRATION",
        }
    elif evidence_id.startswith(f"{EVIDENCE_PREFIX}:conflict:"):
        ts = evidence_id.split(":conflict:", 1)[1]
        group = next((g for g in quality.get("conflict_groups", []) if g["timestamp"] == ts), None)
        if group is None:
            raise not_found("Evidence", evidence_id=evidence_id[:80])
        evidence = {
            **base, "kind": "DATA_QUALITY", "title": f"Conflicting DosTel1 readings at {ts}",
            "measurement": {"timestamp": ts, "rows": group["rows"], "unit": "µGy/hour",
                            "quality_status": "DUPLICATE_CONFLICT"},
            "comparison": {
                "method": "exact-timestamp duplicate check", "rule_version": "e1-quality-v1",
                "formulas": {
                    "rule": "Rows sharing an exact timestamp with different rates are all quarantined.",
                    "not_done": "No first-row choice, no averaging, no summing.",
                    "effect": "Intervals crossing this timestamp are excluded from the dose estimate and the plotted line breaks.",
                },
            },
            "evidence_strength": "SOURCE_DATA_QUALITY_FINDING",
        }
    else:
        raise not_found("Evidence", evidence_id=evidence_id[:80])
    if include_review:
        evidence["review"] = reviews.review_state(conn, evidence_id)
    return evidence
