# Étape 13 — Frontend / Backend Boundary & Découplage


> [!WARNING]
> **Document status: superseded by primary source docs**
> This file is kept for project history and progress traceability.
> Do **not** treat it as current compliance proof or backend architecture evidence.
> For current source-based truth, use:
> - `docs/PRIMARY_SOURCE_BASELINE_INDEX.md`
> - `docs/PRIMARY_SOURCE_DELTA_LEDGER.md`
> - `docs/PRIMARY_SOURCE_ACTIVE_REQUIREMENTS.md`

> Date : 2026-03-23  
> Statut : **historical**

---

## 1. CARTE DU COUPLAGE ACTUEL

### Légende

- 🟢 **CLEAN** : juste affichage, appelle le backend API ou wrappers
- 🟡 **ACCEPTABLE TEMPORAIREMENT** : logique légère / éducative, peut attendre
- 🔴 **BACKEND DÉGUISÉ** : calcul lourd, DOIT migrer côté backend
- ⚫ **OBSOLÈTE** : remplacé par React, peut être ignoré

### Tableau complet (50 pages Streamlit)

| #   | Page                               |                                      Imports genesix/\*                                      | yfinance |           Calcul lourd            |     Catégorie      |
| --- | ---------------------------------- | :------------------------------------------------------------------------------------------: | :------: | :-------------------------------: | :----------------: |
| 1   | admin.py                           |                                              —                                               |    —     |                 —                 |    ⚫ OBSOLÈTE     |
| 2   | advanced_exotics.py                |                                              —                                               |    —     |        Monte Carlo exotics        |    ⚫ OBSOLÈTE     |
| 3   | alt_data.py                        |                                              —                                               |    ✅    |          Fetch sentiment          |    ⚫ OBSOLÈTE     |
| 4   | asset_explorer.py                  |                                              —                                               |    —     |              Wrapper              |    ⚫ OBSOLÈTE     |
| 5   | backtesting_page.py                |                                              —                                               |    —     |       Kupiec, VaR backtest        |    ⚫ OBSOLÈTE     |
| 6   | **backtest_results.py**            |                                 `genesix.backtesting_engine`                                 |    —     |        Backtest execution         | 🔴 BACKEND DÉGUISÉ |
| 7   | **company_analyzer.py**            |                                              —                                               |    ✅    |       DCF, fundamentals, FX       | 🔴 BACKEND DÉGUISÉ |
| 8   | custom_product.py                  |                                              —                                               |    —     |          MC multi-asset           |    ⚫ OBSOLÈTE     |
| 9   | documentation.py                   |                                              —                                               |    —     |              PDF gen              |   🟡 ACCEPTABLE    |
| 10  | **enterprise_valuations.py**       |                                       `src/analysis/`                                        |    ✅    |        DCF, peer comp, MC         | 🔴 BACKEND DÉGUISÉ |
| 11  | equity_research.py                 |                                              —                                               |    —     |              Wrapper              |    ⚫ OBSOLÈTE     |
| 12  | esg.py                             |                                              —                                               |    ✅    |         Greenium, carbon          |   🟡 ACCEPTABLE    |
| 13  | etf_explorer.py                    |                                              —                                               |    —     |              Wrapper              |    ⚫ OBSOLÈTE     |
| 14  | financial_analysis.py              |                                       `src/analysis/`                                        |    —     |              Wrapper              |    ⚫ OBSOLÈTE     |
| 15  | fixed_income.py                    |                                              —                                               |    —     |              Wrapper              |    ⚫ OBSOLÈTE     |
| 16  | **genesix_advanced_analysis.py**   |                                 `genesix.backtesting_engine`                                 |    ✅    |     Efficient frontier, optim     | 🔴 BACKEND DÉGUISÉ |
| 17  | **genesix_data_layer.py**          |                     `genesix.data.feature_store`, `genesix.utils.config`                     |    ✅    |            Data infra             | 🔴 BACKEND DÉGUISÉ |
| 18  | genesix_home.py                    |                                              —                                               |    —     |              Landing              |      🟢 CLEAN      |
| 19  | **genesix_intelligence.py**        |                             `genesix.intelligence.*` (4 modules)                             |    ✅    |   ML signals, regime detection    | 🔴 BACKEND DÉGUISÉ |
| 20  | **genesix_market_intelligence.py** |              `genesix.data.market_fetcher`, `genesix.intelligence.smart_alerts`              |    ✅    | Anomaly detection, health scoring | 🔴 BACKEND DÉGUISÉ |
| 21  | **genesix_ml_engine.py**           | `genesix.ml.prediction_engine`, `genesix.intelligence.regime_ml`, `genesix.risk.risk_engine` |    —     |   Ensemble ML, regime detection   | 🔴 BACKEND DÉGUISÉ |
| 22  | genesix_portfolio_monitor.py       |                                              —                                               |    —     |           Light pandas            |   🟡 ACCEPTABLE    |
| 23  | **genesix_risk_engine.py**         |                    `genesix.risk_metrics_engine`, `genesix.design_system`                    |    ✅    |     VaR, CVaR, stress, factor     | 🔴 BACKEND DÉGUISÉ |
| 24  | greeks_sensitivity_lab.py          |                                              —                                               |    —     |         Analytical Greeks         |    ⚫ OBSOLÈTE     |
| 25  | hedging_page.py                    |                                              —                                               |    —     |           Delta hedging           |    ⚫ OBSOLÈTE     |
| 26  | home.py                            |                                              —                                               |    —     |              Landing              |    ⚫ OBSOLÈTE     |
| 27  | **instrument_detail.py**           |                     `genesix.universe_explorer`, `genesix.design_system`                     |    ✅    |       Data fetch + display        | 🔴 BACKEND DÉGUISÉ |
| 28  | intelligence_center.py             |                                              —                                               |    —     |           Display only            |    ⚫ OBSOLÈTE     |
| 29  | learn.py                           |                                              —                                               |    —     |            Educational            |   🟡 ACCEPTABLE    |
| 30  | legal.py                           |                                              —                                               |    —     |            Static text            |    ⚫ OBSOLÈTE     |
| 31  | live_market.py                     |                                              —                                               |    ✅    |      Live Greeks, technicals      |    ⚫ OBSOLÈTE     |
| 32  | macro_analysis.py                  |                                              —                                               |    —     |              Wrapper              |    ⚫ OBSOLÈTE     |
| 33  | market_news.py                     |                                              —                                               |    —     |              Wrapper              |    ⚫ OBSOLÈTE     |
| 34  | ml_pricing_page.py                 |                                              —                                               |    —     |      ML training, prediction      |    ⚫ OBSOLÈTE     |
| 35  | museum_exotics.py                  |                                              —                                               |    —     |         Path-dependent MC         |    ⚫ OBSOLÈTE     |
| 36  | **physics_demo.py**                |                               `genesix.physics.*` (8 classes)                                |    —     |    LPPL, seismograph, wavelets    | 🔴 BACKEND DÉGUISÉ |
| 37  | pnl_attribution.py                 |                                              —                                               |    —     |       Taylor decomposition        |    ⚫ OBSOLÈTE     |
| 38  | portfolio_optimizer.py             |                                              —                                               |    —     |              Wrapper              |    ⚫ OBSOLÈTE     |
| 39  | position_book.py                   |                                              —                                               |    —     |         Multi-leg Greeks          |    ⚫ OBSOLÈTE     |
| 40  | pricing_center.py                  |                                              —                                               |    —     |          Vanilla Greeks           |    ⚫ OBSOLÈTE     |
| 41  | probability_bible_page.py          |                                              —                                               |    —     |         Distribution sims         |   🟡 ACCEPTABLE    |
| 42  | quantum_academy.py                 |                                              —                                               |    —     |            Educational            |   🟡 ACCEPTABLE    |
| 43  | regulatory_capital.py              |                                              —                                               |    —     |          FRTB, Basel IV           |    ⚫ OBSOLÈTE     |
| 44  | **risk_engine_dashboard.py**       |                    `genesix.risk_metrics_engine`, `genesix.design_system`                    |    ✅    |     VaR, stress, correlation      | 🔴 BACKEND DÉGUISÉ |
| 45  | risk_management.py                 |                                              —                                               |    —     |        VaR, stress testing        |    ⚫ OBSOLÈTE     |
| 46  | sandbox.py                         |                                              —                                               |    —     |          MC structuring           |    ⚫ OBSOLÈTE     |
| 47  | scenario_matrix.py                 |                                              —                                               |    —     |        3D Greeks surfaces         |    ⚫ OBSOLÈTE     |
| 48  | strategy_lab.py                    |                                              —                                               |    —     |         Multi-leg Greeks          |    ⚫ OBSOLÈTE     |
| 49  | structuring.py                     |                                              —                                               |    —     |              Wrapper              |    ⚫ OBSOLÈTE     |
| 50  | tax_lab.py                         |                                              —                                               |    —     |        Tax sim (CSV demo)         |   🟡 ACCEPTABLE    |
| 51  | tradebook.py                       |                                              —                                               |    —     |              Wrapper              |    ⚫ OBSOLÈTE     |
| 52  | **universe_screener.py**           |                     `genesix.universe_explorer`, `genesix.design_system`                     |    —     |          Screener logic           | 🔴 BACKEND DÉGUISÉ |
| 53  | **universe_search.py**             |                     `genesix.universe_explorer`, `genesix.design_system`                     |    —     |           Search logic            | 🔴 BACKEND DÉGUISÉ |
| 54  | vol_calibration_page.py            |                                              —                                               | ⚠️ opt.  |         SABR, SVI, Heston         |    ⚫ OBSOLÈTE     |

### Résumé par catégorie

| Catégorie                        | Nombre | %    |
| -------------------------------- | ------ | ---- |
| 🔴 BACKEND DÉGUISÉ               | **14** | 26%  |
| 🟡 ACCEPTABLE TEMPORAIREMENT     | **7**  | 13%  |
| 🟢 CLEAN                         | **1**  | 2%   |
| ⚫ OBSOLÈTE (remplacé par React) | **32** | 59%  |
| **Total**                        | **54** | 100% |

---

## 2. PLAN DE DÉCOUPLAGE

### Pages 🔴 classées par priorité

#### P0 — Flux financiers temps réel (données sensibles)

| Page                         | Logique à extraire                     | Endpoint API cible                | Existe ? | Effort |
| ---------------------------- | -------------------------------------- | --------------------------------- | :------: | :----: |
| **company_analyzer.py**      | DCF, ratio analysis, yfinance fetch    | `POST /api/v1/analysis/company`   |    ❌    |   L    |
| **enterprise_valuations.py** | DCF Monte Carlo, Altman Z, Piotroski F | `POST /api/v1/analysis/valuation` |    ❌    |   L    |
| **instrument_detail.py**     | Universe lookup + yfinance detail      | `GET /api/v1/universe/{ticker}`   |    ❌    |   M    |

#### P1 — Flux ML / Risk / Backtest

| Page                               | Logique à extraire                    | Endpoint API cible                                 |  Existe ?  | Effort |
| ---------------------------------- | ------------------------------------- | -------------------------------------------------- | :--------: | :----: |
| **genesix_ml_engine.py**           | Ensemble prediction, regime detection | `POST /api/v1/ml/predict`, `POST /api/v1/ml/train` |     ✅     |   S    |
| **genesix_risk_engine.py**         | VaR/CVaR multi-method, stress tests   | `POST /api/v1/risk/compute`                        |     ✅     |   S    |
| **risk_engine_dashboard.py**       | Same as above (duplicate page)        | `POST /api/v1/risk/compute`                        |     ✅     |   S    |
| **genesix_intelligence.py**        | Signal generation, regime detection   | `POST /api/v1/ml/predict` (signals)                | ⚠️ partiel |   M    |
| **genesix_market_intelligence.py** | Anomaly detection, health scoring     | `GET /api/v1/monitoring/data-quality`              | ⚠️ partiel |   M    |
| **backtest_results.py**            | BacktestingEngine execution           | `POST /api/v1/backtest/run`                        |     ✅     |   S    |
| **genesix_advanced_analysis.py**   | Efficient frontier, optimization      | `POST /api/v1/portfolio/optimize`                  |     ❌     |   M    |
| **physics_demo.py**                | LPPL, seismograph, wavelets           | `POST /api/v1/analysis/physics`                    |     ❌     |   M    |

#### P2 — Flux avec accès data / universe

| Page                      | Logique à extraire          | Endpoint API cible             | Existe ? | Effort |
| ------------------------- | --------------------------- | ------------------------------ | :------: | :----: |
| **genesix_data_layer.py** | FeatureStore, data pipeline | `GET /api/v1/data/features`    |    ❌    |   M    |
| **universe_screener.py**  | Screen with criteria        | `POST /api/v1/universe/screen` |    ❌    |   M    |
| **universe_search.py**    | Full-text search            | `GET /api/v1/universe/search`  |    ❌    |   S    |

---

## 3. RÈGLES DE MIGRATION

### Règle M1 — Séparation stricte

> Une page Streamlit NE DOIT PAS importer depuis `src/genesix/` directement.

Tout accès aux modules métier doit passer par une route API FastAPI.  
Pattern :

```
Page Streamlit → requests.get/post("http://backend:8000/api/v1/...") → affichage
```

### Règle M2 — Pas de calcul lourd côté frontend

> Une page Streamlit NE DOIT PAS effectuer de calcul qui prend plus d'1 seconde.

Si le calcul dure >5s, il doit être dispatché via Celery (endpoint `POST .../async` → `GET /api/v1/jobs/{id}`).

### Règle M3 — API comme unique point d'accès

> Tout calcul métier passe par une route API.

Les pages ne font que :

1. Collecter les paramètres utilisateur (formulaire)
2. Appeler l'API backend
3. Afficher le résultat

### Règle M4 — Parité React / Streamlit

> Les pages React DOIVENT utiliser les mêmes endpoints API que les pages Streamlit.

Jamais de route "Streamlit-only" ou "React-only". Un seul backend, une seule API.

### Règle M5 — yfinance interdit en frontend

> `import yfinance` est INTERDIT dans les pages.

Tout accès data passe par les providers backend (`/api/v1/snapshot`, `/api/v1/refresh`, etc.).

### Règle M6 — Import genesix interdit en pages

> `from genesix.*` et `from src.genesix.*` sont INTERDITS dans `src/pages/`.

La couche d'accès aux modules genesix est le backend API.

---

## 4. PRIORISATION DES FLUX À MIGRER

### P0 — Données financières réelles (IMMÉDIAT)

| Flux                     | Pages concernées                        | Risque                                                        |
| ------------------------ | --------------------------------------- | ------------------------------------------------------------- |
| Company fundamental data | company_analyzer, enterprise_valuations | Données yfinance non-cachées, calculs DCF exposés côté client |
| Instrument detail        | instrument_detail                       | Appel yfinance direct sans provider pattern                   |

### P1 — ML / Risk / Backtest (COURT TERME)

| Flux               | Pages concernées                           | Endpoints existants                    |
| ------------------ | ------------------------------------------ | -------------------------------------- |
| ML prediction      | genesix_ml_engine                          | ✅ `/api/v1/ml/predict`, `/train`      |
| Risk compute       | genesix_risk_engine, risk_engine_dashboard | ✅ `/api/v1/risk/compute`              |
| Backtest run       | backtest_results                           | ✅ `/api/v1/backtest/run`              |
| Signal generation  | genesix_intelligence                       | ⚠️ Besoin d'un endpoint signals dédié  |
| Market health      | genesix_market_intelligence                | ⚠️ Monitoring partiel                  |
| Efficient frontier | genesix_advanced_analysis                  | ❌ Besoin `/api/v1/portfolio/optimize` |

### P2 — Accès data / Universe (MOYEN TERME)

| Flux               | Pages concernées   | Action                          |
| ------------------ | ------------------ | ------------------------------- |
| Feature store      | genesix_data_layer | Créer `/api/v1/data/features`   |
| Universe screening | universe_screener  | Créer `/api/v1/universe/screen` |
| Universe search    | universe_search    | Créer `/api/v1/universe/search` |

### P3 — Reste (PEUT ATTENDRE)

| Flux          | Pages concernées | Action                                        |
| ------------- | ---------------- | --------------------------------------------- |
| Physics lab   | physics_demo     | Créer `/api/v1/analysis/physics` (facultatif) |
| ESG scoring   | esg              | Module standalone, peu d'usage                |
| Documentation | documentation    | PDF generation, acceptable côté Streamlit     |
| Tax lab       | tax_lab          | Simulation locale, acceptable temporairement  |

---

## 5. ROUTES API MANQUANTES — PRIORITÉ CRITIQUE

Endpoints à créer en priorité pour débloquer les 14 pages 🔴 :

| #   | Route                        | Méthode | Request body                                     | Response                  |     Sync/Async      | Priorité | Statut  |
| --- | ---------------------------- | ------- | ------------------------------------------------ | ------------------------- | :-----------------: | :------: | :-----: |
| 1   | `/api/v1/universe/search`    | GET     | `?q=...&asset_class=...`                         | `UniverseSearchResponse`  |        Sync         |    P2    | ✅ FAIT |
| 2   | `/api/v1/universe/screen`    | POST    | `ScreenerRequest` (criteria list)                | `ScreenerResponse`        |        Sync         |    P2    | ✅ FAIT |
| 3   | `/api/v1/universe/{ticker}`  | GET     | —                                                | `InstrumentResponse`      |        Sync         |    P0    | ✅ FAIT |
| 4   | `/api/v1/portfolio/optimize` | POST    | `OptimizeRequest` (tickers, method, constraints) | `OptimizeResponse`        | Sync + Celery async |    P1    | ✅ FAIT |
| 5   | `/api/v1/analysis/company`   | POST    | `CompanyAnalysisRequest` (ticker, modules)       | `CompanyAnalysisResponse` | Sync + Celery async |    P0    | ✅ FAIT |

> **Phase 4 COMPLÉTÉE** — 5 routes créées (+ 3 variantes async) = **8 nouveaux endpoints**.
> Total routes : **57 → 60** (+ 3 endpoints dans main.py = 60 total).

### Fichiers créés (Phase 4)

| Fichier                            | Type   | Contenu                                                                                   |
| ---------------------------------- | ------ | ----------------------------------------------------------------------------------------- |
| `backend/app/schemas/universe.py`  | Schema | InstrumentResponse, ScreenerRequest, ScreenerResponse, UniverseSearchResponse             |
| `backend/app/schemas/portfolio.py` | Schema | OptimizeRequest, OptimizeResponse, AssetWeight, EfficientFrontierPoint                    |
| `backend/app/schemas/analysis.py`  | Schema | CompanyAnalysisRequest/Response, FundamentalsResult, DCFResult, RatiosResult, PeersResult |
| `backend/app/routes/universe.py`   | Route  | 3 endpoints — search, screen, detail                                                      |
| `backend/app/routes/portfolio.py`  | Route  | 2 endpoints — optimize sync + async                                                       |
| `backend/app/routes/analysis.py`   | Route  | 2 endpoints — company sync + async                                                        |

---

## 6. RÉSUMÉ EXÉCUTIF

- **54 pages** Streamlit auditées
- **32 (59%)** remplacées par React → ⚫ obsolètes
- **14 (26%)** « backend déguisé » → 🔴 migration nécessaire
- **7 (13%)** temporairement acceptables → 🟡 peuvent attendre
- **1 (2%)** propre → 🟢
- **60 routes API** total après Étape 13 (14 modules de routes)

Le principal problème structurel : **12 pages importent directement `genesix.*`** et **9+ utilisent `yfinance`**. Ces 14 pages font tourner du calcul lourd (VaR, ML, DCF, optimization) dans le processus Streamlit au lieu de le déléguer au backend API.

Parmi les 14 pages 🔴, **6 ont déjà un endpoint backend** (ML, Risk, Backtest) — seule l'intégration côté Streamlit manque. Les **5 routes manquantes** (universe, portfolio optimize, company analysis) ont été **implémentées dans la Phase 4** de cette étape.
