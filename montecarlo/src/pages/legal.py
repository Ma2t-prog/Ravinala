import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st

_render_page_header("LG", "Legal Disclaimers & Important Information", "Read before any real-world use of models or outputs", "Compliance")
st.markdown("""
### IMPORTANT LEGAL DISCLAIMER

**Ravinala by TSIVAHINY Matthias** is an **EDUCATIONAL AND RESEARCH TOOL ONLY**. It is NOT a financial advisory service.

---

#### 1. **No Investment Advice**
- **NOT a financial advisor or recommendation engine**
- Prices calculated are **illustrative purposes only** (typically in USD or EUR)
- DO NOT use for actual investment decisions
- All prices shown should include currency notation (USD, EUR, etc.)

#### 2. **Disclaimer of Accuracy**
- Mathematical models simplify real-world complexity
- Actual market prices may differ significantly from calculated prices
- Missing factors: bid-ask spreads, credit risk, dividends, margin requirements, regulatory costs

#### 3. **Risks of Structured Products**
- **Credit Risk**: If issuer defaults → Loss of 100% capital
- **Market Risk**: Underlying assets may move unfavorably, reducing payoff
- **Liquidity Risk**: Hard to exit positions early at fair prices
- **Correlation Risk**: Multi-asset correlations collapse during financial crises
- **Path Dependency**: Some exotic options depend on price trajectory, not just final level
- **Volatility Risk**: Sensitive to implied volatility changes (vega exposure)
- **Funding Risk**: Rising interest rates compress the bond budget, reducing option value

#### 4. **No Regulatory Approval**
- NOT reviewed or approved by SEC, ESMA, FCA, AMF, BaFin, CONSOB, or any regulator
- NOT compliant with MiFID II (EU), Dodd-Frank (USA), or other financial regulations
- Does NOT meet structured product disclosure requirements
- NOT a substitute for professional compliance reviews

#### 5. **Past Performance ≠ Future Results**
- Historical backtests shown are illustrative only
- Past performance does NOT guarantee future results
- Market conditions, correlations, and volatility regimes change constantly
- Simulated prices may not reflect real market execution

#### 6. **As-Is, No Warranties**
- Ravinala is provided "AS-IS" WITHOUT ANY WARRANTIES
- Developers make NO representations regarding accuracy, completeness, or fitness
- YOU USE THIS APPLICATION AT YOUR OWN RISK

#### 7. **Limitation of Liability**
- Developers are NOT LIABLE for any losses, damages, or claims arising from use
- This includes direct, indirect, incidental, special, or consequential damages
- Even if advised of the possibility of such damages

#### 8. **Before Investing - You MUST Consult:**
- A licensed financial advisor or wealth manager
- Your bank's derivatives specialist (if buying structured products)
- A legal counsel to review contract terms
- Your compliance officer (if institutional investor)

#### 9. **Appropriate Uses**
- Learning derivatives pricing theory (educational)
- Understanding product structures and mechanics
- Exploring "what-if" scenarios in a sandbox environment
- Academic research and teaching
- Professional training and skill development
- Prototyping trading ideas (NOT executing them with real capital)

#### 10. **Inappropriate Uses - DO NOT USE FOR:**
- Making actual investment decisions
- Quoting prices to clients or counterparties
- Trading or hedging structured products with real money
- Regulatory reporting or risk compliance disclosures
- Replacing professional tools (Bloomberg, Murex, Numerix, etc.)
- Claims of pricing accuracy in any legal or contractual context

---

### AVERTISSEMENT JURIDIQUE IMPORTANT (FRANÇAIS)

**Ravinala par TSIVAHINY Matthias** est un **OUTIL PÉDAGOGIQUE ET DE RECHERCHE UNIQUEMENT**. Ce n'est PAS un service de conseil en investissement.

---

#### 1. **Pas de Conseils en Investissement**
- **PAS un conseiller financier**
- Les prix calculés sont **à titre illustratif uniquement** (typiquement en USD ou EUR)
- **N'utilisez PAS** pour prendre des décisions d'investissement réelles
- Tous les prix affichés doivent inclure la devise (USD, EUR, etc.)

#### 2. **Avertissement de Précision**
- Les modèles mathématiques simplifient la réalité
- Les prix réels du marché peuvent différer significativement
- Facteurs manquants: écarts acheteur-vendeur, risque de crédit, dividendes, coûts réglementaires

#### 3. **Risques des Produits Structurés**
- **Risque de crédit**: Si l'émetteur fait défaut → Perte de 100% du capital
- **Risque de marché**: Les sous-jacents peuvent baisser fortement
- **Risque de liquidité**: Sortie difficile et coûteuse
- **Risque de corrélation**: Les corrélations s'effondrent en crise financière
- **Dépendance du chemin**: Certains options exotiques dépendent du chemin des prix
- **Risque de volatilité**: Sensibilité aux changements de volatilité implicite
- **Risque de financement**: La hausse des taux comprime le budget obligataire

#### 4. **Pas d'Approbation Réglementaire**
- NON approuvé par l'AMF, ESMA, FCA, BaFin, CONSOB, ou tout régulateur
- NON conforme à MiFID II, Dodd-Frank, ou autres régulations
- Ne remplace PAS les revues de conformité professionnelles

#### 5. **Performances Passées ≠ Résultats Futurs**
- Les backtests sont illustratifs uniquement
- Les performances passées ne garantissent PAS les résultats futurs
- Les conditions de marché changent constamment

#### 6. **Fourni "TEL QUE" - Pas de Garanties**
- Ravinala est fourni "TEL QUE" SANS AUCUNE GARANTIE
- Les développeurs ne font AUCUNE garantie de précision
- VOUS L'UTILISEZ À VOS PROPRES RISQUES

#### 7. **Limitation de Responsabilité**
- Les développeurs NE SONT PAS RESPONSABLES de toute perte ou dommage
- Même s'ils sont avisés de la possibilité de tels dommages

#### 8. **Avant d'Investir - VOUS DEVEZ Consulter:**
- Un conseiller financier agréé
- Un spécialiste en produits dérivés de votre banque
- Un conseil juridique pour réviser les termes
- Votre responsable de conformité (si investisseur institutionnel)

#### 9. **Usages Appropriés**
- Apprendre la théorie du pricing de dérivés
- Comprendre les structures de produits
- Explorer des scénarios "et si?"
- Recherche académique et enseignement
- Formation professionnelle

#### 10. **Usages Inappropriés - N'UTILISEZ PAS POUR:**
- Prendre des décisions d'investissement réelles
- Coter des prix aux clients
- Trader des produits structurés avec de l'argent réel
- Rapports réglementaires
- Remplacer les outils professionnels (Bloomberg, Murex, etc.)

---

**By using Ravinala, you acknowledge that you have read, understood, and agree to all terms above.**

**En utilisant Ravinala, vous reconnaissez avoir lu, compris et accepté tous les termes ci-dessus.**
""")
