import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { generateRiskSummary } from "../../api/market";
import { Badge, Card, StatCard } from "../../components/ui/index";
import { useIndices } from "../../hooks/useMarketData";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Asset {
  id: string;
  ticker: string;
  weight: number;
  spot: number;
  sigma: number; // annualised vol %
  beta: number;
}

type ConfidenceLevel = "95" | "99" | "99.9";
type Horizon = "1" | "5" | "10" | "21";
type VaRMethod = "Parametric" | "Historical" | "Monte Carlo";

interface StressScenario {
  id: string;
  label: string;
  equityShock: number; // e.g. -0.40 = -40%
  volMultiplier: number; // e.g. 3 = +200%
  energyShock: number;
  bondShock: number;
  enabled: boolean;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const Z_SCORES: Record<ConfidenceLevel, number> = {
  "95": 1.645,
  "99": 2.326,
  "99.9": 3.09,
};

// Standard normal PDF
function normPDF(x: number): number {
  return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}

const DEFAULT_ASSETS: Asset[] = [
  { id: "1", ticker: "AAPL", weight: 35, spot: 189.5, sigma: 28, beta: 1.2 },
  { id: "2", ticker: "MSFT", weight: 30, spot: 415.2, sigma: 24, beta: 0.9 },
  { id: "3", ticker: "SPY", weight: 25, spot: 520.0, sigma: 18, beta: 1.0 },
  { id: "4", ticker: "TLT", weight: 10, spot: 92.3, sigma: 14, beta: -0.3 },
];

const DEFAULT_SCENARIOS: StressScenario[] = [
  {
    id: "gfc",
    label: "2008 GFC",
    equityShock: -0.4,
    volMultiplier: 3.0,
    energyShock: -0.2,
    bondShock: 0.05,
    enabled: true,
  },
  {
    id: "covid",
    label: "COVID-19 2020",
    equityShock: -0.35,
    volMultiplier: 4.0,
    energyShock: -0.3,
    bondShock: 0.08,
    enabled: true,
  },
  {
    id: "russia",
    label: "Russia-Ukraine 2022",
    equityShock: -0.2,
    volMultiplier: 1.5,
    energyShock: 0.5,
    bondShock: -0.08,
    enabled: false,
  },
  {
    id: "rate_shock",
    label: "Rate Shock +200bp",
    equityShock: -0.08,
    volMultiplier: 1.2,
    energyShock: 0.05,
    bondShock: -0.15,
    enabled: false,
  },
  {
    id: "custom",
    label: "Custom",
    equityShock: -0.1,
    volMultiplier: 1.5,
    energyShock: 0.0,
    bondShock: -0.05,
    enabled: false,
  },
];

// ─── Formatting helpers ───────────────────────────────────────────────────────

function fmtCurrency(v: number): string {
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : v > 0 ? "+" : "";
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000)
    return `${sign}$${abs.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
  return `${sign}$${abs.toFixed(2)}`;
}

function fmtPct(v: number, decimals = 2): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(decimals)}%`;
}

// ─── Colour palette ───────────────────────────────────────────────────────────

const RED = "#EF4444";
const GREEN = "#10B981";
const CYAN = "#00D9FF";
const AMBER = "#F59E0B";
const SLATE = "#94A3B8";
const BG_PAGE = "#0B0F1A";
const BORDER = "rgba(51,65,85,0.3)";

const PIE_COLORS = ["#EF4444", "#F59E0B", "#00D9FF", "#6366F1"];

// ─── Small reusable radio/checkbox primitives ──────────────────────────────────

function RadioGroup<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="mb-3">
      <p
        className="mb-1.5 text-xs font-medium uppercase tracking-wider"
        style={{ color: SLATE }}
      >
        {label}
      </p>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className="rounded px-3 py-1 text-xs font-semibold transition-colors"
            style={{
              backgroundColor: value === opt.value ? RED : "rgba(51,65,85,0.2)",
              color: value === opt.value ? "#fff" : SLATE,
              border: `1px solid ${value === opt.value ? RED : BORDER}`,
            }}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Tooltip for recharts ─────────────────────────────────────────────────────

function DarkTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name?: string; color?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded px-3 py-2 text-xs shadow-lg"
      style={{
        backgroundColor: "#1E2536",
        border: `1px solid ${BORDER}`,
        color: "#F1F5F9",
      }}
    >
      {label && (
        <p className="mb-1 font-semibold" style={{ color: SLATE }}>
          {label}
        </p>
      )}
      {payload.map((p, i) => (
        <p key={i} style={{ color: (p.value ?? 0) >= 0 ? GREEN : RED }}>
          {p.name ? `${p.name}: ` : ""}
          {fmtCurrency(p.value ?? 0)}
        </p>
      ))}
    </div>
  );
}

function GreekTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; name?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="rounded px-3 py-2 text-xs shadow-lg"
      style={{
        backgroundColor: "#1E2536",
        border: `1px solid ${BORDER}`,
        color: "#F1F5F9",
      }}
    >
      {label && (
        <p className="mb-1 font-semibold" style={{ color: SLATE }}>
          {label}
        </p>
      )}
      {payload.map((p, i) => (
        <p key={i} style={{ color: (p.value ?? 0) >= 0 ? GREEN : RED }}>
          {fmtCurrency(p.value ?? 0)}
        </p>
      ))}
    </div>
  );
}

// ─── Section header ───────────────────────────────────────────────────────────

function SectionHeader({ title, badge }: { title: string; badge?: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <span
        className="h-4 w-0.5 rounded-full"
        style={{ backgroundColor: RED }}
      />
      <h2
        className="text-sm font-semibold uppercase tracking-wider"
        style={{ color: "#F1F5F9", fontFamily: "JetBrains Mono, monospace" }}
      >
        {title}
      </h2>
      {badge && <Badge variant="down">{badge}</Badge>}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function RiskManagement() {
  // ── Live market data ────────────────────────────────────────────────────────
  const { data: indicesData, isLoading: indicesLoading } = useIndices();
  const usingFallback = !indicesData;

  // ── Portfolio state ──────────────────────────────────────────────────────
  const [assets, setAssets] = useState<Asset[]>(DEFAULT_ASSETS);
  const [portfolioValue, setPortfolioValue] = useState<number>(1_000_000);

  // Update spot prices from live data when available
  useEffect(() => {
    if (!indicesData) return;
    const allItems = Object.values(indicesData).flat();
    setAssets((prev) =>
      prev.map((a) => {
        const match = allItems.find(
          (idx) => idx.symbol.toUpperCase() === a.ticker.toUpperCase(),
        );
        return match ? { ...a, spot: match.price } : a;
      }),
    );
  }, [indicesData]);

  // Key market benchmarks for context
  const keyIndices = useMemo(() => {
    if (!indicesData) return [];
    const symbols = ["^GSPC", "^IXIC", "^DJI", "^RUT"];
    return Object.values(indicesData)
      .flat()
      .filter((idx) => symbols.includes(idx.symbol));
  }, [indicesData]);

  // ── Risk parameter state ─────────────────────────────────────────────────
  const [confidence, setConfidence] = useState<ConfidenceLevel>("99");
  const [horizon, setHorizon] = useState<Horizon>("1");
  const [method, setMethod] = useState<VaRMethod>("Parametric");
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  const handleGenerateSummary = async () => {
    setGeneratingSummary(true);
    setSummaryError(null);
    try {
      const positions = assets.map((a) => ({
        product_type: "european_call" as const,
        product_name: a.ticker,
        underlying: a.ticker,
        spot: a.spot,
        maturity_years: 1.0,
        risk_free_rate: 0.04,
        volatility: a.sigma / 100,
        notional: (a.weight / 100) * portfolioValue,
      }));
      const blob = await generateRiskSummary(positions);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `risk_summary_${new Date().toISOString().slice(0, 10)}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setSummaryError("PDF generation failed — check backend is running");
    } finally {
      setGeneratingSummary(false);
    }
  };

  // ── Stress scenarios ─────────────────────────────────────────────────────
  const [scenarios, setScenarios] =
    useState<StressScenario[]>(DEFAULT_SCENARIOS);
  const [customEquity, setCustomEquity] = useState<number>(-10);
  const [customEnergy, setCustomEnergy] = useState<number>(0);
  const [customBond, setCustomBond] = useState<number>(-5);

  // ── Asset table editing ──────────────────────────────────────────────────
  const totalWeight = assets.reduce((s, a) => s + a.weight, 0);

  function addAsset() {
    const id = String(Date.now());
    setAssets((prev) => [
      ...prev,
      { id, ticker: "NEW", weight: 0, spot: 100, sigma: 20, beta: 1.0 },
    ]);
  }

  function removeAsset(id: string) {
    setAssets((prev) => prev.filter((a) => a.id !== id));
  }

  function updateAsset(id: string, field: keyof Asset, raw: string) {
    setAssets((prev) =>
      prev.map((a) => {
        if (a.id !== id) return a;
        if (field === "ticker") return { ...a, ticker: raw.toUpperCase() };
        const num = parseFloat(raw);
        if (isNaN(num)) return a;
        return { ...a, [field]: num };
      }),
    );
  }

  function toggleScenario(id: string) {
    setScenarios((prev) =>
      prev.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s)),
    );
  }

  // ── VaR / CVaR calculations ───────────────────────────────────────────────
  const { varValue, cvarValue, portfolioSigma } = useMemo(() => {
    const z = Z_SCORES[confidence];
    const h = parseInt(horizon);

    // Weighted portfolio volatility (simplified: weighted average of individual vols)
    const sigma = assets.reduce((s, a) => {
      const w = a.weight / 100;
      return s + w * (a.sigma / 100);
    }, 0);

    const varValue = -portfolioValue * z * sigma * Math.sqrt(h);
    // CVaR = phi(z) / (1 - CL) * portfolio_value * sigma * sqrt(h)
    const cl = parseFloat(confidence) / 100;
    const cvarValue =
      -((portfolioValue * normPDF(z)) / (1 - cl)) * sigma * Math.sqrt(h);

    return { varValue, cvarValue, portfolioSigma: sigma * 100 };
  }, [assets, portfolioValue, confidence, horizon]);

  // ── Greeks decomposition (pseudo-values based on portfolio composition) ───
  const greeksData = useMemo(() => {
    const scale = portfolioValue / 1_000_000;
    // Approximate Greeks P&L contribution (illustrative for equity portfolio)
    const deltaP = -(Math.abs(varValue) * 0.65);
    const gammaP = -(Math.abs(varValue) * 0.12);
    const vegaP = -(Math.abs(varValue) * 0.18);
    const thetaP = Math.abs(varValue) * 0.05 * scale; // theta is usually a gain for short-gamma
    return [
      { name: "Delta", value: deltaP },
      { name: "Gamma", value: gammaP },
      { name: "Vega", value: vegaP },
      { name: "Theta", value: thetaP },
    ];
  }, [varValue, portfolioValue]);

  // ── Stress test P&L ──────────────────────────────────────────────────────
  const stressData = useMemo(() => {
    const enabledScenarios = scenarios.map((s) => {
      let pnl = 0;
      assets.forEach((a) => {
        const w = a.weight / 100;
        const notional = portfolioValue * w;
        // Simplified: equity assets shocked by equityShock, energy tickers by energyShock
        const isEnergy = ["XOM", "CVX", "USO", "OIL", "XLE"].includes(a.ticker);
        const isBond = ["TLT", "IEF", "LQD", "AGG", "BND"].includes(a.ticker);
        const effectiveShock =
          s.id === "custom"
            ? isBond
              ? customBond / 100
              : isEnergy
                ? customEnergy / 100
                : customEquity / 100
            : isBond
              ? s.bondShock
              : isEnergy
                ? s.energyShock
                : s.equityShock;
        pnl += notional * effectiveShock;
      });
      return { name: s.label, value: Math.round(pnl), enabled: s.enabled };
    });
    return enabledScenarios.filter((s) => s.enabled);
  }, [
    scenarios,
    assets,
    portfolioValue,
    customEquity,
    customEnergy,
    customBond,
  ]);

  // ── Risk metrics ──────────────────────────────────────────────────────────
  const metrics = useMemo(() => {
    const annualVol = portfolioSigma;
    const avgBeta = assets.reduce((s, a) => s + (a.weight / 100) * a.beta, 0);
    const sharpe = annualVol > 0 ? (8.5 / annualVol).toFixed(2) : "N/A"; // assume 8.5% expected return
    const maxDrawdown = -(annualVol * 2.5).toFixed(1) + "%";
    const tailRisk = Math.abs(cvarValue / varValue).toFixed(2);
    const infoRatio =
      annualVol > 0 ? (2.1 / (annualVol * 0.5)).toFixed(2) : "N/A"; // illustrative
    return {
      maxDrawdown,
      sharpe,
      annualVol: annualVol.toFixed(1) + "%",
      beta: avgBeta.toFixed(2),
      infoRatio,
      tailRisk,
    };
  }, [portfolioSigma, assets, cvarValue, varValue]);

  // ── Risk decomposition pie ───────────────────────────────────────────────
  const decompData = useMemo(
    () => [
      { name: "Delta Risk", value: 55 },
      { name: "Gamma Risk", value: 18 },
      { name: "Vega Risk", value: 20 },
      { name: "Residual", value: 7 },
    ],
    [],
  );

  // ── Confidence & horizon label ────────────────────────────────────────────
  const horizonLabel =
    horizon === "1"
      ? "1-Day"
      : horizon === "5"
        ? "5-Day"
        : horizon === "10"
          ? "10-Day"
          : "21-Day";
  const confLabel = confidence + "% confidence";

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-screen p-4"
      style={{
        backgroundColor: BG_PAGE,
        color: "#F1F5F9",
        fontFamily: "Inter, sans-serif",
      }}
    >
      {/* Fallback Banner */}
      {usingFallback && !indicesLoading && (
        <div
          className="rounded px-4 py-2 mb-4 text-sm font-mono"
          style={{
            backgroundColor: "rgba(245,158,11,0.1)",
            border: "1px solid rgba(245,158,11,0.3)",
            color: AMBER,
          }}
        >
          Backend unreachable — showing demo data
        </div>
      )}

      {/* Live Market Benchmarks */}
      {keyIndices.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: 10,
            marginBottom: 16,
            flexWrap: "wrap",
          }}
        >
          {keyIndices.map((idx) => (
            <div
              key={idx.symbol}
              style={{
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 8,
                padding: "8px 14px",
                border: "1px solid rgba(51,65,85,0.2)",
                minWidth: 140,
              }}
            >
              <div style={{ fontSize: 10, color: SLATE }}>{idx.name}</div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span
                  style={{
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 14,
                    fontWeight: 700,
                    color: "#F1F5F9",
                  }}
                >
                  {idx.price.toLocaleString(undefined, {
                    maximumFractionDigits: 0,
                  })}
                </span>
                <span
                  style={{
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 12,
                    fontWeight: 600,
                    color: idx.change.percent >= 0 ? GREEN : "#EF4444",
                  }}
                >
                  {idx.change.percent >= 0 ? "+" : ""}
                  {idx.change.percent.toFixed(2)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Page header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1
            className="text-2xl font-bold tracking-tight"
            style={{
              fontFamily: "JetBrains Mono, monospace",
              color: "#F1F5F9",
            }}
          >
            Risk Management
          </h1>
          <p className="mt-1 text-sm" style={{ color: SLATE }}>
            Quantitative risk analytics — VaR, CVaR, stress testing &amp; Greeks
            decomposition
          </p>
        </div>
        <div className="flex items-center gap-3" style={{ flexWrap: "wrap" }}>
          <Badge variant="down">LIVE CALC</Badge>
          <Badge variant="neutral">{method}</Badge>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              gap: 4,
            }}
          >
            <button
              onClick={handleGenerateSummary}
              disabled={generatingSummary}
              style={{
                backgroundColor: generatingSummary
                  ? "rgba(0,217,255,0.08)"
                  : "rgba(0,217,255,0.12)",
                border: "1px solid rgba(0,217,255,0.35)",
                borderRadius: 8,
                color: "#00D9FF",
                padding: "8px 16px",
                fontSize: 12,
                fontWeight: 600,
                cursor: generatingSummary ? "wait" : "pointer",
                opacity: generatingSummary ? 0.7 : 1,
                whiteSpace: "nowrap",
              }}
            >
              {generatingSummary ? "Generating…" : "⬇ Risk Summary PDF"}
            </button>
            {summaryError && (
              <span style={{ color: "#EF4444", fontSize: 11 }}>
                {summaryError}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Two-panel layout */}
      <div className="flex gap-4" style={{ alignItems: "flex-start" }}>
        {/* ── LEFT PANEL ─────────────────────────────────────────────── */}
        <div
          className="flex flex-col gap-4"
          style={{ width: "380px", flexShrink: 0 }}
        >
          {/* Portfolio section */}
          <Card>
            <SectionHeader title="Portfolio" />

            {/* Portfolio value */}
            <div className="mb-3">
              <label
                className="mb-1 block text-xs font-medium uppercase tracking-wider"
                style={{ color: SLATE }}
              >
                Portfolio Notional ($)
              </label>
              <input
                type="number"
                value={portfolioValue}
                onChange={(e) =>
                  setPortfolioValue(parseFloat(e.target.value) || 1_000_000)
                }
                className="w-full rounded px-3 py-1.5 text-sm font-mono"
                style={{
                  backgroundColor: "#0B0F1A",
                  border: `1px solid ${BORDER}`,
                  color: "#F1F5F9",
                  outline: "none",
                }}
              />
            </div>

            {/* Asset table */}
            <div className="mb-2 overflow-x-auto">
              <table
                className="w-full text-xs"
                style={{ borderCollapse: "collapse" }}
              >
                <thead>
                  <tr style={{ color: SLATE }}>
                    <th
                      className="pb-2 text-left font-medium uppercase tracking-wider"
                      style={{ width: 60 }}
                    >
                      Ticker
                    </th>
                    <th
                      className="pb-2 text-right font-medium uppercase tracking-wider"
                      style={{ width: 55 }}
                    >
                      Wt %
                    </th>
                    <th
                      className="pb-2 text-right font-medium uppercase tracking-wider"
                      style={{ width: 65 }}
                    >
                      Spot
                    </th>
                    <th
                      className="pb-2 text-right font-medium uppercase tracking-wider"
                      style={{ width: 50 }}
                    >
                      Vol %
                    </th>
                    <th
                      className="pb-2 text-right font-medium uppercase tracking-wider"
                      style={{ width: 40 }}
                    >
                      Beta
                    </th>
                    <th className="pb-2" style={{ width: 24 }} />
                  </tr>
                </thead>
                <tbody>
                  {assets.map((asset) => (
                    <tr
                      key={asset.id}
                      style={{ borderTop: `1px solid ${BORDER}` }}
                    >
                      {(
                        ["ticker", "weight", "spot", "sigma", "beta"] as const
                      ).map((field) => (
                        <td
                          key={field}
                          className={`py-1.5 ${field === "ticker" ? "pr-1" : "pl-1"}`}
                        >
                          <input
                            type={field === "ticker" ? "text" : "number"}
                            value={asset[field]}
                            onChange={(e) =>
                              updateAsset(asset.id, field, e.target.value)
                            }
                            className="w-full rounded px-1.5 py-0.5 text-right font-mono"
                            style={{
                              backgroundColor: "rgba(15,20,30,0.8)",
                              border: `1px solid ${BORDER}`,
                              color: "#F1F5F9",
                              outline: "none",
                              textAlign: field === "ticker" ? "left" : "right",
                            }}
                          />
                        </td>
                      ))}
                      <td className="py-1.5 pl-1">
                        <button
                          onClick={() => removeAsset(asset.id)}
                          className="flex h-5 w-5 items-center justify-center rounded text-xs transition-colors"
                          style={{
                            color: SLATE,
                            backgroundColor: "transparent",
                          }}
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.color = RED)
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.color = SLATE)
                          }
                          title="Remove asset"
                        >
                          ×
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Total weight */}
            <div className="mb-3 flex items-center justify-between text-xs">
              <span style={{ color: SLATE }}>Total Weight</span>
              <span
                className="font-mono font-semibold"
                style={{
                  color: Math.abs(totalWeight - 100) < 0.01 ? GREEN : AMBER,
                }}
              >
                {totalWeight.toFixed(1)}%
                {Math.abs(totalWeight - 100) >= 0.01 && (
                  <span className="ml-1 text-[10px]" style={{ color: AMBER }}>
                    (≠ 100%)
                  </span>
                )}
              </span>
            </div>

            <button
              onClick={addAsset}
              className="w-full rounded py-1.5 text-xs font-semibold transition-colors"
              style={{
                backgroundColor: "rgba(239,68,68,0.1)",
                border: `1px solid rgba(239,68,68,0.3)`,
                color: RED,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = "rgba(239,68,68,0.2)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = "rgba(239,68,68,0.1)";
              }}
            >
              + Add Asset
            </button>
          </Card>

          {/* Risk parameters */}
          <Card>
            <SectionHeader title="Risk Parameters" />

            <RadioGroup<ConfidenceLevel>
              label="Confidence Level"
              options={[
                { value: "95", label: "95%" },
                { value: "99", label: "99%" },
                { value: "99.9", label: "99.9%" },
              ]}
              value={confidence}
              onChange={setConfidence}
            />

            <RadioGroup<Horizon>
              label="Horizon"
              options={[
                { value: "1", label: "1D" },
                { value: "5", label: "5D" },
                { value: "10", label: "10D" },
                { value: "21", label: "21D" },
              ]}
              value={horizon}
              onChange={setHorizon}
            />

            <RadioGroup<VaRMethod>
              label="Method"
              options={[
                { value: "Parametric", label: "Parametric" },
                { value: "Historical", label: "Historical" },
                { value: "Monte Carlo", label: "Monte Carlo" },
              ]}
              value={method}
              onChange={setMethod}
            />

            {method !== "Parametric" && (
              <div
                className="mt-1 rounded px-3 py-2 text-xs"
                style={{
                  backgroundColor: "rgba(245,158,11,0.08)",
                  border: `1px solid rgba(245,158,11,0.2)`,
                  color: AMBER,
                }}
              >
                {method} simulation uses parametric approximation in this demo.
                Full simulation requires historical returns data.
              </div>
            )}
          </Card>

          {/* Stress scenarios */}
          <Card>
            <SectionHeader title="Stress Scenarios" />

            <div className="flex flex-col gap-2">
              {scenarios.map((s) => (
                <div key={s.id}>
                  <label
                    className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 transition-colors"
                    style={{
                      backgroundColor: s.enabled
                        ? "rgba(239,68,68,0.06)"
                        : "transparent",
                      border: `1px solid ${s.enabled ? "rgba(239,68,68,0.2)" : "transparent"}`,
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={s.enabled}
                      onChange={() => toggleScenario(s.id)}
                      className="h-3.5 w-3.5 rounded"
                      style={{ accentColor: RED }}
                    />
                    <span
                      className="flex-1 text-xs font-medium"
                      style={{ color: s.enabled ? "#F1F5F9" : SLATE }}
                    >
                      {s.label}
                    </span>
                    {s.enabled && (
                      <span
                        className="text-[10px] font-mono"
                        style={{ color: RED }}
                      >
                        {fmtPct(s.equityShock * 100, 0)} eq
                      </span>
                    )}
                  </label>

                  {/* Custom scenario inputs */}
                  {s.id === "custom" && s.enabled && (
                    <div className="mt-1.5 ml-5 flex flex-col gap-1.5">
                      {[
                        {
                          label: "Equity shock %",
                          value: customEquity,
                          set: setCustomEquity,
                        },
                        {
                          label: "Energy shock %",
                          value: customEnergy,
                          set: setCustomEnergy,
                        },
                        {
                          label: "Bond shock %",
                          value: customBond,
                          set: setCustomBond,
                        },
                      ].map(({ label, value, set }) => (
                        <div key={label} className="flex items-center gap-2">
                          <span
                            className="w-28 text-[11px]"
                            style={{ color: SLATE }}
                          >
                            {label}
                          </span>
                          <input
                            type="number"
                            value={value}
                            onChange={(e) =>
                              set(parseFloat(e.target.value) || 0)
                            }
                            className="w-20 rounded px-2 py-0.5 text-right text-xs font-mono"
                            style={{
                              backgroundColor: "#0B0F1A",
                              border: `1px solid ${BORDER}`,
                              color: "#F1F5F9",
                              outline: "none",
                            }}
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* ── RIGHT PANEL ────────────────────────────────────────────── */}
        <div className="flex flex-1 flex-col gap-4">
          {/* VaR / CVaR hero */}
          <Card>
            <SectionHeader
              title="VaR / CVaR"
              badge={`${horizonLabel} · ${confLabel}`}
            />

            <div className="flex items-start gap-6">
              {/* VaR large display */}
              <div>
                <p
                  className="mb-1 text-xs font-medium uppercase tracking-wider"
                  style={{ color: SLATE }}
                >
                  Value at Risk ({horizonLabel})
                </p>
                <p
                  className="font-mono text-4xl font-bold leading-none"
                  style={{ color: RED }}
                >
                  {fmtCurrency(varValue)}
                </p>
                <p className="mt-1 text-xs" style={{ color: SLATE }}>
                  {confLabel} · {method}
                </p>
              </div>

              {/* Divider */}
              <div
                className="h-16 w-px self-center"
                style={{ backgroundColor: BORDER }}
              />

              {/* CVaR */}
              <div>
                <p
                  className="mb-1 text-xs font-medium uppercase tracking-wider"
                  style={{ color: SLATE }}
                >
                  CVaR / Expected Shortfall
                </p>
                <p
                  className="font-mono text-3xl font-bold leading-none"
                  style={{ color: "rgba(239,68,68,0.8)" }}
                >
                  {fmtCurrency(cvarValue)}
                </p>
                <p className="mt-1 text-xs" style={{ color: SLATE }}>
                  Average loss beyond VaR
                </p>
              </div>

              {/* Divider */}
              <div
                className="h-16 w-px self-center"
                style={{ backgroundColor: BORDER }}
              />

              {/* Vol */}
              <div>
                <p
                  className="mb-1 text-xs font-medium uppercase tracking-wider"
                  style={{ color: SLATE }}
                >
                  Portfolio σ (Ann.)
                </p>
                <p
                  className="font-mono text-3xl font-bold leading-none"
                  style={{ color: AMBER }}
                >
                  {portfolioSigma.toFixed(1)}%
                </p>
                <p className="mt-1 text-xs" style={{ color: SLATE }}>
                  Weighted avg vol
                </p>
              </div>

              {/* z-score info */}
              <div className="ml-auto flex flex-col items-end gap-1 self-center">
                <div className="text-xs" style={{ color: SLATE }}>
                  z = {Z_SCORES[confidence].toFixed(3)}
                </div>
                <div className="text-xs" style={{ color: SLATE }}>
                  √h = {Math.sqrt(parseInt(horizon)).toFixed(3)}
                </div>
                <Badge variant="down">
                  VaR/Notional:{" "}
                  {(Math.abs(varValue / portfolioValue) * 100).toFixed(2)}%
                </Badge>
              </div>
            </div>
          </Card>

          {/* Risk Metrics Grid */}
          <div
            className="grid grid-cols-3 gap-3"
            style={{ gridTemplateRows: "auto auto" }}
          >
            <StatCard
              label="Max Drawdown"
              value={metrics.maxDrawdown}
              color={RED}
            />
            <StatCard
              label="Sharpe Ratio"
              value={metrics.sharpe}
              color={GREEN}
            />
            <StatCard
              label="Volatility Ann."
              value={metrics.annualVol}
              color={AMBER}
            />
            <StatCard label="Beta vs SPX" value={metrics.beta} color={CYAN} />
            <StatCard
              label="Information Ratio"
              value={metrics.infoRatio}
              color={GREEN}
            />
            <StatCard
              label="Tail Risk (CVaR/VaR)"
              value={metrics.tailRisk}
              color={RED}
            />
          </div>

          {/* Greeks Decomposition */}
          <Card>
            <SectionHeader title="Greeks Decomposition" />
            <p className="mb-3 text-xs" style={{ color: SLATE }}>
              Estimated P&amp;L attribution over {horizonLabel} horizon
            </p>
            <div style={{ height: 180 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={greeksData}
                  margin={{ top: 4, right: 12, left: 8, bottom: 4 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke={BORDER}
                    vertical={false}
                  />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: SLATE, fontSize: 11 }}
                    axisLine={{ stroke: BORDER }}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: SLATE, fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => fmtCurrency(v)}
                    width={72}
                  />
                  <Tooltip content={<GreekTooltip />} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {greeksData.map((entry, i) => (
                      <Cell
                        key={i}
                        fill={entry.value >= 0 ? GREEN : RED}
                        fillOpacity={0.85}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Stress Test Results + Risk Decomposition side by side */}
          <div className="flex gap-4">
            {/* Stress Test Results */}
            <Card className="flex-1">
              <SectionHeader title="Stress Test Results" />
              {stressData.length === 0 ? (
                <div
                  className="flex h-32 items-center justify-center text-xs"
                  style={{ color: SLATE }}
                >
                  Enable at least one scenario to see results
                </div>
              ) : (
                <div
                  style={{ height: Math.max(160, stressData.length * 48 + 32) }}
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={stressData}
                      layout="vertical"
                      margin={{ top: 4, right: 60, left: 8, bottom: 4 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke={BORDER}
                        horizontal={false}
                      />
                      <XAxis
                        type="number"
                        tick={{ fill: SLATE, fontSize: 10 }}
                        axisLine={{ stroke: BORDER }}
                        tickLine={false}
                        tickFormatter={(v) => fmtCurrency(v)}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fill: SLATE, fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                        width={130}
                      />
                      <Tooltip content={<DarkTooltip />} />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {stressData.map((entry, i) => (
                          <Cell
                            key={i}
                            fill={entry.value >= 0 ? GREEN : RED}
                            fillOpacity={0.85}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>

            {/* Risk Decomposition Pie */}
            <div style={{ width: 280, flexShrink: 0 }}>
              <Card>
                <SectionHeader title="Risk Decomposition" />
                <div style={{ height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={decompData}
                        cx="50%"
                        cy="50%"
                        innerRadius={52}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {decompData.map((_, i) => (
                          <Cell
                            key={i}
                            fill={PIE_COLORS[i % PIE_COLORS.length]}
                            fillOpacity={0.88}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        formatter={(value: any, name: any) =>
                          [`${value ?? 0}%`, name] as any
                        }
                        contentStyle={{
                          backgroundColor: "#1E2536",
                          border: `1px solid ${BORDER}`,
                          borderRadius: 6,
                          color: "#F1F5F9",
                          fontSize: 11,
                        }}
                      />
                      <Legend
                        iconType="circle"
                        iconSize={8}
                        formatter={(value: string) => (
                          <span style={{ color: SLATE, fontSize: 10 }}>
                            {value}
                          </span>
                        )}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          </div>

          {/* Methodology note */}
          <div
            className="rounded px-4 py-3 text-xs"
            style={{
              backgroundColor: "rgba(239,68,68,0.05)",
              border: `1px solid rgba(239,68,68,0.15)`,
              color: SLATE,
            }}
          >
            <span style={{ color: RED }} className="font-semibold">
              Methodology:{" "}
            </span>
            Parametric VaR = −N · z · σ · √h &nbsp;|&nbsp; CVaR = −N · φ(z) /
            (1−CL) · σ · √h &nbsp;|&nbsp; Normal distribution assumption. z ={" "}
            {Z_SCORES[confidence]}, h = {horizon}d, σ ={" "}
            {portfolioSigma.toFixed(2)}%
          </div>
        </div>
      </div>
    </div>
  );
}
