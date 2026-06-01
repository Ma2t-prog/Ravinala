#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/ravinala-web"

if [ ! -d "node_modules" ]; then
  npm install
fi

if [ ! -f ".env.local" ] && [ -f ".env.demo" ]; then
  cp .env.demo .env.local
fi

npm run dev -- --host 127.0.0.1

