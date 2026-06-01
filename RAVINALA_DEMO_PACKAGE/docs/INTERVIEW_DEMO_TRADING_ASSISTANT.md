# Ravinala - Demo Interview Trading Assistant

## Objectif

Presenter Ravinala comme un outil de support a une equipe de trading :

- observer les marches ;
- analyser le contexte macro ;
- pricer des produits derives ;
- mesurer les sensibilites et le risque ;
- simuler des scenarios ;
- produire des sorties exploitables.

Phrase d'ouverture :

> Ravinala est une plateforme cross-asset d'analytics et de risk management que j'ai construite pour reproduire une partie du workflow d'un desk : market monitoring, pricing, Greeks, stress testing, portefeuille et reporting. L'objectif n'est pas de remplacer un trader, mais d'aider un analyste ou trading assistant a structurer plus vite ses analyses.

## Parcours de demo recommande

Garder la demo entre 5 et 7 minutes.

1. Home / vue generale
   - Expliquer que la plateforme est organisee par workflow de desk.
   - Montrer la navigation : Market, Derivatives, Risk, Portfolio, Compliance.

2. Market Intelligence
   - Message cle : "Avant de parler produit, je regarde le contexte de marche."
   - Montrer indices, FX, commodities, macro ou news selon ce qui charge le mieux.

3. Derivatives / Options Analytics
   - Message cle : "Ensuite je peux pricer un produit et lire ses sensibilites."
   - Mentionner Black-Scholes, Monte Carlo, payoff, volatilite.

4. Risk Portfolio Suite
   - Message cle : "Le prix seul ne suffit pas ; il faut comprendre le risque."
   - Mentionner Greeks, VaR, stress testing, scenarios.

5. Portfolio Optimizer ou Scenario Matrix
   - Message cle : "Je peux aussi passer d'un instrument a une vision portefeuille."
   - Mentionner allocation, contraintes, drawdown, Sharpe, scenario analysis.

6. Reporting / Compliance
   - Message cle : "Un trading assistant doit aussi produire des outputs clairs."
   - Montrer la logique de reporting si l'ecran est stable.

## Commandes de lancement

Backend FastAPI :

```powershell
cd C:\Users\Matthias\Project\montecarlo\backend
$env:RAVINALA_SKIP_CELERY_WARMUP = "1"
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend React :

```powershell
cd C:\Users\Matthias\Project\ravinala-web
npm run dev
```

Build frontend :

```powershell
cd C:\Users\Matthias\Project\ravinala-web
npm run build
```

Streamlit historique :

```powershell
cd C:\Users\Matthias\Project\montecarlo
..\.venv\Scripts\python.exe -m streamlit run src/app.py
```

## Ce qu'il faut dire clairement

- Le projet est un prototype avance, pas une plateforme de production.
- Certaines donnees sont live, d'autres sont demo/static fallback.
- La valeur principale est le workflow complet : data -> pricing -> risk -> portfolio -> reporting.
- La prochaine etape serait le hardening : auth, database, providers de marche professionnels, tests UI, deploiement.

## Questions probables

Pourquoi ce projet ?

> Pour comprendre et reproduire le workflow concret d'un desk : suivre le marche, preparer une analyse, verifier le risque, documenter une decision.

Lien avec trading assistant ?

> Un trading assistant doit etre rigoureux sur les donnees, rapide dans les analyses, capable de comprendre le risque et utile aux traders. Ce projet montre ces competences de maniere concrete.

Concepts financiers couverts ?

> Black-Scholes, Monte Carlo, Greeks, VaR, CVaR, stress testing, backtesting, volatilite, allocation de portefeuille, scenarios macro.

Limites ?

> Ce n'est pas Bloomberg ni un systeme de trading execution-ready. C'est un outil d'analytics et de decision support, avec certains composants encore en mode prototype.

Ameliorations futures ?

> Connecter Bloomberg/Refinitiv ou un provider institutionnel, durcir l'authentification, deployer PostgreSQL/Redis proprement, ajouter des tests end-to-end et enrichir le reporting.

## Modules a eviter si le temps est court

- Toute page qui depend d'une API externe lente.
- Les fonctions d'IA/agents si le backend n'est pas lance.
- Les exports PDF/XLSX si tu n'as pas teste juste avant.
- Les modules experimentaux trop larges comme Tax Lab si tu n'as pas un message simple.

## Version 30 secondes

> J'ai construit Ravinala, une plateforme d'analytics cross-asset pour supporter un workflow de trading desk. Elle permet de suivre les marches, analyser le contexte macro, pricer des derives, calculer les Greeks, mesurer le risque, simuler des scenarios et preparer du reporting. Pour un role de trading assistant, elle montre ma capacite a relier finance de marche, data, risque et automatisation.
