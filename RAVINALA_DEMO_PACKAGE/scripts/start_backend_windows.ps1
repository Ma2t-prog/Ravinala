$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "montecarlo\backend"
$python = Join-Path $root "montecarlo\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
  $python = Join-Path (Split-Path -Parent $root) ".venv\Scripts\python.exe"
}

if (-not (Test-Path $python)) {
  Write-Host "Python venv not found. Create one or install dependencies first." -ForegroundColor Red
  exit 1
}

$env:RAVINALA_SKIP_CELERY_WARMUP = "1"
Set-Location $backend
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

