# Security and privacy notes (local research demo)

There is no real patient information here: public, anonymised NASA research data and locally typed notes. No claim of
clinical, HIPAA or other certification is made.

Implemented safeguards (tested in `backend/tests/integration/test_api.py` and `tests/e2e`):
- Binds to **127.0.0.1** only; `Host` header must be 127.0.0.1/localhost (others → 400).
- Writes with a foreign `Origin` → 403. No CORS is enabled.
- The running app makes **no outbound requests**. `scripts/fetch_data.py` (setup only) fetches HTTPS NASA URLs from the manifest.
  The optional model URL must be a loopback address.
- Imports: `.csv` only, ≤ 10 MB, strict UTF-8, documented columns and sample format; parsed in memory and committed in one
  transaction; a failure keeps the last good dataset. Nothing uploaded is executed or rendered as HTML.
- Notes ≤ 4,000 chars; enums and dates validated by Pydantic; all SQL parameterised.
- Exports: HTML-escaped notes; CSV cells beginning with `= + - @` are prefixed to stop spreadsheet formulas; JSON never contains NaN.
- Content-Security-Policy `default-src 'self'` on every response; no inline scripts; fonts bundled.
- The assistant never reads notes or raw text; free-text questions are only classified; notes cannot inject instructions.
- Errors returned to the UI never include stack traces or file paths. Logs record request id, path, status and time — not notes.
- Database and notes live in `runtime/` (git-ignored). Back up by exporting; the export is not a full database backup.
