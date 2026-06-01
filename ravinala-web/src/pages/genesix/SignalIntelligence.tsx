import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Card, Tabs } from "../../components/ui";
import { useIndices, useSnapshot } from "../../hooks/useMarketData";

/* ───────────────────────── design tokens ───────────────────────── */
const C = {
  bg: "#0A0E1A",
  card: "#131823",
  border: "rgba(51,65,85,0.3)",
  gold: "#D4AF37",
  cyan: "#00D9FF",
  green: "#10B981",
  red: "#EF4444",
  purple: "#A855F7",
  amber: "#F59E0B",
  blue: "#3B82F6",
  t1: "#F1F5F9",
  t2: "#94A3B8",
  t3: "#64748B",
  mono: "JetBrains Mono, monospace",
  sans: "Inter, sans-serif",
} as const;

/* ───────────────────── original 12 signal cards ────────────────── */
const SIGNALS = [
  {
    ticker: "NVDA",
    type: "Buy" as const,
    strategy: "Momentum",
    entry: 862.5,
    target: 920.0,
    stop: 840.0,
    confidence: 88,
    timeframe: "1W",
  },
  {
    ticker: "AAPL",
    type: "Buy" as const,
    strategy: "Mean Reversion",
    entry: 196.2,
    target: 210.0,
    stop: 190.0,
    confidence: 74,
    timeframe: "2W",
  },
  {
    ticker: "TSLA",
    type: "Sell" as const,
    strategy: "Breakdown",
    entry: 248.0,
    target: 215.0,
    stop: 260.0,
    confidence: 72,
    timeframe: "1W",
  },
  {
    ticker: "META",
    type: "Buy" as const,
    strategy: "Earnings Momentum",
    entry: 518.4,
    target: 560.0,
    stop: 500.0,
    confidence: 81,
    timeframe: "1M",
  },
  {
    ticker: "AMZN",
    type: "Buy" as const,
    strategy: "Trend Following",
    entry: 190.5,
    target: 205.0,
    stop: 184.0,
    confidence: 69,
    timeframe: "2W",
  },
  {
    ticker: "XOM",
    type: "Sell" as const,
    strategy: "Sector Rotation",
    entry: 114.2,
    target: 102.0,
    stop: 118.0,
    confidence: 65,
    timeframe: "1M",
  },
  {
    ticker: "AMD",
    type: "Buy" as const,
    strategy: "Breakout",
    entry: 178.8,
    target: 200.0,
    stop: 170.0,
    confidence: 77,
    timeframe: "1W",
  },
  {
    ticker: "JPM",
    type: "Buy" as const,
    strategy: "Value",
    entry: 204.5,
    target: 220.0,
    stop: 196.0,
    confidence: 70,
    timeframe: "1M",
  },
  {
    ticker: "COIN",
    type: "Sell" as const,
    strategy: "Overbought",
    entry: 265.0,
    target: 230.0,
    stop: 280.0,
    confidence: 68,
    timeframe: "2W",
  },
  {
    ticker: "GOOGL",
    type: "Buy" as const,
    strategy: "AI Tailwind",
    entry: 176.8,
    target: 195.0,
    stop: 170.0,
    confidence: 83,
    timeframe: "1M",
  },
  {
    ticker: "PLTR",
    type: "Buy" as const,
    strategy: "Momentum",
    entry: 24.8,
    target: 28.0,
    stop: 23.0,
    confidence: 71,
    timeframe: "1W",
  },
  {
    ticker: "BA",
    type: "Sell" as const,
    strategy: "Fundamentals",
    entry: 192.0,
    target: 170.0,
    stop: 200.0,
    confidence: 66,
    timeframe: "1M",
  },
];

/* ──────────────────── Tab 1: Signals demo data ─────────────────── */
const MARKET_SIGNAL = {
  regime: "Bull",
  score: 72,
  confidence: 85,
  outlook:
    "Positive momentum with low volatility. Breadth improving across sectors with tech leadership intact.",
  favored: ["Tech", "AI", "Semiconductors"],
  avoid: ["Utilities", "Staples"],
};

const ASSET_SIGNALS = [
  {
    ticker: "SPY",
    signal: "Buy" as const,
    score: 74,
    confidence: 81,
    reasons: ["Strong breadth", "Above 200d MA", "Positive momentum"],
    sub: {
      momentum: 78,
      mean_reversion: 62,
      volatility: 71,
      trend: 82,
      ml_ensemble: 77,
    },
  },
  {
    ticker: "QQQ",
    signal: "Buy" as const,
    score: 82,
    confidence: 88,
    reasons: ["AI tailwind", "Mag7 earnings", "Vol compression"],
    sub: {
      momentum: 86,
      mean_reversion: 70,
      volatility: 80,
      trend: 88,
      ml_ensemble: 84,
    },
  },
  {
    ticker: "AAPL",
    signal: "Hold" as const,
    score: 55,
    confidence: 65,
    reasons: ["Near resistance", "Earnings neutral", "iPhone cycle peak"],
    sub: {
      momentum: 52,
      mean_reversion: 60,
      volatility: 55,
      trend: 50,
      ml_ensemble: 58,
    },
  },
  {
    ticker: "MSFT",
    signal: "Buy" as const,
    score: 78,
    confidence: 84,
    reasons: ["Azure growth", "AI monetization", "Margin expansion"],
    sub: {
      momentum: 80,
      mean_reversion: 68,
      volatility: 75,
      trend: 84,
      ml_ensemble: 82,
    },
  },
  {
    ticker: "GLD",
    signal: "Hold" as const,
    score: 48,
    confidence: 60,
    reasons: ["Real rates rising", "DXY strength", "Central bank buying"],
    sub: {
      momentum: 45,
      mean_reversion: 55,
      volatility: 42,
      trend: 48,
      ml_ensemble: 50,
    },
  },
  {
    ticker: "TLT",
    signal: "Sell" as const,
    score: 32,
    confidence: 72,
    reasons: ["Rate cuts delayed", "Supply pressure", "Fiscal deficit"],
    sub: {
      momentum: 28,
      mean_reversion: 40,
      volatility: 30,
      trend: 25,
      ml_ensemble: 35,
    },
  },
];

const EVENT_SIGNALS = [
  {
    time: "2h ago",
    event: "FOMC Minutes — Hawkish tilt detected",
    impact: "Bearish Bonds",
    severity: "high" as const,
  },
  {
    time: "4h ago",
    event: "NVDA earnings beat 15% — AI capex surge",
    impact: "Bullish Tech",
    severity: "high" as const,
  },
  {
    time: "1d ago",
    event: "China PMI expansion 51.2",
    impact: "Bullish EM",
    severity: "medium" as const,
  },
  {
    time: "1d ago",
    event: "VIX below 14 — complacency zone",
    impact: "Caution",
    severity: "low" as const,
  },
];

/* ──────────────── Tab 2: Regime Detection demo data ────────────── */
const REGIMES = ["Low Vol", "Normal", "High Vol", "Crisis"] as const;
const REGIME_COLORS = [C.green, C.cyan, C.amber, C.red];
const CURRENT_REGIME = {
  regime: "Low Vol" as const,
  confidence: 87,
  days: 45,
  transitionProb: 12,
};

const TRANSITION_MATRIX = [
  [0.92, 0.06, 0.02, 0.0],
  [0.08, 0.82, 0.08, 0.02],
  [0.02, 0.1, 0.78, 0.1],
  [0.01, 0.04, 0.15, 0.8],
];
const REGIME_DIST = [
  { name: "Low Vol", value: 35 },
  { name: "Normal", value: 40 },
  { name: "High Vol", value: 18 },
  { name: "Crisis", value: 7 },
];

function seedRand(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return s / 2147483647;
  };
}
const rng = seedRand(42);
const HIST_REGIMES = Array.from({ length: 252 }, (_, i) => {
  const r = rng();
  const regime = r < 0.35 ? 0 : r < 0.75 ? 1 : r < 0.93 ? 2 : 3;
  return { day: i + 1, regime, label: REGIMES[regime] };
});

/* ──────────────────── Tab 3: Contagion demo data ───────────────── */
const CONTAGION_TICKERS = [
  "SPY",
  "QQQ",
  "AAPL",
  "MSFT",
  "GLD",
  "TLT",
  "EEM",
  "HYG",
];
const CORR_MATRIX = [
  [1.0, 0.92, 0.85, 0.88, 0.08, -0.42, 0.72, 0.65],
  [0.92, 1.0, 0.88, 0.91, 0.05, -0.38, 0.68, 0.6],
  [0.85, 0.88, 1.0, 0.82, 0.1, -0.3, 0.62, 0.55],
  [0.88, 0.91, 0.82, 1.0, 0.07, -0.35, 0.65, 0.58],
  [0.08, 0.05, 0.1, 0.07, 1.0, 0.32, 0.22, 0.15],
  [-0.42, -0.38, -0.3, -0.35, 0.32, 1.0, -0.18, -0.1],
  [0.72, 0.68, 0.62, 0.65, 0.22, -0.18, 1.0, 0.7],
  [0.65, 0.6, 0.55, 0.58, 0.15, -0.1, 0.7, 1.0],
];
const NETWORK = { density: 0.45, central: "SPY", contagionRisk: 42 };
const SYSTEMIC_RISKS = [
  {
    severity: "high" as const,
    desc: "Equity-credit correlation spike (SPY-HYG) approaching crisis levels — monitor credit spreads",
  },
  {
    severity: "medium" as const,
    desc: "EM contagion channel active — EEM showing elevated beta to SPY drawdowns",
  },
  {
    severity: "low" as const,
    desc: "Gold-bond decorrelation widening — safe haven rotation may reduce portfolio hedge effectiveness",
  },
];

/* ──────────────────── Tab 4: Smart Alerts demo ─────────────────── */
const ALERTS = [
  {
    severity: "critical" as const,
    ts: "2026-03-22 09:15",
    title: "VaR Breach Warning",
    detail:
      "1-day VaR exceeded 95% threshold for equity sleeve. Portfolio delta exposure +2.3σ above normal.",
    source: "Risk Engine",
    category: "reactive",
  },
  {
    severity: "critical" as const,
    ts: "2026-03-22 08:30",
    title: "Correlation Spike",
    detail:
      "Equity-credit correlation jumped to 0.88 (90th percentile). Diversification benefit degraded.",
    source: "Contagion Monitor",
    category: "predictive",
  },
  {
    severity: "warning" as const,
    ts: "2026-03-21 16:00",
    title: "Sector Concentration",
    detail:
      "Tech allocation 42% exceeds 35% limit. Consider rebalancing toward underweight sectors.",
    source: "Portfolio Optimizer",
    category: "reactive",
  },
  {
    severity: "warning" as const,
    ts: "2026-03-21 14:22",
    title: "Volatility Regime Shift",
    detail:
      "Regime model detects transition from Low Vol to Normal (p=0.23). Tail hedges may cheapen.",
    source: "Regime Engine",
    category: "predictive",
  },
  {
    severity: "info" as const,
    ts: "2026-03-21 10:00",
    title: "Rebalancing Opportunity",
    detail:
      "Portfolio drift >5% from target. Expected rebalance cost $12k. Optimal window before FOMC.",
    source: "Rebalancer",
    category: "opportunity",
  },
  {
    severity: "info" as const,
    ts: "2026-03-20 15:45",
    title: "Earnings Season Start",
    detail:
      "18 portfolio holdings report next week. Implied vol elevated — consider collar strategy.",
    source: "Event Scanner",
    category: "opportunity",
  },
];

/* ────────────── Tab 5: Correlation Dynamics demo ───────────────── */
const CORR_PAIRS = [
  "SPY-QQQ",
  "SPY-TLT",
  "GLD-TLT",
  "SPY-EEM",
  "QQQ-AAPL",
] as const;
const PAIR_COLORS = [C.cyan, C.red, C.gold, C.green, C.purple];
const rng2 = seedRand(99);
const ROLLING_CORR = Array.from({ length: 252 }, (_, i) => {
  const base = [0.92, -0.4, 0.3, 0.72, 0.88];
  const row: Record<string, number> = { day: i + 1 };
  CORR_PAIRS.forEach((p, j) => {
    row[p] = Math.max(-1, Math.min(1, base[j] + (rng2() - 0.5) * 0.15));
  });
  return row;
});
const INSTABILITY = CORR_PAIRS.map((p) => ({
  pair: p,
  instability: +(0.03 + rng2() * 0.12).toFixed(3),
}));

/* ──────────────────────── helpers ───────────────────────────────── */
const TABS_LIST = [
  "Signals",
  "Regime Detection",
  "Contagion",
  "Smart Alerts",
  "Correlation Dynamics",
];

function corrColor(v: number): string {
  if (v >= 0.6) return `rgba(16,185,129,${(0.3 + v * 0.5).toFixed(2)})`;
  if (v >= 0.2) return `rgba(16,185,129,${(0.1 + v * 0.3).toFixed(2)})`;
  if (v >= -0.2) return "rgba(100,116,139,0.15)";
  if (v >= -0.6)
    return `rgba(239,68,68,${(0.1 + Math.abs(v) * 0.3).toFixed(2)})`;
  return `rgba(239,68,68,${(0.3 + Math.abs(v) * 0.5).toFixed(2)})`;
}

function signalBadge(s: string) {
  if (s === "Buy") return "up" as const;
  if (s === "Sell") return "down" as const;
  return "neutral" as const;
}

function severityStyle(s: string) {
  if (s === "critical" || s === "high")
    return {
      bg: "rgba(239,68,68,0.12)",
      border: "rgba(239,68,68,0.3)",
      color: C.red,
      icon: "🔴",
    };
  if (s === "warning" || s === "medium")
    return {
      bg: "rgba(245,158,11,0.12)",
      border: "rgba(245,158,11,0.3)",
      color: C.amber,
      icon: "🟡",
    };
  return {
    bg: "rgba(59,130,246,0.12)",
    border: "rgba(59,130,246,0.3)",
    color: C.blue,
    icon: "🔵",
  };
}

const SubScore = ({ label, value }: { label: string; value: number }) => (
  <div
    style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}
  >
    <span style={{ color: C.t3 }}>{label}</span>
    <span
      style={{
        fontFamily: C.mono,
        color: value >= 70 ? C.green : value >= 50 ? C.amber : C.red,
      }}
    >
      {value}
    </span>
  </div>
);

const thStyle: React.CSSProperties = {
  padding: "8px 10px",
  fontFamily: C.mono,
  fontSize: 11,
  color: C.t3,
  borderBottom: `1px solid ${C.border}`,
  textAlign: "left",
  fontWeight: 600,
};
const tdStyle: React.CSSProperties = {
  padding: "8px 10px",
  fontFamily: C.mono,
  fontSize: 12,
  color: C.t1,
  borderBottom: "1px solid rgba(51,65,85,0.15)",
};

/* ══════════════════════════ COMPONENT ══════════════════════════ */
export default function SignalIntelligence() {
  const [activeTab, setActiveTab] = useState(TABS_LIST[0]);
  const { data: indicesData } = useIndices();
  const { data: snapshotData } = useSnapshot();
  const liveData = indicesData ?? snapshotData ?? null;

  /* Enrich original signal cards with live prices */
  const displaySignals = useMemo(() => {
    if (!indicesData && !snapshotData) return SIGNALS;
    const allIndices = indicesData
      ? Object.values(indicesData).flat()
      : snapshotData?.indices
        ? Object.values(snapshotData.indices).flat()
        : [];
    if (allIndices.length === 0) return SIGNALS;
    const priceLookup = new Map(
      allIndices.map((idx: any) => [idx.symbol, idx.price]),
    );
    return SIGNALS.map((sig) => {
      const livePrice = priceLookup.get(sig.ticker);
      return livePrice ? { ...sig, entry: livePrice } : sig;
    });
  }, [indicesData, snapshotData]);

  const buyCount = displaySignals.filter((s) => s.type === "Buy").length;
  const sellCount = displaySignals.filter((s) => s.type === "Sell").length;
  const avgConf = Math.round(
    displaySignals.reduce((a, s) => a + s.confidence, 0) /
      displaySignals.length,
  );

  /* ──────────────────────── TAB 1: Signals ──────────────────────── */
  const renderSignals = () => (
    <>
      {/* Summary row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: 10,
          marginBottom: 16,
        }}
      >
        {[
          {
            label: "Active Signals",
            value: `${displaySignals.length}`,
            color: C.gold,
          },
          { label: "Buy Signals", value: `${buyCount}`, color: C.green },
          { label: "Sell Signals", value: `${sellCount}`, color: C.red },
          { label: "Avg Confidence", value: `${avgConf}%`, color: C.cyan },
        ].map((m) => (
          <Card key={m.label}>
            <div style={{ fontSize: 11, color: C.t3, marginBottom: 2 }}>
              {m.label}
            </div>
            <div
              style={{
                fontSize: 20,
                fontWeight: 700,
                fontFamily: C.mono,
                color: m.color,
              }}
            >
              {m.value}
            </div>
          </Card>
        ))}
      </div>

      {/* Market Signal */}
      <Card title="Market Signal">
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 16,
            alignItems: "center",
            marginBottom: 12,
          }}
        >
          <Badge variant="up">{MARKET_SIGNAL.regime}</Badge>
          <span style={{ fontFamily: C.mono, fontSize: 22, color: C.gold }}>
            {MARKET_SIGNAL.score}
          </span>
          <span style={{ fontSize: 12, color: C.t2 }}>
            Confidence{" "}
            <b style={{ color: C.cyan }}>{MARKET_SIGNAL.confidence}%</b>
          </span>
        </div>
        <p
          style={{
            fontSize: 13,
            color: C.t2,
            marginBottom: 12,
            lineHeight: 1.5,
          }}
        >
          {MARKET_SIGNAL.outlook}
        </p>
        <div style={{ display: "flex", gap: 24, fontSize: 12 }}>
          <div>
            <span style={{ color: C.t3 }}>Favored: </span>
            {MARKET_SIGNAL.favored.map((f) => (
              <Badge key={f} variant="up">
                {f}
              </Badge>
            ))}
          </div>
          <div>
            <span style={{ color: C.t3 }}>Avoid: </span>
            {MARKET_SIGNAL.avoid.map((a) => (
              <Badge key={a} variant="down">
                {a}
              </Badge>
            ))}
          </div>
        </div>
      </Card>

      {/* Asset Signal Matrix */}
      <Card
        title="Asset Signal Matrix"
        subtitle="Composite signal with sub-signal breakdown"
      >
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Ticker", "Signal", "Score", "Confidence", "Key Reasons"].map(
                  (h) => (
                    <th key={h} style={thStyle}>
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {ASSET_SIGNALS.map((a) => (
                <tr key={a.ticker}>
                  <td style={{ ...tdStyle, color: C.gold, fontWeight: 700 }}>
                    {a.ticker}
                  </td>
                  <td style={tdStyle}>
                    <Badge variant={signalBadge(a.signal)}>{a.signal}</Badge>
                  </td>
                  <td style={tdStyle}>{a.score}</td>
                  <td style={tdStyle}>{a.confidence}%</td>
                  <td
                    style={{
                      ...tdStyle,
                      fontFamily: C.sans,
                      fontSize: 12,
                      color: C.t2,
                    }}
                  >
                    {a.reasons.join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Sub-signals breakdown */}
      <Card title="Sub-Signal Breakdown">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: 12,
          }}
        >
          {ASSET_SIGNALS.map((a) => (
            <div
              key={a.ticker}
              style={{
                background: "rgba(10,14,26,0.5)",
                borderRadius: 8,
                padding: 12,
                border: `1px solid ${C.border}`,
              }}
            >
              <div
                style={{
                  fontFamily: C.mono,
                  fontWeight: 700,
                  color: C.gold,
                  marginBottom: 8,
                }}
              >
                {a.ticker}
              </div>
              <SubScore label="Momentum" value={a.sub.momentum} />
              <SubScore label="Mean Reversion" value={a.sub.mean_reversion} />
              <SubScore label="Volatility" value={a.sub.volatility} />
              <SubScore label="Trend" value={a.sub.trend} />
              <SubScore label="ML Ensemble" value={a.sub.ml_ensemble} />
            </div>
          ))}
        </div>
      </Card>

      {/* Event Signals */}
      <Card title="Event Signals">
        {EVENT_SIGNALS.map((e, i) => {
          const sev = severityStyle(e.severity);
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "8px 0",
                borderBottom:
                  i < EVENT_SIGNALS.length - 1
                    ? "1px solid rgba(51,65,85,0.15)"
                    : undefined,
              }}
            >
              <span>{sev.icon}</span>
              <span
                style={{
                  fontSize: 11,
                  color: C.t3,
                  fontFamily: C.mono,
                  width: 52,
                  flexShrink: 0,
                }}
              >
                {e.time}
              </span>
              <span style={{ flex: 1, fontSize: 13, color: C.t1 }}>
                {e.event}
              </span>
              <Badge
                variant={
                  e.severity === "high"
                    ? "warning"
                    : e.severity === "medium"
                      ? "neutral"
                      : "info"
                }
              >
                {e.impact}
              </Badge>
            </div>
          );
        })}
      </Card>

      {/* Original 12 Signal Cards grid */}
      <Card
        title="Signal Grid"
        subtitle="Algorithmic buy/sell signals with entry, target & stop levels"
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: 12,
          }}
        >
          {displaySignals.map((s, i) => (
            <div
              key={i}
              style={{
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 10,
                padding: 14,
                border: `1px solid ${s.type === "Buy" ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span
                    style={{
                      fontFamily: C.mono,
                      fontWeight: 700,
                      fontSize: 16,
                      color: C.gold,
                    }}
                  >
                    {s.ticker}
                  </span>
                  <Badge variant={s.type === "Buy" ? "up" : "down"}>
                    {s.type}
                  </Badge>
                </div>
                <span style={{ fontSize: 11, color: C.t3 }}>{s.timeframe}</span>
              </div>
              <div style={{ fontSize: 12, color: C.t2, marginBottom: 8 }}>
                {s.strategy}
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: 6,
                  fontSize: 12,
                }}
              >
                <div>
                  <div style={{ color: C.t3, fontSize: 10 }}>Entry</div>
                  <div style={{ fontFamily: C.mono, color: C.t1 }}>
                    ${s.entry}
                  </div>
                </div>
                <div>
                  <div style={{ color: C.t3, fontSize: 10 }}>Target</div>
                  <div style={{ fontFamily: C.mono, color: C.green }}>
                    ${s.target}
                  </div>
                </div>
                <div>
                  <div style={{ color: C.t3, fontSize: 10 }}>Stop</div>
                  <div style={{ fontFamily: C.mono, color: C.red }}>
                    ${s.stop}
                  </div>
                </div>
              </div>
              <div
                style={{
                  marginTop: 8,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <div
                  style={{
                    flex: 1,
                    height: 4,
                    backgroundColor: C.border,
                    borderRadius: 2,
                  }}
                >
                  <div
                    style={{
                      width: `${s.confidence}%`,
                      height: 4,
                      borderRadius: 2,
                      backgroundColor:
                        s.confidence >= 80
                          ? C.green
                          : s.confidence >= 70
                            ? C.amber
                            : C.t2,
                    }}
                  />
                </div>
                <span style={{ fontSize: 11, fontFamily: C.mono, color: C.t2 }}>
                  {s.confidence}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </>
  );

  /* ────────────────── TAB 2: Regime Detection ───────────────────── */
  const renderRegime = () => (
    <>
      {/* Current regime */}
      <Card title="Current Regime">
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 20,
            alignItems: "center",
          }}
        >
          <div
            style={{
              padding: "10px 20px",
              borderRadius: 8,
              background: `${REGIME_COLORS[0]}22`,
              border: `1px solid ${REGIME_COLORS[0]}44`,
            }}
          >
            <div style={{ fontSize: 11, color: C.t3 }}>Regime</div>
            <div
              style={{
                fontSize: 22,
                fontWeight: 700,
                fontFamily: C.mono,
                color: REGIME_COLORS[0],
              }}
            >
              {CURRENT_REGIME.regime}
            </div>
          </div>
          {[
            {
              label: "Confidence",
              value: `${CURRENT_REGIME.confidence}%`,
              color: C.cyan,
            },
            {
              label: "Days in Regime",
              value: `${CURRENT_REGIME.days}`,
              color: C.gold,
            },
            {
              label: "Transition Prob",
              value: `${CURRENT_REGIME.transitionProb}%`,
              color: C.amber,
            },
          ].map((m) => (
            <div key={m.label}>
              <div style={{ fontSize: 11, color: C.t3 }}>{m.label}</div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  fontFamily: C.mono,
                  color: m.color,
                }}
              >
                {m.value}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Historical Regime Chart */}
      <Card
        title="Historical Regime"
        subtitle="Regime assignment over 252 trading days"
      >
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={HIST_REGIMES}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.2)" />
            <XAxis dataKey="day" tick={{ fontSize: 11, fill: C.t3 }} />
            <YAxis
              domain={[0, 3]}
              ticks={[0, 1, 2, 3]}
              tick={{ fontSize: 11, fill: C.t3 }}
              tickFormatter={(v: number) => REGIMES[v] ?? ""}
              width={60}
            />
            <Tooltip
              contentStyle={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 6,
                fontSize: 12,
              }}
              formatter={((v: number) => [REGIMES[v], "Regime"]) as any}
            />
            <Line
              type="stepAfter"
              dataKey="regime"
              stroke={C.cyan}
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Transition Probability Heatmap */}
        <Card title="Transition Probability Matrix">
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={{ ...thStyle, width: 70 }}>From \ To</th>
                {REGIMES.map((r) => (
                  <th key={r} style={thStyle}>
                    {r}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {TRANSITION_MATRIX.map((row, i) => (
                <tr key={i}>
                  <td
                    style={{
                      ...tdStyle,
                      color: REGIME_COLORS[i],
                      fontWeight: 700,
                      fontSize: 11,
                    }}
                  >
                    {REGIMES[i]}
                  </td>
                  {row.map((val, j) => (
                    <td
                      key={j}
                      style={{
                        ...tdStyle,
                        textAlign: "center",
                        backgroundColor: `rgba(59,130,246,${(val * 0.6).toFixed(2)})`,
                        color: val > 0.5 ? "#fff" : C.t1,
                      }}
                    >
                      {(val * 100).toFixed(0)}%
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {/* Regime Distribution */}
        <Card title="Regime Distribution">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={REGIME_DIST}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={85}
                paddingAngle={3}
                label={({ name, value }) => `${name} ${value}%`}
                labelLine={false}
              >
                {REGIME_DIST.map((_, i) => (
                  <Cell key={i} fill={REGIME_COLORS[i]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: C.card,
                  border: `1px solid ${C.border}`,
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </>
  );

  /* ─────────────────── TAB 3: Contagion ─────────────────────────── */
  const renderContagion = () => (
    <>
      {/* Network metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: 10,
          marginBottom: 16,
        }}
      >
        {[
          {
            label: "Network Density",
            value: NETWORK.density.toFixed(2),
            color: C.cyan,
          },
          {
            label: "Most Central Asset",
            value: NETWORK.central,
            color: C.gold,
          },
          {
            label: "Contagion Risk",
            value: `${NETWORK.contagionRisk}/100`,
            color: NETWORK.contagionRisk > 60 ? C.red : C.amber,
          },
        ].map((m) => (
          <Card key={m.label}>
            <div style={{ fontSize: 11, color: C.t3, marginBottom: 2 }}>
              {m.label}
            </div>
            <div
              style={{
                fontSize: 20,
                fontWeight: 700,
                fontFamily: C.mono,
                color: m.color,
              }}
            >
              {m.value}
            </div>
          </Card>
        ))}
      </div>

      {/* Correlation Heatmap */}
      <Card
        title="Correlation Matrix"
        subtitle="Real-time cross-asset correlations"
      >
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={{ ...thStyle, width: 50 }}></th>
                {CONTAGION_TICKERS.map((t) => (
                  <th key={t} style={{ ...thStyle, textAlign: "center" }}>
                    {t}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {CORR_MATRIX.map((row, i) => (
                <tr key={i}>
                  <td
                    style={{
                      ...tdStyle,
                      color: C.gold,
                      fontWeight: 700,
                      fontSize: 11,
                    }}
                  >
                    {CONTAGION_TICKERS[i]}
                  </td>
                  {row.map((val, j) => (
                    <td
                      key={j}
                      style={{
                        ...tdStyle,
                        textAlign: "center",
                        fontFamily: C.mono,
                        fontSize: 11,
                        backgroundColor: corrColor(val),
                        color: Math.abs(val) > 0.6 ? "#fff" : C.t1,
                      }}
                    >
                      {val.toFixed(2)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Systemic Risk Alerts */}
      <Card title="Systemic Risk Alerts">
        {SYSTEMIC_RISKS.map((r, i) => {
          const sev = severityStyle(r.severity);
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                padding: 10,
                marginBottom: 8,
                background: sev.bg,
                border: `1px solid ${sev.border}`,
                borderRadius: 8,
              }}
            >
              <span style={{ fontSize: 16 }}>{sev.icon}</span>
              <div>
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: sev.color,
                    marginBottom: 2,
                    textTransform: "uppercase",
                  }}
                >
                  {r.severity} risk
                </div>
                <div style={{ fontSize: 13, color: C.t1, lineHeight: 1.4 }}>
                  {r.desc}
                </div>
              </div>
            </div>
          );
        })}
      </Card>
    </>
  );

  /* ────────────────── TAB 4: Smart Alerts ───────────────────────── */
  const renderAlerts = () => {
    const critCount = ALERTS.filter((a) => a.severity === "critical").length;
    const warnCount = ALERTS.filter((a) => a.severity === "warning").length;
    return (
      <>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
            gap: 10,
            marginBottom: 16,
          }}
        >
          {[
            { label: "Critical", value: `${critCount}`, color: C.red },
            { label: "Warnings", value: `${warnCount}`, color: C.amber },
            { label: "Total Alerts", value: `${ALERTS.length}`, color: C.cyan },
          ].map((m) => (
            <Card key={m.label}>
              <div style={{ fontSize: 11, color: C.t3, marginBottom: 2 }}>
                {m.label}
              </div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  fontFamily: C.mono,
                  color: m.color,
                }}
              >
                {m.value}
              </div>
            </Card>
          ))}
        </div>

        {(["critical", "warning", "info"] as const).map((sev) => {
          const items = ALERTS.filter((a) => a.severity === sev);
          if (items.length === 0) return null;
          const s = severityStyle(sev);
          return (
            <div key={sev} style={{ marginBottom: 16 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: s.color,
                  textTransform: "uppercase",
                  marginBottom: 8,
                }}
              >
                {s.icon}{" "}
                {sev === "info"
                  ? "Informational"
                  : sev.charAt(0).toUpperCase() + sev.slice(1)}{" "}
                ({items.length})
              </div>
              {items.map((a, i) => (
                <Card key={i}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: 6,
                    }}
                  >
                    <span
                      style={{
                        fontFamily: C.mono,
                        fontWeight: 700,
                        fontSize: 14,
                        color: C.t1,
                      }}
                    >
                      {a.title}
                    </span>
                    <span
                      style={{ fontSize: 11, color: C.t3, fontFamily: C.mono }}
                    >
                      {a.ts}
                    </span>
                  </div>
                  <p
                    style={{
                      fontSize: 13,
                      color: C.t2,
                      lineHeight: 1.5,
                      margin: "0 0 8px",
                    }}
                  >
                    {a.detail}
                  </p>
                  <div style={{ display: "flex", gap: 8, fontSize: 11 }}>
                    <Badge variant="neutral">{a.source}</Badge>
                    <Badge
                      variant={
                        a.category === "predictive"
                          ? "info"
                          : a.category === "reactive"
                            ? "warning"
                            : "up"
                      }
                    >
                      {a.category}
                    </Badge>
                  </div>
                </Card>
              ))}
            </div>
          );
        })}
      </>
    );
  };

  /* ──────────── TAB 5: Correlation Dynamics ──────────────────────── */
  const renderCorrDynamics = () => (
    <>
      {/* Rolling correlation line chart */}
      <Card
        title="Rolling Correlation Evolution"
        subtitle="Top 5 pairs — 252-day lookback"
      >
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={ROLLING_CORR}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.2)" />
            <XAxis dataKey="day" tick={{ fontSize: 11, fill: C.t3 }} />
            <YAxis domain={[-1, 1]} tick={{ fontSize: 11, fill: C.t3 }} />
            <Tooltip
              contentStyle={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 6,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {CORR_PAIRS.map((p, i) => (
              <Line
                key={p}
                type="monotone"
                dataKey={p}
                stroke={PAIR_COLORS[i]}
                dot={false}
                strokeWidth={1.5}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {/* Current correlation snapshot */}
        <Card title="Current Correlation Snapshot">
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%" }}>
              <thead>
                <tr>
                  <th style={{ ...thStyle, width: 40 }}></th>
                  {CONTAGION_TICKERS.map((t) => (
                    <th
                      key={t}
                      style={{ ...thStyle, textAlign: "center", fontSize: 10 }}
                    >
                      {t}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {CORR_MATRIX.map((row, i) => (
                  <tr key={i}>
                    <td
                      style={{
                        ...tdStyle,
                        color: C.gold,
                        fontWeight: 700,
                        fontSize: 10,
                      }}
                    >
                      {CONTAGION_TICKERS[i]}
                    </td>
                    {row.map((val, j) => (
                      <td
                        key={j}
                        style={{
                          ...tdStyle,
                          textAlign: "center",
                          fontFamily: C.mono,
                          fontSize: 10,
                          padding: "6px 4px",
                          backgroundColor: corrColor(val),
                          color: Math.abs(val) > 0.6 ? "#fff" : C.t1,
                        }}
                      >
                        {val.toFixed(2)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Instability bar chart */}
        <Card
          title="Correlation Instability"
          subtitle="Std deviation of rolling correlation"
        >
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={INSTABILITY} layout="vertical">
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(51,65,85,0.2)"
              />
              <XAxis
                type="number"
                tick={{ fontSize: 11, fill: C.t3 }}
                domain={[0, 0.15]}
              />
              <YAxis
                type="category"
                dataKey="pair"
                tick={{ fontSize: 11, fill: C.t2, fontFamily: C.mono }}
                width={80}
              />
              <Tooltip
                contentStyle={{
                  background: C.card,
                  border: `1px solid ${C.border}`,
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="instability" radius={[0, 4, 4, 0]}>
                {INSTABILITY.map((_, i) => (
                  <Cell key={i} fill={PAIR_COLORS[i]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </>
  );

  /* ═══════════════════════ MAIN RENDER ═══════════════════════════ */
  return (
    <div style={{ color: C.t1 }}>
      {!liveData && (
        <div
          style={{
            background: "rgba(245,158,11,0.15)",
            border: "1px solid rgba(245,158,11,0.3)",
            borderRadius: 8,
            padding: "8px 16px",
            marginBottom: 16,
            fontSize: 13,
            color: C.amber,
            fontFamily: C.sans,
          }}
        >
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}

      <h1
        style={{
          fontFamily: C.mono,
          fontSize: 24,
          marginBottom: 4,
          color: C.gold,
        }}
      >
        Signal Intelligence
      </h1>
      {/* ÉTAPE 1 — RESEARCH DISCLAIMER: signals, regime and alerts are demo/illustrative */}
      <div
        style={{
          background: "rgba(168,85,247,0.12)",
          border: "1px solid rgba(168,85,247,0.35)",
          borderRadius: 8,
          padding: "8px 16px",
          marginBottom: 12,
          fontSize: 12,
          color: "#C084FC",
          fontFamily: C.mono,
        }}
      >
        ⚗ RESEARCH / EXPERIMENTAL — Buy/Sell signals, regime confidence %, alert
        probabilities and correlation matrices are static demo values, not
        calibrated real-time outputs. Not valid for live trading or risk
        decisions.
      </div>
      <p style={{ color: C.t2, marginBottom: 16, fontSize: 14 }}>
        Advanced signal generation, regime detection, contagion analysis & smart
        alerts
      </p>

      <div style={{ marginBottom: 20 }}>
        <Tabs tabs={TABS_LIST} active={activeTab} onChange={setActiveTab} />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {activeTab === TABS_LIST[0] && renderSignals()}
        {activeTab === TABS_LIST[1] && renderRegime()}
        {activeTab === TABS_LIST[2] && renderContagion()}
        {activeTab === TABS_LIST[3] && renderAlerts()}
        {activeTab === TABS_LIST[4] && renderCorrDynamics()}
      </div>
    </div>
  );
}
