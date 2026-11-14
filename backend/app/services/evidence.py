"""Resolves a stable evidence ID to its canonical evidence object."""
from __future__ import annotations

import sqlite3
from typing import Any

from ..errors import not_found
from . import environment_service, health_service


def resolve(conn: sqlite3.Connection, evidence_id: str, include_review: bool = True) -> dict[str, Any]:
    if len(evidence_id) > 200:
        raise not_found("Evidence")
    if evidence_id.startswith(health_service.EVIDENCE_PREFIX + ":"):
        participant, visit, marker = health_service.parse_evidence_id(evidence_id)
        return health_service.build_evidence(conn, participant, visit, marker, include_review)
    if evidence_id.startswith(environment_service.EVIDENCE_PREFIX + ":"):
        return environment_service.build_evidence(conn, evidence_id, include_review)
    raise not_found("Evidence", evidence_id=evidence_id[:80])
