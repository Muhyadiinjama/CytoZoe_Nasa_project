"""M3 — Mission Health Intelligence Brief (B13, B14, PRD v3 §7.4)."""
from __future__ import annotations

import json

import pytest

from conftest import needs_raw

pytestmark = needs_raw
CMP_SHA = "5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9"


def _brief(c, participant="C001", sample="L-3"):
    r = c.get("/api/mission/brief", params={"participant": participant, "sample": sample})
    assert r.status_code == 200, r.text
    return r.json()


def test_fixture_a_c001_l3_creatinine(loaded_client):
    b = _brief(loaded_client)
    assert b["schema_version"] == "mission-brief-v1" and b["mode"] == "HISTORICAL_RESEARCH"
    assert b["dataset"]["sha256"] == CMP_SHA and b["dataset"]["provenance"] == "NASA_PINNED_VERIFIED"
    assert b["summary"] == {"measured_marker_count": 5, "outside_supplied_range_count": 1,
                            "text": "One displayed measurement is outside its supplied laboratory range."}
    [f] = b["findings"]
    assert (f["marker"], f["value"], f["range_high"], f["status"]) == ("creatinine", 1.37, 1.35, "ABOVE_SUPPLIED_UPPER_BOUND")
    assert f["baseline"]["value"] == pytest.approx(1.2366666667, abs=1e-9) and f["baseline"]["n"] == 3
    assert f["baseline"]["includes_selected_sample"] is True
    assert (f["source"]["source_row"], f["source"]["file_line"]) == (1, 2)
    assert f["source"]["source_column"] == "creatinine_value_milligram_per_deciliter"
    assert f["explanation"]["why_flagged"] == "The measured value is above the supplied upper bound (1.35 mg/dL)."
    assert "cannot reflect a spaceflight effect" in " ".join(f["explanation"]["limitations"])
    assert [o["marker"] for o in b["other_measurements"]] == ["glucose", "sodium", "potassium", "calcium"]
    assert b["missing_measurements"] == []
    assert f["actions"]["create_or_open_review"] == {"finding_id": f["evidence_id"], "review_id": None,
                                                     "method": "POST", "endpoint": "/api/reviews"}


def test_b13_brief_evidence_and_export_agree(loaded_client):
    """Same numbers, units, rule version and source ID across brief, evidence endpoint and frozen export."""
    b = _brief(loaded_client)
    for item in b["findings"] + b["other_measurements"]:
        ev = loaded_client.get(item["actions"]["inspect_evidence"]).json()
        assert ev["evidence_id"] == item["evidence_id"]
        assert ev["measurement"]["value"] == item["value"] and ev["measurement"]["unit"] == item["unit"]
        assert ev["comparison"]["baseline"] == item["baseline"]["value"] and ev["comparison"]["delta"] == item["delta"]
        assert ev["source"]["source_row"] == item["source"]["source_row"]
        assert ev["comparison"]["rule_version"] == b["rule_versions"]["health"]
    f = b["findings"][0]
    loaded_client.post("/api/reviews", json={"finding_id": f["evidence_id"], "note": "repeat measurement",
                                             "status": "FOLLOW_UP_REQUESTED"})
    packet = loaded_client.get("/api/export", params={"format": "json"}).json()
    snap = packet["health"]["reviews"][0]["evidence_snapshot"]
    assert snap["evidence_id"] == f["evidence_id"] and snap["measurement"]["value"] == f["value"]
    assert snap["comparison"]["baseline"] == f["baseline"]["value"] and snap["source"]["sha256"] == b["dataset"]["sha256"]
    assert packet["health"]["reviews"][0]["rule_version"] == b["rule_versions"]["health"]


def test_fixture_b_and_b14_dynamic_not_hardcoded(loaded_client):
    b = _brief(loaded_client, "C001", "R+1")
    assert b["context"]["visit"] == "R+1" and b["context"]["phase"] == "POSTFLIGHT"
    assert b["summary"]["text"] == ("No displayed measurements are outside their supplied ranges; "
                                    "this is not an overall health assessment.")
    assert b["findings"] == []
    g = next(o for o in b["other_measurements"] if o["marker"] == "glucose")
    assert g["value"] == 90 and g["baseline"]["value"] == pytest.approx(77.3333333, abs=1e-6)
    assert g["delta"] == pytest.approx(12.6666667, abs=1e-6) and g["percent_delta"] == pytest.approx(16.37931, abs=1e-4)
    assert g["status"] == "WITHIN_SUPPLIED_RANGE" and g["explanation"]["why_flagged"] is None
    # Every participant/sample yields a self-consistent brief.
    for p in ("C001", "C002", "C003", "C004"):
        for v in ("L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194"):
            bb = _brief(loaded_client, p, v)
            assert bb["context"]["sample_id"] == f"{p}_serum_{v}"
            assert bb["summary"]["outside_supplied_range_count"] == len(bb["findings"])
            assert all(i["needs_review"] for i in bb["findings"])
            if v == "L-92":  # n=1 before L-44 is impossible here: retrospective baseline uses all 3 preflight visits
                assert all(i["baseline"]["n"] == 3 for i in bb["findings"] + bb["other_measurements"])


def test_brief_reflects_review_state_after_save(loaded_client):
    eid = "osd575-cmp:C001_serum_L-3:creatinine"
    rid = loaded_client.post("/api/reviews", json={"finding_id": eid, "note": "x"}).json()["review"]["id"]
    f = _brief(loaded_client)["findings"][0]
    assert f["review"]["id"] == rid and f["review"]["note_present"] is True and f["review"]["version"] == 1
    assert f["actions"]["create_or_open_review"]["method"] == "PATCH"
    loaded_client.patch(f"/api/reviews/{rid}", json={"version": 1, "status": "REVIEWED"})
    assert _brief(loaded_client)["findings"][0]["review"]["status"] == "REVIEWED"


def test_brief_typed_errors_and_edge_cases(loaded_client):
    for params, code in [({"participant": "C999", "sample": "L-3"}, 404),
                         ({"participant": "C001", "sample": "L-999"}, 404),
                         ({"participant": "C001", "sample": "L-3", "mode": "live"}, 400)]:
        r = loaded_client.get("/api/mission/brief", params=params)
        assert r.status_code == code and set(r.json()) == {"code", "message", "details", "request_id"}
    assert loaded_client.get("/api/mission/brief", params={"participant": "C001"}).status_code == 422
    # Missing value / bounds: synthesise via the engine on a copy of the real row (never served as NASA data).
    from app import db
    from app.services import mission_brief

    with db.session() as conn:
        conn.execute("UPDATE health_observations SET value = NULL WHERE id = 'osd575-cmp:C002_serum_L-3:sodium'")
        conn.execute("UPDATE health_observations SET range_low = NULL, range_high = NULL "
                     "WHERE id = 'osd575-cmp:C002_serum_L-3:potassium'")
        b = mission_brief.build(conn, "C002", "L-3")
    assert [m["marker"] for m in b["missing_measurements"]] == ["sodium"]
    assert b["missing_measurements"][0]["status"] == "UNKNOWN" and b["missing_measurements"][0]["delta"] is None
    assert b["coverage"]["missing_markers"] == ["sodium"] and b["coverage"]["without_bounds"] == 1
    pot = next(o for o in b["other_measurements"] if o["marker"] == "potassium")
    assert pot["status"] == "UNKNOWN" and "No supplied laboratory range" in pot["explanation"]["compared_with"]
    assert "has no recorded value" in b["summary"]["text"]


def test_brief_has_no_forbidden_claims_and_is_in_openapi(loaded_client):
    # The only allowed occurrence is the negated disclaimer "— not live astronaut monitoring."
    text = json.dumps(_brief(loaded_client)).lower().replace("not live astronaut monitoring", "")
    for bad in ("diagnosed", "disease", "danger", "health score", "risk of", "live astronaut", "caused by radiation"):
        assert bad not in text
    spec = loaded_client.get("/api/openapi.json").json()
    assert "/api/mission/brief" in spec["paths"] and "MissionBriefV1" in spec["components"]["schemas"]


def test_new_guided_questions(loaded_client):
    eid = "osd575-cmp:C001_serum_L-3:creatinine"
    src = loaded_client.post("/api/explain", json={"evidence_id": eid, "question_id": "SOURCE_LOCATION"}).json()
    assert "data row 1 (file line 2)" in src["paragraphs"][1] and "verified NASA snapshot" in src["paragraphs"][0]
    fu = loaded_client.post("/api/explain", json={"evidence_id": eid, "question_id": "FOLLOW_UP_OPTIONS"}).json()
    assert "does not choose or recommend a clinical action" in " ".join(fu["paragraphs"])
    assert loaded_client.post("/api/explain", json={"evidence_id": eid, "message": "where did this number come from?"}).json()["question_id"] == "SOURCE_LOCATION"
    env = loaded_client.post("/api/explain", json={"evidence_id": "radlab-dostel1:summary", "question_id": "SOURCE_LOCATION"})
    assert env.status_code == 200 and "DosTel1" in env.json()["paragraphs"][1]
