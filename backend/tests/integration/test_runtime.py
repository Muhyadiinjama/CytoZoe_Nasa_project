"""M1 — liveness, readiness, typed diagnostics (B20)."""
from __future__ import annotations

from conftest import needs_raw


def test_healthz_is_db_free_and_readyz_reports_missing_data(client):
    h = client.get("/api/healthz")
    assert h.status_code == 200 and h.json()["app"] == "CytoZoe"
    r = client.get("/api/readyz")
    assert r.status_code == 503
    body = r.json()
    assert body["ready"] is False and body["state"] == "DATASET_NOT_IMPORTED"
    assert any(c["name"] == "migrations" and c["ok"] for c in body["checks"])
    assert client.get("/api/status").json()["state"] == "DATASET_NOT_IMPORTED"


@needs_raw
def test_readyz_ready_with_verified_data(loaded_client):
    r = loaded_client.get("/api/readyz")
    assert r.status_code == 200 and r.json()["state"] == "READY"
    assert loaded_client.get("/api/status").json()["state"] == "READY"


def test_frontend_build_check_is_configurable(client, monkeypatch, tmp_path):
    from app import config

    monkeypatch.setattr(config, "FRONTEND_DIST", tmp_path / "nope")
    monkeypatch.setenv("CYTOZOE_REQUIRE_FRONTEND", "1")
    checks = {c["name"]: c for c in client.get("/api/readyz").json()["checks"]}
    assert checks["frontend_build"]["ok"] is False and checks["frontend_build"]["code"] == "FRONTEND_NOT_BUILT"


def test_errors_carry_request_id_and_no_internals(client):
    r = client.get("/api/evidence/does-not-exist")
    body = r.json()
    assert r.status_code == 404 and set(body) == {"code", "message", "details", "request_id"}
    assert body["request_id"] == r.headers["x-request-id"]
    assert "Traceback" not in r.text and "\\Users\\" not in r.text and "/home/" not in r.text


def test_corrupt_database_keeps_liveness_and_gives_typed_503(data_dir):
    from fastapi.testclient import TestClient

    from app.main import create_app

    (data_dir / "cytozoe.sqlite").write_bytes(b"this is not a sqlite database" * 100)
    c = TestClient(create_app())
    assert c.get("/api/healthz").status_code == 200
    ready = c.get("/api/readyz")
    assert ready.status_code == 503 and ready.json()["state"] == "DATABASE_UNAVAILABLE"
    p = c.get("/api/participants")
    assert p.status_code == 503 and p.json()["code"] == "DATABASE_UNAVAILABLE"
    assert "Traceback" not in p.text and "sqlite" not in p.json()["message"].lower().replace("sqlite database", "")
