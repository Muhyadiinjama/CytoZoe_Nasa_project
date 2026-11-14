"""Verified explanation templates (PRD 7). Inputs are evidence objects only; notes and raw text are never read."""
from __future__ import annotations

import re
from typing import Any

QUESTIONS = ("EXPLAIN", "HOW_CALCULATED", "LIMITS")
UNSUPPORTED = re.compile(
    r"diagnos|disease|illness|sick|treat|therap|prescri|medicat|drug|cause|caus|because|why did|link|correl|related to|"
    r"radiation (?:did|do|does|effect|affect)|danger|safe|risk|cancer|kidney (?:fail|damage|injur)|should i|should they|"
    r"ignore (?:all |previous|the )|system prompt|instruction", re.I)


def fmt(v: float | None, dp: int) -> str:
    if v is None:
        return "not available"
    return f"{v:.{dp}f}"


def signed(v: float | None, dp: int) -> str:
    if v is None:
        return "not available"
    return f"{'+' if v > 0 else '−' if v < 0 else ''}{abs(v):.{dp}f}"


def _status_words(status: str) -> str:
    return {
        "ABOVE_SUPPLIED_UPPER_BOUND": "above the supplied upper bound",
        "BELOW_SUPPLIED_LOWER_BOUND": "below the supplied lower bound",
        "WITHIN_SUPPLIED_RANGE": "within the supplied range",
        "ONE_SIDED_COMPARISON": "within the only supplied bound (one-sided comparison)",
        "UNKNOWN": "not comparable because the source supplies no range",
        "NOT_ASSESSABLE": "not assessable because the value is missing",
    }.get(status, status)


def insufficient() -> dict[str, Any]:
    return {"mode": "VERIFIED_EXPLANATION", "question_id": "INSUFFICIENT_EVIDENCE", "title": "Not enough evidence", "source_ids": [],
            "paragraphs": ["This tool cannot diagnose, recommend treatment, judge safety or say what caused a result.",
                           "The blood samples and the ISS radiation record are separate historical cases with different people, missions and dates, so no link between them can be drawn.",
                           "Supported questions: Explain this result · How was this calculated? · What can this dataset not tell us?"]}


def classify_free_text(text: str) -> str:
    t = (text or "").strip().lower()
    if not t or UNSUPPORTED.search(t):
        return "INSUFFICIENT_EVIDENCE"
    if re.search(r"how|calcul|formula|computed|baseline|average|method", t):
        return "HOW_CALCULATED"
    if re.search(r"limit|cannot|can't|not tell|missing|uncertain|weak", t):
        return "LIMITS"
    if re.search(r"explain|what (?:is|does)|mean|result|this", t):
        return "EXPLAIN"
    return "INSUFFICIENT_EVIDENCE"


def explain(ev: dict[str, Any], question_id: str) -> dict[str, Any]:
    if question_id not in QUESTIONS:
        return insufficient()
    return _health(ev, question_id) if ev["kind"] == "HEALTH_OBSERVATION" else _env(ev, question_id)


def _health(ev: dict[str, Any], q: str) -> dict[str, Any]:
    m, c, x, s = ev["measurement"], ev["comparison"], ev["context"], ev["source"]
    dp = m["display_decimals"]
    ids = [ev["evidence_id"]]
    phase = "preflight" if x["phase"] == "PREFLIGHT" else "after return"
    rng = (f"supplied range {m['range_low'] if m['range_low'] is not None else 'no lower bound'} to "
           f"{m['range_high'] if m['range_high'] is not None else 'no upper bound'} {m['unit']}")
    if q == "HOW_CALCULATED":
        paras = [
            f"Value: {fmt(m['value'], dp)} {m['unit']} from source line {s['source_row']} of {s['file_name']}, sample {x['sample_id']}.",
            f"Range check: the value is compared with the {rng} given on the same source row. Equal to a bound counts as inside.",
            (f"Baseline: retrospective mean of all {c['n']} preflight values for {x['participant_id']} "
             f"({', '.join(str(v) for v in c['baseline_values'])}) = {fmt(c['baseline'], 4)} {m['unit']}. It needs at least 2 values.")
            if c["baseline"] is not None else f"Baseline: not available; it needs at least 2 preflight values and {c['n']} were found.",
            (f"Difference = value − baseline = {fmt(m['value'], 4)} − {fmt(c['baseline'], 4)} = {signed(c['delta'], 4)} {m['unit']}"
             + (f" ({signed(c['percent_delta'], 2)}%)." if c["percent_delta"] is not None else "."))
            if c["delta"] is not None else "Difference: not available.",
            f"Rule version {c['rule_version']}. Rounding happens only for display.",
        ]
        title = "How this was calculated"
    elif q == "LIMITS":
        paras = list(ev["limitations"]) + ["Visits are irregular (L-92 to R+194); the chart does not imply daily measurements between them."]
        title = "What this dataset cannot tell us"
    else:
        paras = [
            f"{m['label']} for {x['participant_id']} at {x['visit']} ({phase}) is {fmt(m['value'], dp)} {m['unit']}, {_status_words(m['range_status'])} ({rng}).",
            (f"{x['participant_id']}'s retrospective preflight mean is {fmt(c['baseline'], dp)} {m['unit']} (n={c['n']}); this value differs by "
             f"{signed(c['delta'], dp)} {m['unit']}.") if c["baseline"] is not None else "No personal baseline is available for this marker.",
            "This is a numerical comparison with the values supplied in the source file. It is not a diagnosis.",
        ]
        title = "Explain this result"
    return {"mode": "VERIFIED_EXPLANATION", "question_id": q, "title": title, "paragraphs": paras, "source_ids": ids}


def _env(ev: dict[str, Any], q: str) -> dict[str, Any]:
    o, x = ev["observation"], ev["context"]
    ids = [ev["evidence_id"]]
    if ev["kind"] == "DATA_QUALITY":
        if q == "HOW_CALCULATED":
            paras = [
                f"Rows with the same timestamp but different rates are conflicts. All {o['quarantined_rows']} rows in {o['conflict_groups']} groups are kept in the raw table and left out of every calculation; nothing is averaged or chosen.",
                f"Estimated dose = sum over accepted adjacent readings of {o['formula']}, only when the readings are at most {o['max_gap_s']} s apart and no excluded reading lies between them.",
                f"Accepted intervals cover {fmt(o['covered_seconds'] / 3600, 2)} h and add up to {fmt(o['estimated_sensor_dose_uGy'], 3)} µGy at the sensor.",
                f"{o['excluded_intervals']} interval(s) were excluded. Nothing is extrapolated before the first or after the last reading.",
            ]
            title = "How this was calculated"
        elif q == "LIMITS":
            paras, title = list(ev["limitations"]), "What this dataset cannot tell us"
        else:
            times = ", ".join(c["source_timestamp"][11:] for c in o["conflicts"])
            paras = [f"{x['instrument_id']} on {x['date_text']}: {o['conflict_groups']} timestamps ({times}) each have two different rates. Those {o['quarantined_rows']} rows are set aside.",
                     "The charts break at those times, so no line or dose is drawn across them.",
                     "This is a data-quality decision about the record, not a health finding."]
            title = "Explain this result"
    else:
        if q == "HOW_CALCULATED":
            paras = [f"The highest rate among {o['accepted_rows']} accepted readings: {fmt(o['rate'], 2)} µGy/h at source time {o['source_timestamp']} (source line {o['source_row']}).",
                     "Conflicting and invalid rows are not considered."]
            title = "How this was calculated"
        elif q == "LIMITS":
            paras, title = list(ev["limitations"]), "What this dataset cannot tell us"
        else:
            paras = [f"The highest accepted reading in this record is {fmt(o['rate'], 2)} µGy/h at source time {o['source_timestamp']}.",
                     "It describes the sensor record. It is not an alarm, a personal dose or a safety judgement."]
            title = "Explain this result"
    return {"mode": "VERIFIED_EXPLANATION", "question_id": q, "title": title, "paragraphs": paras, "source_ids": ids}
