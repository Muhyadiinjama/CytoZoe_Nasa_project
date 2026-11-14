"""One-time setup download of the pinned NASA source files (never called by the running app).

Usage:
  python scripts/fetch_data.py --dataset osd575-cmp
  python scripts/fetch_data.py --dataset radlab-dostel1-2022-03-01
  python scripts/fetch_data.py --all [--force]

Only HTTPS URLs on allow-listed NASA hosts from data/manifests/sources.json are fetched. Existing raw
files are immutable and are not overwritten unless --force is given. A hash difference is reported,
not hidden; nothing is substituted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "manifests" / "sources.json"
RAW = ROOT / "data" / "raw"
ALLOWED_HOSTS = {"osdr.nasa.gov", "visualization.osdr.nasa.gov"}
MAX_BYTES = 10 * 1024 * 1024


def fetch(entry: dict, force: bool) -> int:
    url = entry["download_url"]
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        print(f"[BLOCKED] {entry['fetch_key']}: URL is not an allow-listed NASA HTTPS host.")
        return 2
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / entry["file_name"]
    if target.exists() and not force:
        print(f"[SKIP] {target.name} already present (raw files are immutable; use --force to re-download).")
        return 0
    request = urllib.request.Request(url, headers={"User-Agent": "cytozoe-setup/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60, context=ssl.create_default_context()) as resp:
            if resp.status != 200:
                print(f"[BLOCKED] {entry['fetch_key']}: HTTP {resp.status}. No substitute data was created.")
                return 2
            raw = resp.read(MAX_BYTES + 1)
    except Exception as exc:  # noqa: BLE001
        print(f"[BLOCKED] {entry['fetch_key']}: download failed ({type(exc).__name__}). No substitute data was created.")
        return 2
    if len(raw) > MAX_BYTES:
        print(f"[BLOCKED] {entry['fetch_key']}: response exceeds 10 MB.")
        return 2
    sha = hashlib.sha256(raw).hexdigest()
    tmp = target.with_suffix(".part")
    tmp.write_bytes(raw)
    tmp.replace(target)
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    record = {"fetch_key": entry["fetch_key"], "dataset_id": entry["id"], "file_name": entry["file_name"],
              "download_url": url, "fetched_at": fetched_at, "bytes": len(raw), "sha256": sha,
              "matches_pinned_sha256": sha == entry["expected_sha256"],
              "header": raw.decode("utf-8-sig", errors="replace").splitlines()[0][:2000]}
    (RAW / f"{entry['fetch_key']}.fetch.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    flag = "OK" if record["matches_pinned_sha256"] else "CHANGED"
    print(f"[{flag}] {target.name}: {len(raw)} bytes sha256={sha}")
    if not record["matches_pinned_sha256"]:
        print("        Source bytes differ from the pinned manifest. Inspect before importing; nothing was altered.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", action="append", default=[])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))["datasets"]
    keys = [e["fetch_key"] for e in entries] if args.all else args.dataset
    if not keys:
        parser.error("choose --dataset KEY or --all")
    code = 0
    for key in keys:
        entry = next((e for e in entries if e["fetch_key"] == key), None)
        if entry is None:
            print(f"[ERROR] unknown dataset '{key}'. Known: {', '.join(e['fetch_key'] for e in entries)}")
            code = 2
            continue
        code = max(code, fetch(entry, args.force))
    return code


if __name__ == "__main__":
    sys.exit(main())
