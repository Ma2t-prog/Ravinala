# INSTRUCTIONS FRONTEND — OBLIGATOIRE POUR TOUT AGENT

## CONTEXTE
Ce projet migre de Streamlit (Python) vers React (TypeScript).
L'objectif est 0% Streamlit, 100% React connecte au backend FastAPI.

Le backend est dans `backend/app/` avec des routes dans `backend/app/routes/`.
Le frontend React est dans `src/frontend/`.
Les anciennes pages Streamlit sont dans `src/pages/` (fichiers .py).

## REGLES ABSOLUES

### Migration
1. JAMAIS creer de nouveau fichier .py pour une page frontend
2. JAMAIS importer streamlit (import streamlit as st)
3. Toute nouvelle page = fichier .tsx dans frontend/src/pages/
4. Toute page doit utiliser les composants communs du projet

### Connexion Backend
5. Toute donnee affichee DOIT venir d'un appel API (pas de donnees hardcodees)
6. Utiliser le service API centralise (pas de fetch() en dur dans les composants)
7. Chaque appel API doit avoir un loading state + error handling
8. Les types TypeScript DOIVENT matcher les schemas Pydantic du backend

### Qualite
9. Pas de `any` en TypeScript (typer correctement)
10. Pas de `console.log` en production
11. Chaque page a un titre, un breadcrumb, et respecte le layout commun
12. Les onglets utilisent le composant Tabs commun du projet

### Fusion de pages
13. Quand on fusionne des pages, le plus gros absorbe le plus petit
14. Les features du petit deviennent des onglets/sections du gros
15. Les fichiers source sont SUPPRIMES apres fusion (pas de doublons)
16. App.tsx et la sidebar DOIVENT etre mis a jour apres chaque fusion

### Audit obligatoire
17. Apres TOUTE modification frontend, executer:
    ```
    python scripts/frontend_audit_agent.py
    python scripts/frontend_backend_bridge_audit.py
    ```
18. Score minimum accepte: 7/10 par page
19. 0 endpoint orphelin tolere

## SCRIPTS DISPONIBLES

### Audit general du frontend
```bash
python scripts/frontend_audit_agent.py [--fix-hints] [--verbose] [--page NomPage]
```
- Scanne tous les .tsx/.jsx
- Detecte les imports Streamlit restants
- Verifie la connexion backend
- Score chaque page de 0-10
- Produit un rapport JSON dans tmp/frontend_audit_report.json

### Fusion de pages
```bash
python scripts/frontend_fusion_agent.py --sources "Page1.tsx,Page2.tsx" --target "MergedPage.tsx" --tabs "Tab1,Tab2"
```
- Analyse les imports communs
- Detecte le code duplique
- Genere un squelette de page fusionnee avec onglets
- Produit un rapport de fusion dans tmp/

### Audit connexion frontend-backend
```bash
python scripts/frontend_backend_bridge_audit.py [--verbose]
```
- Matrice de couverture routes backend vs appels frontend
- Detecte les endpoints orphelins (backend sans frontend)
- Detecte les appels morts (frontend vers endpoint inexistant)
- Compare les types Pydantic vs TypeScript
- Produit un rapport JSON dans tmp/bridge_audit_report.json

### Detection Streamlit
```bash
python scripts/streamlit_detector.py [--detailed]
```
- Scanne TOUT le projet pour trouver des traces de Streamlit
- Score de migration: X% complete
- Liste exacte de ce qui doit encore etre migre
- Produit un rapport JSON dans tmp/streamlit_detector_report.json

## WORKFLOW TYPE POUR UN AGENT

1. **Avant de commencer**: Lire ce fichier
2. **Etat des lieux**: `python scripts/streamlit_detector.py`
3. **Travailler** sur le frontend (creation/modification de pages .tsx)
4. **Apres chaque modification**:
   - `python scripts/frontend_audit_agent.py --fix-hints`
   - `python scripts/frontend_backend_bridge_audit.py`
5. **Si fusion de pages**: `python scripts/frontend_fusion_agent.py --sources ... --target ... --tabs ...`
6. **Validation finale**: Tous les scores >= 7/10, 0 orphelin, 0 appel mort

## STRUCTURE DU PROJET

```
montecarlo/
├── backend/
│   └── app/
│       ├── routes/          # FastAPI endpoints
│       ├── schemas/         # Pydantic models
│       ├── services/        # Business logic
│       └── main.py          # App entry point
├── src/
│   ├── frontend/            # React app (TARGET)
│   │   └── src/
│   │       └── pages/       # React pages (.tsx)
│   └── pages/               # OLD Streamlit pages (.py) -> A MIGRER
├── scripts/
│   ├── frontend_audit_agent.py
│   ├── frontend_fusion_agent.py
│   ├── frontend_backend_bridge_audit.py
│   └── streamlit_detector.py
└── AGENT_INSTRUCTIONS_FRONTEND.md  # CE FICHIER
```
