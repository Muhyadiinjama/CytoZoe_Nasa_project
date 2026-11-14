#!/usr/bin/env python3
"""ONE-TIME setup download of the two NASA source files into data/raw/ (never called by the running app).

    python scripts/fetch_data.py --dataset osd575-cmp
    python scripts/fetch_data.py --dataset radlab-dostel1-2022-03-01
    python scripts/fetch_data.py --all

Only HTTPS URLs on NASA domains from data/manifests/sources.json are fetched. Existing files are never
overwritten; a different download is saved beside them as *.new for deliberate review.
"""
from __future__ import annotations

import argparse
import ssl
import sys
import urllib.request
from urllib.parse import urlparse

from _common import RAW, manifest, sha256_file

ALLOWED = (".nasa.gov",)


def fetch(entry: dict) -> int:
    url = entry["download_url"]
    u = urlparse(url)
    if u.scheme != "https" or not (u.hostname or "").endswith(ALLOWED):
        print(f"REFUSED non-allowlisted URL: {url}")
        return 2
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / entry["file_name"]
    target = dest if not dest.exists() else dest.with_suffix(dest.suffix + ".new")
    print(f"GET {url}")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "CytoZoe-setup/2.0"}),
                                    timeout=60, context=ssl.create_default_context()) as r:
            data = r.read(11 * 1024 * 1024)
    except Exception as e:  # report the block; never substitute data
        print(f"BLOCKED: could not download ({type(e).__name__}: {e}). No data was invented. Copy the file into data/raw/ manually.")
        return 1
    target.write_bytes(data)
    sha = sha256_file(target)
    match = "MATCHES manifest" if sha == entry["sha256"] else "DIFFERS from manifest - inspect before using"
    print(f"saved {target.relative_to(RAW.parent.parent)}  sha256={sha}  {match}")
    return 0 if sha == entry["sha256"] else 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=[d["key"] for d in manifest()])
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    todo = manifest() if a.all else [d for d in manifest() if d["key"] == a.dataset]
    if not todo:
        ap.error("choose --dataset or --all")
    return max(fetch(d) for d in todo)


if __name__ == "__main__":
    sys.exit(main())
