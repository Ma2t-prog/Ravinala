$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "ravinala-web"

Set-Location $frontend

if (-not (Test-Path "node_modules")) {
  Write-Host "node_modules not found. Running npm install..." -ForegroundColor Yellow
  npm install
}

if (-not (Test-Path ".env.local") -and (Test-Path ".env.demo")) {
  Copy-Item ".env.demo" ".env.local"
}

npm run dev -- --host 127.0.0.1

