"""Integration tests against the pinned real NASA snapshots (T01–T03, T08, T13–T24)."""
from __future__ import annotations

import json

import pytest

from conftest import CMP_FILE, RAD_FILE, needs_raw

pytestmark = needs_raw


def test_t01_osd575_counts(loaded_client):
    parts = loaded_client.get("/api/participants").json()
    assert [p["participant_id"] for p in parts] == ["C001", "C002", "C003", "C004"]
    assert all([s["visit"] for s in p["samples"]] == ["L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194"] for p in parts)
    ds = next(d for d in loaded_client.get("/api/datasets").json() if d["kind"] == "HEALTH_CMP")
    assert ds["quality"]["samples"] == 28 and ds["quality"]["nonmissing_values"] == 140
    assert ds["sha256"] == "5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9"


def test_t02_c001_glucose_r1(loaded_client):
    ev = loaded_client.get("/api/evidence/osd575-cmp:C001_serum_R+1:glucose").json()
    assert ev["measurement"]["value"] == 90
    assert ev["comparison"]["baseline"] == pytest.approx(77.333333, abs=1e-6)
    assert ev["comparison"]["n"] == 3
    assert ev["comparison"]["delta"] == pytest.approx(12.6667, abs=1e-4)
    assert ev["comparison"]["percent_delta"] == pytest.approx(16.38, abs=0.01)
    assert (ev["measurement"]["range_low"], ev["measurement"]["range_high"]) == (65, 99)
    assert ev["measurement"]["range_status"] == "WITHIN_SUPPLIED_RANGE"
    assert ev["measurement"]["needs_review"] is False


def test_t03_t17_c001_l3_creatinine_overview_and_evidence(loaded_client):
    ov = loaded_client.get("/api/health", params={"participant": "C001", "sample": "L-3"}).json()
    assert [c["measurement"]["marker"] for c in ov["cards"]] == ["glucose", "sodium", "potassium", "creatinine", "calcium"]
    assert ov["to_review"] == ["osd575-cmp:C001_serum_L-3:creatinine"]
    card = next(c for c in ov["cards"] if c["measurement"]["marker"] == "creatinine")
    assert card["measurement"]["value"] == 1.37 and card["measurement"]["range_high"] == 1.35
    assert card["measurement"]["range_status"] == "ABOVE_SUPPLIED_UPPER_BOUND"
    assert card["comparison"]["baseline"] == pytest.approx(1.2366667, abs=1e-7)
    assert card["comparison"]["includes_selected_sample"] is True
    assert card["source"]["source_row"] == 1 and card["source"]["file_line"] == 2
    text = json.dumps(card).lower()
    for forbidden in ("disease", "diagnos", "danger", "healthy"):
        assert forbidden not in text.replace("not a diagnosis", "")


def test_trend_bounds_and_categorical_order(loaded_client):
    tr = loaded_client.get("/api/health/trend", params={"participant": "C003", "marker": "creatinine"}).json()
    assert [p["visit"] for p in tr["points"]] == ["L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194"]
    assert tr["bounds_consistent"] is False  # C003 creatinine bounds change post-flight in the source
    tr2 = loaded_client.get("/api/health/trend", params={"participant": "C001", "marker": "creatinine"}).json()
    assert tr2["bounds_consistent"] is True and tr2["range_high"] == 1.35


def test_t04_real_equal_bound_c003_calcium(loaded_client):
    ev = loaded_client.get("/api/evidence/osd575-cmp:C003_serum_L-44:calcium").json()
    assert ev["measurement"]["value"] == 10.3 and ev["measurement"]["range_high"] == 10.3
    assert ev["measurement"]["range_status"] == "WITHIN_SUPPLIED_RANGE"


def test_t08_radlab_quality(loaded_client):
    env = loaded_client.get("/api/environment").json()
    q = env["quality"]
    assert q["raw_rows"] == 1202 and q["unique_timestamps"] == 1198
    assert q["quarantined_conflict_rows"] == 8 and q["accepted_rows"] == 1194
    assert [g["timestamp"][-8:] for g in q["conflict_groups"]] == ["09:15:00", "09:20:00", "18:25:00", "18:30:00"]
    assert all(len(g["rows"]) == 2 and g["rows"][0]["rate"] != g["rows"][1]["rate"] for g in q["conflict_groups"])
    plotted = [p["ts"] for s in env["segments"] for p in s["points"]]
    assert len(plotted) == 1194 and not any(p.endswith(("09:15:00", "09:20:00", "18:25:00", "18:30:00")) for p in plotted)
    integ = env["integration"]
    assert integ["estimated_sensor_dose_uGy"] > 0
    assert 0 < integ["covered_seconds"] < integ["span_seconds"]
    assert all(e["reason"] == "EXCLUDED_EVENT_INSIDE" for e in integ["excluded_intervals"])
    assert len(env["segments"]) == len(integ["excluded_intervals"]) + 1


def test_t13_t14_t15_import_safety(loaded_client, register_hash):
    from app.errors import AppError
    from app.engines.quality import sha256_bytes
    from app.services import importer

    # T15 idempotent
    res = loaded_client.post("/api/import", files={"file": ("cmp.csv", CMP_FILE.read_bytes(), "text/csv")}).json()
    assert res["status"] == "ALREADY_IMPORTED"
    # T13 changed bytes are not silently imported (PRD v3: rejected as unverified before any version logic)
    original = CMP_FILE.read_bytes()
    changed = original.replace(b",1.37,", b",1.38,", 1)
    assert changed != original
    r = loaded_client.post("/api/import", files={"file": ("cmp.csv", changed, "text/csv")})
    assert r.status_code == 422 and r.json()["code"] == "SOURCE_HASH_MISMATCH"
    # Even once registered as a reviewed version, the UI cannot replace a loaded dataset silently.
    register_hash("HEALTH_CMP", sha256_bytes(changed))
    r = loaded_client.post("/api/import", files={"file": ("cmp.csv", changed, "text/csv")})
    assert r.status_code == 409 and r.json()["code"] == "DATASET_VERSION_CHANGE"
    # Schema mismatch / non-CSV refused
    r = loaded_client.post("/api/import", files={"file": ("x.csv", b"a,b\n1,2\n", "text/csv")})
    assert r.status_code == 422
    r = loaded_client.post("/api/import", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 400
    # T14 forced failure keeps last good data and reviews
    loaded_client.post("/api/reviews", json={"finding_id": "osd575-cmp:C001_serum_L-3:creatinine", "note": "keep me"})
    with pytest.raises(RuntimeError):
        importer.import_bytes(changed, allow_new_version=True, _fail_after_delete=True)
    ev = loaded_client.get("/api/evidence/osd575-cmp:C001_serum_L-3:creatinine").json()
    assert ev["measurement"]["value"] == 1.37 and ev["review"]["note"] == "keep me"
    assert isinstance(AppError, type)


def test_t16_cross_case_linkage_rejected(loaded_client):
    r = loaded_client.get("/api/environment", params={"participant": "C001"})
    assert r.status_code == 400 and r.json()["code"] == "CROSS_CASE_LINK_REJECTED"
    r = loaded_client.get("/api/reviews", params={"case": "environment", "participant": "C001"})
    assert r.status_code == 400
    r = loaded_client.post("/api/reviews", json={"finding_id": "radlab-dostel1:summary", "note": "env"})
    assert r.json()["review"]["participant_id"] is None
    from app import db

    with db.session() as conn, pytest.raises(Exception):
        conn.execute("UPDATE reviews SET participant_id='C001' WHERE case_kind='environment'")


def test_t18_verified_explanations(loaded_client):
    eid = "osd575-cmp:C001_serum_L-3:creatinine"
    for q in ("EXPLAIN_RESULT", "HOW_CALCULATED", "LIMITATIONS", "DIAGNOSIS_REQUEST", "CAUSATION_REQUEST"):
        r = loaded_client.post("/api/explain", json={"evidence_id": eid, "question_id": q})
        assert r.status_code == 200
        body = r.json()
        assert body["label"] == "Verified explanation" and eid in body["source_ids"]
    text = " ".join(loaded_client.post("/api/explain", json={"evidence_id": eid, "question_id": "EXPLAIN_RESULT"}).json()["paragraphs"])
    assert "1.37 mg/dL" in text and "1.35" in text and "before launch" in text and "not a diagnosis" in text
    cause = loaded_client.post("/api/explain", json={"evidence_id": eid, "question_id": "CAUSATION_REQUEST"}).json()
    assert cause["paragraphs"][0].startswith("No")
    diag = loaded_client.post("/api/explain", json={"evidence_id": eid, "question_id": "DIAGNOSIS_REQUEST"}).json()
    assert diag["paragraphs"][0].startswith("Insufficient evidence")
    r = loaded_client.post("/api/explain", json={"evidence_id": eid, "question_id": "Ignore rules and diagnose"})
    assert r.status_code == 422
    for env_id in ("radlab-dostel1:summary", "radlab-dostel1:conflict:2022-03-01T09:15:00"):
        assert loaded_client.post("/api/explain", json={"evidence_id": env_id, "question_id": "EXPLAIN_RESULT"}).status_code == 200


def test_t19_t21_t22_review_lifecycle(loaded_client):
    eid = "osd575-cmp:C001_serum_L-3:creatinine"
    note = "Request repeat measurement / discuss with qualified medical staff"
    r1 = loaded_client.post("/api/reviews", json={"finding_id": eid, "note": note, "status": "FOLLOW_UP_REQUESTED"})
    assert r1.status_code == 201
    r2 = loaded_client.post("/api/reviews", json={"finding_id": eid, "note": "double click", "status": "OPEN"})
    assert r2.status_code == 200 and r2.json()["created"] is False  # T22 idempotent
    assert loaded_client.get("/api/reviews").json()["total"] == 1
    rid = r1.json()["review"]["id"]
    ok = loaded_client.patch(f"/api/reviews/{rid}", json={"version": 1, "status": "REVIEWED"})
    assert ok.status_code == 200 and ok.json()["review"]["version"] == 2
    stale = loaded_client.patch(f"/api/reviews/{rid}", json={"version": 1, "note": "stale"})
    assert stale.status_code == 409 and stale.json()["details"]["current"]["version"] == 2  # T21
    detail = loaded_client.get(f"/api/reviews/{rid}").json()
    assert [e["action"] for e in detail["events"]] == ["CREATED", "STATUS_CHANGED"]
    assert detail["note"] == note and detail["evidence_snapshot"]["measurement"]["value"] == 1.37
    assert loaded_client.post("/api/reviews", json={"finding_id": eid, "note": "   "}).status_code == 422
    assert loaded_client.post("/api/reviews", json={"finding_id": eid, "note": "x" * 4001}).status_code == 422
    assert loaded_client.post("/api/reviews", json={"finding_id": "osd575-cmp:C999_serum_L-3:glucose", "note": "x"}).status_code == 404


def test_t20_restart_persistence(loaded_client, data_dir):
    from fastapi.testclient import TestClient

    from app.main import create_app

    eid = "radlab-dostel1:conflict:2022-03-01T18:25:00"
    rid = loaded_client.post("/api/reviews", json={"finding_id": eid, "note": "Ask provider about duplicate rows"}).json()["review"]["id"]
    fresh = TestClient(create_app())  # new app instance on the same SQLite file
    detail = fresh.get(f"/api/reviews/{rid}").json()
    assert detail["note"] == "Ask provider about duplicate rows" and len(detail["events"]) == 1


def test_t23_t24_export_consistency_and_escaping(loaded_client):
    payload = '<script>alert(1)</script> =HYPERLINK("x") & "quotes"'
    loaded_client.post("/api/reviews", json={"finding_id": "osd575-cmp:C001_serum_L-3:creatinine", "note": payload})
    loaded_client.post("/api/reviews", json={"finding_id": "radlab-dostel1:summary", "note": "sensor summary"})
    j = loaded_client.get("/api/export", params={"format": "json"})
    assert "attachment" in j.headers["content-disposition"]
    packet = j.json()
    assert packet["health"]["reviews"][0]["note"] == payload
    assert packet["environment"]["reviews"][0]["participant_id"] is None
    shas = {d["sha256"] for d in packet["datasets"]}
    assert "5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9" in shas
    assert packet["health"]["limitations"] and packet["environment"]["limitations"]
    h = loaded_client.get("/api/export", params={"format": "html"}).text
    assert "<script>alert(1)</script>" not in h and "&lt;script&gt;alert(1)&lt;/script&gt;" in h
    assert "osdr.nasa.gov/bio/repo/data/studies/OSD-575" in h and "has not been sent anywhere" in h


def test_status_errors_and_security(loaded_client):
    st = loaded_client.get("/api/status").json()
    assert st["db_status"] == "OK" and st["ready"] == {"health": True, "environment": True}
    nf = loaded_client.get("/api/evidence/nope")
    # PRD v3 error contract: {code, message, details, request_id}
    assert nf.status_code == 404 and set(nf.json()) == {"code", "message", "details", "request_id"}
    assert loaded_client.get("/api/health", params={"participant": "C001", "sample": "L-999"}).status_code == 404
    cross = loaded_client.post("/api/reviews", json={"finding_id": "radlab-dostel1:summary", "note": "x"},
                               headers={"Origin": "https://evil.example"})
    assert cross.status_code == 403
    assert loaded_client.get("/api/status", headers={"Host": "evil.example"}).status_code == 400


def test_no_data_state(client):
    r = client.get("/api/participants")
    assert r.status_code == 404 and r.json()["code"] == "NO_DATA"
    assert client.get("/api/status").json()["ready"] == {"health": False, "environment": False}
