"""Dataset import (atomic, idempotent by hash) and read access to the active datasets."""
from __future__ import annotations

import json
import threading
from typing import Any, Callable

from ..config import SCHEMA_VERSION
from ..db import Database, dumps, utcnow
from ..engines import ingest

KIND_META = {
    "HEALTH_CMP": {
        "prefix": "OSD-575-CMP", "title": "NASA OSDR OSD-575 Inspiration4 comprehensive metabolic panel",
        "source_url": "https://osdr.nasa.gov/bio/repo/data/studies/OSD-575",
        "license_note": "Study page lists CC0-1.0. Cite NASA OSDR OSD-575.",
        "parse": ingest.parse_health_csv,
    },
    "ENV_RADIATION": {
        "prefix": "RADLAB", "title": "NASA OSDR RadLab radiation time series",
        "source_url": "https://visualization.osdr.nasa.gov/radlab/gui/data-api/",
        "license_note": "NASA RadLab public API export. Redistribution terms not separately verified; cite RadLab.",
        "parse": ingest.parse_radiation_csv,
    },
}


class Store:
    def __init__(self, db: Database):
        self.db = db
        self._cache: dict[str, Any] = {}
        self._lock = threading.Lock()

    # ---------- import ----------
    def import_file(self, kind: str, data: bytes, file_name: str, *, fetched_at: str | None = None,
                    _fail_hook: Callable[[], None] | None = None) -> dict[str, Any]:
        if kind not in KIND_META:
            raise ingest.DataError("UNKNOWN_KIND", "Unknown dataset kind.", {"allowed": list(KIND_META)})
        meta = KIND_META[kind]
        safe_name = file_name.replace("\\", "/").split("/")[-1][:200]
        try:
            parsed = meta["parse"](data, safe_name)
        except ingest.DataError as e:
            self._log_run(kind, safe_name, None, "FAILED", {"code": e.code, "message": e.message, "details": e.details})
            raise
        ds_id = f"{meta['prefix']}:{parsed.sha256[:12]}"
        with self.db.tx() as con:
            existing = con.execute("SELECT id FROM datasets WHERE kind=? AND sha256=?", (kind, parsed.sha256)).fetchone()
            if existing:
                con.execute("UPDATE datasets SET is_active = (id = ?) WHERE kind = ?", (existing["id"], kind))
                status = "ALREADY_IMPORTED"
            else:
                con.execute(
                    "INSERT INTO datasets(id,kind,title,file_name,source_url,fetched_at,imported_at,sha256,license_note,schema_version,parser_version,quality_json,is_active)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)",
                    (ds_id, kind, meta["title"], safe_name, meta["source_url"], fetched_at, utcnow(), parsed.sha256,
                     meta["license_note"], SCHEMA_VERSION, ingest.PARSER_VERSION, dumps(parsed.quality)))
                if kind == "HEALTH_CMP":
                    con.executemany(
                        "INSERT INTO health_observations(id,dataset_id,source_row,participant_id,sample_id,specimen,phase,visit,relative_day,visit_order,marker,value,raw_value,unit,range_low,range_high)"
                        " VALUES (:id,:ds,:source_row,:participant_id,:sample_id,:specimen,:phase,:visit,:relative_day,:visit_order,:marker,:value,:raw_value,:unit,:range_low,:range_high)",
                        [{**r, "ds": ds_id} for r in parsed.rows])
                else:
                    con.executemany(
                        "INSERT INTO radiation_observations(id,dataset_id,source_row,instrument_id,source_timestamp,epoch_ms,rate,raw_rate,unit,quality_status)"
                        " VALUES (:id,:ds,:source_row,:instrument_id,:source_timestamp,:epoch_ms,:rate,:raw_rate,:unit,:quality_status)",
                        [{**r, "ds": ds_id} for r in parsed.rows])
                if _fail_hook:
                    _fail_hook()  # test hook: simulate a failure mid-transaction (T14)
                con.execute("UPDATE datasets SET is_active = (id = ?) WHERE kind = ?", (ds_id, kind))
                status = "IMPORTED"
        report = {"status": status, "dataset_id": existing["id"] if existing else ds_id, "kind": kind, "file_name": safe_name,
                  "sha256": parsed.sha256, "quality": parsed.quality}
        self._log_run(kind, safe_name, parsed.sha256, status, {"dataset_id": report["dataset_id"]})
        self._cache.clear()
        return report

    def _log_run(self, kind: str, file_name: str, sha: str | None, status: str, report: dict[str, Any]) -> None:
        try:
            with self.db.tx() as con:
                con.execute("INSERT INTO import_runs(kind,file_name,sha256,status,report_json,created_at) VALUES (?,?,?,?,?,?)",
                            (kind, file_name, sha, status, dumps(report), utcnow()))
        except Exception:  # never let logging hide the real result
            pass

    # ---------- reads ----------
    def datasets(self) -> list[dict[str, Any]]:
        with self.db.read() as con:
            rows = con.execute("SELECT * FROM datasets ORDER BY kind, imported_at DESC").fetchall()
        return [self._ds(r) for r in rows]

    def active(self, kind: str) -> dict[str, Any] | None:
        with self.db.read() as con:
            r = con.execute("SELECT * FROM datasets WHERE kind=? AND is_active=1", (kind,)).fetchone()
        return self._ds(r) if r else None

    def dataset(self, ds_id: str) -> dict[str, Any] | None:
        with self.db.read() as con:
            r = con.execute("SELECT * FROM datasets WHERE id=?", (ds_id,)).fetchone()
        return self._ds(r) if r else None

    @staticmethod
    def _ds(r: Any) -> dict[str, Any]:
        d = dict(r)
        d["quality"] = json.loads(d.pop("quality_json"))
        d["is_active"] = bool(d["is_active"])
        return d

    def health_obs(self, ds_id: str) -> list[dict[str, Any]]:
        key = "h:" + ds_id
        with self._lock:
            if key not in self._cache:
                with self.db.read() as con:
                    self._cache[key] = [dict(r) for r in con.execute(
                        "SELECT * FROM health_observations WHERE dataset_id=? ORDER BY participant_id, visit_order, marker", (ds_id,))]
            return self._cache[key]

    def radiation_rows(self, ds_id: str, instrument: str) -> list[dict[str, Any]]:
        key = f"r:{ds_id}:{instrument}"
        with self._lock:
            if key not in self._cache:
                with self.db.read() as con:
                    self._cache[key] = [dict(r) for r in con.execute(
                        "SELECT * FROM radiation_observations WHERE dataset_id=? AND instrument_id=? ORDER BY source_row", (ds_id, instrument))]
            return self._cache[key]
