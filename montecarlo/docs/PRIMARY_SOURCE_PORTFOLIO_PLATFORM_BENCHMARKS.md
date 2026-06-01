# Baseline Primaire - Benchmarks Plateformes Portfolio

> Date de creation : 2026-03-24
> Statut : benchmark documentaire
> Usage : comprendre ce que les plateformes institutionnelles ou wealth-tech rendent explicite publiquement, afin de traduire cela en exigences produits pour GenesiX

---

## Regle de lecture

Ce document n'est **pas** un comparatif marketing.

Il sert a repondre a une seule question :

**quelles capacites publiques les plateformes serieuses mettent-elles en avant, et qu'est-ce que cela implique pour le niveau cible de GenesiX ?**

On ne conclut pas :

- "GenesiX doit tout copier" ;
- "GenesiX doit battre Aladdin" ;
- "si une plateforme a une feature, il faut l'ajouter".

On conclut seulement :

- quelles capacites reviennent systematiquement ;
- quelles attentes produit elles rendent visibles ;
- quelles pieces manquent encore chez GenesiX.

---

## Lecture rapide

Les plateformes de reference convergent presque toutes sur 7 themes :

1. whole portfolio view ;
2. risk language unifie ;
3. rebalancing et model management a l'echelle ;
4. contraintes et suitability explicites ;
5. scenario / what-if / stress ;
6. personnalisation client ou mandate-aware ;
7. persistance, workflows et integration ecosysteme.

Si GenesiX ne couvre pas ces themes, il restera un bon moteur quant, mais pas un vrai allocateur / advisor engine.

---

## Matrice de benchmark

| Plateforme | Sources | Ce que la plateforme rend public | Traduction utile pour GenesiX | Ce qu'il ne faut pas sur-interpreter |
|---|---|---|---|---|
| Aladdin | SRC-25 | langage du whole portfolio, cycle complet investissement, ecosysteme integre, multi-asset | GenesiX doit penser `decision chain`, pas uniquement analytics isolee | BlackRock ne publie pas sa secret sauce interne complete |
| Aladdin Wealth | SRC-26,SRC-27 | model management, scaled portfolio management, restrictions client, next best action, suitability | GenesiX doit inclure contraintes client, rebalancing a l'echelle et couche recommendation/explainability | les communiques ne prouvent pas la qualite interne de chaque modele |
| Bloomberg AIM / PORT / MARS | SRC-28,SRC-29,SRC-30 | continuites front-office / risk / compliance / operations, pre/post-trade analytics, MARS risk | GenesiX doit relier allocation, risque, compliance logique et execution | PORT/MARS ne sont pas des specs ouvertes de leur moteur |
| MSCI BarraOne / PortfolioManager | SRC-31 | factor risk, attribution, what-if, optimization, direct indexing et tax-aware personalization | GenesiX doit exposer source du risque, scenarios et personnalisation scalable | les docs MSCI ne signifient pas qu'il faut absolument du facteur partout au premier sprint |
| SimCorp Axioma | SRC-32 | optimizer avance, vaste bibliotheque de contraintes, multiperspective risk, batch rebalancing | GenesiX doit traiter les contraintes comme objets de premier rang | l'ampleur fonctionnelle Axioma depasse largement un premier MVP |
| ALTO (Amundi Technology) | SRC-33 | couverture asset management + advisory/distribution, front-to-back, wealth/DPM | GenesiX doit penser a la chaine complete depuis la proposition jusqu'au suivi | annonce corporate, pas spec technique detaillee |
| Addepar | SRC-34 | aggregation holdings multi-entites, whole wealth view, APIs, rebalancing/trading, reporting | GenesiX doit pouvoir federer holdings internes/externe et produire un run advisory riche | Addepar est plus fort historiquement sur aggregation/reporting que sur alpha engine pur |
| Morningstar Direct / Direct Indexing | SRC-35 | recherche, analytics, personalisation, tax efficiency et direct indexing | GenesiX doit anticiper la personnalisation et la tax awareness comme axe credible | la presence d'un offering DI ne suffit pas a rendre un allocateur pertinent pour tous les clients |

---

## Implications fortes pour GenesiX

### 1. Whole portfolio view

Les plateformes les plus serieuses parlent presque toutes de vision consolidee :

- publics + privates ;
- comptes internes + held-away ;
- portefeuille modele + portefeuille reel.

Pour GenesiX, cela implique au minimum :

- un canonical holding model ;
- la capacite a raisonner sur portefeuille courant et portefeuille cible ;
- un delta de reallocation clair.

### 2. Risk language unifie

Toutes les plateformes fortes mettent en avant une langue commune du risque :

- exposure ;
- factor risk ;
- VaR / stress ;
- scenario ;
- attribution ;
- benchmark risk.

Pour GenesiX, cela implique :

- un risk payload unique ;
- la meme convention de risque du moteur au reporting ;
- pas de doubles verites entre `src/` et `backend/`.

### 3. Suitability, restrictions, tax and personalization

Le wealth moderne ne se limite pas a "profil prudent / agressif".

Les benchmarks montrent l'importance de :

- restrictions client ;
- product suitability ;
- tax-aware transitions ;
- preferences explicites ;
- personalized indexing.

Pour GenesiX, cela implique :

- un schema profile plus riche ;
- des contraintes de portefeuille persistantes ;
- une separation nette entre univers modeles et portefeuille personnalise.

### 4. Scaled portfolio management

Les plateformes fortes ne gerent pas seulement un portefeuille optimal theorique.
Elles gerent :

- alignement a des modeles ;
- exceptions ;
- rebalancing de masse ;
- suivi des comptes ecartes ;
- priorisation des actions.

Pour GenesiX, cela implique a terme :

- couche de model portfolio ;
- suivi `portfolio actuel vs portefeuille recommande` ;
- notion de `next best action`.

### 5. Open architecture et integration

Les references publiques insistent sur l'integration :

- APIs ;
- data feeds ;
- connectors ;
- workflows.

Pour GenesiX, cela implique :

- API typed et persistante ;
- architecture service/repository claire ;
- sources de donnees encapsulees ;
- traces de runs et auditability.

---

## Ce que GenesiX doit viser en priorite

Par rapport a ces benchmarks, les priorites raisonnables sont :

1. investor policy + constraints layer ;
2. eligible universe layer ;
3. capital market assumptions / views layer ;
4. unified risk payload ;
5. constrained allocation engine ;
6. recommendation payload with reasons ;
7. persistent allocation runs ;
8. model portfolio / rebalance delta plus tard.

---

## Ce que GenesiX ne doit pas faire

- simuler une plateforme type Aladdin avec des heuristiques opaques ;
- confondre "plus de ML" avec "meilleure recommendation" ;
- promettre direct indexing / tax awareness sans architecture de lots, couts et contraintes ;
- afficher un portefeuille "optimal" sans alternatives ni limites.

---

## Resume executif

La lecon principale des benchmarks publics est simple :

les meilleurs outils du marche ne vendent pas seulement de l'optimisation ;
ils vendent une **chaine coherente de decision, de risque, de contraintes, d'explication et d'execution**.

Si GenesiX veut atteindre son objectif final, c'est cette chaine qu'il faut construire.

