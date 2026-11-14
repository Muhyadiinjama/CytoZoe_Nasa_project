"""Shared helpers for the setup scripts. Network use is limited to fetch_data.py and an allowlist."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "manifests" / "sources.json"
sys.path.insert(0, str(ROOT / "backend"))


def manifest() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["datasets"]


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()
