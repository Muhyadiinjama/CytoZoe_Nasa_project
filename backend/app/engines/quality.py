"""E1 — Source ingestion and data quality.

Parses the two documented NASA CSV schemas without fabricating values. Every record keeps its
original data-row number. Conflicting radiation timestamps are quarantined, never averaged.
"""
from __future__ import annotations

import hashlib
import io
import math
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

import pandas as pd

from ..config import MAX_IMPORT_BYTES
from ..errors import SchemaMismatch

PARSER_VERSION = "e1-quality-v1"
MAX_ROWS = 100_000          # resource bound for uploads; the pinned files have 28 and 1,202 rows
MAX_LINE_BYTES = 20_000     # the widest pinned line is < 1 kB
SCHEMA_VERSION = "1.0"

# (stem, display name, source unit token)
CMP_MARKERS: list[tuple[str, str, str]] = [
    ("glucose", "Glucose", "milligram_per_deciliter"),
    ("sodium", "Sodium", "millimol_per_liter"),
    ("potassium", "Potassium", "millimol_per_liter"),
    ("creatinine", "Creatinine", "milligram_per_deciliter"),
    ("calcium", "Calcium", "milligram_per_deciliter"),
]
MARKER_NAMES = {stem: name for stem, name, _ in CMP_MARKERS}
UNIT_DISPLAY = {"milligram_per_deciliter": "mg/dL", "millimol_per_liter": "mmol/L"}

# Visit metadata. L = days before launch, R = days after return: two different reference points.
VISITS: dict[str, dict[str, Any]] = {
    "L-92": {"order": 1, "phase": "PREFLIGHT", "relative_day": -92},
    "L-44": {"order": 2, "phase": "PREFLIGHT", "relative_day": -44},
    "L-3": {"order": 3, "phase": "PREFLIGHT", "relative_day": -3},
    "R+1": {"order": 4, "phase": "POSTFLIGHT", "relative_day": 1},
    "R+45": {"order": 5, "phase": "POSTFLIGHT", "relative_day": 45},
    "R+82": {"order": 6, "phase": "POSTFLIGHT", "relative_day": 82},
    "R+194": {"order": 7, "phase": "POSTFLIGHT", "relative_day": 194},
}
PREFLIGHT_VISITS = tuple(v for v, m in VISITS.items() if m["phase"] == "PREFLIGHT")
SAMPLE_RE = re.compile(r"^(C\d{3})_serum_([LR][+-]\d+)$")
NULL_TOKENS = {"", "NA", "N/A", "NAN", "NULL", "NONE"}

RADLAB_COLUMNS = ["timestamp", "instrument_id", "absorbed_dose_rate"]
RADLAB_INSTRUMENT = "DosTel1"
RADLAB_UNIT = "µGy/hour"
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def cmp_columns(stem: str, unit: str) -> tuple[str, str, str]:
    return f"{stem}_value_{unit}", f"{stem}_range_min_{unit}", f"{stem}_range_max_{unit}"


def parse_number(text: str) -> tuple[float | None, str | None]:
    token = (text or "").strip()
    if token.upper() in NULL_TOKENS:
        return None, "MISSING"
    try:
        value = float(token)
    except ValueError:
        return None, "NOT_NUMERIC"
    if not math.isfinite(value):
        return None, "NONFINITE"
    return value, None


def precheck(raw: bytes) -> None:
    """Cheap structural limits, applied before hashing or parsing so errors say why a file was refused."""
    if len(raw) > MAX_IMPORT_BYTES:
        raise SchemaMismatch("FILE_TOO_LARGE", "The file exceeds the 10 MB import limit.", {"bytes": len(raw)})
    if b"\x00" in raw:
        raise SchemaMismatch("BINARY_CONTENT", "The file contains binary content and is not a documented CSV.")
    lines = raw.count(b"\n") + 1
    if lines > MAX_ROWS + 1:
        raise SchemaMismatch("TOO_MANY_ROWS", f"The file has more than {MAX_ROWS:,} rows.", {"rows": lines})
    if max((len(line) for line in raw.split(b"\n")), default=0) > MAX_LINE_BYTES:
        raise SchemaMismatch("LINE_TOO_LONG", f"A line exceeds {MAX_LINE_BYTES:,} bytes.")


def _read_table(raw: bytes) -> pd.DataFrame:
    precheck(raw)
    if len(raw) > MAX_IMPORT_BYTES:
        raise SchemaMismatch("FILE_TOO_LARGE", "The file exceeds the 10 MB import limit.", {"bytes": len(raw)})
    if b"\x00" in raw:
        raise SchemaMismatch("BINARY_CONTENT", "The file contains binary content and is not a documented CSV.")
    lines = raw.count(b"\n") + 1
    if lines > MAX_ROWS + 1:
        raise SchemaMismatch("TOO_MANY_ROWS", f"The file has more than {MAX_ROWS:,} rows.", {"rows": lines})
    if max((len(line) for line in raw.split(b"\n")), default=0) > MAX_LINE_BYTES:
        raise SchemaMismatch("LINE_TOO_LONG", f"A line exceeds {MAX_LINE_BYTES:,} bytes.")
    try:
        raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SchemaMismatch("ENCODING_INVALID", "The file is not valid UTF-8 text.") from exc
    try:
        frame = pd.read_csv(
            io.BytesIO(raw), encoding="utf-8-sig", dtype=str, keep_default_na=False, on_bad_lines="error"
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise SchemaMismatch("CSV_UNPARSEABLE", "The CSV could not be parsed with a consistent row length.") from exc
    if frame.isna().any().any():
        raise SchemaMismatch("ROW_LENGTH_MISMATCH", "At least one row has fewer fields than the header.")
    return frame


def detect_kind(raw: bytes) -> str:
    head = raw[:4096].decode("utf-8-sig", errors="replace").splitlines()[0:1]
    header = head[0] if head else ""
    if header.startswith("Sample Name") or header.startswith('"Sample Name"'):
        return "HEALTH_CMP"
    if header.replace('"', "").strip() == ",".join(RADLAB_COLUMNS):
        return "ENV_RADIATION"
    raise SchemaMismatch(
        "UNKNOWN_SCHEMA",
        "Only the documented OSD-575 CMP and RadLab DosTel1 CSV schemas can be imported.",
        {"header_start": header[:80]},
    )


def parse_cmp(raw: bytes) -> dict[str, Any]:
    frame = _read_table(raw)
    required = ["Sample Name"] + [c for stem, _, unit in CMP_MARKERS for c in cmp_columns(stem, unit)]
    missing = [c for c in required if c not in frame.columns]
    if missing:
        raise SchemaMismatch("DATA_SCHEMA_MISMATCH", "Required OSD-575 CMP columns are missing.", {"missing": missing})

    records: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(frame.to_dict("records")):
        source_row = index + 1  # 1-based data row (file line = source_row + 1, header is line 1)
        sample_id = row["Sample Name"].strip()
        match = SAMPLE_RE.match(sample_id)
        if not match or match.group(2) not in VISITS:
            raise SchemaMismatch(
                "SAMPLE_LABEL_UNRECOGNISED",
                "A sample label does not follow the documented '<participant>_serum_<visit>' pattern.",
                {"source_row": source_row, "sample": sample_id[:40]},
            )
        if sample_id in seen:
            raise SchemaMismatch("DUPLICATE_SAMPLE", "A sample appears more than once.", {"sample": sample_id})
        seen.add(sample_id)
        participant, visit = match.group(1), match.group(2)
        meta = VISITS[visit]
        for stem, _, unit in CMP_MARKERS:
            value_col, low_col, high_col = cmp_columns(stem, unit)
            value, issue = parse_number(row[value_col])
            low, low_issue = parse_number(row[low_col])
            high, high_issue = parse_number(row[high_col])
            for col, problem in ((value_col, issue), (low_col, low_issue), (high_col, high_issue)):
                if problem:
                    issues.append({"source_row": source_row, "column": col, "issue": problem})
            records.append(
                {
                    "id": f"osd575-cmp:{sample_id}:{stem}",
                    "source_row": source_row,
                    "participant_id": participant,
                    "sample_id": sample_id,
                    "visit": visit,
                    "phase": meta["phase"],
                    "relative_day": meta["relative_day"],
                    "visit_order": meta["order"],
                    "marker": stem,
                    "value": value,
                    "value_raw": row[value_col],
                    "unit": UNIT_DISPLAY[unit],
                    "source_unit": unit,
                    "source_column": value_col,
                    "range_low": low,
                    "range_high": high,
                }
            )
    participants = sorted({r["participant_id"] for r in records})
    report = {
        "parser_version": PARSER_VERSION,
        "raw_rows": len(frame),
        "samples": len(seen),
        "participants": participants,
        "visits": sorted({r["visit"] for r in records}, key=lambda v: VISITS[v]["order"]),
        "selected_markers": [s for s, _, _ in CMP_MARKERS],
        "selected_observations": len(records),
        "nonmissing_values": sum(1 for r in records if r["value"] is not None),
        "issues": issues,
        "excluded_columns_note": "Only five selected markers are imported. Race-based eGFR fields are deliberately not used.",
    }
    return {"records": records, "report": report}


def _epoch(ts: str) -> float:
    # Source timestamps carry no timezone suffix; we only use differences between them.
    return (datetime.fromisoformat(ts) - datetime(1970, 1, 1)).total_seconds()


def parse_radlab(raw: bytes) -> dict[str, Any]:
    frame = _read_table(raw)
    if list(frame.columns) != RADLAB_COLUMNS:
        raise SchemaMismatch(
            "DATA_SCHEMA_MISMATCH",
            "RadLab export columns must be exactly timestamp,instrument_id,absorbed_dose_rate.",
            {"columns": list(frame.columns)[:10]},
        )
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(frame.to_dict("records")):
        source_row = index + 1
        instrument = row["instrument_id"].strip()
        if instrument != RADLAB_INSTRUMENT:
            raise SchemaMismatch(
                "UNEXPECTED_INSTRUMENT", "Only DosTel1 exports are supported.", {"source_row": source_row}
            )
        ts = row["timestamp"].strip()
        rate, rate_issue = parse_number(row["absorbed_dose_rate"])
        status, detail, epoch = "ACCEPTED", None, None
        if not TIMESTAMP_RE.match(ts):
            status, detail = "INVALID_TIMESTAMP", "Timestamp is not in the documented YYYY-MM-DDTHH:MM:SS form."
        else:
            try:
                epoch = _epoch(ts)
            except ValueError:
                status, detail = "INVALID_TIMESTAMP", "Timestamp is not a real calendar time."
        if status == "ACCEPTED":
            if rate_issue == "MISSING":
                status, detail = "MISSING_VALUE", "Absorbed dose rate is blank or NA."
            elif rate_issue or rate is None or rate < 0:
                status, detail = "INVALID_RATE", "Absorbed dose rate is not a finite non-negative number."
                rate = None if rate_issue else rate
        rows.append(
            {
                "id": f"radlab-dostel1:row{source_row}",
                "source_row": source_row,
                "instrument_id": instrument,
                "source_timestamp": ts,
                "epoch": epoch,
                "rate": rate,
                "rate_raw": row["absorbed_dose_rate"],
                "unit": RADLAB_UNIT,
                "quality_status": status,
                "quality_detail": detail,
            }
        )

    # Group rows sharing an exact timestamp. Different rates => quarantine every row in the group.
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r["epoch"] is not None:
            groups[r["source_timestamp"]].append(r)
    conflict_groups, identical_groups = [], []
    for ts, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        valid = [m for m in members if m["quality_status"] == "ACCEPTED"]
        rates = {m["rate"] for m in valid}
        if len(valid) == len(members) and len(rates) == 1:
            # Documented policy: retain all source rows; use only the first for derived calculations.
            for m in members[1:]:
                m["quality_status"] = "DUPLICATE_IDENTICAL"
                m["quality_detail"] = "Identical duplicate of an earlier row; retained, not double-counted."
            identical_groups.append({"timestamp": ts, "source_rows": [m["source_row"] for m in members]})
        else:
            for m in valid:
                m["quality_status"] = "DUPLICATE_CONFLICT"
                m["quality_detail"] = "Same timestamp reported with different rates; all rows quarantined."
            conflict_groups.append(
                {
                    "timestamp": ts,
                    "rows": [
                        {"source_row": m["source_row"], "rate": m["rate"], "rate_raw": m["rate_raw"]} for m in members
                    ],
                }
            )

    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r["quality_status"]] += 1
    valid_ts = sorted({r["source_timestamp"] for r in rows if r["epoch"] is not None})
    accepted = sorted((r for r in rows if r["quality_status"] == "ACCEPTED"), key=lambda r: r["epoch"])
    intervals = [b["epoch"] - a["epoch"] for a, b in zip(accepted, accepted[1:])]
    report = {
        "parser_version": PARSER_VERSION,
        "raw_rows": len(rows),
        "unique_timestamps": len(valid_ts),
        "first_timestamp": valid_ts[0] if valid_ts else None,
        "last_timestamp": valid_ts[-1] if valid_ts else None,
        "status_counts": dict(sorted(counts.items())),
        "accepted_rows": counts.get("ACCEPTED", 0),
        "quarantined_rows": counts.get("DUPLICATE_CONFLICT", 0),
        "conflict_groups": conflict_groups,
        "identical_duplicate_groups": identical_groups,
        "observed_max_interval_seconds": max(intervals) if intervals else None,
        "observed_median_interval_seconds": sorted(intervals)[len(intervals) // 2] if intervals else None,
        "documented_nominal_cadence_seconds": 300,
        "timestamp_semantics": "Source clock as exported; no timezone suffix. Not converted to UTC or local time.",
        "unit": RADLAB_UNIT,
    }
    return {"records": rows, "report": report}
