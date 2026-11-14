from __future__ import annotations

import json
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.config import Settings  # noqa: E402
from app.db import Database  # noqa: E402
from app.services.store import Store  # noqa: E402

RAW = ROOT / "data" / "raw"
BLOOD = RAW / "LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv"
RAD = RAW / "radlab_dostel1_2022_03_01.csv"
FIXTURES = BACKEND / "tests" / "fixtures"


def make_settings(tmp: Path, **kw) -> Settings:
    base = dict(data_dir=tmp, db_path=tmp / "t.sqlite", frontend_dist=tmp / "nodist", host="127.0.0.1", port=0,
                ollama_url="http://127.0.0.1:9", ollama_model="", ai_timeout_s=15.0)
    base.update(kw)
    return Settings(**base)


@pytest.fixture
def store(tmp_path):
    return Store(Database(tmp_path / "t.sqlite"))


@pytest.fixture
def loaded(store):
    store.import_file("HEALTH_CMP", BLOOD.read_bytes(), BLOOD.name)
    store.import_file("ENV_RADIATION", RAD.read_bytes(), RAD.name)
    return store


class Server:
    """Real uvicorn server on a free loopback port (no httpx needed)."""

    def __init__(self, settings: Settings):
        import uvicorn
        from app.main import create_app
        self.settings = settings
        s = socket.socket(); s.bind(("127.0.0.1", 0)); self.port = s.getsockname()[1]; s.close()
        self.app = create_app(settings)
        self.server = uvicorn.Server(uvicorn.Config(self.app, host="127.0.0.1", port=self.port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        for _ in range(200):
            if self.server.started:
                break
            time.sleep(0.02)

    def stop(self):
        self.server.should_exit = True
        self.thread.join(5)

    def req(self, method: str, path: str, body=None, raw: bytes | None = None, headers=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        h = {"Content-Type": "application/json"} | (headers or {})
        r = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(r, timeout=30) as resp:
                b = resp.read()
                return resp.status, (json.loads(b) if resp.headers.get_content_type() == "application/json" else b.decode()), dict(resp.headers)
        except urllib.error.HTTPError as e:
            b = e.read()
            try:
                return e.code, json.loads(b), dict(e.headers)
            except json.JSONDecodeError:
                return e.code, b.decode(), dict(e.headers)


@pytest.fixture
def server(tmp_path):
    srv = Server(make_settings(tmp_path))
    yield srv
    srv.stop()


@pytest.fixture
def loaded_server(server):
    for kind, p in (("HEALTH_CMP", BLOOD), ("ENV_RADIATION", RAD)):
        st, _, _ = server.req("POST", f"/api/import?kind={kind}&file_name={p.name}", raw=p.read_bytes(), headers={"Content-Type": "text/csv"})
        assert st == 201
    return server
