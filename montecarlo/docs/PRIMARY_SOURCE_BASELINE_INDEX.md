# Baseline Primaire - Index et Methode

> Date de creation : 2026-03-23
> Statut : baseline normative
> Portee : backend Ravinala / GenesiX (`backend/app/`, `src/db/`, `src/genesix/`, `src/analysis/`)

---

## Pourquoi ce corpus existe

Cette documentation n'est pas un rapport d'audit marketing, ni un compte-rendu "tout va bien", ni une synthese IA improvisee.

Son but est de fournir un socle de reference :

1. base sur des sources primaires ou quasi-primaires verifiables ;
2. relie aux besoins reels d'une plateforme backend finance / quant ;
3. exploitable par un humain ou un agent pour transformer des standards en taches d'ingenierie concretes ;
4. separe clairement :
   - ce qui vient des standards externes ;
   - ce qui vient des regles internes du repo ;
   - ce qui est observe dans le code ;
   - ce qui reste a prouver par tests.

Cette baseline ne dit pas "le projet est conforme".
Elle dit : "voici le niveau cible, les sources qui le fondent, et comment mesurer les ecarts".

---

## Regle de lecture obligatoire

Quand un agent travaille sur le backend, il doit distinguer 4 choses :

1. **Source externe** : norme, guide officiel, documentation officielle, papier de reference.
2. **Traduction projet** : exigence concrete adaptee a Ravinala.
3. **Preuve de code** : fichier, schema, test, migration, route, worker, modele.
4. **Preuve d'execution** : test, audit, import, comportement observable.

Interdiction de melanger ces niveaux.

Exemples de formulations correctes :

- "OWASP API Security Top 10 2023 exige une attention particuliere sur l'autorisation objet ; dans Ravinala cela se traduit par un controle explicite sur les endpoints `users`, `portfolio`, `risk`, `backtest`."
- "Le code actuel semble aller dans ce sens, mais la conformite n'est pas acquise tant qu'un test d'acces interdit n'existe pas."

Exemples de formulations interdites :

- "La securite est complete."
- "Le backend est production-ready."
- "Le moteur quant est robuste."

Sans preuves de code et de validation, ces phrases n'ont aucune valeur.

---

## Hierarchie des sources autorisees

### Niveau A - Source primaire

- normes et standards officiels ;
- publications de regulateur ;
- documentation officielle d'un framework ;
- publication academique originale.

### Niveau B - Source quasi-primaire

- cheat sheets officielles d'un organisme reconnu ;
- documentation maintenue par les auteurs d'une bibliotheque ;
- note technique officielle adossee a une norme.

### Niveau C - Source interne

- `AUDIT_RULES.md`
- `AGENT_INSTRUCTIONS.md`
- code du repo ;
- tests du repo ;
- docs historiques du repo.

### Niveau D - Source interdite comme base unique

- texte genere par IA sans citation ;
- billet de blog non officiel ;
- "audit" non source ;
- comparaison marketing ;
- opinion sans trace technique.

---

## Comment utiliser cette baseline

### Etape 1 - Construire la matrice d'exigences

Pour chaque domaine, produire une table :

| Champ | Contenu |
|---|---|
| domaine | ex: auth, API contracts, model risk |
| source | URL + titre |
| exigence | exigence traduite en langage projet |
| preuve attendue | code, schema, migration, test, trace |
| criticite | P0 / P1 / P2 |
| statut actuel | prouve / partiel / absent / contradictoire |

### Etape 2 - Verifier le code reel

Un agent ne doit jamais conclure sur la base d'une doc historique seule.
Il doit verifier dans le code :

- routes ;
- schemas ;
- services ;
- providers ;
- db models ;
- workers ;
- tests ;
- configuration ;
- persistence ;
- observabilite.

### Etape 3 - Transformer l'ecart en tache

Une tache d'amelioration n'est valide que si elle comporte :

- le risque evite ;
- les fichiers cibles ;
- le comportement cible ;
- les criteres d'acceptation ;
- les validations a executer.

---

## Cartographie Ravinala concernee

Cette baseline cible en priorite :

- `backend/app/main.py`
- `backend/app/routes/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/providers/`
- `backend/app/db/`
- `backend/app/auth/`
- `backend/app/risk/`
- `backend/app/ml/`
- `backend/app/workers/`
- `backend/app/observability/`
- `backend/app/middleware/`
- `src/db/`
- `src/genesix/`
- `src/analysis/`

---

## Registre des sources retenues

Les sources ci-dessous ont ete consultees le 2026-03-23 puis enrichies le 2026-03-24.

| ID | Domaine | Source | Type | Pourquoi elle est retenue |
|---|---|---|---|---|
| SRC-01 | AppSec | OWASP Application Security Verification Standard (ASVS) - <https://owasp.org/www-project-application-security-verification-standard/> | standard officiel | Base de verification applicative pour auth, session, config, journalisation |
| SRC-02 | API security | OWASP API Security Top 10 2023 - <https://owasp.org/API-Security/editions/2023/en/0x11-t10/> | standard officiel | Risques API concrets : BOLA, authz, misconfiguration, unsafe consumption |
| SRC-03 | Logging | OWASP Logging Cheat Sheet - <https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html> | cheat sheet officielle | Cadre utile pour quoi logger, quoi ne pas logger, correlation et securite des logs |
| SRC-04 | REST/API | OWASP REST Security Cheat Sheet - <https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html> | cheat sheet officielle | Contrats d'erreur, verbes, authn/authz, TLS, validation, statelessness |
| SRC-05 | SDLC | NIST SP 800-218 Secure Software Development Framework - <https://csrc.nist.gov/pubs/sp/800/218/final> | standard officiel | Socle de pratiques secure-by-design pour backlog, code, verification, release |
| SRC-06 | API framework | FastAPI Response Model - <https://fastapi.tiangolo.com/tutorial/response-model/> | doc officielle framework | Contrats de sortie, filtrage de reponse, validation et documentation OpenAPI |
| SRC-07 | API framework | FastAPI Handling Errors - <https://fastapi.tiangolo.com/tutorial/handling-errors/> | doc officielle framework | Gestion d'erreurs HTTP coherente et explicite |
| SRC-08 | Validation | Pydantic Models - <https://docs.pydantic.dev/latest/concepts/models/> | doc officielle framework | Types, modeles, serialization, validation |
| SRC-09 | Validation | Pydantic Strict Mode - <https://docs.pydantic.dev/latest/concepts/strict_mode/> | doc officielle framework | Limite les coercitions silencieuses sur des donnees sensibles |
| SRC-10 | ORM async | SQLAlchemy AsyncIO - <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html> | doc officielle framework | Regles de session async, transactions, engine, patterns per-task |
| SRC-11 | Background jobs | Celery User Guide - Tasks - <https://docs.celeryq.dev/en/stable/userguide/tasks.html> | doc officielle framework | Retries, acks, idempotence, time limits, comportements des taches |
| SRC-12 | Background jobs | Celery Calling Guide - Retry Policy - <https://docs.celeryq.dev/en/stable/userguide/calling.html#retry-policy> | doc officielle framework | Strategie de retry et options d'appel |
| SRC-13 | Trace propagation | W3C Trace Context - <https://www.w3.org/TR/trace-context/> | recommandation officielle | Correlation inter-services et propagation standardisee des traces |
| SRC-14 | Observabilite | OpenTelemetry Signals - <https://opentelemetry.io/docs/concepts/signals/> | doc officielle | Traces, metrics, logs, separation des signaux et instrumentations |
| SRC-15 | Model risk | Federal Reserve SR 11-7 - <https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm> | guidance officielle regulateur | Gouvernance du risque modele, inventaire, validation, "effective challenge" |
| SRC-16 | Market risk | BIS Minimum capital requirements for market risk (d457) - <https://www.bis.org/bcbs/publ/d457.htm> | standard officiel regulateur | Reference robuste sur backtesting, stress, governance market risk |
| SRC-17 | Quant validation | Bailey et al., The Probability of Backtest Overfitting - <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253> | publication academique originale | Justifie une discipline forte sur l'overfitting des backtests |
| SRC-18 | Quant validation | Arian, Norouzi, Seco, Backtest Overfitting in the Machine Learning Era - <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4778909> | publication academique originale | Met a jour le risque d'overfitting dans un contexte ML moderne |
| SRC-19 | Portfolio theory | Markowitz, *Portfolio Selection* - <https://www.jstor.org/stable/2975974> | publication academique originale | Base minimale de la construction moyenne-variance |
| SRC-20 | Portfolio theory | He & Litterman, *The Intuition Behind Black-Litterman Model Portfolios* - <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=334304> | publication academique / auteurs du modele | Rend les vues et leur combinaison avec l'equilibre plus explicites |
| SRC-21 | Portfolio theory | Idzorek, *A Step-By-Step Guide to the Black-Litterman Model Incorporating User-specified Confidence Levels* - <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3479867> | publication quasi-primaire | Utile pour traduire une confiance utilisateur en parametres exploitables |
| SRC-22 | Portfolio theory | Meucci, *Beyond Black-Litterman: Views on Non-Normal Markets* - <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=848407> | publication academique originale | Rappelle les limites des hypotheses normales dans l'allocation |
| SRC-23 | Allocation practice | AQR, *Understanding Risk Parity* - <https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/Understanding-Risk-Parity.pdf> | white paper officiel | Reference pratique sur budget de risque et diversification structurelle |
| SRC-24 | Portfolio construction | CFA Institute, *Active Equity Investing: Portfolio Construction* - <https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/active-equity-investing-portfolio-construction> | corpus professionnel de reference | Cadre utile pour risk budgeting, contraintes et portefeuille bien construit |
| SRC-25 | Platform benchmark | BlackRock Aladdin - <https://www.blackrock.com/aladdin> | doc officielle plateforme | Reference publique sur cycle investissement complet et whole portfolio language |
| SRC-26 | Platform benchmark | BlackRock Aladdin Wealth - <https://www.blackrock.com/aladdin/products/aladdin-wealth> | doc officielle plateforme | Reference publique sur scaled portfolio management et personalised wealth workflows |
| SRC-27 | Platform benchmark | BlackRock Aladdin Wealth x Investment Navigator - <https://www.blackrock.com/aladdin/discover/aladdin-wealth-integrates-investment-navigator-capabilities> | press release officielle | Rend visibles suitability, restrictions et tax/product checks dans la proposition |
| SRC-28 | Platform benchmark | Bloomberg AIM - <https://professional.bloomberg.com/products/trading/order-management-system/aim/> | doc officielle plateforme | Reference buy-side sur gestion de portefeuille, trading, compliance et operations |
| SRC-29 | Platform benchmark | Bloomberg MARS - <https://professional.bloomberg.com/products/risk/mars/> | doc officielle plateforme | Reference multi-actifs sur risque, stress, pre/post-trade analytics |
| SRC-30 | Platform benchmark | Bloomberg Asset Management / PORT - <https://professional.bloomberg.com/solutions/asset-management/> | doc officielle plateforme | Montre l'importance d'une couche integree analytics + risk + benchmark + workflow |
| SRC-31 | Platform benchmark | MSCI BarraOne / PortfolioManager / Direct Indexing - <https://www.msci.com/data-and-analytics/portfolio-management/barra-one>, <https://www.msci.com/data-and-analytics/portfolio-management/barra-portfolio-manager>, <https://www.msci.com/our-solutions/indexes/direct-indexing> | docs officielles plateforme | Reference sur factor risk, optimisation, what-if, personnalisation et direct indexing |
| SRC-32 | Platform benchmark | SimCorp Axioma Optimizer / Risk / Factor Models - <https://www.simcorp.com/solutions/strategic-solutions/axioma-solutions/axioma-portfolio-optimizer>, <https://www.simcorp.com/solutions/strategic-solutions/Axioma-Solutions/axioma-risk>, <https://www.simcorp.com/solutions/strategic-solutions/axioma-solutions/axioma-factor-risk-models> | docs officielles plateforme | Reference sur optimizer avance, contraintes riches et vues multiples du risque |
| SRC-33 | Platform benchmark | Amundi Technology ALTO - <https://int.media.amundi.com/news/amundi-creates-amundi-technology-a-new-business-line-dedicated-to-technology-products-and-services-371a-b6afb.html> | annonce officielle | Reference europeenne sur front-to-back asset/wealth/distribution |
| SRC-34 | Platform benchmark | Addepar wealth / trading / APIs - <https://addepar.com/wealth-management>, <https://addepar.com/advisorpeak-trading-rebalancing>, <https://developers.addepar.com/docs/about-addepar> | docs officielles plateforme | Reference sur whole-portfolio aggregation, rebalancing et architecture API ouverte |
| SRC-35 | Platform benchmark | Morningstar Direct / Direct Indexing - <https://www.morningstar.com/en-us/products/direct>, <https://newsroom.morningstar.com/news/news-details/2022/Morningstar-Launches-Direct-Indexing-Combining-Market-Leading-Technology-and-Investment-Management/default.aspx> | docs officielles plateforme | Reference sur recherche, analytics, personnalisation et tax efficiency |

---

## Comment ces sources se traduisent pour Ravinala

Le corpus est ensuite decline dans les documents cibles suivants :

- [PRIMARY_SOURCE_BACKEND_ENGINEERING_BASELINE.md](/c:/Users/Matthias/Project/montecarlo/docs/PRIMARY_SOURCE_BACKEND_ENGINEERING_BASELINE.md)
- [PRIMARY_SOURCE_SECURITY_AND_OPERATIONS_BASELINE.md](/c:/Users/Matthias/Project/montecarlo/docs/PRIMARY_SOURCE_SECURITY_AND_OPERATIONS_BASELINE.md)
- [PRIMARY_SOURCE_QUANT_AND_MODEL_RISK_BASELINE.md](/c:/Users/Matthias/Project/montecarlo/docs/PRIMARY_SOURCE_QUANT_AND_MODEL_RISK_BASELINE.md)
- [PRIMARY_SOURCE_PORTFOLIO_CONSTRUCTION_BASELINE.md](/c:/Users/Matthias/Project/montecarlo/docs/PRIMARY_SOURCE_PORTFOLIO_CONSTRUCTION_BASELINE.md)
- [PRIMARY_SOURCE_PORTFOLIO_PLATFORM_BENCHMARKS.md](/c:/Users/Matthias/Project/montecarlo/docs/PRIMARY_SOURCE_PORTFOLIO_PLATFORM_BENCHMARKS.md)
- [PORTFOLIO_CONSTRUCTION_TARGET_ARCHITECTURE.md](/c:/Users/Matthias/Project/montecarlo/docs/PORTFOLIO_CONSTRUCTION_TARGET_ARCHITECTURE.md)
- [PRIMARY_SOURCE_DELTA_LEDGER.md](/c:/Users/Matthias/Project/montecarlo/docs/PRIMARY_SOURCE_DELTA_LEDGER.md)
- [PRIMARY_SOURCE_ACTIVE_REQUIREMENTS.md](/c:/Users/Matthias/Project/montecarlo/docs/PRIMARY_SOURCE_ACTIVE_REQUIREMENTS.md)

Chaque document contient :

- les exigences cibles ;
- les preuves attendues ;
- les zones du repo concernees ;
- les criteres d'acceptation.

Le fonctionnement recommande est le suivant :

- la baseline longue porte les exigences de reference ;
- le delta ledger porte les ajouts/corrections depuis cette baseline ;
- l'active requirements file porte la shortlist de ce qui reste reellement ouvert.

Ce decoupage sert a limiter les tokens consommes par les agents tout en preservant la trace historique.

---

## Regles de mise a jour

Quand cette baseline est mise a jour :

1. garder l'URL exacte de la source ;
2. indiquer la date de consultation ;
3. eviter de transformer une source en interpretation trop large ;
4. si une exigence est seulement interne au projet, la marquer comme telle ;
5. ne jamais remplacer une source officielle par un resume IA.

---

## Regles de redaction pour les futurs agents

Un agent qui s'appuie sur cette baseline doit :

- citer la source externe qui fonde l'exigence ;
- citer les fichiers du repo qui prouvent ou infirment l'exigence ;
- separer "target state" et "current state" ;
- separer "code exists" et "validated in tests" ;
- signaler explicitement tout point non verifiable.
- lire en priorite `PRIMARY_SOURCE_DELTA_LEDGER.md` puis `PRIMARY_SOURCE_ACTIVE_REQUIREMENTS.md` avant les docs historiques.

Un agent n'a pas le droit :

- de conclure a la conformite sans verification code + validation ;
- d'inventer des pratiques "best-in-class" sans reference ;
- de traiter une doc historique `COMPLET` comme preuve suffisante.

---

## Resume

Cette baseline doit devenir la base documentaire serieuse du projet pour :

- auditer proprement ;
- prioriser proprement ;
- ecrire des prompts d'agents plus intelligents ;
- et, surtout, faire evoluer le backend sur des exigences reellement defendables.
