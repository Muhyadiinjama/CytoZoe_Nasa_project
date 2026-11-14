"""Mission Health Intelligence Brief (MissionBriefV1).

Assembled ONLY from canonical evidence objects produced by health_service.build_evidence — no second
calculation engine. Every number in the brief is the same object/value served by /api/evidence/{id} and
frozen into exports. Text uses fixed verified templates: no diagnosis, cause, severity rank or LLM.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from .. import db
from ..engines import environment, health, quality
from ..errors import bad_request
from . import explain, health_service

NO_FINDINGS_TEXT = ("No displayed measurements are outside their supplied ranges; "
                    "this is not an overall health assessment.")
CASE_SEPARATION = ("The ISS DosTel1 radiation record is a separate environmental case (different mission, date and "
                   "people). It is never combined with this participant's results.")
QUESTIONS = [
    {"id": "EXPLAIN_RESULT", "label": "What changed?"},
    {"id": "HOW_CALCULATED", "label": "How was the comparison calculated?"},
    {"id": "SOURCE_LOCATION", "label": "Where did this number come from?"},
    {"id": "LIMITATIONS", "label": "What are the limitations?"},
    {"id": "FOLLOW_UP_OPTIONS", "label": "What follow-up can be recorded?"},
]


def _bounds_text(m: dict[str, Any]) -> str:
    lo, hi, u = m["range_low"], m["range_high"], m["unit"]
    if lo is not None and hi is not None:
        return f"Supplied laboratory range {explain.fmt(lo)}–{explain.fmt(hi)} {u}."
    if hi is not None:
        return f"Only a supplied upper bound ({explain.fmt(hi)} {u}) is recorded."
    if lo is not None:
        return f"Only a supplied lower bound ({explain.fmt(lo)} {u}) is recorded."
    return "No supplied laboratory range is recorded for this sample."


def _item(ev: dict[str, Any]) -> dict[str, Any]:
    m, c, ctx, s = ev["measurement"], ev["comparison"], ev["context"], ev["source"]
    u = m["unit"]
    if m["value"] is None:
        observed = (f"No {m['marker_name'].lower()} value is recorded for {ctx['participant_id']} at "
                    f"{ctx['visit_label']} (data row {s['source_row']}). Nothing is inferred for the missing value.")
    else:
        observed = (f"{m['marker_name']} {explain.fmt(m['value'])} {u} at {ctx['visit_label']} "
                    f"({abs(ctx['relative_day'])} {ctx['relative_day_reference']}); historical research sample, "
                    f"data row {s['source_row']}.")
    parts = [_bounds_text(m)]
    if c["baseline_available"]:
        used = ", ".join(f"{b['visit']} {explain.fmt(b['value'])}" for b in c["baseline_values"] if b["value"] is not None)
        parts.append(f"Retrospective preflight mean {explain.fmt(c['baseline'])} {u} (n = {c['n']}: {used}).")
        if c["delta"] is not None:
            pct = f" ({explain.signed(c['percent_delta'], 2)}%)" if c["percent_delta"] is not None else ""
            parts.append(f"Different from that mean by {explain.signed(c['delta'])} {u}{pct}; descriptive, not an abnormality threshold.")
    else:
        parts.append(f"No personal baseline: fewer than two preflight values (n = {c['n']}).")
    why = None
    if m["range_status"] == health.ABOVE:
        why = f"The measured value is above the supplied upper bound ({explain.fmt(m['range_high'])} {u})."
    elif m["range_status"] == health.BELOW:
        why = f"The measured value is below the supplied lower bound ({explain.fmt(m['range_low'])} {u})."
    limits = ["This individual measurement does not establish a diagnosis."]
    limits.append("Collected before launch, so it cannot reflect a spaceflight effect." if ctx["phase"] == "PREFLIGHT"
                  else "Descriptive comparison only; no cause is inferred.")
    if c["includes_selected_sample"]:
        limits.append("The preflight mean includes this sample, so the comparison is retrospective.")
    action = ("Record a reviewer follow-up note and status. CytoZoe does not recommend clinical action."
              if m["needs_review"] else
              "Not flagged by the supplied range. A reviewer may still record a note.")
    review = ev.get("review")
    return {
        "evidence_id": ev["evidence_id"], "marker": m["marker"], "marker_name": m["marker_name"],
        "value": m["value"], "unit": u, "range_low": m["range_low"], "range_high": m["range_high"],
        "status": m["range_status"], "needs_review": m["needs_review"],
        "baseline": {"value": c["baseline"], "n": c["n"], "available": c["baseline_available"],
                     "includes_selected_sample": c["includes_selected_sample"],
                     "samples_used": [b for b in c["baseline_values"] if b["value"] is not None]},
        "delta": c["delta"], "percent_delta": c["percent_delta"],
        "source": {"dataset_id": s["dataset_id"], "file_name": s["file_name"], "sha256": s["sha256"],
                   "provenance": s.get("provenance"), "source_row": s["source_row"], "file_line": s["file_line"],
                   "source_column": s["source_columns"]["value"], "raw_value": s["raw_value"]},
        "explanation": {"observed": observed, "compared_with": " ".join(parts), "why_flagged": why,
                        "limitations": limits, "next_review_action": action},
        "review": {"id": review["id"] if review else None, "status": review["status"] if review else None,
                   "version": review["version"] if review else None,
                   "note_present": bool(review and review["note"].strip()),
                   "updated_at": review["updated_at"] if review else None},
        "actions": {
            "inspect_evidence": f"/api/evidence/{ev['evidence_id']}",
            "create_or_open_review": {"finding_id": ev["evidence_id"], "review_id": review["id"] if review else None,
                                      "method": "PATCH" if review else "POST",
                                      "endpoint": f"/api/reviews/{review['id']}" if review else "/api/reviews"},
            "export_packet": {"html": "/api/export?format=html", "json": "/api/export?format=json"},
        },
    }


def build(conn: sqlite3.Connection, participant: str, sample: str, mode: str = "historical") -> dict[str, Any]:
    if mode != "historical":
        raise bad_request("INVALID_MODE", "Only mode=historical is supported. Replays use /api/replay/*.",
                          allowed=["historical"])
    ds = health_service.dataset_row(conn)
    ov = health_service.overview(conn, participant, sample)  # canonical evidence objects (validated params)
    cards = ov["cards"]
    items = [_item(ev) for ev in cards]
    missing = [i for i in items if i["value"] is None]
    measured = [i for i in items if i["value"] is not None]
    findings = [i for i in measured if i["needs_review"]]
    others = [i for i in measured if not i["needs_review"]]
    n_out = len(findings)
    if n_out == 0:
        text = NO_FINDINGS_TEXT
    elif n_out == 1:
        text = "One displayed measurement is outside its supplied laboratory range."
    else:
        text = f"{n_out} displayed measurements are outside their supplied laboratory ranges."
    if missing:
        text += f" {len(missing)} selected marker{'s have' if len(missing) > 1 else ' has'} no recorded value."
    report = json.loads(ds["quality_json"])
    ctx = cards[0]["context"]
    warnings = []
    if any(not (i["range_low"] is not None and i["range_high"] is not None) for i in items):
        warnings.append("At least one marker lacks a two-sided supplied range; its status is one-sided or unknown.")
    return {
        "schema_version": "mission-brief-v1",
        "brief_id": f"mission-brief-v1:{ds['sha256'][:12]}:{ctx['sample_id']}",
        "mode": "HISTORICAL_RESEARCH",
        "title": f"Health brief · {ctx['participant_id']} · {ctx['visit_label']}",
        "generated_at": db.utc_now(),
        "rule_versions": {"quality": quality.PARSER_VERSION, "health": health.RULE_VERSION,
                          "environment": environment.RULE_VERSION, "brief": "mission-brief-v1"},
        "dataset": {"dataset_id": ds["id"], "title": ds["title"], "provider": ds["provider"], "file_name": ds["file_name"],
                    "sha256": ds["sha256"], "provenance": ds["provenance"], "source_url": ds["source_url"],
                    "imported_at": ds["imported_at"]},
        "context": {k: ctx[k] for k in ("participant_id", "sample_id", "visit", "visit_label", "phase", "relative_day",
                                        "relative_day_reference")},
        "coverage": {
            "markers_considered": [i["marker"] for i in items], "considered_count": len(items),
            "measured_count": len(measured), "missing_markers": [i["marker"] for i in missing],
            "with_both_bounds": sum(1 for i in items if i["range_low"] is not None and i["range_high"] is not None),
            "one_sided_bounds": sum(1 for i in items if (i["range_low"] is None) != (i["range_high"] is None)),
            "without_bounds": sum(1 for i in items if i["range_low"] is None and i["range_high"] is None),
            "note": ("5 selected markers of the comprehensive metabolic panel; the other CMP analytes are not shown. "
                     "More markers would not add participants: 4 people are not a validation cohort."),
        },
        "summary": {"measured_marker_count": len(measured), "outside_supplied_range_count": n_out, "text": text},
        "findings": findings,
        "other_measurements": others,
        "missing_measurements": missing,
        "quality": {"provenance": ds["provenance"], "validation_status": "SHA256_MATCHES_REGISTERED_SNAPSHOT",
                    "parser_version": ds["parser_version"], "parse_issues": len(report.get("issues", [])),
                    "warnings": warnings},
        "dataset_limitations": health_service.HEALTH_LIMITATIONS,
        "case_separation": CASE_SEPARATION,
        "available_questions": QUESTIONS,
    }
