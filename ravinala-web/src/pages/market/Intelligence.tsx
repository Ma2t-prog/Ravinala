import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { IndexItem, MacroIndicator } from "../../api/types";
import { Badge, Card } from "../../components/ui";
import { useIndices, useMacro } from "../../hooks/useMarketData";

/* ── palette ── */
const GOLD = "#D4AF37",
  CYAN = "#00D9FF",
  GREEN = "#10B981",
  RED = "#EF4444",
  PURPLE = "#A855F7",
  AMBER = "#F59E0B";
const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
} as const;
const mono = "JetBrains Mono, monospace";

/* ── tabs ── */
const TABS = [
  "Regime",
  "Factor Analysis",
  "Cross-Asset",
  "Sector Rotation",
  "Risk Monitor",
] as const;
type Tab = (typeof TABS)[number];

/* ═══════════════════════════════════════════
   DATA
═══════════════════════════════════════════ */

/* ── Regime ── */
const regimeHistory = Array.from({ length: 60 }, (_, i) => {
  const base = Math.sin(i * 0.08) * 30 + 55;
  return {
    day: i + 1,
    score: Math.round(base + Math.random() * 8 - 4),
    vix: +(12 + Math.sin(i * 0.15) * 8 + Math.random() * 3).toFixed(1),
  };
});

const MACRO_SIGNALS = [
  {
    name: "Yield Curve (10Y-2Y)",
    value: "+0.42%",
    signal: "green" as const,
    desc: "Positive slope — expansion signal",
  },
  {
    name: "ISM Manufacturing",
    value: "51.2",
    signal: "yellow" as const,
    desc: "Barely above contraction threshold",
  },
  {
    name: "Consumer Confidence",
    value: "104.7",
    signal: "green" as const,
    desc: "Above long-run average of 100",
  },
  {
    name: "Initial Jobless Claims",
    value: "215K",
    signal: "green" as const,
    desc: "Below 250K threshold",
  },
  {
    name: "Leading Economic Index",
    value: "-0.1%",
    signal: "red" as const,
    desc: "3 consecutive negative readings",
  },
  {
    name: "Credit Spread (HY-IG)",
    value: "142 bps",
    signal: "green" as const,
    desc: "Below 200 bps stress level",
  },
  {
    name: "Monetary Supply (M2)",
    value: "+3.8%",
    signal: "yellow" as const,
    desc: "Growing but below trend",
  },
  {
    name: "Housing Starts",
    value: "1.42M",
    signal: "green" as const,
    desc: "Stable at pre-pandemic levels",
  },
];

const regimeProbabilities = [
  { regime: "Expansion", prob: 62, color: GREEN },
  { regime: "Late Cycle", prob: 24, color: AMBER },
  { regime: "Recession", prob: 8, color: RED },
  { regime: "Recovery", prob: 6, color: CYAN },
];

/* ── Factor Analysis ── */
const factorReturns = Array.from({ length: 12 }, (_, i) => ({
  month: [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ][i],
  momentum: +(
    2.1 +
    Math.sin(i * 0.5) * 3.5 +
    Math.random() * 1.5 -
    0.75
  ).toFixed(2),
  value: +(1.2 + Math.cos(i * 0.4) * 2.8 + Math.random() * 1.2 - 0.6).toFixed(
    2,
  ),
  quality: +(1.8 + Math.sin(i * 0.3) * 1.5 + Math.random() * 0.8 - 0.4).toFixed(
    2,
  ),
  size: +(0.5 + Math.cos(i * 0.6) * 2.2 + Math.random() * 1.0 - 0.5).toFixed(2),
  lowVol: +(1.0 + Math.sin(i * 0.35) * 1.8 + Math.random() * 0.6 - 0.3).toFixed(
    2,
  ),
}));

const factorExposure = [
  { factor: "Momentum", sp500: 65, nasdaq: 82, russell: 45 },
  { factor: "Value", sp500: 48, nasdaq: 25, russell: 72 },
  { factor: "Quality", sp500: 72, nasdaq: 78, russell: 38 },
  { factor: "Size", sp500: 30, nasdaq: 40, russell: 85 },
  { factor: "Low Vol", sp500: 55, nasdaq: 35, russell: 50 },
  { factor: "Growth", sp500: 60, nasdaq: 88, russell: 42 },
];

const factorTable = [
  {
    name: "Momentum (12-1)",
    ytd: 8.4,
    sharpe: 0.92,
    maxDD: -12.3,
    turnover: 45,
    ic: 0.042,
  },
  {
    name: "Value (B/P)",
    ytd: 3.1,
    sharpe: 0.58,
    maxDD: -18.7,
    turnover: 22,
    ic: 0.031,
  },
  {
    name: "Quality (ROE)",
    ytd: 6.2,
    sharpe: 0.81,
    maxDD: -8.5,
    turnover: 18,
    ic: 0.038,
  },
  {
    name: "Size (SMB)",
    ytd: -1.8,
    sharpe: 0.22,
    maxDD: -22.4,
    turnover: 12,
    ic: 0.018,
  },
  {
    name: "Low Volatility",
    ytd: 4.5,
    sharpe: 0.72,
    maxDD: -6.8,
    turnover: 15,
    ic: 0.035,
  },
  {
    name: "Growth (EPS Est.)",
    ytd: 9.8,
    sharpe: 0.95,
    maxDD: -14.1,
    turnover: 38,
    ic: 0.048,
  },
  {
    name: "Dividend Yield",
    ytd: 2.8,
    sharpe: 0.55,
    maxDD: -9.2,
    turnover: 8,
    ic: 0.025,
  },
];

/* ── Cross-Asset ── */
const CORRELATION_ASSETS = [
  "SPY",
  "QQQ",
  "TLT",
  "GLD",
  "DXY",
  "HYG",
  "VIX",
  "BTC",
];
const CORR_MATRIX = [
  [1.0, 0.92, -0.45, 0.12, -0.38, 0.72, -0.82, 0.42],
  [0.92, 1.0, -0.52, 0.08, -0.42, 0.65, -0.78, 0.55],
  [-0.45, -0.52, 1.0, 0.35, 0.18, -0.38, 0.52, -0.22],
  [0.12, 0.08, 0.35, 1.0, -0.55, 0.15, 0.08, 0.18],
  [-0.38, -0.42, 0.18, -0.55, 1.0, -0.28, 0.35, -0.32],
  [0.72, 0.65, -0.38, 0.15, -0.28, 1.0, -0.65, 0.38],
  [-0.82, -0.78, 0.52, 0.08, 0.35, -0.65, 1.0, -0.28],
  [0.42, 0.55, -0.22, 0.18, -0.32, 0.38, -0.28, 1.0],
];

const crossAssetPerf = Array.from({ length: 52 }, (_, i) => ({
  week: `W${i + 1}`,
  spy: +(100 + Math.sin(i * 0.12) * 8 + i * 0.15 + Math.random() * 2).toFixed(
    1,
  ),
  tlt: +(100 + Math.cos(i * 0.08) * 5 - i * 0.05 + Math.random() * 1.5).toFixed(
    1,
  ),
  gld: +(100 + Math.sin(i * 0.1) * 6 + i * 0.08 + Math.random() * 1.8).toFixed(
    1,
  ),
  btc: +(100 + Math.sin(i * 0.15) * 15 + i * 0.3 + Math.random() * 4).toFixed(
    1,
  ),
}));

/* ── Sector Rotation ── */
const SECTORS = [
  {
    name: "Technology",
    score: 82,
    change: 3.2,
    phase: "Expansion" as const,
    weight: 29.5,
  },
  {
    name: "Health Care",
    score: 71,
    change: 1.5,
    phase: "Late Cycle" as const,
    weight: 13.2,
  },
  {
    name: "Financials",
    score: 68,
    change: -0.8,
    phase: "Expansion" as const,
    weight: 12.8,
  },
  {
    name: "Consumer Disc.",
    score: 64,
    change: 2.1,
    phase: "Expansion" as const,
    weight: 10.5,
  },
  {
    name: "Comm. Services",
    score: 61,
    change: 0.4,
    phase: "Expansion" as const,
    weight: 9.2,
  },
  {
    name: "Industrials",
    score: 58,
    change: -1.2,
    phase: "Late Cycle" as const,
    weight: 8.8,
  },
  {
    name: "Consumer Staples",
    score: 52,
    change: 0.1,
    phase: "Late Cycle" as const,
    weight: 6.1,
  },
  {
    name: "Energy",
    score: 45,
    change: -3.5,
    phase: "Contraction" as const,
    weight: 3.8,
  },
  {
    name: "Utilities",
    score: 42,
    change: -0.3,
    phase: "Recovery" as const,
    weight: 2.5,
  },
  {
    name: "Real Estate",
    score: 35,
    change: -2.8,
    phase: "Contraction" as const,
    weight: 2.2,
  },
  {
    name: "Materials",
    score: 38,
    change: -1.9,
    phase: "Recovery" as const,
    weight: 2.4,
  },
];

const sectorRotation = Array.from({ length: 12 }, (_, i) => ({
  month: [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ][i],
  tech: 28 + Math.round(Math.sin(i * 0.5) * 3),
  health: 13 + Math.round(Math.cos(i * 0.4) * 2),
  finance: 12 + Math.round(Math.sin(i * 0.3) * 2),
  energy: 4 + Math.round(Math.cos(i * 0.6) * 1.5),
}));

/* ── Risk Monitor ── */
const riskMetrics = [
  { name: "VIX", value: "14.2", level: "Low", color: GREEN, threshold: "<20" },
  {
    name: "MOVE Index",
    value: "98.5",
    level: "Normal",
    color: GREEN,
    threshold: "<120",
  },
  {
    name: "US HY Spread",
    value: "142 bps",
    level: "Tight",
    color: GREEN,
    threshold: "<200",
  },
  {
    name: "TED Spread",
    value: "22 bps",
    level: "Normal",
    color: GREEN,
    threshold: "<50",
  },
  {
    name: "EM Sovereign CDS",
    value: "185 bps",
    level: "Watch",
    color: AMBER,
    threshold: "<150",
  },
  {
    name: "SKEW Index",
    value: "148.2",
    level: "Elevated",
    color: AMBER,
    threshold: "<140",
  },
  {
    name: "Put/Call Ratio",
    value: "0.82",
    level: "Normal",
    color: GREEN,
    threshold: "<1.0",
  },
  {
    name: "Margin Debt Chg",
    value: "+2.1%",
    level: "Normal",
    color: GREEN,
    threshold: "<5%",
  },
];

const stressIndex = Array.from({ length: 52 }, (_, i) => ({
  week: `W${i + 1}`,
  financial: +(0.2 + Math.sin(i * 0.12) * 0.3 + Math.random() * 0.1).toFixed(2),
  credit: +(0.15 + Math.cos(i * 0.1) * 0.25 + Math.random() * 0.08).toFixed(2),
  equity: +(0.18 + Math.sin(i * 0.15) * 0.35 + Math.random() * 0.12).toFixed(2),
}));

const geopoliticalRisks = [
  {
    region: "Middle East",
    level: "High",
    score: 78,
    trend: "Rising",
    impact: "Energy prices, shipping",
  },
  {
    region: "US-China",
    level: "Medium",
    score: 62,
    trend: "Stable",
    impact: "Tech supply chain, tariffs",
  },
  {
    region: "Europe (East)",
    level: "High",
    score: 75,
    trend: "Stable",
    impact: "Gas prices, defense spend",
  },
  {
    region: "Taiwan Strait",
    level: "Medium",
    score: 58,
    trend: "Falling",
    impact: "Semiconductor supply",
  },
  {
    region: "LATAM Politics",
    level: "Low",
    score: 35,
    trend: "Stable",
    impact: "Commodity exports, FX",
  },
];

/* ═══════════════════════════════════════════
   HELPERS
═══════════════════════════════════════════ */
function corrColor(v: number): string {
  if (v >= 0.7) return "rgba(16,185,129,0.6)";
  if (v >= 0.3) return "rgba(16,185,129,0.3)";
  if (v >= -0.3) return "rgba(100,116,139,0.2)";
  if (v >= -0.7) return "rgba(239,68,68,0.3)";
  return "rgba(239,68,68,0.6)";
}

function signalDot(s: string) {
  const c = s === "green" ? GREEN : s === "yellow" ? AMBER : RED;
  return (
    <div
      style={{
        width: 12,
        height: 12,
        borderRadius: "50%",
        backgroundColor: c,
        boxShadow: `0 0 8px ${c}`,
      }}
    />
  );
}

const phaseColor = (p: string) =>
  p === "Expansion"
    ? GREEN
    : p === "Late Cycle"
      ? AMBER
      : p === "Contraction"
        ? RED
        : CYAN;

/* ═══════════════════════════════════════════
   COMPONENT
═══════════════════════════════════════════ */
export default function Intelligence() {
  const { data: indicesData } = useIndices();
  const { data: macroData } = useMacro();
  const usingFallback = !indicesData && !macroData;
  const [tab, setTab] = useState<Tab>("Regime");

  const displaySectors = useMemo(() => {
    if (!indicesData) return SECTORS;
    const live = Object.values(indicesData)
      .flat()
      .map((idx: IndexItem) => ({
        name: idx.name,
        score: Math.round(50 + idx.change.percent * 10),
        change: idx.change.percent,
        phase: (idx.change.percent > 1
          ? "Expansion"
          : idx.change.percent > 0
            ? "Late Cycle"
            : idx.change.percent > -1
              ? "Recovery"
              : "Contraction") as
          | "Expansion"
          | "Late Cycle"
          | "Recovery"
          | "Contraction",
        weight: 9.1,
      }));
    return live.length > 0 ? live : SECTORS;
  }, [indicesData]);

  const displayMacroSignals = useMemo(() => {
    if (!macroData?.indicators) return MACRO_SIGNALS;
    const live = macroData.indicators
      .slice(0, 8)
      .map((ind: MacroIndicator) => ({
        name: ind.indicator,
        value: `${ind.value}${ind.unit}`,
        signal: (ind.previous != null
          ? ind.value >= ind.previous
            ? "green"
            : "red"
          : "yellow") as "green" | "yellow" | "red",
        desc: `Previous: ${ind.previous ?? "—"}`,
      }));
    return live.length > 0 ? live : MACRO_SIGNALS;
  }, [macroData]);

  const kpi = (label: string, value: string, sub: string, color: string) => (
    <div
      style={{
        backgroundColor: "rgba(10,14,26,0.5)",
        borderRadius: 10,
        padding: 14,
        border: "1px solid rgba(51,65,85,0.2)",
      }}
    >
      <div style={{ fontSize: 11, color: "#64748B", marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color, fontFamily: mono }}>
        {value}
      </div>
      <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>{sub}</div>
    </div>
  );

  return (
    <div style={{ color: "#F1F5F9" }}>
      <h1 style={{ fontFamily: mono, fontSize: 24, marginBottom: 4 }}>
        Intelligence Center
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        Market regime, factor analysis, cross-asset & risk monitoring
      </p>

      {usingFallback && (
        <div
          style={{
            background: "rgba(245,158,11,0.08)",
            border: "1px solid rgba(245,158,11,0.2)",
            borderRadius: 8,
            padding: "8px 14px",
            marginBottom: 12,
            fontSize: 12,
            color: AMBER,
          }}
        >
          Backend unreachable — showing demo data
        </div>
      )}

      <div
        style={{ display: "flex", gap: 4, marginBottom: 18, flexWrap: "wrap" }}
      >
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "7px 16px",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              border: "none",
              backgroundColor: tab === t ? GOLD : "rgba(30,41,59,0.5)",
              color: tab === t ? "#0A0E1A" : "#94A3B8",
              transition: "all .2s",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ═══════════ Regime ═══════════ */}
      {tab === "Regime" && (
        <>
          <Card>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 20,
                flexWrap: "wrap",
                marginBottom: 16,
              }}
            >
              <div>
                <div
                  style={{ fontSize: 12, color: "#94A3B8", marginBottom: 4 }}
                >
                  MARKET REGIME
                </div>
                <div
                  style={{
                    fontSize: 32,
                    fontWeight: 700,
                    color: GREEN,
                    fontFamily: mono,
                  }}
                >
                  Bull Market
                </div>
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                {[
                  { label: "Trend Strength", value: "78/100", color: CYAN },
                  { label: "Volatility", value: "Low Vol", color: GREEN },
                  { label: "Breadth", value: "67% > 200MA", color: GOLD },
                  { label: "Risk Appetite", value: "Risk-On", color: GREEN },
                ].map((m) => (
                  <div
                    key={m.label}
                    style={{
                      backgroundColor: "rgba(10,14,26,0.5)",
                      borderRadius: 8,
                      padding: "8px 14px",
                    }}
                  >
                    <div style={{ fontSize: 11, color: "#64748B" }}>
                      {m.label}
                    </div>
                    <div
                      style={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: m.color,
                        fontFamily: mono,
                      }}
                    >
                      {m.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              margin: "16px 0",
            }}
          >
            {regimeProbabilities.map((r) => (
              <div
                key={r.regime}
                style={{
                  backgroundColor: "rgba(10,14,26,0.5)",
                  borderRadius: 10,
                  padding: 14,
                  border: "1px solid rgba(51,65,85,0.2)",
                }}
              >
                <div
                  style={{ fontSize: 11, color: "#64748B", marginBottom: 4 }}
                >
                  {r.regime}
                </div>
                <div
                  style={{
                    fontSize: 26,
                    fontWeight: 700,
                    color: r.color,
                    fontFamily: mono,
                  }}
                >
                  {r.prob}%
                </div>
                <div
                  style={{
                    width: "100%",
                    height: 4,
                    borderRadius: 2,
                    backgroundColor: "rgba(51,65,85,0.3)",
                    marginTop: 6,
                  }}
                >
                  <div
                    style={{
                      width: `${r.prob}%`,
                      height: 4,
                      borderRadius: 2,
                      backgroundColor: r.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 16,
            }}
          >
            <Card
              title="Regime Score (60d)"
              subtitle="Composite bull/bear indicator"
            >
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <AreaChart data={regimeHistory}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="day"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                    />
                    <YAxis
                      domain={[0, 100]}
                      tick={{ fill: "#64748B", fontSize: 10 }}
                    />
                    <Tooltip contentStyle={ttStyle} />
                    <ReferenceLine
                      y={70}
                      stroke={GREEN}
                      strokeDasharray="4 4"
                    />
                    <ReferenceLine y={30} stroke={RED} strokeDasharray="4 4" />
                    <Area
                      type="monotone"
                      dataKey="score"
                      stroke={CYAN}
                      fill={CYAN}
                      fillOpacity={0.15}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card
              title="Macro Signal Dashboard"
              subtitle="Economic indicators with traffic light status"
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {displayMacroSignals.map((s) => (
                  <div
                    key={s.name}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      backgroundColor: "rgba(10,14,26,0.5)",
                      borderRadius: 8,
                      padding: "8px 12px",
                    }}
                  >
                    <div>
                      <div style={{ color: "#F1F5F9", fontSize: 13 }}>
                        {s.name}
                      </div>
                      <div style={{ color: "#64748B", fontSize: 10 }}>
                        {s.desc}
                      </div>
                    </div>
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 8 }}
                    >
                      <span
                        style={{
                          fontFamily: mono,
                          fontSize: 13,
                          color: "#94A3B8",
                        }}
                      >
                        {s.value}
                      </span>
                      {signalDot(s.signal)}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}

      {/* ═══════════ Factor Analysis ═══════════ */}
      {tab === "Factor Analysis" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi("Top Factor", "Growth", "+9.8% YTD", GREEN)}
            {kpi("Worst Factor", "Size (SMB)", "-1.8% YTD", RED)}
            {kpi("Best Sharpe", "0.95", "Growth factor", GOLD)}
            {kpi("Avg IC", "0.034", "7 factors", CYAN)}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 16,
            }}
          >
            <Card
              title="Factor Monthly Returns"
              subtitle="Long-short factor performance"
            >
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <LineChart data={factorReturns}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="month"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                    />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip contentStyle={ttStyle} />
                    <ReferenceLine y={0} stroke="rgba(100,116,139,0.4)" />
                    <Line
                      type="monotone"
                      dataKey="momentum"
                      stroke={CYAN}
                      strokeWidth={2}
                      dot={false}
                      name="Momentum"
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke={GOLD}
                      strokeWidth={2}
                      dot={false}
                      name="Value"
                    />
                    <Line
                      type="monotone"
                      dataKey="quality"
                      stroke={GREEN}
                      strokeWidth={2}
                      dot={false}
                      name="Quality"
                    />
                    <Line
                      type="monotone"
                      dataKey="size"
                      stroke={PURPLE}
                      strokeWidth={2}
                      dot={false}
                      name="Size"
                    />
                    <Line
                      type="monotone"
                      dataKey="lowVol"
                      stroke={AMBER}
                      strokeWidth={2}
                      dot={false}
                      name="Low Vol"
                    />
                    <Legend />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card
              title="Factor Exposure Radar"
              subtitle="Index factor tilts (0-100)"
            >
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <RadarChart data={factorExposure}>
                    <PolarGrid stroke="rgba(51,65,85,0.3)" />
                    <PolarAngleAxis
                      dataKey="factor"
                      tick={{ fill: "#94A3B8", fontSize: 11 }}
                    />
                    <PolarRadiusAxis tick={{ fill: "#64748B", fontSize: 9 }} />
                    <Radar
                      name="S&P 500"
                      dataKey="sp500"
                      stroke={CYAN}
                      fill={CYAN}
                      fillOpacity={0.15}
                    />
                    <Radar
                      name="NASDAQ"
                      dataKey="nasdaq"
                      stroke={GOLD}
                      fill={GOLD}
                      fillOpacity={0.15}
                    />
                    <Radar
                      name="Russell 2000"
                      dataKey="russell"
                      stroke={PURPLE}
                      fill={PURPLE}
                      fillOpacity={0.15}
                    />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
          <Card
            title="Factor Performance Summary"
            subtitle="YTD metrics for systematic factors"
          >
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {[
                      "Factor",
                      "YTD %",
                      "Sharpe",
                      "Max DD",
                      "Turnover %",
                      "IC",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 10px",
                          textAlign: h === "Factor" ? "left" : "center",
                          fontSize: 11,
                          color: "#94A3B8",
                          borderBottom: "1px solid rgba(51,65,85,0.3)",
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {factorTable.map((f) => (
                    <tr
                      key={f.name}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                    >
                      <td
                        style={{
                          padding: "6px 10px",
                          fontWeight: 600,
                          color: "#F1F5F9",
                        }}
                      >
                        {f.name}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 13,
                          color: f.ytd >= 0 ? GREEN : RED,
                        }}
                      >
                        {f.ytd > 0 ? "+" : ""}
                        {f.ytd}%
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 13,
                        }}
                      >
                        {f.sharpe.toFixed(2)}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 13,
                          color: RED,
                        }}
                      >
                        {f.maxDD}%
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 13,
                          color: "#94A3B8",
                        }}
                      >
                        {f.turnover}%
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 13,
                          color: f.ic > 0.035 ? GREEN : AMBER,
                        }}
                      >
                        {f.ic.toFixed(3)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ═══════════ Cross-Asset ═══════════ */}
      {tab === "Cross-Asset" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi("Stock-Bond Corr.", "-0.45", "SPY vs TLT", CYAN)}
            {kpi("USD Strength", "-0.38", "DXY vs SPY", AMBER)}
            {kpi("Gold Hedge", "+0.35", "GLD vs TLT", GOLD)}
            {kpi("BTC Equity Corr.", "+0.55", "vs QQQ", PURPLE)}
          </div>
          <Card
            title="Cross-Asset Correlation Matrix"
            subtitle="Rolling 60-day pairwise correlations (8 assets)"
          >
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "separate",
                  borderSpacing: 3,
                }}
              >
                <thead>
                  <tr>
                    <th style={{ padding: 6 }} />
                    {CORRELATION_ASSETS.map((a) => (
                      <th
                        key={a}
                        style={{
                          padding: 6,
                          color: CYAN,
                          fontFamily: mono,
                          fontWeight: 600,
                          fontSize: 11,
                          textAlign: "center",
                        }}
                      >
                        {a}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {CORRELATION_ASSETS.map((a, i) => (
                    <tr key={a}>
                      <td
                        style={{
                          padding: 6,
                          color: CYAN,
                          fontFamily: mono,
                          fontWeight: 600,
                          fontSize: 11,
                        }}
                      >
                        {a}
                      </td>
                      {CORR_MATRIX[i].map((v, j) => (
                        <td
                          key={j}
                          style={{
                            padding: 5,
                            textAlign: "center",
                            fontFamily: mono,
                            fontSize: 11,
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
            </div>
          </Card>
          <div style={{ marginTop: 16 }}>
            <Card
              title="Relative Performance (52 weeks)"
              subtitle="Indexed to 100 at start"
            >
              <div style={{ width: "100%", height: 300 }}>
                <ResponsiveContainer>
                  <LineChart data={crossAssetPerf}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="week"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                      interval={7}
                    />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip contentStyle={ttStyle} />
                    <ReferenceLine
                      y={100}
                      stroke="rgba(100,116,139,0.3)"
                      strokeDasharray="4 4"
                    />
                    <Line
                      type="monotone"
                      dataKey="spy"
                      stroke={CYAN}
                      strokeWidth={2}
                      dot={false}
                      name="SPY"
                    />
                    <Line
                      type="monotone"
                      dataKey="tlt"
                      stroke={GOLD}
                      strokeWidth={2}
                      dot={false}
                      name="TLT"
                    />
                    <Line
                      type="monotone"
                      dataKey="gld"
                      stroke={AMBER}
                      strokeWidth={2}
                      dot={false}
                      name="GLD"
                    />
                    <Line
                      type="monotone"
                      dataKey="btc"
                      stroke={PURPLE}
                      strokeWidth={2}
                      dot={false}
                      name="BTC"
                    />
                    <Legend />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}

      {/* ═══════════ Sector Rotation ═══════════ */}
      {tab === "Sector Rotation" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi("Strongest", "Tech (82)", "+3.2% WoW", GREEN)}
            {kpi("Weakest", "Real Estate (35)", "-2.8% WoW", RED)}
            {kpi("Avg Score", "56.0", "11 GICS sectors", CYAN)}
            {kpi("Phase", "Expansion", "62% probability", GOLD)}
          </div>
          <Card
            title="Sector Momentum Ranking"
            subtitle="Relative strength score & business cycle phase"
          >
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {[
                      "Sector",
                      "Score",
                      "7d Chg",
                      "Phase",
                      "S&P Wgt",
                      "Strength",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 10px",
                          textAlign: h === "Sector" ? "left" : "center",
                          fontSize: 11,
                          color: "#94A3B8",
                          borderBottom: "1px solid rgba(51,65,85,0.3)",
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {displaySectors.map((s) => (
                    <tr
                      key={s.name}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                    >
                      <td
                        style={{
                          padding: "6px 10px",
                          fontWeight: 600,
                          color: "#F1F5F9",
                        }}
                      >
                        {s.name}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 14,
                          fontWeight: 700,
                          color:
                            s.score >= 60 ? GREEN : s.score >= 45 ? AMBER : RED,
                        }}
                      >
                        {s.score}
                      </td>
                      <td style={{ padding: "6px 10px", textAlign: "center" }}>
                        <Badge
                          variant={
                            s.change > 0
                              ? "up"
                              : s.change < 0
                                ? "down"
                                : "neutral"
                          }
                        >
                          {s.change > 0 ? "+" : ""}
                          {s.change.toFixed(1)}
                        </Badge>
                      </td>
                      <td style={{ padding: "6px 10px", textAlign: "center" }}>
                        <span
                          style={{
                            padding: "2px 10px",
                            borderRadius: 12,
                            fontSize: 11,
                            fontWeight: 600,
                            backgroundColor: `${phaseColor(s.phase)}15`,
                            color: phaseColor(s.phase),
                          }}
                        >
                          {s.phase}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          color: "#94A3B8",
                        }}
                      >
                        {s.weight}%
                      </td>
                      <td style={{ padding: "6px 10px" }}>
                        <div
                          style={{
                            width: 80,
                            height: 6,
                            backgroundColor: "rgba(51,65,85,0.3)",
                            borderRadius: 3,
                            margin: "0 auto",
                          }}
                        >
                          <div
                            style={{
                              width: `${s.score}%`,
                              height: 6,
                              borderRadius: 3,
                              backgroundColor:
                                s.score >= 60
                                  ? GREEN
                                  : s.score >= 45
                                    ? AMBER
                                    : RED,
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <div style={{ marginTop: 16 }}>
            <Card
              title="Sector Weight Drift"
              subtitle="Monthly allocation shift in top sectors"
            >
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <AreaChart data={sectorRotation}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="month"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                    />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip contentStyle={ttStyle} />
                    <Area
                      type="monotone"
                      dataKey="tech"
                      stackId="1"
                      stroke={CYAN}
                      fill={CYAN}
                      fillOpacity={0.3}
                      name="Technology"
                    />
                    <Area
                      type="monotone"
                      dataKey="health"
                      stackId="1"
                      stroke={PURPLE}
                      fill={PURPLE}
                      fillOpacity={0.2}
                      name="Healthcare"
                    />
                    <Area
                      type="monotone"
                      dataKey="finance"
                      stackId="1"
                      stroke={GOLD}
                      fill={GOLD}
                      fillOpacity={0.2}
                      name="Financials"
                    />
                    <Area
                      type="monotone"
                      dataKey="energy"
                      stackId="1"
                      stroke={RED}
                      fill={RED}
                      fillOpacity={0.2}
                      name="Energy"
                    />
                    <Legend />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}

      {/* ═══════════ Risk Monitor ═══════════ */}
      {tab === "Risk Monitor" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi("Systemic Risk", "Low", "composite index", GREEN)}
            {kpi("VIX", "14.2", "below avg (19.5)", GREEN)}
            {kpi("Credit Stress", "142 bps", "HY OAS", GREEN)}
            {kpi("Geo Risk", "Elevated", "2 hotspots", AMBER)}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 16,
            }}
          >
            <Card
              title="Risk Indicator Dashboard"
              subtitle="Real-time stress signals"
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 8,
                }}
              >
                {riskMetrics.map((r) => (
                  <div
                    key={r.name}
                    style={{
                      backgroundColor: "rgba(10,14,26,0.5)",
                      borderRadius: 8,
                      padding: 10,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 11, color: "#64748B" }}>
                        {r.name}
                      </div>
                      <div
                        style={{
                          fontSize: 16,
                          fontWeight: 700,
                          color: r.color,
                          fontFamily: mono,
                        }}
                      >
                        {r.value}
                      </div>
                      <div style={{ fontSize: 10, color: "#64748B" }}>
                        Threshold: {r.threshold}
                      </div>
                    </div>
                    <span
                      style={{
                        padding: "3px 8px",
                        borderRadius: 6,
                        fontSize: 10,
                        fontWeight: 600,
                        backgroundColor: `${r.color}20`,
                        color: r.color,
                      }}
                    >
                      {r.level}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
            <Card
              title="Financial Stress Index"
              subtitle="52-week decomposition by type"
            >
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <AreaChart data={stressIndex}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="week"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                      interval={7}
                    />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip contentStyle={ttStyle} />
                    <Area
                      type="monotone"
                      dataKey="financial"
                      stackId="1"
                      stroke={CYAN}
                      fill={CYAN}
                      fillOpacity={0.2}
                      name="Financial"
                    />
                    <Area
                      type="monotone"
                      dataKey="credit"
                      stackId="1"
                      stroke={GOLD}
                      fill={GOLD}
                      fillOpacity={0.2}
                      name="Credit"
                    />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stackId="1"
                      stroke={RED}
                      fill={RED}
                      fillOpacity={0.2}
                      name="Equity"
                    />
                    <Legend />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
          <Card
            title="Geopolitical Risk Monitor"
            subtitle="Regional risk assessment & market impact"
          >
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {[
                      "Region",
                      "Risk Level",
                      "Score",
                      "Trend",
                      "Market Impact",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 10px",
                          textAlign: h === "Market Impact" ? "left" : "center",
                          fontSize: 11,
                          color: "#94A3B8",
                          borderBottom: "1px solid rgba(51,65,85,0.3)",
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {geopoliticalRisks.map((g) => (
                    <tr
                      key={g.region}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                    >
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontWeight: 600,
                          color: "#F1F5F9",
                        }}
                      >
                        {g.region}
                      </td>
                      <td style={{ padding: "6px 10px", textAlign: "center" }}>
                        <span
                          style={{
                            padding: "2px 10px",
                            borderRadius: 12,
                            fontSize: 11,
                            fontWeight: 600,
                            backgroundColor:
                              g.level === "High"
                                ? "rgba(239,68,68,0.15)"
                                : g.level === "Medium"
                                  ? "rgba(245,158,11,0.15)"
                                  : "rgba(16,185,129,0.15)",
                            color:
                              g.level === "High"
                                ? RED
                                : g.level === "Medium"
                                  ? AMBER
                                  : GREEN,
                          }}
                        >
                          {g.level}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontWeight: 700,
                          color:
                            g.score > 65 ? RED : g.score > 45 ? AMBER : GREEN,
                        }}
                      >
                        {g.score}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontSize: 12,
                          color:
                            g.trend === "Rising"
                              ? RED
                              : g.trend === "Falling"
                                ? GREEN
                                : "#94A3B8",
                        }}
                      >
                        {g.trend === "Rising"
                          ? "▲"
                          : g.trend === "Falling"
                            ? "▼"
                            : "●"}{" "}
                        {g.trend}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          fontSize: 12,
                          color: "#94A3B8",
                        }}
                      >
                        {g.impact}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
