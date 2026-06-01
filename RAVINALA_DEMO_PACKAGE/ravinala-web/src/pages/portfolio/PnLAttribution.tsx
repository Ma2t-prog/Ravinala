import React, { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "../../components/ui/Card";
import { useIndices } from "../../hooks/useMarketData";

// ── BSM Math for Greeks Decomp tab ──────────────────────────────────────────
function _erf(x: number): number {
  const sign = x >= 0 ? 1 : -1;
  const a = Math.abs(x);
  const t = 1 / (1 + 0.3275911 * a);
  const y =
    1 -
    ((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) *
      t +
      0.254829592) *
      t *
      Math.exp(-a * a);
  return sign * y;
}
const normCdf = (x: number) => 0.5 * (1 + _erf(x / Math.SQRT2));
const normPdf = (x: number) => Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);

interface BSMResult {
  price: number;
  delta: number;
  gamma: number;
  vega: number;
  theta: number;
}
function bsm(
  S: number,
  K: number,
  T: number,
  sigma: number,
  r: number,
  q: number,
  isCall: boolean,
): BSMResult {
  if (T <= 0) {
    const p = isCall ? Math.max(S - K, 0) : Math.max(K - S, 0);
    return {
      price: p,
      delta: isCall ? (S > K ? 1 : 0) : S < K ? -1 : 0,
      gamma: 0,
      vega: 0,
      theta: 0,
    };
  }
  const sqrtT = Math.sqrt(T);
  const d1 =
    (Math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrtT);
  const d2 = d1 - sigma * sqrtT;
  const eqT = Math.exp(-q * T),
    erT = Math.exp(-r * T);
  const Nd1 = normCdf(d1),
    Nd2 = normCdf(d2),
    nd1 = normPdf(d1);
  const price = isCall
    ? S * eqT * Nd1 - K * erT * Nd2
    : K * erT * (1 - Nd2) - S * eqT * (1 - Nd1);
  const delta = isCall ? eqT * Nd1 : eqT * (Nd1 - 1);
  const gamma = (eqT * nd1) / (S * sigma * sqrtT);
  const vega = (S * eqT * sqrtT * nd1) / 100; // per 1% vol
  const theta = isCall
    ? ((-S * eqT * nd1 * sigma) / (2 * sqrtT) -
        r * K * erT * Nd2 +
        q * S * eqT * Nd1) /
      365
    : ((-S * eqT * nd1 * sigma) / (2 * sqrtT) +
        r * K * erT * (1 - Nd2) -
        q * S * eqT * (1 - Nd1)) /
      365;
  return { price, delta, gamma, vega, theta };
}

interface DecompResult {
  actualPnL: number;
  deltaPnL: number;
  gammaPnL: number;
  vegaPnL: number;
  thetaPnL: number;
  residual: number;
  g0: BSMResult;
}
function decompPnL(
  S0: number,
  S1: number,
  sigma0: number,
  sigma1: number,
  T0: number,
  T1: number,
  r: number,
  q: number,
  K: number,
  isCall: boolean,
  qty: number,
): DecompResult {
  const g0 = bsm(S0, K, T0, sigma0, r, q, isCall);
  const g1 = bsm(S1, K, T1, sigma1, r, q, isCall);
  const actualPnL = (g1.price - g0.price) * qty;
  const dS = S1 - S0;
  const dSig = (sigma1 - sigma0) * 100; // in vol-points (percentage)
  const dtYr = Math.max(T0 - T1, 0);
  const deltaPnL = g0.delta * dS * qty;
  const gammaPnL = 0.5 * g0.gamma * dS * dS * qty;
  const vegaPnL = g0.vega * dSig * qty; // vega already per 1%
  const thetaPnL = g0.theta * dtYr * 365 * qty; // theta already per day
  const residual = actualPnL - deltaPnL - gammaPnL - vegaPnL - thetaPnL;
  return { actualPnL, deltaPnL, gammaPnL, vegaPnL, thetaPnL, residual, g0 };
}

// ── Demo Data ────────────────────────────────────────────────────────────────

// Waterfall: P&L decomposition
const waterfallData = [
  { name: "Asset Allocation", value: 1.45, cumulative: 1.45 },
  { name: "Security Selection", value: 0.92, cumulative: 2.37 },
  { name: "Currency Effect", value: -0.28, cumulative: 2.09 },
  { name: "Interaction", value: 0.21, cumulative: 2.3 },
  { name: "Total P&L", value: 2.3, cumulative: 2.3 },
];

// For the waterfall, we need base + value for stacked bar
const waterfallBars = waterfallData.map((d, i) => {
  if (i === waterfallData.length - 1) {
    // Total bar starts at 0
    return { name: d.name, base: 0, value: d.value, isTotal: true };
  }
  const base = i === 0 ? 0 : waterfallData[i - 1].cumulative;
  return {
    name: d.name,
    base: d.value >= 0 ? base : base + d.value,
    value: Math.abs(d.value),
    isTotal: false,
  };
});

// Daily P&L time series (30 days)
const dailyPnL: { day: string; pnl: number; cumulative: number }[] = [];
let cum = 0;
const dailyValues = [
  0.12, -0.08, 0.25, 0.18, -0.15, 0.32, 0.05, -0.22, 0.28, 0.14, -0.06, 0.19,
  0.08, -0.11, 0.35, -0.18, 0.22, 0.15, 0.09, -0.25, 0.3, 0.12, -0.05, 0.18,
  0.24, -0.13, 0.2, 0.16, 0.08, 0.11,
];
for (let i = 0; i < 30; i++) {
  cum += dailyValues[i];
  dailyPnL.push({
    day: `Mar ${i + 1}`,
    pnl: dailyValues[i],
    cumulative: Math.round(cum * 100) / 100,
  });
}

// Factor attribution
const factorData = [
  { factor: "Market (Beta)", beta: 1.05, contribution: 1.82, tStat: 4.25 },
  { factor: "Size (SMB)", beta: -0.12, contribution: -0.08, tStat: -0.85 },
  { factor: "Value (HML)", beta: 0.18, contribution: 0.15, tStat: 1.42 },
  { factor: "Momentum (UMD)", beta: 0.25, contribution: 0.28, tStat: 2.18 },
  { factor: "Quality (QMJ)", beta: 0.15, contribution: 0.13, tStat: 1.65 },
];

// ── Shared mini-styles ───────────────────────────────────────────────────────
const inputSt: React.CSSProperties = {
  background: "#1E293B",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 6,
  color: "#F1F5F9",
  padding: "6px 10px",
  fontSize: 13,
  fontFamily: "JetBrains Mono, monospace",
  width: "100%",
  boxSizing: "border-box",
};

// ── Component ────────────────────────────────────────────────────────────────

export default function PnLAttribution() {
  // ── Live market data ────────────────────────────────────────────────────────
  const { data: indicesData, isLoading: indicesLoading } = useIndices();
  const usingFallback = !indicesData;

  // ── Tab state ───────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<0 | 1>(0);

  // ── Greeks Decomp state ─────────────────────────────────────────────────────
  const [gS0, setGS0] = useState(100);
  const [gK, setGK] = useState(100);
  const [gT, setGT] = useState(30); // days to expiry
  const [gSig0, setGSig0] = useState(25); // vol %
  const [gR, setGR] = useState(5); // rate %
  const [gDiv, setGDiv] = useState(0); // div yield %
  const [gType, setGType] = useState<"call" | "put">("call");
  const [gQty, setGQty] = useState(1);
  const [gS1, setGS1] = useState(103);
  const [gSig1, setGSig1] = useState(26); // new vol %
  const [gDtDays, setGDtDays] = useState(1);
  const [gResult, setGResult] = useState<DecompResult | null>(null);

  const runDecomp = () => {
    const T0 = gT / 365;
    const T1 = Math.max(T0 - gDtDays / 365, 1e-4);
    setGResult(
      decompPnL(
        gS0,
        gS1,
        gSig0 / 100,
        gSig1 / 100,
        T0,
        T1,
        gR / 100,
        gDiv / 100,
        gK,
        gType === "call",
        gQty,
      ),
    );
  };

  const keyIndices = useMemo(() => {
    if (!indicesData) return [];
    const targets = ["^GSPC", "^IXIC", "^DJI", "^RUT"];
    return Object.values(indicesData)
      .flat()
      .filter((idx) => targets.includes(idx.symbol));
  }, [indicesData]);

  return (
    <div style={{ color: "#F1F5F9", minHeight: "100vh" }}>
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
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 4,
        }}
      >
        P&amp;L Attribution
      </h1>
      <p style={{ color: "#94A3B8", fontSize: 14, marginBottom: 16 }}>
        Portfolio attribution &amp; derivatives P&amp;L decomposition
      </p>
      {/* ── Tab bar ── */}
      <div
        style={{
          display: "flex",
          gap: 2,
          marginBottom: 20,
          borderBottom: "1px solid rgba(51,65,85,0.4)",
        }}
      >
        {(["Portfolio Attribution", "Greeks Decomp"] as const).map((t, i) => (
          <button
            key={t}
            onClick={() => setActiveTab(i as 0 | 1)}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              padding: "8px 18px",
              fontSize: 13,
              color: activeTab === i ? "#8B5CF6" : "#94A3B8",
              borderBottom: `2px solid ${activeTab === i ? "#8B5CF6" : "transparent"}`,
              fontFamily: "Inter, sans-serif",
              fontWeight: activeTab === i ? 600 : 400,
              marginBottom: -1,
              transition: "color 0.15s",
            }}
          >
            {t}
          </button>
        ))}
      </div>
      {/* ── Live Market Benchmarks ── */}
      {activeTab === 0 && (
        <React.Fragment>
          {keyIndices.length > 0 && (
            <div
              style={{
                display: "flex",
                gap: 12,
                marginBottom: 16,
                flexWrap: "wrap",
              }}
            >
              {keyIndices.map((idx) => (
                <div
                  key={idx.symbol}
                  style={{
                    padding: "6px 14px",
                    borderRadius: 8,
                    backgroundColor: "rgba(139,92,246,0.06)",
                    border: "1px solid rgba(139,92,246,0.15)",
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 12,
                  }}
                >
                  <span style={{ color: "#94A3B8", marginRight: 8 }}>
                    {idx.symbol.replace("^", "")}
                  </span>
                  <span style={{ color: "#F1F5F9", fontWeight: 600 }}>
                    {idx.price.toLocaleString()}
                  </span>
                  <span
                    style={{
                      color: idx.change.percent >= 0 ? "#10B981" : "#EF4444",
                      marginLeft: 8,
                      fontSize: 11,
                    }}
                  >
                    {idx.change.percent >= 0 ? "+" : ""}
                    {idx.change.percent.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* ── Summary Stats ── */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {(
              [
                ["MTD P&L", "+2.30%", true],
                ["Asset Allocation", "+1.45%", true],
                ["Security Selection", "+0.92%", true],
                ["Currency Effect", "-0.28%", false],
              ] as [string, string, boolean][]
            ).map(([label, val, isPos]) => (
              <Card key={label}>
                <div
                  style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}
                >
                  {label}
                </div>
                <div
                  style={{
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 22,
                    fontWeight: 700,
                    color: isPos ? "#8B5CF6" : "#EF4444",
                  }}
                >
                  {val}
                </div>
              </Card>
            ))}
          </div>

          {/* ── Row: Waterfall + Daily P&L ── */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 16,
            }}
          >
            {/* Waterfall Chart */}
            <Card title="P&L Waterfall" subtitle="Attribution decomposition">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={waterfallBars}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "#94A3B8", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: "#94A3B8", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: any) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#131823",
                      border: "1px solid rgba(51,65,85,0.3)",
                      borderRadius: 8,
                      color: "#F1F5F9",
                    }}
                    formatter={(v: any, name: any) => {
                      if (name === "base") return [null, null];
                      return [`${Number(v).toFixed(2)}%`, "P&L"];
                    }}
                  />
                  {/* Invisible base bar */}
                  <Bar dataKey="base" stackId="stack" fill="transparent" />
                  {/* Visible value bar */}
                  <Bar dataKey="value" stackId="stack" radius={[4, 4, 0, 0]}>
                    {waterfallBars.map((entry, i) => {
                      let color: string;
                      if (entry.isTotal) color = "#8B5CF6";
                      else if (waterfallData[i].value >= 0) color = "#10B981";
                      else color = "#EF4444";
                      return <Cell key={i} fill={color} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>

            {/* Daily P&L */}
            <Card title="Daily P&L" subtitle="Cumulative return over 30 days">
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={dailyPnL}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="day"
                    tick={{ fill: "#94A3B8", fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    interval={4}
                  />
                  <YAxis
                    tick={{ fill: "#94A3B8", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v: any) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#131823",
                      border: "1px solid rgba(51,65,85,0.3)",
                      borderRadius: 8,
                      color: "#F1F5F9",
                    }}
                    formatter={(v: any, name: any) => [
                      `${Number(v).toFixed(2)}%`,
                      name === "cumulative" ? "Cumulative" : "Daily",
                    ]}
                  />
                  <Line
                    type="monotone"
                    dataKey="cumulative"
                    stroke="#8B5CF6"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="pnl"
                    stroke="rgba(139,92,246,0.4)"
                    strokeWidth={1}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* ── Factor Attribution Table ── */}
          <Card
            title="Factor Attribution"
            subtitle="Multi-factor model decomposition"
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
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.3)" }}>
                    {[
                      "Factor",
                      "Beta Exposure",
                      "Contribution (%)",
                      "t-Statistic",
                      "Significance",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: "left",
                          padding: "10px 12px",
                          color: "#94A3B8",
                          fontSize: 11,
                          fontWeight: 600,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {factorData.map((f) => {
                    const sig =
                      Math.abs(f.tStat) >= 2
                        ? "Significant"
                        : Math.abs(f.tStat) >= 1.5
                          ? "Marginal"
                          : "Not Sig.";
                    const sigColor =
                      Math.abs(f.tStat) >= 2
                        ? "#10B981"
                        : Math.abs(f.tStat) >= 1.5
                          ? "#F59E0B"
                          : "#94A3B8";
                    return (
                      <tr
                        key={f.factor}
                        style={{
                          borderBottom: "1px solid rgba(51,65,85,0.15)",
                        }}
                      >
                        <td style={{ padding: "10px 12px", fontWeight: 600 }}>
                          {f.factor}
                        </td>
                        <td
                          style={{
                            padding: "10px 12px",
                            fontFamily: "JetBrains Mono, monospace",
                          }}
                        >
                          <span
                            style={{
                              color: f.beta >= 0 ? "#8B5CF6" : "#EF4444",
                            }}
                          >
                            {f.beta >= 0 ? "+" : ""}
                            {f.beta.toFixed(2)}
                          </span>
                        </td>
                        <td
                          style={{
                            padding: "10px 12px",
                            fontFamily: "JetBrains Mono, monospace",
                          }}
                        >
                          <span
                            style={{
                              color:
                                f.contribution >= 0 ? "#10B981" : "#EF4444",
                            }}
                          >
                            {f.contribution >= 0 ? "+" : ""}
                            {f.contribution.toFixed(2)}%
                          </span>
                        </td>
                        <td
                          style={{
                            padding: "10px 12px",
                            fontFamily: "JetBrains Mono, monospace",
                          }}
                        >
                          {f.tStat.toFixed(2)}
                        </td>
                        <td style={{ padding: "10px 12px" }}>
                          <span
                            style={{
                              padding: "2px 8px",
                              borderRadius: 4,
                              fontSize: 11,
                              fontWeight: 600,
                              backgroundColor: `${sigColor}20`,
                              color: sigColor,
                            }}
                          >
                            {sig}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
                {/* Total row */}
                <tfoot>
                  <tr style={{ borderTop: "2px solid rgba(51,65,85,0.3)" }}>
                    <td style={{ padding: "10px 12px", fontWeight: 700 }}>
                      Total
                    </td>
                    <td style={{ padding: "10px 12px" }} />
                    <td
                      style={{
                        padding: "10px 12px",
                        fontFamily: "JetBrains Mono, monospace",
                        fontWeight: 700,
                        color: "#8B5CF6",
                      }}
                    >
                      +
                      {factorData
                        .reduce((a, f) => a + f.contribution, 0)
                        .toFixed(2)}
                      %
                    </td>
                    <td colSpan={2} />
                  </tr>
                </tfoot>
              </table>
            </div>
          </Card>
        </React.Fragment>
      )}{" "}
      {/* end activeTab === 0 */}
      {/* ── Tab 1: Greeks Decomp ── */}
      {activeTab === 1 && (
        <div>
          <Card
            title="Option P&L — Taylor Decomposition"
            subtitle="ΔP ≈ Δ·ΔS + ½Γ·ΔS² + ν·Δσ + Θ·Δt + residual"
          >
            <div style={{ marginBottom: 14 }}>
              <div
                style={{
                  fontSize: 13,
                  color: "#8B5CF6",
                  fontWeight: 600,
                  marginBottom: 10,
                }}
              >
                Initial Position
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
                  gap: 10,
                }}
              >
                {(
                  [
                    { label: "Spot S₀", val: gS0, set: setGS0, step: 1 },
                    { label: "Strike K", val: gK, set: setGK, step: 1 },
                    { label: "Expiry (days)", val: gT, set: setGT, step: 1 },
                    {
                      label: "Vol σ₀ (%)",
                      val: gSig0,
                      set: setGSig0,
                      step: 0.5,
                    },
                    { label: "Rate r (%)", val: gR, set: setGR, step: 0.1 },
                    {
                      label: "Div Yield (%)",
                      val: gDiv,
                      set: setGDiv,
                      step: 0.1,
                    },
                    { label: "Quantity", val: gQty, set: setGQty, step: 1 },
                  ] as {
                    label: string;
                    val: number;
                    set: (v: number) => void;
                    step: number;
                  }[]
                ).map(({ label, val, set, step }) => (
                  <div key={label}>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#64748B",
                        marginBottom: 3,
                      }}
                    >
                      {label}
                    </div>
                    <input
                      type="number"
                      value={val}
                      step={step}
                      onChange={(e) => {
                        set(parseFloat(e.target.value) || 0);
                        setGResult(null);
                      }}
                      style={inputSt}
                    />
                  </div>
                ))}
                <div>
                  <div
                    style={{ fontSize: 11, color: "#64748B", marginBottom: 3 }}
                  >
                    Option Type
                  </div>
                  <select
                    value={gType}
                    onChange={(e) => {
                      setGType(e.target.value as "call" | "put");
                      setGResult(null);
                    }}
                    style={{ ...inputSt, cursor: "pointer" }}
                  >
                    <option value="call">Call</option>
                    <option value="put">Put</option>
                  </select>
                </div>
              </div>
            </div>

            <div style={{ marginBottom: 14 }}>
              <div
                style={{
                  fontSize: 13,
                  color: "#00D9FF",
                  fontWeight: 600,
                  marginBottom: 10,
                }}
              >
                Scenario (next period)
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                  gap: 10,
                }}
              >
                {(
                  [
                    { label: "New Spot S₁", val: gS1, set: setGS1, step: 1 },
                    {
                      label: "New Vol σ₁ (%)",
                      val: gSig1,
                      set: setGSig1,
                      step: 0.5,
                    },
                    {
                      label: "Time elapsed (days)",
                      val: gDtDays,
                      set: setGDtDays,
                      step: 1,
                    },
                  ] as {
                    label: string;
                    val: number;
                    set: (v: number) => void;
                    step: number;
                  }[]
                ).map(({ label, val, set, step }) => (
                  <div key={label}>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#64748B",
                        marginBottom: 3,
                      }}
                    >
                      {label}
                    </div>
                    <input
                      type="number"
                      value={val}
                      step={step}
                      onChange={(e) => {
                        set(parseFloat(e.target.value) || 0);
                        setGResult(null);
                      }}
                      style={inputSt}
                    />
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={runDecomp}
              style={{
                background: "rgba(139,92,246,0.15)",
                border: "1px solid rgba(139,92,246,0.4)",
                borderRadius: 8,
                color: "#8B5CF6",
                padding: "8px 22px",
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              Decompose P&L
            </button>

            {gResult &&
              (() => {
                const items = [
                  { name: "Delta", value: gResult.deltaPnL, desc: "Δ·ΔS" },
                  { name: "Gamma", value: gResult.gammaPnL, desc: "½Γ·ΔS²" },
                  { name: "Vega", value: gResult.vegaPnL, desc: "ν·Δσ" },
                  { name: "Theta", value: gResult.thetaPnL, desc: "Θ·Δt" },
                  { name: "Residual", value: gResult.residual, desc: "ε" },
                ] as const;
                const totalExplained =
                  gResult.deltaPnL +
                  gResult.gammaPnL +
                  gResult.vegaPnL +
                  gResult.thetaPnL;
                const wfData = items.map((it, i) => {
                  const _base =
                    i === 0
                      ? 0
                      : items
                          .slice(0, i)
                          .reduce(
                            (s, x) =>
                              s +
                              (x.value >= 0 ? x.value : 0) +
                              (x.value < 0 ? x.value : 0),
                            0,
                          );
                  const prevCum = items
                    .slice(0, i)
                    .reduce((s, x) => s + x.value, 0);
                  return {
                    name: it.name,
                    base: it.value >= 0 ? prevCum : prevCum + it.value,
                    value: Math.abs(it.value),
                    isPos: it.value >= 0,
                  };
                });
                return (
                  <div style={{ marginTop: 20 }}>
                    {/* Metric strip */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(140px, 1fr))",
                        gap: 10,
                        marginBottom: 16,
                      }}
                    >
                      <div
                        style={{
                          background: "#131823",
                          borderRadius: 8,
                          padding: "12px 14px",
                          border: "1px solid rgba(139,92,246,0.3)",
                        }}
                      >
                        <div
                          style={{
                            fontSize: 11,
                            color: "#64748B",
                            marginBottom: 2,
                          }}
                        >
                          Actual P&L
                        </div>
                        <div
                          style={{
                            fontFamily: "JetBrains Mono, monospace",
                            fontSize: 16,
                            fontWeight: 700,
                            color:
                              gResult.actualPnL >= 0 ? "#10B981" : "#EF4444",
                          }}
                        >
                          {gResult.actualPnL >= 0 ? "+" : ""}$
                          {gResult.actualPnL.toFixed(4)}
                        </div>
                      </div>
                      <div
                        style={{
                          background: "#131823",
                          borderRadius: 8,
                          padding: "12px 14px",
                          border: "1px solid rgba(51,65,85,0.3)",
                        }}
                      >
                        <div
                          style={{
                            fontSize: 11,
                            color: "#64748B",
                            marginBottom: 2,
                          }}
                        >
                          Theoretical
                        </div>
                        <div
                          style={{
                            fontFamily: "JetBrains Mono, monospace",
                            fontSize: 16,
                            fontWeight: 700,
                            color: "#8B5CF6",
                          }}
                        >
                          {totalExplained >= 0 ? "+" : ""}$
                          {totalExplained.toFixed(4)}
                        </div>
                      </div>
                      {items.map((it) => (
                        <div
                          key={it.name}
                          style={{
                            background: "#131823",
                            borderRadius: 8,
                            padding: "12px 14px",
                            border: "1px solid rgba(51,65,85,0.3)",
                          }}
                        >
                          <div
                            style={{
                              fontSize: 11,
                              color: "#64748B",
                              marginBottom: 2,
                            }}
                          >
                            {it.name} ({it.desc})
                          </div>
                          <div
                            style={{
                              fontFamily: "JetBrains Mono, monospace",
                              fontSize: 14,
                              fontWeight: 600,
                              color: it.value >= 0 ? "#10B981" : "#EF4444",
                            }}
                          >
                            {it.value >= 0 ? "+" : ""}${it.value.toFixed(4)}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Waterfall */}
                    <ResponsiveContainer width="100%" height={260}>
                      <BarChart
                        data={wfData}
                        margin={{ top: 8, right: 16, left: 8, bottom: 8 }}
                      >
                        <CartesianGrid
                          strokeDasharray="3 3"
                          stroke="rgba(51,65,85,0.3)"
                        />
                        <XAxis
                          dataKey="name"
                          tick={{ fill: "#94A3B8", fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          tick={{ fill: "#94A3B8", fontSize: 10 }}
                          axisLine={false}
                          tickLine={false}
                          tickFormatter={(v: number) => `$${v.toFixed(3)}`}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#131823",
                            border: "1px solid rgba(51,65,85,0.5)",
                            borderRadius: 8,
                            color: "#F1F5F9",
                          }}
                          formatter={
                            ((val: number, name: string) =>
                              name === "base"
                                ? [null, null]
                                : [`$${val.toFixed(4)}`, "P&L"]) as any
                          }
                        />
                        <Bar
                          dataKey="base"
                          stackId="stack"
                          fill="transparent"
                        />
                        <Bar
                          dataKey="value"
                          stackId="stack"
                          radius={[4, 4, 0, 0]}
                        >
                          {wfData.map((entry, i) => (
                            <Cell
                              key={i}
                              fill={entry.isPos ? "#10B981" : "#EF4444"}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>

                    {/* Greeks at T0 */}
                    <div style={{ marginTop: 14 }}>
                      <div
                        style={{
                          fontSize: 12,
                          color: "#64748B",
                          marginBottom: 8,
                        }}
                      >
                        Initial Greeks (at T₀)
                      </div>
                      <div
                        style={{ display: "flex", flexWrap: "wrap", gap: 12 }}
                      >
                        {(
                          [
                            ["Δ (Delta)", gResult.g0.delta.toFixed(4)],
                            ["Γ (Gamma)", gResult.g0.gamma.toFixed(6)],
                            ["ν (Vega/1%)", `$${gResult.g0.vega.toFixed(4)}`],
                            [
                              "Θ (Theta/day)",
                              `$${gResult.g0.theta.toFixed(4)}`,
                            ],
                            ["Price", `$${gResult.g0.price.toFixed(4)}`],
                          ] as [string, string][]
                        ).map(([label, val]) => (
                          <div
                            key={label}
                            style={{
                              background: "rgba(139,92,246,0.07)",
                              border: "1px solid rgba(139,92,246,0.2)",
                              borderRadius: 6,
                              padding: "6px 12px",
                              display: "flex",
                              gap: 8,
                              alignItems: "center",
                            }}
                          >
                            <span style={{ fontSize: 11, color: "#64748B" }}>
                              {label}
                            </span>
                            <span
                              style={{
                                fontFamily: "JetBrains Mono, monospace",
                                fontSize: 12,
                                color: "#A5B4FC",
                              }}
                            >
                              {val}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })()}
          </Card>
        </div>
      )}
    </div>
  );
}
