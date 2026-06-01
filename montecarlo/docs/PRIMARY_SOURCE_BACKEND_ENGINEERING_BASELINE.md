# Baseline Primaire - Backend Engineering

> Date de creation : 2026-03-23
> Scope principal : `backend/app/main.py`, `backend/app/routes/`, `backend/app/schemas/`, `backend/app/services/`, `backend/app/providers/`, `backend/app/db/`, `backend/app/workers/`
> Sources racines : SRC-05 a SRC-14

---

## Objet

Ce document traduit les standards officiels backend en exigences concretes pour Ravinala.

Il ne dit pas que le projet est deja conforme.
Il definit :

- le niveau cible ;
- les preuves attendues ;
- les criteres d'acceptation ;
- les zones de code a verifier.

---

## Principe directeur

Pour Ravinala, le backend cible doit respecter cette chaine :

`Route -> Service -> Repository/DB`

et, pour les donnees externes :

`Route -> Service -> Provider -> API externe`

Les routes orchestrent.
Les schemas contractent.
Les services decident.
Les repositories et providers isolent l'acces aux dependances.

---

## B1 - Contrats API et schemas de sortie

### Sources

- FastAPI Response Model
- FastAPI Handling Errors
- Pydantic Models
- Pydantic Strict Mode

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue | Zone repo |
|---|---|---|---|---|
| B1.1 | Tout endpoint JSON public expose un `response_model` explicite | Evite les contrats implicites et stabilise OpenAPI | `response_model=` dans chaque route JSON | `backend/app/routes/` |
| B1.2 | Les modeles de reponse utilisent Pydantic v2 comme contrat canonique | Limite les retours arbitraires et la derive de schema | schemas dans `backend/app/schemas/` | `backend/app/schemas/` |
| B1.3 | Les donnees sensibles ou internes ne doivent pas sortir par accident | FastAPI filtre les champs selon le model de sortie | tests de serialization et modeles separes lecture/ecriture | `routes/`, `schemas/` |
| B1.4 | Les erreurs applicatives suivent une structure stable | Le client ne doit pas parser des messages heterogenes | handler global + schema d'erreur | `main.py`, `schemas/envelope.py` |
| B1.5 | Les entrees sensibles ne reposent pas sur la coercition permissive seule | En finance, une coercition silencieuse peut corrompre un calcul ou un droit | usage cible de validation stricte sur champs critiques | `schemas/`, `routes/` |

### Criteres d'acceptation

- aucun endpoint JSON critique sans `response_model` ;
- distinction claire entre models d'entree et de sortie ;
- erreurs 4xx et 5xx homogenes ;
- champs comme identifiants, montants, dates, horizons, enums et flags critiques traites de maniere explicite ;
- tests de non-regression sur les schemas les plus exposes.

---

## B2 - Validation d'entree et discipline de schema

### Sources

- Pydantic Models
- Pydantic Strict Mode
- OWASP REST Security Cheat Sheet

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue | Zone repo |
|---|---|---|---|---|
| B2.1 | Les contraintes de domaine doivent etre encodees dans les schemas, pas laissees au hasard du service | Rend les erreurs plus precoces et plus explicites | `Field`, validateurs, enums, constrained types | `backend/app/schemas/` |
| B2.2 | Les identifiants, quantites, dates et horizons doivent etre valides au plus pres de l'entree | Evite des erreurs tardives en risk/ml/backtest | schemas metier et tests invalides | `schemas/risk.py`, `schemas/ml.py`, `schemas/backtest.py` |
| B2.3 | Les valeurs par defaut doivent etre semantiquement defendables | Un default faible cree du comportement cache | documentation + tests des defaults | `schemas/`, `core/config.py` |
| B2.4 | Les payloads partiels ou ambigus doivent etre rejetes explicitement | Evite des comportements "best effort" dangereux | 422 ou 400 attendus sur cas invalides | `routes/`, tests API |

### Criteres d'acceptation

- tout schema critique a ses invariants explicites ;
- aucun `dict` free-form pour des payloads metier critiques ;
- tests d'entree invalide couverts sur auth, ml, risk, backtest, jobs.

---

## B3 - Gestion des erreurs, timeouts et contrats d'echec

### Sources

- FastAPI Handling Errors
- OWASP REST Security Cheat Sheet
- NIST SSDF

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue | Zone repo |
|---|---|---|---|---|
| B3.1 | Chaque classe d'echec significative produit une reponse explicite et non ambigue | Rend le systeme exploitable par frontend, workers et monitoring | handlers, status codes, schemas d'erreur | `main.py`, `routes/` |
| B3.2 | Les erreurs d'infrastructure sont distinguees des erreurs fonctionnelles | Permet la bonne remediaton | mapping d'exceptions et logs | `services/`, `main.py` |
| B3.3 | Les timeouts metier ou externes ne doivent jamais se traduire en succes partiel implicite | Evite les faux positifs | exceptions, retries ou statuts explicites | `services/`, `workers/` |
| B3.4 | Les fallback doivent annoncer leur qualite de donnees | En finance, "stale", "demo" et "live" n'ont pas la meme signification | data quality explicite dans reponse/logs | `schemas/envelope.py`, `services/` |

### Criteres d'acceptation

- pas d'exception brute qui fuit vers le client ;
- status codes coherents ;
- erreurs observables et testables ;
- les degradations de qualite de donnees sont explicites.

---

## B4 - Persistence et discipline transactionnelle

### Sources

- SQLAlchemy AsyncIO
- NIST SSDF
- regles internes `AUDIT_RULES.md`

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue | Zone repo |
|---|---|---|---|---|
| B4.1 | Tout resultat critique doit survivre a un restart | Condition de reproductibilite et d'auditabilite | modeles DB, repositories, migrations, tests | `backend/app/db/`, `src/db/` |
| B4.2 | Les modeles miroir sync/async doivent etre synchronises ou explicitement justifies | Evite la derive entre monde backend et monde src | champs alignes, commentaire miroir, tests ou diff documente | `backend/app/db/models.py`, `src/db/models.py` |
| B4.3 | Les transactions doivent etre bornees et explicites | Evite les effets partiels silencieux | usage net des sessions/commits/rollbacks | `db/`, `services/`, `routes/` |
| B4.4 | Les objets de persistence ne doivent pas etre manipules directement partout dans les routes | Limite le couplage et les bugs d'orchestration | repositories ou services d'acces cible | `routes/`, `services/` |

### Criteres d'acceptation

- plus aucun resultat critique purement in-memory ;
- schema DB et objets metier coherents ;
- echec transactionnel gere proprement ;
- tests de persistence sur artefacts ML, snapshots risk, runs de backtest, jobs si applicables.

---

## B5 - Async, SQLAlchemy et usage par tache

### Sources

- SQLAlchemy AsyncIO

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue | Zone repo |
|---|---|---|---|---|
| B5.1 | Une session async ne doit pas etre partagee de maniere unsafe entre taches concurrentes | Evite corruptions et fuites d'etat | pattern sessionmaker, injection claire | `backend/app/db/`, `services/` |
| B5.2 | Les appels DB et I/O doivent etre compatibles avec le mode async reel du backend | Evite blocages et pseudo-async | fonctions async coherentes, pas de sync cachee sur chemin critique | `routes/`, `services/`, `db/` |
| B5.3 | Le demarrage et l'arret de l'application doivent initialiser/fermer proprement les ressources | Evite etats zombies | lifespan propre, fermeture DB, clients externes | `backend/app/main.py` |

### Criteres d'acceptation

- pas de pattern dangereux de session globale mutable ;
- pas de confusion entre client sync et async dans le chemin principal ;
- ressources fermees proprement au shutdown.

---

## B6 - Taches de fond, workers et Celery

### Sources

- Celery User Guide - Tasks
- Celery Calling Guide - Retry Policy
- NIST SSDF

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue | Zone repo |
|---|---|---|---|---|
| B6.1 | Toute tache longue ou fragile declare ses retries, time limits et politique d'echec | Rend les workers previsibles | decorateurs/config Celery | `backend/app/workers/tasks/` |
| B6.2 | Une tache doit etre idempotente ou explicitement marquee non-idempotente | Evite doublons et corruption sur retry | commentaire, design de persistence, test | `workers/tasks/`, `services/` |
| B6.3 | Le client doit pouvoir suivre l'etat d'un job de maniere observable | Necessaire pour UX et support ops | job id, route de statut, persistence eventuelle | `routes/jobs.py`, `workers/` |
| B6.4 | Les erreurs de taches doivent etre journalisees sans exposer de secret | Condition d'operabilite | logs structures, exceptions ciblees | `workers/`, `observability/` |

### Criteres d'acceptation

- pas de tache importante sans limites d'execution ;
- retry explicite ou justification d'absence ;
- statut job consultable ;
- traces et logs suffisants pour debug.

---

## B7 - Fournisseurs de donnees et acces externe

### Sources

- NIST SSDF
- OWASP API Security Top 10 2023
- regles internes `AUDIT_RULES.md`

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue | Zone repo |
|---|---|---|---|---|
| B7.1 | Aucun appel externe critique ne doit etre disperse dans les routes | Evite couplage fort, tests difficiles et erreurs de securite | providers dedies | `backend/app/providers/`, `services/` |
| B7.2 | La qualite de la source, sa fraicheur et son fallback doivent etre explicites | Le backend finance ne doit pas masquer l'origine et la fraicheur des donnees | metadata source/quality/staleness | `services/`, `schemas/` |
| B7.3 | Les appels vers API tierces doivent gerer timeout, retry borne et erreurs connues | Evite cascade failures | wrappers provider + tests | `providers/`, `services/` |
| B7.4 | La consommation d'API tierces doit etre consideree comme surface de risque | OWASP 2023 insiste sur "Unsafe Consumption of APIs" | validation reponse, schemas, sanitation | `providers/`, `services/` |

### Criteres d'acceptation

- routes sans appels externes directs ;
- services et providers clairement separes ;
- staleness et source quality exposes ;
- validation des reponses tierces avant usage.

---

## B8 - Configuration, secrets et modes d'execution

### Sources

- NIST SSDF
- OWASP ASVS
- OWASP REST Security Cheat Sheet

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue | Zone repo |
|---|---|---|---|---|
| B8.1 | Les secrets ne vivent ni dans le code ni dans les defaults de demonstration dangereux | Reduit le risque de compromission | config par env, absence de secrets commites | `core/config.py`, `auth/`, `.env` handling |
| B8.2 | Les modes local/demo/test/production doivent modifier explicitement le niveau de securite | Evite les environnements permissifs oublies | flags clairs, docs, tests comportementaux | `core/config.py`, `auth/rbac.py` |
| B8.3 | Les defaults de config critiques doivent etre defensifs | Un default permissif est un risque systemique | revue des defaults et tests | `core/config.py`, `auth/` |

### Criteres d'acceptation

- aucun fallback de secret dangereux non documente ;
- niveaux de securite et comportements associes testables ;
- pas de "mode local" pouvant etre confondu avec un mode deploiable.

---

## B9 - Observabilite, correlation et sante systeme

### Sources

- W3C Trace Context
- OpenTelemetry Signals
- OWASP Logging Cheat Sheet

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue | Zone repo |
|---|---|---|---|---|
| B9.1 | Chaque requete importante doit etre correlable via un identifiant stable | Rend possible le suivi bout en bout | request id, trace id, propagation | `middleware/`, `observability/`, `main.py` |
| B9.2 | Les traces, metrics et logs doivent etre penses comme signaux distincts mais relies | OpenTelemetry separe les signaux | instrumentation ou au moins conventions claires | `observability/`, `middleware/` |
| B9.3 | Les logs ne doivent pas exposer secrets, tokens ou payloads sensibles | Exigence de securite et conformite | politique de logging + revue des logs | `observability/`, `routes/`, `workers/` |
| B9.4 | Les endpoints de sante doivent distinguer l'etat du process et l'etat des dependances | "up" ne suffit pas si DB/Redis/worker sont morts | health checks structures | `main.py`, `routes/monitoring.py` |

### Criteres d'acceptation

- correlation id visible cote API et logs ;
- health checks utiles, pas cosmetiques ;
- logs secrets-safe ;
- base exploitable pour traces/metrics futures.

---

## Definition of Done backend

Une evolution backend n'est pas terminee tant que :

1. le contrat API est explicite ;
2. l'erreur est testable ;
3. la persistence ou l'absence de persistence est justifiee ;
4. la configuration critique est defensive ;
5. le comportement async/worker est borne ;
6. la trace et le log sont suffisants pour debugger ;
7. la logique externe passe bien par provider/service ;
8. la validation ne repose pas uniquement sur une lecture du code.

---

## Checklist de verification pour un agent

- l'exigence est-elle fondee sur une source primaire ?
- le fichier cible est-il identifie ?
- la preuve de code existe-t-elle ?
- la preuve de test existe-t-elle ?
- l'amelioration elimine-t-elle un risque reel ?
- la modification renforce-t-elle le contrat, la persistence, la securite ou l'operabilite ?

Si la reponse est "non" sur plusieurs points, ce n'est pas encore un enrichissement serieux.
