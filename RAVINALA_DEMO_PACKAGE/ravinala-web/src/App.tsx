import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout";

// ── Home ────────────────────────────────────────────────────────────────────
const Home = lazy(() => import("./pages/Home"));

// ── Market (fused) ───────────────────────────────────────────────────────────
const MarketIntelligencePage = lazy(
  () => import("./pages/market/MarketIntelligencePage"),
);
const InstrumentNavigator = lazy(
  () => import("./pages/research/InstrumentNavigator"),
);
const Intelligence = lazy(() => import("./pages/market/Intelligence"));
const FinancialAnalysis = lazy(
  () => import("./pages/market/FinancialAnalysis"),
);

// ── Derivatives (fused) ──────────────────────────────────────────────────────
const OptionsAnalytics = lazy(
  () => import("./pages/derivatives/OptionsAnalytics"),
);
const StructuringSuite = lazy(
  () => import("./pages/derivatives/StructuringSuite"),
);
const CustomProduct = lazy(() => import("./pages/derivatives/CustomProduct"));
const AdvancedExotics = lazy(
  () => import("./pages/derivatives/AdvancedExotics"),
);
const MuseumExotics = lazy(() => import("./pages/derivatives/MuseumExotics"));
const Sandbox = lazy(() => import("./pages/derivatives/Sandbox"));

// ── Research (fused) ─────────────────────────────────────────────────────────
const EquityResearchWorkbench = lazy(
  () => import("./pages/research/EquityResearchWorkbench"),
);
const EquityResearch = lazy(() => import("./pages/research/EquityResearch"));
const FixedIncome = lazy(() => import("./pages/research/FixedIncome"));

// ── Risk & Portfolio (fused) ─────────────────────────────────────────────────
const RiskPortfolioSuite = lazy(
  () => import("./pages/risk/RiskPortfolioSuite"),
);
const VolCalibration = lazy(() => import("./pages/risk/VolCalibration"));
const MLPricing = lazy(() => import("./pages/risk/MLPricing"));
const PortfolioOptimizer = lazy(
  () => import("./pages/portfolio/PortfolioOptimizer"),
);

// ── Tax Lab ───────────────────────────────────────────────────────────────────
const TaxLab = lazy(() => import("./pages/TaxLab"));

// ── GENESIX Ω (fused) ────────────────────────────────────────────────────────
const GenesixHub = lazy(() => import("./pages/genesix/GenesixHub"));
const AdvancedScreener = lazy(() => import("./pages/genesix/AdvancedScreener"));
const InstrumentAnalysis = lazy(
  () => import("./pages/genesix/InstrumentAnalysis"),
);
const GenesixBacktesting = lazy(() => import("./pages/genesix/Backtesting"));
const SignalIntelligence = lazy(
  () => import("./pages/genesix/SignalIntelligence"),
);
const PhysicsLab = lazy(() => import("./pages/genesix/PhysicsLab"));

// ── Compliance ────────────────────────────────────────────────────────────────
const ESG = lazy(() => import("./pages/compliance/ESG"));
const RegulatoryCapital = lazy(
  () => import("./pages/compliance/RegulatoryCapital"),
);
const ReportGenerator = lazy(
  () => import("./pages/compliance/ReportGenerator"),
);
const Legal = lazy(() => import("./pages/compliance/Legal"));

// ── Learning (fused) ─────────────────────────────────────────────────────────
const MathFoundations = lazy(() => import("./pages/learning/MathFoundations"));

// ── Trading Desk ──────────────────────────────────────────────────────────────
const TradeBook = lazy(() => import("./pages/trading/TradeBook"));
const AdminPanel = lazy(() => import("./pages/trading/AdminPanel"));

// ── AI Agents ─────────────────────────────────────────────────────────────────
const AgentMonitorPage = lazy(() => import("./pages/AgentMonitorPage"));

// ─────────────────────────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Standalone — Agent Monitor (independent of main UI) */}
          <Route
            path="agents/monitor"
            element={
              <Suspense>
                <AgentMonitorPage />
              </Suspense>
            }
          />

          <Route element={<Layout />}>
            {/* Home */}
            <Route
              index
              element={
                <Suspense>
                  <Home />
                </Suspense>
              }
            />

            {/* Market — fused */}
            <Route
              path="market"
              element={
                <Suspense>
                  <MarketIntelligencePage />
                </Suspense>
              }
            />
            <Route
              path="market/instruments"
              element={
                <Suspense>
                  <InstrumentNavigator />
                </Suspense>
              }
            />
            <Route
              path="market/intelligence"
              element={
                <Suspense>
                  <Intelligence />
                </Suspense>
              }
            />
            <Route
              path="market/financial-analysis"
              element={
                <Suspense>
                  <FinancialAnalysis />
                </Suspense>
              }
            />

            {/* Derivatives — fused */}
            <Route
              path="derivatives/options"
              element={
                <Suspense>
                  <OptionsAnalytics />
                </Suspense>
              }
            />
            <Route
              path="derivatives/structuring"
              element={
                <Suspense>
                  <StructuringSuite />
                </Suspense>
              }
            />
            <Route
              path="derivatives/custom"
              element={
                <Suspense>
                  <CustomProduct />
                </Suspense>
              }
            />
            <Route
              path="derivatives/exotics"
              element={
                <Suspense>
                  <AdvancedExotics />
                </Suspense>
              }
            />
            <Route
              path="derivatives/museum"
              element={
                <Suspense>
                  <MuseumExotics />
                </Suspense>
              }
            />
            <Route
              path="derivatives/sandbox"
              element={
                <Suspense>
                  <Sandbox />
                </Suspense>
              }
            />

            {/* Research — fused */}
            <Route
              path="research/workbench"
              element={
                <Suspense>
                  <EquityResearchWorkbench />
                </Suspense>
              }
            />
            <Route
              path="research/equity"
              element={
                <Suspense>
                  <EquityResearch />
                </Suspense>
              }
            />
            <Route
              path="research/fixed-income"
              element={
                <Suspense>
                  <FixedIncome />
                </Suspense>
              }
            />

            {/* Risk & Portfolio — fused */}
            <Route
              path="risk/suite"
              element={
                <Suspense>
                  <RiskPortfolioSuite />
                </Suspense>
              }
            />
            <Route
              path="risk/vol-calibration"
              element={
                <Suspense>
                  <VolCalibration />
                </Suspense>
              }
            />
            <Route
              path="risk/ml-pricing"
              element={
                <Suspense>
                  <MLPricing />
                </Suspense>
              }
            />
            <Route
              path="portfolio/optimizer"
              element={
                <Suspense>
                  <PortfolioOptimizer />
                </Suspense>
              }
            />

            {/* Tax Lab */}
            <Route
              path="tax"
              element={
                <Suspense>
                  <TaxLab />
                </Suspense>
              }
            />

            {/* GENESIX Ω — fused */}
            <Route
              path="genesix/hub"
              element={
                <Suspense>
                  <GenesixHub />
                </Suspense>
              }
            />
            <Route
              path="genesix/screener"
              element={
                <Suspense>
                  <AdvancedScreener />
                </Suspense>
              }
            />
            <Route
              path="genesix/instrument"
              element={
                <Suspense>
                  <InstrumentAnalysis />
                </Suspense>
              }
            />
            <Route
              path="genesix/backtest"
              element={
                <Suspense>
                  <GenesixBacktesting />
                </Suspense>
              }
            />
            <Route
              path="genesix/signals"
              element={
                <Suspense>
                  <SignalIntelligence />
                </Suspense>
              }
            />
            <Route
              path="genesix/physics"
              element={
                <Suspense>
                  <PhysicsLab />
                </Suspense>
              }
            />

            {/* Compliance */}
            <Route
              path="compliance/esg"
              element={
                <Suspense>
                  <ESG />
                </Suspense>
              }
            />
            <Route
              path="compliance/regulatory"
              element={
                <Suspense>
                  <RegulatoryCapital />
                </Suspense>
              }
            />
            <Route
              path="compliance/reports"
              element={
                <Suspense>
                  <ReportGenerator />
                </Suspense>
              }
            />
            <Route
              path="compliance/legal"
              element={
                <Suspense>
                  <Legal />
                </Suspense>
              }
            />

            {/* Learning — fused */}
            <Route
              path="learning/foundations"
              element={
                <Suspense>
                  <MathFoundations />
                </Suspense>
              }
            />

            {/* Trading Desk */}
            <Route
              path="trading/tradebook"
              element={
                <Suspense>
                  <TradeBook />
                </Suspense>
              }
            />
            <Route
              path="trading/admin"
              element={
                <Suspense>
                  <AdminPanel />
                </Suspense>
              }
            />

          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
