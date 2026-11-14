# Security, privacy and operational behaviour

**Scope:** a local demo tool that processes public research CSVs and locally typed notes. It contains no real astronaut PHI. No regulatory compliance or security certification is claimed.

| Risk | Safeguard (implemented) |
|---|---|
| Accidental LAN exposure | Server binds `127.0.0.1`; `TrustedHostMiddleware` allow-list (`CYTOZOE_ALLOWED_HOSTS`) |
| Cross-site writes (CSRF) | Non-GET requests with a foreign `Origin` are rejected with 403; there is no CORS middleware |
| Runtime data exfiltration / CDN dependence | The app makes no outbound calls; fonts and icons are bundled; CSP sets `connect-src 'self'` |
| Malicious CSV | Extension check; ≤ 10 MB; UTF-8 only; NUL bytes rejected; exact schema; finite-number checks; temporary parse then a transactional insert; last good data kept |
| Source tampering / fake "NASA" data | Trust gate: only bytes whose SHA-256 is registered in the reviewed manifest (`expected_sha256` / `accepted_sha256`) are stored as NASA data, even on an empty DB. Each dataset carries a `provenance` class; NASA endpoints serve only `NASA_PINNED_VERIFIED`. Replacing a loaded version needs the CLI flag `--allow-new-version` |
| Resource exhaustion via upload | ≤ 10 MB, ≤ 100,000 rows, ≤ 20,000 bytes per line, checked before hashing/parsing |
| HTML / script injection | React escaping in the UI; `html.escape` on every field in the HTML export; CSP `script-src 'self'` |
| Spreadsheet formula injection | No CSV export is produced; JSON/HTML only |
| Path traversal | Static file serving resolves inside `frontend/dist` only |
| Prompt injection | No language model. Explanations accept only enum question IDs and never interpolate notes |
| Cross-case linkage | The API rejects `participant` on environment routes; a DB CHECK keeps environment reviews participant-free |
| Lost edits | Optimistic versioning (409); drafts kept on failure; "Saved locally" appears only after the commit |
| Log leakage | Logs record request ID, method, path, status and ms only — never notes or file bytes |
| Error leakage | Structured `{code,message,details}`; no tracebacks or filesystem paths |

## Operations
- Logs go to the server console. The database is `runtime/cytozoe.sqlite`, or `$CYTOZOE_DATA_DIR`.
- **Backup:** copy the SQLite file while the server is stopped. An exported packet is a handoff document, not a full database backup.
- **Recovery:** if the database is corrupt, move it aside, restart (migrations recreate the schema) and re-run `scripts/import_data.py --all`. Reviews can then be re-entered from the last export.
