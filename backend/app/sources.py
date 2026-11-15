"""Pinned source manifest (data/manifests/sources.json)."""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from typing import Any

from .config import MANIFEST_PATH

_MONTHS = ("January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December")


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


def date_label(kind: str) -> str:
    value = date.fromisoformat(by_kind(kind)["source_date"])
    return f"{value.day} {_MONTHS[value.month - 1]} {value.year}"
