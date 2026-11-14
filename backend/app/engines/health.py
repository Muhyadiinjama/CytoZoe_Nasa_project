"""E2 — Deterministic health comparisons.

Descriptive only: a baseline deviation is never an abnormality threshold and no disease label is produced.
Values are never rounded here; rounding happens only at presentation.
"""
from __future__ import annotations

import math
from typing import Iterable

RULE_VERSION = "health-compare-v1"
MIN_BASELINE_N = 2

BELOW = "BELOW_SUPPLIED_LOWER_BOUND"
ABOVE = "ABOVE_SUPPLIED_UPPER_BOUND"
WITHIN = "WITHIN_SUPPLIED_RANGE"
ONE_SIDED = "ONE_SIDED_COMPARISON"
UNKNOWN = "UNKNOWN"


def range_status(value: float | None, low: float | None, high: float | None) -> str:
    """Strict comparison: a value equal to a bound is within that bound.

    Precedence (tested): missing value -> UNKNOWN; no bounds -> UNKNOWN; a violated known bound wins;
    both bounds known and satisfied -> WITHIN; only one bound known and satisfied -> ONE_SIDED.
    """
    if value is None:
        return UNKNOWN
    if low is None and high is None:
        return UNKNOWN
    if low is not None and value < low:
        return BELOW
    if high is not None and value > high:
        return ABOVE
    if low is not None and high is not None:
        return WITHIN
    return ONE_SIDED


def needs_review(status: str) -> bool:
    return status in (BELOW, ABOVE)


def baseline(values: Iterable[float | None]) -> dict | None:
    """Arithmetic mean of finite preflight values; requires n >= 2."""
    finite = [v for v in values if v is not None and math.isfinite(v)]
    if len(finite) < MIN_BASELINE_N:
        return None
    return {"value": sum(finite) / len(finite), "n": len(finite)}


def compare(value: float | None, base: float | None) -> dict:
    if value is None or base is None:
        return {"delta": None, "percent_delta": None}
    delta = value - base
    percent = 100.0 * delta / base if base != 0 else None
    return {"delta": delta, "percent_delta": percent}
