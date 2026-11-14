"""Canonical evidence objects (PRD 16.1). Every number shown in the UI comes from here."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..config import EVIDENCE_SCHEMA_VERSION, HEALTH_RULE_VERSION, RADIATION_RULE_VERSION
from ..engines import health, radiation
from ..engines.ingest import MARKER_BY_ID, MARKERS
from .store import Store


class EvidenceNotFound(Exception):
    pass


HEALTH_LIMITS = [
    "Historical Inspiration4 research sample, not live monitoring.",
    "Descriptive comparison only; not a diagnosis or a clinical abnormality threshold.",
    "Four participants are not a clinical validation cohort.",
    "Not matched to any ISS radiation record.",
]
ENV_LIMITS = [
    "Sensor reading at one ISS location; not personal, organ or effective dose and not a health risk.",
    "The 300 s gap rule is an engineering coverage rule, not a NASA safety threshold.",
    "Separate case study; not linked to any health participant.",
    "Source timestamps carry no timezone and are shown exactly as provided.",
]


def _source(ds: dict[str, Any], row: int | None) -> dict[str, Any]:
    return {"dataset_id": ds["id"], "file_name": ds["file_name"], "sha256": ds["sha256"], "source_row": row,
            "source_url": ds["source_url"], "license_note": ds["license_note"], "imported_at": ds["imported_at"]}


def health_evidence(ds: dict[str, Any], obs: dict[str, Any], same_marker: list[dict[str, Any]]) -> dict[str, Any]:
    m = MARKER_BY_ID[obs["marker"]]
    comp = health.marker_comparison(obs, same_marker)
    eid = f"osd575:{ds['sha256'][:12]}:{obs['sample_id']}:{obs['marker']}:{HEALTH_RULE_VERSION}"
    lim = list(HEALTH_LIMITS)
    lim.insert(1, "Preflight sample: a difference here cannot be a spaceflight effect." if obs["phase"] == "PREFLIGHT"
               else "Many things change between visits; a difference does not show a cause.")
    return {
        "schema_version": EVIDENCE_SCHEMA_VERSION, "evidence_id": eid, "kind": "HEALTH_OBSERVATION", "case": "health",
        "source": _source(ds, obs["source_row"]),
        "context": {"participant_id": obs["participant_id"], "sample_id": obs["sample_id"], "phase": obs["phase"],
                    "visit": obs["visit"], "relative_day": obs["relative_day"]},
        "measurement": {"marker": m["id"], "label": m["label"], "value": obs["value"], "raw_value": obs["raw_value"], "unit": m["unit"],
                        "display_decimals": m["dp"] + 1, "range_low": obs["range_low"], "range_high": obs["range_high"],
                        "range_status": comp["range_status"]},
        "comparison": {k: comp[k] for k in ("method", "baseline", "n", "baseline_values", "delta", "percent_delta", "rule_version", "retrospective")},
        "evidence_strength": "DIRECT_RESEARCH_MEASUREMENT_WITH_DESCRIPTIVE_COMPARISON",
        "limitations": lim,
        "observation_id": obs["id"],
    }


def health_cards(store: Store, participant: str, visit: str) -> dict[str, Any]:
    ds = store.active("HEALTH_CMP")
    if not ds:
        raise EvidenceNotFound("NO_HEALTH_DATA")
    obs = [o for o in store.health_obs(ds["id"]) if o["participant_id"] == participant]
    if not obs:
        raise EvidenceNotFound("UNKNOWN_PARTICIPANT")
    sel = [o for o in obs if o["visit"] == visit]
    if not sel:
        raise EvidenceNotFound("UNKNOWN_SAMPLE")
    cards = []
    for m in MARKERS:
        o = next((x for x in sel if x["marker"] == m["id"]), None)
        if o is None:
            continue
        cards.append(health_evidence(ds, o, [x for x in obs if x["marker"] == m["id"]]))
    return {"dataset": ds, "cards": cards, "sample": {k: sel[0][k] for k in ("participant_id", "sample_id", "visit", "phase", "relative_day", "source_row")}}


def health_trend(store: Store, participant: str, marker: str) -> dict[str, Any]:
    ds = store.active("HEALTH_CMP")
    if not ds:
        raise EvidenceNotFound("NO_HEALTH_DATA")
    if marker not in MARKER_BY_ID:
        raise EvidenceNotFound("UNKNOWN_MARKER")
    obs = sorted([o for o in store.health_obs(ds["id"]) if o["participant_id"] == participant and o["marker"] == marker], key=lambda o: o["visit_order"])
    if not obs:
        raise EvidenceNotFound("UNKNOWN_PARTICIPANT")
    m = MARKER_BY_ID[marker]
    pts = []
    for o in obs:
        ev = health_evidence(ds, o, obs)
        pts.append({"visit": o["visit"], "phase": o["phase"], "visit_order": o["visit_order"], "sample_id": o["sample_id"],
                    "source_row": o["source_row"], "value": o["value"], "range_low": o["range_low"], "range_high": o["range_high"],
                    "range_status": ev["measurement"]["range_status"], "delta": ev["comparison"]["delta"],
                    "percent_delta": ev["comparison"]["percent_delta"], "evidence_id": ev["evidence_id"]})
    base = health.baseline([o["value"] for o in obs if o["phase"] == "PREFLIGHT"])
    return {"dataset": ds, "participant_id": participant, "marker": {k: m[k] for k in ("id", "label", "unit", "dp")},
            "points": pts, "baseline": base, "ranges_consistent": health.ranges_consistent(pts), "rule_version": HEALTH_RULE_VERSION}


def _date_text(ts: str | None) -> str | None:
    try:
        d = datetime.fromisoformat(ts) if ts else None
    except ValueError:
        return ts
    return f"{d.day} {d.strftime('%B %Y')}" if d else None


def environment(store: Store, ds_id: str | None = None, instrument: str | None = None) -> dict[str, Any]:
    ds = store.dataset(ds_id) if ds_id else store.active("ENV_RADIATION")
    if not ds or ds["kind"] != "ENV_RADIATION":
        raise EvidenceNotFound("NO_RADIATION_DATA")
    insts = ds["quality"]["instruments"]
    inst = instrument or ("DosTel1" if "DosTel1" in insts else insts[0])
    if inst not in insts:
        raise EvidenceNotFound("UNKNOWN_INSTRUMENT")
    rows = store.radiation_rows(ds["id"], inst)
    q = ds["quality"]["per_instrument"][inst]
    conflicts = [c for c in ds["quality"]["conflict_groups"] if c["instrument_id"] == inst]
    integ = radiation.integrate(rows)
    location = "ISS Columbus" if inst.startswith("DosTel") else "Location not stated in file"
    banner = {"location": location, "instrument": inst, "date_text": _date_text(q["first_timestamp"]),
              "location_note": "DosTel1 location from RadLab instrument documentation, not from the CSV."}
    findings = environment_findings(ds, inst, q, conflicts, integ, rows)
    table = []
    nxt = {iv["from_row"]: iv for iv in integ["intervals"]}
    for r in sorted(rows, key=lambda r: (r["epoch_ms"] is None, r["epoch_ms"] or 0, r["source_row"])):
        iv = nxt.get(r["source_row"])
        table.append({"source_row": r["source_row"], "source_timestamp": r["source_timestamp"], "rate": r["rate"], "raw_rate": r["raw_rate"],
                      "quality_status": r["quality_status"], "interval_s": iv["dt_s"] if iv else None,
                      "interval_reason": iv["reason"] if iv else None, "interval_accepted": iv["accepted"] if iv else None,
                      "cumulative_uGy": iv["cumulative_uGy"] if iv and iv["accepted"] else None})
    public_integ = {k: v for k, v in integ.items() if k != "intervals"}
    return {"dataset": ds, "instrument": inst, "instruments": insts, "banner": banner, "quality": q, "conflict_groups": conflicts,
            "integration": public_integ, "findings": findings, "table": table, "limitations": ENV_LIMITS}


def environment_findings(ds: dict[str, Any], inst: str, q: dict[str, Any], conflicts: list[dict[str, Any]],
                         integ: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = f"radlab:{ds['sha256'][:12]}:{inst}"
    day = _date_text(q["first_timestamp"])
    out = [{
        "schema_version": EVIDENCE_SCHEMA_VERSION, "evidence_id": f"{base}:quality:{RADIATION_RULE_VERSION}", "kind": "DATA_QUALITY",
        "case": "environment", "source": _source(ds, None),
        "context": {"instrument_id": inst, "date_text": day, "participant_id": None},
        "title": f"Conflicting timestamps set aside: {q['conflict_groups']} group(s), {q['quarantined_rows']} rows",
        "observation": {"raw_rows": q["raw_rows"], "conflict_groups": q["conflict_groups"], "quarantined_rows": q["quarantined_rows"],
                        "accepted_rows": q["accepted_rows"], "conflicts": conflicts,
                        "excluded_intervals": len(integ["excluded_intervals"]), "excluded_by_reason": integ["excluded_by_reason"],
                        "covered_seconds": integ["covered_seconds"], "estimated_sensor_dose_uGy": integ["estimated_sensor_dose_uGy"],
                        "max_gap_s": integ["max_gap_s"], "formula": integ["formula"]},
        "rule_version": RADIATION_RULE_VERSION, "evidence_strength": "SOURCE_DATA_QUALITY_DECISION", "limitations": ENV_LIMITS,
    }]
    acc = [r for r in rows if r["quality_status"] == "ACCEPTED" and r["rate"] is not None]
    if acc:
        peak = max(acc, key=lambda r: r["rate"])
        out.append({
            "schema_version": EVIDENCE_SCHEMA_VERSION, "evidence_id": f"{base}:peak:{RADIATION_RULE_VERSION}", "kind": "ENV_OBSERVATION",
            "case": "environment", "source": _source(ds, peak["source_row"]),
            "context": {"instrument_id": inst, "date_text": day, "participant_id": None},
            "title": f"Highest accepted dose rate in this record: {peak['rate']:.2f} µGy/h",
            "observation": {"rate": peak["rate"], "unit": "µGy/h", "source_timestamp": peak["source_timestamp"], "source_row": peak["source_row"],
                            "accepted_rows": len(acc)},
            "rule_version": RADIATION_RULE_VERSION, "evidence_strength": "DIRECT_SENSOR_READING",
            "limitations": ["An observation about the record, not an alarm or a safety judgement."] + ENV_LIMITS,
        })
    return out


def find_evidence(store: Store, evidence_id: str) -> dict[str, Any]:
    """Recompute an evidence object from its stable id against the active datasets."""
    parts = evidence_id.split(":")
    if parts[0] == "osd575" and len(parts) == 5:
        ds = store.active("HEALTH_CMP")
        if not ds or ds["sha256"][:12] != parts[1]:
            raise EvidenceNotFound("EVIDENCE_NOT_IN_ACTIVE_DATA")
        sample, marker = parts[2], parts[3]
        obs = store.health_obs(ds["id"])
        o = next((x for x in obs if x["sample_id"] == sample and x["marker"] == marker), None)
        if not o:
            raise EvidenceNotFound("UNKNOWN_EVIDENCE")
        return health_evidence(ds, o, [x for x in obs if x["participant_id"] == o["participant_id"] and x["marker"] == marker])
    if parts[0] == "radlab" and len(parts) == 5:
        for d in store.datasets():
            if d["kind"] == "ENV_RADIATION" and d["sha256"][:12] == parts[1]:
                env = environment(store, d["id"], parts[2])
                f = next((x for x in env["findings"] if x["evidence_id"] == evidence_id), None)
                if f:
                    return f
        raise EvidenceNotFound("UNKNOWN_EVIDENCE")
    raise EvidenceNotFound("UNKNOWN_EVIDENCE")
