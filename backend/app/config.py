"""Runtime configuration. Values are read at call time so tests can override env vars."""
from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_VERSION = "1.0.0"
MANIFEST_PATH = ROOT / "data" / "manifests" / "sources.json"
RAW_DIR = ROOT / "data" / "raw"
MIGRATIONS_DIR = ROOT / "backend" / "migrations"
FRONTEND_DIST = ROOT / "frontend" / "dist"

MAX_IMPORT_BYTES = 10 * 1024 * 1024
# Engineering coverage rule for sensor-dose integration — NOT a NASA health threshold.
RADIATION_MAX_GAP_SECONDS = 300
NOTE_MAX_CHARS = 4000


def data_dir() -> Path:
    path = Path(os.environ.get("CYTOZOE_DATA_DIR", ROOT / "runtime")).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "cytozoe.sqlite"


def allowed_hosts() -> list[str]:
    raw = os.environ.get("CYTOZOE_ALLOWED_HOSTS", "127.0.0.1,localhost")
    return [h.strip() for h in raw.split(",") if h.strip()]


@lru_cache(maxsize=1)
def git_version() -> str:
    env = os.environ.get("CYTOZOE_GIT_VERSION")
    if env:
        return env
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=3
        )
        if out.returncode == 0:
            dirty = subprocess.run(
                ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, timeout=3
            )
            suffix = "-dirty" if dirty.stdout.strip() else ""
            return out.stdout.strip() + suffix
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"
