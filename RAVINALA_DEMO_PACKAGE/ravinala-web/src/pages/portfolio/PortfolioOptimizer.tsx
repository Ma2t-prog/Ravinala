import { useCallback, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "../../components/ui/index";
import { useIndices } from "../../hooks/useMarketData";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Asset {
  id: string;
  ticker: string;
  expectedReturn: number; // %
  volatility: number; // %
  currentWeight: number; // %
}

interface OptimizationResult {
  weights: number[];
  expectedReturn: number;
  volatility: number;
  sharpeRatio: number;
  equalWeightReturn: number;
  equalWeightVolatility: number;
  equalWeightSharpe: number;
  simulatedPortfolios: SimulatedPortfolio[];
  efficientFrontier: EfficientFrontierPoint[];
  maxSharpePoint: SimulatedPortfolio;
  minVarPoint: SimulatedPortfolio;
  marginalRiskContributions: number[];
}

interface SimulatedPortfolio {
  vol: number;
  ret: number;
  sharpe: number;
  weights: number[];
}

interface EfficientFrontierPoint {
  vol: number;
  ret: number;
}

type OptimizationMethod =
  | "maxSharpe"
  | "minVariance"
  | "riskParity"
  | "equalWeight";

// ─── Constants ────────────────────────────────────────────────────────────────

const PURPLE = "#8B5CF6";
const CYAN = "#00D9FF";
const AMBER = "#F59E0B";
const GREEN = "#10B981";
const ORANGE = "#F97316";
const GOLD = "#FFD700";

const PIE_COLORS = [
  "#8B5CF6",
  "#A78BFA",
  "#7C3AED",
  "#6D28D9",
  "#C4B5FD",
  "#DDD6FE",
  "#4C1D95",
  "#5B21B6",
];

const DEFAULT_ASSETS: Asset[] = [
  {
    id: "1",
    ticker: "AAPL",
    expectedReturn: 15,
    volatility: 25,
    currentWeight: 20,
  },
  {
    id: "2",
    ticker: "MSFT",
    expectedReturn: 12,
    volatility: 22,
    currentWeight: 20,
  },
  {
    id: "3",
    ticker: "GOOGL",
    expectedReturn: 14,
    volatility: 28,
    currentWeight: 15,
  },
  {
    id: "4",
    ticker: "JPM",
    expectedReturn: 10,
    volatility: 20,
    currentWeight: 15,
  },
  {
    id: "5",
    ticker: "GLD",
    expectedReturn: 8,
    volatility: 15,
    currentWeight: 15,
  },
  {
    id: "6",
    ticker: "BND",
    expectedReturn: 5,
    volatility: 6,
    currentWeight: 15,
  },
];

function buildDefaultCorrelation(n: number): number[][] {
  return Array.from({ length: n }, (_, i) =>
    Array.from({ length: n }, (_, j) => (i === j ? 1 : 0.3)),
  );
}

// ─── MVO Math ─────────────────────────────────────────────────────────────────

function portfolioStats(
  weights: number[],
  returns: number[],
  vols: number[],
  corr: number[][],
  rfRate: number,
): { ret: number; vol: number; sharpe: number } {
  const n = weights.length;
  let ret = 0;
  for (let i = 0; i < n; i++) ret += weights[i] * returns[i];

  let variance = 0;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      variance += weights[i] * weights[j] * vols[i] * vols[j] * corr[i][j];
    }
  }
  const vol = Math.sqrt(variance);
  const sharpe = vol > 0 ? (ret - rfRate) / vol : 0;
  return { ret, vol, sharpe };
}

function dirichletRandom(
  n: number,
  minW: number,
  maxW: number,
): number[] | null {
  // Try to generate random weights satisfying bounds
  for (let attempt = 0; attempt < 30; attempt++) {
    const raw = Array.from({ length: n }, () => Math.random());
    const sum = raw.reduce((a, b) => a + b, 0);
    const w = raw.map((x) => x / sum);
    if (w.every((wi) => wi >= minW / 100 - 1e-9 && wi <= maxW / 100 + 1e-9))
      return w;
  }
  // fallback: clamp and renorm
  const raw = Array.from({ length: n }, () => Math.random());
  const sum = raw.reduce((a, b) => a + b, 0);
  let w = raw.map((x) => Math.min(Math.max(x / sum, minW / 100), maxW / 100));
  const ws = w.reduce((a, b) => a + b, 0);
  return w.map((x) => x / ws);
}

function marginalRiskContributions(
  weights: number[],
  vols: number[],
  corr: number[][],
  totalVol: number,
): number[] {
  const n = weights.length;
  return weights.map((wi, i) => {
    let cov_i = 0;
    for (let j = 0; j < n; j++) {
      cov_i += weights[j] * vols[i] * vols[j] * corr[i][j];
    }
    return totalVol > 0 ? (wi * cov_i) / totalVol : 0;
  });
}

function riskParityWeights(
  vols: number[],
  corr: number[][],
  iterations = 200,
): number[] {
  const n = vols.length;
  let w = Array(n).fill(1 / n);
  for (let iter = 0; iter < iterations; iter++) {
    let variance = 0;
    for (let i = 0; i < n; i++)
      for (let j = 0; j < n; j++)
        variance += w[i] * w[j] * vols[i] * vols[j] * corr[i][j];
    const vol = Math.sqrt(variance);
    // marginal risk contributions
    const mrc = w.map((wi, i) => {
      let s = 0;
      for (let j = 0; j < n; j++) s += w[j] * vols[i] * vols[j] * corr[i][j];
      return vol > 0 ? (wi * s) / vol : 0;
    });
    // target: equal risk contribution = vol / n
    const target = vol / n;
    const newW = mrc.map((m, i) => (m > 0 ? w[i] * (target / m) : w[i]));
    const sum = newW.reduce((a, b) => a + b, 0);
    w = newW.map((x) => x / sum);
  }
  return w;
}

function runOptimization(
  assets: Asset[],
  corr: number[][],
  method: OptimizationMethod,
  minWeight: number,
  maxWeight: number,
  rfRate: number,
  _targetReturn: number | null,
): OptimizationResult {
  const n = assets.length;
  const returns = assets.map((a) => a.expectedReturn);
  const vols = assets.map((a) => a.volatility);
  const N_SIM = 10000;

  // Simulate portfolios
  const simulated: SimulatedPortfolio[] = [];
  for (let i = 0; i < N_SIM; i++) {
    const w = dirichletRandom(n, minWeight, maxWeight);
    if (!w) continue;
    const stats = portfolioStats(w, returns, vols, corr, rfRate);
    simulated.push({
      vol: stats.vol,
      ret: stats.ret,
      sharpe: stats.sharpe,
      weights: w,
    });
  }

  // Find extremes
  let maxSharpePoint = simulated[0];
  let minVarPoint = simulated[0];
  for (const p of simulated) {
    if (p.sharpe > maxSharpePoint.sharpe) maxSharpePoint = p;
    if (p.vol < minVarPoint.vol) minVarPoint = p;
  }

  // Build efficient frontier (pareto-optimal: for each vol band, highest return)
  const VOL_BANDS = 60;
  const minVol = Math.min(...simulated.map((p) => p.vol));
  const maxVol = Math.max(...simulated.map((p) => p.vol));
  const bandWidth = (maxVol - minVol) / VOL_BANDS;
  const frontierMap = new Map<number, number>();
  for (const p of simulated) {
    const band = Math.floor((p.vol - minVol) / bandWidth);
    const key = Math.min(band, VOL_BANDS - 1);
    if (!frontierMap.has(key) || frontierMap.get(key)! < p.ret) {
      frontierMap.set(key, p.ret);
    }
  }
  const efficientFrontier: EfficientFrontierPoint[] = Array.from(
    frontierMap.entries(),
  )
    .sort((a, b) => a[0] - b[0])
    .map(([band, ret]) => ({
      vol: minVol + (band + 0.5) * bandWidth,
      ret,
    }));

  // Compute optimal weights based on method
  let optWeights: number[];
  if (method === "maxSharpe") {
    optWeights = maxSharpePoint.weights;
  } else if (method === "minVariance") {
    optWeights = minVarPoint.weights;
  } else if (method === "riskParity") {
    optWeights = riskParityWeights(vols, corr);
  } else {
    // equal weight
    optWeights = Array(n).fill(1 / n);
  }

  const optStats = portfolioStats(optWeights, returns, vols, corr, rfRate);

  // Equal weight benchmark
  const eqW = Array(n).fill(1 / n);
  const eqStats = portfolioStats(eqW, returns, vols, corr, rfRate);

  // Marginal risk contributions
  const mrc = marginalRiskContributions(optWeights, vols, corr, optStats.vol);

  // Downsample simulated for display (max 500 points)
  const step = Math.max(1, Math.floor(simulated.length / 500));
  const displaySim = simulated.filter((_, i) => i % step === 0);

  return {
    weights: optWeights,
    expectedReturn: optStats.ret,
    volatility: optStats.vol,
    sharpeRatio: optStats.sharpe,
    equalWeightReturn: eqStats.ret,
    equalWeightVolatility: eqStats.vol,
    equalWeightSharpe: eqStats.sharpe,
    simulatedPortfolios: displaySim,
    efficientFrontier,
    maxSharpePoint,
    minVarPoint,
    marginalRiskContributions: mrc,
  };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

const inputStyle: React.CSSProperties = {
  background: "#0D1117",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 6,
  color: "#F1F5F9",
  fontFamily: "JetBrains Mono, monospace",
  fontSize: 12,
  padding: "4px 8px",
  width: "100%",
  outline: "none",
};

const labelStyle: React.CSSProperties = {
  color: "#94A3B8",
  fontSize: 11,
  fontFamily: "JetBrains Mono, monospace",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginBottom: 4,
  display: "block",
};

const sectionTitleStyle: React.CSSProperties = {
  color: "#8B5CF6",
  fontFamily: "JetBrains Mono, monospace",
  fontSize: 11,
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.12em",
  marginBottom: 12,
  paddingBottom: 6,
  borderBottom: "1px solid rgba(139,92,246,0.3)",
};

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <div style={sectionTitleStyle}>{children}</div>;
}

// ─── Custom Tooltip for Scatter ───────────────────────────────────────────────

function ScatterTooltipContent({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: SimulatedPortfolio }>;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div
      style={{
        background: "#1E293B",
        border: "1px solid rgba(139,92,246,0.4)",
        borderRadius: 6,
        padding: "8px 12px",
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 11,
      }}
    >
      <div style={{ color: "#94A3B8" }}>
        Vol: <span style={{ color: CYAN }}>{p.vol.toFixed(2)}%</span>
      </div>
      <div style={{ color: "#94A3B8" }}>
        Ret: <span style={{ color: GREEN }}>{p.ret.toFixed(2)}%</span>
      </div>
      <div style={{ color: "#94A3B8" }}>
        Sharpe: <span style={{ color: AMBER }}>{p.sharpe.toFixed(3)}</span>
      </div>
    </div>
  );
}

function PieTooltipContent({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number }>;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div
      style={{
        background: "#1E293B",
        border: "1px solid rgba(139,92,246,0.4)",
        borderRadius: 6,
        padding: "8px 12px",
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 11,
      }}
    >
      <span style={{ color: PURPLE }}>{p.name}: </span>
      <span style={{ color: "#F1F5F9" }}>{p.value.toFixed(1)}%</span>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function PortfolioOptimizer() {
  // ── Live market data ────────────────────────────────────────────────────────
  const { data: indicesData, isLoading: indicesLoading } = useIndices();
  const usingFallback = !indicesData;

  const [assets, setAssets] = useState<Asset[]>(DEFAULT_ASSETS);
  const [corr, setCorr] = useState<number[][]>(() =>
    buildDefaultCorrelation(DEFAULT_ASSETS.length),
  );
  const [method, setMethod] = useState<OptimizationMethod>("maxSharpe");

  // Key market benchmarks for context display
  const keyIndices = useMemo(() => {
    if (!indicesData) return [];
    const symbols = ["^GSPC", "^IXIC", "^DJI", "^RUT"];
    return Object.values(indicesData)
      .flat()
      .filter((idx) => symbols.includes(idx.symbol));
  }, [indicesData]);

  const [minWeight, setMinWeight] = useState(0);
  const [maxWeight, setMaxWeight] = useState(40);
  const [targetReturn, setTargetReturn] = useState<string>("");
  const [rfRate, setRfRate] = useState(5);
  const [longOnly, setLongOnly] = useState(true);
  const [result, setResult] = useState<OptimizationResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  // ── Asset table handlers ──────────────────────────────────────────────────

  const updateAsset = useCallback(
    (id: string, field: keyof Asset, value: string | number) => {
      setAssets((prev) =>
        prev.map((a) => (a.id === id ? { ...a, [field]: value } : a)),
      );
    },
    [],
  );

  const addAsset = useCallback(() => {
    const newId = String(Date.now());
    const newAsset: Asset = {
      id: newId,
      ticker: "NEW",
      expectedReturn: 10,
      volatility: 20,
      currentWeight: 0,
    };
    setAssets((prev) => {
      const next = [...prev, newAsset];
      setCorr(buildDefaultCorrelation(next.length));
      return next;
    });
  }, []);

  const removeAsset = useCallback((id: string) => {
    setAssets((prev) => {
      if (prev.length <= 2) return prev;
      const next = prev.filter((a) => a.id !== id);
      setCorr(buildDefaultCorrelation(next.length));
      return next;
    });
  }, []);

  // ── Correlation matrix handler ────────────────────────────────────────────

  const updateCorr = useCallback((i: number, j: number, val: number) => {
    setCorr((prev) => {
      const next = prev.map((row) => [...row]);
      const clamped = Math.min(1, Math.max(-1, val));
      next[i][j] = clamped;
      next[j][i] = clamped;
      return next;
    });
  }, []);

  // ── Run optimization ──────────────────────────────────────────────────────

  const handleOptimize = useCallback(() => {
    setIsRunning(true);
    setTimeout(() => {
      try {
        const effectiveMin = longOnly ? Math.max(0, minWeight) : minWeight;
        const tr = targetReturn !== "" ? parseFloat(targetReturn) : null;
        const res = runOptimization(
          assets,
          corr,
          method,
          effectiveMin,
          maxWeight,
          rfRate,
          tr,
        );
        setResult(res);
      } finally {
        setIsRunning(false);
      }
    }, 0);
  }, [
    assets,
    corr,
    method,
    minWeight,
    maxWeight,
    rfRate,
    longOnly,
    targetReturn,
  ]);

  // ── Derived display data ──────────────────────────────────────────────────

  const pieData = result
    ? assets
        .map((a, i) => ({
          name: a.ticker,
          value: parseFloat((result.weights[i] * 100).toFixed(2)),
        }))
        .filter((d) => d.value > 0.1)
    : [];

  const weightsComparisonData = assets.map((a, i) => ({
    ticker: a.ticker,
    current: parseFloat(a.currentWeight.toFixed(1)),
    optimal: result ? parseFloat((result.weights[i] * 100).toFixed(1)) : 0,
  }));

  const riskDecompData = result
    ? assets.map((a, i) => ({
        ticker: a.ticker,
        mrc: parseFloat((result.marginalRiskContributions[i] * 100).toFixed(3)),
      }))
    : [];

  const currentPortfolioStats = (() => {
    const totalW = assets.reduce((s, a) => s + a.currentWeight, 0);
    if (totalW === 0) return null;
    const w = assets.map((a) => a.currentWeight / totalW / 100);
    const returns = assets.map((a) => a.expectedReturn);
    const vols = assets.map((a) => a.volatility);
    return portfolioStats(w, returns, vols, corr, rfRate);
  })();

  // ─── Render ───────────────────────────────────────────────────────────────

  return (
    <div
      style={{
        color: "#F1F5F9",
        fontFamily: "JetBrains Mono, monospace",
        minHeight: "100vh",
        padding: "0 0 40px",
      }}
    >
      {/* Fallback Banner */}
      {usingFallback && !indicesLoading && (
        <div
          style={{
            backgroundColor: "rgba(245,158,11,0.1)",
            border: "1px solid rgba(245,158,11,0.3)",
            borderRadius: 6,
            padding: "8px 16px",
            marginBottom: 16,
            color: "#F59E0B",
            fontSize: 13,
            fontFamily: "JetBrains Mono, monospace",
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
              <div style={{ fontSize: 10, color: "#64748B" }}>{idx.name}</div>
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

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontSize: 22,
            fontWeight: 700,
            color: "#F1F5F9",
            margin: 0,
            letterSpacing: "-0.01em",
          }}
        >
          Portfolio Optimizer
        </h1>
        <p
          style={{
            color: "#94A3B8",
            fontSize: 12,
            margin: "4px 0 0",
            letterSpacing: "0.04em",
          }}
        >
          Mean-Variance Optimization · Markowitz Framework · Monte Carlo
          Simulation
        </p>
      </div>

      {/* Two-column layout */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "420px 1fr",
          gap: 20,
          alignItems: "start",
        }}
      >
        {/* ── LEFT PANEL ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Asset Universe */}
          <Card>
            <SectionTitle>Asset Universe</SectionTitle>

            {/* Table */}
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 12,
                }}
              >
                <thead>
                  <tr>
                    {[
                      "Ticker",
                      "Exp. Return %",
                      "Volatility %",
                      "Weight %",
                      "",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          color: "#64748B",
                          fontSize: 10,
                          textAlign: "left",
                          padding: "4px 6px",
                          fontWeight: 600,
                          letterSpacing: "0.05em",
                          textTransform: "uppercase",
                          borderBottom: "1px solid rgba(51,65,85,0.4)",
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {assets.map((asset) => (
                    <tr
                      key={asset.id}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td style={{ padding: "4px 6px" }}>
                        <input
                          style={{
                            ...inputStyle,
                            width: 60,
                            textTransform: "uppercase",
                          }}
                          value={asset.ticker}
                          onChange={(e) =>
                            updateAsset(
                              asset.id,
                              "ticker",
                              e.target.value.toUpperCase(),
                            )
                          }
                        />
                      </td>
                      <td style={{ padding: "4px 6px" }}>
                        <input
                          style={{ ...inputStyle, width: 70 }}
                          type="number"
                          value={asset.expectedReturn}
                          onChange={(e) =>
                            updateAsset(
                              asset.id,
                              "expectedReturn",
                              parseFloat(e.target.value) || 0,
                            )
                          }
                        />
                      </td>
                      <td style={{ padding: "4px 6px" }}>
                        <input
                          style={{ ...inputStyle, width: 70 }}
                          type="number"
                          value={asset.volatility}
                          onChange={(e) =>
                            updateAsset(
                              asset.id,
                              "volatility",
                              parseFloat(e.target.value) || 0,
                            )
                          }
                        />
                      </td>
                      <td style={{ padding: "4px 6px" }}>
                        <input
                          style={{ ...inputStyle, width: 60 }}
                          type="number"
                          value={asset.currentWeight}
                          onChange={(e) =>
                            updateAsset(
                              asset.id,
                              "currentWeight",
                              parseFloat(e.target.value) || 0,
                            )
                          }
                        />
                      </td>
                      <td style={{ padding: "4px 6px" }}>
                        <button
                          onClick={() => removeAsset(asset.id)}
                          style={{
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            color: "#64748B",
                            fontSize: 14,
                            padding: "0 4px",
                            lineHeight: 1,
                          }}
                          title="Remove"
                        >
                          ×
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              onClick={addAsset}
              style={{
                marginTop: 12,
                background: "rgba(139,92,246,0.1)",
                border: "1px solid rgba(139,92,246,0.4)",
                borderRadius: 6,
                color: PURPLE,
                cursor: "pointer",
                fontSize: 11,
                fontFamily: "JetBrains Mono, monospace",
                padding: "6px 14px",
                letterSpacing: "0.05em",
                fontWeight: 600,
              }}
            >
              + ADD ASSET
            </button>

            {/* Correlation Matrix */}
            <div style={{ marginTop: 20 }}>
              <div
                style={{
                  color: "#94A3B8",
                  fontSize: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  marginBottom: 8,
                  fontWeight: 600,
                }}
              >
                Correlation Matrix
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ borderCollapse: "collapse", fontSize: 11 }}>
                  <thead>
                    <tr>
                      <th
                        style={{
                          padding: "3px 5px",
                          color: "#475569",
                          fontSize: 10,
                        }}
                      ></th>
                      {assets.map((a) => (
                        <th
                          key={a.id}
                          style={{
                            padding: "3px 5px",
                            color: "#64748B",
                            fontSize: 10,
                            fontWeight: 600,
                          }}
                        >
                          {a.ticker}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {assets.map((rowAsset, i) => (
                      <tr key={rowAsset.id}>
                        <td
                          style={{
                            padding: "3px 5px",
                            color: "#64748B",
                            fontSize: 10,
                            fontWeight: 600,
                          }}
                        >
                          {rowAsset.ticker}
                        </td>
                        {assets.map((_, j) => (
                          <td key={j} style={{ padding: "2px 3px" }}>
                            {i === j ? (
                              <div
                                style={{
                                  width: 44,
                                  height: 24,
                                  background: "rgba(139,92,246,0.15)",
                                  border: "1px solid rgba(139,92,246,0.3)",
                                  borderRadius: 4,
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "center",
                                  color: PURPLE,
                                  fontSize: 11,
                                  fontWeight: 700,
                                }}
                              >
                                1.00
                              </div>
                            ) : (
                              <input
                                style={{
                                  ...inputStyle,
                                  width: 44,
                                  height: 24,
                                  padding: "2px 4px",
                                  fontSize: 11,
                                  textAlign: "center",
                                }}
                                type="number"
                                step={0.05}
                                min={-1}
                                max={1}
                                value={corr[i][j]}
                                onChange={(e) =>
                                  updateCorr(
                                    i,
                                    j,
                                    parseFloat(e.target.value) || 0,
                                  )
                                }
                              />
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </Card>

          {/* Optimization Method */}
          <Card>
            <SectionTitle>Optimization Method</SectionTitle>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {(
                [
                  ["maxSharpe", "Max Sharpe Ratio"],
                  ["minVariance", "Min Variance"],
                  ["riskParity", "Risk Parity"],
                  ["equalWeight", "Equal Weight"],
                ] as [OptimizationMethod, string][]
              ).map(([val, label]) => (
                <label
                  key={val}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    cursor: "pointer",
                  }}
                >
                  <div style={{ position: "relative", width: 16, height: 16 }}>
                    <input
                      type="radio"
                      name="method"
                      value={val}
                      checked={method === val}
                      onChange={() => setMethod(val)}
                      style={{
                        position: "absolute",
                        opacity: 0,
                        width: "100%",
                        height: "100%",
                        cursor: "pointer",
                        margin: 0,
                      }}
                    />
                    <div
                      style={{
                        width: 16,
                        height: 16,
                        borderRadius: "50%",
                        border: `2px solid ${method === val ? PURPLE : "#475569"}`,
                        background:
                          method === val
                            ? "rgba(139,92,246,0.2)"
                            : "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      {method === val && (
                        <div
                          style={{
                            width: 7,
                            height: 7,
                            borderRadius: "50%",
                            background: PURPLE,
                          }}
                        />
                      )}
                    </div>
                  </div>
                  <span
                    style={{
                      color: method === val ? "#F1F5F9" : "#94A3B8",
                      fontSize: 12,
                    }}
                  >
                    {label}
                  </span>
                </label>
              ))}
            </div>
          </Card>

          {/* Constraints */}
          <Card>
            <SectionTitle>Constraints</SectionTitle>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
              }}
            >
              <div>
                <label style={labelStyle}>Min Weight / Asset (%)</label>
                <input
                  style={inputStyle}
                  type="number"
                  value={minWeight}
                  min={-100}
                  max={100}
                  onChange={(e) =>
                    setMinWeight(parseFloat(e.target.value) || 0)
                  }
                />
              </div>
              <div>
                <label style={labelStyle}>Max Weight / Asset (%)</label>
                <input
                  style={inputStyle}
                  type="number"
                  value={maxWeight}
                  min={1}
                  max={100}
                  onChange={(e) =>
                    setMaxWeight(parseFloat(e.target.value) || 100)
                  }
                />
              </div>
              <div>
                <label style={labelStyle}>Target Return (% optional)</label>
                <input
                  style={inputStyle}
                  type="number"
                  value={targetReturn}
                  placeholder="—"
                  onChange={(e) => setTargetReturn(e.target.value)}
                />
              </div>
              <div>
                <label style={labelStyle}>Risk-Free Rate (%)</label>
                <input
                  style={inputStyle}
                  type="number"
                  value={rfRate}
                  step={0.1}
                  onChange={(e) => setRfRate(parseFloat(e.target.value) || 0)}
                />
              </div>
            </div>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginTop: 14,
                cursor: "pointer",
              }}
            >
              <div
                onClick={() => setLongOnly((v) => !v)}
                style={{
                  width: 36,
                  height: 20,
                  borderRadius: 10,
                  background: longOnly ? PURPLE : "#374151",
                  position: "relative",
                  cursor: "pointer",
                  transition: "background 0.2s",
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    width: 14,
                    height: 14,
                    borderRadius: "50%",
                    background: "#F1F5F9",
                    position: "absolute",
                    top: 3,
                    left: longOnly ? 19 : 3,
                    transition: "left 0.2s",
                  }}
                />
              </div>
              <span style={{ color: "#94A3B8", fontSize: 12 }}>
                Long-only (no short positions)
              </span>
            </label>
          </Card>

          {/* Run button */}
          <button
            onClick={handleOptimize}
            disabled={isRunning}
            style={{
              background: isRunning
                ? "rgba(139,92,246,0.3)"
                : "linear-gradient(135deg, #7C3AED 0%, #8B5CF6 50%, #A78BFA 100%)",
              border: "none",
              borderRadius: 8,
              color: "#FFFFFF",
              cursor: isRunning ? "not-allowed" : "pointer",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13,
              fontWeight: 700,
              letterSpacing: "0.1em",
              padding: "14px 24px",
              textTransform: "uppercase",
              boxShadow: isRunning ? "none" : "0 4px 24px rgba(139,92,246,0.4)",
              transition: "all 0.2s",
            }}
          >
            {isRunning ? "⟳ OPTIMIZING…" : "▶ RUN OPTIMIZATION"}
          </button>
        </div>

        {/* ── RIGHT PANEL ── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {!result ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                minHeight: 400,
                color: "#475569",
                gap: 12,
              }}
            >
              <div style={{ fontSize: 48 }}>◈</div>
              <div
                style={{
                  fontSize: 13,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                Configure parameters and run optimization
              </div>
            </div>
          ) : (
            <>
              {/* ── Optimal Portfolio Stats ── */}
              <Card>
                <SectionTitle>Optimal Portfolio</SectionTitle>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: 12,
                    marginBottom: 16,
                  }}
                >
                  <div
                    style={{
                      textAlign: "center",
                      padding: "12px 8px",
                      background: "rgba(16,185,129,0.05)",
                      border: "1px solid rgba(16,185,129,0.2)",
                      borderRadius: 8,
                    }}
                  >
                    <div
                      style={{
                        color: "#64748B",
                        fontSize: 10,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        marginBottom: 6,
                      }}
                    >
                      Expected Return
                    </div>
                    <div
                      style={{ color: GREEN, fontSize: 26, fontWeight: 700 }}
                    >
                      {result.expectedReturn.toFixed(2)}%
                    </div>
                    <div
                      style={{ color: "#475569", fontSize: 10, marginTop: 4 }}
                    >
                      {result.expectedReturn - result.equalWeightReturn >= 0
                        ? "+"
                        : ""}
                      {(
                        result.expectedReturn - result.equalWeightReturn
                      ).toFixed(2)}
                      % vs EW
                    </div>
                  </div>
                  <div
                    style={{
                      textAlign: "center",
                      padding: "12px 8px",
                      background: "rgba(245,158,11,0.05)",
                      border: "1px solid rgba(245,158,11,0.2)",
                      borderRadius: 8,
                    }}
                  >
                    <div
                      style={{
                        color: "#64748B",
                        fontSize: 10,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        marginBottom: 6,
                      }}
                    >
                      Portfolio Volatility
                    </div>
                    <div
                      style={{ color: AMBER, fontSize: 26, fontWeight: 700 }}
                    >
                      {result.volatility.toFixed(2)}%
                    </div>
                    <div
                      style={{ color: "#475569", fontSize: 10, marginTop: 4 }}
                    >
                      {result.volatility - result.equalWeightVolatility >= 0
                        ? "+"
                        : ""}
                      {(
                        result.volatility - result.equalWeightVolatility
                      ).toFixed(2)}
                      % vs EW
                    </div>
                  </div>
                  <div
                    style={{
                      textAlign: "center",
                      padding: "12px 8px",
                      background: "rgba(0,217,255,0.05)",
                      border: "1px solid rgba(0,217,255,0.2)",
                      borderRadius: 8,
                    }}
                  >
                    <div
                      style={{
                        color: "#64748B",
                        fontSize: 10,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        marginBottom: 6,
                      }}
                    >
                      Sharpe Ratio
                    </div>
                    <div style={{ color: CYAN, fontSize: 26, fontWeight: 700 }}>
                      {result.sharpeRatio.toFixed(3)}
                    </div>
                    <div
                      style={{ color: "#475569", fontSize: 10, marginTop: 4 }}
                    >
                      {result.sharpeRatio - result.equalWeightSharpe >= 0
                        ? "+"
                        : ""}
                      {(result.sharpeRatio - result.equalWeightSharpe).toFixed(
                        3,
                      )}{" "}
                      vs EW
                    </div>
                  </div>
                </div>

                {/* Weights summary */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {assets.map((a, i) =>
                    result.weights[i] * 100 > 0.1 ? (
                      <div
                        key={a.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                          background: "rgba(139,92,246,0.08)",
                          border: "1px solid rgba(139,92,246,0.25)",
                          borderRadius: 6,
                          padding: "4px 10px",
                          fontSize: 11,
                        }}
                      >
                        <span style={{ color: PURPLE, fontWeight: 700 }}>
                          {a.ticker}
                        </span>
                        <span style={{ color: "#94A3B8" }}>
                          {(result.weights[i] * 100).toFixed(1)}%
                        </span>
                      </div>
                    ) : null,
                  )}
                </div>
              </Card>

              {/* ── Charts row 1: Pie + Efficient Frontier ── */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 16,
                }}
              >
                {/* Allocation Pie */}
                <Card>
                  <SectionTitle>Asset Allocation</SectionTitle>
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie
                        data={pieData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                        label={({ name, value }) =>
                          `${name} ${value.toFixed(1)}%`
                        }
                        labelLine={{ stroke: "#475569", strokeWidth: 1 }}
                      >
                        {pieData.map((_, idx) => (
                          <Cell
                            key={idx}
                            fill={PIE_COLORS[idx % PIE_COLORS.length]}
                            stroke="rgba(0,0,0,0.3)"
                            strokeWidth={1}
                          />
                        ))}
                      </Pie>
                      <Tooltip content={<PieTooltipContent />} />
                    </PieChart>
                  </ResponsiveContainer>
                </Card>

                {/* Weights Comparison Bar */}
                <Card>
                  <SectionTitle>Weights Comparison</SectionTitle>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart
                      data={weightsComparisonData}
                      margin={{ top: 8, right: 8, bottom: 8, left: -12 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(51,65,85,0.3)"
                      />
                      <XAxis
                        dataKey="ticker"
                        tick={{
                          fill: "#94A3B8",
                          fontSize: 10,
                          fontFamily: "JetBrains Mono, monospace",
                        }}
                      />
                      <YAxis
                        tick={{
                          fill: "#64748B",
                          fontSize: 10,
                          fontFamily: "JetBrains Mono, monospace",
                        }}
                        unit="%"
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#1E293B",
                          border: "1px solid rgba(139,92,246,0.4)",
                          borderRadius: 6,
                          fontFamily: "JetBrains Mono, monospace",
                          fontSize: 11,
                        }}
                        labelStyle={{ color: "#F1F5F9" }}
                        itemStyle={{ color: "#94A3B8" }}
                      />
                      <Legend
                        wrapperStyle={{
                          fontSize: 10,
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#94A3B8",
                        }}
                      />
                      <Bar
                        dataKey="current"
                        name="Current"
                        fill="#475569"
                        radius={[2, 2, 0, 0]}
                      />
                      <Bar
                        dataKey="optimal"
                        name="Optimal"
                        fill={PURPLE}
                        radius={[2, 2, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              </div>

              {/* ── Efficient Frontier ── */}
              <Card>
                <SectionTitle>Efficient Frontier</SectionTitle>
                <ResponsiveContainer width="100%" height={320}>
                  <ScatterChart
                    margin={{ top: 16, right: 24, bottom: 24, left: 8 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.25)"
                    />
                    <XAxis
                      type="number"
                      dataKey="vol"
                      name="Volatility"
                      unit="%"
                      tick={{
                        fill: "#64748B",
                        fontSize: 10,
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                      label={{
                        value: "Volatility (%)",
                        position: "insideBottom",
                        offset: -10,
                        fill: "#64748B",
                        fontSize: 10,
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                    />
                    <YAxis
                      type="number"
                      dataKey="ret"
                      name="Return"
                      unit="%"
                      tick={{
                        fill: "#64748B",
                        fontSize: 10,
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                      label={{
                        value: "Return (%)",
                        angle: -90,
                        position: "insideLeft",
                        offset: 16,
                        fill: "#64748B",
                        fontSize: 10,
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                    />
                    <Tooltip content={<ScatterTooltipContent />} />

                    {/* Simulated portfolios cloud */}
                    <Scatter
                      name="Simulated"
                      data={result.simulatedPortfolios}
                      fill="rgba(71,85,105,0.5)"
                      r={2}
                    />

                    {/* Efficient frontier line rendered as scatter with line */}
                    <Scatter
                      name="Frontier"
                      data={result.efficientFrontier}
                      fill={CYAN}
                      line={{ stroke: CYAN, strokeWidth: 2 }}
                      r={0}
                    />

                    {/* Max Sharpe */}
                    <Scatter
                      name="Max Sharpe"
                      data={[result.maxSharpePoint]}
                      fill={GOLD}
                      r={8}
                      shape="star"
                    />

                    {/* Min Variance */}
                    <Scatter
                      name="Min Variance"
                      data={[result.minVarPoint]}
                      fill={PURPLE}
                      r={7}
                    />

                    {/* Current Portfolio */}
                    {currentPortfolioStats && (
                      <Scatter
                        name="Current"
                        data={[
                          {
                            vol: currentPortfolioStats.vol,
                            ret: currentPortfolioStats.ret,
                            sharpe: currentPortfolioStats.sharpe,
                            weights: [],
                          },
                        ]}
                        fill={ORANGE}
                        r={7}
                      />
                    )}

                    <Legend
                      wrapperStyle={{
                        fontSize: 10,
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#94A3B8",
                        paddingTop: 8,
                      }}
                    />
                  </ScatterChart>
                </ResponsiveContainer>

                {/* Legend explanations */}
                <div
                  style={{
                    display: "flex",
                    gap: 16,
                    flexWrap: "wrap",
                    marginTop: 8,
                    paddingTop: 8,
                    borderTop: "1px solid rgba(51,65,85,0.3)",
                  }}
                >
                  {[
                    { color: GOLD, label: "Max Sharpe" },
                    { color: PURPLE, label: "Min Variance" },
                    { color: ORANGE, label: "Current Portfolio" },
                    { color: CYAN, label: "Efficient Frontier" },
                  ].map(({ color, label }) => (
                    <div
                      key={label}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        fontSize: 11,
                      }}
                    >
                      <div
                        style={{
                          width: 10,
                          height: 10,
                          borderRadius: "50%",
                          background: color,
                        }}
                      />
                      <span style={{ color: "#94A3B8" }}>{label}</span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* ── Risk Decomposition ── */}
              <Card>
                <SectionTitle>
                  Risk Decomposition — Marginal Risk Contribution
                </SectionTitle>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    layout="vertical"
                    data={riskDecompData}
                    margin={{ top: 4, right: 40, bottom: 4, left: 20 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                      horizontal={false}
                    />
                    <XAxis
                      type="number"
                      unit="%"
                      tick={{
                        fill: "#64748B",
                        fontSize: 10,
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                    />
                    <YAxis
                      type="category"
                      dataKey="ticker"
                      tick={{
                        fill: "#94A3B8",
                        fontSize: 11,
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                      width={44}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#1E293B",
                        border: "1px solid rgba(139,92,246,0.4)",
                        borderRadius: 6,
                        fontFamily: "JetBrains Mono, monospace",
                        fontSize: 11,
                      }}
                      labelStyle={{ color: "#F1F5F9" }}
                      formatter={(v) => [
                        `${typeof v === "number" ? v.toFixed(3) : v}%`,
                        "MRC",
                      ]}
                    />
                    <ReferenceLine x={0} stroke="rgba(51,65,85,0.6)" />
                    <Bar
                      dataKey="mrc"
                      name="Marginal Risk Contribution"
                      radius={[0, 3, 3, 0]}
                    >
                      {riskDecompData.map((entry, idx) => (
                        <Cell
                          key={idx}
                          fill={
                            entry.mrc >= 0
                              ? `rgba(139,92,246,${0.4 + 0.6 * Math.min(1, entry.mrc / (Math.max(...riskDecompData.map((d) => Math.abs(d.mrc))) || 1))})`
                              : `rgba(239,68,68,0.6)`
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
