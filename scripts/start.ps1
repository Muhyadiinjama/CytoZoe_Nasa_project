# Start CytoZoe on loopback only (Windows PowerShell). Works with the internet disconnected.
Set-Location (Join-Path $PSScriptRoot "..")
Write-Host "CytoZoe running at http://127.0.0.1:8000  (Ctrl+C to stop)"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
