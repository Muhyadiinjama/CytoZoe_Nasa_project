"""E3 - environmental integration (PRD 6 and 16.4). Estimated sensor dose over covered intervals only."""
from __future__ import annotations

from typing import Any

from ..config import DEFAULT_MAX_GAP_S, RADIATION_RULE_VERSION


def integrate(rows: list[dict[str, Any]], max_gap_s: float = DEFAULT_MAX_GAP_S) -> dict[str, Any]:
    """rows: radiation observations for ONE instrument (all statuses).

    Accepted rows are sorted; an interval between adjacent accepted readings counts only if
    0 < dt <= max_gap_s and no excluded event (conflict, invalid rate, missing value) lies strictly inside it.
    dose = ((r_i + r_j) / 2) * dt / 3600, in µGy. Nothing is extrapolated or interpolated.
    """
    acc = sorted((r for r in rows if r["quality_status"] == "ACCEPTED" and r["rate"] is not None and r["epoch_ms"] is not None),
                 key=lambda r: r["epoch_ms"])
    bad_times = sorted(r["epoch_ms"] for r in rows if r["epoch_ms"] is not None and r["quality_status"] in
                       ("DUPLICATE_CONFLICT", "INVALID_RATE", "MISSING_VALUE"))
    bad_kind = {r["epoch_ms"]: r["quality_status"] for r in rows if r["epoch_ms"] is not None and r["quality_status"] != "ACCEPTED"
                and r["quality_status"] != "DUPLICATE_IDENTICAL"}
    intervals: list[dict[str, Any]] = []
    total = covered = 0.0
    bi = 0
    for a, b in zip(acc, acc[1:]):
        dt = (b["epoch_ms"] - a["epoch_ms"]) / 1000.0
        while bi < len(bad_times) and bad_times[bi] <= a["epoch_ms"]:
            bi += 1
        inside = bi < len(bad_times) and bad_times[bi] < b["epoch_ms"]
        reason = None
        if dt <= 0:
            reason = "NON_POSITIVE_INTERVAL"
        elif inside:
            k = bad_kind.get(bad_times[bi], "DUPLICATE_CONFLICT")
            reason = "CONFLICT_INSIDE" if k == "DUPLICATE_CONFLICT" else "INVALID_READING_INSIDE"
        elif dt > max_gap_s:
            reason = "GAP_OVER_LIMIT"
        dose = None
        if reason is None:
            dose = (a["rate"] + b["rate"]) / 2.0 * dt / 3600.0
            total += dose
            covered += dt
        intervals.append({"from_ms": a["epoch_ms"], "to_ms": b["epoch_ms"], "from_ts": a["source_timestamp"], "to_ts": b["source_timestamp"],
                          "from_row": a["source_row"], "to_row": b["source_row"], "dt_s": dt, "accepted": reason is None,
                          "reason": reason, "dose_uGy": dose, "cumulative_uGy": total})
    # chart segments: maximal runs of accepted intervals; never bridged across an exclusion
    rate_segments: list[list[dict[str, Any]]] = []
    dose_segments: list[list[dict[str, Any]]] = []
    cur_r: list[dict[str, Any]] = []
    cur_d: list[dict[str, Any]] = []
    by_ms = {r["epoch_ms"]: r for r in acc}
    for iv in intervals:
        if iv["accepted"]:
            if not cur_r:
                a = by_ms[iv["from_ms"]]
                cur_r.append({"t": iv["from_ms"], "ts": iv["from_ts"], "v": a["rate"], "row": a["source_row"]})
                cur_d.append({"t": iv["from_ms"], "ts": iv["from_ts"], "v": iv["cumulative_uGy"] - iv["dose_uGy"]})
            b = by_ms[iv["to_ms"]]
            cur_r.append({"t": iv["to_ms"], "ts": iv["to_ts"], "v": b["rate"], "row": b["source_row"]})
            cur_d.append({"t": iv["to_ms"], "ts": iv["to_ts"], "v": iv["cumulative_uGy"]})
        else:
            if cur_r:
                rate_segments.append(cur_r)
                dose_segments.append(cur_d)
            cur_r, cur_d = [], []
    if cur_r:
        rate_segments.append(cur_r)
        dose_segments.append(cur_d)
    # isolated accepted points (not part of any accepted interval) are still shown as points
    in_seg = {p["t"] for seg in rate_segments for p in seg}
    isolated = [{"t": r["epoch_ms"], "ts": r["source_timestamp"], "v": r["rate"], "row": r["source_row"]} for r in acc if r["epoch_ms"] not in in_seg]
    excluded = [iv for iv in intervals if not iv["accepted"]]
    return {
        "method": "trapezoid over adjacent accepted readings", "formula": "((r_i + r_j) / 2) x (t_j - t_i seconds) / 3600",
        "max_gap_s": max_gap_s, "rule_version": RADIATION_RULE_VERSION, "unit": "µGy",
        "estimated_sensor_dose_uGy": total, "covered_seconds": covered,
        "accepted_points": len(acc), "intervals_total": len(intervals), "excluded_intervals": excluded,
        "excluded_by_reason": {k: sum(1 for x in excluded if x["reason"] == k) for k in sorted({x["reason"] for x in excluded})},
        "rate_segments": rate_segments, "dose_segments": dose_segments, "isolated_points": isolated,
        "intervals": intervals,
    }
