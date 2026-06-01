# Demo Mac - Checklist

Objectif : faire tourner une demo fluide sur un Mac peu puissant, sans Redis, sans Celery, sans base PostgreSQL, et sans setup lourd.

## Strategie recommandee

Utiliser :

- le frontend React en mode Vite ;
- le backend FastAPI en mode local leger ;
- `RAVINALA_SKIP_CELERY_WARMUP=1` pour eviter le blocage Redis/Celery ;
- un parcours de demo court ;
- des screenshots ou une video de secours.

Ne pas utiliser pour la demo :

- training ML lourd ;
- Celery worker ;
- Redis obligatoire ;
- exports PDF/XLSX si non testes juste avant ;
- pages experimentales qui appellent beaucoup d'APIs externes.

## A transferer sur le Mac

Transferer seulement le necessaire :

- `montecarlo/`
- `ravinala-web/`
- `docs/`
- `.gitignore`
- les fichiers README utiles

Eviter de transferer :

- `.venv/`
- `.uv-cache/`
- `.uv-python/`
- `node_modules/`
- `ravinala-web/dist/`
- `tmp/`
- `*.joblib`
- `*.parquet`
- `*.xlsx`
- `*.pdf`
- caches Python `__pycache__/`

## Installation Mac

Depuis le dossier du projet :

```bash
cd ravinala-web
npm install
```

Backend :

```bash
cd ../montecarlo
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r backend/requirements.txt
```

Si l'installation backend est trop longue, priorite a la demo frontend avec pages statiques et screenshots.

## Lancement demo

Terminal 1 - backend :

```bash
cd montecarlo/backend
export RAVINALA_SKIP_CELERY_WARMUP=1
../../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verifier :

```bash
curl http://127.0.0.1:8000/health
```

Terminal 2 - frontend :

```bash
cd ravinala-web
cp .env.demo .env.local
npm run dev -- --host 127.0.0.1
```

Ouvrir :

```text
http://127.0.0.1:5173
```

## Parcours court

1. Home
2. Market Intelligence
3. Options Analytics
4. Risk & Portfolio Suite
5. Portfolio Optimizer
6. Report Generator ou Compliance si stable

## Plan B obligatoire

Avant l'entretien, preparer :

- 5 captures d'ecran du parcours ci-dessus ;
- une video locale de 2 minutes ;
- le pitch dans `docs/INTERVIEW_DEMO_TRADING_ASSISTANT.md`.

Phrase si le Mac rame :

> Pour eviter de perdre du temps sur la machine de demo, j'ai aussi prepare des captures du parcours principal. Le point important est le workflow : marche, pricing, risque, portefeuille, reporting.

## Verification la veille

```bash
cd ravinala-web
npm run build
```

Puis :

```bash
curl http://127.0.0.1:8000/health
```

Si ces deux commandes passent, la demo est assez solide.

