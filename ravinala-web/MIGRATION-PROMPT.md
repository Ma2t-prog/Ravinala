# PROMPT DE MIGRATION REACT — RAVINALA / GENESIX

> Copie-colle ce document entier dans Claude Code VS Code pour continuer la migration.

---

## CONTEXTE

Tu travailles sur `ravinala-web/` — une migration React de l'app Streamlit qui est dans `montecarlo/src/`.
Le design system Streamlit est defini dans `montecarlo/src/_shared.py` (1700+ lignes de CSS).
Le theme GenesiX est dans `montecarlo/src/genesix/dashboard/theme_v2.py`.

### CE QUI A ETE FAIT
- Projet Vite + React + TypeScript + Tailwind + React Router + React Query + Recharts
- 53 pages creees dans `src/pages/` avec du contenu fonctionnel
- Layout avec sidebar + routing complet
- Design system de base (Card, Badge, Spinner, StatCard)
- Hooks: `usePricing` (Black-Scholes client-side), `useMarketData`
- API layer dans `src/api/`
- Build propre, zero erreurs TypeScript

### CE QUI DOIT ETRE AMELIORE / CORRIGE
L'UI React actuelle est trop simplifiee par rapport au Streamlit. Il manque :

1. **Le header fixe avec market strip** — barre scrollante avec indices live (S&P 500, NASDAQ, DAX, etc.) et plus grosses capitalisations mondiales qui defilent, + indicateur marches ouverts/fermes
2. **Les boutons sont mal finis** — ils doivent avoir le style premium silver/gold du Streamlit
3. **Les menus/sidebar manquent de details** — icones, couleurs par section, animations
4. **Le backend FastAPI n'est pas connecte** — toutes les pages utilisent du mock data
5. **Les cartes et composants manquent de polish** — gradients, hover effects, animations

---

## DESIGN SYSTEM EXACT A REPRODUIRE

### Palette de couleurs

```
Backgrounds:
  --bg-base:      #0A0E1A    (fond de page)
  --bg-surface:   #131823    (sidebar, cartes)
  --bg-elevated:  #1A2332    (panneaux, dropdowns)
  --bg-hover:     #1F2A3A    (hover)
  --bg-active:    #2A3647    (active/pressed)

Texte:
  --text-primary:   #F1F5F9
  --text-secondary: #CBD5E1
  --text-tertiary:  #94A3B8
  --text-disabled:  #64748B
  --text-muted:     #475569

Accents:
  --accent-cyan:    #00D9FF   (accent principal)
  --accent-purple:  #7C3AED
  --accent-green:   #10B981   (positif/success)
  --accent-red:     #EF4444   (negatif/error)
  --accent-amber:   #F59E0B   (warning)
  --accent-gold:    #D4AF37   (GENESIX branding)

Asset Classes:
  --equities:     #3B82F6
  --fixed-income: #10B981
  --derivatives:  #F59E0B
  --commodities:  #EF4444
  --etfs:         #8B5CF6
  --crypto:       #F97316

Couleurs par section sidebar:
  Market Intel:   #00D4FF (cyan)
  Derivatives:    #8B5CF6 (purple)
  Research:       #3B82F6 (blue)
  Risk & Quant:   #F59E0B (amber)
  Portfolio Desk: #10B981 (emerald)
  GENESIX:        #D4AF37 (gold)
  Compliance:     #6366F1 (indigo)
  Learning:       #14B8A6 (teal)
  Trading Desk:   #F43F5E (rose)
```

### Typographie

```
Fonts a importer (Google Fonts):
  - Orbitron (logo GENESIX: 16px, weight 800, letter-spacing 0.22em)
  - DM Sans (nav links sidebar: 13px, weight 400)
  - Inter (body text, headings)
  - JetBrains Mono (nombres, data, code, section headers sidebar: 8.5px, weight 700, spacing 0.18em)

Tailles:
  h1: 32px semibold, letter-spacing -0.02em
  h2: 24px semibold, letter-spacing -0.01em
  h3: 18px semibold
  h4: 14px bold uppercase, letter-spacing 0.5px
  body: 13px
  body-sm: 12px
  xs: 11px

Tous les nombres: font-variant-numeric: tabular-nums
```

### Layout Structure

```
+----280px----+--------rest of viewport--------+
|  SIDEBAR    |   TOPBAR (56px, fixed)          |
|  (fixed)    |   backdrop-filter: blur(20px)   |
|             |   saturate(180%)                |
|  Logo       |   MARKET STRIP (54px, fixed)    |
|  Orbitron   |   indices + tickers defilants   |
|             |                                 |
|  Nav items  |   PAGE CONTENT                  |
|  avec       |   padding-top: 116px            |
|  icones     |   padding: 0 18px               |
|  couleurs   |                                 |
+-------------+---------------------------------+
```

### Topbar (56px fixe)

```css
background: rgba(10,14,26,0.82);
backdrop-filter: blur(20px) saturate(180%);
border-bottom: 1px solid rgba(51,65,85,0.2);
```

Contenu:
- Titre de la page courante (a gauche)
- Indicateur LIVE (dot vert pulsant) avec status marches US/EU/ASIA (ouvert/ferme)
- Date et heure live (a droite, JetBrains Mono, cyan)

### Market Strip (54px fixe, sous le topbar)

```css
background: rgba(8,12,20,0.92);
border-bottom: 1px solid rgba(51,65,85,0.15);
```

Contenu scrollant horizontalement (marquee/ticker):
- Indices: S&P 500, NASDAQ, DOW, DAX, CAC 40, FTSE, Nikkei, HSI
- Top caps: AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA, BRK.B
- Chaque item: ticker + prix + variation % (vert/rouge)
- Animation CSS marquee ou defilement continu

### Sidebar (280px fixe)

```css
background: linear-gradient(180deg, #080C14 0%, #0A0E18 55%, #08090E 100%);
box-shadow: 4px 0 32px rgba(0,0,0,0.55), 1px 0 0 rgba(212,175,55,0.04);
scrollbar: 3px, rgba(192,192,192,0.12) thumb
```

- Logo: "RAVINALA" en Orbitron, gold shimmer animation
- Sous-titre: "Quantum Lab Omega" en JetBrains Mono
- Sections avec headers en JetBrains Mono 8.5px uppercase, couleur par section
- Items: DM Sans 13px, icone a gauche, couleur par section au hover
- Hover: padding-left slide de 14px a 17px (transition subtile)
- Active: background accent + border-left 3px

### Cartes (.rvn-card)

```css
background: linear-gradient(135deg, rgba(19,24,35,0.6), rgba(15,18,24,0.6));
border: 1px solid rgba(51,65,85,0.3);
border-radius: 10px;
padding: 24px;
transition: all 250ms cubic-bezier(0.34, 1.56, 0.64, 1);

/* Hover: */
border-color: rgba(0,217,255,0.25);
box-shadow: 0 8px 24px rgba(0,217,255,0.06);
transform: translateY(-2px);
```

### Boutons (style premium silver/gold)

```css
/* Primary Button */
background: linear-gradient(135deg,
    rgba(192,192,200,0.12) 0%,
    rgba(212,212,220,0.18) 50%,
    rgba(192,192,200,0.12) 100%);
border: 1px solid rgba(192,192,210,0.25);
color: #F0F0F5;
border-radius: 10px;
font-family: 'DM Sans';
font-weight: 500;
font-size: 0.9rem;
padding: 12px 24px;
min-height: 44px;
box-shadow: 0 1px 2px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06);
transition: all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94);

/* Hover: translateY(-1px), gradient plus brillant, glow */
/* Active: translateY(0) scale(0.98), inset shadow */

/* Download/Accent Button */
background: rgba(0,217,255,0.06);
border: 1px solid rgba(0,217,255,0.2);
color: #00D9FF;
border-radius: 6px;
font-weight: 600;
```

### Metric Cards

```css
background: linear-gradient(135deg, rgba(19,24,35,0.6), rgba(15,18,24,0.6));
border: 1px solid rgba(51,65,85,0.3);
border-radius: 10px;
padding: 10px 14px;

/* Label: 10px uppercase, letter-spacing 0.08em, color #94A3B8 */
/* Value: JetBrains Mono, 20px, font-weight 700, tabular-nums */
/* Delta: 11px, font-weight 600, vert si positif, rouge si negatif */
/* Hover: translateY(-2px) + cyan border glow */
```

### Inputs / Formulaires

```css
background: rgba(51,65,85,0.2);
border: 1px solid rgba(51,65,85,0.3);
border-radius: 6px;
color: #F1F5F9;
font-family: 'JetBrains Mono';
font-size: 13px;
padding: 8px 12px;

/* Focus: border-color: #00D9FF; box-shadow: 0 0 12px rgba(0,217,255,0.1) */
```

### Radio comme Pills/Chips

```css
/* Non selectionne */
border: 1px solid rgba(51,65,85,0.3);
border-radius: 9999px;
background: rgba(19,24,35,0.5);
color: #94A3B8;
padding: 6px 14px;
font-size: 12px;

/* Selectionne */
border-color: rgba(0,217,255,0.35);
background: rgba(0,217,255,0.08);
color: #F1F5F9;
```

### Tabs

```css
/* Tab bar: border-bottom: 1px solid rgba(51,65,85,0.2) */
/* Tab: color #94A3B8, 12px, 600, letter-spacing 0.04em, padding 6px 14px */
/* Hover: color #F1F5F9, background rgba(0,217,255,0.03) */
/* Active: color #00D9FF, border-bottom 2px solid #00D9FF */
```

### Tables

```css
/* Header: */
background: rgba(19,24,35,0.4);
color: #94A3B8;
font-size: 12px;
letter-spacing: 0.05em;
text-transform: uppercase;
font-weight: 700;
padding: 12px;
border-bottom: 1px solid rgba(51,65,85,0.2);

/* Cells: */
color: #CBD5E1;
font-size: 12px;
font-family: 'JetBrains Mono';
padding: 10px 12px;
border-bottom: 1px solid rgba(51,65,85,0.1);

/* Row hover: background rgba(0,217,255,0.03) */
```

### Page Header Pattern

Chaque page commence par un header avec:
```
[Icon 40x40 cyan] Titre (24px semibold)
                   Sous-titre (12px tertiary)
                                              [Badge pill] section
```

### Animations CSS

```css
/* Entree des cartes (staggered) */
@keyframes rvn-card-in {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
/* Appliquer avec delay 0.05s par carte */

/* Logo shimmer metallique */
@keyframes rvn-logo-shimmer {
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
}
/* 5s linear infinite sur le texte du logo */

/* Dot LIVE pulsant */
@keyframes rvn-live-dot {
  0%, 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.4); }
  50% { box-shadow: 0 0 0 6px rgba(16,185,129,0); }
}

/* Fade up (hero) */
@keyframes rvn-fade-up {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### Background Effects

```css
/* Fond de page avec halos subtils */
background-image:
    radial-gradient(ellipse 1200px 800px at 20% 10%, rgba(0,217,255,0.04), transparent 55%),
    radial-gradient(ellipse 900px 650px at 85% 20%, rgba(124,58,237,0.03), transparent 55%);
```

### Scrollbar

```css
/* Global: 4px, rgba(51,65,85,0.3) thumb */
/* Main content: 6px, gold-tinted rgba(212,175,55,0.35) thumb */
/* Sidebar: 3px, rgba(192,192,192,0.12) thumb */
```

---

## FICHIERS DE REFERENCE STREAMLIT (A LIRE)

Pour comprendre le design exact:
- `montecarlo/src/_shared.py` — Design system complet (CSS + helpers Python)
- `montecarlo/src/app.py` — Entry point, navigation structure
- `montecarlo/src/genesix/dashboard/theme_v2.py` — Theme GenesiX
- `montecarlo/src/analysis/charting.py` — Plotly chart styles
- `montecarlo/src/analysis/core.py` — DARK_THEME dict

Pour comprendre le contenu des pages:
- `montecarlo/src/pages/` — Toutes les pages Streamlit

---

## TACHES A EFFECTUER (PAR PRIORITE)

### Phase 1 — Polish UI (URGENT)

1. **Refaire le composant Layout** (`src/components/layout/Layout.tsx`):
   - Ajouter le **Topbar fixe 56px** avec titre page, indicateur LIVE, status marches, date/heure
   - Ajouter le **Market Strip fixe 54px** avec ticker defilant (indices + top caps avec prix et variations)
   - Ameliorer la **Sidebar**: logo Orbitron avec shimmer, icones par item, couleurs par section, animations hover

2. **Refaire les composants UI** (`src/components/ui/`):
   - `Card.tsx` — ajouter gradient background, hover translateY(-2px) avec spring easing, glow cyan
   - `Button.tsx` — creer avec style premium silver/gold gradient, hover/active states
   - `MetricCard.tsx` — refaire avec le style exact (label uppercase, value JetBrains Mono, delta colore)
   - `Input.tsx` — style sombre avec focus cyan glow
   - `Tabs.tsx` — creer composant tabs avec style exact
   - `Table.tsx` — creer composant table avec header uppercase, hover rows, JetBrains Mono
   - `PillSelect.tsx` — radio buttons en pills/chips
   - `PageHeader.tsx` — header standard de page avec icone + titre + badge

3. **Ajouter les CSS globaux**:
   - Background halos radial-gradient
   - Scrollbar custom
   - Animations (card-in, fade-up, shimmer, live-dot)
   - Google Fonts imports (Orbitron, DM Sans, Inter, JetBrains Mono)

### Phase 2 — Connecter le Backend FastAPI

4. **Lire le backend existant** dans `montecarlo/src/` pour comprendre les endpoints disponibles
5. **Enrichir `src/api/`** avec tous les endpoints FastAPI
6. **Remplacer le mock data** dans chaque page par de vrais appels API via React Query
7. **Commencer par**: Live Market, Macro Analysis, Company Analyzer (pages les plus data-driven)

### Phase 3 — Fidelite Page par Page

8. **Pour chaque page**: ouvrir la version Streamlit (`montecarlo/src/pages/XXX.py`) et la version React (`src/pages/XXX.tsx`) cote a cote, et ajuster le React pour matcher exactement le layout, les composants, et les interactions du Streamlit.

---

## REGLES IMPORTANTES

- Ne JAMAIS toucher aux fichiers dans `montecarlo/` — c'est la reference, pas a modifier
- Toujours builder (`npm run build`) apres chaque modification pour verifier zero erreurs TS
- Garder l'architecture existante (lazy loading, React Router, React Query)
- Pour les charts Recharts: utiliser paper_bgcolor transparent, fond gere par la Card parente
- Tester dans le navigateur a chaque etape
- Faire les changements incrementalement, pas tout d'un coup
