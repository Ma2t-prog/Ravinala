#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/montecarlo/backend"

export RAVINALA_SKIP_CELERY_WARMUP=1

if [ -x "../.venv/bin/python" ]; then
  PY="../.venv/bin/python"
else
  PY="python3"
fi

"$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

