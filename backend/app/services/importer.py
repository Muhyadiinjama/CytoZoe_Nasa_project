"""Atomic, idempotent dataset import (E1 orchestration).

* Trust gate: bytes must hash to a manifest-registered NASA snapshot (expected_sha256 or accepted_sha256),
  otherwise SOURCE_HASH_MISMATCH (422) — even on an empty database.
* Same bytes imported twice -> no-op (idempotent by SHA-256).
* A different *registered* version for an already-loaded dataset -> refused unless allow_new_version=True
  (deliberate CLI action). Frozen review evidence keeps the hash it was reviewed against.
* Any failure rolls back the whole transaction; previous data and reviews remain intact.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from .. import db
from ..engines import quality
from ..errors import AppError
from ..sources import by_kind


def import_bytes(
    raw: bytes,
    *,
    fetched_at: str | None = None,
    allow_new_version: bool = False,
    _fail_after_delete: bool = False,
) -> dict[str, Any]:
    quality.precheck(raw)
    kind = quality.detect_kind(raw)
    meta = by_kind(kind)
    sha = quality.sha256_bytes(raw)
    run_id = str(uuid.uuid4())
    # Trust gate (PRD v3 §5.1): a matching schema is not proof of NASA origin. Only bytes whose hash is
    # registered in the reviewed manifest may be stored under the NASA dataset identity.
    if sha not in accepted_hashes(meta):
        with db.session() as conn:
            _record_run(conn, run_id, meta["id"], sha, "REFUSED_HASH_MISMATCH", {"received_sha256": sha})
        raise AppError(
            422,
            "SOURCE_HASH_MISMATCH",
            "This file does not match a verified NASA snapshot, so it was not imported as NASA data. "
            "Existing data and reviews were preserved.",
            {"dataset_id": meta["id"], "expected_sha256": sorted(accepted_hashes(meta)), "received_sha256": sha},
        )
    parsed = quality.parse_cmp(raw) if kind == "HEALTH_CMP" else quality.parse_radlab(raw)
    report = parsed["report"]

    with db.session() as conn:
        existing = conn.execute("SELECT sha256 FROM datasets WHERE id = ?", (meta["id"],)).fetchone()
        if existing and existing["sha256"] == sha:
            result = {"import_run_id": run_id, "dataset_id": meta["id"], "status": "ALREADY_IMPORTED",
                      "sha256": sha, "report": report}
            _record_run(conn, run_id, meta["id"], sha, "ALREADY_IMPORTED", result)
            return result
        if existing and not allow_new_version:
            _record_run(conn, run_id, meta["id"], sha, "REFUSED_VERSION_CHANGE", {"report": report})
            raise AppError(
                409,
                "DATASET_VERSION_CHANGE",
                "A different registered NASA version is already loaded. The current data was kept. "
                "Replace it deliberately with the CLI (scripts/import_data.py --allow-new-version).",
                {"dataset_id": meta["id"], "loaded_sha256": existing["sha256"], "new_sha256": sha},
            )
        pinned = meta.get("expected_sha256")
        has_provenance = any(r[1] == "provenance" for r in conn.execute("PRAGMA table_info(datasets)"))
        with db.transaction(conn):
            conn.execute("DELETE FROM health_observations WHERE dataset_id = ?", (meta["id"],))
            conn.execute("DELETE FROM radiation_observations WHERE dataset_id = ?", (meta["id"],))
            if _fail_after_delete:
                raise RuntimeError("forced failure for transaction test")
            quality_summary = dict(report)
            quality_summary["matches_pinned_manifest_sha256"] = sha == pinned
            conn.execute(
                """INSERT INTO datasets (id, kind, title, provider, source_url, download_url, file_name,
                       fetched_at, imported_at, sha256, byte_count, license_note, citation, schema_version,
                       parser_version, quality_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET fetched_at=excluded.fetched_at, imported_at=excluded.imported_at,
                       sha256=excluded.sha256, byte_count=excluded.byte_count, quality_json=excluded.quality_json,
                       parser_version=excluded.parser_version, schema_version=excluded.schema_version""",
                (meta["id"], kind, meta["title"], meta["provider"], meta["study_url"], meta["download_url"],
                 meta["file_name"], fetched_at, db.utc_now(), sha, len(raw), meta["license_note"],
                 meta["citation"], quality.SCHEMA_VERSION, quality.PARSER_VERSION, json.dumps(quality_summary)),
            )
            if has_provenance:
                conn.execute("UPDATE datasets SET provenance = 'NASA_PINNED_VERIFIED' WHERE id = ?", (meta["id"],))
            if kind == "HEALTH_CMP":
                conn.executemany(
                    """INSERT INTO health_observations (id, dataset_id, source_row, participant_id, sample_id,
                           visit, phase, relative_day, visit_order, marker, value, value_raw, unit, source_unit,
                           source_column, range_low, range_high)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    [(r["id"], meta["id"], r["source_row"], r["participant_id"], r["sample_id"], r["visit"],
                      r["phase"], r["relative_day"], r["visit_order"], r["marker"], r["value"], r["value_raw"],
                      r["unit"], r["source_unit"], r["source_column"], r["range_low"], r["range_high"])
                     for r in parsed["records"]],
                )
            else:
                conn.executemany(
                    """INSERT INTO radiation_observations (id, dataset_id, source_row, instrument_id,
                           source_timestamp, rate, rate_raw, unit, quality_status, quality_detail)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    [(r["id"], meta["id"], r["source_row"], r["instrument_id"], r["source_timestamp"], r["rate"],
                      r["rate_raw"], r["unit"], r["quality_status"], r["quality_detail"])
                     for r in parsed["records"]],
                )
        result = {"import_run_id": run_id, "dataset_id": meta["id"],
                  "status": "IMPORTED_NEW_VERSION" if existing else "IMPORTED", "sha256": sha,
                  "provenance": "NASA_PINNED_VERIFIED",
                  "matches_pinned_manifest_sha256": sha == pinned, "report": report}
        _record_run(conn, run_id, meta["id"], sha, result["status"], result)
    from . import environment_service

    environment_service._cache.clear()
    return result


def accepted_hashes(meta: dict[str, Any]) -> set[str]:
    """Hashes registered in the reviewed manifest as verified NASA snapshots for this dataset."""
    return {meta["expected_sha256"], *meta.get("accepted_sha256", [])}


def reconcile_provenance() -> None:
    """Mark each loaded dataset NASA_PINNED_VERIFIED only if its bytes hash is registered in the manifest."""
    from ..sources import manifest

    with db.session() as conn:
        if not any(r[1] == "provenance" for r in conn.execute("PRAGMA table_info(datasets)")):
            return
        registered = {e["id"]: accepted_hashes(e) for e in manifest()["datasets"]}
        with db.transaction(conn):
            for row in conn.execute("SELECT id, sha256, provenance FROM datasets").fetchall():
                want = "NASA_PINNED_VERIFIED" if row["sha256"] in registered.get(row["id"], set()) else "UNVERIFIED_LEGACY"
                if row["provenance"] != want:
                    conn.execute("UPDATE datasets SET provenance = ? WHERE id = ?", (want, row["id"]))


def _record_run(conn, run_id: str, dataset_id: str, sha: str, status: str, payload: dict) -> None:
    conn.execute(
        "INSERT INTO import_runs (id, dataset_id, sha256, status, report_json, created_at) VALUES (?,?,?,?,?,?)",
        (run_id, dataset_id, sha, status, json.dumps(payload, default=str), db.utc_now()),
    )
