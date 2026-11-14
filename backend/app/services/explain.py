"""Deterministic 'Verified explanation' templates grounded only in canonical evidence objects.

No model, no free text input: the request carries an evidence ID and a question ID from a fixed enum.
Notes and imported text are never interpolated as instructions.
"""
from __future__ import annotations

from typing import Any

QUESTIONS = {
    "EXPLAIN_RESULT": "Explain this result",
    "HOW_CALCULATED": "How was this calculated?",
    "LIMITATIONS": "What can this dataset not tell us?",
    "DIAGNOSIS_REQUEST": "Does this mean something is medically wrong?",
    "CAUSATION_REQUEST": "Did radiation cause this?",
    "SOURCE_LOCATION": "Where did this number come from?",
    "FOLLOW_UP_OPTIONS": "What follow-up can be recorded?",
}


def _source_paragraphs(ev: dict[str, Any]) -> list[str]:
    s = ev["source"]
    prov = "a verified NASA snapshot (its SHA-256 is registered in the reviewed manifest)" \
        if s.get("provenance") == "NASA_PINNED_VERIFIED" else "NOT a verified NASA snapshot"
    out = [f"Dataset: {s['title']} ({s['provider']}). File {s['file_name']}, SHA-256 {s['sha256']}, which is {prov}."]
    if ev["case"] == "health":
        out.append(f"Exact location: data row {s['source_row']} (file line {s['file_line']}), sample \"{s['sample_name']}\", "
                   f"column {s['source_columns']['value']}, raw text \"{s['raw_value']}\" ({s['source_unit']}). "
                   f"Bounds come from {s['source_columns']['range_min']} and {s['source_columns']['range_max']} in the same row.")
    else:
        out.append("Instrument DosTel1, ISS Columbus module; values are the exported absorbed dose rates in µGy/hour.")
    out.append(f"Study page: {s['source_url']}. Fetched once during setup; the running app makes no network requests.")
    return out


FOLLOW_UP_TEXT = [
    "You can save one review per finding with a status — Open, Follow-up requested or Reviewed — a note in your own "
    "words and an optional follow-up date. Every change is versioned and kept in a local history.",
    "Saved reviews can be exported as a self-contained HTML or JSON packet that freezes this evidence, its source hash "
    "and rule version. Export is a local file; nothing is sent anywhere.",
    "CytoZoe does not choose or recommend a clinical action. Status is an administrative workflow state, not a medical status.",
]

STATUS_TEXT = {
    "ABOVE_SUPPLIED_UPPER_BOUND": "above the supplied upper bound",
    "BELOW_SUPPLIED_LOWER_BOUND": "below the supplied lower bound",
    "WITHIN_SUPPLIED_RANGE": "within the supplied range",
    "ONE_SIDED_COMPARISON": "only comparable against one supplied bound",
    "UNKNOWN": "not assessable against a supplied range",
}


def fmt(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "not available"
    text = f"{value:.{digits}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def signed(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "not available"
    return ("+" if value > 0 else "") + fmt(value, digits)


def hms(seconds: float | None) -> str:
    if seconds is None:
        return "not available"
    s = int(round(seconds))
    return f"{s // 3600} h {s % 3600 // 60:02d} min {s % 60:02d} s"


def _health(ev: dict[str, Any], q: str) -> tuple[list[str], list[dict[str, str]]]:
    m, c, ctx = ev["measurement"], ev["comparison"], ev["context"]
    u = m["unit"]
    who = f"{ctx['participant_id']}'s {m['marker_name'].lower()}"
    when = f"visit {ctx['visit']} ({'preflight' if ctx['phase'] == 'PREFLIGHT' else 'postflight'}, {abs(ctx['relative_day'])} {ctx['relative_day_reference']})"
    rng = f"{fmt(m['range_low'])}–{fmt(m['range_high'])} {u}" if m["range_low"] is not None and m["range_high"] is not None else "an incomplete range"
    bvals = ", ".join(f"{b['visit']} {fmt(b['value'])}" for b in c["baseline_values"])
    facts = [
        {"label": "Observed", "value": f"{fmt(m['value'])} {u} at {ctx['visit']}"},
        {"label": "Supplied range", "value": rng},
        {"label": "Range status", "value": STATUS_TEXT[m["range_status"]]},
        {"label": "Retrospective preflight mean", "value": f"{fmt(c['baseline'])} {u} (n = {c['n']})" if c["baseline_available"] else f"not computed (n = {c['n']} < 2)"},
        {"label": "Difference from mean", "value": f"{signed(c['delta'])} {u} ({signed(c['percent_delta'], 2)}%)" if c["delta"] is not None else "not available"},
        {"label": "Source", "value": f"{ev['source']['file_name']}, data row {ev['source']['source_row']}, column {ev['source']['source_columns']['value']}"},
    ]
    if q == "EXPLAIN_RESULT":
        paras = []
        if m["value"] is None:
            paras.append(f"No {m['marker_name'].lower()} value is recorded for {ctx['participant_id']} at {when}. Nothing is inferred for the missing value.")
        else:
            line = f"At {when}, {who} was {fmt(m['value'])} {u}. The source file supplies {rng} for this sample, so the value is {STATUS_TEXT[m['range_status']]}"
            if m["range_status"] == "ABOVE_SUPPLIED_UPPER_BOUND":
                line += f" by {fmt(m['value'] - m['range_high'])} {u}"
            elif m["range_status"] == "BELOW_SUPPLIED_LOWER_BOUND":
                line += f" by {fmt(m['range_low'] - m['value'])} {u}"
            paras.append(line + ".")
        if c["baseline_available"] and m["value"] is not None:
            paras.append(
                f"Compared with {ctx['participant_id']}'s retrospective preflight mean of {fmt(c['baseline'])} {u} "
                f"(n = {c['n']}: {bvals}), the difference is {signed(c['delta'])} {u}"
                + (f" ({signed(c['percent_delta'], 2)}%)." if c["percent_delta"] is not None else ".")
            )
            if c["includes_selected_sample"]:
                paras.append("This sample is itself one of the preflight values in that mean, so the comparison is retrospective, not a real-time prediction.")
        elif not c["baseline_available"]:
            paras.append(f"A personal baseline is not computed because fewer than two preflight values are available (n = {c['n']}).")
        if ctx["phase"] == "PREFLIGHT":
            paras.append("This sample was collected before launch, so it cannot reflect an effect of spaceflight. It is a numerical comparison, not a diagnosis.")
        else:
            paras.append("This is a descriptive comparison after return. CytoZoe does not attribute it to spaceflight or any other cause, and it is not a diagnosis.")
        if m["range_status"] == "WITHIN_SUPPLIED_RANGE":
            paras.append("Being within the supplied range is not an assessment of overall health.")
        return paras, facts
    if q == "HOW_CALCULATED":
        paras = [
            f"Baseline: B = mean of available preflight values for {ctx['participant_id']} and {m['marker_name'].lower()} = mean({bvals}) = {fmt(c['baseline'], 6)} {u}, n = {c['n']}. At least two values are required." if c["baseline_available"] else f"Baseline: not computed because only {c['n']} preflight value(s) are available; at least two are required.",
            f"Difference: Δ = x − B = {fmt(m['value'], 6)} − {fmt(c['baseline'], 6)} = {fmt(c['delta'], 6)} {u}." if c["delta"] is not None else "Difference: not computed.",
            f"Percentage: %Δ = 100 × Δ / B = {fmt(c['percent_delta'], 4)}% (only when B ≠ 0)." if c["percent_delta"] is not None else "Percentage: not computed (no baseline or B = 0).",
            "Range status: a value is outside only if it is strictly below the supplied lower bound or strictly above the supplied upper bound. A value equal to a bound is within it. Rounded displays never drive this rule.",
            f"Rule version {c['rule_version']}. Source: {ev['source']['file_name']} (SHA-256 {ev['source']['sha256'][:12]}…), data row {ev['source']['source_row']}.",
        ]
        return paras, facts
    if q == "LIMITATIONS":
        return list(ev["limitations"]) + [
            "A difference from the personal mean is descriptive; CytoZoe has no validated abnormality threshold for it.",
        ], facts
    if q == "DIAGNOSIS_REQUEST":
        return [
            "Insufficient evidence. CytoZoe does not diagnose, predict illness or recommend treatment.",
            f"What the data shows is limited to: the recorded value, the supplied laboratory bounds and a comparison with this participant's own preflight samples. Interpreting it requires a qualified medical professional with the full clinical context, which this public anonymised dataset does not contain.",
        ], facts
    return [
        "No — the available data cannot support that claim.",
        "The Inspiration4 blood samples (OSD-575) and the ISS DosTel1 radiation record (1 March 2022, ISS Columbus module) come from different missions, times and people. There is no personal dose for this participant, so CytoZoe deliberately never links the two case studies.",
        "Answering a causal question would require matched, time-aligned personal dosimetry and physiological measurements for the same person, plus a validated study design.",
    ], facts


def _environment(ev: dict[str, Any], q: str) -> tuple[list[str], list[dict[str, str]]]:
    m = ev["measurement"]
    if ev["kind"] == "DATA_QUALITY":
        rows = "; ".join(f"data row {r['source_row']}: {r['rate_raw']} µGy/hour" for r in m["rows"])
        facts = [{"label": "Timestamp (source clock)", "value": m["timestamp"]},
                 {"label": "Conflicting rows", "value": rows},
                 {"label": "Decision", "value": "All rows quarantined from derived analysis"}]
        if q in ("EXPLAIN_RESULT", "HOW_CALCULATED"):
            return [
                f"The source export reports more than one different absorbed dose rate at exactly {m['timestamp']} ({rows}).",
                "There is no documented basis to prefer one value, so CytoZoe keeps every original row for audit but excludes all of them from the plotted rate series and the sensor-dose estimate. It does not take the first value, sum them or average them.",
                "Any integration interval that crosses this timestamp is excluded, and the plotted lines break there.",
            ], facts
    else:
        facts = [
            {"label": "Estimated dose over covered intervals at sensor", "value": f"{fmt(m['estimated_sensor_dose_uGy'], 2)} µGy"},
            {"label": "Covered duration", "value": f"{hms(m['covered_seconds'])} of {hms(m['span_seconds'])} ({fmt(100 * (m['coverage_ratio'] or 0), 2)}%)"},
            {"label": "Rows", "value": f"{m['raw_rows']} raw · {m['accepted_rows']} accepted · {m['quarantined_conflict_rows']} quarantined"},
            {"label": "Intervals", "value": f"{m['included_intervals']} included · {m['excluded_intervals']} excluded"},
        ]
        if q == "EXPLAIN_RESULT":
            return [
                f"On 1 March 2022 the DosTel1 instrument in the ISS Columbus module exported {m['raw_rows']} rows. {m['quarantined_conflict_rows']} rows share timestamps with conflicting values and were quarantined; {m['accepted_rows']} rows were accepted.",
                f"Integrating the accepted readings gives an estimated {fmt(m['estimated_sensor_dose_uGy'], 2)} µGy absorbed at the sensor over {hms(m['covered_seconds'])} of covered time ({fmt(100 * (m['coverage_ratio'] or 0), 2)}% of the recorded span).",
                "This is an approximate instrument-level estimate. It is not a personal, organ or effective dose and is not compared with any exposure limit.",
            ], facts
        if q == "HOW_CALCULATED":
            f = ev["comparison"]["formulas"]
            return [f"Per interval: {f['interval']}.", f"Inclusion: {f['inclusion']}.", f"Total: {f['total']}.",
                    "The 300-second cut-off is an engineering coverage rule, not a NASA safety threshold. The instrument's documented nominal cadence is 300 s, but this export shows irregular intervals.",
                    f"Rule version {ev['comparison']['rule_version']}. Source SHA-256 {ev['source']['sha256'][:12]}…."], facts
    if q == "LIMITATIONS":
        return list(ev["limitations"]), facts
    if q == "DIAGNOSIS_REQUEST":
        return ["Insufficient evidence. This is an instrument reading on the ISS, not a measurement of any person. CytoZoe draws no health conclusion and shows no safe/unsafe dose signal."], facts
    return [
        "No — this record cannot show that radiation caused any health change.",
        "It is a single-instrument environmental record that is not linked to any participant. The Inspiration4 blood samples come from a different mission, time and crew.",
    ], facts


import re

# Deterministic keyword routing for typed questions. Order matters: boundary questions are checked first.
_ROUTES: list[tuple[str, re.Pattern[str]]] = [
    ("CAUSATION_REQUEST", re.compile(r"\b(cause[ds]?|causing|because|radiation|exposure|due to|effect of)\b", re.I)),
    ("DIAGNOSIS_REQUEST", re.compile(r"\b(diagnos\w*|sick|ill|illness|disease|wrong|danger\w*|serious|healthy|safe|normal|worry|worried|treat\w*|medic\w*)\b", re.I)),
    ("SOURCE_LOCATION", re.compile(r"\b(where|source|come[s]? from|provenance|origin|file|row|hash)\b", re.I)),
    ("FOLLOW_UP_OPTIONS", re.compile(r"\b(follow[- ]?up|next step|what (can|should) (i|we) (do|record)|record|save)\b", re.I)),
    ("HOW_CALCULATED", re.compile(r"\b(calculat\w*|comput\w*|formula|baseline|mean|average|how)\b", re.I)),
    ("LIMITATIONS", re.compile(r"\b(limit\w*|cannot|can't|trust|reliab\w*|uncertain\w*|accura\w*|missing|not tell)\b", re.I)),
    ("EXPLAIN_RESULT", re.compile(r"\b(explain|what|mean[s]?|why|tell|summar\w*|result|value|flag\w*)\b", re.I)),
]


def classify(message: str) -> str | None:
    for qid, pattern in _ROUTES:
        if pattern.search(message):
            return qid
    return None


def unsupported(evidence_id: str) -> dict[str, Any]:
    return {
        "mode": "VERIFIED_EXPLANATION", "label": "Verified explanation", "question_id": None,
        "question": "Unsupported question", "evidence_id": evidence_id,
        "paragraphs": [
            "I can only answer from the evidence on this page, using fixed verified templates. "
            "Try asking what the result means, how it was calculated, what the data cannot tell us, "
            "whether it means something is wrong, or whether radiation caused it.",
        ],
        "facts": [], "source_ids": [evidence_id], "generated_by": "deterministic template (no language model)",
    }


def explain(evidence: dict[str, Any], question_id: str) -> dict[str, Any]:
    if question_id in ("SOURCE_LOCATION", "FOLLOW_UP_OPTIONS"):
        base = _health(evidence, "LIMITATIONS")[1] if evidence["case"] == "health" else _environment(evidence, "LIMITATIONS")[1]
        paragraphs = _source_paragraphs(evidence) if question_id == "SOURCE_LOCATION" else list(FOLLOW_UP_TEXT)
        return {
            "mode": "VERIFIED_EXPLANATION", "label": "Verified explanation", "question_id": question_id,
            "question": QUESTIONS[question_id], "evidence_id": evidence["evidence_id"], "paragraphs": paragraphs,
            "facts": base, "source_ids": [evidence["evidence_id"], evidence["source"]["dataset_id"]],
            "generated_by": "deterministic template (no language model)",
        }
    if evidence["case"] == "health":
        paragraphs, facts = _health(evidence, question_id)
    else:
        paragraphs, facts = _environment(evidence, question_id)
    return {
        "mode": "VERIFIED_EXPLANATION",
        "label": "Verified explanation",
        "question_id": question_id,
        "question": QUESTIONS[question_id],
        "evidence_id": evidence["evidence_id"],
        "paragraphs": paragraphs,
        "facts": facts,
        "source_ids": [evidence["evidence_id"], evidence["source"]["dataset_id"]],
        "generated_by": "deterministic template (no language model)",
    }
