# Project Map

## Racine

- `montecarlo/` : application Python principale, backend FastAPI, app Streamlit historique, modules quantitatifs, tests.
- `ravinala-web/` : frontend React/Vite/TypeScript.
- `docs/` : documentation utile pour presentation, architecture, roadmaps et guides.
- `data/` : donnees locales et runtime historique.

## Montecarlo

- `backend/app/main.py` : factory FastAPI et assemblage des routers.
- `backend/app/routes/` : endpoints API par domaine.
- `backend/app/services/` : logique metier backend.
- `backend/app/schemas/` : contrats Pydantic.
- `backend/app/auth/` : JWT, password hashing, RBAC, audit.
- `backend/app/risk/` : moteurs et modeles de risque.
- `backend/app/workers/` : taches Celery.
- `src/app.py` : application Streamlit historique.
- `src/pages/` : pages Streamlit.
- `src/core/`, `src/modules/`, `src/analysis/`, `src/genesix/` : librairies analytics/quant.
- `tests/` : tests Python.

## Ravinala Web

- `src/App.tsx` : routes React.
- `src/main.tsx` : point d'entree React.
- `src/api/` : clients API Axios par domaine.
- `src/hooks/` : hooks React Query/Auth.
- `src/components/` : layout et composants UI.
- `src/pages/` : pages fonctionnelles de la demo web.
- `vite.config.ts` : proxy dev vers FastAPI sur `localhost:8000`.

## Rangement conseille apres l'interview

1. Garder le code source dans `montecarlo/`, `ravinala-web/`, `docs/`.
2. Sortir les fichiers runtime de Git : caches, exports, `.joblib`, `.parquet`, `.db`, `.xlsx`, `.pdf`.
3. Creer un commit baseline une fois la demo stabilisee.
4. Ajouter une documentation courte : installation, lancement, demo, limites.

