# Windows PowerShell: start the local service on http://127.0.0.1:8000 (loopback only).
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
if (-not (Test-Path "frontend/dist/index.html")) { Write-Error "Frontend not built: run scripts\build_local.ps1 first" }
python scripts/import_data.py --all | Out-Null
$port = if ($env:CYTOZOE_PORT) { $env:CYTOZOE_PORT } else { "8000" }
Write-Host "CytoZoe: http://127.0.0.1:$port/overview"
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $port
