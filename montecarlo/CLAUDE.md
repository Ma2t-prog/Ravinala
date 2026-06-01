# CLAUDE.md — Instructions pour Claude Code

## RÈGLE ABSOLUE
Avant de modifier TOUT fichier Python dans ce projet, lis OBLIGATOIREMENT :
1. `AUDIT_RULES.md` — Les règles du projet (bloquantes + qualité)
2. `AGENT_INSTRUCTIONS.md` — Les instructions détaillées

## VALIDATION OBLIGATOIRE
Après toute modification, exécute :
```bash
python scripts/audit_guard.py --fix-hints
```
Si des violations bloquantes sont détectées, corrige-les AVANT de continuer.

## PROJET
GENESIX Ω Suite — Terminal financier professionnel.
Stack : FastAPI + Celery + PostgreSQL/TimescaleDB + Redis + React.

## INTERDICTIONS
- JAMAIS de np.random dans du code ML/signal/prediction
- JAMAIS de risk_free_rate hardcodé (importer depuis constants.py)
- JAMAIS d'appel yfinance direct dans services/ ou routes/
- JAMAIS de secrets en dur dans le code
- JAMAIS de stockage in-memory seul pour les résultats
