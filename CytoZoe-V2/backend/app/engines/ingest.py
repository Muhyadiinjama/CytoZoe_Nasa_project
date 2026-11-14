"""E1 - ingestion and data quality. Pure functions: bytes in, typed rows + quality report out.

Rules (PRD section 6/18): strict UTF-8 (BOM removed), documented columns only, NA/N/A/blank -> null,
non-finite or non-numeric -> null and counted, original line numbers preserved, nothing invented.
"""
from __future__ import annotations

import hashlib
import io
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd

from ..config import MAX_IMPORT_BYTES

PARSER_VERSION = "cz-parse-2.0"
NULL_TOKENS = {"", "na", "n/a", "nan", "null", "none", "-"}

MARKERS: list[dict[str, Any]] = [
    {"id": "glucose", "label": "Glucose", "stem": "glucose", "src_unit": "milligram_per_deciliter", "unit": "mg/dL", "dp": 0},
    {"id": "sodium", "label": "Sodium", "stem": "sodium", "src_unit": "millimol_per_liter", "unit": "mmol/L", "dp": 0},
    {"id": "potassium", "label": "Potassium", "stem": "potassium", "src_unit": "millimol_per_liter", "unit": "mmol/L", "dp": 1},
    {"id": "creatinine", "label": "Creatinine", "stem": "creatinine", "src_unit": "milligram_per_deciliter", "unit": "mg/dL", "dp": 2},
    {"id": "calcium", "label": "Calcium", "stem": "calcium", "src_unit": "milligram_per_deciliter", "unit": "mg/dL", "dp": 1},
]
MARKER_BY_ID = {m["id"]: m for m in MARKERS}

# Exact OSD-575 sample format, e.g. C001_serum_L-3. L = days before launch, R = days after return.
SAMPLE_RE = re.compile(r"^(C\d{3})_([A-Za-z]+)_([LR])([-+])(\d{1,4})$")


class DataError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details or {}


@dataclass
class ParsedFile:
    sha256: str
    rows: list[dict[str, Any]]
    quality: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode(data: bytes, file_name: str) -> str:
    if not file_name.lower().endswith(".csv"):
        raise DataError("BAD_FILE_TYPE", "Only .csv files are accepted.", {"file_name": file_name})
    if len(data) == 0:
        raise DataError("EMPTY_FILE", "The file is empty.")
    if len(data) > MAX_IMPORT_BYTES:
        raise DataError("FILE_TOO_LARGE", "The file is over 10 MB. Use the documented CSV only.", {"bytes": len(data)})
    if b"\x00" in data[:4096]:
        raise DataError("NOT_TEXT", "This is not a text CSV file.")
    try:
        return data.decode("utf-8-sig")  # strict; removes UTF-8 BOM
    except UnicodeDecodeError as e:
        raise DataError("NOT_UTF8", "The file is not valid UTF-8 text.", {"byte_offset": e.start}) from e


def _table(text: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, na_filter=False, skip_blank_lines=True)
    except Exception as e:  # pandas raises several parser error types
        raise DataError("CSV_PARSE_ERROR", "The CSV could not be parsed.", {"reason": type(e).__name__}) from e
    df.columns = [str(c).strip().lstrip("﻿") for c in df.columns]
    if df.empty:
        raise DataError("EMPTY_FILE", "The CSV has a header but no data rows.")
    return df


def parse_number(raw: str) -> tuple[float | None, str]:
    """Returns (value, state) where state is OK | MISSING | INVALID."""
    s = (raw or "").strip()
    if s.lower() in NULL_TOKENS:
        return None, "MISSING"
    try:
        v = float(s)
    except ValueError:
        return None, "INVALID"
    if not math.isfinite(v):
        return None, "INVALID"
    return v, "OK"


def parse_sample_name(name: str) -> dict[str, Any] | None:
    m = SAMPLE_RE.match((name or "").strip().lstrip("﻿"))
    if not m:
        return None
    pid, specimen, side, sign, days = m.groups()
    if sign != ("-" if side == "L" else "+"):
        return None
    d = int(days)
    return {
        "participant_id": pid, "specimen": specimen,
        "visit": f"{side}{sign}{d}", "phase": "PREFLIGHT" if side == "L" else "POSTFLIGHT",
        "relative_day": -d if side == "L" else d,
    }


def parse_health_csv(data: bytes, file_name: str) -> ParsedFile:
    sha = sha256_hex(data)
    df = _table(_decode(data, file_name))
    required = ["Sample Name"] + [f"{m['stem']}_{k}_{m['src_unit']}" for m in MARKERS for k in ("value", "range_min", "range_max")]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataError("DATA_SCHEMA_MISMATCH", "This file does not have the documented OSD-575 CMP columns.", {"missing_columns": missing[:10]})

    samples: list[dict[str, Any]] = []
    bad_names: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for i, name in enumerate(df["Sample Name"].tolist()):
        line = i + 2
        ps = parse_sample_name(name)
        if ps is None:
            bad_names.append({"source_row": line, "value": str(name)[:60]})
            continue
        if name in seen:
            raise DataError("DUPLICATE_SAMPLE", f"Sample {name} appears twice.", {"source_rows": [seen[name], line]})
        seen[name] = line
        samples.append({**ps, "sample_id": name.strip(), "source_row": line, "i": i})
    if bad_names:
        raise DataError("UNPARSED_SAMPLE_NAME", "Some sample names do not match {Participant}_{specimen}_{L-n|R+n}.", {"rows": bad_names[:10], "count": len(bad_names)})

    days = sorted({s["relative_day"] for s in samples})
    order = {d: k for k, d in enumerate(days)}
    rows: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    counts = {m["id"]: 0 for m in MARKERS}
    for s in samples:
        rec = df.iloc[s["i"]]
        for m in MARKERS:
            raw = rec[f"{m['stem']}_value_{m['src_unit']}"]
            v, st = parse_number(raw)
            lo, st_lo = parse_number(rec[f"{m['stem']}_range_min_{m['src_unit']}"])
            hi, st_hi = parse_number(rec[f"{m['stem']}_range_max_{m['src_unit']}"])
            for state, col in ((st, "value"), (st_lo, "range_min"), (st_hi, "range_max")):
                if state == "INVALID":
                    invalid.append({"source_row": s["source_row"], "marker": m["id"], "field": col})
            if v is not None:
                counts[m["id"]] += 1
            rows.append({
                "id": f"h:{sha[:12]}:{s['sample_id']}:{m['id']}", "source_row": s["source_row"],
                "participant_id": s["participant_id"], "sample_id": s["sample_id"], "specimen": s["specimen"],
                "phase": s["phase"], "visit": s["visit"], "relative_day": s["relative_day"], "visit_order": order[s["relative_day"]],
                "marker": m["id"], "value": v, "raw_value": str(raw), "unit": m["unit"], "range_low": lo, "range_high": hi,
            })
    participants = sorted({s["participant_id"] for s in samples})
    visits = [next(s["visit"] for s in samples if s["relative_day"] == d) for d in days]
    quality = {
        "rows": len(samples), "columns": len(df.columns), "participants": participants, "participant_count": len(participants),
        "visits": visits, "visit_count": len(visits), "markers": [m["id"] for m in MARKERS],
        "nonmissing_by_marker": counts, "nonmissing_total": sum(counts.values()),
        "invalid_values_treated_as_missing": len(invalid), "invalid_examples": invalid[:10],
        "ignored_columns_note": "Only the five documented markers are imported; race-based eGFR and other columns are ignored.",
    }
    return ParsedFile(sha256=sha, rows=rows, quality=quality)


def _parse_ts(raw: str) -> int | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)  # arithmetic only; the label always keeps the source text
    # treat the naive source clock as a plain timeline for differences; no timezone is claimed
    return int((dt - datetime(1970, 1, 1)).total_seconds() * 1000)


def parse_radiation_csv(data: bytes, file_name: str) -> ParsedFile:
    sha = sha256_hex(data)
    df = _table(_decode(data, file_name))
    for c in ("timestamp", "absorbed_dose_rate"):
        if c not in df.columns:
            raise DataError("DATA_SCHEMA_MISMATCH", "This file does not have the documented RadLab columns.", {"missing_columns": [c]})
    has_inst = "instrument_id" in df.columns
    rows: list[dict[str, Any]] = []
    for i, rec in enumerate(df.to_dict("records")):
        line = i + 2
        ts_raw = str(rec["timestamp"]).strip()
        ms = _parse_ts(ts_raw)
        rate, st = parse_number(rec["absorbed_dose_rate"])
        status = "ACCEPTED"
        if ms is None:
            status = "INVALID_TIMESTAMP"
        elif st == "MISSING":
            status = "MISSING_VALUE"
        elif st == "INVALID" or (rate is not None and rate < 0):
            status, rate = "INVALID_RATE", None
        rows.append({
            "id": f"r:{sha[:12]}:{line}", "source_row": line,
            "instrument_id": (str(rec.get("instrument_id", "")).strip() if has_inst else "") or "unknown",
            "source_timestamp": ts_raw, "epoch_ms": ms, "rate": rate, "raw_rate": str(rec["absorbed_dose_rate"]),
            "unit": "µGy/h", "quality_status": status,
        })
    # duplicate timestamps per instrument: different values -> quarantine ALL rows; identical -> keep first only
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for r in rows:
        if r["epoch_ms"] is not None and r["quality_status"] == "ACCEPTED":
            groups.setdefault((r["instrument_id"], r["epoch_ms"]), []).append(r)
    conflicts: list[dict[str, Any]] = []
    for (inst, _ms), g in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if len(g) < 2:
            continue
        if len({x["rate"] for x in g}) > 1:
            for x in g:
                x["quality_status"] = "DUPLICATE_CONFLICT"
            conflicts.append({"instrument_id": inst, "source_timestamp": g[0]["source_timestamp"],
                              "rows": [{"source_row": x["source_row"], "rate": x["rate"]} for x in g]})
        else:
            for x in g[1:]:
                x["quality_status"] = "DUPLICATE_IDENTICAL"
    instruments = sorted({r["instrument_id"] for r in rows})
    per_inst = {}
    for inst in instruments:
        rr = [r for r in rows if r["instrument_id"] == inst]
        st_counts: dict[str, int] = {}
        for r in rr:
            st_counts[r["quality_status"]] = st_counts.get(r["quality_status"], 0) + 1
        valid_ts = [r for r in rr if r["epoch_ms"] is not None]
        per_inst[inst] = {
            "raw_rows": len(rr), "status_counts": st_counts,
            "unique_timestamps": len({r["epoch_ms"] for r in valid_ts}),
            "conflict_groups": sum(1 for c in conflicts if c["instrument_id"] == inst),
            "quarantined_rows": st_counts.get("DUPLICATE_CONFLICT", 0),
            "accepted_rows": st_counts.get("ACCEPTED", 0),
            "first_timestamp": min(valid_ts, key=lambda r: r["epoch_ms"])["source_timestamp"] if valid_ts else None,
            "last_timestamp": max(valid_ts, key=lambda r: r["epoch_ms"])["source_timestamp"] if valid_ts else None,
        }
    quality = {"raw_rows": len(rows), "instruments": instruments, "per_instrument": per_inst, "conflict_groups": conflicts,
               "timezone_note": "Source timestamps have no timezone suffix; they are shown exactly as provided."}
    return ParsedFile(sha256=sha, rows=rows, quality=quality)
