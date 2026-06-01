# AGENT INSTRUCTIONS — GENESIX Ω Suite
# ══════════════════════════════════════════════════════════════════════
# Ce fichier s'adresse à TOUT agent IA travaillant sur ce projet :
# Claude, GPT, Gemini, Copilot, Cursor, Windsurf, ou autre.
#
# LIS CE FICHIER EN ENTIER AVANT DE TOUCHER AU CODE.
# ══════════════════════════════════════════════════════════════════════

## ÉTAPE 0 — AVANT TOUTE MODIFICATION

1. Lis `AUDIT_RULES.md` à la racine du projet — c'est la loi absolue
2. Lis ce fichier en entier
3. Comprends l'architecture (décrite dans AUDIT_RULES.md section Architecture)
4. Identifie les fichiers que tu vas modifier
5. Vérifie que tes modifications ne violent AUCUNE règle bloquante (R1-R7)

## ÉTAPE 1 — PENDANT LA MODIFICATION

### Ce que tu DOIS faire :
- Respecter les patterns existants (factory pattern, providers, schemas)
- Utiliser les types canoniques (CanonicalQuote, CanonicalBond, etc.)
- Importer les constantes depuis les fichiers constants.py (JAMAIS hardcoder)
- Ajouter des type hints et docstrings
- Utiliser Pydantic v2 pour les schemas API
- Persister tout résultat en DB (jamais in-memory seul)

### Ce que tu NE DOIS PAS faire :
- Ajouter np.random dans du code ML/signal/prediction
- Hardcoder risk_free_rate, trading_days, ou d'autres constantes
- Appeler yfinance directement dans services/ (passe par providers/)
- Créer un nouveau modèle DB sans vérifier s'il existe déjà dans l'autre models.py
- Stocker des secrets dans le code
- Laisser du code mort sans le marquer dans feature_flags.py

## ÉTAPE 2 — APRÈS LA MODIFICATION

Exécute OBLIGATOIREMENT :
```bash
python scripts/audit_guard.py
```

Si le script signale des violations → corrige AVANT de considérer ton travail terminé.

Si tu ne peux pas exécuter le script, vérifie manuellement :
1. `grep -rn "np.random" src/genesix/ml/ backend/app/ml/` → 0 résultats
2. `grep -rn "risk_free_rate.*=.*0\." --include="*.py"` → seulement dans constants.py
3. `grep -rn "yf.download\|yf.Ticker" backend/app/services/` → 0 résultats
4. Tes imports fonctionnent
5. Tes types de retour matchent les schemas Pydantic

---

## CONTEXTE TECHNIQUE RAPIDE

| Composant | Techno | Localisation |
|-----------|--------|-------------|
| Backend API | FastAPI + Pydantic v2 | backend/app/ |
| Async tasks | Celery + Redis | backend/app/workers/ |
| DB sync | SQLAlchemy (Column style) | src/db/models.py |
| DB async | SQLAlchemy (Mapped style) | backend/app/db/models.py |
| ML | XGBoost/LightGBM/RandomForest + MLflow | src/genesix/ml/ + backend/app/ml/ |
| Risk | VaR/CVaR multi-method | src/genesix/risk/ + backend/app/risk/ |
| Backtesting | Walk-forward + kill switches | src/analysis/ + backend/app/backtest/ |
| Data providers | yfinance via adapter pattern | backend/app/providers/ |
| Feature flags | Registres DISABLED/EXPERIMENTAL | src/genesix/utils/feature_flags.py |
| Frontend | React + React Router | ravinala-web/ (projet séparé) |

## FICHIERS CRITIQUES — NE PAS CASSER

Ces fichiers sont au coeur du système. Toute modification doit être faite avec précaution :

| Fichier | Rôle | Attention |
|---------|------|-----------|
| backend/app/main.py | Factory + startup | Ne pas changer l'ordre des middleware |
| backend/app/db/models.py | Modèles DB async | Garder en sync avec src/db/models.py |
| src/db/models.py | Modèles DB sync | Garder en sync avec backend/app/db/models.py |
| backend/app/schemas/envelope.py | ApiResponse[T] | Tous les endpoints en dépendent |
| backend/app/providers/base.py | ABC providers | Interface = contrat, pas toucher sans raison |
| backend/app/risk/constants.py | Constantes risk | Source de vérité unique |
| src/genesix/utils/feature_flags.py | Feature gates | Tout code désactivé doit y être |

## PROBLÈMES CONNUS (à corriger)

Ces problèmes sont documentés dans AUDIT_RULES.md section "Problèmes ouverts".
Si tu tombes dessus pendant ton travail, CORRIGE-LES en priorité.

1. `src/genesix/ml/prediction_engine.py` — 6x np.random (lignes ~250, 257, 260, 278, 382, 390, 428)
2. risk_free_rate hardcodé : 0.02 dans backtesting/risk_metrics, 0.04 dans portfolio, 0.05 dans optimizer
3. `backend/app/services/data_fetcher.py` — instancie YFinanceProvider mais ne l'utilise pas
4. BacktestRun : 10 colonnes dans src/ vs 24 dans backend/ — schémas différents
5. AuditEvent dans src/db/models.py — jamais importé/utilisé
6. Risk snapshots — in-memory seulement, pas persistés en DB
7. data/ml_artifacts/ et data/mlruns/ — dossiers vides, jamais exécuté

## QUAND TU AS UN DOUTE

- Architecture → regarde `backend/app/main.py` et les `routes/`
- Schémas → regarde `backend/app/schemas/`
- Patterns → regarde comment `backtest.py` route est implémentée (le plus propre)
- Constantes → `backend/app/risk/constants.py` (à créer si manquant)
- Feature flags → `src/genesix/utils/feature_flags.py`
