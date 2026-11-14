"""M4 — replay integrity (B15, B16) and the full action loop (B18, B19, PRD v3 §13 critical journey)."""
from __future__ import annotations

import asyncio
import html as htmlmod
import json
import re

import pytest

from conftest import needs_raw
from test_live import _parse_sse

pytestmark = needs_raw
CMP_SHA = "5eb1e7f025dd8443a9e70111e62bc32afae3432753024489c5c013e401d709d9"


def _counts():
    from app import db

    with db.session() as conn:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                for t in ("health_observations", "radiation_observations", "findings", "reviews", "review_events", "datasets")}


def test_b15_b16_replays_are_read_only(loaded_client):
    before = _counts()
    for p in ("C001", "C002", "C003", "C004"):
        rp = loaded_client.get("/api/replay/health", params={"participant": p}).json()
        assert [f["visit"] for f in rp["frames"]] == ["L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194"]
        # Prospective baseline never includes the replayed visit or any later visit.
        for k, f in enumerate(rp["frames"]):
            assert set(f["baseline_visits"]) <= {"L-92", "L-44", "L-3"}
            assert all(v in [x["visit"] for x in rp["frames"][:k]] for v in f["baseline_visits"])
    loaded_client.get("/api/replay/environment", params={"speed": 200000})
    assert _counts() == before


def test_b16_radiation_resume_matches_full_run(loaded_client):
    full = [e for n, d in _parse_sse(loaded_client.get("/api/replay/environment", params={"speed": 200000}).text)
            if n == "frame" for e in d["events"] if e["kind"] == "reading"]
    cut = full[600]["t"]
    resumed_events = _parse_sse(loaded_client.get("/api/replay/environment", params={"speed": 200000, "start": cut}).text)
    assert resumed_events[0][1]["mode"] == "HISTORICAL_REPLAY"
    resumed = [e for n, d in resumed_events if n == "frame" for e in d["events"] if e["kind"] == "reading"]
    assert resumed[0]["t"] >= cut and len(resumed) == len(full) - 600
    # Same source rows, same running totals: no phantom readings, no double counting after resume.
    assert [r["source_row"] for r in resumed] == [r["source_row"] for r in full[600:]]
    assert resumed[-1]["cumulative"] == pytest.approx(full[-1]["cumulative"])
    assert resumed[0]["covered_seconds"] == pytest.approx(full[600]["covered_seconds"])


def test_b16_radiation_stream_stops_on_disconnect(loaded_client):
    from app import db
    from app.services import environment_service, live

    with db.session() as conn:
        view = environment_service.environment_view(conn)
    calls = {"n": 0}

    async def gone() -> bool:
        calls["n"] += 1
        return calls["n"] >= 2

    async def run():
        out = []
        async for chunk in live.environment_replay(view, speed=50_000, start=0, is_disconnected=gone):
            out.append(chunk)
        return out

    chunks = asyncio.run(run())
    readings = sum(c.count('"kind": "reading"') for c in chunks)
    assert 0 < readings < 1194 and not any(c.startswith("event: end") for c in chunks)


def test_critical_journey_brief_review_restart_export(loaded_client, data_dir):
    """C001 L-3 → brief → inspect → save → restart → reopen → export HTML/JSON → parse and verify."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    brief = loaded_client.get("/api/mission/brief", params={"participant": "C001", "sample": "L-3"}).json()
    f = brief["findings"][0]
    ev = loaded_client.get(f["actions"]["inspect_evidence"]).json()
    note = 'Request repeat measurement / discuss with qualified medical staff <b>"x"</b>'
    created = loaded_client.post(f["actions"]["create_or_open_review"]["endpoint"],
                                 json={"finding_id": f["evidence_id"], "note": note, "status": "FOLLOW_UP_REQUESTED"})
    assert created.status_code == 201
    rid = created.json()["review"]["id"]

    restarted = TestClient(create_app())  # new app instance, same SQLite file (process restart: E2E restart.spec)
    assert restarted.get("/api/readyz").status_code == 200
    reopened = restarted.get(f"/api/reviews/{rid}").json()
    assert reopened["note"] == note and reopened["status"] == "FOLLOW_UP_REQUESTED"
    assert restarted.get("/api/mission/brief", params={"participant": "C001", "sample": "L-3"}).json()["findings"][0]["review"]["id"] == rid

    packet = json.loads(restarted.get("/api/export", params={"format": "json"}).text)
    r = packet["health"]["reviews"][0]
    assert r["note"] == note and r["evidence_snapshot"]["measurement"]["value"] == ev["measurement"]["value"] == 1.37
    assert r["evidence_snapshot"]["comparison"]["baseline"] == f["baseline"]["value"]
    assert r["dataset_sha256"] == CMP_SHA and r["rule_version"] == brief["rule_versions"]["health"]
    assert next(d for d in packet["datasets"] if d["id"] == "OSD-575-CMP")["provenance"] == "NASA_PINNED_VERIFIED"
    assert packet["health"]["limitations"] == brief["dataset_limitations"]
    assert packet["environment"]["reviews"] == []  # cases stay separate

    page = restarted.get("/api/export", params={"format": "html"}).text
    assert "<b>" not in page.split("Reviewer note")[1].split("</p>")[0]  # note is escaped
    assert htmlmod.escape(note, quote=True) in page and CMP_SHA in page
    assert "Verified NASA snapshot" in page and "has not been sent anywhere" in page
    assert re.search(r"Retrospective preflight mean</th><td>1\.236667", page)
