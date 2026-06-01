# Pack de Prompts - Sous-Agents Backend

> Date de creation : 2026-03-23
> Usage : missions specialisees pour une equipe de sous-agents pilotee par l'agent principal
> Base documentaire : le corpus `PRIMARY_SOURCE_*` + `AUDIT_RULES.md` + `AGENT_INSTRUCTIONS.md`

---

## Regle commune a tous les sous-agents

Chaque sous-agent recoit :

- un domaine ;
- un perimetre exclusif ;
- un mandat fonde sur des sources reelles ;
- des criteres d'acceptation ;
- une forme de livrable stricte.

Chaque sous-agent doit :

1. lire `AUDIT_RULES.md` ;
2. lire `AGENT_INSTRUCTIONS.md` ;
3. lire les baselines `PRIMARY_SOURCE_*` pertinentes ;
4. auditer le code reel de son perimetre ;
5. n'implementer que des changements justifies ;
6. fournir preuves, validations et risques residuels.

---

## Template universel

```text
Mission : traiter le domaine `<DOMAINE>` du backend Ravinala.

Sources obligatoires :
- `<SOURCES>`

Perimetre exclusif :
- `<FICHIERS_OU_DOSSIERS>`

Probleme a traiter :
- `<PROBLEMES_REELS>`

Tu n'es pas autorise a faire un nettoyage cosmetique.
Tu dois produire un enrichissement reel et defendable.

Tu dois :
1. verifier l'etat actuel du code ;
2. lister les ecarts reels ;
3. implementer les corrections a plus forte valeur ;
4. ajouter la validation necessaire ;
5. rendre compte avec preuves.

Interdits :
- sortir de ton perimetre
- renommer/refactorer sans gain mesurable
- conclure "done" sans test ou verification
- inventer des exigences absentes du corpus

Definition of Done :
- le risque cible est reduit ou supprime
- le comportement cible est visible dans le code
- la validation a ete executee
- les limites restantes sont explicites

Sortie finale obligatoire :
1. constats
2. fichiers modifies
3. changements apportes
4. validations executees
5. risques restants
```

---

## Sous-agent 1 - Auth, RBAC, secrets, modes de securite

```text
Mission : renforcer l'authentification, l'autorisation, la gestion des secrets et les modes de securite.

Sources obligatoires :
- docs/PRIMARY_SOURCE_SECURITY_AND_OPERATIONS_BASELINE.md
- docs/PRIMARY_SOURCE_BASELINE_INDEX.md
- OWASP ASVS
- OWASP API Security Top 10 2023
- NIST SP 800-218

Perimetre exclusif :
- backend/app/auth/
- backend/app/routes/auth.py
- backend/app/routes/users.py
- backend/app/core/

Problemes a traiter :
- modes permissifs trop larges
- defaults de securite non defensifs
- RBAC insuffisamment testable
- secrets ou placeholders dangereux
- confusion entre local/demo/controle/production

Definition of Done :
- auth et RBAC explicites
- aucun bypass implicite injustifie
- comportement des modes de securite documente et testable
- secrets critiques non derives de defaults faibles
```

---

## Sous-agent 2 - Contrats API, schemas, erreurs

```text
Mission : rendre les contrats API stricts, lisibles, types et robustes.

Sources obligatoires :
- docs/PRIMARY_SOURCE_BACKEND_ENGINEERING_BASELINE.md
- FastAPI Response Model
- FastAPI Handling Errors
- Pydantic Models
- Pydantic Strict Mode

Perimetre exclusif :
- backend/app/routes/
- backend/app/schemas/
- backend/app/main.py

Problemes a traiter :
- endpoints sans contrat clair
- erreurs heterogenes
- schemas trop permissifs
- retours incoherents avec OpenAPI
- validation d'entree insuffisamment stricte

Definition of Done :
- chaque endpoint critique a un contrat defensable
- erreurs homogenes et testables
- schemas d'entree/sortie explicites
- pas de fuite de champs internes par serialization
```

---

## Sous-agent 3 - Persistence, DB, coherence des modeles

```text
Mission : fiabiliser la persistence et supprimer les divergences structurelles de modeles.

Sources obligatoires :
- docs/PRIMARY_SOURCE_BACKEND_ENGINEERING_BASELINE.md
- docs/PRIMARY_SOURCE_QUANT_AND_MODEL_RISK_BASELINE.md
- SQLAlchemy AsyncIO
- regles internes sur persistance et modeles miroir

Perimetre exclusif :
- backend/app/db/
- src/db/
- backend/app/repositories/ si cree

Problemes a traiter :
- resultats critiques seulement in-memory
- divergence entre modeles backend et src
- transactions peu bornees
- manque de couche repository si necessaire pour clarifier l'acces DB

Definition of Done :
- les resultats critiques survivent au restart
- les modeles miroir sont alignes ou explicitement justifies
- les chemins transactionnels critiques sont lisibles et testables
```

---

## Sous-agent 4 - Providers, services, qualite des donnees

```text
Mission : clarifier l'acces aux donnees externes, la qualite de donnees et les fallbacks.

Sources obligatoires :
- docs/PRIMARY_SOURCE_BACKEND_ENGINEERING_BASELINE.md
- OWASP API Security Top 10 2023
- NIST SP 800-218

Perimetre exclusif :
- backend/app/providers/
- backend/app/services/
- backend/app/routes/market.py
- backend/app/routes/analysis.py
- backend/app/routes/portfolio.py

Problemes a traiter :
- appels externes trop disperses
- fallbacks non explicites
- staleness ou data quality mal exposes
- validation insuffisante des reponses tierces

Definition of Done :
- pattern Route -> Service -> Provider respecte
- source, fraicheur et qualite des donnees observables
- consommation d'API tierces bornees et defendables
```

---

## Sous-agent 5 - ML governance et artefacts

```text
Mission : renforcer la gouvernance ML, la reproductibilite et la discipline de validation.

Sources obligatoires :
- docs/PRIMARY_SOURCE_QUANT_AND_MODEL_RISK_BASELINE.md
- Federal Reserve SR 11-7
- publications sur backtest overfitting
- regles internes de honesty flags et de non-randomness

Perimetre exclusif :
- backend/app/ml/
- src/genesix/ml/

Problemes a traiter :
- sorties trompeuses ou insuffisamment governées
- manque d'artefacts persistants
- validation trop faible ou mal tracee
- ecart entre recherche et usage controle

Definition of Done :
- metadata et artefacts defendables
- limites explicites
- baselines et validations mieux encadrees
- aucun comportement simulé vendu comme prediction fiable
```

---

## Sous-agent 6 - Risk engine et backtesting

```text
Mission : rendre le risk engine et le backtesting plus defendables et plus lisibles.

Sources obligatoires :
- docs/PRIMARY_SOURCE_QUANT_AND_MODEL_RISK_BASELINE.md
- BIS d457
- Federal Reserve SR 11-7
- AUDIT_RULES.md

Perimetre exclusif :
- backend/app/risk/
- backend/app/backtest/
- src/analysis/
- src/genesix/risk/

Problemes a traiter :
- hypotheses implicites
- conventions dispersees
- limites non exploitables
- backtests insuffisamment encadres
- runs/snapshots insuffisamment persistants

Definition of Done :
- conventions centrales et explicites
- hypotheses d'execution lisibles
- limites et governance plus exploitables
- preuves de non-lookahead ou d'absence de preuve clairement annoncees
```

---

## Sous-agent 7 - Workers, jobs, observabilite

```text
Mission : fiabiliser les jobs asynchrones, leur suivi et leur observabilite.

Sources obligatoires :
- docs/PRIMARY_SOURCE_BACKEND_ENGINEERING_BASELINE.md
- docs/PRIMARY_SOURCE_SECURITY_AND_OPERATIONS_BASELINE.md
- Celery Tasks
- Celery Retry Policy
- W3C Trace Context
- OpenTelemetry Signals

Perimetre exclusif :
- backend/app/workers/
- backend/app/routes/jobs.py
- backend/app/routes/monitoring.py
- backend/app/observability/
- backend/app/middleware/

Problemes a traiter :
- jobs peu tracables
- retries/time limits manquants
- logs et traces insuffisants
- health checks peu actionnables

Definition of Done :
- jobs observables et bornees
- erreurs corrélables
- health et monitoring utiles pour le run
- base exploitable pour l'orchestration future
```

---

## Regle de coordination

Le chef d'orchestration doit attribuer chaque mission avec ownership clair.
Un sous-agent n'a pas le droit d'etendre son scope "par confort".

S'il detecte un probleme hors perimetre :

1. il le note ;
2. il n'intervient pas dessus ;
3. il le remonte comme dependance ou risque.
