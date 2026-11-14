"""Pinned source manifest (data/manifests/sources.json)."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import MANIFEST_PATH


@lru_cache(maxsize=1)
def manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def by_kind(kind: str) -> dict[str, Any]:
    for entry in manifest()["datasets"]:
        if entry["kind"] == kind:
            return entry
    raise KeyError(kind)


def by_fetch_key(key: str) -> dict[str, Any]:
    for entry in manifest()["datasets"]:
        if entry["fetch_key"] == key:
            return entry
    raise KeyError(key)
