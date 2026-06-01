# Portfolio Construction - Target Architecture

> Date de creation : 2026-03-24
> Statut : target state
> Depend de : `PRIMARY_SOURCE_PORTFOLIO_CONSTRUCTION_BASELINE.md`, `PRIMARY_SOURCE_QUANT_AND_MODEL_RISK_BASELINE.md`

---

## Objet

Definir l'architecture cible du futur moteur GenesiX de recommendation d'allocation.

Le but n'est pas de remplacer brutalement ce qui existe.
Le but est de **composer** les briques existantes dans une chaine propre et versionnable.

---

## Contrat produit cible

Input utilisateur minimal :

- `amount`
- `base_currency`
- `risk_aversion`
- `max_drawdown_tolerance`
- `investment_horizon`
- `liquidity_needs`
- `objective_type`
- `income_need`
- `allowed_asset_classes`
- `exclusions`
- `tax_profile` si supporte
- `benchmark_preference` si applicable

Output cible :

- `recommended_portfolio`
- `target_weights`
- `target_amounts`
- `selected_assets`
- `rejected_assets`
- `expected_return_assumptions`
- `risk_summary`
- `scenario_summary`
- `benchmark_comparison`
- `rebalancing_delta`
- `warnings`
- `run_id`

---

## Pipeline cible

### 1. Investor Policy Layer

Responsabilite :

- valider les inputs investisseur ;
- normaliser le mandat ;
- produire une politique investisseur exploitable en aval.

Module cible :

- `backend/app/services/investor_policy_service.py`
- `backend/app/schemas/investor_policy.py`

Sortie attendue :

- `InvestorPolicy`

### 2. Universe Eligibility Layer

Responsabilite :

- partir d'un univers large ;
- filtrer eligibilite, liquidite, cout, data quality ;
- produire un univers investissable canonique.

Peut reutiliser :

- `backend/app/services/universe_service.py`
- `backend/app/routes/universe.py`

Extension cible :

- `backend/app/services/investable_universe_service.py`

Sortie attendue :

- `EligibleUniverse`

### 3. Assumptions / Views Layer

Responsabilite :

- produire des hypotheses de rendement, risque et confiance ;
- combiner baseline + signaux + vues optionnelles.

Sources possibles :

- rendement historique shrinke ;
- carry ;
- momentum ;
- valuation ;
- macro ;
- signaux ML ;
- vues CIO / utilisateur.

Module cible :

- `backend/app/services/capital_market_assumptions_service.py`

Sortie attendue :

- `CapitalMarketAssumptions`

### 4. Risk Model Layer

Responsabilite :

- produire covariance / correlation / drawdown proxies / stress payload ;
- documenter conventions et qualite des donnees.

Peut reutiliser :

- `backend/app/services/risk_service.py`
- `src/genesix/risk/`

Sortie attendue :

- `PortfolioRiskInputs`

### 5. Allocation Engine Layer

Responsabilite :

- resoudre l'allocation sous contraintes ;
- comparer plusieurs objectifs ;
- renvoyer des solutions candidates.

Peut reutiliser :

- `backend/app/services/portfolio_optimization_service.py`
- `src/genesix/optimizer/optimizer.py`

Mais doit evoluer vers :

- solveur multi-objectifs plus riche ;
- contraintes explicites ;
- alternatives candidates ;
- cout de contraintes ;
- support benchmark-aware / tax-aware plus tard.

Sortie attendue :

- `AllocationCandidates`

### 6. Recommendation Layer

Responsabilite :

- transformer les solutions candidates en recommendation lisible ;
- expliquer pourquoi chaque actif est retenu ;
- afficher limites et alternatives.

Module cible :

- `backend/app/services/allocation_recommendation_service.py`

Sortie attendue :

- `AllocationRecommendation`

### 7. Persistence Layer

Responsabilite :

- persister le run complet ;
- rendre la recommendation auditabile ;
- supporter comparaisons ulterieures.

Module cible :

- `backend/app/db/models_allocation.py`
- `backend/app/repositories/allocation_run_repository.py`

Sortie attendue :

- `AllocationRunRecord`

### 8. API / Async Delivery Layer

Responsabilite :

- exposer le moteur au front React et aux futurs clients ;
- supporter sync pour petits cas, async pour gros univers.

Routes cibles :

- `POST /api/v1/allocator/recommend`
- `POST /api/v1/allocator/recommend/async`
- `GET /api/v1/allocator/runs/{run_id}`
- `GET /api/v1/allocator/runs/{run_id}/explain`

---

## Cartographie current state -> target state

| Brique | Existant | Gap principal |
|---|---|---|
| profile investisseur | partiel / epars | pas de schema investisseur canonique |
| universe | present | eligibility et data quality encore trop legeres |
| assumptions | tres eparses | pas de couche CMA unique |
| risk | present | pas encore raccorde comme input canonique d'un moteur unique |
| optimizer | present | trop centre sur solveur et pas sur decision pipeline |
| recommendation | absent comme couche dediee | pas de moteur d'explication/rejet/alternatives |
| persistence run allocation | absente | pas de trail complet de recommendation |
| API allocation complete | absente | `/portfolio/optimize` ne couvre pas le besoin final |

---

## Ordre de build recommande

1. `InvestorPolicy`
2. `EligibleUniverse`
3. `CapitalMarketAssumptions`
4. `PortfolioRiskInputs`
5. `AllocationCandidates`
6. `AllocationRecommendation`
7. `AllocationRunRecord`
8. routes sync/async dediees

---

## Regle d'implementation

Tant que GenesiX ne dispose pas de cette chaine complete, toute page ou doc qui parle
de "AI portfolio allocator complet" doit etre lue comme **aspiration produit**,
pas comme preuve de capacite actuellement industrialisee.

