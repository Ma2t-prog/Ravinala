# Baseline Primaire - Portfolio Construction et Recommendation Engine

> Date de creation : 2026-03-24
> Scope principal : `backend/app/routes/portfolio.py`, `backend/app/services/portfolio_optimization_service.py`, `backend/app/services/universe_service.py`, `src/genesix/optimizer/`, `src/genesix/risk/`, `src/genesix/ml/`, `src/genesix/intelligence/`
> Sources racines : SRC-15 a SRC-35

---

## Objet

Ce document fixe le niveau cible de GenesiX non pas comme simple "optimizer",
mais comme **moteur de construction de portefeuille** capable de :

- recevoir un profil investisseur et des contraintes explicites ;
- definir un univers investissable defendable ;
- estimer rendement, risque, correlations, couts et limites ;
- arbitrer entre plusieurs allocations candidates ;
- recommander des actifs nominatifs avec poids, montants, raisons et limites ;
- laisser une trace persistante et auditable de chaque recommandation.

Le produit cible n'est donc pas :

- un pie chart ;
- un Sharpe optimizer isole ;
- un classement de tickers sans contraintes ;
- un modele ML qui "sort des poids".

Le produit cible est un **decision engine**.

---

## Definition du resultat cible

Pour un utilisateur donne, GenesiX doit pouvoir produire un objet final de ce type :

- profil investisseur versionne ;
- universe eligibile versionne ;
- hypotheses de marche explicites ;
- methode de risque explicite ;
- optimisation effectuee sous contraintes ;
- portefeuille recommande ;
- actifs rejetes et raisons de rejet ;
- alternatives comparees ;
- limites et avertissements ;
- run ID persistant.

Si une partie manque, GenesiX peut rester un bon outil quant.
Il n'est pas encore un moteur d'allocation de niveau institutionnel / wealth-tech solide.

---

## Sources de reference retenues

| ID | Source | Type | Pourquoi elle compte pour GenesiX |
|---|---|---|---|
| SRC-19 | Markowitz, *Portfolio Selection* - <https://www.jstor.org/stable/2975974> | publication academique originale | base minimale de la construction moyenne-variance et du trade-off rendement/risque |
| SRC-20 | He & Litterman, *The Intuition Behind Black-Litterman Model Portfolios* - <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=334304> | publication academique / auteurs du modele | cadre cle pour combiner prior, vues et portefeuilles plus stables |
| SRC-21 | Idzorek, *A Step-By-Step Guide to the Black-Litterman Model Incorporating User-specified Confidence Levels* - <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3479867> | publication quasi-primaire | utile pour rendre la confiance utilisateur exploitable au lieu de rester implicite |
| SRC-22 | Meucci, *Beyond Black-Litterman: Views on Non-Normal Markets* - <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=848407> | publication academique originale | rappelle que les hypotheses normales sont souvent trop faibles pour un moteur multi-actifs |
| SRC-23 | AQR, *Understanding Risk Parity* - <https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/Understanding-Risk-Parity.pdf> | white paper officiel | reference pratique pour allocations basees sur budget de risque et non seulement sur poids notionnels |
| SRC-24 | CFA Institute, *Active Equity Investing: Portfolio Construction* - <https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/active-equity-investing-portfolio-construction> | corpus professionnel de reference | couvre risk budgeting, contraintes, concentration, benchmark awareness et construction reelle |
| SRC-25 | BlackRock Aladdin - <https://www.blackrock.com/aladdin> | doc officielle plateforme | reference publique sur whole portfolio language, integration et cycle investissement complet |
| SRC-26 | BlackRock Aladdin Wealth - <https://www.blackrock.com/aladdin/products/aladdin-wealth> | doc officielle plateforme | reference sur wealth-scale portfolio management, rebalancing, restrictions et next best action |
| SRC-27 | BlackRock Aladdin Wealth x Investment Navigator - <https://www.blackrock.com/aladdin/discover/aladdin-wealth-integrates-investment-navigator-capabilities> | press release officielle | rend explicite la place de suitability, fiscal suitability et restrictions dans la proposition d'investissement |
| SRC-28 | Bloomberg AIM - <https://professional.bloomberg.com/products/trading/order-management-system/aim/> | doc officielle plateforme | reference buy-side sur portfolio management, trading, compliance, operations et audit trail |
| SRC-29 | Bloomberg MARS - <https://professional.bloomberg.com/products/risk/mars/> | doc officielle plateforme | reference sur vues multi-actifs coherentes pour risque, stress et pre/post-trade analytics |
| SRC-30 | Bloomberg Portfolio Analytics / PORT - <https://professional.bloomberg.com/solutions/asset-management/> | doc officielle plateforme | montre l'importance d'une couche integrant analytics, attribution, benchmark et workflow |
| SRC-31 | MSCI BarraOne / PortfolioManager / Direct Indexing - <https://www.msci.com/data-and-analytics/portfolio-management/barra-one>, <https://www.msci.com/data-and-analytics/portfolio-management/barra-portfolio-manager>, <https://www.msci.com/our-solutions/indexes/direct-indexing> | docs officielles plateforme | reference sur factor risk, what-if, optimization, direct indexing et personnalisation taxable |
| SRC-32 | SimCorp Axioma Portfolio Optimizer / Risk / Factor Models - <https://www.simcorp.com/solutions/strategic-solutions/axioma-solutions/axioma-portfolio-optimizer>, <https://www.simcorp.com/solutions/strategic-solutions/Axioma-Solutions/axioma-risk>, <https://www.simcorp.com/solutions/strategic-solutions/axioma-solutions/axioma-factor-risk-models> | docs officielles plateforme | reference sur optimiser avance, vaste bibliotheque de contraintes, multiperspective risk et batch scale |
| SRC-33 | Amundi Technology ALTO - <https://int.media.amundi.com/news/amundi-creates-amundi-technology-a-new-business-line-dedicated-to-technology-products-and-services-371a-b6afb.html> | annonce officielle | reference europeenne sur plateforme asset / wealth couvrant DPM, advisory et distribution |
| SRC-34 | Addepar Wealth Management / Trading / APIs - <https://addepar.com/wealth-management>, <https://addepar.com/advisorpeak-trading-rebalancing>, <https://developers.addepar.com/docs/about-addepar> | docs officielles plateforme | reference sur whole-portfolio aggregation, rebalancing a l'echelle et architecture API ouverte |
| SRC-35 | Morningstar Direct / Direct Indexing - <https://www.morningstar.com/en-us/products/direct>, <https://newsroom.morningstar.com/news/news-details/2022/Morningstar-Launches-Direct-Indexing-Combining-Market-Leading-Technology-and-Investment-Management/default.aspx> | docs officielles plateforme | reference sur recherche, analytics, personnalisation et tax efficiency pour wealth |

---

## Traduction produit pour GenesiX

Les sources ci-dessus convergent vers 8 blocs cibles.

### PC1 - Investor policy et suitability

GenesiX doit traiter l'utilisateur comme un **mandat d'investissement** et non comme un simple slider de risque.

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| PC1.1 | Le profil investisseur doit inclure au minimum montant, horizon, devise, tolerance a la perte, objectif principal, besoin de liquidite et contraintes d'exclusion | Une aversion au risque seule est insuffisante pour construire un portefeuille defendable | schema profile + validation API |
| PC1.2 | Les contraintes investisseur doivent etre explicites : concentration, classes d'actifs autorisees, geographies, durabilite, fiscalite si applicable | Les contraintes changent la solution optimale | modele de donnees + persistence |
| PC1.3 | Le moteur doit distinguer objectif absolu, objectif benchmark relatif et objectif liability-aware | Le bon risque n'est pas le meme selon le mandat | champs d'objectif + logique aval |
| PC1.4 | Toute recommandation doit etre rattachee a une version de profil investisseur | Evite les recommandations orphelines ou non auditables | run ID + profile ID |

### PC2 - Investable universe

Un allocateur serieux commence par definir ce qui **peut** entrer, pas par optimiser tout ce qui existe.

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| PC2.1 | L'univers doit etre construit a partir de regles d'eligibilite explicites | Sans eligibility layer, l'optimizer compare des actifs incomparables | service universe eligibility |
| PC2.2 | Chaque actif doit porter nom, ticker, asset_class, devise, region, liquidite proxy, cout proxy et qualite de donnees | Le portefeuille final doit etre executable et explicable | canonical asset record |
| PC2.3 | Les actifs sans donnees suffisantes, trop illiquides ou trop couteux doivent pouvoir etre exclus avant optimisation | Nettoie le probleme en amont | filtres documentes + tests |
| PC2.4 | Le moteur doit savoir former des sleeves : cash, core beta, satellite, thematic, hedge, alternatives si supportees | Le portefeuille n'est pas qu'une liste plate de poids | schema sleeve / bucket |

### PC3 - Expected return engine

Les rendements attendus ne doivent pas etre confondus avec "le score ML".

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| PC3.1 | GenesiX doit disposer d'une baseline simple pour les rendements attendus avant tout enrichissement ML | Evite qu'un modele opaque devienne la seule source de conviction | baseline CMA documentee |
| PC3.2 | Les vues doivent pouvoir venir de plusieurs briques : carry, momentum, valuation, macro, signals, ML | L'allocation serieuse combine plusieurs couches de conviction | service de vues composees |
| PC3.3 | Chaque vue doit avoir un niveau de confiance ou un poids epistemique explicite | Necessaire pour un cadre Black-Litterman ou assimilable | champs confidence / reliability |
| PC3.4 | Les hypotheses de rendement doivent etre persistantes et versionnees par run | Sans trace, pas de revue ni de challenge | persistence des assumptions |

### PC4 - Risk model

Le risque ne peut pas etre reduit a la volatilite annualisee.

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| PC4.1 | Le moteur doit produire au minimum covariance/correlation, vol, concentration et drawdown proxies | minimum vital pour allouer | risk payload versionne |
| PC4.2 | Le moteur doit pouvoir distinguer risque total, risque benchmark relatif et budget de risque par sleeve | condition de realisme produit | risk budgets et constraints |
| PC4.3 | Les sources de risque doivent etre lisibles : facteur, devise, duration, credit, equity beta, etc. quand supporte | rapproche GenesiX d'une logique type Barra/MARS/Axioma | modeles de decomposition |
| PC4.4 | Les what-if, stress et scenarios doivent pouvoir challenger une allocation candidate avant recommandation | un portefeuille non teste est incomplet | scenario layer + reporting |

### PC5 - Optimization engine

L'optimizer doit devenir un solveur de decision sous contraintes, pas juste un Sharpe maximizer.

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| PC5.1 | Le moteur doit supporter plusieurs objectifs : max_sharpe, min_var, risk_budgeting, tracking_error_control, tax-aware ou equivalents si supportes | les plateformes de reference ne se limitent pas a mean-variance pur | API et service objectifs multiples |
| PC5.2 | La bibliotheque de contraintes doit couvrir poids min/max, concentration, cardinalite, classes d'actifs, sleeves, turnover, cash, liquidite et couts | sans contraintes reelles, l'optimum est souvent inutilisable | contraintes modelisees et testees |
| PC5.3 | L'optimizer doit etre capable de comparer plusieurs allocations candidates et non sortir une seule reponse brute | utile pour recommendation et challenge | frontier / candidates report |
| PC5.4 | Les contraintes actives et leur cout marginal doivent etre explicites autant que possible | pratique observee chez Axioma/BarraOne | reporting de contraintes |

### PC6 - Recommendation engine

La sortie produit doit etre un conseil structure, pas un vecteur de poids nu.

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| PC6.1 | La recommandation doit inclure noms, tickers, poids, montants et role de chaque actif | requirement utilisateur final direct | payload recommandation complet |
| PC6.2 | Le moteur doit expliquer pourquoi chaque actif est retenu ou rejete | la confiance utilisateur depend de l'explicabilite | reasons / exclusions |
| PC6.3 | La recommendation doit afficher ses limites : donnees manquantes, hypothese de rendements, mode demo, etc. | pas de faux sentiment de precision | warnings / maturity flags |
| PC6.4 | Le moteur doit pouvoir produire des alternatives proches : plus defensif, plus liquide, plus taxe-efficient, plus benchmark-like | utile en advisory reel | compare_solutions output |

### PC7 - Validation et challenge

Un allocateur n'est pas "bon" parce qu'il optimise.

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| PC7.1 | Chaque recommendation methodologique doit etre comparee a des baselines simples | condition minimale de serieux | benchmark equal weight / 60-40 / naive |
| PC7.2 | Les tests doivent separer optimisation in-sample et evaluation out-of-sample | evite les illusions de robustesse | walk-forward / holdout |
| PC7.3 | Les resultats doivent etre challengeables par scenarios adverses | requirement de gouvernance risque | stress reports |
| PC7.4 | Les couches demo / research / production-controlled doivent etre etiquetees | evite les promesses infondees | maturity flag |

### PC8 - Delivery produit et backend

Sans orchestration backend propre, tout le reste restera fragile.

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| PC8.1 | Il faut une API dediee de recommendation d'allocation, distincte du simple `/portfolio/optimize` | le besoin produit depasse l'optimisation seule | route/service dedie(s) |
| PC8.2 | Chaque run doit persister inputs, univers, assumptions, risques, allocation et explications | auditabilite et revision | DB + models + repository |
| PC8.3 | Le systeme doit pouvoir tourner sync pour petits cas et async pour gros univers | pattern deja etabli backend | route sync/async |
| PC8.4 | Le resultat doit etre exploitable par React, par reporting et par monitoring | rapproche le backend d'un produit complet | schemas stables et typed |

---

## Gap principal du repo actuel

En lisant le code actuel, l'etat de verite est le suivant :

- il existe deja une brique `optimizer` ;
- il existe deja des services `portfolio` et `universe` cote backend ;
- il existe deja du `risk`, du `ML`, du `signal`, du `backtest` ;
- mais il n'existe pas encore de **decision pipeline unique** allant de `investor profile -> eligible universe -> assumptions -> risk -> optimization -> recommendation -> persistence`.

Donc le plus gros chantier n'est pas "ameliorer `optimizer.py`".

Le plus gros chantier est :

**industrialiser une chaine complete de portfolio construction.**

---

## Definition of Done portfolio construction

Une amelioration n'est terminee que si :

1. elle rapproche GenesiX d'un moteur de recommendation complet ;
2. elle relie les inputs investisseur aux actifs recommandes ;
3. elle rend les contraintes explicites ;
4. elle rend les hypotheses de marche explicites ;
5. elle laisse une trace persistante ;
6. elle explique ses choix ;
7. elle annonce ses limites ;
8. elle est challengeable par benchmark, stress et test hors echantillon.

