# Baseline Primaire - Securite et Operations

> Date de creation : 2026-03-23
> Scope principal : `backend/app/auth/`, `backend/app/routes/auth.py`, `backend/app/routes/users.py`, `backend/app/core/`, `backend/app/middleware/`, `backend/app/observability/`, `backend/app/routes/monitoring.py`, `backend/app/workers/`
> Sources racines : SRC-01 a SRC-05, SRC-13, SRC-14

---

## Objet

Ce document fixe le niveau cible de securite et d'operabilite du backend.

Il s'appuie sur :

- OWASP ASVS ;
- OWASP API Security Top 10 2023 ;
- OWASP REST Security Cheat Sheet ;
- OWASP Logging Cheat Sheet ;
- NIST SSDF ;
- W3C Trace Context ;
- OpenTelemetry.

---

## S1 - Authentification

### Sources

- OWASP ASVS
- OWASP REST Security Cheat Sheet
- NIST SSDF

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| S1.1 | Aucune authentification ne doit dependre d'un secret par defaut dangereux en environnement deployable | Un fallback permissif annule tout le reste | config defensive, tests d'absence de secret |
| S1.2 | Le backend doit distinguer sans ambiguite les modes local, demo, test, controle et production | Evite les derives de configuration | niveau de securite documente et teste |
| S1.3 | La creation, la verification et la rotation des tokens doivent etre explicites | Rend l'auth mesurable et auditable | handlers, expiration, docs, tests |
| S1.4 | Les erreurs d'auth ne doivent pas reveler d'information sensible | Evite enumeration et leakage | reponses homogenes, logs separes |

### Critere d'acceptation

Une plateforme ne peut pas etre dite "serieuse" si son chemin nominal d'auth depend encore d'un secret de demonstration ou d'un mode permissif mal borne.

---

## S2 - Autorisation et controle d'acces

### Sources

- OWASP API Security Top 10 2023
- OWASP ASVS

### Risques a couvrir

OWASP API 2023 met en avant notamment :

- Broken Object Level Authorization ;
- Broken Authentication ;
- Broken Object Property Level Authorization ;
- Unrestricted Access to Sensitive Business Flows ;
- Broken Function Level Authorization ;
- Security Misconfiguration ;
- Unsafe Consumption of APIs.

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| S2.1 | Tout endpoint portant sur un objet sensible doit verifier l'autorisation au niveau objet, pas seulement au niveau role global | Evite la BOLA/BOPLA | tests de refus sur acces a l'objet d'autrui |
| S2.2 | Les endpoints admin, user management, jobs, portfolio, risk, ml et backtest doivent avoir une politique de role explicite | Evite les trous d'autorisation | dependencies RBAC, tests 403 |
| S2.3 | Les routes `monitoring` ou `security/status` doivent etre pensees comme surface sensible | Beaucoup de fuites passent par les endpoints d'observabilite | policy d'acces, tests |
| S2.4 | Les fonctionnalites de demonstration ne doivent pas donner un acces silencieux au niveau admin | Un mode demo mal borne devient un bypass | tests en environnement non-local |

### Critere d'acceptation

La presence d'un RBAC dans le code ne suffit pas.
La baseline exige des tests qui prouvent qu'un acteur non autorise ne peut pas lire, modifier ou declencher ce qu'il ne doit pas.

---

## S3 - Secrets, configuration et hardening

### Sources

- OWASP ASVS
- NIST SSDF
- OWASP REST Security Cheat Sheet

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| S3.1 | Aucun secret durable ne doit etre committe ou derive d'un placeholder de demonstration | Hygiene minimale | scan, `.gitignore`, config, examples separes |
| S3.2 | Les variables critiques doivent etre clairement marquees "required in controlled environments" | Evite la confusion entre dev local et execution serieuse | docs + validation startup si mode >= controle |
| S3.3 | Les options de hardening doivent etre centralisees et non dispersees | Permet revue et audit | `core/config.py` ou equivalent |
| S3.4 | Les defaults de securite doivent etre defensifs | Le default fait souvent la securite reelle | revue des defaults et tests |

---

## S4 - Journalisation et audit trail

### Sources

- OWASP Logging Cheat Sheet
- OWASP ASVS
- NIST SSDF

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| S4.1 | Les evenements sensibles doivent etre journalises avec contexte suffisant | Auth, role change, delete, export, calcul critique doivent etre auditables | audit trail structure |
| S4.2 | Les logs ne doivent jamais contenir secrets, tokens bruts, mots de passe, payloads trop sensibles | La log peut devenir la fuite | politique de redaction + revue code |
| S4.3 | Les logs doivent distinguer succes, echec, refus, erreur technique | Support incident et forensic | structure de log explicite |
| S4.4 | L'audit trail doit etre persistant et interrogeable | Un audit purement console ne vaut rien | persistence + route de consultation si justifiee |

### Criteres d'acceptation

- actions critiques tracees ;
- informations sensibles masquees ;
- correlation possible avec request id / trace id ;
- retention et acces clarifies.

---

## S5 - Tracing, correlation et evidence operatoire

### Sources

- W3C Trace Context
- OpenTelemetry Signals
- OWASP Logging Cheat Sheet

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| S5.1 | Les requetes et jobs doivent etre correlables entre API, workers et logs | Rend le debug multi-composant possible | propagation request/trace id |
| S5.2 | Les logs, traces et metrics doivent etre concus comme signaux complets, pas comme un seul fichier log | L'operabilite moderne n'est pas monolithique | conventions d'instrumentation |
| S5.3 | Les traces ne doivent pas devenir un vecteur de fuite de donnees | Le tracing doit rester safe | sanitation des attributs |

---

## S6 - Health, readiness, failure modes

### Sources

- NIST SSDF
- OpenTelemetry
- OWASP REST Security Cheat Sheet

### Exigences cibles

| ID | Exigence | Pourquoi | Preuve attendue |
|---|---|---|---|
| S6.1 | Le backend doit distinguer sante du process, disponibilite des dependances, et degradation partielle | "process up" ne veut pas dire "service fiable" | endpoints et statuts structures |
| S6.2 | Redis, DB, providers critiques et workers doivent avoir un etat observable | Aide exploitation et incidents | health checks, metrics, logs |
| S6.3 | Les modes fallback doivent etre visibles | Un fallback silencieux peut tromper l'utilisateur ou l'equipe | flags de qualite, logs, headers |

---

## S7 - Secure SDLC applique a Ravinala

### Source

- NIST SP 800-218

### Traduction projet

Pour Ravinala, le SSDF ne doit pas rester theorique. Il implique au minimum :

1. des exigences de securite explicites par domaine ;
2. une verification du code et des dependencies sensibles ;
3. une validation avant merge ou avant livraison locale significative ;
4. une distinction nette entre demo/research et environnements controles ;
5. une trace des changements de securite et de leur justification.

---

## Ce qu'un agent doit prouver avant de conclure "securise"

Un agent n'a pas le droit de conclure que la securite est bonne si :

- il n'a pas verifie les modes de securite reels ;
- il n'a pas teste au moins quelques refus d'acces ;
- il n'a pas verifie la persistence de l'audit trail ;
- il n'a pas controle les defaults critiques ;
- il n'a pas verifie que les logs ne fuient pas d'elements sensibles.

---

## Definition of Done securite/ops

Une amelioration securite/ops est terminee seulement si :

1. elle supprime un comportement permissif reel ;
2. elle ajoute une preuve testable de controle ;
3. elle n'introduit pas de faux sentiment de securite ;
4. elle rend le comportement observable en incident ;
5. elle documente clairement la difference entre local/demo et execution serieuse.
