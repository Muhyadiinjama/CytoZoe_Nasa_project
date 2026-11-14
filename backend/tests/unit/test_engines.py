"""Unit tests for E1/E2/E3 using PRD fixtures (T04–T07, T09–T13) and synthetic test-only inputs."""
from __future__ import annotations

import pytest

from app.engines import environment, health, quality
from app.errors import SchemaMismatch


# ---------- E2 health ----------
def test_t04_value_equal_to_bound_is_within():
    assert health.range_status(1.35, 0.6, 1.35) == health.WITHIN
    assert health.range_status(0.6, 0.6, 1.35) == health.WITHIN
    assert health.range_status(1.37, 0.6, 1.35) == health.ABOVE
    assert health.range_status(0.59, 0.6, 1.35) == health.BELOW


def test_t05_missing_value_and_bounds():
    assert health.range_status(None, 0.6, 1.35) == health.UNKNOWN
    assert health.range_status(1.0, None, None) == health.UNKNOWN
    assert health.range_status(1.0, None, 1.35) == health.ONE_SIDED
    assert health.range_status(1.0, 0.6, None) == health.ONE_SIDED
    # A violated known bound takes precedence over the one-sided label.
    assert health.range_status(2.0, None, 1.35) == health.ABOVE
    assert health.range_status(0.1, 0.6, None) == health.BELOW


def test_t06_baseline_requires_two_values_and_zero_denominator():
    assert health.baseline([1.0]) is None
    assert health.baseline([1.0, None]) is None
    assert health.baseline([float("nan"), 2.0]) is None
    b = health.baseline([83, 80, 69])
    assert b["n"] == 3 and b["value"] == pytest.approx(77.333333, abs=1e-6)
    assert health.compare(1.0, 0.0) == {"delta": 1.0, "percent_delta": None}
    assert health.compare(None, 1.0) == {"delta": None, "percent_delta": None}


def test_t02_glucose_fixture_math():
    b = health.baseline([83, 80, 69])["value"]
    c = health.compare(90, b)
    assert c["delta"] == pytest.approx(12.6667, abs=1e-4)
    assert c["percent_delta"] == pytest.approx(16.38, abs=0.01)
    assert health.range_status(90, 65, 99) == health.WITHIN


def test_t03_creatinine_fixture_math():
    b = health.baseline([1.24, 1.10, 1.37])["value"]
    assert b == pytest.approx(1.2366667, abs=1e-7)
    assert health.range_status(1.37, 0.6, 1.35) == health.ABOVE


# ---------- E3 environment ----------
def _pts(*pairs):
    return [{"epoch": float(t), "rate": float(r), "source_timestamp": str(t)} for t, r in pairs]


def test_t10_six_uGy_per_hour_for_600_seconds_is_one_uGy_only_when_permitted():
    allowed = environment.integrate(_pts((0, 6), (600, 6)), [], max_gap_seconds=600)
    assert allowed["estimated_sensor_dose_uGy"] == pytest.approx(1.0)
    assert allowed["covered_seconds"] == 600
    default = environment.integrate(_pts((0, 6), (600, 6)), [], max_gap_seconds=300)
    assert default["estimated_sensor_dose_uGy"] == 0
    assert default["excluded_intervals"][0]["reason"] == "GAP_EXCEEDS_MAX"
    assert len(default["segments"]) == 2


def test_t12_conflict_inside_interval_breaks_segment_and_irregular_intervals():
    res = environment.integrate(_pts((0, 4), (100, 8), (250, 8), (300, 2)), [200], max_gap_seconds=300)
    # (0,100): 6*100/3600 ; (100,250) excluded (event at 200) ; (250,300): 5*50/3600
    assert res["estimated_sensor_dose_uGy"] == pytest.approx(600 / 3600 + 250 / 3600)
    assert res["covered_seconds"] == 150
    assert [len(s) for s in res["segments"]] == [2, 2]
    assert res["excluded_intervals"][0]["reason"] == "EXCLUDED_EVENT_INSIDE"
    # Cumulative stays flat across the excluded interval (no bridging, no extrapolation).
    assert res["segments"][1][0]["cumulative"] == pytest.approx(600 / 3600)


def test_event_exactly_at_endpoint_does_not_block_and_no_extrapolation():
    res = environment.integrate(_pts((10, 3), (20, 3)), [10], max_gap_seconds=300)
    assert res["included_intervals"] == 1
    assert res["span_seconds"] == 10


def test_number_formatting_keeps_integer_zeros():
    from app.services.explain import fmt
    from app.services.export import _num

    assert fmt(300.0, 0) == "300" and fmt(1.2366666, 4) == "1.2367" and fmt(90.0) == "90"
    assert _num(85480.0, 0) == "85480"


# ---------- E1 quality ----------
RAD_HEADER = b"timestamp,instrument_id,absorbed_dose_rate\n"


def test_t09_conflicting_duplicates_quarantined_not_averaged():
    raw = RAD_HEADER + (
        b'"2022-03-01T00:00:00","DosTel1",5\n'
        b'"2022-03-01T00:01:00","DosTel1",4\n"2022-03-01T00:01:00","DosTel1",6\n'
        b'"2022-03-01T00:02:00","DosTel1",5\n'
    )
    rep = quality.parse_radlab(raw)
    statuses = [r["quality_status"] for r in rep["records"]]
    assert statuses == ["ACCEPTED", "DUPLICATE_CONFLICT", "DUPLICATE_CONFLICT", "ACCEPTED"]
    group = rep["report"]["conflict_groups"][0]
    assert [r["rate"] for r in group["rows"]] == [4.0, 6.0]


def test_identical_duplicate_policy_is_not_double_counted():
    raw = RAD_HEADER + b'"2022-03-01T00:00:00","DosTel1",5\n"2022-03-01T00:00:00","DosTel1",5\n'
    rep = quality.parse_radlab(raw)
    assert [r["quality_status"] for r in rep["records"]] == ["ACCEPTED", "DUPLICATE_IDENTICAL"]


def test_t11_invalid_rows_rejected_from_derived_and_reported():
    raw = RAD_HEADER + (
        b'"2022-03-01T00:00:00","DosTel1",NaN\n'
        b'"2022-03-01T00:01:00","DosTel1",\n'
        b'"not-a-time","DosTel1",4\n'
        b'"2022-03-01T00:03:00","DosTel1",-2\n'
        b'"2022-03-01T00:04:00","DosTel1",abc\n'
        b'"2022-03-01T00:05:00","DosTel1",inf\n'
        b'"2022-02-30T00:05:00","DosTel1",3\n'
    )
    statuses = [r["quality_status"] for r in quality.parse_radlab(raw)["records"]]
    assert statuses == ["MISSING_VALUE", "MISSING_VALUE", "INVALID_TIMESTAMP", "INVALID_RATE", "INVALID_RATE",
                        "INVALID_RATE", "INVALID_TIMESTAMP"]


def test_t13_schema_mismatch_is_refused():
    with pytest.raises(SchemaMismatch):
        quality.parse_radlab(b"time,instrument,rate\n1,2,3\n")
    with pytest.raises(SchemaMismatch):
        quality.parse_cmp(b"\xef\xbb\xbfSample Name,glucose_value_milligram_per_deciliter\nC001_serum_L-3,80\n")
    with pytest.raises(SchemaMismatch):
        quality.detect_kind(b"<html><script>alert(1)</script>")
    with pytest.raises(SchemaMismatch):
        quality.parse_radlab(RAD_HEADER + b"\x00\x01")


def _cmp_csv(rows: list[str]) -> bytes:
    cols = ["Sample Name"] + [c for s, _, u in quality.CMP_MARKERS for c in quality.cmp_columns(s, u)]
    return ("﻿" + ",".join(cols) + "\n" + "\n".join(rows) + "\n").encode("utf-8")


def test_t07_out_of_order_rows_get_categorical_visit_order_and_na_is_null():
    vals = ",".join(["1", "0", "2"] * 5)
    na_vals = ",".join(["NA", "0", "2"] + ["1", "0", "2"] * 4)
    raw = _cmp_csv([f"C009_serum_R+1,{vals}", f"C009_serum_L-92,{na_vals}", f"C009_serum_L-3,{vals}"])
    rep = quality.parse_cmp(raw)
    orders = {r["sample_id"]: r["visit_order"] for r in rep["records"]}
    assert orders == {"C009_serum_R+1": 4, "C009_serum_L-92": 1, "C009_serum_L-3": 3}
    glucose_l92 = next(r for r in rep["records"] if r["sample_id"] == "C009_serum_L-92" and r["marker"] == "glucose")
    assert glucose_l92["value"] is None and glucose_l92["value_raw"] == "NA"
    assert rep["report"]["nonmissing_values"] == 14


def test_unknown_visit_label_is_refused():
    vals = ",".join(["1", "0", "2"] * 5)
    with pytest.raises(SchemaMismatch):
        quality.parse_cmp(_cmp_csv([f"C009_serum_R+999,{vals}"]))
