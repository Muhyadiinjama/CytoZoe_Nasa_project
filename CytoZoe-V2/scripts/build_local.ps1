# Windows PowerShell equivalent of build_local.sh
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python scripts/verify_data.py --strict
python scripts/import_data.py --all
Push-Location frontend; npm run typecheck; npm run build; Pop-Location
Write-Host "done. Start with scripts\start.ps1"
