"""Local review-packet export (JSON / self-contained HTML). A local download, never a transmission."""
from __future__ import annotations

import html
import json
import sqlite3
from typing import Any

from .. import config, db
from ..engines import environment, health, quality
from . import environment_service, health_service, reviews

DISCLAIMER = (
    "CytoZoe research demonstration. Historical public NASA research data; not live astronaut monitoring, "
    "not a diagnosis and not a clinical device. The health and environment case studies are separate and "
    "are never linked at person level. Review status is an administrative workflow state."
)


def build_packet(conn: sqlite3.Connection) -> dict[str, Any]:
    datasets = [
        {k: r[k] for k in ("id", "kind", "title", "provider", "file_name", "sha256", "byte_count", "source_url",
                            "download_url", "license_note", "citation", "fetched_at", "imported_at", "parser_version",
                            "provenance") if k in r.keys()}
        for r in conn.execute("SELECT * FROM datasets ORDER BY id")
    ]
    items = reviews.all_full(conn)
    return {
        "export_schema_version": "1.0",
        "generated_at": db.utc_now(),
        "app": {"name": "CytoZoe", "version": config.APP_VERSION, "git_version": config.git_version(),
                "db_schema_version": db.schema_version()},
        "disclaimer": DISCLAIMER,
        "rule_versions": {"quality": quality.PARSER_VERSION, "health": health.RULE_VERSION,
                          "environment": environment.RULE_VERSION},
        "datasets": datasets,
        "health": {
            "case_note": "OSD-575 Inspiration4 comprehensive metabolic panel — historical research samples.",
            "limitations": health_service.HEALTH_LIMITATIONS,
            "reviews": [r for r in items if r["case"] == "health"],
        },
        "environment": {
            "case_note": "RadLab DosTel1, ISS Columbus, 1 March 2022 — separate case study, not linked to any participant.",
            "limitations": environment_service.ENV_LIMITATIONS,
            "reviews": [r for r in items if r["case"] == "environment"],
        },
    }


def _provenance_label(p: str | None) -> str:
    return {"NASA_PINNED_VERIFIED": "Verified NASA snapshot (SHA-256 registered in the reviewed manifest)"}.get(
        p or "", "NOT a verified NASA snapshot")


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _num(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        text = f"{value:.{digits}f}"
        return _e(text.rstrip("0").rstrip(".") if "." in text else text)
    return _e(value)


def _review_html(r: dict[str, Any]) -> str:
    ev = r["evidence_snapshot"]
    m, c, s = ev["measurement"], ev["comparison"], ev["source"]
    if ev["case"] == "health":
        facts = [
            ("Participant / visit", f"{ev['context']['participant_id']} · {ev['context']['visit_label']}"),
            ("Observed", f"{_num(m['value'])} {_e(m['unit'])}"),
            ("Supplied range", f"{_num(m['range_low'])} – {_num(m['range_high'])} {_e(m['unit'])}"),
            ("Range status", _e(m["range_status"])),
            ("Retrospective preflight mean", f"{_num(c['baseline'], 6)} {_e(m['unit'])} (n = {_e(c['n'])})"),
            ("Δ / %Δ", f"{_num(c['delta'], 6)} / {_num(c['percent_delta'], 4)}%"),
            ("Source", f"{_e(s['file_name'])}, data row {_e(s['source_row'])}, column {_e(s['source_columns']['value'])}"),
        ]
    elif ev["kind"] == "DATA_QUALITY":
        facts = [("Instrument", "DosTel1 · ISS Columbus"), ("Timestamp (source clock)", _e(m["timestamp"])),
                 ("Conflicting rows", "; ".join(f"row {_e(x['source_row'])}: {_e(x['rate_raw'])} µGy/hour" for x in m["rows"])),
                 ("Decision", "All rows quarantined from derived analysis")]
    else:
        facts = [("Instrument", "DosTel1 · ISS Columbus"),
                 ("Estimated dose over covered intervals at sensor", f"{_num(m['estimated_sensor_dose_uGy'], 3)} µGy"),
                 ("Covered / span (s)", f"{_num(m['covered_seconds'], 0)} / {_num(m['span_seconds'], 0)}"),
                 ("Rows", f"{_e(m['raw_rows'])} raw · {_e(m['accepted_rows'])} accepted · {_e(m['quarantined_conflict_rows'])} quarantined")]
    fact_rows = "".join(f"<tr><th scope='row'>{k}</th><td>{v}</td></tr>" for k, v in facts)
    events = "".join(
        f"<li><time>{_e(e['timestamp'])}</time> — {_e(e['action'])}: status {_e((e['before'] or {}).get('status', '—'))} → {_e(e['after']['status'])}, version {_e(e['after']['version'])}</li>"
        for e in r["events"]
    )
    return f"""
<article class="review">
  <h3>{_e(r['title'])}</h3>
  <p class="meta">Status <strong>{_e(r['status'])}</strong> · follow-up date {_e(r['follow_up_date'] or '—')} · updated {_e(r['updated_at'])} · version {_e(r['version'])}</p>
  <h4>Reviewer note</h4>
  <p class="note">{_e(r['note'])}</p>
  <h4>Evidence (frozen when first reviewed)</h4>
  <table>{fact_rows}<tr><th scope='row'>Evidence ID</th><td><code>{_e(ev['evidence_id'])}</code></td></tr>
  <tr><th scope='row'>Rule version</th><td>{_e(r['rule_version'])}</td></tr>
  <tr><th scope='row'>Dataset SHA-256</th><td><code>{_e(r['dataset_sha256'])}</code></td></tr></table>
  <h4>Audit history</h4><ul>{events}</ul>
</article>"""


def render_html(packet: dict[str, Any]) -> str:
    ds_rows = "".join(
        f"<tr><td>{_e(d['title'])}<br><small>{_e(d['provider'])}</small></td><td>{_e(d['file_name'])}</td>"
        f"<td><code>{_e(d['sha256'])}</code><br><small>{_e(_provenance_label(d.get('provenance')))}</small></td><td><a href=\"{_e(d['source_url'])}\">{_e(d['source_url'])}</a><br><small>{_e(d['license_note'])}</small></td></tr>"
        for d in packet["datasets"]
    )

    def section(key: str, heading: str) -> str:
        sec = packet[key]
        body = "".join(_review_html(r) for r in sec["reviews"]) or "<p>No saved reviews in this case.</p>"
        lims = "".join(f"<li>{_e(x)}</li>" for x in sec["limitations"])
        return f"<section><h2>{_e(heading)}</h2><p>{_e(sec['case_note'])}</p>{body}<h4>Limitations</h4><ul>{lims}</ul></section>"

    app = packet["app"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CytoZoe review packet</title>
<style>
body{{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#14283F;background:#fff;max-width:960px;margin:32px auto;padding:0 16px;line-height:1.5;font-size:15px}}
h1{{font-size:26px;margin:0 0 4px}} h2{{font-size:20px;border-bottom:2px solid #DCE4EB;padding-bottom:6px;margin-top:40px}}
h3{{font-size:17px;margin:0 0 4px}} h4{{font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#526579;margin:16px 0 4px}}
.banner{{background:#FFF3DF;color:#7a3c06;border:1px solid #f0d6ad;border-radius:10px;padding:12px 14px}}
.meta{{color:#526579;font-size:13px}} .note{{white-space:pre-wrap;background:#F4F6F8;border-radius:8px;padding:10px 12px}}
table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border:1px solid #DCE4EB;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#F4F6F8;font-weight:600;width:34%}} code{{font-size:12px;word-break:break-all}}
.review{{border:1px solid #DCE4EB;border-radius:14px;padding:16px 18px;margin:16px 0;break-inside:avoid}}
@media print{{body{{margin:0}} a{{color:inherit}}}}
</style></head><body>
<h1>CytoZoe review packet</h1>
<p class="meta">Generated {_e(packet['generated_at'])} (UTC) · CytoZoe {_e(app['version'])} · build {_e(app['git_version'])} · DB schema {_e(app['db_schema_version'])} · rules {_e(', '.join(f'{k} {v}' for k, v in packet['rule_versions'].items()))}</p>
<p class="banner">{_e(packet['disclaimer'])} This file was generated locally; it has not been sent anywhere.</p>
<h2>Sources</h2><table><tr><th>Dataset</th><th>File</th><th>SHA-256</th><th>Source</th></tr>{ds_rows}</table>
{section('health', 'Health case · OSD-575 Inspiration4')}
{section('environment', 'Environment case · ISS DosTel1 (separate)')}
</body></html>"""


def to_json(packet: dict[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False, indent=2, allow_nan=False)
