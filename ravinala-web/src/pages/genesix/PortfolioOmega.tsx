import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
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
import { useIndices } from "../../hooks/useMarketData";

// ─── Design Tokens ──────────────────────────────────────────────────────────
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
  text: "#F1F5F9",
  sub: "#94A3B8",
  muted: "#64748B",
} as const;

const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
};

const heading: React.CSSProperties = {
  fontFamily: "JetBrains Mono, monospace",
  color: C.gold,
  margin: 0,
};
const labelCss: React.CSSProperties = {
  fontFamily: "Inter, sans-serif",
  color: C.sub,
  fontSize: 13,
  marginBottom: 4,
};
const inputStyle: React.CSSProperties = {
  background: "rgba(15,18,24,0.8)",
  border: `1px solid ${C.border}`,
  borderRadius: 6,
  padding: "8px 12px",
  color: C.text,
  fontSize: 14,
  fontFamily: "Inter, sans-serif",
  width: "100%",
  outline: "none",
};
const btnPrimary: React.CSSProperties = {
  background: `linear-gradient(135deg, ${C.gold}, #B8941E)`,
  color: "#0A0E1A",
  border: "none",
  borderRadius: 8,
  padding: "12px 24px",
  fontWeight: 700,
  fontSize: 15,
  cursor: "pointer",
  fontFamily: "JetBrains Mono, monospace",
  letterSpacing: "0.04em",
  width: "100%",
};

// ─── Risk Matrix (20 Levels) ────────────────────────────────────────────────
interface RiskLevel {
  level: number;
  name: string;
  category: string;
  categoryColor: string;
  vol: number;
  maxDD: number;
  var95: number;
  targetReturn: number;
  sharpe: number;
  allocation: Record<string, number>;
}

const RISK_MATRIX: RiskLevel[] = [
  {
    level: 1,
    name: "Capital Preservation",
    category: "Capital Preservation",
    categoryColor: "#10B981",
    vol: 2,
    maxDD: 3,
    var95: 0.12,
    targetReturn: 2.5,
    sharpe: 1.2,
    allocation: {
      Cash: 40,
      "Govt Bonds": 40,
      "IG Corporate": 10,
      "US Equities": 5,
      "Intl Equities": 5,
    },
  },
  {
    level: 2,
    name: "Capital Preserve+",
    category: "Capital Preservation",
    categoryColor: "#10B981",
    vol: 3,
    maxDD: 5,
    var95: 0.19,
    targetReturn: 3.0,
    sharpe: 1.0,
    allocation: {
      Cash: 30,
      "Govt Bonds": 40,
      "IG Corporate": 15,
      "US Equities": 10,
      "Intl Equities": 5,
    },
  },
  {
    level: 3,
    name: "Ultra Conservative",
    category: "Capital Preservation",
    categoryColor: "#10B981",
    vol: 4,
    maxDD: 7,
    var95: 0.25,
    targetReturn: 3.5,
    sharpe: 0.88,
    allocation: {
      Cash: 20,
      "Govt Bonds": 35,
      "IG Corporate": 20,
      "US Equities": 15,
      "Intl Equities": 10,
    },
  },
  {
    level: 4,
    name: "Conservative",
    category: "Conservative",
    categoryColor: "#34D399",
    vol: 5,
    maxDD: 8,
    var95: 0.31,
    targetReturn: 4.0,
    sharpe: 0.8,
    allocation: {
      Cash: 10,
      "Govt Bonds": 30,
      "IG Corporate": 20,
      "US Equities": 25,
      "Intl Equities": 10,
      Commodities: 5,
    },
  },
  {
    level: 5,
    name: "Conservative Growth",
    category: "Conservative",
    categoryColor: "#34D399",
    vol: 6,
    maxDD: 10,
    var95: 0.38,
    targetReturn: 5.0,
    sharpe: 0.83,
    allocation: {
      Cash: 5,
      "Govt Bonds": 25,
      "IG Corporate": 20,
      "US Equities": 30,
      "Intl Equities": 12,
      Alternatives: 5,
      Commodities: 3,
    },
  },
  {
    level: 6,
    name: "Moderate Conservative",
    category: "Conservative",
    categoryColor: "#34D399",
    vol: 7,
    maxDD: 12,
    var95: 0.44,
    targetReturn: 5.5,
    sharpe: 0.79,
    allocation: {
      Cash: 3,
      "Govt Bonds": 20,
      "IG Corporate": 22,
      "US Equities": 32,
      "Intl Equities": 13,
      Alternatives: 7,
      Commodities: 3,
    },
  },
  {
    level: 7,
    name: "Balanced",
    category: "Balanced",
    categoryColor: "#00D9FF",
    vol: 9,
    maxDD: 15,
    var95: 0.56,
    targetReturn: 7.0,
    sharpe: 0.78,
    allocation: {
      "Govt Bonds": 15,
      "IG Corporate": 15,
      "US Equities": 35,
      "Intl Equities": 15,
      Alternatives: 8,
      Commodities: 5,
      Cash: 2,
      REITs: 5,
    },
  },
  {
    level: 8,
    name: "Balanced Growth",
    category: "Balanced",
    categoryColor: "#00D9FF",
    vol: 10,
    maxDD: 18,
    var95: 0.63,
    targetReturn: 8.0,
    sharpe: 0.8,
    allocation: {
      "Govt Bonds": 12,
      "IG Corporate": 12,
      "US Equities": 38,
      "Intl Equities": 17,
      Alternatives: 8,
      Commodities: 5,
      REITs: 5,
      Cash: 3,
    },
  },
  {
    level: 9,
    name: "Dynamic Balanced",
    category: "Balanced",
    categoryColor: "#00D9FF",
    vol: 11,
    maxDD: 20,
    var95: 0.69,
    targetReturn: 9.0,
    sharpe: 0.82,
    allocation: {
      "Govt Bonds": 10,
      "IG Corporate": 10,
      "US Equities": 40,
      "Intl Equities": 18,
      "EM Equities": 5,
      Alternatives: 7,
      Commodities: 5,
      REITs: 5,
    },
  },
  {
    level: 10,
    name: "Growth",
    category: "Growth",
    categoryColor: "#D4AF37",
    vol: 13,
    maxDD: 25,
    var95: 0.81,
    targetReturn: 10.0,
    sharpe: 0.77,
    allocation: {
      "US Equities": 40,
      "Intl Equities": 18,
      "EM Equities": 7,
      Alternatives: 10,
      "IG Corporate": 10,
      "Govt Bonds": 5,
      Commodities: 5,
      REITs: 5,
    },
  },
  {
    level: 11,
    name: "Dynamic Growth",
    category: "Growth",
    categoryColor: "#D4AF37",
    vol: 15,
    maxDD: 28,
    var95: 0.94,
    targetReturn: 11.0,
    sharpe: 0.73,
    allocation: {
      "US Equities": 42,
      "Intl Equities": 20,
      "EM Equities": 8,
      Alternatives: 12,
      "IG Corporate": 8,
      Commodities: 5,
      REITs: 5,
    },
  },
  {
    level: 12,
    name: "High Growth",
    category: "Growth",
    categoryColor: "#D4AF37",
    vol: 17,
    maxDD: 32,
    var95: 1.06,
    targetReturn: 12.5,
    sharpe: 0.74,
    allocation: {
      "US Equities": 45,
      "Intl Equities": 22,
      "EM Equities": 8,
      Alternatives: 12,
      "HY Bonds": 5,
      Commodities: 5,
      REITs: 3,
    },
  },
  {
    level: 13,
    name: "Aggressive Growth",
    category: "Aggressive Growth",
    categoryColor: "#F59E0B",
    vol: 19,
    maxDD: 35,
    var95: 1.19,
    targetReturn: 14.0,
    sharpe: 0.74,
    allocation: {
      "US Equities": 45,
      "Intl Equities": 20,
      "EM Equities": 10,
      "Small Cap": 7,
      Alternatives: 8,
      Commodities: 5,
      "HY Bonds": 5,
    },
  },
  {
    level: 14,
    name: "Aggressive",
    category: "Aggressive Growth",
    categoryColor: "#F59E0B",
    vol: 21,
    maxDD: 38,
    var95: 1.31,
    targetReturn: 15.0,
    sharpe: 0.71,
    allocation: {
      "US Equities": 48,
      "Intl Equities": 18,
      "EM Equities": 12,
      "Small Cap": 8,
      Alternatives: 7,
      Commodities: 5,
      "HY Bonds": 2,
    },
  },
  {
    level: 15,
    name: "Very Aggressive",
    category: "Aggressive Growth",
    categoryColor: "#F59E0B",
    vol: 24,
    maxDD: 42,
    var95: 1.5,
    targetReturn: 16.5,
    sharpe: 0.69,
    allocation: {
      "US Equities": 50,
      "Intl Equities": 18,
      "EM Equities": 12,
      "Small Cap": 10,
      Alternatives: 5,
      Commodities: 5,
    },
  },
  {
    level: 16,
    name: "High Risk",
    category: "High Risk",
    categoryColor: "#EF4444",
    vol: 28,
    maxDD: 48,
    var95: 1.75,
    targetReturn: 18.0,
    sharpe: 0.64,
    allocation: {
      "US Equities": 50,
      "Intl Equities": 15,
      "EM Equities": 12,
      "Small Cap": 10,
      Crypto: 3,
      Alternatives: 5,
      Commodities: 5,
    },
  },
  {
    level: 17,
    name: "Very High Risk",
    category: "High Risk",
    categoryColor: "#EF4444",
    vol: 32,
    maxDD: 55,
    var95: 2.0,
    targetReturn: 20.0,
    sharpe: 0.63,
    allocation: {
      "US Equities": 48,
      "Intl Equities": 15,
      "EM Equities": 15,
      "Small Cap": 10,
      Crypto: 5,
      Alternatives: 4,
      Commodities: 3,
    },
  },
  {
    level: 18,
    name: "Speculative",
    category: "Speculative",
    categoryColor: "#DC2626",
    vol: 38,
    maxDD: 65,
    var95: 2.38,
    targetReturn: 25.0,
    sharpe: 0.66,
    allocation: {
      "US Equities": 40,
      "EM Equities": 18,
      "Small Cap": 15,
      "Tech/Growth": 12,
      Crypto: 8,
      Alternatives: 7,
    },
  },
  {
    level: 19,
    name: "Maximum Risk",
    category: "Maximum Risk",
    categoryColor: "#991B1B",
    vol: 45,
    maxDD: 75,
    var95: 2.81,
    targetReturn: 30.0,
    sharpe: 0.67,
    allocation: {
      "US Equities": 35,
      "EM Equities": 18,
      "Small Cap": 15,
      "Tech/Growth": 15,
      Crypto: 10,
      Leveraged: 7,
    },
  },
  {
    level: 20,
    name: "Extreme Risk",
    category: "Maximum Risk",
    categoryColor: "#991B1B",
    vol: 55,
    maxDD: 85,
    var95: 3.44,
    targetReturn: 40.0,
    sharpe: 0.73,
    allocation: {
      "US Equities": 30,
      "EM Equities": 15,
      "Small Cap": 15,
      "Tech/Growth": 15,
      Crypto: 10,
      Leveraged: 10,
      Options: 5,
    },
  },
];

const PIE_COLORS = [
  "#00D9FF",
  "#D4AF37",
  "#10B981",
  "#A855F7",
  "#F59E0B",
  "#EF4444",
  "#3B82F6",
  "#EC4899",
  "#14B8A6",
  "#F97316",
  "#8B5CF6",
  "#06B6D4",
];

const CURRENCIES = ["USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD"] as const;
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$",
  EUR: "\u20AC",
  GBP: "\u00A3",
  CHF: "CHF\u00A0",
  JPY: "\u00A5",
  CAD: "C$",
  AUD: "A$",
};
const HORIZON_UNITS = ["Years", "Months"] as const;

// ─── Portfolio Monitor Data ──────────────────────────────────────────────────
const MONITOR_TABS = [
  "Positions",
  "Performance",
  "Rebalancing",
  "Tax Harvesting",
] as const;
const PM_PERIODS = ['1M', '3M', '6M', 'YTD', '1Y', '3Y', '5Y', 'Inception'] as const;

const POSITIONS = [
  { ticker: "AAPL", name: "Apple Inc.", qty: 150, avgCost: 178.5, current: 198.5, pnl: 3000, pnlPct: 11.2 },
  { ticker: "NVDA", name: "NVIDIA Corp.", qty: 80, avgCost: 680.0, current: 875.2, pnl: 15616, pnlPct: 28.7 },
  { ticker: "MSFT", name: "Microsoft Corp.", qty: 60, avgCost: 395.0, current: 425.2, pnl: 1812, pnlPct: 7.6 },
  { ticker: "GOOGL", name: "Alphabet Inc.", qty: 100, avgCost: 168.0, current: 178.3, pnl: 1030, pnlPct: 6.1 },
  { ticker: "AMZN", name: "Amazon.com", qty: 45, avgCost: 185.0, current: 192.8, pnl: 351, pnlPct: 4.2 },
  { ticker: "JPM", name: "JPMorgan Chase", qty: 70, avgCost: 198.0, current: 205.4, pnl: 518, pnlPct: 3.7 },
  { ticker: "TLT", name: "20+ Yr Treasury", qty: 200, avgCost: 98.5, current: 95.2, pnl: -660, pnlPct: -3.4 },
  { ticker: "GLD", name: "SPDR Gold", qty: 100, avgCost: 210.0, current: 222.5, pnl: 1250, pnlPct: 6.0 },
  { ticker: "TSLA", name: "Tesla Inc.", qty: 30, avgCost: 260.0, current: 242.8, pnl: -516, pnlPct: -6.6 },
  { ticker: "XOM", name: "Exxon Mobil", qty: 90, avgCost: 108.0, current: 112.4, pnl: 396, pnlPct: 4.1 },
];

const totalPnl = POSITIONS.reduce((s, p) => s + p.pnl, 0);
const totalValue = POSITIONS.reduce((s, p) => s + p.qty * p.current, 0);
const totalCost = POSITIONS.reduce((s, p) => s + p.qty * p.avgCost, 0);

const ALLOC_COLORS = [
  "#D4AF37", "#00D9FF", "#10B981", "#EF4444", "#A855F7",
  "#F59E0B", "#EC4899", "#3B82F6", "#84CC16", "#F97316",
];
const allocation = POSITIONS.map((p, i) => ({
  name: p.ticker,
  value: Math.round(p.qty * p.current),
  color: ALLOC_COLORS[i % ALLOC_COLORS.length],
}));

const PERF_DATA = Array.from({ length: 90 }, (_, i) => ({
  day: `D${i + 1}`,
  portfolio: +(100 + i * 0.12 + Math.sin(i * 0.08) * 4).toFixed(2),
  benchmark: +(100 + i * 0.09 + Math.sin(i * 0.06) * 3).toFixed(2),
}));

const REBALANCE = [
  { ticker: "AAPL", target: 12, current: +((POSITIONS[0].qty * POSITIONS[0].current) / totalValue * 100).toFixed(1), action: "" },
  { ticker: "NVDA", target: 20, current: +((POSITIONS[1].qty * POSITIONS[1].current) / totalValue * 100).toFixed(1), action: "" },
  { ticker: "MSFT", target: 10, current: +((POSITIONS[2].qty * POSITIONS[2].current) / totalValue * 100).toFixed(1), action: "" },
  { ticker: "GOOGL", target: 8, current: +((POSITIONS[3].qty * POSITIONS[3].current) / totalValue * 100).toFixed(1), action: "" },
  { ticker: "AMZN", target: 5, current: +((POSITIONS[4].qty * POSITIONS[4].current) / totalValue * 100).toFixed(1), action: "" },
  { ticker: "JPM", target: 8, current: +((POSITIONS[5].qty * POSITIONS[5].current) / totalValue * 100).toFixed(1), action: "" },
  { ticker: "TLT", target: 15, current: +((POSITIONS[6].qty * POSITIONS[6].current) / totalValue * 100).toFixed(1), action: "" },
  { ticker: "GLD", target: 10, current: +((POSITIONS[7].qty * POSITIONS[7].current) / totalValue * 100).toFixed(1), action: "" },
  { ticker: "TSLA", target: 4, current: +((POSITIONS[8].qty * POSITIONS[8].current) / totalValue * 100).toFixed(1), action: "" },
  { ticker: "XOM", target: 8, current: +((POSITIONS[9].qty * POSITIONS[9].current) / totalValue * 100).toFixed(1), action: "" },
].map((r) => ({
  ...r,
  action:
    +r.current - r.target > 0.5
      ? "SELL"
      : +r.current - r.target < -0.5
        ? "BUY"
        : "HOLD",
}));

const TAX_HARVEST = POSITIONS.filter((p) => p.pnl < 0).map((p) => ({
  ticker: p.ticker,
  loss: p.pnl,
  daysHeld: p.ticker === "TLT" ? 245 : 89,
  longTerm: p.ticker === "TLT",
  replacement: p.ticker === "TLT" ? "BND" : p.ticker === "TSLA" ? "RIVN" : "—",
}));

// ─── Helpers ────────────────────────────────────────────────────────────────
function fmtMoney(n: number, sym: string) {
  if (n >= 1_000_000) return `${sym}${(n / 1_000_000).toFixed(2)}M`;
  if (n >= 1_000) return `${sym}${(n / 1_000).toFixed(1)}k`;
  return `${sym}${n.toFixed(0)}`;
}

function fmtPct(n: number) {
  return `${n.toFixed(1)}%`;
}

function horizonLabel(unit: string, val: number): string {
  if (unit === "Years") {
    if (val <= 1) return "Short-term (\u22641Y)";
    if (val <= 3) return "Medium-term (1\u20133Y)";
    if (val <= 7) return "Long-term (3\u20137Y)";
    return "Very Long-term (7Y+)";
  }
  const y = val / 12;
  if (y <= 1) return "Short-term (\u22641Y)";
  if (y <= 3) return "Medium-term (1\u20133Y)";
  return "Long-term (3Y+)";
}

function horizonYears(unit: string, val: number) {
  return unit === "Years" ? val : val / 12;
}

function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return s / 2147483647;
  };
}

function hashStr(str: string): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) - h + str.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

// ─── Risk Gauge SVG ─────────────────────────────────────────────────────────
function RiskGauge({ level }: { level: number }) {
  const cx = 150;
  const cy = 130;
  const r = 100;
  const startAngle = Math.PI;
  const endAngle = 0;

  const bands: { from: number; to: number; color: string }[] = [
    { from: 1, to: 3, color: "#10B981" },
    { from: 4, to: 6, color: "#34D399" },
    { from: 7, to: 9, color: "#00D9FF" },
    { from: 10, to: 12, color: "#D4AF37" },
    { from: 13, to: 15, color: "#F59E0B" },
    { from: 16, to: 17, color: "#EF4444" },
    { from: 18, to: 18, color: "#DC2626" },
    { from: 19, to: 20, color: "#991B1B" },
  ];

  function levelToAngle(l: number) {
    const frac = (l - 1) / 19;
    return startAngle - frac * (startAngle - endAngle);
  }

  function arcPath(sA: number, eA: number, radius: number) {
    const x1 = cx + radius * Math.cos(sA);
    const y1 = cy - radius * Math.sin(sA);
    const x2 = cx + radius * Math.cos(eA);
    const y2 = cy - radius * Math.sin(eA);
    const large = sA - eA > Math.PI ? 1 : 0;
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`;
  }

  const needleAngle = levelToAngle(level);
  const nx = cx + (r - 15) * Math.cos(needleAngle);
  const ny = cy - (r - 15) * Math.sin(needleAngle);

  return (
    <svg viewBox="0 0 300 160" style={{ width: "100%", maxWidth: 320 }}>
      <path
        d={arcPath(startAngle, endAngle, r)}
        fill="none"
        stroke="rgba(51,65,85,0.3)"
        strokeWidth={18}
      />
      {bands.map((b, i) => (
        <path
          key={i}
          d={arcPath(levelToAngle(b.from), levelToAngle(b.to), r)}
          fill="none"
          stroke={b.color}
          strokeWidth={18}
          strokeLinecap="butt"
          opacity={0.7}
        />
      ))}
      <line
        x1={cx}
        y1={cy}
        x2={nx}
        y2={ny}
        stroke={C.gold}
        strokeWidth={3}
        strokeLinecap="round"
      />
      <circle cx={cx} cy={cy} r={6} fill={C.gold} />
      <text
        x={cx}
        y={cy + 30}
        textAnchor="middle"
        fill={C.text}
        fontSize={22}
        fontFamily="JetBrains Mono, monospace"
        fontWeight={700}
      >
        {level}
      </text>
      <text
        x={cx}
        y={cy + 48}
        textAnchor="middle"
        fill={C.sub}
        fontSize={11}
        fontFamily="Inter, sans-serif"
      >
        / 20
      </text>
    </svg>
  );
}

// ─── Growth Projection Data ─────────────────────────────────────────────────
function buildProjection(
  amount: number,
  returnPct: number,
  volPct: number,
  years: number,
) {
  const steps = Math.max(Math.round(years * 4), 4);
  const dt = years / steps;
  const data: {
    period: string;
    expected: number;
    upper: number;
    lower: number;
  }[] = [];
  for (let i = 0; i <= steps; i++) {
    const t = i * dt;
    const lbl = t < 1 ? `${Math.round(t * 12)}mo` : `${t.toFixed(1)}y`;
    const drift = (returnPct / 100 - 0.5 * (volPct / 100) ** 2) * t;
    const exp = amount * Math.exp(drift);
    const sigma = (volPct / 100) * Math.sqrt(t);
    data.push({
      period: lbl,
      expected: Math.round(exp),
      upper: Math.round(exp * Math.exp(sigma)),
      lower: Math.round(exp * Math.exp(-sigma)),
    });
  }
  return data;
}

// ─── Optimizer Logic ────────────────────────────────────────────────────────
interface OptimizerResult {
  tickers: string[];
  weights: number[];
  expReturn: number;
  vol: number;
  sharpe: number;
}

function runOptimizer(tickerStr: string, riskLvl: number): OptimizerResult {
  const tickers = tickerStr
    .split(",")
    .map((t) => t.trim().toUpperCase())
    .filter(Boolean);
  const n = tickers.length;
  if (n === 0)
    return { tickers: [], weights: [], expReturn: 0, vol: 0, sharpe: 0 };

  const seed = hashStr(tickers.join(",")) + riskLvl * 1000;
  const rng = seededRandom(seed);

  const raw = Array.from({ length: n }, () => rng() + 0.05);
  const sum = raw.reduce((a, b) => a + b, 0);
  const weights = raw.map((w) => Math.round((w / sum) * 1000) / 10);
  const diff = 100 - weights.reduce((a, b) => a + b, 0);
  weights[0] = Math.round((weights[0] + diff) * 10) / 10;

  const rm = RISK_MATRIX[riskLvl - 1];
  const base = rm.targetReturn + (rng() - 0.5) * 2;
  const vol = rm.vol * (0.85 + rng() * 0.3);
  const sharpe = base / vol;

  return {
    tickers,
    weights,
    expReturn: Math.round(base * 100) / 100,
    vol: Math.round(vol * 100) / 100,
    sharpe: Math.round(sharpe * 100) / 100,
  };
}

// ═════════════════════════════════════════════════════════════════════════════
// Main Component
// ═════════════════════════════════════════════════════════════════════════════
export default function PortfolioOmega() {
  // ── Outer tabs ──
  const [outerTab, setOuterTab] = useState<"Portfolio Allocation" | "Portfolio Monitor">("Portfolio Allocation");

  // ── Portfolio Allocation state ──
  const [mode, setMode] = useState<"classic" | "advanced">("classic");
  const [amount, setAmount] = useState(100_000);
  const [currency, setCurrency] = useState("USD");
  const [riskLevel, setRiskLevel] = useState(7);
  const [horizonUnit, setHorizonUnit] = useState<"Years" | "Months">("Years");
  const [horizonVal, setHorizonVal] = useState(5);
  const [esg, setEsg] = useState(false);
  const [income, setIncome] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [optTickers, setOptTickers] = useState("SPY, QQQ, TLT, GLD, IWM, EEM");
  const [optRisk, setOptRisk] = useState(10);
  const [optResult, setOptResult] = useState<OptimizerResult | null>(null);
  const [activeTab, setActiveTab] = useState("Portfolio Builder");

  // ── Portfolio Monitor state ──
  const [monitorTab, setMonitorTab] = useState<(typeof MONITOR_TABS)[number]>(MONITOR_TABS[0]);
  const [perfPeriod, setPerfPeriod] = useState<string>('1Y');

  // ── Market data ──
  const { data: indicesData, isLoading: indicesLoading } = useIndices();

  // ── Portfolio Allocation derived ──
  const risk = RISK_MATRIX[riskLevel - 1];
  const sym = CURRENCY_SYMBOLS[currency] ?? "$";
  const yrs = horizonYears(horizonUnit, horizonVal);

  const allocData = useMemo(() => {
    const entries = Object.entries(risk.allocation);
    return entries.map(([name, weight], i) => ({
      name,
      weight,
      value: Math.round((amount * weight) / 100),
      color: PIE_COLORS[i % PIE_COLORS.length],
    }));
  }, [risk, amount]);

  const projectionData = useMemo(
    () => buildProjection(amount, risk.targetReturn, risk.vol, yrs),
    [amount, risk, yrs],
  );

  const indexList = useMemo(() => {
    if (!indicesData) return [];
    const items: { name: string; value: number; change: number }[] = [];
    for (const zone of Object.values(indicesData)) {
      for (const idx of zone) {
        items.push({
          name: idx.name,
          value: idx.price,
          change: idx.change.percent,
        });
      }
    }
    return items.slice(0, 6);
  }, [indicesData]);

  // ── Portfolio Monitor derived ──
  const pmUsingFallback = !indicesData;

  const keyIndices = useMemo(() => {
    if (!indicesData) return [];
    const targets = ["^GSPC", "^IXIC", "^DJI"];
    return Object.values(indicesData)
      .flat()
      .filter((idx) => targets.includes(idx.symbol));
  }, [indicesData]);

  // ─── Render ───────────────────────────────────────────────────────────────
  return (
    <div style={{ fontFamily: "Inter, sans-serif", color: C.text }}>
      <h1 style={{ ...heading, fontSize: 26, marginBottom: 4 }}>
        Portfolio Suite
      </h1>
      <p style={{ color: C.sub, fontSize: 13, margin: "0 0 20px" }}>
        Portfolio allocation engine & live position monitoring
      </p>

      <div style={{ marginBottom: 24 }}>
        <Tabs
          tabs={["Portfolio Allocation", "Portfolio Monitor"]}
          active={outerTab}
          onChange={(t) => setOuterTab(t as typeof outerTab)}
        />
      </div>

      {/* ══════════════════ PORTFOLIO ALLOCATION TAB ══════════════════ */}
      {outerTab === "Portfolio Allocation" && (
        <div>
          {/* Market Ticker */}
          {indicesLoading ? (
            <div style={{ padding: "8px 0", color: C.muted, fontSize: 12 }}>
              Loading market data\u2026
            </div>
          ) : indexList.length > 0 ? (
            <div
              style={{
                display: "flex",
                gap: 16,
                flexWrap: "wrap",
                marginBottom: 16,
                padding: "8px 0",
                borderBottom: `1px solid ${C.border}`,
              }}
            >
              {indexList.map((ix) => (
                <span key={ix.name} style={{ fontSize: 12, color: C.sub }}>
                  {ix.name}{" "}
                  <span
                    style={{
                      color: ix.change >= 0 ? C.green : C.red,
                      fontWeight: 600,
                    }}
                  >
                    {ix.change >= 0 ? "+" : ""}
                    {ix.change.toFixed(2)}%
                  </span>
                </span>
              ))}
            </div>
          ) : (
            <div
              style={{
                padding: "6px 12px",
                marginBottom: 12,
                background: "rgba(245,158,11,0.1)",
                border: "1px solid rgba(245,158,11,0.3)",
                borderRadius: 6,
                fontSize: 12,
                color: C.amber,
              }}
            >
              \u26A0 Market data unavailable \u2014 showing standalone allocator
            </div>
          )}

          <h2 style={{ ...heading, fontSize: 22, marginBottom: 4 }}>
            OMEGA Portfolio Allocator
          </h2>
          <p style={{ color: C.sub, fontSize: 13, margin: "0 0 20px" }}>
            Institutional-grade risk-profiled asset allocation engine
          </p>

          {/* Mode Selector */}
          <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
            {(["classic", "advanced"] as const).map((m) => (
              <label
                key={m}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  cursor: "pointer",
                  padding: "8px 16px",
                  borderRadius: 8,
                  background: mode === m ? "rgba(0,217,255,0.1)" : "transparent",
                  border: `1px solid ${mode === m ? "rgba(0,217,255,0.3)" : C.border}`,
                }}
              >
                <input
                  type="radio"
                  name="mode"
                  checked={mode === m}
                  onChange={() => setMode(m)}
                  style={{ accentColor: C.cyan }}
                />
                <span
                  style={{
                    color: mode === m ? C.cyan : C.sub,
                    fontSize: 13,
                    fontWeight: 600,
                  }}
                >
                  {m === "classic"
                    ? "Classic Risk Matrix Mode"
                    : "Advanced Dynamic Universe Mode"}
                </span>
              </label>
            ))}
          </div>

          {mode === "advanced" ? (
            <Card>
              <div style={{ textAlign: "center", padding: "60px 20px" }}>
                <div style={{ fontSize: 48, marginBottom: 16 }}>
                  {"\uD83D\uDE80"}
                </div>
                <h2 style={{ ...heading, fontSize: 20, marginBottom: 8 }}>
                  Advanced Dynamic Universe Mode
                </h2>
                <p style={{ color: C.sub, fontSize: 14 }}>
                  Coming soon \u2014 AI-driven universe selection with real-time
                  factor tilting
                </p>
                <Badge variant="info">In Development</Badge>
              </div>
            </Card>
          ) : (
            <>
              <Tabs
                tabs={["Portfolio Builder", "Quantitative Optimizer"]}
                active={activeTab}
                onChange={setActiveTab}
              />

              <div style={{ marginTop: 20 }}>
                {activeTab === "Portfolio Builder" ? (
                  <PortfolioBuilderTab
                    amount={amount}
                    setAmount={setAmount}
                    currency={currency}
                    setCurrency={setCurrency}
                    riskLevel={riskLevel}
                    setRiskLevel={(v) => {
                      setRiskLevel(v);
                      setGenerated(false);
                    }}
                    horizonUnit={horizonUnit}
                    setHorizonUnit={setHorizonUnit}
                    horizonVal={horizonVal}
                    setHorizonVal={setHorizonVal}
                    esg={esg}
                    setEsg={setEsg}
                    income={income}
                    setIncome={setIncome}
                    generated={generated}
                    setGenerated={setGenerated}
                    risk={risk}
                    sym={sym}
                    yrs={yrs}
                    allocData={allocData}
                    projectionData={projectionData}
                  />
                ) : (
                  <OptimizerTab
                    optTickers={optTickers}
                    setOptTickers={setOptTickers}
                    optRisk={optRisk}
                    setOptRisk={setOptRisk}
                    optResult={optResult}
                    setOptResult={setOptResult}
                  />
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* ══════════════════ PORTFOLIO MONITOR TAB ══════════════════ */}
      {outerTab === "Portfolio Monitor" && (
        <div style={{ color: "#F1F5F9" }}>
          <h2
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 22,
              marginBottom: 4,
              color: "#D4AF37",
            }}
          >
            Portfolio Monitor
          </h2>
          <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
            Live positions & P&L tracking
          </p>

          {pmUsingFallback && (
            <div
              style={{
                background: "rgba(245,158,11,0.08)",
                border: "1px solid rgba(245,158,11,0.2)",
                borderRadius: 8,
                padding: "8px 14px",
                marginBottom: 16,
                fontSize: 12,
                color: "#F59E0B",
              }}
            >
              Backend unreachable — showing demo data
            </div>
          )}

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
                    backgroundColor: "rgba(212,175,55,0.06)",
                    border: "1px solid rgba(212,175,55,0.15)",
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

          {/* Summary cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
              gap: 10,
              marginBottom: 16,
            }}
          >
            {[
              { label: "Portfolio Value", value: `$${(totalValue / 1000).toFixed(0)}K`, color: "#F1F5F9" },
              { label: "Total P&L", value: `${totalPnl >= 0 ? "+" : ""}$${totalPnl.toLocaleString()}`, color: totalPnl >= 0 ? "#10B981" : "#EF4444" },
              { label: "Total Return", value: `${((totalPnl / totalCost) * 100).toFixed(1)}%`, color: totalPnl >= 0 ? "#10B981" : "#EF4444" },
              { label: "Positions", value: `${POSITIONS.length}`, color: "#D4AF37" },
              { label: "Day P&L", value: "+$2,840", color: "#10B981" },
            ].map((m) => (
              <Card key={m.label}>
                <div style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}>{m.label}</div>
                <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: m.color }}>{m.value}</div>
              </Card>
            ))}
          </div>

          <div style={{ display: "flex", gap: 4, marginBottom: 16, flexWrap: "wrap" }}>
            {MONITOR_TABS.map((t) => (
              <button
                key={t}
                onClick={() => setMonitorTab(t)}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  border: monitorTab === t ? "1px solid rgba(212,175,55,0.5)" : "1px solid rgba(51,65,85,0.3)",
                  backgroundColor: monitorTab === t ? "rgba(212,175,55,0.15)" : "rgba(15,23,42,0.5)",
                  color: monitorTab === t ? "#D4AF37" : "#94A3B8",
                }}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Positions */}
          {monitorTab === "Positions" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Card title="Live Positions">
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                        {["Ticker", "Name", "Qty", "Avg Cost", "Current", "Value", "P&L", "P&L %"].map((h) => (
                          <th
                            key={h}
                            style={{
                              padding: "8px 10px",
                              textAlign: h === "Ticker" || h === "Name" ? "left" : "right",
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
                      {POSITIONS.map((p) => (
                        <tr key={p.ticker} style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}>
                          <td style={{ padding: "8px 10px", fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color: "#D4AF37" }}>{p.ticker}</td>
                          <td style={{ padding: "8px 10px", color: "#F1F5F9" }}>{p.name}</td>
                          <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#94A3B8" }}>{p.qty}</td>
                          <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#94A3B8" }}>${p.avgCost.toFixed(2)}</td>
                          <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#F1F5F9" }}>${p.current.toFixed(2)}</td>
                          <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#F1F5F9" }}>${(p.qty * p.current).toLocaleString()}</td>
                          <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: p.pnl >= 0 ? "#10B981" : "#EF4444" }}>{p.pnl >= 0 ? "+" : ""}${p.pnl.toLocaleString()}</td>
                          <td style={{ padding: "8px 10px", textAlign: "right" }}>
                            <Badge variant={p.pnlPct >= 0 ? "up" : "down"}>
                              {p.pnlPct >= 0 ? "+" : ""}{p.pnlPct}%
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
              <Card title="Allocation">
                <div style={{ width: "100%", height: 280 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={allocation} cx="50%" cy="50%" innerRadius={60} outerRadius={100} dataKey="value" nameKey="name" paddingAngle={2}>
                        {allocation.map((a, i) => <Cell key={i} fill={a.color} />)}
                      </Pie>
                      <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 11 }} />
                      <Tooltip contentStyle={ttStyle} formatter={(v: any) => `$${Number(v).toLocaleString()}`} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          )}

          {/* Performance */}
          {monitorTab === "Performance" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {PM_PERIODS.map((p) => (
                  <button
                    key={p}
                    onClick={() => setPerfPeriod(p)}
                    style={{
                      padding: '6px 14px',
                      borderRadius: 20,
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      border: perfPeriod === p ? '1px solid rgba(212,175,55,0.5)' : '1px solid rgba(51,65,85,0.3)',
                      backgroundColor: perfPeriod === p ? 'rgba(212,175,55,0.15)' : 'rgba(15,23,42,0.5)',
                      color: perfPeriod === p ? '#D4AF37' : '#94A3B8',
                    }}
                  >
                    {p}
                  </button>
                ))}
              </div>
              <Card title={`Portfolio vs Benchmark (${perfPeriod})`} subtitle="Normalized to 100">
                <div style={{ width: "100%", height: 320 }}>
                  <ResponsiveContainer>
                    <LineChart data={PERF_DATA}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                      <XAxis dataKey="day" tick={{ fill: "#64748B", fontSize: 10 }} interval={14} />
                      <YAxis domain={["auto", "auto"]} tick={{ fill: "#64748B", fontSize: 10 }} />
                      <Tooltip contentStyle={ttStyle} />
                      <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                      <Line type="monotone" dataKey="portfolio" stroke="#D4AF37" strokeWidth={2} dot={false} name="Portfolio" />
                      <Line type="monotone" dataKey="benchmark" stroke="#64748B" strokeWidth={1.5} strokeDasharray="4 4" dot={false} name="S&P 500" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10 }}>
                {[
                  { label: "Alpha (ann.)", value: "+3.2%", color: "#10B981" },
                  { label: "Beta", value: "1.05", color: "#94A3B8" },
                  { label: "Sharpe Ratio", value: "1.42", color: "#D4AF37" },
                  { label: "Max Drawdown", value: "-6.8%", color: "#EF4444" },
                  { label: "Ann. Return", value: "+18.4%", color: "#10B981" },
                  { label: "Ann. Volatility", value: "14.2%", color: "#F59E0B" },
                ].map((m) => (
                  <Card key={m.label}>
                    <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: m.color }}>{m.value}</div>
                  </Card>
                ))}
              </div>
              <Card title="Impact & Income Metrics">
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 }}>
                  {[
                    { label: 'Carbon Avoidance', value: '125 metric tons CO₂eq', delta: 'vs benchmark', color: '#10B981' },
                    { label: 'ESG Score', value: '78/100', delta: 'vs benchmark 65/100', color: '#A855F7' },
                    { label: 'Dividend Yield', value: '2.15%', delta: 'vs benchmark 1.84%', color: '#D4AF37' },
                  ].map((m) => (
                    <div key={m.label}>
                      <div style={{ fontSize: 11, color: '#64748B', marginBottom: 2 }}>{m.label}</div>
                      <div style={{ fontSize: 18, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: m.color }}>{m.value}</div>
                      <div style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>{m.delta}</div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {/* Rebalancing */}
          {monitorTab === "Rebalancing" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Card title="Rebalancing Analysis" subtitle="Current allocation vs model targets">
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                        {["Ticker", "Current %", "Target %", "Drift", "Action"].map((h) => (
                          <th key={h} style={{ padding: "8px 10px", textAlign: h === "Ticker" ? "left" : "right", color: "#94A3B8", fontWeight: 500 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {REBALANCE.map((r) => {
                        const drift = +(+r.current - r.target).toFixed(1);
                        return (
                          <tr key={r.ticker} style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}>
                            <td style={{ padding: "8px 10px", fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color: "#D4AF37" }}>{r.ticker}</td>
                            <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#F1F5F9" }}>{r.current}%</td>
                            <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#94A3B8" }}>{r.target}%</td>
                            <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: Math.abs(drift) > 0.5 ? (drift > 0 ? "#F59E0B" : "#00D9FF") : "#64748B" }}>
                              {drift > 0 ? "+" : ""}{drift}%
                            </td>
                            <td style={{ padding: "8px 10px", textAlign: "right" }}>
                              <Badge variant={r.action === "SELL" ? "down" : r.action === "BUY" ? "up" : "neutral"}>{r.action}</Badge>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
              <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                <button style={{ padding: '10px 20px', borderRadius: 8, border: 'none', fontWeight: 700, fontSize: 13, cursor: 'pointer', backgroundColor: '#D4AF37', color: '#0A0E1A' }}>Rebalance Now</button>
                <button style={{ padding: '10px 20px', borderRadius: 8, border: '1px solid #D4AF37', fontWeight: 700, fontSize: 13, cursor: 'pointer', backgroundColor: 'transparent', color: '#D4AF37' }}>Schedule Rebalancing</button>
              </div>
            </div>
          )}

          {/* Tax Harvesting */}
          {monitorTab === "Tax Harvesting" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
                {[
                  { label: "Total Unrealized Losses", value: `$${Math.abs(TAX_HARVEST.reduce((a, b) => a + b.loss, 0)).toLocaleString()}`, color: "#EF4444" },
                  { label: "Harvestable (Short-Term)", value: `$${Math.abs(TAX_HARVEST.filter((t) => !t.longTerm).reduce((a, b) => a + b.loss, 0)).toLocaleString()}`, color: "#F59E0B" },
                  { label: "Harvestable (Long-Term)", value: `$${Math.abs(TAX_HARVEST.filter((t) => t.longTerm).reduce((a, b) => a + b.loss, 0)).toLocaleString()}`, color: "#A855F7" },
                ].map((m) => (
                  <Card key={m.label}>
                    <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: m.color }}>{m.value}</div>
                  </Card>
                ))}
              </div>
              <Card title="Tax-Loss Harvesting Candidates" subtitle="Positions with unrealized losses">
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                        {["Ticker", "Unrealized Loss", "Days Held", "Term", "Replacement", "Wash Sale Risk"].map((h) => (
                          <th key={h} style={{ padding: "8px 10px", textAlign: h === "Ticker" ? "left" : "right", color: "#94A3B8", fontWeight: 500 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {TAX_HARVEST.map((t) => (
                        <tr key={t.ticker} style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}>
                          <td style={{ padding: "8px 10px", fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color: "#D4AF37" }}>{t.ticker}</td>
                          <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#EF4444" }}>-${Math.abs(t.loss).toLocaleString()}</td>
                          <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#94A3B8" }}>{t.daysHeld}d</td>
                          <td style={{ padding: "8px 10px", textAlign: "right" }}>
                            <Badge variant={t.longTerm ? "info" : "warning"}>{t.longTerm ? "Long-Term" : "Short-Term"}</Badge>
                          </td>
                          <td style={{ padding: "8px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#00D9FF" }}>{t.replacement}</td>
                          <td style={{ padding: "8px 10px", textAlign: "right" }}><Badge variant="neutral">None</Badge></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
              <div style={{ padding: "10px 14px", backgroundColor: "rgba(245,158,11,0.08)", borderRadius: 8, fontSize: 12, color: "#94A3B8" }}>
                <strong style={{ color: "#F59E0B" }}>Wash Sale Rule:</strong> Cannot repurchase substantially identical securities within 30 days before or after realizing a loss. Suggested replacements maintain similar market exposure without triggering wash sale.
              </div>
              <button style={{ padding: '10px 20px', borderRadius: 8, border: 'none', fontWeight: 700, fontSize: 13, cursor: 'pointer', backgroundColor: '#10B981', color: '#0A0E1A', alignSelf: 'flex-start' }}>Execute Harvesting Trades</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// Portfolio Builder Tab
// ═════════════════════════════════════════════════════════════════════════════
interface AllocItem {
  name: string;
  weight: number;
  value: number;
  color: string;
}
interface ProjItem {
  period: string;
  expected: number;
  upper: number;
  lower: number;
}

function PortfolioBuilderTab({
  amount,
  setAmount,
  currency,
  setCurrency,
  riskLevel,
  setRiskLevel,
  horizonUnit,
  setHorizonUnit,
  horizonVal,
  setHorizonVal,
  esg,
  setEsg,
  income,
  setIncome,
  generated,
  setGenerated,
  risk,
  sym,
  yrs,
  allocData,
  projectionData,
}: {
  amount: number;
  setAmount: (v: number) => void;
  currency: string;
  setCurrency: (v: string) => void;
  riskLevel: number;
  setRiskLevel: (v: number) => void;
  horizonUnit: "Years" | "Months";
  setHorizonUnit: (v: "Years" | "Months") => void;
  horizonVal: number;
  setHorizonVal: (v: number) => void;
  esg: boolean;
  setEsg: (v: boolean) => void;
  income: boolean;
  setIncome: (v: boolean) => void;
  generated: boolean;
  setGenerated: (v: boolean) => void;
  risk: RiskLevel;
  sym: string;
  yrs: number;
  allocData: AllocItem[];
  projectionData: ProjItem[];
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Investment Profile + Gauge Row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Left: inputs */}
        <Card
          title="Investment Profile"
          subtitle="Configure your allocation parameters"
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 16,
              marginTop: 8,
            }}
          >
            {/* Amount */}
            <div>
              <div style={labelCss}>Investment Amount</div>
              <div style={{ display: "flex", gap: 8 }}>
                <input
                  type="number"
                  min={1000}
                  max={10_000_000}
                  step={10_000}
                  value={amount}
                  onChange={(e) =>
                    setAmount(Math.max(1000, Number(e.target.value)))
                  }
                  style={{ ...inputStyle, flex: 1 }}
                />
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  style={{ ...inputStyle, width: 90 }}
                >
                  {CURRENCIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Risk Level */}
            <div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={labelCss}>Risk Level</span>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    padding: "3px 10px",
                    borderRadius: 12,
                    background: `${risk.categoryColor}22`,
                    color: risk.categoryColor,
                    border: `1px solid ${risk.categoryColor}44`,
                  }}
                >
                  {risk.category}
                </span>
              </div>
              <input
                type="range"
                min={1}
                max={20}
                value={riskLevel}
                onChange={(e) => setRiskLevel(Number(e.target.value))}
                style={{ width: "100%", accentColor: risk.categoryColor }}
              />
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 11,
                  color: C.muted,
                }}
              >
                <span>1 \u2013 Safe</span>
                <span
                  style={{
                    color: risk.categoryColor,
                    fontWeight: 700,
                    fontSize: 13,
                  }}
                >
                  Level {riskLevel}: {risk.name}
                </span>
                <span>20 \u2013 Extreme</span>
              </div>
            </div>

            {/* Time Horizon */}
            <div>
              <div style={labelCss}>Time Horizon</div>
              <div style={{ display: "flex", gap: 8 }}>
                <select
                  value={horizonUnit}
                  onChange={(e) =>
                    setHorizonUnit(e.target.value as "Years" | "Months")
                  }
                  style={{ ...inputStyle, width: 100 }}
                >
                  {HORIZON_UNITS.map((u) => (
                    <option key={u} value={u}>
                      {u}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min={1}
                  max={horizonUnit === "Years" ? 30 : 360}
                  value={horizonVal}
                  onChange={(e) =>
                    setHorizonVal(Math.max(1, Number(e.target.value)))
                  }
                  style={{ ...inputStyle, flex: 1 }}
                />
              </div>
              <div style={{ fontSize: 11, color: C.muted, marginTop: 4 }}>
                {horizonLabel(horizonUnit, horizonVal)}
              </div>
            </div>

            {/* Checkboxes */}
            <div style={{ display: "flex", gap: 20 }}>
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  cursor: "pointer",
                  fontSize: 13,
                  color: C.sub,
                }}
              >
                <input
                  type="checkbox"
                  checked={esg}
                  onChange={(e) => setEsg(e.target.checked)}
                  style={{ accentColor: C.green }}
                />
                ESG Focus
              </label>
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  cursor: "pointer",
                  fontSize: 13,
                  color: C.sub,
                }}
              >
                <input
                  type="checkbox"
                  checked={income}
                  onChange={(e) => setIncome(e.target.checked)}
                  style={{ accentColor: C.amber }}
                />
                Income Focus
              </label>
            </div>

            {/* Generate Button */}
            <button
              type="button"
              style={btnPrimary}
              onClick={() => setGenerated(true)}
            >
              {"\u26A1"} Generate Optimal Portfolio
            </button>
          </div>
        </Card>

        {/* Right: Risk Gauge + Key Metrics */}
        <Card
          title="Risk / Return Profile"
          subtitle={`Level ${riskLevel} \u2014 ${risk.name}`}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 12,
              marginTop: 8,
            }}
          >
            <RiskGauge level={riskLevel} />
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
                width: "100%",
              }}
            >
              {[
                {
                  label: "Target Return",
                  value: fmtPct(risk.targetReturn),
                  color: C.green,
                },
                {
                  label: "Sharpe Target",
                  value: risk.sharpe.toFixed(2),
                  color: C.cyan,
                },
                {
                  label: "Vol Budget",
                  value: fmtPct(risk.vol),
                  color: C.amber,
                },
                {
                  label: "Time Horizon",
                  value: `${horizonVal} ${horizonUnit}`,
                  color: C.purple,
                },
              ].map((m) => (
                <div
                  key={m.label}
                  style={{
                    padding: "10px 12px",
                    borderRadius: 8,
                    background: "rgba(15,18,24,0.6)",
                    border: `1px solid ${C.border}`,
                  }}
                >
                  <div style={{ fontSize: 11, color: C.muted }}>{m.label}</div>
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
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Results (shown after Generate) */}
      {generated && (
        <PortfolioResults
          risk={risk}
          riskLevel={riskLevel}
          sym={sym}
          amount={amount}
          yrs={yrs}
          horizonVal={horizonVal}
          horizonUnit={horizonUnit}
          allocData={allocData}
          projectionData={projectionData}
          esg={esg}
          income={income}
        />
      )}
    </div>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// Portfolio Results (after Generate)
// ═════════════════════════════════════════════════════════════════════════════
function PortfolioResults({
  risk,
  riskLevel,
  sym,
  amount,
  yrs,
  horizonVal,
  horizonUnit,
  allocData,
  projectionData,
  esg,
  income,
}: {
  risk: RiskLevel;
  riskLevel: number;
  sym: string;
  amount: number;
  yrs: number;
  horizonVal: number;
  horizonUnit: string;
  allocData: AllocItem[];
  projectionData: ProjItem[];
  esg: boolean;
  income: boolean;
}) {
  const finalExp = projectionData[projectionData.length - 1].expected;
  const gain = finalExp - amount;
  const annRet =
    (Math.pow(finalExp / amount, 1 / Math.max(yrs, 0.25)) - 1) * 100;
  const maxLoss = (amount * risk.maxDD) / 100;

  const metrics = [
    {
      label: "Projected Final Value",
      value: fmtMoney(finalExp, sym),
      color: C.green,
    },
    {
      label: "Total Gain",
      value: `${gain >= 0 ? "+" : ""}${fmtMoney(gain, sym)}`,
      color: gain >= 0 ? C.green : C.red,
    },
    { label: "Annual Return", value: fmtPct(annRet), color: C.cyan },
    {
      label: "Max Expected Loss (2\u03C3)",
      value: `-${fmtMoney(maxLoss, sym)}`,
      color: C.red,
    },
  ];

  return (
    <>
      {/* Allocation Row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Pie */}
        <Card
          title="Asset Allocation"
          subtitle={`Risk Level ${riskLevel} \u2014 ${risk.name}`}
        >
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={allocData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={110}
                  dataKey="weight"
                  nameKey="name"
                  paddingAngle={2}
                >
                  {allocData.map((d, i) => (
                    <Cell key={i} fill={d.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={ttStyle}
                  formatter={(val, name) => [
                    `${Number(val)}% (${fmtMoney((amount * Number(val)) / 100, sym)})`,
                    String(name),
                  ]}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: C.sub }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Breakdown Table */}
        <Card
          title="Investment Breakdown"
          subtitle={`Total: ${fmtMoney(amount, sym)}`}
        >
          <div style={{ overflowX: "auto", marginTop: 8 }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 13,
              }}
            >
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {["Asset Class", "Weight", "Amount"].map((h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: "left",
                        padding: "8px 6px",
                        color: C.muted,
                        fontWeight: 600,
                        fontSize: 11,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {allocData.map((d) => (
                  <tr
                    key={d.name}
                    style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                  >
                    <td style={{ padding: "8px 6px" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        <span
                          style={{
                            width: 10,
                            height: 10,
                            borderRadius: "50%",
                            background: d.color,
                            display: "inline-block",
                          }}
                        />
                        {d.name}
                      </span>
                    </td>
                    <td
                      style={{
                        padding: "8px 6px",
                        color: C.cyan,
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                    >
                      {d.weight}%
                    </td>
                    <td
                      style={{
                        padding: "8px 6px",
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                    >
                      {fmtMoney(d.value, sym)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Projected Metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 16,
        }}
      >
        {metrics.map((m) => (
          <Card key={m.label}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 11, color: C.muted, marginBottom: 6 }}>
                {m.label}
              </div>
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  fontFamily: "JetBrains Mono, monospace",
                  color: m.color,
                }}
              >
                {m.value}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Growth Projection Chart */}
      <Card
        title="Growth Projection"
        subtitle={`${horizonVal} ${horizonUnit} \u2014 with \u00B11\u03C3 confidence band`}
      >
        <div style={{ width: "100%", height: 350 }}>
          <ResponsiveContainer>
            <AreaChart data={projectionData}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(51,65,85,0.3)"
              />
              <XAxis dataKey="period" tick={{ fill: C.muted, fontSize: 11 }} />
              <YAxis
                tick={{ fill: C.muted, fontSize: 11 }}
                tickFormatter={(v: number) => fmtMoney(v, sym)}
                width={80}
              />
              <Tooltip
                contentStyle={ttStyle}
                formatter={(v) => fmtMoney(Number(v), sym)}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area
                type="monotone"
                dataKey="upper"
                name="Upper +1\u03C3"
                stroke="transparent"
                fill={C.green}
                fillOpacity={0.08}
              />
              <Area
                type="monotone"
                dataKey="lower"
                name="Lower \u22121\u03C3"
                stroke="transparent"
                fill={C.red}
                fillOpacity={0.08}
              />
              <Line
                type="monotone"
                dataKey="upper"
                name="Upper +1\u03C3"
                stroke={C.green}
                strokeDasharray="4 4"
                strokeWidth={1.5}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="expected"
                name="Expected"
                stroke={C.gold}
                strokeWidth={2.5}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="lower"
                name="Lower \u22121\u03C3"
                stroke={C.red}
                strokeDasharray="4 4"
                strokeWidth={1.5}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Why + Warnings + Actions */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <Card title="Why This Allocation?" subtitle="Risk-level rationale">
          <div
            style={{
              fontSize: 13,
              color: C.sub,
              lineHeight: 1.7,
              marginTop: 8,
            }}
          >
            <p style={{ margin: "0 0 10px" }}>
              At{" "}
              <strong style={{ color: C.cyan }}>
                Risk Level {riskLevel} ({risk.name})
              </strong>
              , your portfolio targets a{" "}
              <strong style={{ color: C.green }}>
                {fmtPct(risk.targetReturn)}
              </strong>{" "}
              annual return with a volatility budget of{" "}
              <strong style={{ color: C.amber }}>{fmtPct(risk.vol)}</strong>.
            </p>
            <p style={{ margin: "0 0 10px" }}>
              The maximum historical drawdown allowed is{" "}
              <strong style={{ color: C.red }}>{fmtPct(risk.maxDD)}</strong>,
              with a daily 95% VaR of {fmtPct(risk.var95)}. Sharpe target:{" "}
              {risk.sharpe.toFixed(2)}.
            </p>
            <p style={{ margin: 0 }}>
              {riskLevel <= 6
                ? "The allocation favors fixed income and cash equivalents, providing capital stability with modest growth."
                : riskLevel <= 12
                  ? "A balanced mix of equities and bonds aims for growth while managing downside through diversification."
                  : "Equity-heavy allocation seeks maximum growth, accepting higher volatility and drawdown risk."}
              {esg
                ? " ESG screening applied to all equity and bond selections."
                : ""}
              {income
                ? " Income-generating assets (dividend stocks, bonds) are overweighted."
                : ""}
            </p>
          </div>
        </Card>

        <Card title="Risk Warnings & Actions">
          <div style={{ marginTop: 8 }}>
            <div style={{ marginBottom: 16 }}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: C.amber,
                  marginBottom: 8,
                }}
              >
                {"\u26A0"} Risk Warnings
              </div>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: 18,
                  fontSize: 12,
                  color: C.sub,
                  lineHeight: 1.8,
                }}
              >
                <li>
                  Max drawdown of {fmtPct(risk.maxDD)} possible in adverse
                  conditions
                </li>
                <li>
                  Daily VaR (95%): you could lose {fmtPct(risk.var95)} on any
                  given day
                </li>
                {riskLevel >= 16 && (
                  <li style={{ color: C.red }}>
                    Leverage and crypto exposure present \u2014 monitor closely
                  </li>
                )}
                {riskLevel >= 18 && (
                  <li style={{ color: C.red }}>
                    Speculative assets included \u2014 only invest money you can
                    afford to lose
                  </li>
                )}
              </ul>
            </div>
            <div style={{ marginBottom: 16 }}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  color: C.green,
                  marginBottom: 8,
                }}
              >
                {"\u2713"} Mitigations
              </div>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: 18,
                  fontSize: 12,
                  color: C.sub,
                  lineHeight: 1.8,
                }}
              >
                <li>
                  Diversified across {Object.keys(risk.allocation).length} asset
                  classes
                </li>
                <li>
                  Volatility budget capped at {fmtPct(risk.vol)} annualised
                </li>
                <li>Rebalancing triggers at \u00B15% drift</li>
              </ul>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {[
                "\uD83D\uDCE4 Export PDF",
                "\uD83D\uDCCA Detailed Analysis",
                "\uD83D\uDCAC Discuss with Advisor",
              ].map((a) => (
                <button
                  key={a}
                  type="button"
                  style={{
                    background: "rgba(0,217,255,0.08)",
                    border: "1px solid rgba(0,217,255,0.2)",
                    borderRadius: 6,
                    padding: "6px 14px",
                    color: C.cyan,
                    fontSize: 12,
                    cursor: "pointer",
                    fontWeight: 600,
                  }}
                >
                  {a}
                </button>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </>
  );
}

// ═════════════════════════════════════════════════════════════════════════════
// Quantitative Optimizer Tab
// ═════════════════════════════════════════════════════════════════════════════
function OptimizerTab({
  optTickers,
  setOptTickers,
  optRisk,
  setOptRisk,
  optResult,
  setOptResult,
}: {
  optTickers: string;
  setOptTickers: (v: string) => void;
  optRisk: number;
  setOptRisk: (v: number) => void;
  optResult: OptimizerResult | null;
  setOptResult: (v: OptimizerResult) => void;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <Card
        title="Quantitative Portfolio Optimizer"
        subtitle="Mean-variance optimisation on custom tickers"
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 16,
            marginTop: 8,
          }}
        >
          <div>
            <div style={labelCss}>Tickers (comma-separated)</div>
            <input
              type="text"
              value={optTickers}
              onChange={(e) => setOptTickers(e.target.value)}
              style={inputStyle}
              placeholder="SPY, QQQ, TLT, GLD, IWM, EEM"
            />
          </div>
          <div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={labelCss}>Risk Level</span>
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 700,
                  color: C.cyan,
                  fontFamily: "JetBrains Mono, monospace",
                }}
              >
                {optRisk}
              </span>
            </div>
            <input
              type="range"
              min={1}
              max={20}
              value={optRisk}
              onChange={(e) => setOptRisk(Number(e.target.value))}
              style={{ width: "100%", accentColor: C.cyan }}
            />
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 11,
                color: C.muted,
              }}
            >
              <span>Conservative</span>
              <span>Aggressive</span>
            </div>
          </div>
          <button
            type="button"
            style={btnPrimary}
            onClick={() => setOptResult(runOptimizer(optTickers, optRisk))}
          >
            {"\uD83D\uDD2C"} Run Optimization
          </button>
        </div>
      </Card>

      {optResult && optResult.tickers.length > 0 && (
        <>
          {/* Metrics */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 16,
            }}
          >
            {[
              {
                label: "Expected Return",
                value: fmtPct(optResult.expReturn),
                color: C.green,
              },
              {
                label: "Portfolio Vol",
                value: fmtPct(optResult.vol),
                color: C.amber,
              },
              {
                label: "Sharpe Ratio",
                value: optResult.sharpe.toFixed(2),
                color: C.cyan,
              },
            ].map((m) => (
              <Card key={m.label}>
                <div style={{ textAlign: "center" }}>
                  <div
                    style={{ fontSize: 11, color: C.muted, marginBottom: 6 }}
                  >
                    {m.label}
                  </div>
                  <div
                    style={{
                      fontSize: 24,
                      fontWeight: 700,
                      fontFamily: "JetBrains Mono, monospace",
                      color: m.color,
                    }}
                  >
                    {m.value}
                  </div>
                </div>
              </Card>
            ))}
          </div>

          {/* Weights + Pie */}
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}
          >
            <Card title="Optimal Weights">
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 13,
                  marginTop: 8,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    <th
                      style={{
                        textAlign: "left",
                        padding: "8px 6px",
                        color: C.muted,
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      Ticker
                    </th>
                    <th
                      style={{
                        textAlign: "right",
                        padding: "8px 6px",
                        color: C.muted,
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      Weight
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {optResult.tickers.map((t, i) => (
                    <tr
                      key={t}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                    >
                      <td style={{ padding: "8px 6px" }}>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 8,
                          }}
                        >
                          <span
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: "50%",
                              background: PIE_COLORS[i % PIE_COLORS.length],
                              display: "inline-block",
                            }}
                          />
                          <span style={{ fontWeight: 600 }}>{t}</span>
                        </span>
                      </td>
                      <td
                        style={{
                          padding: "8px 6px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: C.cyan,
                        }}
                      >
                        {optResult.weights[i]}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            <Card title="Allocation">
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={optResult.tickers.map((t, i) => ({
                        name: t,
                        value: optResult.weights[i],
                      }))}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={100}
                      dataKey="value"
                      nameKey="name"
                      paddingAngle={2}
                    >
                      {optResult.tickers.map((_, i) => (
                        <Cell
                          key={i}
                          fill={PIE_COLORS[i % PIE_COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={ttStyle}
                      formatter={(val, name) => [
                        `${Number(val)}%`,
                        String(name),
                      ]}
                    />
                    <Legend wrapperStyle={{ fontSize: 11, color: C.sub }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
