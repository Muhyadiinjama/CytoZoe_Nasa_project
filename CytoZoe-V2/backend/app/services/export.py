"""Local review packet: JSON, self-contained printable HTML, and a CSV subset. Nothing is sent anywhere."""
from __future__ import annotations

import csv
import html
import io
import json
from pathlib import Path
from typing import Any

from ..config import APP_VERSION, HEALTH_RULE_VERSION, RADIATION_RULE_VERSION, REPO_ROOT
from ..db import utcnow
from .reviews import Reviews
from .store import Store


def git_version() -> str:
    head = REPO_ROOT / ".git" / "HEAD"
    try:
        ref = head.read_text().strip()
        if ref.startswith("ref: "):
            return (REPO_ROOT / ".git" / ref[5:]).read_text().strip()[:12]
        return ref[:12]
    except OSError:
        return "not-a-git-checkout"


def build_packet(store: Store, reviews: Reviews) -> dict[str, Any]:
    items = reviews.list(limit=10_000)["items"]
    full = [reviews.get(r["id"]) for r in items]
    def section(case: str) -> list[dict[str, Any]]:
        return [{"review_id": r["id"], "title": r["title"], "status": r["status"], "note": r["note"], "follow_up_date": r["follow_up_date"],
                 "created_at": r["created_at"], "updated_at": r["updated_at"], "version": r["version"],
                 "evidence": r["evidence"], "events": r["events"]} for r in full if r["case"] == case]
    sources = [{"id": d["id"], "kind": d["kind"], "title": d["title"], "file_name": d["file_name"], "sha256": d["sha256"],
                "source_url": d["source_url"], "license_note": d["license_note"], "imported_at": d["imported_at"], "active": d["is_active"]}
               for d in store.datasets()]
    return {
        "packet": "CytoZoe review packet", "generated_at": utcnow(), "app_version": APP_VERSION, "git_version": git_version(),
        "rule_versions": {"health": HEALTH_RULE_VERSION, "radiation": RADIATION_RULE_VERSION},
        "notice": "Local research-demo export. Not a medical record, not clinical advice, not transmitted to anyone.",
        "sources": sources,
        "methods": {
            "health": "Retrospective preflight mean (n>=2) of the same participant and marker; delta = value - baseline; percent only if baseline != 0; strict range comparison, equality inside.",
            "radiation": "Conflicting duplicate timestamps quarantined; estimated sensor dose = sum of ((r_i+r_j)/2)*dt/3600 over adjacent accepted readings <= 300 s apart with no excluded reading between.",
        },
        "health": {"case": "NASA OSD-575 historical blood samples", "reviews": section("health")},
        "environment": {"case": "NASA RadLab ISS radiation record (separate case, not linked to any participant)", "reviews": section("environment")},
        "limitations": [
            "Historical research data; no live monitoring.",
            "Health and radiation records are separate cases and are never paired.",
            "No diagnosis, treatment advice, personal dose or risk estimate.",
            "Review status is an administrative workflow state, not a medical status.",
        ],
    }


def to_json(p: dict[str, Any]) -> str:
    return json.dumps(p, ensure_ascii=False, allow_nan=False, indent=2)


def to_html(p: dict[str, Any]) -> str:
    e = lambda v: html.escape("" if v is None else str(v), quote=True)  # noqa: E731
    def rev(r: dict[str, Any]) -> str:
        ev = r["evidence"]
        src = ev["source"]
        if ev["kind"] == "HEALTH_OBSERVATION":
            m, c = ev["measurement"], ev["comparison"]
            facts = (f"<p>{e(m['label'])}: <b>{e(m['value'])} {e(m['unit'])}</b> · supplied range {e(m['range_low'])}–{e(m['range_high'])} · {e(m['range_status'])}</p>"
                     f"<p>Retrospective preflight mean {e(None if c['baseline'] is None else round(c['baseline'], 4))} (n={e(c['n'])}); difference {e(None if c['delta'] is None else round(c['delta'], 4))}</p>")
        else:
            facts = f"<p>{e(ev['title'])}</p>"
        events = "".join(f"<li>{e(x['timestamp'])} · {e(x['action'])} · {e((x['after'] or {}).get('status'))}</li>" for x in r["events"])
        return (f"<section class=r><h3>{e(r['title'])}</h3>{facts}<p class=m>Source: {e(src['file_name'])} line {e(src['source_row'])} · SHA-256 {e(src['sha256'])}<br>{e(src['source_url'])}</p>"
                f"<p><b>Status:</b> {e(r['status'])} · <b>Follow-up date:</b> {e(r['follow_up_date'] or '—')} · v{e(r['version'])}</p>"
                f"<p><b>Reviewer note:</b></p><pre>{e(r['note'] or '(no note)')}</pre>"
                f"<p class=m>Limits: {e(' '.join(ev.get('limitations', [])))}</p><details><summary>History</summary><ul>{events}</ul></details></section>")
    secs = "".join(f"<h2>{e(p[k]['case'])}</h2>" + ("".join(rev(r) for r in p[k]["reviews"]) or "<p>No saved reviews.</p>") for k in ("health", "environment"))
    srcs = "".join(f"<li>{e(s['title'])} — {e(s['file_name'])} · SHA-256 {e(s['sha256'])} · {e(s['source_url'])} · {e(s['license_note'])}</li>" for s in p["sources"])
    return ("<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>CytoZoe review packet</title><style>body{font:15px/1.5 system-ui,sans-serif;color:#14283F;max-width:860px;margin:24px auto;padding:0 16px}"
            "h1{font-size:24px}h2{font-size:18px;margin-top:28px;border-bottom:1px solid #DCE4EB}.r{border:1px solid #DCE4EB;border-radius:10px;padding:12px 16px;margin:12px 0}"
            ".m{color:#526579;font-size:13px;overflow-wrap:anywhere}pre{white-space:pre-wrap;background:#F4F6F8;padding:8px;border-radius:6px}</style></head><body>"
            f"<h1>CytoZoe review packet</h1><p class=m>Generated {e(p['generated_at'])} · app {e(p['app_version'])} · git {e(p['git_version'])} · rules {e(', '.join(p['rule_versions'].values()))}</p>"
            f"<p><b>{e(p['notice'])}</b></p><h2>Sources</h2><ul>{srcs}</ul><h2>Methods</h2><p>{e(p['methods']['health'])}</p><p>{e(p['methods']['radiation'])}</p>"
            f"{secs}<h2>Limitations</h2><ul>{''.join(f'<li>{e(x)}</li>' for x in p['limitations'])}</ul></body></html>")


def _cell(v: Any) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s  # spreadsheet formula injection guard


def to_csv(p: dict[str, Any]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["case", "review_id", "title", "status", "follow_up_date", "note", "evidence_id", "source_file", "source_row", "sha256", "updated_at"])
    for k in ("health", "environment"):
        for r in p[k]["reviews"]:
            s = r["evidence"]["source"]
            w.writerow([_cell(x) for x in (k, r["review_id"], r["title"], r["status"], r["follow_up_date"], r["note"],
                                           r["evidence"]["evidence_id"], s["file_name"], s["source_row"], s["sha256"], r["updated_at"])])
    return buf.getvalue()


def safe_filename(fmt: str) -> str:
    return f"cytozoe-review-packet.{fmt}"


_ = Path  # keep import for type hints in callers
