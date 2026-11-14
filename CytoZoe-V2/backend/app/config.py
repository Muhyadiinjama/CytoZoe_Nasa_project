"""Runtime configuration. Everything is local; nothing here reaches the internet."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_VERSION = "2.0.0"
SCHEMA_VERSION = 1
HEALTH_RULE_VERSION = "health-compare-v1"
RADIATION_RULE_VERSION = "radiation-integrate-v1"
EVIDENCE_SCHEMA_VERSION = "1.0"
DEFAULT_MAX_GAP_S = 300
MAX_IMPORT_BYTES = 10 * 1024 * 1024
AI_TIMEOUT_S = 15.0


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_path: Path
    frontend_dist: Path
    host: str
    port: int
    ollama_url: str
    ollama_model: str
    ai_timeout_s: float

    @property
    def assistant_mode(self) -> str:
        return "VERIFIED_PLUS_LOCAL_AI_DRAFT" if self.ollama_model else "VERIFIED_ONLY"


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("CYTOZOE_DATA_DIR") or (REPO_ROOT / "runtime")).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        data_dir=data_dir,
        db_path=data_dir / "cytozoe.sqlite",
        frontend_dist=Path(os.environ.get("CYTOZOE_FRONTEND_DIST") or (REPO_ROOT / "frontend" / "dist")).resolve(),
        host=os.environ.get("CYTOZOE_HOST", "127.0.0.1"),
        port=int(os.environ.get("CYTOZOE_PORT", "8000")),
        ollama_url=os.environ.get("CYTOZOE_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
        ollama_model=os.environ.get("CYTOZOE_OLLAMA_MODEL", "").strip(),
        ai_timeout_s=float(os.environ.get("CYTOZOE_AI_TIMEOUT_S", str(AI_TIMEOUT_S))),
    )
