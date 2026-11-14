"""E3 — Environmental (sensor radiation) integration.

Trapezoidal estimate over accepted adjacent readings only. An interval is excluded when its duration is
not positive, exceeds the configured gap (engineering coverage rule, not a NASA health threshold), or
when an excluded/quarantined source event lies strictly inside it. No extrapolation, no Gy->Sv conversion.
"""
from __future__ import annotations

from bisect import bisect_right
from typing import Any, Sequence

RULE_VERSION = "env-integration-v1"


def integrate(
    points: Sequence[dict[str, Any]],
    break_epochs: Sequence[float],
    max_gap_seconds: float = 300,
) -> dict[str, Any]:
    """points: dicts with 'epoch' (seconds) and 'rate' (µGy/hour), plus any passthrough fields.

    Returns segments of contiguous accepted points carrying a running cumulative sum (µGy). The
    cumulative value is flat across an excluded interval and segments are never joined when plotted.
    """
    ordered = sorted(points, key=lambda p: p["epoch"])
    breaks = sorted(break_epochs)

    def break_inside(a: float, b: float) -> float | None:
        i = bisect_right(breaks, a)
        if i < len(breaks) and breaks[i] < b:
            return breaks[i]
        return None

    segments: list[list[dict[str, Any]]] = []
    excluded: list[dict[str, Any]] = []
    total = 0.0
    covered = 0.0
    included = 0
    current: list[dict[str, Any]] = []
    for idx, point in enumerate(ordered):
        if idx == 0:
            current = [{**point, "cumulative": 0.0}]
            continue
        prev = ordered[idx - 1]
        dt = point["epoch"] - prev["epoch"]
        reason = None
        if dt <= 0:
            reason = "NON_POSITIVE_INTERVAL"
        elif dt > max_gap_seconds:
            reason = "GAP_EXCEEDS_MAX"
        elif break_inside(prev["epoch"], point["epoch"]) is not None:
            reason = "EXCLUDED_EVENT_INSIDE"
        if reason:
            excluded.append(
                {"start_epoch": prev["epoch"], "end_epoch": point["epoch"], "seconds": dt, "reason": reason,
                 "start": prev.get("source_timestamp"), "end": point.get("source_timestamp")}
            )
            segments.append(current)
            current = [{**point, "cumulative": total}]
            continue
        dose = (prev["rate"] + point["rate"]) / 2.0 * dt / 3600.0
        total += dose
        covered += dt
        included += 1
        current.append({**point, "cumulative": total})
    if current:
        segments.append(current)
    span = (ordered[-1]["epoch"] - ordered[0]["epoch"]) if len(ordered) > 1 else 0.0
    return {
        "rule_version": RULE_VERSION,
        "method": "trapezoidal: ((r_i + r_j) / 2) × (t_j − t_i) seconds / 3600",
        "max_gap_seconds": max_gap_seconds,
        "segments": segments,
        "excluded_intervals": excluded,
        "included_intervals": included,
        "covered_seconds": covered,
        "span_seconds": span,
        "estimated_sensor_dose_uGy": total,
    }
