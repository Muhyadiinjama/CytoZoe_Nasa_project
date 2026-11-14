"""PRD section 20.1, T01-T16 (engine and store level)."""
from __future__ import annotations

import math

import pytest

from conftest import BLOOD, FIXTURES, RAD
from app.engines import health, ingest, radiation
from app.services import evidence as E


def rad_row(ms, rate, status="ACCEPTED", row=0):
    return {"epoch_ms": ms, "rate": rate, "quality_status": status, "source_row": row, "source_timestamp": str(ms)}


# T01
def test_T01_osd575_counts():
    p = ingest.parse_health_csv(BLOOD.read_bytes(), BLOOD.name)
    assert p.sha256 == "5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9"
    assert p.quality["rows"] == 28 and p.quality["participants"] == ["C001", "C002", "C003", "C004"]
    assert p.quality["visits"] == ["L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194"]
    assert p.quality["nonmissing_total"] == 140 and len(p.rows) == 140
    assert all(r["sample_id"].count("_serum_") == 1 for r in p.rows)


# T02
def test_T02_c001_glucose(loaded):
    t = E.health_trend(loaded, "C001", "glucose")
    assert t["baseline"]["values"] == [83.0, 80.0, 69.0] and t["baseline"]["mean"] == pytest.approx(77.333333, abs=1e-6)
    r1 = next(p for p in t["points"] if p["visit"] == "R+1")
    assert r1["value"] == 90 and r1["delta"] == pytest.approx(12.6667, abs=1e-4) and r1["percent_delta"] == pytest.approx(16.38, abs=0.01)
    assert (r1["range_low"], r1["range_high"], r1["range_status"]) == (65, 99, "WITHIN_SUPPLIED_RANGE")


# T03
def test_T03_c001_l3_creatinine(loaded):
    cards = E.health_cards(loaded, "C001", "L-3")["cards"]
    c = next(x for x in cards if x["measurement"]["marker"] == "creatinine")
    assert c["measurement"]["value"] == 1.37 and c["measurement"]["range_high"] == 1.35
    assert c["measurement"]["range_status"] == "ABOVE_SUPPLIED_UPPER_BOUND"
    assert c["comparison"]["baseline"] == pytest.approx(1.2366667, abs=1e-7) and c["comparison"]["n"] == 3
    assert c["source"]["source_row"] == 2 and c["context"]["phase"] == "PREFLIGHT"
    text = (str(c["measurement"]) + str(c["comparison"])).lower()
    assert "disease" not in text and "abnormal" not in text and "spaceflight" not in text


# T04
def test_T04_equal_bounds_inside():
    assert health.range_status(1.35, 0.6, 1.35) == "WITHIN_SUPPLIED_RANGE"
    assert health.range_status(0.6, 0.6, 1.35) == "WITHIN_SUPPLIED_RANGE"
    assert health.range_status(1.3501, 0.6, 1.35) == "ABOVE_SUPPLIED_UPPER_BOUND"
    assert health.range_status(0.5999, 0.6, 1.35) == "BELOW_SUPPLIED_LOWER_BOUND"


# T05
def test_T05_missing_value_and_bounds():
    assert health.range_status(None, 1, 2) == "NOT_ASSESSABLE"
    assert health.range_status(5, None, None) == "UNKNOWN"
    assert health.range_status(5, 1, None) == "ONE_SIDED_COMPARISON"
    assert health.range_status(0.5, 1, None) == "BELOW_SUPPLIED_LOWER_BOUND"
    for tok in ("NA", "N/A", "", "nan"):
        assert ingest.parse_number(tok) == (None, "MISSING")
    assert ingest.parse_number("inf") == (None, "INVALID") and ingest.parse_number("abc") == (None, "INVALID")


# T06
def test_T06_baseline_n_and_zero():
    assert health.baseline([1.0])["mean"] is None and health.baseline([1.0, None])["n"] == 1
    assert health.compare(5, health.baseline([0.0, 0.0])) == {"delta": 5.0, "percent_delta": None}


# T07
def test_T07_out_of_order_rows_sorted_by_visit(tmp_path):
    lines = BLOOD.read_bytes().decode("utf-8-sig").splitlines()
    shuffled = "\n".join([lines[0]] + list(reversed(lines[1:]))).encode()
    p = ingest.parse_health_csv(shuffled, "x.csv")
    assert p.quality["visits"] == ["L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194"]
    c1 = sorted([r for r in p.rows if r["participant_id"] == "C001" and r["marker"] == "glucose"], key=lambda r: r["visit_order"])
    assert [r["visit"] for r in c1] == ["L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194"]


# T08
def test_T08_radlab_counts():
    q = ingest.parse_radiation_csv(RAD.read_bytes(), RAD.name).quality
    pi = q["per_instrument"]["DosTel1"]
    assert (pi["raw_rows"], pi["unique_timestamps"], pi["conflict_groups"], pi["quarantined_rows"], pi["accepted_rows"]) == (1202, 1198, 4, 8, 1194)
    assert [c["source_timestamp"][11:] for c in q["conflict_groups"]] == ["09:15:00", "09:20:00", "18:25:00", "18:30:00"]


# T09
def test_T09_conflict_preserved_not_bridged():
    p = ingest.parse_radiation_csv(RAD.read_bytes(), RAD.name)
    g = p.quality["conflict_groups"][0]
    assert len(g["rows"]) == 2 and g["rows"][0]["rate"] != g["rows"][1]["rate"]
    I = radiation.integrate(p.rows)
    conflict_ms = {r["epoch_ms"] for r in p.rows if r["quality_status"] == "DUPLICATE_CONFLICT"}
    for iv in I["intervals"]:
        if iv["accepted"]:
            assert not any(iv["from_ms"] < t < iv["to_ms"] or t in (iv["from_ms"], iv["to_ms"]) for t in conflict_ms)
    for seg in I["rate_segments"]:
        for a, b in zip(seg, seg[1:]):
            assert not any(a["t"] < t < b["t"] for t in conflict_ms)
    assert I["estimated_sensor_dose_uGy"] == pytest.approx(296.037, abs=1e-3)


# T10
def test_T10_fixture_6uGy_600s():
    rows = [rad_row(0, 6.0, row=2), rad_row(600_000, 6.0, row=3)]
    assert radiation.integrate(rows, max_gap_s=600)["estimated_sensor_dose_uGy"] == pytest.approx(1.0)
    d = radiation.integrate(rows)  # default 300 s
    assert d["estimated_sensor_dose_uGy"] == 0 and d["excluded_by_reason"] == {"GAP_OVER_LIMIT": 1}


# T11
def test_T11_bad_values_rejected():
    csv = ("timestamp,instrument_id,absorbed_dose_rate\n2022-03-01T00:00:00,D,6\n2022-03-01T00:01:00,D,NaN\n"
           "not-a-time,D,5\n2022-03-01T00:02:00,D,-1\n2022-03-01T00:03:00,D,\n2022-03-01T00:04:00,D,6\n").encode()
    p = ingest.parse_radiation_csv(csv, "x.csv")
    st = [r["quality_status"] for r in p.rows]
    assert st == ["ACCEPTED", "MISSING_VALUE", "INVALID_TIMESTAMP", "INVALID_RATE", "MISSING_VALUE", "ACCEPTED"]
    I = radiation.integrate(p.rows)
    assert I["estimated_sensor_dose_uGy"] == 0 and I["excluded_by_reason"] == {"INVALID_READING_INSIDE": 1}
    assert radiation.integrate([rad_row(5, 1.0), rad_row(5, 1.0, "DUPLICATE_IDENTICAL")])["intervals_total"] == 0  # no zero-time doubles


# T12
def test_T12_gap_and_conflict_segment():
    rows = [rad_row(0, 1), rad_row(100_000, 1), rad_row(500_000, 1), rad_row(600_000, 1), rad_row(650_000, 9, "DUPLICATE_CONFLICT"), rad_row(700_000, 1)]
    I = radiation.integrate(rows)
    assert I["excluded_by_reason"] == {"CONFLICT_INSIDE": 1, "GAP_OVER_LIMIT": 1}
    assert len(I["rate_segments"]) == 2 and I["covered_seconds"] == 200


# T13
def test_T13_schema_mismatch_keeps_previous(loaded):
    before = loaded.active("HEALTH_CMP")["id"]
    with pytest.raises(ingest.DataError) as e:
        loaded.import_file("HEALTH_CMP", b"Sample Name,foo\nC001_serum_L-3,1\n", "bad.csv")
    assert e.value.code == "DATA_SCHEMA_MISMATCH" and loaded.active("HEALTH_CMP")["id"] == before
    for bad, code in ((b"", "EMPTY_FILE"), (b"\xff\xfe\x00", "NOT_TEXT"), (b"a" * (10 * 1024 * 1024 + 1), "FILE_TOO_LARGE")):
        with pytest.raises(ingest.DataError) as e:
            loaded.import_file("HEALTH_CMP", bad, "x.csv")
        assert e.value.code == code
    with pytest.raises(ingest.DataError) as e:
        loaded.import_file("HEALTH_CMP", b"x", "x.exe")
    assert e.value.code == "BAD_FILE_TYPE"


def test_T13b_sample_names_strict():
    assert ingest.parse_sample_name("﻿C001_serum_L-3")["visit"] == "L-3"
    assert ingest.parse_sample_name("C004_serum_R+194")["phase"] == "POSTFLIGHT"
    for bad in ("C001_serum_L+3", "C001_L-3", "weird", "C01_serum_L-3"):
        assert ingest.parse_sample_name(bad) is None


# T14
def test_T14_forced_failure_rolls_back(loaded):
    before = loaded.active("HEALTH_CMP")["id"]
    fixture = (FIXTURES / "test_fixture_NOT_REAL.csv").read_bytes()
    def boom():
        raise RuntimeError("simulated crash mid-import")
    # fixture uses C001_L-92 names (no specimen) so it is rejected before the transaction; craft a valid variant
    variant = fixture.decode("utf-8-sig").replace("C00", "C00").replace("_L-", "_serum_L-").replace("_R+", "_serum_R+").encode()
    with pytest.raises(RuntimeError):
        loaded.import_file("HEALTH_CMP", variant, "variant.csv", _fail_hook=boom)
    assert loaded.active("HEALTH_CMP")["id"] == before
    assert len([d for d in loaded.datasets() if d["kind"] == "HEALTH_CMP"]) == 1


# T15
def test_T15_idempotent_import(loaded):
    rep = loaded.import_file("HEALTH_CMP", BLOOD.read_bytes(), BLOOD.name)
    assert rep["status"] == "ALREADY_IMPORTED"
    with loaded.db.read() as con:
        assert con.execute("SELECT COUNT(*) FROM health_observations").fetchone()[0] == 140
        assert con.execute("SELECT COUNT(*) FROM radiation_observations").fetchone()[0] == 1202


# T16
def test_T16_no_cross_case_join(loaded):
    with pytest.raises(PermissionError):
        health.no_cross_case_join("C001", "DosTel1")
    env = E.environment(loaded)
    assert all(f["context"]["participant_id"] is None for f in env["findings"])
    assert "participant" not in str(env["integration"]).lower()


def test_no_nan_anywhere(loaded):
    import json
    env = E.environment(loaded)
    json.dumps(env, allow_nan=False)
    json.dumps(E.health_trend(loaded, "C003", "glucose"), allow_nan=False)
    assert not any(isinstance(v, float) and math.isnan(v) for r in loaded.health_obs(loaded.active("HEALTH_CMP")["id"]) for v in r.values())
