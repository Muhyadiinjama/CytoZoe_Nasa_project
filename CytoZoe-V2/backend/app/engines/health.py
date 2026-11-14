"""E2 - health comparisons (PRD 6 and 16.3). Pure functions over observation dicts. No rounding before presentation."""
from __future__ import annotations

from typing import Any, Iterable

from ..config import HEALTH_RULE_VERSION

PREFLIGHT_VISITS = ("L-92", "L-44", "L-3")  # used only for documentation; phase comes from parsed metadata


def baseline(values: Iterable[float | None]) -> dict[str, Any]:
    s = [v for v in values if v is not None]
    if len(s) < 2:
        return {"mean": None, "n": len(s), "values": s, "method": "retrospective_preflight_arithmetic_mean"}
    return {"mean": sum(s) / len(s), "n": len(s), "values": s, "method": "retrospective_preflight_arithmetic_mean"}


def range_status(value: float | None, low: float | None, high: float | None) -> str:
    """Strict comparison; equality is inside. One known bound gives a one-sided result."""
    if value is None:
        return "NOT_ASSESSABLE"
    if low is None and high is None:
        return "UNKNOWN"
    if low is not None and value < low:
        return "BELOW_SUPPLIED_LOWER_BOUND"
    if high is not None and value > high:
        return "ABOVE_SUPPLIED_UPPER_BOUND"
    if low is None or high is None:
        return "ONE_SIDED_COMPARISON"  # within the single known bound
    return "WITHIN_SUPPLIED_RANGE"


def compare(value: float | None, base: dict[str, Any]) -> dict[str, Any]:
    b = base["mean"]
    if value is None or b is None:
        return {"delta": None, "percent_delta": None}
    return {"delta": value - b, "percent_delta": (100.0 * (value - b) / b) if b != 0 else None}


def is_outside(status: str) -> bool:
    return status in ("BELOW_SUPPLIED_LOWER_BOUND", "ABOVE_SUPPLIED_UPPER_BOUND")


def marker_comparison(obs: dict[str, Any], same_marker_obs: list[dict[str, Any]]) -> dict[str, Any]:
    pre = [o["value"] for o in sorted(same_marker_obs, key=lambda o: o["visit_order"]) if o["phase"] == "PREFLIGHT"]
    base = baseline(pre)
    return {
        "range_status": range_status(obs["value"], obs["range_low"], obs["range_high"]),
        "baseline": base["mean"], "n": base["n"], "baseline_values": base["values"],
        "method": base["method"], "rule_version": HEALTH_RULE_VERSION, **compare(obs["value"], base),
        "retrospective": True,
    }


def ranges_consistent(points: list[dict[str, Any]]) -> bool:
    keys = {(p["range_low"], p["range_high"]) for p in points if p["value"] is not None}
    return len(keys) == 1


def no_cross_case_join(*_: Any, **__: Any) -> None:
    """There is deliberately no function that pairs a health participant with a radiation record."""
    raise PermissionError("CROSS_CASE_JOIN_FORBIDDEN")
