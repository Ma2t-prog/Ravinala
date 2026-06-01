# Ravinala

Ravinala est une plateforme de finance de marché que j'ai développée comme projet personnel : pricing de produits dérivés, optimisation de portefeuille, calcul de risque, et quelques agents IA pour automatiser des analyses. Le tout dans une interface web qui ressemble à un terminal type Bloomberg.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](montecarlo/backend/requirements.txt)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue.svg)](ravinala-web/tsconfig.json)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](montecarlo/backend/requirements.txt)
[![React 19](https://img.shields.io/badge/React-19-blue.svg)](ravinala-web/package.json)
[![Docker Ready](https://img.shields.io/badge/Docker-ready-blue.svg)](montecarlo/deployment/docker-compose.yml)

Pour lancer : `docker compose up -d` puis http://localhost:5173

## Pourquoi ce projet

Je suis en école de commerce et la finance de marché m'intéresse depuis un moment. Le problème quand on vient d'une formation business, c'est qu'on apprend les concepts (Black-Scholes, la VaR, Markowitz...) sans jamais vraiment mettre les mains dedans.

J'ai donc décidé de coder les outils moi-même. Ça m'a forcé à comprendre les modèles pour de vrai — quand il faut les implémenter, on ne peut plus se contenter de réciter une formule. Et au passage j'ai appris à construire une vraie application : backend, base de données, frontend, déploiement.

C'est un projet à double lecture : la partie finance pour montrer que je comprends les modèles, la partie technique pour montrer que je sais les faire tourner.

## Lancer l'application

Il faut juste Docker d'installé ([Docker Desktop](https://www.docker.com/products/docker-desktop)). Pas besoin de Python, Node ou PostgreSQL en local.

```bash
git clone https://github.com/Ma2t-prog/Ravinala.git
cd Ravinala/montecarlo/deployment

# créer le fichier de config (mot de passe de la base)
echo "DB_USER=ravinala
DB_PASSWORD=ravinala
DB_NAME=ravinala" > .env

docker compose up -d
```

Laissez tourner 30 à 60 secondes le temps que tout démarre, puis :

- Application : http://localhost:5173
- API + documentation Swagger : http://localhost:8000/docs
- Suivi des agents IA : http://localhost:5173/agents/monitor

Pour arrêter : `docker compose down`

Les agents IA ont besoin d'une clé `ANTHROPIC_API_KEY` (à mettre dans le `.env`) pour fonctionner pleinement. Sans elle, le reste de l'application marche quand même.

## Les modules

L'appli est découpée en pôles, un peu comme les différents écrans d'un terminal financier.

**Produits dérivés.** La partie la plus quantitative. Pricing d'options en Black-Scholes et Monte Carlo, options exotiques (barrières, asiatiques, lookback), un designer pour construire ses propres payoffs structurés, et des surfaces de prix/volatilité.

**Risque.** Calcul de VaR, sensibilités (les Greeks : Delta, Gamma, Vega...), stratégies de couverture, backtesting, et un module de pricing assisté par machine learning.

**Portefeuille.** Optimisation moyenne-variance et CVaR (Markowitz), attribution de performance, analyse de scénarios, suivi des positions.

**Recherche.** Analyse fondamentale d'actions, valorisation d'entreprises (DCF, multiples), exploration d'ETF et de l'univers d'investissement.

**Agents IA.** La partie sur laquelle j'ai le plus appris. Des agents construits avec LangGraph et Claude qui enchaînent plusieurs étapes de raisonnement pour analyser ou surveiller un portefeuille. On peut suivre leur activité depuis le dashboard.

**Marché, conformité, apprentissage.** Données de marché et macro, scoring ESG, capital réglementaire (Bâle III), génération de rapports, et quelques pages pédagogiques sur les maths financières.

## Stack technique

Frontend en React 19 / TypeScript avec Vite. Backend en Python avec FastAPI. Les calculs quant s'appuient sur NumPy, pandas et scipy ; le ML sur scikit-learn. Les agents utilisent LangGraph et l'API Claude. Côté données, PostgreSQL (avec TimescaleDB pour les séries temporelles) et Redis pour le cache.

Tout est conteneurisé : un seul `docker compose up` lance les quatre services (base, cache, API, interface).

```
Frontend (React/TS)
        │  HTTP / WebSocket
Backend (FastAPI)
   - moteurs quant (pricing, risque, allocation)
   - agents autonomes (LangGraph + Claude)
   - pipelines ML
        │
Données : PostgreSQL + TimescaleDB · Redis
```

## Organisation du code

```
Ravinala/
├── montecarlo/
│   ├── backend/app/
│   │   ├── routes/        endpoints API (market, risk, portfolio, agents...)
│   │   ├── services/      logique métier (pricing, optimisation, risque)
│   │   ├── agents/        agents LangGraph (graph, nodes, runner)
│   │   ├── risk/          moteur de risque et stress-testing
│   │   ├── allocation/    allocation d'actifs
│   │   └── ml/            pipelines machine learning
│   └── deployment/        Docker Compose, Dockerfiles, schéma SQL
│
└── ravinala-web/src/
    ├── pages/             modules : derivatives, risk, portfolio, research...
    ├── components/        composants UI
    └── api/               appels API
```

## API

Une fois lancé, la documentation interactive est sur `/docs` (Swagger) ou `/redoc`. Quelques endpoints clés :

- `POST /api/portfolio/optimize` — optimisation de portefeuille
- `GET /api/market/indices` — données de marché
- `POST /api/derivatives/price` — pricing de dérivés
- `GET /api/risk/analytics` — métriques de risque

## Licence

MIT (voir [LICENSE](LICENSE)).
