# CytoZoe one-time setup (Windows PowerShell). Network is needed only for this step.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"

Push-Location frontend
npm ci
npm run build
Pop-Location

.\.venv\Scripts\python.exe scripts\fetch_data.py --all
.\.venv\Scripts\python.exe scripts\verify_data.py --strict
.\.venv\Scripts\python.exe scripts\import_data.py --all
Write-Host "Setup complete. Start with: .\scripts\start.ps1  ->  http://127.0.0.1:8000"
