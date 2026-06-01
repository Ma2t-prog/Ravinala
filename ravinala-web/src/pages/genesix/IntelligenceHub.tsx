import { useMemo, useState } from "react";
import {
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
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Card, Tabs } from "../../components/ui";
import { useIndices, useMacro, useSnapshot } from "../../hooks/useMarketData";

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

const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
};

/* ═══════════════════════════════════════════════════════════════════
   MARKET INTELLIGENCE DATA
   ═══════════════════════════════════════════════════════════════════ */

const MI_TABS = [
  "Market Data",
  "Overview",
  "Signals",
  "Health Score",
  "Alerts",
  "News",
] as const;

const MI_SIGNALS = [
  {
    id: 1,
    time: "09:31",
    ticker: "NVDA",
    signal: "Momentum Breakout",
    strength: 92,
    direction: "Long" as const,
  },
  {
    id: 2,
    time: "09:45",
    ticker: "AAPL",
    signal: "RSI Divergence",
    strength: 78,
    direction: "Long" as const,
  },
  {
    id: 3,
    time: "10:02",
    ticker: "TSLA",
    signal: "Volume Spike",
    strength: 85,
    direction: "Short" as const,
  },
  {
    id: 4,
    time: "10:15",
    ticker: "SPY",
    signal: "VWAP Cross",
    strength: 65,
    direction: "Long" as const,
  },
  {
    id: 5,
    time: "10:30",
    ticker: "AMD",
    signal: "Bollinger Squeeze",
    strength: 71,
    direction: "Long" as const,
  },
  {
    id: 6,
    time: "10:48",
    ticker: "META",
    signal: "Golden Cross (50/200)",
    strength: 88,
    direction: "Long" as const,
  },
  {
    id: 7,
    time: "11:05",
    ticker: "AMZN",
    signal: "Earnings Momentum",
    strength: 76,
    direction: "Long" as const,
  },
  {
    id: 8,
    time: "11:22",
    ticker: "XOM",
    signal: "Sector Rotation",
    strength: 62,
    direction: "Short" as const,
  },
  {
    id: 9,
    time: "11:40",
    ticker: "JPM",
    signal: "Support Bounce",
    strength: 69,
    direction: "Long" as const,
  },
  {
    id: 10,
    time: "12:01",
    ticker: "GOOGL",
    signal: "Mean Reversion",
    strength: 73,
    direction: "Long" as const,
  },
];

const MARKET_SUMMARY = [
  { label: "S&P 500", value: "5,248.32", change: "+0.82%", up: true },
  { label: "NASDAQ", value: "16,742.18", change: "+1.24%", up: true },
  { label: "VIX", value: "14.2", change: "-5.3%", up: false },
  { label: "DXY", value: "103.42", change: "-0.18%", up: false },
  { label: "10Y Yield", value: "4.28%", change: "+2bp", up: true },
  { label: "BTC", value: "$68,420", change: "+2.8%", up: true },
];

const HEALTH_COMPONENTS = [
  {
    label: "Breadth",
    score: 72,
    desc: "% S&P stocks above 200d MA",
    color: "#10B981",
  },
  {
    label: "Momentum",
    score: 81,
    desc: "RSI composite (14d)",
    color: "#00D9FF",
  },
  {
    label: "Volatility",
    score: 65,
    desc: "VIX regime relative",
    color: "#F59E0B",
  },
  {
    label: "Sentiment",
    score: 58,
    desc: "Put/Call + AAII survey",
    color: "#A855F7",
  },
  {
    label: "Liquidity",
    score: 78,
    desc: "Bid-ask spreads, volume",
    color: "#D4AF37",
  },
  {
    label: "Credit",
    score: 85,
    desc: "HY spread compression",
    color: "#10B981",
  },
];

const HEALTH_HISTORY = Array.from({ length: 30 }, (_, i) => ({
  day: `D${i + 1}`,
  score: Math.round(60 + Math.sin(i * 0.2) * 12 + Math.cos(i * 0.15) * 8),
}));

const SECTORS = [
  { name: "Technology", perf: 2.4, weight: 31.5 },
  { name: "Healthcare", perf: 0.8, weight: 12.1 },
  { name: "Financials", perf: 1.2, weight: 13.4 },
  { name: "Consumer Disc.", perf: -0.3, weight: 10.8 },
  { name: "Industrials", perf: 0.6, weight: 8.9 },
  { name: "Energy", perf: -1.1, weight: 4.2 },
  { name: "Real Estate", perf: -0.5, weight: 2.4 },
  { name: "Utilities", perf: 0.2, weight: 2.6 },
  { name: "Materials", perf: 0.4, weight: 2.5 },
  { name: "Communication", perf: 1.8, weight: 8.8 },
  { name: "Staples", perf: 0.1, weight: 5.8 },
];

const ASSETS = [
  "SPY",
  "QQQ",
  "AAPL",
  "MSFT",
  "GOOGL",
  "NVDA",
  "BTC-USD",
  "GLD",
] as const;
const PERIODS = [30, 60, 90] as const;
const ASSET_DATA: Record<
  string,
  { base: number; vol: number; trend: number; baseVol: number }
> = {
  SPY: { base: 524, vol: 0.012, trend: 0.0003, baseVol: 78_000_000 },
  QQQ: { base: 460, vol: 0.015, trend: 0.0004, baseVol: 52_000_000 },
  AAPL: { base: 196, vol: 0.018, trend: 0.0002, baseVol: 65_000_000 },
  MSFT: { base: 430, vol: 0.016, trend: 0.0003, baseVol: 24_000_000 },
  GOOGL: { base: 177, vol: 0.02, trend: 0.0002, baseVol: 22_000_000 },
  NVDA: { base: 862, vol: 0.028, trend: 0.0008, baseVol: 48_000_000 },
  "BTC-USD": { base: 68400, vol: 0.035, trend: 0.001, baseVol: 32_000_000_000 },
  GLD: { base: 214, vol: 0.008, trend: 0.0001, baseVol: 9_000_000 },
};

function miSeededRandom(seed: number) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return () => {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}
function randn(rng: () => number) {
  const u1 = rng(),
    u2 = rng();
  return Math.sqrt(-2 * Math.log(u1 || 0.001)) * Math.cos(2 * Math.PI * u2);
}
function sma(arr: number[], window: number) {
  return arr.map((_, i) => {
    if (i < window - 1) return null;
    let sum = 0;
    for (let j = i - window + 1; j <= i; j++) sum += arr[j];
    return sum / window;
  });
}

function generateOHLCV(asset: string, days: number) {
  const cfg = ASSET_DATA[asset];
  if (!cfg) return [];
  const rng = miSeededRandom(
    asset.split("").reduce((a, c) => a + c.charCodeAt(0), 0) * 1000 + days,
  );
  const data: {
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }[] = [];
  let prevClose = cfg.base;
  for (let i = 0; i < days; i++) {
    const r1 = randn(rng),
      r2 = randn(rng),
      r3 = randn(rng),
      r4 = randn(rng);
    const open = prevClose * (1 + cfg.trend + cfg.vol * r1);
    const high = open * (1 + Math.abs(r2) * cfg.vol * 0.5);
    const low = open * (1 - Math.abs(r3) * cfg.vol * 0.5);
    const close = open * (1 + cfg.trend + cfg.vol * r4 * 0.8);
    const volume = Math.round(cfg.baseVol * (1 + Math.abs(randn(rng)) * 0.3));
    const d = new Date();
    d.setDate(d.getDate() - (days - i));
    data.push({
      date: `${d.getMonth() + 1}/${d.getDate()}`,
      open: +open.toFixed(2),
      high: +Math.max(high, open, close).toFixed(2),
      low: +Math.min(low, open, close).toFixed(2),
      close: +close.toFixed(2),
      volume,
    });
    prevClose = close;
  }
  return data;
}

const NEWS = [
  {
    time: "2h ago",
    title: "Fed signals patience on rate cuts amid sticky inflation",
    source: "Reuters",
    sentiment: "negative" as const,
  },
  {
    time: "3h ago",
    title: "NVIDIA beats Q4 expectations, data center revenue surges 409%",
    source: "Bloomberg",
    sentiment: "positive" as const,
  },
  {
    time: "5h ago",
    title: "China manufacturing PMI expands for first time in 6 months",
    source: "Caixin",
    sentiment: "positive" as const,
  },
  {
    time: "8h ago",
    title: "European banks face new capital requirements under Basel III",
    source: "FT",
    sentiment: "negative" as const,
  },
  {
    time: "1d ago",
    title: "Oil prices steady amid OPEC+ production decision uncertainty",
    source: "CNBC",
    sentiment: "neutral" as const,
  },
  {
    time: "1d ago",
    title: "Bitcoin ETF inflows hit record $1.1B in single day",
    source: "CoinDesk",
    sentiment: "positive" as const,
  },
];

const SECTOR_SENTIMENT = [
  { sector: "Technology", score: 78, momentum: 2.4 },
  { sector: "Healthcare", score: 55, momentum: 0.8 },
  { sector: "Financials", score: 62, momentum: 1.2 },
  { sector: "Energy", score: 38, momentum: -1.1 },
  { sector: "Industrials", score: 58, momentum: 0.6 },
  { sector: "Communication", score: 70, momentum: 1.8 },
  { sector: "Consumer Disc.", score: 45, momentum: -0.3 },
  { sector: "Real Estate", score: 42, momentum: -0.5 },
];

const MI_ALERTS = [
  {
    id: 1,
    severity: "high" as const,
    time: "08:30",
    title: "CPI Print Above Consensus",
    detail: "Core CPI +0.4% m/m vs +0.3% expected — hawkish for Fed path",
    source: "BLS",
  },
  {
    id: 2,
    severity: "medium" as const,
    time: "09:15",
    title: "NVDA Options Flow Surge",
    detail:
      "$82M call premium swept in first 15 min — institutional positioning",
    source: "CBOE",
  },
  {
    id: 3,
    severity: "low" as const,
    time: "10:00",
    title: "VIX Term Structure Inversion",
    detail: "Front-month VIX > 2nd month — short-term hedging demand elevated",
    source: "CBOE",
  },
  {
    id: 4,
    severity: "high" as const,
    time: "10:45",
    title: "China PMI Contraction",
    detail: "Caixin Manufacturing PMI 49.2 — sub-50 for 2nd consecutive month",
    source: "Caixin",
  },
  {
    id: 5,
    severity: "medium" as const,
    time: "11:30",
    title: "Treasury Auction Tails",
    detail: "10Y auction tailed 2.5bp — weak demand from dealers",
    source: "Treasury",
  },
  {
    id: 6,
    severity: "low" as const,
    time: "12:15",
    title: "Sector Rotation: Energy → Tech",
    detail: "Net $1.2B flow from XLE to XLK ETFs in 3 hours",
    source: "Flow",
  },
];

/* ═══════════════════════════════════════════════════════════════════
   SIGNAL INTELLIGENCE DATA
   ═══════════════════════════════════════════════════════════════════ */

const SI_SIGNALS = [
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

const SI_REGIMES = ["Low Vol", "Normal", "High Vol", "Crisis"] as const;
const REGIME_COLORS = [C.green, C.cyan, C.amber, C.red];
const CURRENT_REGIME = {
  regime: "Low Vol" as const,
  confidence: 87,
  days: 45,
  transitionProb: 12,
};

const SI_TRANSITION_MATRIX = [
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
  return { day: i + 1, regime, label: SI_REGIMES[regime] };
});

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

const SI_ALERTS = [
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

const SI_TABS_LIST = [
  "Signals",
  "Regime Detection",
  "Contagion",
  "Smart Alerts",
  "Correlation Dynamics",
];

/* ───────────────────────── helpers ─────────────────────────────── */
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

/* ═══════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════════ */
export default function IntelligenceHub() {
  /* ── outer tabs ── */
  const [activeTab, setActiveTab] = useState<
    "Market Intelligence" | "Signal Intelligence"
  >("Market Intelligence");

  /* ── Market Intelligence state ── */
  const [miTab, setMiTab] = useState<(typeof MI_TABS)[number]>(MI_TABS[0]);
  const [selectedAsset, setSelectedAsset] = useState<string>("SPY");
  const [selectedPeriod, setSelectedPeriod] = useState<number>(60);

  /* ── Signal Intelligence state ── */
  const [siActiveTab, setSiActiveTab] = useState(SI_TABS_LIST[0]);

  /* ── shared data hooks ── */
  const { data: indicesData } = useIndices();
  const { data: _macroData } = useMacro();
  const { data: snapshotData } = useSnapshot();

  const miUsingFallback = !indicesData;
  const siLiveData = indicesData ?? snapshotData ?? null;

  /* ── Market Intelligence memos ── */
  const ohlcv = useMemo(
    () => generateOHLCV(selectedAsset, selectedPeriod),
    [selectedAsset, selectedPeriod],
  );
  const closes = ohlcv.map((d) => d.close);
  const ma20 = sma(closes, 20);
  const ma50 = sma(closes, 50);
  const ma200 = selectedPeriod >= 200 ? sma(closes, 200) : null;
  const chartData = ohlcv.map((d, i) => {
    const bullish = d.close >= d.open;
    const dailyReturn =
      i > 0 ? ((d.close - ohlcv[i - 1].close) / ohlcv[i - 1].close) * 100 : 0;
    return {
      ...d,
      bodyBottom: Math.min(d.open, d.close),
      bodyHeight: Math.abs(d.close - d.open),
      wickRange: [d.low, d.high] as [number, number],
      bullish,
      dailyReturn: +dailyReturn.toFixed(2),
      ma20: ma20[i],
      ma50: ma50[i],
      ma200: ma200 ? ma200[i] : null,
    };
  });
  const lastD = ohlcv[ohlcv.length - 1];
  const firstD = ohlcv[0];
  const ytdReturn =
    firstD && lastD
      ? (((lastD.close - firstD.open) / firstD.open) * 100).toFixed(2)
      : "0";
  const realizedVol =
    closes.length >= 30
      ? (() => {
          const rets = closes
            .slice(-30)
            .map((c, i, a) => (i > 0 ? Math.log(c / a[i - 1]) : 0))
            .slice(1);
          const mean = rets.reduce((a, b) => a + b, 0) / rets.length;
          const variance =
            rets.reduce((a, b) => a + (b - mean) ** 2, 0) / rets.length;
          return (Math.sqrt(variance * 252) * 100).toFixed(1);
        })()
      : "—";

  const overallHealth = Math.round(
    HEALTH_COMPONENTS.reduce((a, b) => a + b.score, 0) /
      HEALTH_COMPONENTS.length,
  );

  /* ── Signal Intelligence memos ── */
  const displaySignals = useMemo(() => {
    if (!indicesData && !snapshotData) return SI_SIGNALS;
    const allIndices = indicesData
      ? Object.values(indicesData).flat()
      : snapshotData?.indices
        ? Object.values(snapshotData.indices).flat()
        : [];
    if (allIndices.length === 0) return SI_SIGNALS;
    const priceLookup = new Map(
      (allIndices as any[]).map((idx: any) => [idx.symbol, idx.price]),
    );
    return SI_SIGNALS.map((sig) => {
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

  /* ────────────────── Signal Intelligence render functions ────────────────── */
  const renderSiSignals = () => (
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

  const renderSiRegime = () => (
    <>
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
              tickFormatter={(v: number) => SI_REGIMES[v] ?? ""}
              width={60}
            />
            <Tooltip
              contentStyle={{
                background: C.card,
                border: `1px solid ${C.border}`,
                borderRadius: 6,
                fontSize: 12,
              }}
              formatter={((v: number) => [SI_REGIMES[v], "Regime"]) as any}
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
        <Card title="Transition Probability Matrix">
          <table style={{ borderCollapse: "collapse", width: "100%" }}>
            <thead>
              <tr>
                <th style={{ ...thStyle, width: 70 }}>From \ To</th>
                {SI_REGIMES.map((r) => (
                  <th key={r} style={thStyle}>
                    {r}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {SI_TRANSITION_MATRIX.map((row, i) => (
                <tr key={i}>
                  <td
                    style={{
                      ...tdStyle,
                      color: REGIME_COLORS[i],
                      fontWeight: 700,
                      fontSize: 11,
                    }}
                  >
                    {SI_REGIMES[i]}
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

  const renderSiContagion = () => (
    <>
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

  const renderSiAlerts = () => {
    const critCount = SI_ALERTS.filter((a) => a.severity === "critical").length;
    const warnCount = SI_ALERTS.filter((a) => a.severity === "warning").length;
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
            {
              label: "Total Alerts",
              value: `${SI_ALERTS.length}`,
              color: C.cyan,
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

        {(["critical", "warning", "info"] as const).map((sev) => {
          const items = SI_ALERTS.filter((a) => a.severity === sev);
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

  const renderSiCorrDynamics = () => (
    <>
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

  /* ════════════════════════ MAIN RENDER ════════════════════════════ */
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
        Intelligence Hub
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        Market intelligence, signal generation & advanced analytics
      </p>

      <div style={{ marginBottom: 20 }}>
        <Tabs
          tabs={["Market Intelligence", "Signal Intelligence"]}
          active={activeTab}
          onChange={(t) => setActiveTab(t as typeof activeTab)}
        />
      </div>

      {/* ══════════════════ MARKET INTELLIGENCE TAB ══════════════════ */}
      {activeTab === "Market Intelligence" && (
        <div style={{ color: "#F1F5F9" }}>
          {miUsingFallback && (
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

          <div
            style={{
              display: "flex",
              gap: 4,
              marginBottom: 16,
              flexWrap: "wrap",
            }}
          >
            {MI_TABS.map((t) => (
              <button
                key={t}
                onClick={() => setMiTab(t)}
                style={{
                  padding: "8px 14px",
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  border:
                    miTab === t
                      ? "1px solid rgba(212,175,55,0.5)"
                      : "1px solid rgba(51,65,85,0.3)",
                  backgroundColor:
                    miTab === t
                      ? "rgba(212,175,55,0.15)"
                      : "rgba(15,23,42,0.5)",
                  color: miTab === t ? "#D4AF37" : "#94A3B8",
                }}
              >
                {t}
              </button>
            ))}
          </div>

          {/* Market Data */}
          {miTab === "Market Data" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div
                style={{
                  display: "flex",
                  gap: 12,
                  alignItems: "center",
                  flexWrap: "wrap",
                }}
              >
                <label style={{ fontSize: 13, color: "#94A3B8" }}>Asset</label>
                <select
                  value={selectedAsset}
                  onChange={(e) => setSelectedAsset(e.target.value)}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 6,
                    border: "1px solid rgba(51,65,85,0.5)",
                    backgroundColor: "#0F172A",
                    color: "#F1F5F9",
                    fontSize: 13,
                  }}
                >
                  {ASSETS.map((a) => (
                    <option key={a} value={a}>
                      {a}
                    </option>
                  ))}
                </select>
                <label style={{ fontSize: 13, color: "#94A3B8" }}>Period</label>
                <select
                  value={selectedPeriod}
                  onChange={(e) => setSelectedPeriod(Number(e.target.value))}
                  style={{
                    padding: "6px 12px",
                    borderRadius: 6,
                    border: "1px solid rgba(51,65,85,0.5)",
                    backgroundColor: "#0F172A",
                    color: "#F1F5F9",
                    fontSize: 13,
                  }}
                >
                  {PERIODS.map((p) => (
                    <option key={p} value={p}>
                      {p} days
                    </option>
                  ))}
                </select>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
                  gap: 10,
                }}
              >
                {[
                  {
                    label: "Last Price",
                    value: lastD ? `$${lastD.close.toLocaleString()}` : "—",
                  },
                  {
                    label: "Volume",
                    value: lastD ? lastD.volume.toLocaleString() : "—",
                  },
                  { label: "YTD Return", value: `${ytdReturn}%` },
                  { label: "30D Realized Vol", value: `${realizedVol}%` },
                ].map((m) => (
                  <Card key={m.label}>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#64748B",
                        marginBottom: 2,
                      }}
                    >
                      {m.label}
                    </div>
                    <div
                      style={{
                        fontSize: 16,
                        fontWeight: 700,
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#F1F5F9",
                      }}
                    >
                      {m.value}
                    </div>
                  </Card>
                ))}
              </div>

              <Card
                title={`${selectedAsset} — Price (${selectedPeriod}D)`}
                subtitle="OHLC with Moving Averages"
              >
                <div style={{ width: "100%", height: 360 }}>
                  <ResponsiveContainer>
                    <ComposedChart
                      data={chartData}
                      barGap={0}
                      barCategoryGap="4%"
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(51,65,85,0.3)"
                      />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: "#64748B", fontSize: 10 }}
                        interval={Math.max(
                          1,
                          Math.floor(chartData.length / 12),
                        )}
                      />
                      <YAxis
                        domain={["auto", "auto"]}
                        tick={{ fill: "#64748B", fontSize: 10 }}
                        tickFormatter={(v: number) =>
                          v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)
                        }
                      />
                      <Tooltip contentStyle={ttStyle} />
                      <Bar
                        dataKey="high"
                        stackId="wick"
                        fill="transparent"
                        barSize={1}
                        isAnimationActive={false}
                      >
                        {chartData.map((_d, i) => (
                          <Cell key={i} fill="transparent" />
                        ))}
                      </Bar>
                      <Bar
                        dataKey="wickRange"
                        barSize={1}
                        isAnimationActive={false}
                      >
                        {chartData.map((d, i) => (
                          <Cell
                            key={i}
                            fill={d.bullish ? "#10B981" : "#EF4444"}
                          />
                        ))}
                      </Bar>
                      <Bar
                        dataKey="bodyBottom"
                        stackId="body"
                        fill="transparent"
                        barSize={6}
                        isAnimationActive={false}
                      />
                      <Bar
                        dataKey="bodyHeight"
                        stackId="body"
                        barSize={6}
                        isAnimationActive={false}
                      >
                        {chartData.map((d, i) => (
                          <Cell
                            key={i}
                            fill={d.bullish ? "#10B981" : "#EF4444"}
                          />
                        ))}
                      </Bar>
                      <Line
                        type="monotone"
                        dataKey="ma20"
                        stroke="#F59E0B"
                        strokeWidth={1.5}
                        dot={false}
                        name="MA20"
                        connectNulls
                      />
                      <Line
                        type="monotone"
                        dataKey="ma50"
                        stroke="#3B82F6"
                        strokeWidth={1.5}
                        dot={false}
                        name="MA50"
                        connectNulls
                      />
                      {ma200 && (
                        <Line
                          type="monotone"
                          dataKey="ma200"
                          stroke="#EF4444"
                          strokeWidth={1.5}
                          dot={false}
                          name="MA200"
                          connectNulls
                        />
                      )}
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card title="Volume" subtitle="Daily trading volume">
                <div style={{ width: "100%", height: 160 }}>
                  <ResponsiveContainer>
                    <BarChart data={chartData}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(51,65,85,0.3)"
                      />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: "#64748B", fontSize: 10 }}
                        interval={Math.max(
                          1,
                          Math.floor(chartData.length / 12),
                        )}
                      />
                      <YAxis
                        tick={{ fill: "#64748B", fontSize: 10 }}
                        tickFormatter={(v: number) =>
                          v >= 1e9
                            ? `${(v / 1e9).toFixed(1)}B`
                            : v >= 1e6
                              ? `${(v / 1e6).toFixed(0)}M`
                              : `${(v / 1e3).toFixed(0)}K`
                        }
                      />
                      <Tooltip
                        contentStyle={ttStyle}
                        formatter={((v: number) => v.toLocaleString()) as any}
                      />
                      <Bar dataKey="volume" isAnimationActive={false}>
                        {chartData.map((d, i) => (
                          <Cell
                            key={i}
                            fill={
                              d.bullish
                                ? "rgba(16,185,129,0.6)"
                                : "rgba(239,68,68,0.6)"
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card title="Daily Returns" subtitle="Day-over-day % change">
                <div style={{ width: "100%", height: 160 }}>
                  <ResponsiveContainer>
                    <BarChart data={chartData.slice(1)}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(51,65,85,0.3)"
                      />
                      <XAxis
                        dataKey="date"
                        tick={{ fill: "#64748B", fontSize: 10 }}
                        interval={Math.max(
                          1,
                          Math.floor(chartData.length / 12),
                        )}
                      />
                      <YAxis
                        tick={{ fill: "#64748B", fontSize: 10 }}
                        tickFormatter={(v: number) => `${v}%`}
                      />
                      <Tooltip
                        contentStyle={ttStyle}
                        formatter={((v: number) => `${v}%`) as any}
                      />
                      <Bar dataKey="dailyReturn" isAnimationActive={false}>
                        {chartData.slice(1).map((d, i) => (
                          <Cell
                            key={i}
                            fill={d.dailyReturn >= 0 ? "#10B981" : "#EF4444"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          )}

          {/* Overview */}
          {miTab === "Overview" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
                  gap: 10,
                }}
              >
                {MARKET_SUMMARY.map((m) => (
                  <Card key={m.label}>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#64748B",
                        marginBottom: 2,
                      }}
                    >
                      {m.label}
                    </div>
                    <div
                      style={{
                        fontSize: 16,
                        fontWeight: 700,
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#F1F5F9",
                      }}
                    >
                      {m.value}
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: m.up ? "#10B981" : "#EF4444",
                        marginTop: 2,
                      }}
                    >
                      {m.change}
                    </div>
                  </Card>
                ))}
              </div>
              <Card
                title="Sector Performance (1D)"
                subtitle="S&P 500 GICS sectors"
              >
                <div style={{ width: "100%", height: 320 }}>
                  <ResponsiveContainer>
                    <BarChart
                      data={SECTORS.sort((a, b) => b.perf - a.perf)}
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
                        dataKey="name"
                        tick={{ fill: "#F1F5F9", fontSize: 11 }}
                        width={120}
                      />
                      <Tooltip
                        contentStyle={ttStyle}
                        formatter={(v: any) => `${v}%`}
                      />
                      <Bar
                        dataKey="perf"
                        radius={[0, 4, 4, 0]}
                        fill="#D4AF37"
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        shape={(props: any) => {
                          const { x, y, width, height, payload } = props;
                          return (
                            <rect
                              x={payload.perf >= 0 ? x : x + width}
                              y={y}
                              width={Math.abs(width)}
                              height={height}
                              rx={4}
                              fill={payload.perf >= 0 ? "#10B981" : "#EF4444"}
                            />
                          );
                        }}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          )}

          {/* Signals */}
          {miTab === "Signals" && (
            <Card
              title="Active Signals"
              subtitle="Algorithmically detected trading signals"
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
                        "Time",
                        "Ticker",
                        "Signal",
                        "Strength",
                        "Direction",
                      ].map((h) => (
                        <th
                          key={h}
                          style={{
                            padding: "8px 12px",
                            textAlign: h === "Strength" ? "center" : "left",
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
                    {MI_SIGNALS.map((s) => (
                      <tr
                        key={s.id}
                        style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                      >
                        <td
                          style={{
                            padding: "8px 12px",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#64748B",
                          }}
                        >
                          {s.time}
                        </td>
                        <td
                          style={{
                            padding: "8px 12px",
                            fontFamily: "JetBrains Mono, monospace",
                            fontWeight: 700,
                            color: "#D4AF37",
                          }}
                        >
                          {s.ticker}
                        </td>
                        <td style={{ padding: "8px 12px", color: "#F1F5F9" }}>
                          {s.signal}
                        </td>
                        <td
                          style={{ padding: "8px 12px", textAlign: "center" }}
                        >
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 6,
                              justifyContent: "center",
                            }}
                          >
                            <div
                              style={{
                                width: 50,
                                height: 6,
                                backgroundColor: "rgba(51,65,85,0.3)",
                                borderRadius: 3,
                              }}
                            >
                              <div
                                style={{
                                  width: `${s.strength}%`,
                                  height: 6,
                                  borderRadius: 3,
                                  backgroundColor:
                                    s.strength >= 80
                                      ? "#10B981"
                                      : s.strength >= 65
                                        ? "#F59E0B"
                                        : "#94A3B8",
                                }}
                              />
                            </div>
                            <span
                              style={{
                                fontFamily: "JetBrains Mono, monospace",
                                fontSize: 12,
                                color: "#94A3B8",
                              }}
                            >
                              {s.strength}
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: "8px 12px" }}>
                          <Badge
                            variant={s.direction === "Long" ? "up" : "down"}
                          >
                            {s.direction}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Health Score */}
          {miTab === "Health Score" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Card>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 20,
                    marginBottom: 16,
                  }}
                >
                  <div
                    style={{ position: "relative", width: 100, height: 100 }}
                  >
                    <svg viewBox="0 0 100 100" width={100} height={100}>
                      <circle
                        cx={50}
                        cy={50}
                        r={42}
                        fill="none"
                        stroke="rgba(51,65,85,0.3)"
                        strokeWidth={8}
                      />
                      <circle
                        cx={50}
                        cy={50}
                        r={42}
                        fill="none"
                        stroke={
                          overallHealth >= 70
                            ? "#10B981"
                            : overallHealth >= 50
                              ? "#F59E0B"
                              : "#EF4444"
                        }
                        strokeWidth={8}
                        strokeDasharray={`${overallHealth * 2.64} ${264 - overallHealth * 2.64}`}
                        strokeDashoffset={66}
                        strokeLinecap="round"
                      />
                    </svg>
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: "JetBrains Mono, monospace",
                        fontSize: 28,
                        fontWeight: 700,
                        color: "#F1F5F9",
                      }}
                    >
                      {overallHealth}
                    </div>
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: 18,
                        fontWeight: 700,
                        color: "#F1F5F9",
                      }}
                    >
                      AI Market Health Score
                    </div>
                    <div style={{ fontSize: 13, color: "#94A3B8" }}>
                      Composite of 6 sub-indicators — updated every 5 minutes
                    </div>
                    <Badge
                      variant={
                        overallHealth >= 70
                          ? "up"
                          : overallHealth >= 50
                            ? "warning"
                            : "down"
                      }
                    >
                      {overallHealth >= 70
                        ? "HEALTHY"
                        : overallHealth >= 50
                          ? "CAUTIOUS"
                          : "STRESSED"}
                    </Badge>
                  </div>
                </div>
              </Card>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                  gap: 10,
                }}
              >
                {HEALTH_COMPONENTS.map((h) => (
                  <Card key={h.label}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: 6,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: "#F1F5F9",
                        }}
                      >
                        {h.label}
                      </span>
                      <span
                        style={{
                          fontFamily: "JetBrains Mono, monospace",
                          fontWeight: 700,
                          color: h.color,
                        }}
                      >
                        {h.score}
                      </span>
                    </div>
                    <div
                      style={{
                        height: 6,
                        backgroundColor: "rgba(51,65,85,0.3)",
                        borderRadius: 3,
                        marginBottom: 6,
                      }}
                    >
                      <div
                        style={{
                          width: `${h.score}%`,
                          height: 6,
                          backgroundColor: h.color,
                          borderRadius: 3,
                        }}
                      />
                    </div>
                    <div style={{ fontSize: 11, color: "#64748B" }}>
                      {h.desc}
                    </div>
                  </Card>
                ))}
              </div>
              <Card title="Health Score Trend (30D)">
                <div style={{ width: "100%", height: 200 }}>
                  <ResponsiveContainer>
                    <LineChart data={HEALTH_HISTORY}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(51,65,85,0.3)"
                      />
                      <XAxis
                        dataKey="day"
                        tick={{ fill: "#64748B", fontSize: 10 }}
                        interval={4}
                      />
                      <YAxis
                        domain={[0, 100]}
                        tick={{ fill: "#64748B", fontSize: 10 }}
                      />
                      <Tooltip contentStyle={ttStyle} />
                      <Line
                        type="monotone"
                        dataKey="score"
                        stroke="#D4AF37"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          )}

          {/* Alerts */}
          {miTab === "Alerts" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {MI_ALERTS.map((a) => (
                <Card key={a.id}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: 12,
                    }}
                  >
                    <div
                      style={{
                        width: 4,
                        minHeight: 40,
                        borderRadius: 2,
                        flexShrink: 0,
                        backgroundColor:
                          a.severity === "high"
                            ? "#EF4444"
                            : a.severity === "medium"
                              ? "#F59E0B"
                              : "#64748B",
                      }}
                    />
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          marginBottom: 4,
                        }}
                      >
                        <span
                          style={{
                            fontSize: 14,
                            fontWeight: 600,
                            color: "#F1F5F9",
                          }}
                        >
                          {a.title}
                        </span>
                        <div
                          style={{
                            display: "flex",
                            gap: 8,
                            alignItems: "center",
                          }}
                        >
                          <Badge
                            variant={
                              a.severity === "high"
                                ? "down"
                                : a.severity === "medium"
                                  ? "warning"
                                  : "neutral"
                            }
                          >
                            {a.severity.toUpperCase()}
                          </Badge>
                          <span
                            style={{
                              fontSize: 11,
                              fontFamily: "JetBrains Mono, monospace",
                              color: "#64748B",
                            }}
                          >
                            {a.time}
                          </span>
                        </div>
                      </div>
                      <div
                        style={{
                          fontSize: 13,
                          color: "#94A3B8",
                          marginBottom: 4,
                        }}
                      >
                        {a.detail}
                      </div>
                      <div style={{ fontSize: 11, color: "#475569" }}>
                        Source: {a.source}
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}

          {/* News */}
          {miTab === "News" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Card
                title="Sector Sentiment Heatmap"
                subtitle="Sentiment score & momentum by sector"
              >
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 8 }}
                >
                  {SECTOR_SENTIMENT.map((s) => (
                    <div
                      key={s.sector}
                      style={{ display: "flex", alignItems: "center", gap: 12 }}
                    >
                      <span
                        style={{
                          width: 120,
                          fontSize: 13,
                          color: "#F1F5F9",
                          flexShrink: 0,
                        }}
                      >
                        {s.sector}
                      </span>
                      <div
                        style={{
                          flex: 1,
                          height: 20,
                          backgroundColor: "rgba(51,65,85,0.3)",
                          borderRadius: 4,
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${s.score}%`,
                            height: "100%",
                            borderRadius: 4,
                            backgroundColor:
                              s.score >= 70
                                ? "#10B981"
                                : s.score >= 55
                                  ? "#F59E0B"
                                  : s.score >= 45
                                    ? "#94A3B8"
                                    : "#EF4444",
                          }}
                        />
                      </div>
                      <span
                        style={{
                          width: 36,
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          fontSize: 12,
                          color: "#F1F5F9",
                        }}
                      >
                        {s.score}
                      </span>
                      <span
                        style={{
                          width: 50,
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          fontSize: 12,
                          color: s.momentum >= 0 ? "#10B981" : "#EF4444",
                        }}
                      >
                        {s.momentum >= 0 ? "+" : ""}
                        {s.momentum}%
                      </span>
                    </div>
                  ))}
                </div>
              </Card>

              <Card
                title="Market News Feed"
                subtitle="Latest headlines & sentiment"
              >
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 10 }}
                >
                  {NEWS.map((n, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 12,
                        padding: "10px 0",
                        borderBottom:
                          idx < NEWS.length - 1
                            ? "1px solid rgba(51,65,85,0.2)"
                            : "none",
                      }}
                    >
                      <div style={{ flex: 1 }}>
                        <div
                          style={{
                            fontSize: 14,
                            fontWeight: 600,
                            color: "#F1F5F9",
                            marginBottom: 4,
                          }}
                        >
                          {n.title}
                        </div>
                        <div
                          style={{
                            display: "flex",
                            gap: 12,
                            alignItems: "center",
                          }}
                        >
                          <span style={{ fontSize: 11, color: "#64748B" }}>
                            {n.source}
                          </span>
                          <span style={{ fontSize: 11, color: "#64748B" }}>
                            {n.time}
                          </span>
                        </div>
                      </div>
                      <Badge
                        variant={
                          n.sentiment === "positive"
                            ? "up"
                            : n.sentiment === "negative"
                              ? "down"
                              : "neutral"
                        }
                      >
                        {n.sentiment.charAt(0).toUpperCase() +
                          n.sentiment.slice(1)}
                      </Badge>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════ SIGNAL INTELLIGENCE TAB ══════════════════ */}
      {activeTab === "Signal Intelligence" && (
        <div style={{ color: C.t1 }}>
          {!siLiveData && (
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
              Backend unreachable — displaying demo data
            </div>
          )}
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
            RESEARCH / EXPERIMENTAL — Buy/Sell signals, regime confidence %,
            alert probabilities and correlation matrices are static demo values,
            not calibrated real-time outputs. Not valid for live trading or risk
            decisions.
          </div>
          <p style={{ color: C.t2, marginBottom: 16, fontSize: 14 }}>
            Advanced signal generation, regime detection, contagion analysis &
            smart alerts
          </p>

          <div style={{ marginBottom: 20 }}>
            <Tabs
              tabs={SI_TABS_LIST}
              active={siActiveTab}
              onChange={setSiActiveTab}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {siActiveTab === SI_TABS_LIST[0] && renderSiSignals()}
            {siActiveTab === SI_TABS_LIST[1] && renderSiRegime()}
            {siActiveTab === SI_TABS_LIST[2] && renderSiContagion()}
            {siActiveTab === SI_TABS_LIST[3] && renderSiAlerts()}
            {siActiveTab === SI_TABS_LIST[4] && renderSiCorrDynamics()}
          </div>
        </div>
      )}
    </div>
  );
}
