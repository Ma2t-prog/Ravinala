# Ravinala Demo Package

Ce dossier contient une version propre pour la demo interview.

## Contenu

- `ravinala-web/` : frontend React/Vite sans `node_modules` ni `dist`.
- `montecarlo/backend/` : backend FastAPI.
- `montecarlo/src/` : modules Python utiles au backend et a la demo.
- `docs/` : scripts de presentation et setup Mac.
- `scripts/` : scripts de lancement Windows/Mac.

## Ce qui a ete exclu

- environnements virtuels Python ;
- `node_modules` ;
- builds `dist` ;
- caches ;
- exports PDF/XLSX ;
- artefacts ML lourds ;
- fichiers runtime `.env`.

## Lancement rapide Windows

Terminal 1 :

```powershell
.\scripts\start_backend_windows.ps1
```

Terminal 2 :

```powershell
.\scripts\start_frontend_windows.ps1
```

Ouvrir :

```text
http://127.0.0.1:5173
```

## Lancement rapide Mac

Voir :

```text
docs/MAC_DEMO_SETUP.md
```

Resume :

```bash
cd ravinala-web
npm install
cp .env.demo .env.local
npm run dev -- --host 127.0.0.1
```

Backend :

```bash
cd montecarlo
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r backend/requirements.txt
cd backend
export RAVINALA_SKIP_CELERY_WARMUP=1
../../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Parcours de demo conseille

1. Home
2. Market Intelligence
3. Options Analytics
4. Risk & Portfolio Suite
5. Portfolio Optimizer
6. Report Generator ou Compliance

Le pitch complet est dans :

```text
docs/INTERVIEW_DEMO_TRADING_ASSISTANT.md
```

