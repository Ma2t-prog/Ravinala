# Protocole d'Execution - Agent Principal et Sous-Agents

> Date de creation : 2026-03-23
> Usage : protocole operationnel a utiliser avec `PRIMARY_SOURCE_AGENT_MASTER_PROMPT.md` et `PRIMARY_SOURCE_SUBAGENT_PROMPT_PACK.md`

---

## Objet

Ce document definit comment l'equipe d'agents doit travailler, livrer, se synchroniser et prouver ses conclusions.

Le but est d'eviter :

- les conclusions vagues ;
- les livraisons cosmetiques ;
- les doublons de travail ;
- les conflits de perimetre ;
- les claims non prouves.

---

## Regle 1 - Aucune mission sans matrice de preuve

Avant de coder, l'agent principal doit construire pour chaque mission une mini-matrice :

| Champ | Contenu attendu |
|---|---|
| domaine | ex: auth, api, db, risk, ml |
| source(s) | references du corpus |
| exigence cible | ce que la baseline exige |
| preuve trouvee | code actuel observe |
| gap | absent / partiel / contradictoire |
| risque | P0 / P1 / P2 |
| mission | travail a deleguer ou a traiter |

Sans cette matrice, aucune delegation ne doit partir.

---

## Regle 2 - Ownership de fichiers obligatoire

Chaque sous-agent doit recevoir un scope de fichiers clairement borne.

Exemples corrects :

- `backend/app/auth/` + `backend/app/routes/auth.py`
- `backend/app/schemas/` + `backend/app/routes/*.py`
- `backend/app/workers/` + `backend/app/observability/`

Exemples incorrects :

- "prends tout le backend"
- "ameliore la securite globale"
- "regarde si tu peux clean un peu"

---

## Regle 3 - Format de mission obligatoire

Chaque mission doit etre redigee ainsi :

```text
Domaine :
Sources :
Perimetre exclusif :
Problemes cibles :
Interdits :
Definition of Done :
Validations attendues :
Format de sortie :
```

---

## Regle 4 - Interdits absolus

Aucun agent ne peut conclure "done" si :

- le comportement n'est pas teste ou relu ;
- la persistance attendue n'existe pas ;
- l'ecart a la baseline n'est pas explicite ;
- un fallback dangereux reste en place ;
- les limites residuelles ne sont pas documentees ;
- le changement est seulement stylistique.

---

## Regle 5 - Format de sortie de chaque sous-agent

Chaque sous-agent doit rendre une sortie finale contenant exactement :

1. **Problemes constates**
2. **Sources appliquees**
3. **Fichiers modifies**
4. **Changements apportes**
5. **Validations executees**
6. **Risques restants**
7. **Points hors perimetre remontes**

Si un sous-agent n'a pas modifie de code, il doit expliquer pourquoi et ce qui bloquait legitimement.

---

## Regle 6 - Format de synthese de l'agent principal

L'agent principal doit finir avec une synthese qui separe :

### A - Ce qui est prouve

- changements integres ;
- validations executees ;
- risques reduits ;
- standards mieux couverts.

### B - Ce qui n'est pas encore prouve

- validations non executees ;
- hypotheses encore fragiles ;
- zones non couvertes ;
- dependances non traitees.

### C - Ce qui doit venir ensuite

- prochaine vague P0 ;
- prochaine vague P1 ;
- refactors a ne faire qu'apres stabilisation.

---

## Regle 7 - Definition d'un enrichissement reel

Un enrichissement est reel seulement si au moins une des conditions suivantes est vraie :

- un risque de securite est supprime ;
- un contrat API est rendu strict et testable ;
- un resultat critique devient persistant ;
- un mode permissif devient borne et explicite ;
- une hypothese quant devient visible et defendable ;
- un worker devient traçable et borne ;
- une divergence structurelle entre deux parties du systeme est supprimee ;
- un faux sentiment de robustesse est remplace par une verite explicite.

Si aucune de ces conditions n'est remplie, la mission est reputee cosmetique.

---

## Regle 8 - Quand escalader vers l'humain

L'agent principal doit stopper et demander arbitrage si :

- deux standards se contredisent dans le contexte produit ;
- une correction impose un choix produit non evident ;
- un changement casse l'ergonomie ou la promesse du projet ;
- une dette historique rend impossible une correction propre sans refonte plus large ;
- un secret, des donnees sensibles ou une incoherence critique sont decouverts.

---

## Regle 9 - Artefacts attendus a la fin d'une vague

Selon le domaine traite, une vague serieuse doit laisser :

- code modifie ;
- tests ou validations ajoutes ;
- eventuelle migration ;
- eventuelle doc courte ;
- etat des risques residuels ;
- backlog de suite.

Les modifications invisibles, non prouvees ou non reliees a un risque ne comptent pas.

---

## Mini-checklist finale

Avant de clore une vague d'agents, verifier :

- les missions etaient-elles sourcees ?
- les scopes etaient-ils exclusifs ?
- les preuves de code sont-elles reelles ?
- les validations sont-elles reelles ?
- les gains sont-ils mesurables ?
- les risques restants sont-ils dits clairement ?

Si une de ces reponses manque, la vague n'est pas encore suffisamment serieuse.
