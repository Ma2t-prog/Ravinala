# REACT MIGRATION — PROMPT ULTIME POUR AGENT IA

# ══════════════════════════════════════════════════════════════════════

# CE FICHIER EST UNE MISSION COMPLETE. LIS-LE EN ENTIER AVANT D'AGIR.

# Tu es l'agent orchestrateur principal de la migration React.

# Tu peux et DOIS utiliser des sous-agents pour paralléliser le travail.

# AUCUN raccourci. AUCUNE simplification. Code réel, complet, testé.

# ══════════════════════════════════════════════════════════════════════

---

## ÉTAPE 0 — AVANT TOUTE MODIFICATION

### Fichiers à lire OBLIGATOIREMENT (dans cet ordre)

1. `montecarlo/AUDIT_RULES.md` — Les 7 règles bloquantes (R1-R7) + règles qualité (Q1-Q7)
2. `montecarlo/AGENT_INSTRUCTIONS.md` — Instructions backend (patterns, providers, schemas)
3. `montecarlo/AGENT_INSTRUCTIONS_FRONTEND.md` — Instructions frontend (règles migration, fusion, audit)
4. `ravinala-web/MIGRATION-PROMPT.md` — Design system complet (palette, typo, components CSS, layout)
5. Ce fichier en entier

### Architecture du workspace

```
c:\Users\Matthias\Project\
├── montecarlo/              ← Backend FastAPI + Streamlit (RÉFÉRENCE — NE PAS MODIFIER)
│   ├── backend/app/         ← API FastAPI (routes, services, providers, schemas, auth)
│   ├── src/pages/           ← 32 pages Streamlit (post-fusion) — RÉFÉRENCE FONCTIONNELLE
│   ├── src/pages/_archived/ ← 30 pages absorbées par les fusions
│   └── src/_shared.py       ← Design system CSS + sidebar nav (1700+ lignes)
└── ravinala-web/            ← React app — TON PÉRIMÈTRE DE TRAVAIL
    └── src/
        ├── api/             ← Axios client + types + market.ts (seul hook connecté)
        ├── hooks/           ← useMarketData.ts + usePricing.ts
        ├── components/      ← layout/ (Layout, Sidebar, TopBar, MarketStrip) + ui/ (Card, Badge, etc.)
        ├── pages/           ← 54 routes (pré-fusion) — À RÉALIGNER SUR LES 32 STREAMLIT
        ├── lib/             ← cn.ts (clsx wrapper)
        ├── App.tsx          ← Routes avec lazy loading
        └── main.tsx         ← Entry point
```

### Stack technique React

| Dépendance           | Version | Usage                      |
| -------------------- | ------- | -------------------------- |
| React                | 19.2.4  | Framework                  |
| React Router         | 7.13.1  | Routing (lazy + Suspense)  |
| TanStack React Query | 5.94.5  | Data fetching + cache      |
| Axios                | 1.13.6  | HTTP client (interceptors) |
| Tailwind CSS         | 4.2.2   | Utility-first styling      |
| Recharts             | 3.8.0   | Charts                     |
| Plotly.js            | 3.4.0   | Charts avancés             |
| Lucide React         | 0.577.0 | Icônes                     |
| TypeScript           | 5.9.3   | Typage strict              |

### Conventions de code existantes

```typescript
// === IMPORTS ===
// Lazy loading pour toutes les pages
const MyPage = lazy(() => import("./pages/section/MyPage"));

// === API LAYER ===
// Toutes les requêtes passent par src/api/client.ts (Axios, baseURL: '/api', timeout: 30s)
// Fonctions fetch dans src/api/*.ts → transforment les réponses raw
// Hooks React Query dans src/hooks/use*.ts avec query key factory

// === QUERY KEY FACTORY PATTERN ===
export const marketKeys = {
  all: ["market"] as const,
  snapshot: (s?: string) => ["market", "snapshot", s ?? "all"] as const,
  // ...
};

// === HOOK PATTERN ===
export function useSnapshot(sections?: string) {
  return useQuery<FullSnapshot, Error>({
    queryKey: marketKeys.snapshot(sections),
    queryFn: () => fetchSnapshot(sections),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

// === COMPOSANTS ===
// Tailwind + inline styles (pas de CSS-in-JS)
// Lucide icons (14px default)
// Composants UI dans src/components/ui/ (Card, Badge, Button, Tabs, Spinner, etc.)
// Layout fixe: Sidebar 280px, TopBar 56px, MarketStrip 54px, main padding-top: 122px

// === VITE PROXY ===
// /api → http://localhost:8000 (backend FastAPI)
// /health → http://localhost:8000
```

---

## MISSION PRINCIPALE — FUSION REACT (7 fusions)

Le Streamlit a été rationalisé de 55 pages → 32 pages via 7 fusions.
Le React a encore 54 routes reflétant l'ancienne architecture.
**Tu dois réaligner React sur les 32 pages Streamlit.**

### FUSION 1 — MarketIntelligence.tsx

**Route :** `/market`
**Fichier :** `src/pages/market/MarketIntelligence.tsx` (NOUVEAU)
**Absorbe :**

- `src/pages/market/LiveMarket.tsx` → Onglet "Live Market"
- `src/pages/market/MarketNews.tsx` → Onglet "Market News"
- `src/pages/market/MacroAnalysis.tsx` → Onglet "Macro Analysis"
- `src/pages/market/AltData.tsx` → Onglet "Alternative Data"

**4 onglets** via le composant `<Tabs>` commun.
**Après fusion** : SUPPRIMER LiveMarket.tsx, MarketNews.tsx, MacroAnalysis.tsx, AltData.tsx

**Pages market qui RESTENT séparées :**

- `Intelligence.tsx` (route: `/market/intelligence`)
- `FinancialAnalysis.tsx` (route: `/market/financial-analysis`)

---

### FUSION 2 — OptionsAnalytics.tsx

**Route :** `/derivatives/options`
**Fichier :** `src/pages/derivatives/OptionsAnalytics.tsx` (NOUVEAU)
**Absorbe :**

- `src/pages/derivatives/PricingCenter.tsx` → Onglet "Pricing Center"
- `src/pages/portfolio/StrategyLab.tsx` → Onglet "Strategy Lab"
- `src/pages/risk/Greeks.tsx` (était GreeksVolLab) → Onglet "Greeks & Sensitivity"
- `src/pages/portfolio/ScenarioMatrix.tsx` → Onglet "Scenario Matrix"

**4 onglets** via `<Tabs>`.
**Après fusion** : SUPPRIMER PricingCenter.tsx, StrategyLab.tsx, Greeks.tsx, ScenarioMatrix.tsx

**Pages derivatives qui RESTENT séparées :**

- StructuringSuite.tsx, CustomProduct.tsx, AdvancedExotics.tsx, MuseumExotics.tsx, Sandbox.tsx

---

### FUSION 3 — RiskPortfolioSuite.tsx

**Route :** `/risk/suite`
**Fichier :** `src/pages/risk/RiskPortfolioSuite.tsx` (NOUVEAU)
**Absorbe :**

- `src/pages/risk/RiskManagement.tsx` → Onglet "Risk Analytics"
- `src/pages/portfolio/PositionBook.tsx` → Onglet "Position Book"
- `src/pages/risk/Hedging.tsx` → Onglet "Hedging"
- `src/pages/risk/Backtesting.tsx` → Onglet "Backtesting"
- `src/pages/portfolio/PnLAttribution.tsx` → Onglet "P&L Attribution"

**5 onglets** via `<Tabs>`.
**Onglet "Risk Analytics" contient 4 sous-sections** (radio/pills) :

1. "VaR Analysis"
2. "Stress Scenarios"
3. "Risk Decomposition"
4. "Portfolio Risk"

**Après fusion** : SUPPRIMER RiskManagement.tsx, PositionBook.tsx, Hedging.tsx, Backtesting.tsx (risk), PnLAttribution.tsx

**Pages risk/portfolio qui RESTENT séparées :**

- VolCalibration.tsx, MLPricing.tsx, PortfolioOptimizer.tsx

---

### FUSION 4 — EquityResearchWorkbench.tsx

**Route :** `/research/workbench`
**Fichier :** `src/pages/research/EquityResearchWorkbench.tsx` (NOUVEAU)
**Absorbe :**

- `src/pages/research/EnterpriseValuations.tsx` → Onglets DCF, Monte Carlo, Multiples, Sensitivity
- `src/pages/research/CompanyAnalyzer.tsx` → Onglets Overview, Financials, Health, Ownership

**8 onglets** via `<Tabs>` :

1. "Overview"
2. "DCF Valuation"
3. "Monte Carlo DCF"
4. "Multiples"
5. "Financials" (sous-onglets: Income Statement, Balance Sheet, Cash Flow)
6. "Health & Risk"
7. "Ownership"
8. "Sensitivity"

**Après fusion** : SUPPRIMER EnterpriseValuations.tsx, CompanyAnalyzer.tsx

**Pages research qui RESTENT séparées :**

- EquityResearch.tsx, FixedIncome.tsx, AssetExplorer.tsx, ETFExplorer.tsx

---

### FUSION 5 — InstrumentNavigator.tsx

**Route :** `/market/instruments`
**Fichier :** `src/pages/market/InstrumentNavigator.tsx` (NOUVEAU)
**Absorbe :**

- `src/pages/genesix/UniverseSearch.tsx` → Onglet "Search"
- `src/pages/genesix/UniverseScreener.tsx` → Onglet "Screener"
- `src/pages/research/AssetExplorer.tsx` → Onglet "Asset Classes"
- `src/pages/research/ETFExplorer.tsx` → Onglet "ETF Focus"

**4 onglets** via `<Tabs>`.
**Onglet "Screener" contient 5 sous-onglets** :

1. "Classification"
2. "Fundamentals"
3. "Risk & Performance"
4. "Geographic"
5. "ESG"

**Après fusion** : SUPPRIMER UniverseSearch.tsx, UniverseScreener.tsx, AssetExplorer.tsx, ETFExplorer.tsx

---

### FUSION 6 — GenesixHub.tsx

**Route :** `/genesix/hub`
**Fichier :** `src/pages/genesix/GenesixHub.tsx` (NOUVEAU)
**Absorbe :**

- `src/pages/genesix/PortfolioOmega.tsx` → Section "Portfolio Allocator"
- `src/pages/genesix/PortfolioMonitor.tsx` → Section "Portfolio Monitor"
- `src/pages/genesix/RiskEngine.tsx` → Section "Risk Engine"
- `src/pages/genesix/MLEngine.tsx` → Section "ML Engine"
- `src/pages/genesix/MarketIntelligence.tsx` → Section "Market Intelligence"
- `src/pages/genesix/AdvancedAnalysis.tsx` → Section "Advanced Analysis"
- `src/pages/genesix/DataLayer.tsx` → Section "Data Layer"
- `src/pages/genesix/IntelligenceHub.tsx` (si existant) → Section "Intelligence Center"

**8 sections** via un `<select>` ou dropdown (pas des tabs — trop de sections).
Pattern Streamlit : `st.selectbox("Module", [...])` puis affichage conditionnel.

**Après fusion** : SUPPRIMER PortfolioOmega.tsx, PortfolioMonitor.tsx, RiskEngine.tsx, MLEngine.tsx, MarketIntelligence.tsx (genesix), AdvancedAnalysis.tsx, DataLayer.tsx

**Pages genesix qui RESTENT séparées :**

- AdvancedScreener.tsx, InstrumentAnalysis.tsx, GenesixBacktesting.tsx, SignalIntelligence.tsx, PhysicsLab.tsx

---

### FUSION 7 — MathFoundations.tsx

**Route :** `/learning/foundations`
**Fichier :** `src/pages/learning/MathFoundations.tsx` (NOUVEAU)
**Absorbe :**

- `src/pages/learning/LearningHub.tsx` → Onglet "📚 Educational Hub"
- `src/pages/learning/QuantumAcademy.tsx` → Onglet "⚛️ Quantum Academy"
- `src/pages/learning/ProbabilityBible.tsx` → Onglet "🎲 Probability Bible"

**3 onglets** via `<Tabs>`.
**Onglet "Educational Hub" contient 5 sous-onglets** :

1. "Equities & Indices"
2. "Commodities"
3. "FX Pairs"
4. "Interest Rates"
5. "Macro Indicators"

**Après fusion** : SUPPRIMER LearningHub.tsx, QuantumAcademy.tsx, ProbabilityBible.tsx

---

## MISE À JOUR App.tsx ET Sidebar.tsx (POST-FUSION)

### App.tsx — Routes finales cibles (32 routes)

```typescript
// ── Home ──
<Route index element={<Home />} />

// ── Market (3 routes au lieu de 6) ──
<Route path="market" element={<MarketIntelligence />} />           // FUSION 1
<Route path="market/instruments" element={<InstrumentNavigator />} /> // FUSION 5
<Route path="market/intelligence" element={<Intelligence />} />
<Route path="market/financial-analysis" element={<FinancialAnalysis />} />

// ── Derivatives (6 routes, PricingCenter absorbé → OptionsAnalytics) ──
<Route path="derivatives/options" element={<OptionsAnalytics />} /> // FUSION 2
<Route path="derivatives/structuring" element={<StructuringSuite />} />
<Route path="derivatives/custom" element={<CustomProduct />} />
<Route path="derivatives/exotics" element={<AdvancedExotics />} />
<Route path="derivatives/museum" element={<MuseumExotics />} />
<Route path="derivatives/sandbox" element={<Sandbox />} />

// ── Research (3 routes au lieu de 6) ──
<Route path="research/workbench" element={<EquityResearchWorkbench />} /> // FUSION 4
<Route path="research/equity" element={<EquityResearch />} />
<Route path="research/fixed-income" element={<FixedIncome />} />

// ── Risk & Portfolio (3 routes au lieu de 11) ──
<Route path="risk/suite" element={<RiskPortfolioSuite />} /> // FUSION 3
<Route path="risk/vol-calibration" element={<VolCalibration />} />
<Route path="risk/ml-pricing" element={<MLPricing />} />
<Route path="portfolio/optimizer" element={<PortfolioOptimizer />} />

// ── Tax Lab ──
<Route path="tax" element={<TaxLab />} />

// ── GENESIX Ω (6 routes au lieu de 13) ──
<Route path="genesix/hub" element={<GenesixHub />} />           // FUSION 6
<Route path="genesix/screener" element={<AdvancedScreener />} />
<Route path="genesix/instrument" element={<InstrumentAnalysis />} />
<Route path="genesix/backtest" element={<GenesixBacktesting />} />
<Route path="genesix/signals" element={<SignalIntelligence />} />
<Route path="genesix/physics" element={<PhysicsLab />} />

// ── Compliance (4 routes — inchangé) ──
<Route path="compliance/esg" element={<ESG />} />
<Route path="compliance/regulatory" element={<RegulatoryCapital />} />
<Route path="compliance/reports" element={<ReportGenerator />} />
<Route path="compliance/legal" element={<Legal />} />

// ── Learning (1 route au lieu de 3) ──
<Route path="learning/foundations" element={<MathFoundations />} /> // FUSION 7

// ── Trading Desk (2 routes — inchangé) ──
<Route path="trading/tradebook" element={<TradeBook />} />
<Route path="trading/admin" element={<AdminPanel />} />
```

### Sidebar.tsx — Sections cibles

```typescript
const sections: Section[] = [
  {
    id: 'market', title: 'Market', color: '#00D4FF',
    items: [
      { label: 'Market Intelligence', path: '/market',                    icon: <BarChart2 /> },
      { label: 'Instrument Navigator', path: '/market/instruments',       icon: <ScanSearch /> },
      { label: 'Instrument Detail',    path: '/market/intelligence',      icon: <Brain /> },
      { label: 'Financial Analysis',   path: '/market/financial-analysis', icon: <LineChart /> },
    ],
  },
  {
    id: 'derivatives', title: 'Derivatives & Structuring', color: '#8B5CF6',
    items: [
      { label: 'Options Analytics',  path: '/derivatives/options',     icon: <TrendingUp /> },
      { label: 'Structuring Suite',  path: '/derivatives/structuring', icon: <Layers /> },
      { label: 'Custom Product',     path: '/derivatives/custom',      icon: <Wrench /> },
      { label: 'Advanced Exotics',   path: '/derivatives/exotics',     icon: <FlaskConical /> },
      { label: 'Vol Calibration',    path: '/risk/vol-calibration',    icon: <Sliders /> },
      { label: 'Museum of Exotics',  path: '/derivatives/museum',      icon: <Archive /> },
      { label: 'The Sandbox',        path: '/derivatives/sandbox',     icon: <Boxes /> },
    ],
  },
  {
    id: 'risk', title: 'Risk & Portfolio', color: '#F59E0B',
    items: [
      { label: 'Risk & Portfolio Suite', path: '/risk/suite',         icon: <ShieldAlert /> },
      { label: 'Portfolio Optimizer',    path: '/portfolio/optimizer', icon: <Target /> },
      { label: 'ML Pricing',            path: '/risk/ml-pricing',     icon: <Bot /> },
    ],
  },
  {
    id: 'research', title: 'Research & Education', color: '#3B82F6',
    items: [
      { label: 'Equity Research Workbench', path: '/research/workbench',   icon: <Building2 /> },
      { label: 'Equity Research',           path: '/research/equity',      icon: <BarChart /> },
      { label: 'Fixed Income',              path: '/research/fixed-income', icon: <BookOpen /> },
      { label: 'Mathematical Foundations',  path: '/learning/foundations',  icon: <GraduationCap /> },
    ],
  },
  {
    id: 'tax', title: 'Tax Lab Ω', color: '#F59E0B',
    items: [
      { label: 'TAX LAB Ω — Full Suite', path: '/tax', icon: <Receipt /> },
    ],
  },
  {
    id: 'genesix', title: 'GENESIX Ω', color: '#D4AF37',
    items: [
      { label: 'GenesiX Hub',          path: '/genesix/hub',        icon: <Network /> },
      { label: 'Signal Intelligence',  path: '/genesix/signals',    icon: <Signal /> },
      { label: 'Advanced Screener',    path: '/genesix/screener',   icon: <Filter /> },
      { label: 'Instrument Analysis',  path: '/genesix/instrument', icon: <Microscope /> },
      { label: 'Backtesting',          path: '/genesix/backtest',   icon: <History /> },
      { label: 'Physics Lab',          path: '/genesix/physics',    icon: <Atom /> },
    ],
  },
  {
    id: 'compliance', title: 'Compliance', color: '#6366F1',
    items: [
      { label: 'ESG & Green Lab',    path: '/compliance/esg',        icon: <Leaf /> },
      { label: 'Regulatory Capital', path: '/compliance/regulatory', icon: <Scale /> },
      { label: 'Report Generator',   path: '/compliance/reports',    icon: <FileText /> },
      { label: 'Legal & Compliance', path: '/compliance/legal',      icon: <BookMarked /> },
    ],
  },
  {
    id: 'trading', title: 'Trading Desk', color: '#F43F5E',
    items: [
      { label: 'Trade Book',  path: '/trading/tradebook', icon: <ClipboardList /> },
      { label: 'Admin Panel', path: '/trading/admin',     icon: <Settings /> },
    ],
  },
]
```

---

## MISSION SECONDAIRE — API HOOKS (7 nouveaux hooks)

L'app n'a qu'un seul hook connecté au backend (`useMarketData.ts`).
Il faut créer 7 hooks supplémentaires en suivant le même pattern.

### Hook Pattern à respecter

```typescript
// src/api/<domain>.ts  — Fonctions fetch
// src/hooks/use<Domain>.ts — React Query hooks

// Exemple pattern (copier de useMarketData.ts) :
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "../api/client";

// Query key factory
export const riskKeys = {
  all: ["risk"] as const,
  var: (params?: string) => ["risk", "var", params ?? "default"] as const,
  stress: () => ["risk", "stress"] as const,
};

// Fetch function
async function fetchVaR(params?: string) {
  const { data } = await api.get("/api/v1/risk/var", {
    params: { portfolio: params },
  });
  return data;
}

// Hook
export function useVaR(params?: string) {
  return useQuery({
    queryKey: riskKeys.var(params),
    queryFn: () => fetchVaR(params),
    staleTime: 5 * 60_000,
  });
}
```

### Hooks à créer

| Fichier                                                | Hook                                     | Endpoints backend      | Pages consommatrices                   |
| ------------------------------------------------------ | ---------------------------------------- | ---------------------- | -------------------------------------- |
| `src/api/risk.ts` + `src/hooks/useRisk.ts`             | `useVaR`, `useStress`, `useCVaR`         | `/api/v1/risk/*`       | RiskPortfolioSuite                     |
| `src/api/backtest.ts` + `src/hooks/useBacktest.ts`     | `useBacktest`, `useBacktestResults`      | `/api/v1/backtest/*`   | RiskPortfolioSuite, GenesixBacktesting |
| `src/api/portfolio.ts` + `src/hooks/usePortfolio.ts`   | `usePositions`, `usePnL`, `useOptimizer` | `/api/v1/portfolio/*`  | RiskPortfolioSuite, PortfolioOptimizer |
| `src/api/ml.ts` + `src/hooks/useML.ts`                 | `useMLPrediction`, `useMLModels`         | `/api/v1/ml/*`         | MLPricing, GenesixHub                  |
| `src/api/analysis.ts` + `src/hooks/useAnalysis.ts`     | `useValuation`, `useDCF`, `useMultiples` | `/api/v1/analysis/*`   | EquityResearchWorkbench                |
| `src/api/users.ts` + `src/hooks/useUsers.ts`           | `useProfile`, `usePreferences`           | `/api/v1/users/*`      | AdminPanel, auth                       |
| `src/api/monitoring.ts` + `src/hooks/useMonitoring.ts` | `useAlerts`, `useSignals`                | `/api/v1/monitoring/*` | GenesixHub, SignalIntelligence         |

**IMPORTANT** : Pour chaque hook, vérifie d'abord que l'endpoint backend existe dans `montecarlo/backend/app/routes/`. Si l'endpoint n'existe pas encore, crée le fetch avec un commentaire `// TODO: Backend endpoint needed` et un fallback gracieux (pas de crash, affiche un message "Coming soon" ou "Connecting...").

---

## MISSION TERTIAIRE — SYSTÈME D'AUTHENTIFICATION

Le backend a un système auth complet (JWT + RBAC + bcrypt). React a ZÉRO auth.

### Fichiers à créer

#### 1. `src/api/auth.ts`

```typescript
import api from "./client";

export interface LoginRequest {
  email: string;
  password: string;
}
export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}
export interface UserInfo {
  id: number;
  email: string;
  name: string;
  role: string;
}

export async function login(creds: LoginRequest): Promise<AuthResponse> {
  const { data } = await api.post("/api/v1/auth/login", creds);
  return data;
}

export async function register(creds: RegisterRequest): Promise<AuthResponse> {
  const { data } = await api.post("/api/v1/auth/register", creds);
  return data;
}

export async function refreshToken(): Promise<{ access_token: string }> {
  const { data } = await api.post("/api/v1/auth/refresh");
  return data;
}

export async function fetchMe(): Promise<UserInfo> {
  const { data } = await api.get("/api/v1/auth/me");
  return data;
}
```

#### 2. `src/hooks/useAuth.ts` — AuthContext + Provider

- Stocke le JWT dans `localStorage` (clé: `access_token`)
- Expose: `user`, `login()`, `logout()`, `register()`, `isAuthenticated`, `isLoading`
- Auto-fetch `/auth/me` au mount si token présent
- Gère le refresh token

#### 3. Intercepteur Axios JWT (modifier `src/api/client.ts`)

```typescript
// Request interceptor — ajouter le token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — 401 → redirect login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);
```

#### 4. `src/pages/auth/LoginPage.tsx` + `src/pages/auth/RegisterPage.tsx`

- Design dark theme conforme au design system
- Formulaires avec validation
- Redirection vers Home après login réussi

#### 5. `src/components/auth/ProtectedRoute.tsx`

```typescript
// Wraps routes that need auth — redirects to /login if not authenticated
```

#### 6. Mise à jour App.tsx

```typescript
// Routes publiques
<Route path="login" element={<LoginPage />} />
<Route path="register" element={<RegisterPage />} />

// Routes protégées (wrapper)
<Route element={<ProtectedRoute />}>
  <Route element={<Layout />}>
    {/* ... toutes les routes existantes ... */}
  </Route>
</Route>
```

---

## PROTOCOLE D'EXÉCUTION — PHASES

### PHASE 1 : Fusions (Priorité MAXIMALE)

Pour chaque fusion (1 à 7) :

1. **Lis les fichiers source** React qui vont être absorbés (comprends le code existant)
2. **Lis la page Streamlit correspondante** dans `montecarlo/src/pages/` pour comprendre la logique métier et les onglets
3. **Crée le nouveau fichier fusionné** (composant avec Tabs, reprend le contenu des pages absorbées)
4. **Supprime les fichiers absorbés** (pas de doublons, AGENT_INSTRUCTIONS_FRONTEND.md règle 15)
5. **Vérifie `npm run build`** — ZÉRO erreur TypeScript

**Tu peux déléguer les fusions à des sous-agents** avec ce scope :

- Sous-agent A : Fusions 1 + 3 (Market Intelligence + Risk Portfolio Suite)
- Sous-agent B : Fusions 2 + 4 (Options Analytics + Equity Research Workbench)
- Sous-agent C : Fusions 5 + 6 (Instrument Navigator + GenesiX Hub)
- Sous-agent D : Fusion 7 (Math Foundations) + mise à jour App.tsx + Sidebar.tsx

Chaque sous-agent reçoit :

- Le scope exact des fichiers à créer/modifier/supprimer
- Les structures d'onglets détaillées ci-dessus
- L'interdiction de toucher aux fichiers hors de son périmètre

### PHASE 2 : Mise à jour routing + sidebar

1. **Modifier `src/App.tsx`** — Remplacer les 54 routes par les 32 routes cibles (voir section ci-dessus)
2. **Modifier `src/components/layout/Sidebar.tsx`** — Remplacer les sections par les sections cibles
3. **Vérifier `npm run build`** — ZÉRO erreur TS
4. **Vérifier navigation** — Chaque lien sidebar pointe vers une route existante

### PHASE 3 : API Hooks

1. Créer les 7 paires `api/*.ts` + `hooks/use*.ts`
2. Inspecter `montecarlo/backend/app/routes/` pour mapper les endpoints réels
3. Créer les types TypeScript correspondant aux schemas Pydantic du backend
4. Brancher les hooks dans les pages fusionnées (remplacer le mock data)

### PHASE 4 : Auth

1. `src/api/auth.ts` + intercepteur JWT dans `client.ts`
2. `src/hooks/useAuth.ts` (AuthContext + Provider)
3. `src/pages/auth/LoginPage.tsx` + `RegisterPage.tsx`
4. `src/components/auth/ProtectedRoute.tsx`
5. Wrapper dans App.tsx
6. Test : login → navigation protégée → logout → redirect

---

## RÈGLES ABSOLUES

### Ce que tu DOIS faire

1. **Respecter les patterns existants** — React Query, Tailwind, Lucide icons, lazy loading
2. **Chaque page fusionne TOUT le contenu** des pages absorbées — pas de features perdues
3. **Supprimer les fichiers absorbés** après fusion (AGENT_INSTRUCTIONS_FRONTEND.md règle 15)
4. **Mettre à jour App.tsx ET Sidebar.tsx** après chaque fusion (règle 16)
5. **`npm run build`** après chaque modification — ZÉRO erreur TS tolérée
6. **Typer correctement** — pas de `any` (AGENT_INSTRUCTIONS_FRONTEND.md règle 9)
7. **Toute donnée affichée doit venir d'un appel API** ou être explicitement mock avec un commentaire `// MOCK` (règle 5)
8. **Composant Tabs commun** pour toutes les fusions (règle 12)
9. **Tester le build final** avec `npm run build` ET ouvrir dans le navigateur

### Ce que tu NE DOIS PAS faire

1. ❌ **NE PAS toucher aux fichiers dans `montecarlo/`** — c'est la référence, lecture seule
2. ❌ **NE PAS créer de fichiers .py** (AGENT_INSTRUCTIONS_FRONTEND.md règle 1)
3. ❌ **NE PAS utiliser `console.log`** en production (règle 10)
4. ❌ **NE PAS hardcoder des données** présentées comme réelles (AUDIT_RULES R1)
5. ❌ **NE PAS hardcoder `risk_free_rate`** ou d'autres constantes (R2)
6. ❌ **NE PAS stocker de secrets** dans le code (R6)
7. ❌ **NE PAS laisser de code mort** actif (R7) — si une feature est désactivée, `throw new Error('Not implemented')`
8. ❌ **NE PAS laisser de doublons** — un fichier absorbé DOIT être supprimé
9. ❌ **NE PAS inventer des endpoints** qui n'existent pas — vérifier dans le backend d'abord

---

## VALIDATION FINALE

Quand TOUTES les phases sont terminées, vérifie :

```bash
# 1. Build propre
cd ravinala-web && npm run build
# → DOIT réussir avec 0 erreurs

# 2. Nombre de routes dans App.tsx
grep -c "Route path=" src/App.tsx
# → DOIT retourner ~32 (pas 54)

# 3. Pas de fichiers orphelins
# Les fichiers supprimés ne doivent plus exister :
# - src/pages/market/LiveMarket.tsx (absorbé → MarketIntelligence.tsx)
# - src/pages/market/MarketNews.tsx
# - src/pages/market/MacroAnalysis.tsx
# - src/pages/market/AltData.tsx
# - src/pages/derivatives/PricingCenter.tsx (absorbé → OptionsAnalytics.tsx)
# - src/pages/portfolio/StrategyLab.tsx
# - src/pages/portfolio/ScenarioMatrix.tsx
# - src/pages/risk/Greeks.tsx
# - src/pages/risk/RiskManagement.tsx (absorbé → RiskPortfolioSuite.tsx)
# - src/pages/risk/Backtesting.tsx
# - src/pages/risk/Hedging.tsx
# - src/pages/portfolio/PositionBook.tsx
# - src/pages/portfolio/PnLAttribution.tsx
# - src/pages/research/EnterpriseValuations.tsx (absorbé → EquityResearchWorkbench.tsx)
# - src/pages/research/CompanyAnalyzer.tsx
# - src/pages/genesix/UniverseSearch.tsx (absorbé → InstrumentNavigator.tsx)
# - src/pages/genesix/UniverseScreener.tsx
# - src/pages/research/AssetExplorer.tsx
# - src/pages/research/ETFExplorer.tsx
# - src/pages/genesix/PortfolioOmega.tsx (absorbé → GenesixHub.tsx)
# - src/pages/genesix/PortfolioMonitor.tsx
# - src/pages/genesix/RiskEngine.tsx
# - src/pages/genesix/MLEngine.tsx
# - src/pages/genesix/MarketIntelligence.tsx
# - src/pages/genesix/AdvancedAnalysis.tsx
# - src/pages/genesix/DataLayer.tsx
# - src/pages/learning/LearningHub.tsx (absorbé → MathFoundations.tsx)
# - src/pages/learning/QuantumAcademy.tsx
# - src/pages/learning/ProbabilityBible.tsx

# 4. Lint propre
npm run lint
# → 0 erreurs bloquantes

# 5. Auth fonctionnel
# LoginPage et RegisterPage existent et se buildent
# ProtectedRoute wraps les routes dans App.tsx
# Intercepteur JWT dans client.ts

# 6. Hooks API créés
ls src/hooks/
# → useAuth.ts, useMarketData.ts, usePricing.ts, useRisk.ts, useBacktest.ts,
#    usePortfolio.ts, useML.ts, useAnalysis.ts, useUsers.ts, useMonitoring.ts

# 7. Sidebar alignée
# Nombre d'items sidebar = ~30 (pas 60)
# Chaque item pointe vers une route valide dans App.tsx
```

---

## CHECKLIST DE LIVRAISON

- [ ] 7 fichiers fusion créés (MarketIntelligence, OptionsAnalytics, RiskPortfolioSuite, EquityResearchWorkbench, InstrumentNavigator, GenesixHub, MathFoundations)
- [ ] 28 fichiers absorbés supprimés
- [ ] App.tsx mis à jour (~32 routes)
- [ ] Sidebar.tsx mis à jour (8 sections, ~30 items)
- [ ] `npm run build` → 0 erreurs
- [ ] 7 API hooks créés
- [ ] Auth system complet (login, register, JWT, protected routes)
- [ ] `npm run lint` → 0 erreurs bloquantes
- [ ] Navigation testée (chaque lien sidebar fonctionne)

---

## POUR LES SOUS-AGENTS

Chaque sous-agent qui reçoit une tâche doit :

1. **Lire les fichiers sources** avant de coder
2. **Vérifier `npm run build`** après chaque fichier modifié
3. **Ne toucher qu'à son périmètre** — pas de modification hors scope
4. **Rapporter** : fichiers créés, fichiers supprimés, erreurs rencontrées
5. **Ne pas inventer de données** — si une donnée n'existe pas dans le fichier source, ne pas l'ajouter

---

_Fin du prompt. Bonne exécution._
