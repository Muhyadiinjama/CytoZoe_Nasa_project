from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CMP_FILE = RAW / "LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv"
RAD_FILE = RAW / "radlab_DosTel1_2022-03-01.csv"

needs_raw = pytest.mark.skipif(
    not (CMP_FILE.exists() and RAD_FILE.exists()),
    reason="Pinned NASA raw files not staged. Run: python scripts/fetch_data.py --all",
)


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CYTOZOE_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture()
def client(data_dir):
    from fastapi.testclient import TestClient

    from app.main import create_app

    return TestClient(create_app())


@pytest.fixture()
def register_hash():
    """Temporarily register an extra SHA-256 as a reviewed NASA version (simulates a deliberate manifest update)."""
    from app.sources import manifest

    added: list[tuple[dict, str]] = []

    def _register(kind: str, sha: str) -> None:
        entry = next(e for e in manifest()["datasets"] if e["kind"] == kind)
        entry.setdefault("accepted_sha256", []).append(sha)
        added.append((entry, sha))

    yield _register
    for entry, sha in added:
        entry["accepted_sha256"].remove(sha)


@pytest.fixture()
def loaded_client(client):
    from app.services import importer

    importer.import_bytes(CMP_FILE.read_bytes())
    importer.import_bytes(RAD_FILE.read_bytes())
    return client
