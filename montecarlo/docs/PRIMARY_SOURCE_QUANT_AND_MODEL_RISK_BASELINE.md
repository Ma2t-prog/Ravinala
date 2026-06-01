# Baseline Primaire - Quant, Backtesting et Model Risk

> Date de creation : 2026-03-23
> Scope principal : `backend/app/ml/`, `backend/app/risk/`, `backend/app/backtest/`, `src/genesix/ml/`, `src/genesix/risk/`, `src/analysis/`
> Sources racines : SRC-15 a SRC-18, completees par `AUDIT_RULES.md`

---

## Objet

Ce document fixe le niveau cible pour les parties quantitatives du projet :

- moteur ML ;
- moteur risk ;
- backtesting ;
- gouvernance modele ;
- persistance des resultats ;
- validite des hypotheses.

La logique ici n'est pas "faire plus sophistique".
La logique est :

- rendre les resultats defendables ;
- rendre les limites explicites ;
- reduire les illusions de robustesse ;
- separer recherche, experimentation et execution serieuse.

---

## Q1 - Gouvernance du risque modele

### Source

- Federal Reserve SR 11-7

### Traduction pour Ravinala

SR 11-7 traite les modeles comme des objets qui doivent etre gouvernes, documentes, valides et challengees.
Pour Ravinala, cela implique qu'un modele ML, risk ou backtest ne doit jamais etre considere comme "bon" uniquement parce qu'il tourne ou affiche une courbe.

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| Q1.1 | Chaque modele important doit avoir un objectif explicite, un domaine de validite et des hypotheses documentees | Sans cela, impossible de juger le bon usage | spec, docstring, metadata |
| Q1.2 | Les jeux de donnees, features, cibles et transformations doivent etre tracables | Condition de reproductibilite et d'audit | metadata, artefacts, persistence |
| Q1.3 | La validation d'un modele doit etre distincte de son entrainement et de sa promotion | Evite l'auto-approbation implicite | separation des etapes, tests, rapports |
| Q1.4 | Les limites connues doivent etre explicites | Un modele sans limites documentees est dangereux | champs "limitations" ou docs associees |
| Q1.5 | Les versions de modele, metriques et artefacts doivent etre persistantes | Permet revue ulterieure et comparaisons | joblib, metadata JSON, MLflow ou equivalent |

---

## Q2 - Integrite temporelle et causalite

### Sources

- SR 11-7
- `AUDIT_RULES.md`
- Bailey et al. (PBO)

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| Q2.1 | Aucune feature ne doit incorporer d'information future a la date de prediction | Condition minimale de validite | revue pipeline + tests anti-lookahead |
| Q2.2 | Les jointures et remplissages doivent rester causalement defendables | `ffill` et interpolation peuvent etre legitimes ou trompeurs selon les cas | justification par type de serie + tests |
| Q2.3 | Les transformations de preprocessing doivent etre fit sur train puis appliquees hors train | Evite fuite de distribution | pipeline clair train/val/test |
| Q2.4 | Tout raccourci "best effort" sur donnees manquantes doit etre explicite et observable | En quant, un remplissage silencieux peut changer la conclusion | metadata de qualite, logs, tests |

### Critere d'acceptation

Un modele n'est pas "propre" parce que la colonne cible a ete retiree avant fit.
Il faut prouver l'absence de fuite sur la chaine complete :

- source ;
- feature build ;
- alignement temporel ;
- split ;
- preprocessing ;
- evaluation.

---

## Q3 - Validation hors echantillon et overfitting

### Sources

- Bailey et al., The Probability of Backtest Overfitting
- Arian, Norouzi, Seco, Backtest Overfitting in the Machine Learning Era
- SR 11-7

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| Q3.1 | Le simple split train/test unique n'est pas une preuve suffisante de robustesse | Les travaux sur PBO montrent la fragilite des procedures trop simples | walk-forward, plusieurs folds ou regimes |
| Q3.2 | Les resultats doivent etre observes sur plusieurs segments temporels | Un resultat bon en une periode peut etre artefactuel | rapports par periode/regime |
| Q3.3 | Les modeles doivent etre compares a des baselines naives ou plus simples | Une sophistication sans baseline est irrelevante | baseline metrics persistées |
| Q3.4 | Les decisions d'acceptation ne doivent pas dependre d'une seule metrique flatteuse | Directional accuracy seule peut etre trompeuse | plusieurs metriques + interpretation |
| Q3.5 | Les experimentations multiples doivent etre traitees comme risque d'overfitting, pas comme simple exploration innocente | Plus on cherche, plus on trouve des faux edges | historique d'experiences, discipline de comparaison |

---

## Q4 - Backtesting

### Sources

- BIS d457
- Bailey et al. (PBO)
- `AUDIT_RULES.md`

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| Q4.1 | Le backtest doit respecter la chronologie de decision et d'execution | Sinon le resultat n'a pas de sens operationnel | engine, tests, validate_no_lookahead |
| Q4.2 | Les hypotheses d'execution doivent etre explicites : prix utilise, delai, slippage, commissions, liquidite | Sans hypothese explicite, la perf n'est pas interpretable | params de backtest + doc |
| Q4.3 | Les resultats doivent etre compares au minimum a un benchmark simple et a une baseline naive | Necessaire pour juger la valeur ajoutee | metrics comparatives |
| Q4.4 | Les limites du backtest doivent etre affichees : survivorship bias, universe actuel, corporate actions, impact, donnees manquantes | Un beau rapport sans limites est trompeur | rapport de limitations |
| Q4.5 | Les runs de backtest doivent etre persistants et versionnes | Permet revue et audit | DB + metadata |

---

## Q5 - Moteur risk et conventions

### Sources

- BIS d457
- SR 11-7
- regles internes du projet

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| Q5.1 | Les conventions quant doivent avoir une source de verite unique | Evite incoherences sur taux, annualisation, horizons | constantes centralisees |
| Q5.2 | VaR/CVaR et mesures voisines doivent annoncer leur methode, horizon, confiance et limites | Condition de lecture correcte | schema + metadata |
| Q5.3 | Les snapshots risk doivent etre persistants | Un risk report ephemere est peu gouvernable | DB + historique |
| Q5.4 | Les limites et seuils doivent etre exploitables, pas seulement calcules | Calculer une VaR sans effet systeme est insuffisant | limite, alerte, gouvernance ou justification |
| Q5.5 | Les stress tests doivent etre distingues des mesures indicatives standard | Evite la confusion analytique | modele de donnees clair |

---

## Q6 - Separation recherche / demo / production

### Sources

- SR 11-7
- NIST SSDF
- BIS d457

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| Q6.1 | Un module exploratoire ne doit pas etre presente comme production-grade sans validation supplementaire | Evite le faux sentiment de fiabilite | niveau de gouvernance ou maturity flag |
| Q6.2 | Les donnees demo, statiques ou simulees doivent etre etiquetees comme telles | Le client ne doit pas croire a du live ou a du valide si ce n'est pas le cas | champs de data quality / governance |
| Q6.3 | Les modeles indisponibles ou invalides doivent echouer explicitement, pas "inventer" des sorties | Rigueur minimale | status `unavailable`, erreur claire |

---

## Q7 - Artefacts, reproductibilite et evidence

### Sources

- SR 11-7
- NIST SSDF
- publications sur overfitting

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| Q7.1 | Chaque entrainement important doit laisser une trace exploitable | Permet revision, comparaison et rollback | artefacts + metadata + timestamp |
| Q7.2 | Les seeds, versions de donnees, hyperparametres et metriques doivent etre conserves | Condition de reproductibilite | metadata persistée |
| Q7.3 | Les ecarts entre backend et `src/genesix` doivent etre explicites quand ils portent sur les modeles ou calculs | Evite doubles verites silencieuses | doc ou sync des implementations |

---

## Q8 - Ce qu'un agent doit prouver avant de conclure "solide"

Un agent n'a pas le droit de conclure qu'une brique quant est serieuse s'il n'a pas verifie :

1. l'integrite temporelle ;
2. la validite du split ou du walk-forward ;
3. la presence de baselines ;
4. la persistence des runs et artefacts ;
5. les hypotheses de cout et d'execution ;
6. les limites documentees ;
7. la distinction entre demo, recherche et usage controle.

---

## Definition of Done quant/model risk

Une amelioration quant/backtest/risk n'est terminee que si :

1. elle rend le resultat plus defendable, pas seulement plus complexe ;
2. elle reduit un risque de fuite, d'overfitting ou d'illusion de robustesse ;
3. elle rend les hypotheses explicites ;
4. elle laisse une evidence persistante ;
5. elle annonce ses limites ;
6. elle ameliore la capacite de challenge, pas seulement la sophistication numerique.
