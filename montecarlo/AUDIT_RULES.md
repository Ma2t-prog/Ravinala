# AUDIT RULES — GENESIX Ω Suite
# ══════════════════════════════════════════════════════════════════════
# Ce fichier est la LOI du projet. Tout agent IA (Claude, GPT, Gemini,
# Copilot, ou autre) DOIT lire ce fichier AVANT de modifier du code.
# Toute violation = rejet immédiat + correction obligatoire.
#
# Dernière mise à jour : 2026-03-23
# ══════════════════════════════════════════════════════════════════════

## COMMENT UTILISER CE FICHIER

1. Lis TOUT ce fichier avant de commencer à coder
2. Après chaque modification, vérifie la CHECKLIST en bas
3. Si tu violes une règle, corrige AVANT de passer à autre chose
4. En cas de doute, la règle la plus stricte s'applique
5. Exécute `python scripts/audit_guard.py` après tes modifications

---

## 🔴 RÈGLES BLOQUANTES (zéro tolérance)

### R1 — Pas de données aléatoires présentées comme des prédictions
```
INTERDIT : np.random.* dans tout code ML/signal/prediction
SAUF : dans les tests (tests/) ou dans du code explicitement marqué "simulation"
```
Si un modèle n'est pas disponible, retourne TOUJOURS :
```python
{
    'status': 'unavailable',
    'reason': '<raison_explicite>',
    'prediction': None,
    'confidence': 0.0
}
```
JAMAIS de bruit aléatoire vendu comme une vraie prédiction.

### R2 — risk_free_rate centralisé
```
INTERDIT : risk_free_rate = 0.02 (ou 0.04, 0.05) en dur dans un fichier
OBLIGATOIRE : import depuis le fichier constants centralisé
```
Fichiers source de vérité :
- Backend : `backend/app/risk/constants.py` → `RISK_FREE_RATE`
- Src : `src/genesix/constants.py` → `RISK_FREE_RATE`

Ces deux fichiers DOIVENT avoir la même valeur. Tout autre fichier DOIT importer depuis l'un de ces deux.

### R3 — Tout accès data passe par les providers
```
INTERDIT : yf.download(), yf.Ticker() dans services/ ou routes/
OBLIGATOIRE : passer par backend/app/providers/yfinance_adapter.py
```
Le pattern est : Route → Service → Provider → API externe.
Jamais Route → API externe directement.

### R4 — Schémas de données synchronisés
```
INTERDIT : définir le même modèle (ex: BacktestRun) dans deux fichiers
           avec des schémas différents
OBLIGATOIRE : si un modèle est défini en double, les colonnes DOIVENT
              être identiques + commentaire "MIRROR of <autre fichier>"
```
Fichiers concernés :
- `src/db/models.py`
- `backend/app/db/models.py`

### R5 — Persistance obligatoire
```
INTERDIT : stocker des résultats uniquement en mémoire (dict/list global)
OBLIGATOIRE : persister en DB tout résultat de calcul (ML, risk, backtest)
```
Chaque résultat doit survivre à un restart du serveur.

### R6 — Pas de secrets en dur
```
INTERDIT : api_key = "sk-...", password = "...", token = "..." dans le code
OBLIGATOIRE : variables d'environnement via os.environ ou .env
```

### R7 — Pas de code mort actif
```
INTERDIT : fonctionnalité désactivée qui peut être appelée silencieusement
OBLIGATOIRE : raise NotImplementedError ou retour explicite 'unavailable'
           + enregistrement dans feature_flags.py
```

---

## 🟡 RÈGLES DE QUALITÉ (fortement recommandé)

### Q1 — Validation API
- Chaque endpoint FastAPI a un `response_model=` Pydantic
- Chaque retour utilise l'envelope `ApiResponse[T]`
- Préfixe `/api/v1/` sur toutes les routes

### Q2 — Async/Celery
- Chaque tâche Celery a `soft_time_limit` + `hard_time_limit` + `max_retries`
- Les opérations longues (>5s) passent par Celery, pas par l'endpoint sync
- Chaque `.delay()` retourne un `job_id` consultable via `/api/v1/jobs/{id}`

### Q3 — ML Pipeline
- Tout entraînement compare au moins 2 baselines (naive + linear)
- Seuil de directional accuracy : rejeter si ≤ 0.52
- Persistance : joblib + metadata JSON + MLflow (si disponible)
- Feature flags pour les modèles expérimentaux

### Q4 — Backtesting
- Walk-forward validation obligatoire (pas de simple train/test split)
- `validate_no_lookahead()` exécuté avant chaque backtest
- Kill switches : max_drawdown, stop_loss, take_profit
- Comparaison automatique vs buy-hold + equal-weight
- Matrice de limitations documentée (survivorship bias, etc.)

### Q5 — Risk Governance
- VaR/CVaR : au moins 2 méthodes (historical + parametric ou Monte Carlo)
- Toutes les conventions dans `backend/app/risk/conventions.py`
- Snapshots risk persistés en DB (pas in-memory)
- Annualisation : 252 jours partout (jamais 250 ou 365)

### Q6 — Documentation code
- Docstring sur chaque module, classe, et fonction publique
- Type hints sur tous les paramètres et retours
- Commentaires sur la logique métier non-triviale

### Q7 — Architecture
- Pattern : Route → Service → Repository → DB
- Providers pour tout accès externe (API, data feeds)
- Pas de logique métier dans les routes (juste orchestration)
- Pas d'import circulaire

---

## 📋 CHECKLIST POST-MODIFICATION

Après TOUTE modification de code Python, vérifie ces points :

```bash
# Exécuter l'audit automatique complet :
python scripts/audit_guard.py

# Ou vérifier manuellement :

# 1. Pas de np.random dans le code ML/signal
grep -rn "np\.random" src/genesix/ml/ backend/app/ml/ src/genesix/intelligence/
# → DOIT retourner 0 résultats (hors tests/)

# 2. risk_free_rate pas hardcodé
grep -rn "risk_free_rate.*=.*0\." --include="*.py" | grep -v constants.py | grep -v test
# → DOIT retourner 0 résultats

# 3. Pas d'appel yfinance direct dans services
grep -rn "yf\.download\|yf\.Ticker" backend/app/services/
# → DOIT retourner 0 résultats

# 4. Pas de secrets hardcodés
grep -rn "api_key\s*=\s*['\"]" --include="*.py" | grep -v example | grep -v test
# → DOIT retourner 0 résultats

# 5. Imports pas cassés
python -c "import backend.app.main; print('Backend OK')"
python -c "import src.genesix; print('Src OK')"
```

---

## 🏗️ ARCHITECTURE DE RÉFÉRENCE

```
montecarlo/
├── backend/
│   └── app/
│       ├── main.py              ← Factory pattern create_app()
│       ├── routes/              ← 8 routers (market, ml, backtest, risk, ...)
│       ├── schemas/             ← Pydantic v2 (envelope, market, risk, ml, backtest)
│       ├── services/            ← Business logic (data_fetcher, etc.)
│       ├── providers/           ← Adapters API externes (yfinance, etc.)
│       │   ├── base.py          ← ABC + CanonicalQuote/Bond/FX
│       │   └── yfinance_adapter.py
│       ├── repositories/        ← Couche d'accès DB (à créer si manquant)
│       ├── db/models.py         ← 9 entités async (Mapped style)
│       ├── ml/                  ← Pipeline ML (training, prediction, tracking)
│       ├── risk/                ← Risk engine + conventions + constants
│       ├── backtest/            ← Engine backtesting
│       ├── workers/             ← Celery tasks (4 fichiers)
│       └── middleware/          ← CORS, Headers, Tracing
├── src/
│   ├── db/models.py             ← 14 entités sync (Column style)
│   ├── genesix/                 ← Suite GENESIX premium
│   │   ├── constants.py         ← Constantes partagées (MIRROR de backend)
│   │   ├── ml/                  ← ML prediction engine
│   │   ├── intelligence/        ← Signals
│   │   ├── optimizer/           ← Portfolio optimization
│   │   ├── risk/                ← Risk engine
│   │   └── utils/feature_flags.py
│   └── analysis/                ← Backtesting, financial analysis
├── scripts/
│   └── audit_guard.py           ← Audit automatique
├── AUDIT_RULES.md               ← CE FICHIER
└── AGENT_INSTRUCTIONS.md        ← Instructions pour les agents IA
```

---

## 📊 CONSTANTES DE RÉFÉRENCE

| Constante | Valeur | Source |
|-----------|--------|--------|
| RISK_FREE_RATE | 0.04 | backend/app/risk/constants.py |
| TRADING_DAYS | 252 | backend/app/risk/constants.py |
| VAR_CONFIDENCE | 0.95 | backend/app/risk/constants.py |
| MC_SIMULATIONS | 10,000 | backend/app/risk/constants.py |
| MC_SEED | 42 | backend/app/risk/constants.py |
| DIR_ACCURACY_THRESHOLD | 0.52 | Seuil minimum ML |

---

## 🔄 HISTORIQUE DES AUDITS

| Date | Score | Problèmes critiques | Status |
|------|-------|---------------------|--------|
| 2026-03-23 | 6.7/10 | 7 problèmes identifiés (audit manuel) | En cours de correction |
| 2026-03-23 | 0.0/10 | 46 blockers + 38 warnings (audit_guard.py) | En cours de correction |
| 2026-04-01 | ~7.5/10 | Audit complet + 4 fixes backend appliqués | Partiellement corrigé |

### Fixes appliqués (2026-04-01) — audit-réparation backend :
- ✅ main.py : ajout handler global `Exception` → ApiError format (500)
- ✅ main.py : ajout handler `RequestValidationError` → ApiError format (422)
- ✅ main.py : log WARNING au démarrage si SECRET_KEY = default (security_level=0)
- ✅ market.py : validation `sections` contre `_ALLOWED_SECTIONS` (frozenset) + log warning si inconnu
- ✅ market.py : contraintes `ge=1, le=200` sur `/indices` limit, `ge=1, le=50` sur `/fx-pairs` limit
- ✅ market.py : validation `section` param sur `/refresh` → 400 si valeur inconnue
- ✅ identity_service.py : login throttle Redis-backed (`_ThrottleStore`) avec fallback in-memory
- ✅ R4 vérifié : BacktestRun/BacktestTrade en sync (27 cols / 12 cols dans les deux fichiers)

### Problèmes ouverts (2026-04-01) :
1. ❌ R1: np.random dans 35 endroits (prediction_engine, contagion, nlp_engine, regime_ml, smart_alerts)
2. ❌ R2: risk_free_rate hardcode dans 2+ fichiers (0.02/0.04/0.05)
3. ❌ R3: yfinance direct dans data_fetcher.py + routes/ml.py + routes/risk.py (5 occurrences)
4. ✅ R4: BacktestRun/BacktestTrade synchronisés (corrigé)
5. ❌ R5: Cache in-memory dans services/cache.py (partiel — Redis fallback amélioré)
6. ❌ R6: Mot de passe hardcode dans auth.py (password='ravinala2026') — à vérifier si encore présent
7. ❌ Q1: Endpoints sans response_model — à auditer
8. ❌ Q2: Tâches Celery sans soft_time_limit
9. ❌ R7: Classes mortes (FullDashboardModel, EmailExportRequest, etc.)
10. ❌ ML artifacts jamais exécutés (dossiers vides)
11. ❌ Risk snapshots in-memory uniquement
12. ⚠️ Frontend : architecture chaotique — audit séparé à mener
