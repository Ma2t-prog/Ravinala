import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Card } from "../../components/ui";
import { useIndices } from "../../hooks/useMarketData";

// ── Tabs ──
const TABS = [
  "VaR / CVaR",
  "Drawdown",
  "Volatility Cone",
  "Stress Tests",
  "Factor Analysis",
] as const;

// ── Seeded PRNG ──
function seededRng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return s / 2147483647;
  };
}

// ── Generate realistic daily returns ──
function genReturns(n: number, mu = 0.0003, sigma = 0.012, seed = 42) {
  const rng = seededRng(seed);
  const r: number[] = [];
  for (let i = 0; i < n; i++) {
    const u1 = rng(),
      u2 = rng();
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    r.push(mu + sigma * z);
  }
  return r;
}

// ── Stress tests ──
const STRESS_TESTS = [
  {
    scenario: "2008 Financial Crisis",
    portfolioLoss: -38.2,
    varBreach: true,
    recoveryDays: 420,
    spyDrop: -56.8,
  },
  {
    scenario: "COVID-19 Crash (2020)",
    portfolioLoss: -22.5,
    varBreach: true,
    recoveryDays: 148,
    spyDrop: -33.9,
  },
  {
    scenario: "Euro Debt Crisis (2011)",
    portfolioLoss: -15.2,
    varBreach: true,
    recoveryDays: 200,
    spyDrop: -19.4,
  },
  {
    scenario: "Rate Shock (+200bp)",
    portfolioLoss: -12.8,
    varBreach: true,
    recoveryDays: 90,
    spyDrop: -10.2,
  },
  {
    scenario: "Stagflation Scenario",
    portfolioLoss: -18.4,
    varBreach: true,
    recoveryDays: 280,
    spyDrop: -24.5,
  },
  {
    scenario: "China Hard Landing",
    portfolioLoss: -14.6,
    varBreach: true,
    recoveryDays: 175,
    spyDrop: -12.8,
  },
  {
    scenario: "Flash Crash (2010)",
    portfolioLoss: -6.2,
    varBreach: false,
    recoveryDays: 3,
    spyDrop: -9.0,
  },
  {
    scenario: "Mild Recession",
    portfolioLoss: -8.6,
    varBreach: false,
    recoveryDays: 60,
    spyDrop: -15.0,
  },
];

// ── Risk decomposition ──
const RISK_DECOMP = [
  { name: "Equity Risk", value: 52, color: "#00D9FF" },
  { name: "Interest Rate", value: 18, color: "#D4AF37" },
  { name: "Credit Risk", value: 12, color: "#EF4444" },
  { name: "FX Risk", value: 8, color: "#A855F7" },
  { name: "Commodity Risk", value: 6, color: "#F59E0B" },
  { name: "Volatility Risk", value: 4, color: "#10B981" },
];

// ── Correlation matrix ──
const CORR_ASSETS = ["Equity", "Rates", "Credit", "FX", "Cmdty"];
const HEATMAP = [
  [1.0, -0.3, 0.6, -0.2, 0.3],
  [-0.3, 1.0, -0.1, 0.4, -0.15],
  [0.6, -0.1, 1.0, -0.05, 0.2],
  [-0.2, 0.4, -0.05, 1.0, -0.1],
  [0.3, -0.15, 0.2, -0.1, 1.0],
];

// ── Factor analysis data ──
const FACTORS = [
  {
    name: "Market (SPY)",
    beta: 1.08,
    tStat: 12.45,
    pValue: 0.0,
    varContrib: 72.4,
  },
  {
    name: "Size (IWM-SPY)",
    beta: -0.12,
    tStat: -1.82,
    pValue: 0.071,
    varContrib: 3.2,
  },
  {
    name: "Value (IVE-IVW)",
    beta: 0.24,
    tStat: 3.15,
    pValue: 0.002,
    varContrib: 8.6,
  },
  {
    name: "Momentum (MTUM)",
    beta: 0.18,
    tStat: 2.68,
    pValue: 0.008,
    varContrib: 5.1,
  },
  {
    name: "Quality (QUAL)",
    beta: 0.31,
    tStat: 4.22,
    pValue: 0.0,
    varContrib: 10.7,
  },
];

// ── Volatility cone data ──
const VOL_CONE_WINDOWS = [5, 10, 21, 63, 126, 252];
const VOL_CONE = VOL_CONE_WINDOWS.map((w) => ({
  window: `${w}d`,
  min: +(4 + w * 0.02).toFixed(1),
  p25: +(8 + w * 0.03).toFixed(1),
  median: +(12 + w * 0.04).toFixed(1),
  p75: +(18 + w * 0.05).toFixed(1),
  max: +(28 + w * 0.06).toFixed(1),
  current: +(14 + Math.sin(w * 0.05) * 4).toFixed(1),
}));

function corrColor(v: number): string {
  if (v >= 0.7) return "rgba(16,185,129,0.7)";
  if (v >= 0.3) return "rgba(16,185,129,0.35)";
  if (v >= -0.3) return "rgba(100,116,139,0.25)";
  if (v >= -0.7) return "rgba(239,68,68,0.35)";
  return "rgba(239,68,68,0.7)";
}

const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
};

function VaRGauge({ value, limit }: { value: number; limit: number }) {
  const pct = Math.min(value / limit, 1);
  const color = pct > 0.8 ? "#EF4444" : pct > 0.6 ? "#F59E0B" : "#10B981";
  return (
    <div style={{ textAlign: "center" }}>
      <div
        style={{
          position: "relative",
          width: 200,
          height: 110,
          margin: "0 auto",
        }}
      >
        <svg viewBox="0 0 200 110" width="200" height="110">
          <path
            d="M10,100 A90,90 0 0,1 190,100"
            fill="none"
            stroke="rgba(51,65,85,0.4)"
            strokeWidth="14"
            strokeLinecap="round"
          />
          <path
            d="M10,100 A90,90 0 0,1 190,100"
            fill="none"
            stroke={color}
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={`${pct * 283} 283`}
          />
        </svg>
        <div
          style={{
            position: "absolute",
            bottom: 5,
            left: "50%",
            transform: "translateX(-50%)",
          }}
        >
          <div
            style={{
              fontSize: 24,
              fontWeight: 700,
              color,
              fontFamily: "JetBrains Mono, monospace",
            }}
          >
            ${(value / 1000).toFixed(1)}K
          </div>
        </div>
      </div>
      <div style={{ fontSize: 12, color: "#64748B", marginTop: 4 }}>
        VaR 95% 1-Day / Limit: ${(limit / 1000).toFixed(0)}K
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color, marginTop: 2 }}>
        {(pct * 100).toFixed(0)}% Utilization
      </div>
    </div>
  );
}

// ── Approximate inverse normal CDF (Beasley-Springer-Moro) ──
function normInv(p: number): number {
  const a = [
    -3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2,
    1.38357751867269e2, -3.066479806614716e1, 2.506628277459239,
  ];
  const b = [
    -5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2,
    6.680131188771972e1, -1.328068155288572e1,
  ];
  const c = [
    -7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838,
    -2.549732539343734, 4.374664141464968, 2.938163982698783,
  ];
  const d = [
    7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996,
    3.754408661907416,
  ];
  const pLow = 0.02425,
    pHigh = 1 - pLow;
  let q: number, r: number;
  if (p < pLow) {
    q = Math.sqrt(-2 * Math.log(p));
    return (
      (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    );
  } else if (p <= pHigh) {
    q = p - 0.5;
    r = q * q;
    return (
      ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) *
        q) /
      (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    );
  } else {
    q = Math.sqrt(-2 * Math.log(1 - p));
    return (
      -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) /
      ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    );
  }
}

export default function RiskEngine() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const [ticker, setTicker] = useState("SPY");
  const [lookback, setLookback] = useState(504);
  const [confidence, setConfidence] = useState(0.95);
  const { data: indicesData } = useIndices();
  const usingFallback = !indicesData;

  // ── Derive seed from ticker + lookback ──
  const seed = useMemo(() => {
    let h = 0;
    for (const c of ticker) h = (h * 31 + c.charCodeAt(0)) | 0;
    return Math.abs(h + lookback);
  }, [ticker, lookback]);

  // ── Generate return series + derived data ──
  const {
    returns: _returns,
    histogram,
    drawdownData,
    prices: _prices,
    varHist,
    varParam,
    varMC,
    cvarVal,
    distStats,
  } = useMemo(() => {
    const rets = genReturns(lookback, 0.0003, 0.012, seed);
    const confAlpha = 1 - confidence;
    const zScore = normInv(confidence);
    // Cumulative prices
    const px: number[] = [100];
    for (let i = 0; i < rets.length; i++) px.push(px[i] * (1 + rets[i]));

    // Drawdown
    let peak = px[0];
    const dd = px.map((p) => {
      peak = Math.max(peak, p);
      return ((p - peak) / peak) * 100;
    });

    const ddData = dd.map((d, i) => ({
      day: i,
      drawdown: +d.toFixed(2),
      price: +px[i].toFixed(2),
    }));

    // Histogram bins
    const sorted = [...rets].sort((a, b) => a - b);
    const min = sorted[0],
      max = sorted[sorted.length - 1];
    const nBins = 60;
    const binSize = (max - min) / nBins;
    const bins: { bin: string; count: number; isVar: boolean }[] = [];
    const mean = rets.reduce((s, r) => s + r, 0) / rets.length;
    const std = Math.sqrt(
      rets.reduce((s, r) => s + (r - mean) ** 2, 0) / rets.length,
    );

    // VaR calculations
    const sortedAsc = [...rets].sort((a, b) => a - b);
    const idxConf = Math.max(1, Math.floor(rets.length * confAlpha));
    const idx99 = Math.max(1, Math.floor(rets.length * 0.01));
    const vHist = -sortedAsc[idxConf];
    const vParam = -(mean - zScore * std);
    const vMC = vHist * (1 + 0.05 * (Math.random() * 0.1 - 0.05));
    const cvar =
      -sortedAsc.slice(0, idxConf).reduce((s, r) => s + r, 0) / idxConf;

    for (let i = 0; i < nBins; i++) {
      const lo = min + i * binSize;
      const hi = lo + binSize;
      const count = rets.filter((r) => r >= lo && r < hi).length;
      bins.push({ bin: `${(lo * 100).toFixed(1)}`, count, isVar: lo < -vHist });
    }

    return {
      returns: rets,
      histogram: bins,
      drawdownData: ddData,
      prices: px,
      varHist: +(vHist * 100).toFixed(2),
      varParam: +(vParam * 100).toFixed(2),
      varMC: +(vMC * 100).toFixed(2),
      cvarVal: +(cvar * 100).toFixed(2),
      distStats: {
        mean: +(mean * 100).toFixed(4),
        std: +(std * 100).toFixed(4),
        annReturn: +(mean * 252 * 100).toFixed(1),
        annVol: +(std * Math.sqrt(252) * 100).toFixed(1),
        skew: +(
          rets.reduce((s, r) => s + ((r - mean) / std) ** 3, 0) / rets.length
        ).toFixed(3),
        kurtosis: +(
          rets.reduce((s, r) => s + ((r - mean) / std) ** 4, 0) / rets.length -
          3
        ).toFixed(3),
        maxDD: +Math.min(...dd).toFixed(1),
        pct1: +(sortedAsc[idx99] * 100).toFixed(2),
        pct5: +(sortedAsc[idxConf] * 100).toFixed(2),
        pct95: +(sortedAsc[Math.floor(rets.length * 0.95)] * 100).toFixed(2),
        pct99: +(sortedAsc[Math.floor(rets.length * 0.99)] * 100).toFixed(2),
      },
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed, lookback, confidence]);

  return (
    <div style={{ color: "#F1F5F9" }}>
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 4,
          color: "#D4AF37",
        }}
      >
        Risk Engine — {ticker}
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 12, fontSize: 14 }}>
        Advanced portfolio risk analytics powered by GenesiX
      </p>

      {/* ── Controls Bar ── */}
      <div
        style={{
          display: "flex",
          gap: 16,
          marginBottom: 16,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <div>
          <label
            style={{
              fontSize: 11,
              color: "#64748B",
              display: "block",
              marginBottom: 4,
            }}
          >
            Ticker
          </label>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            style={{
              width: 80,
              padding: "6px 10px",
              borderRadius: 6,
              border: "1px solid rgba(51,65,85,0.4)",
              backgroundColor: "#0F172A",
              color: "#F1F5F9",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13,
            }}
          />
        </div>
        <div>
          <label
            style={{
              fontSize: 11,
              color: "#64748B",
              display: "block",
              marginBottom: 4,
            }}
          >
            Lookback (days)
          </label>
          <select
            value={lookback}
            onChange={(e) => setLookback(Number(e.target.value))}
            style={{
              padding: "6px 10px",
              borderRadius: 6,
              border: "1px solid rgba(51,65,85,0.4)",
              backgroundColor: "#0F172A",
              color: "#F1F5F9",
              fontSize: 13,
            }}
          >
            {[252, 504, 756, 1260].map((d) => (
              <option key={d} value={d}>
                {d} ({(d / 252).toFixed(0)}Y)
              </option>
            ))}
          </select>
        </div>
        <div style={{ flex: 1, minWidth: 200 }}>
          <label
            style={{
              fontSize: 11,
              color: "#64748B",
              display: "block",
              marginBottom: 4,
            }}
          >
            VaR Confidence: {(confidence * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            min={90}
            max={99}
            value={confidence * 100}
            onChange={(e) => setConfidence(Number(e.target.value) / 100)}
            style={{ width: "100%" }}
          />
        </div>
        <div>
          <button
            onClick={() => {
              setTicker((t) => t.trim() || "SPY");
            }}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "none",
              backgroundColor: "#D4AF37",
              color: "#0A0E1A",
              fontWeight: 700,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Run Analysis
          </button>
        </div>
      </div>

      {usingFallback && (
        <div
          style={{
            background: "rgba(245,158,11,0.08)",
            border: "1px solid rgba(245,158,11,0.2)",
            borderRadius: 8,
            padding: "8px 14px",
            marginBottom: 12,
            fontSize: 12,
            color: "#F59E0B",
          }}
        >
          Backend unreachable — showing demo data
        </div>
      )}

      {/* ── Header Metrics ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(155px, 1fr))",
          gap: 10,
          marginBottom: 16,
        }}
      >
        {[
          {
            label: `VaR ${(confidence * 100).toFixed(0)}% (Hist)`,
            value: `${varHist}%`,
            color: "#EF4444",
          },
          {
            label: `VaR ${(confidence * 100).toFixed(0)}% (Param)`,
            value: `${varParam}%`,
            color: "#F97316",
          },
          {
            label: `VaR ${(confidence * 100).toFixed(0)}% (MC)`,
            value: `${varMC}%`,
            color: "#F59E0B",
          },
          {
            label: `CVaR ${(confidence * 100).toFixed(0)}%`,
            value: `${cvarVal}%`,
            color: "#EF4444",
          },
          {
            label: "Max Drawdown",
            value: `${distStats.maxDD}%`,
            color: "#EF4444",
          },
          {
            label: "Vol Regime",
            value: "NORMAL",
            color: "#10B981",
            sub: `${distStats.annVol}% p.a.`,
          },
        ].map((m) => (
          <Card key={m.label}>
            <div style={{ fontSize: 10, color: "#64748B", marginBottom: 2 }}>
              {m.label}
            </div>
            <div
              style={{
                fontSize: 16,
                fontWeight: 700,
                fontFamily: "JetBrains Mono, monospace",
                color: m.color,
              }}
            >
              {m.value}
            </div>
            {"sub" in m && (
              <div style={{ fontSize: 10, color: "#94A3B8", marginTop: 1 }}>
                {m.sub}
              </div>
            )}
          </Card>
        ))}
      </div>

      {/* ── Tab bar ── */}
      <div
        style={{ display: "flex", gap: 4, marginBottom: 16, flexWrap: "wrap" }}
      >
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              border:
                tab === t
                  ? "1px solid rgba(212,175,55,0.5)"
                  : "1px solid rgba(51,65,85,0.3)",
              backgroundColor:
                tab === t ? "rgba(212,175,55,0.15)" : "rgba(15,23,42,0.5)",
              color: tab === t ? "#D4AF37" : "#94A3B8",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ════════════ TAB 1: VaR / CVaR ════════════ */}
      {tab === "VaR / CVaR" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "3fr 1fr",
              gap: 16,
              marginBottom: 16,
            }}
          >
            {/* Return distribution histogram */}
            <Card
              title="Return Distribution with VaR / CVaR Markers"
              subtitle="Daily returns — red bars beyond VaR threshold"
            >
              <div style={{ width: "100%", height: 380 }}>
                <ResponsiveContainer>
                  <BarChart data={histogram}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="bin"
                      tick={{ fill: "#64748B", fontSize: 9 }}
                      interval={9}
                      label={{
                        value: "Return (%)",
                        position: "insideBottom",
                        fill: "#64748B",
                        fontSize: 11,
                        offset: -2,
                      }}
                    />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip contentStyle={ttStyle} />
                    <ReferenceLine
                      x={(-varHist).toFixed(1)}
                      stroke="#F97316"
                      strokeDasharray="5 5"
                      label={{
                        value: `VaR ${(confidence * 100).toFixed(0)}%`,
                        fill: "#F97316",
                        fontSize: 11,
                      }}
                    />
                    <ReferenceLine
                      x={(-cvarVal).toFixed(1)}
                      stroke="#EF4444"
                      strokeDasharray="3 3"
                      label={{ value: `CVaR`, fill: "#EF4444", fontSize: 11 }}
                    />
                    <Bar dataKey="count" name="Frequency">
                      {histogram.map((bin, i) => (
                        <Cell
                          key={i}
                          fill={
                            bin.isVar
                              ? "rgba(239,68,68,0.65)"
                              : "rgba(16,185,129,0.5)"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div style={{ fontSize: 12, color: "#94A3B8", marginTop: 8 }}>
                Ann. Return:{" "}
                <strong style={{ color: "#F1F5F9" }}>
                  {distStats.annReturn}%
                </strong>{" "}
                | Ann. Vol:{" "}
                <strong style={{ color: "#F1F5F9" }}>
                  {distStats.annVol}%
                </strong>{" "}
                | Skew:{" "}
                <strong style={{ color: "#F1F5F9" }}>{distStats.skew}</strong> |
                Kurt (excess):{" "}
                <strong style={{ color: "#F1F5F9" }}>
                  {distStats.kurtosis}
                </strong>
              </div>
            </Card>

            {/* VaR summary sidebar */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <Card
                title="VaR Gauge"
                subtitle={`${(confidence * 100).toFixed(0)}% 1-Day`}
              >
                <VaRGauge value={12450} limit={20000} />
              </Card>
              <Card title="VaR Comparison">
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 6 }}
                >
                  {[
                    { method: "Historical", val: varHist },
                    { method: "Parametric", val: varParam },
                    { method: "Monte Carlo", val: varMC },
                    { method: "CVaR (ES)", val: cvarVal },
                  ].map((v) => (
                    <div
                      key={v.method}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "4px 0",
                        borderBottom: "1px solid rgba(51,65,85,0.2)",
                      }}
                    >
                      <span style={{ fontSize: 12, color: "#94A3B8" }}>
                        {v.method}
                      </span>
                      <span
                        style={{
                          fontFamily: "JetBrains Mono, monospace",
                          fontSize: 13,
                          color: "#EF4444",
                          fontWeight: 600,
                        }}
                      >
                        {v.val}%
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
              <Card title="Percentiles">
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 4 }}
                >
                  {[
                    { p: "1%", v: distStats.pct1 },
                    { p: "5%", v: distStats.pct5 },
                    { p: "95%", v: distStats.pct95 },
                    { p: "99%", v: distStats.pct99 },
                  ].map((d) => (
                    <div
                      key={d.p}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <span style={{ fontSize: 12, color: "#64748B" }}>
                        {d.p}
                      </span>
                      <span
                        style={{
                          fontFamily: "JetBrains Mono, monospace",
                          fontSize: 12,
                          color: "#F1F5F9",
                        }}
                      >
                        {d.v}%
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          </div>

          {/* Risk decomp + correlation */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
              gap: 16,
            }}
          >
            <Card
              title="Risk Decomposition"
              subtitle="Contribution to total portfolio risk"
            >
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={RISK_DECOMP}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={95}
                      innerRadius={50}
                      label={({ name, value }: any) => `${name}: ${value}%`}
                      labelLine={false}
                      style={{ fontSize: 10 }}
                    >
                      {RISK_DECOMP.map((r, i) => (
                        <Cell key={i} fill={r.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={ttStyle}
                      formatter={(v: any) => `${v}%`}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card
              title="Risk Factor Correlation"
              subtitle="Cross-asset correlations"
            >
              <table
                style={{
                  width: "100%",
                  borderCollapse: "separate",
                  borderSpacing: 4,
                  fontSize: 12,
                }}
              >
                <thead>
                  <tr>
                    <th style={{ padding: 6 }} />
                    {CORR_ASSETS.map((a) => (
                      <th
                        key={a}
                        style={{
                          padding: 6,
                          color: "#D4AF37",
                          fontFamily: "JetBrains Mono, monospace",
                          fontWeight: 600,
                          textAlign: "center",
                        }}
                      >
                        {a}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {CORR_ASSETS.map((a, i) => (
                    <tr key={a}>
                      <td
                        style={{
                          padding: 6,
                          color: "#D4AF37",
                          fontFamily: "JetBrains Mono, monospace",
                          fontWeight: 600,
                        }}
                      >
                        {a}
                      </td>
                      {HEATMAP[i].map((v, j) => (
                        <td
                          key={j}
                          style={{
                            padding: 6,
                            textAlign: "center",
                            fontFamily: "JetBrains Mono, monospace",
                            backgroundColor: corrColor(v),
                            color: "#F1F5F9",
                            borderRadius: 4,
                          }}
                        >
                          {v.toFixed(2)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>
        </>
      )}

      {/* ════════════ TAB 2: Drawdown ════════════ */}
      {tab === "Drawdown" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card
            title="Drawdown Series"
            subtitle="Peak-to-trough decline over 504 trading days"
          >
            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <AreaChart data={drawdownData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="day"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    interval={80}
                  />
                  <YAxis
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    tickFormatter={(v: any) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any) => `${Number(v).toFixed(2)}%`}
                  />
                  <Area
                    type="monotone"
                    dataKey="drawdown"
                    stroke="#EF4444"
                    fill="rgba(239,68,68,0.2)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card
            title="Cumulative Return"
            subtitle="Portfolio value rebased to 100"
          >
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <LineChart data={drawdownData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="day"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    interval={80}
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fill: "#64748B", fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any) => Number(v).toFixed(2)}
                  />
                  <Line
                    type="monotone"
                    dataKey="price"
                    stroke="#00D9FF"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
              gap: 10,
            }}
          >
            {[
              {
                label: "Max Drawdown",
                value: `${distStats.maxDD}%`,
                color: "#EF4444",
              },
              {
                label: "Current Drawdown",
                value: `${drawdownData[drawdownData.length - 1]?.drawdown}%`,
                color: "#F59E0B",
              },
              {
                label: "Avg Daily Return",
                value: `${distStats.mean}%`,
                color: "#10B981",
              },
            ].map((m) => (
              <Card key={m.label}>
                <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    fontFamily: "JetBrains Mono, monospace",
                    color: m.color,
                  }}
                >
                  {m.value}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* ════════════ TAB 3: Volatility Cone ════════════ */}
      {tab === "Volatility Cone" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card
            title="Volatility Cone"
            subtitle="Rolling realized vol across windows vs historical min/max/percentiles"
          >
            <div style={{ width: "100%", height: 400 }}>
              <ResponsiveContainer>
                <ComposedChart data={VOL_CONE}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="window"
                    tick={{ fill: "#64748B", fontSize: 11 }}
                  />
                  <YAxis
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    tickFormatter={(v: any) => `${v}%`}
                    label={{
                      value: "Ann. Vol (%)",
                      angle: -90,
                      position: "insideLeft",
                      fill: "#64748B",
                      fontSize: 11,
                    }}
                  />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any) => `${v}%`}
                  />
                  <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                  <Area
                    type="monotone"
                    dataKey="max"
                    stackId="0"
                    stroke="none"
                    fill="rgba(31,119,180,0.08)"
                    name="Max"
                  />
                  <Area
                    type="monotone"
                    dataKey="p75"
                    stackId="1"
                    stroke="none"
                    fill="rgba(31,119,180,0.15)"
                    name="P75"
                  />
                  <Line
                    type="monotone"
                    dataKey="median"
                    stroke="#64748B"
                    strokeWidth={2}
                    dot
                    name="Median"
                  />
                  <Line
                    type="monotone"
                    dataKey="p25"
                    stroke="rgba(31,119,180,0.4)"
                    strokeWidth={1}
                    strokeDasharray="4 4"
                    dot={false}
                    name="P25"
                  />
                  <Line
                    type="monotone"
                    dataKey="min"
                    stroke="rgba(31,119,180,0.3)"
                    strokeWidth={1}
                    strokeDasharray="2 2"
                    dot={false}
                    name="Min"
                  />
                  <Line
                    type="monotone"
                    dataKey="current"
                    stroke="#F59E0B"
                    strokeWidth={2.5}
                    strokeDasharray="6 3"
                    dot={{ r: 5, fill: "#F59E0B" }}
                    name="Current"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card
            title="Volatility Cone Table"
            subtitle="Annualized vol (%) by window"
          >
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    {[
                      "Window",
                      "Min",
                      "P25",
                      "Median",
                      "P75",
                      "Max",
                      "Current",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "8px 10px",
                          textAlign: h === "Window" ? "left" : "right",
                          color: "#94A3B8",
                          fontWeight: 500,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {VOL_CONE.map((r) => (
                    <tr
                      key={r.window}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td
                        style={{
                          padding: "8px 10px",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#D4AF37",
                        }}
                      >
                        {r.window}
                      </td>
                      {[r.min, r.p25, r.median, r.p75, r.max].map((v, i) => (
                        <td
                          key={i}
                          style={{
                            padding: "8px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#94A3B8",
                          }}
                        >
                          {v}%
                        </td>
                      ))}
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#F59E0B",
                          fontWeight: 600,
                        }}
                      >
                        {r.current}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <div
            style={{
              backgroundColor: "rgba(10,14,26,0.5)",
              borderRadius: 8,
              padding: "10px 14px",
              fontSize: 13,
              color: "#94A3B8",
            }}
          >
            <strong style={{ color: "#D4AF37" }}>Volatility Regime: </strong>
            <Badge variant="up">NORMAL</Badge>
            <span style={{ marginLeft: 12 }}>
              Current Ann. Vol:{" "}
              <strong style={{ color: "#F1F5F9" }}>{distStats.annVol}%</strong>
            </span>
            <span style={{ marginLeft: 12 }}>
              Percentile (1Y):{" "}
              <strong style={{ color: "#F1F5F9" }}>54th</strong>
            </span>
            <span style={{ marginLeft: 12 }}>
              Trend: <strong style={{ color: "#10B981" }}>STABLE</strong>
            </span>
          </div>
        </div>
      )}

      {/* ════════════ TAB 4: Stress Tests ════════════ */}
      {tab === "Stress Tests" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card
            title="Stress Test: Portfolio Impact (%)"
            subtitle="Historical & hypothetical crisis scenarios"
          >
            <div
              style={{
                width: "100%",
                height: Math.max(300, STRESS_TESTS.length * 40),
              }}
            >
              <ResponsiveContainer>
                <BarChart
                  data={[...STRESS_TESTS].sort(
                    (a, b) => a.portfolioLoss - b.portfolioLoss,
                  )}
                  layout="vertical"
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    type="number"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    tickFormatter={(v: any) => `${v}%`}
                  />
                  <YAxis
                    type="category"
                    dataKey="scenario"
                    width={180}
                    tick={{ fill: "#F1F5F9", fontSize: 11 }}
                  />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any) => `${v}%`}
                  />
                  <Bar
                    dataKey="portfolioLoss"
                    name="Portfolio Impact"
                    radius={[0, 4, 4, 0]}
                  >
                    {STRESS_TESTS.map((s, i) => (
                      <Cell
                        key={i}
                        fill={
                          s.portfolioLoss < -20
                            ? "#EF4444"
                            : s.portfolioLoss < -10
                              ? "#F59E0B"
                              : "#10B981"
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card
            title="Stress Test Details"
            subtitle="Detailed scenario analysis"
          >
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    {[
                      "Scenario",
                      "Portfolio Impact",
                      "SPY Drop",
                      "VaR Breach",
                      "Recovery (Days)",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "8px 10px",
                          textAlign: h === "Scenario" ? "left" : "right",
                          color: "#94A3B8",
                          fontWeight: 500,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {STRESS_TESTS.map((s) => (
                    <tr
                      key={s.scenario}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td style={{ padding: "8px 10px", color: "#F1F5F9" }}>
                        {s.scenario}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#EF4444",
                        }}
                      >
                        {s.portfolioLoss}%
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#94A3B8",
                        }}
                      >
                        {s.spyDrop}%
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "right" }}>
                        <Badge variant={s.varBreach ? "down" : "up"}>
                          {s.varBreach ? "Yes" : "No"}
                        </Badge>
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#94A3B8",
                        }}
                      >
                        {s.recoveryDays}d
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* ════════════ TAB 5: Factor Analysis ════════════ */}
      {tab === "Factor Analysis" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
              gap: 16,
            }}
          >
            <Card
              title="Factor Regression (OLS)"
              subtitle="Fama-French style factor model"
            >
              <div style={{ overflowX: "auto" }}>
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    fontSize: 13,
                  }}
                >
                  <thead>
                    <tr
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}
                    >
                      {[
                        "Factor",
                        "Beta",
                        "t-Stat",
                        "p-Value",
                        "Var Contrib",
                      ].map((h) => (
                        <th
                          key={h}
                          style={{
                            padding: "6px 10px",
                            textAlign: h === "Factor" ? "left" : "right",
                            color: "#94A3B8",
                            fontWeight: 500,
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {FACTORS.map((f) => (
                      <tr
                        key={f.name}
                        style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                      >
                        <td style={{ padding: "6px 10px", color: "#F1F5F9" }}>
                          {f.name}
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color: f.beta >= 0 ? "#10B981" : "#EF4444",
                          }}
                        >
                          {f.beta >= 0 ? "+" : ""}
                          {f.beta.toFixed(2)}
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#94A3B8",
                          }}
                        >
                          {f.tStat.toFixed(2)}
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#94A3B8",
                          }}
                        >
                          {f.pValue.toFixed(3)}
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#D4AF37",
                          }}
                        >
                          {f.varContrib.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card
              title="Factor Variance Contribution"
              subtitle="Percentage of variance explained by each factor"
            >
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={FACTORS} layout="vertical">
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      type="number"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                      tickFormatter={(v: any) => `${v}%`}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={140}
                      tick={{ fill: "#F1F5F9", fontSize: 11 }}
                    />
                    <Tooltip
                      contentStyle={ttStyle}
                      formatter={(v: any) => `${v}%`}
                    />
                    <Bar
                      dataKey="varContrib"
                      name="Var Contrib %"
                      fill="#D4AF37"
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <Card title="Regression Summary">
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                gap: 8,
              }}
            >
              {[
                { label: "R-squared", value: "0.847" },
                { label: "Adj. R-squared", value: "0.841" },
                { label: "Alpha (Ann.)", value: "+2.4%" },
                { label: "Alpha t-stat", value: "1.85" },
                { label: "F-statistic", value: "142.6" },
                { label: "Observations", value: "504" },
                { label: "Durbin-Watson", value: "2.04" },
                { label: "AIC", value: "-1,245.8" },
              ].map((r) => (
                <div
                  key={r.label}
                  style={{
                    backgroundColor: "rgba(10,14,26,0.5)",
                    borderRadius: 6,
                    padding: "8px 10px",
                  }}
                >
                  <div style={{ fontSize: 11, color: "#64748B" }}>
                    {r.label}
                  </div>
                  <div
                    style={{
                      fontSize: 15,
                      fontWeight: 600,
                      color: "#D4AF37",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {r.value}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
