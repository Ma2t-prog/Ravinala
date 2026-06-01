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
import { Card } from "../../components/ui";
import { useSnapshot } from "../../hooks/useMarketData";

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
  "Technical",
  "Fundamentals",
  "Peer Comparison",
  "Screener",
  "Quant Signals",
] as const;
type Tab = (typeof TABS)[number];

/* ═══════════════════════════════════════════
   TECHNICAL DATA
═══════════════════════════════════════════ */
const BASE = 185;
const chartData = Array.from({ length: 120 }, (_, i) => {
  const trend = Math.sin(i * 0.05) * 20 + Math.sin(i * 0.02) * 10;
  const noise = Math.sin(i * 1.7) * 2;
  const price = BASE + trend + noise + i * 0.08;
  const ma20 =
    i >= 19
      ? BASE +
        Math.sin((i - 10) * 0.05) * 20 +
        Math.sin((i - 10) * 0.02) * 10 +
        (i - 10) * 0.08
      : undefined;
  const ma50 =
    i >= 49
      ? BASE +
        Math.sin((i - 25) * 0.05) * 20 +
        Math.sin((i - 25) * 0.02) * 10 +
        (i - 25) * 0.08
      : undefined;
  const ma200 = i >= 60 ? BASE + (i - 60) * 0.08 + 5 : undefined;
  const rsi = 30 + Math.sin(i * 0.1) * 25 + Math.sin(i * 0.3) * 5;
  const macdLine = Math.sin(i * 0.08) * 3 + Math.sin(i * 0.15) * 0.5;
  const signal = Math.sin((i - 3) * 0.08) * 2.5;
  const histogram = macdLine - signal;
  const volume = 20 + Math.abs(Math.sin(i * 0.2)) * 25;
  const bbUpper = price + 8 + Math.sin(i * 0.1) * 3;
  const bbLower = price - 8 - Math.sin(i * 0.1) * 3;
  return {
    day: i + 1,
    date: `Day ${i + 1}`,
    price: +price.toFixed(2),
    ma20: ma20 !== undefined ? +ma20.toFixed(2) : undefined,
    ma50: ma50 !== undefined ? +ma50.toFixed(2) : undefined,
    ma200: ma200 !== undefined ? +ma200.toFixed(2) : undefined,
    rsi: +Math.min(100, Math.max(0, rsi)).toFixed(1),
    macd: +macdLine.toFixed(3),
    signal: +signal.toFixed(3),
    histogram: +histogram.toFixed(3),
    volume: +volume.toFixed(1),
    bbUpper: +bbUpper.toFixed(2),
    bbLower: +bbLower.toFixed(2),
  };
});

const INDICATORS = [
  { name: "RSI (14)", value: "58.4", status: "Neutral", color: AMBER },
  { name: "MACD", value: "1.24", status: "Bullish", color: GREEN },
  { name: "Bollinger", value: "Mid-Band", status: "Neutral", color: AMBER },
  { name: "Stochastic", value: "72.1", status: "Overbought", color: RED },
  { name: "ADX", value: "28.5", status: "Trending", color: CYAN },
  { name: "OBV", value: "+12.4M", status: "Accumulation", color: GREEN },
];

/* ═══════════════════════════════════════════
   FUNDAMENTALS DATA
═══════════════════════════════════════════ */
const fundamentals = {
  ticker: "AAPL",
  name: "Apple Inc.",
  sector: "Technology",
  mcap: "3.42T",
  price: 198.42,
  metrics: [
    { label: "P/E Ratio", value: "31.2", industry: "28.5", verdict: "Premium" },
    { label: "Fwd P/E", value: "28.8", industry: "26.1", verdict: "Premium" },
    {
      label: "PEG Ratio",
      value: "2.14",
      industry: "1.85",
      verdict: "Overvalued",
    },
    { label: "P/S Ratio", value: "8.92", industry: "6.45", verdict: "Premium" },
    {
      label: "P/B Ratio",
      value: "48.2",
      industry: "12.8",
      verdict: "Expensive",
    },
    { label: "EV/EBITDA", value: "25.8", industry: "20.2", verdict: "Premium" },
    { label: "Debt/Equity", value: "1.76", industry: "0.85", verdict: "High" },
    { label: "ROE", value: "157.4%", industry: "28.5%", verdict: "Excellent" },
    {
      label: "Net Margin",
      value: "26.3%",
      industry: "18.2%",
      verdict: "Strong",
    },
    {
      label: "FCF Yield",
      value: "3.2%",
      industry: "4.1%",
      verdict: "Below avg",
    },
  ],
};

const revenueData = Array.from({ length: 8 }, (_, i) => {
  const qs = [
    "Q1 24",
    "Q2 24",
    "Q3 24",
    "Q4 24",
    "Q1 25",
    "Q2 25",
    "Q3 25",
    "Q4 25",
  ];
  return {
    quarter: qs[i],
    revenue: +(
      82 +
      Math.sin(i * 0.8) * 12 +
      i * 2.5 +
      Math.random() * 3
    ).toFixed(1),
    earnings: +(
      1.25 +
      Math.sin(i * 0.6) * 0.3 +
      i * 0.05 +
      Math.random() * 0.1
    ).toFixed(2),
    margin: +(24 + Math.sin(i * 0.5) * 3 + Math.random() * 1.5).toFixed(1),
  };
});

const cashFlowData = [
  { item: "Operating CF", value: 118.2, prev: 110.5 },
  { item: "Capital Expenditure", value: -11.8, prev: -10.2 },
  { item: "Free Cash Flow", value: 106.4, prev: 100.3 },
  { item: "Dividends Paid", value: -15.2, prev: -14.8 },
  { item: "Share Buybacks", value: -85.5, prev: -77.2 },
  { item: "Net Debt Change", value: -12.4, prev: 8.5 },
];

/* ═══════════════════════════════════════════
   PEER COMPARISON DATA
═══════════════════════════════════════════ */
const peers = [
  {
    ticker: "AAPL",
    pe: 31.2,
    ps: 8.9,
    roe: 157,
    margin: 26.3,
    growth: 8.2,
    beta: 1.23,
    div: 0.55,
    mcap: "3.42T",
    score: 88,
  },
  {
    ticker: "MSFT",
    pe: 35.8,
    ps: 13.2,
    roe: 38.5,
    margin: 35.2,
    growth: 14.5,
    beta: 0.92,
    div: 0.72,
    mcap: "3.18T",
    score: 91,
  },
  {
    ticker: "GOOGL",
    pe: 24.5,
    ps: 6.8,
    roe: 28.2,
    margin: 25.1,
    growth: 12.8,
    beta: 1.08,
    div: 0.0,
    mcap: "2.15T",
    score: 85,
  },
  {
    ticker: "AMZN",
    pe: 58.2,
    ps: 3.4,
    roe: 22.8,
    margin: 8.2,
    growth: 18.4,
    beta: 1.18,
    div: 0.0,
    mcap: "1.98T",
    score: 82,
  },
  {
    ticker: "META",
    pe: 22.8,
    ps: 8.5,
    roe: 32.1,
    margin: 28.5,
    growth: 22.1,
    beta: 1.35,
    div: 0.38,
    mcap: "1.42T",
    score: 87,
  },
  {
    ticker: "NVDA",
    pe: 62.5,
    ps: 38.2,
    roe: 85.2,
    margin: 55.8,
    growth: 125.4,
    beta: 1.72,
    div: 0.03,
    mcap: "3.65T",
    score: 94,
  },
  {
    ticker: "TSLA",
    pe: 85.3,
    ps: 12.8,
    roe: 18.5,
    margin: 8.5,
    growth: -8.2,
    beta: 2.05,
    div: 0.0,
    mcap: "0.85T",
    score: 62,
  },
];

const peerRadar = [
  { metric: "Valuation", AAPL: 65, MSFT: 58, NVDA: 35, GOOGL: 72 },
  { metric: "Growth", AAPL: 52, MSFT: 68, NVDA: 95, GOOGL: 65 },
  { metric: "Profitability", AAPL: 82, MSFT: 88, NVDA: 92, GOOGL: 78 },
  { metric: "Leverage", AAPL: 45, MSFT: 72, NVDA: 85, GOOGL: 88 },
  { metric: "Momentum", AAPL: 60, MSFT: 65, NVDA: 90, GOOGL: 55 },
  { metric: "Dividend", AAPL: 45, MSFT: 55, NVDA: 10, GOOGL: 15 },
];

/* ═══════════════════════════════════════════
   SCREENER DATA
═══════════════════════════════════════════ */
const screenerResults = [
  {
    ticker: "NVDA",
    name: "NVIDIA",
    sector: "Tech",
    price: 924.8,
    pe: 62.5,
    roe: 85.2,
    growth: 125.4,
    rsi: 71.2,
    signal: "Buy" as const,
  },
  {
    ticker: "META",
    name: "Meta Platforms",
    sector: "Tech",
    price: 502.3,
    pe: 22.8,
    roe: 32.1,
    growth: 22.1,
    rsi: 58.4,
    signal: "Buy" as const,
  },
  {
    ticker: "MSFT",
    name: "Microsoft",
    sector: "Tech",
    price: 418.5,
    pe: 35.8,
    roe: 38.5,
    growth: 14.5,
    rsi: 55.2,
    signal: "Hold" as const,
  },
  {
    ticker: "AAPL",
    name: "Apple Inc",
    sector: "Tech",
    price: 198.4,
    pe: 31.2,
    roe: 157.4,
    growth: 8.2,
    rsi: 58.4,
    signal: "Hold" as const,
  },
  {
    ticker: "GOOGL",
    name: "Alphabet",
    sector: "Tech",
    price: 155.2,
    pe: 24.5,
    roe: 28.2,
    growth: 12.8,
    rsi: 48.5,
    signal: "Buy" as const,
  },
  {
    ticker: "JPM",
    name: "JPMorgan Chase",
    sector: "Finance",
    price: 198.2,
    pe: 12.1,
    roe: 15.8,
    growth: 8.5,
    rsi: 62.1,
    signal: "Buy" as const,
  },
  {
    ticker: "V",
    name: "Visa Inc",
    sector: "Finance",
    price: 285.6,
    pe: 30.2,
    roe: 48.5,
    growth: 10.2,
    rsi: 54.8,
    signal: "Hold" as const,
  },
  {
    ticker: "UNH",
    name: "UnitedHealth",
    sector: "Health",
    price: 528.4,
    pe: 18.5,
    roe: 25.8,
    growth: 12.4,
    rsi: 42.1,
    signal: "Buy" as const,
  },
  {
    ticker: "LLY",
    name: "Eli Lilly",
    sector: "Health",
    price: 782.5,
    pe: 58.2,
    roe: 62.8,
    growth: 32.5,
    rsi: 68.5,
    signal: "Hold" as const,
  },
  {
    ticker: "XOM",
    name: "Exxon Mobil",
    sector: "Energy",
    price: 108.2,
    pe: 12.8,
    roe: 18.2,
    growth: -5.2,
    rsi: 38.5,
    signal: "Sell" as const,
  },
  {
    ticker: "CVX",
    name: "Chevron",
    sector: "Energy",
    price: 152.8,
    pe: 14.2,
    roe: 15.5,
    growth: -8.4,
    rsi: 35.2,
    signal: "Sell" as const,
  },
  {
    ticker: "COST",
    name: "Costco",
    sector: "Staples",
    price: 845.2,
    pe: 52.5,
    roe: 28.5,
    growth: 9.8,
    rsi: 62.5,
    signal: "Hold" as const,
  },
];

const sectorDistribution = [
  { name: "Tech", value: 5, color: CYAN },
  { name: "Finance", value: 2, color: GOLD },
  { name: "Health", value: 2, color: GREEN },
  { name: "Energy", value: 2, color: RED },
  { name: "Staples", value: 1, color: PURPLE },
];

/* ═══════════════════════════════════════════
   QUANT SIGNALS DATA
═══════════════════════════════════════════ */
const quantSignals = [
  {
    ticker: "NVDA",
    strategy: "Momentum Breakout",
    direction: "Long" as const,
    confidence: 92,
    entry: 918.5,
    target: 1050.0,
    stop: 875.0,
    timeframe: "2-4 wks",
    pnl: "+3.8%",
  },
  {
    ticker: "META",
    strategy: "Mean Reversion",
    direction: "Long" as const,
    confidence: 78,
    entry: 495.2,
    target: 530.0,
    stop: 478.0,
    timeframe: "1-2 wks",
    pnl: "+1.4%",
  },
  {
    ticker: "XOM",
    strategy: "Trend Following",
    direction: "Short" as const,
    confidence: 71,
    entry: 110.5,
    target: 98.0,
    stop: 116.0,
    timeframe: "3-6 wks",
    pnl: "-2.1%",
  },
  {
    ticker: "AAPL",
    strategy: "Support Bounce",
    direction: "Long" as const,
    confidence: 68,
    entry: 195.0,
    target: 210.0,
    stop: 188.0,
    timeframe: "2-3 wks",
    pnl: "+1.7%",
  },
  {
    ticker: "JPM",
    strategy: "Earnings Momentum",
    direction: "Long" as const,
    confidence: 82,
    entry: 196.8,
    target: 215.0,
    stop: 190.0,
    timeframe: "4-8 wks",
    pnl: "+0.7%",
  },
  {
    ticker: "TSLA",
    strategy: "Volatility Crush",
    direction: "Short" as const,
    confidence: 65,
    entry: 178.5,
    target: 155.0,
    stop: 192.0,
    timeframe: "2-4 wks",
    pnl: "-5.2%",
  },
  {
    ticker: "GOOGL",
    strategy: "Factor Rotation",
    direction: "Long" as const,
    confidence: 74,
    entry: 152.8,
    target: 170.0,
    stop: 145.0,
    timeframe: "3-5 wks",
    pnl: "+1.6%",
  },
  {
    ticker: "UNH",
    strategy: "Sector Tilt",
    direction: "Long" as const,
    confidence: 76,
    entry: 525.0,
    target: 560.0,
    stop: 510.0,
    timeframe: "4-6 wks",
    pnl: "+0.6%",
  },
];

const strategyPerf = Array.from({ length: 12 }, (_, i) => ({
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
    1.5 +
    Math.sin(i * 0.5) * 3.2 +
    Math.random() * 1.2 -
    0.6
  ).toFixed(2),
  meanRev: +(0.8 + Math.cos(i * 0.4) * 2.0 + Math.random() * 0.8 - 0.4).toFixed(
    2,
  ),
  factor: +(1.2 + Math.sin(i * 0.3) * 1.8 + Math.random() * 0.6 - 0.3).toFixed(
    2,
  ),
  combined: +(
    1.8 +
    Math.sin(i * 0.35) * 2.5 +
    Math.random() * 0.5 -
    0.25
  ).toFixed(2),
}));

/* ═══════════════════════════════════════════
   COMPONENT
═══════════════════════════════════════════ */
export default function FinancialAnalysis() {
  const { data: snapshotData } = useSnapshot();
  const usingFallback = !snapshotData;
  const [tab, setTab] = useState<Tab>("Technical");
  const [sortCol, setSortCol] = useState<string>("");
  const [sortAsc, setSortAsc] = useState(true);
  const [screenerSector, setScreenerSector] = useState("All");

  const toggleSort = (col: string) => {
    setSortAsc(sortCol === col ? !sortAsc : true);
    setSortCol(col);
  };

  const sortedScreener = useMemo(() => {
    let data =
      screenerSector === "All"
        ? screenerResults
        : screenerResults.filter((s) => s.sector === screenerSector);
    if (!sortCol) return data;
    return [...data].sort((a, b) => {
      const va = (a as Record<string, unknown>)[sortCol],
        vb = (b as Record<string, unknown>)[sortCol];
      const cmp =
        typeof va === "number" && typeof vb === "number"
          ? va - vb
          : String(va).localeCompare(String(vb));
      return sortAsc ? cmp : -cmp;
    });
  }, [sortCol, sortAsc, screenerSector]);

  const th = (label: string, col: string, align: string = "center") => (
    <th
      onClick={() => toggleSort(col)}
      style={{
        cursor: "pointer",
        padding: "6px 10px",
        textAlign: align as "left" | "center" | "right",
        fontSize: 11,
        color: "#94A3B8",
        borderBottom: "1px solid rgba(51,65,85,0.3)",
      }}
    >
      {label} {sortCol === col ? (sortAsc ? "▲" : "▼") : ""}
    </th>
  );

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
        Financial Analysis
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        Technical charting, fundamentals, peer comparison & quant signals
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

      {/* ═══════════ Technical ═══════════ */}
      {tab === "Technical" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(6,1fr)",
              gap: 10,
              marginBottom: 16,
            }}
          >
            {INDICATORS.map((ind) => (
              <div
                key={ind.name}
                style={{
                  backgroundColor: "rgba(10,14,26,0.5)",
                  borderRadius: 8,
                  padding: 10,
                  border: "1px solid rgba(51,65,85,0.2)",
                }}
              >
                <div style={{ fontSize: 10, color: "#64748B" }}>{ind.name}</div>
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    fontFamily: mono,
                    color: "#F1F5F9",
                  }}
                >
                  {ind.value}
                </div>
                <div style={{ fontSize: 10, color: ind.color }}>
                  {ind.status}
                </div>
              </div>
            ))}
          </div>

          <Card
            title="AAPL — Price, MAs & Bollinger Bands"
            subtitle="20/50/200-day Moving Averages with Bollinger Bands (2σ)"
          >
            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <LineChart data={chartData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    interval={19}
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fill: "#64748B", fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={((v: number) => `$${v.toFixed(2)}`) as any}
                  />
                  <Line
                    type="monotone"
                    dataKey="bbUpper"
                    stroke="rgba(168,85,247,0.3)"
                    strokeWidth={1}
                    dot={false}
                    name="BB Upper"
                  />
                  <Line
                    type="monotone"
                    dataKey="bbLower"
                    stroke="rgba(168,85,247,0.3)"
                    strokeWidth={1}
                    dot={false}
                    name="BB Lower"
                  />
                  <Line
                    type="monotone"
                    dataKey="price"
                    stroke="#F1F5F9"
                    strokeWidth={1.5}
                    dot={false}
                    name="Price"
                  />
                  <Line
                    type="monotone"
                    dataKey="ma20"
                    stroke={CYAN}
                    strokeWidth={1.5}
                    dot={false}
                    name="MA 20"
                  />
                  <Line
                    type="monotone"
                    dataKey="ma50"
                    stroke={GOLD}
                    strokeWidth={1.5}
                    dot={false}
                    name="MA 50"
                  />
                  <Line
                    type="monotone"
                    dataKey="ma200"
                    stroke={RED}
                    strokeWidth={1.5}
                    dot={false}
                    name="MA 200"
                  />
                  <Legend />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginTop: 16,
            }}
          >
            <Card title="RSI (14)" subtitle="Overbought >70, Oversold <30">
              <div style={{ width: "100%", height: 200 }}>
                <ResponsiveContainer>
                  <AreaChart data={chartData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                      interval={29}
                    />
                    <YAxis
                      domain={[0, 100]}
                      tick={{ fill: "#64748B", fontSize: 10 }}
                      ticks={[0, 30, 50, 70, 100]}
                    />
                    <Tooltip contentStyle={ttStyle} />
                    <ReferenceLine
                      y={70}
                      stroke="rgba(239,68,68,0.4)"
                      strokeDasharray="4 4"
                    />
                    <ReferenceLine
                      y={30}
                      stroke="rgba(16,185,129,0.4)"
                      strokeDasharray="4 4"
                    />
                    <Area
                      type="monotone"
                      dataKey="rsi"
                      stroke={PURPLE}
                      fill={PURPLE}
                      fillOpacity={0.1}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card title="MACD" subtitle="Signal line crossover indicator">
              <div style={{ width: "100%", height: 200 }}>
                <ResponsiveContainer>
                  <ComposedChart data={chartData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                      interval={29}
                    />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip contentStyle={ttStyle} />
                    <ReferenceLine y={0} stroke="rgba(100,116,139,0.3)" />
                    <Bar dataKey="histogram" opacity={0.4}>
                      {chartData.map((d, i) => (
                        <Cell key={i} fill={d.histogram >= 0 ? GREEN : RED} />
                      ))}
                    </Bar>
                    <Line
                      type="monotone"
                      dataKey="macd"
                      stroke={CYAN}
                      strokeWidth={2}
                      dot={false}
                      name="MACD"
                    />
                    <Line
                      type="monotone"
                      dataKey="signal"
                      stroke={RED}
                      strokeWidth={1.5}
                      dot={false}
                      name="Signal"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <div style={{ marginTop: 16 }}>
            <Card
              title="Volume Analysis"
              subtitle="Daily trading volume (millions)"
            >
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
                      interval={19}
                    />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip
                      contentStyle={ttStyle}
                      formatter={((v: number) => `${v.toFixed(1)}M`) as any}
                    />
                    <Bar dataKey="volume" radius={[2, 2, 0, 0]}>
                      {chartData.map((d, i) => (
                        <Cell
                          key={i}
                          fill={
                            d.price > (chartData[i - 1]?.price || d.price)
                              ? GREEN
                              : RED
                          }
                          opacity={0.5}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}

      {/* ═══════════ Fundamentals ═══════════ */}
      {tab === "Fundamentals" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi("Market Cap", fundamentals.mcap, fundamentals.ticker, CYAN)}
            {kpi("P/E Ratio", "31.2x", "vs Industry 28.5x", AMBER)}
            {kpi("ROE", "157.4%", "exceptional", GREEN)}
            {kpi("Net Margin", "26.3%", "vs Industry 18.2%", GOLD)}
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
              title="Valuation Metrics"
              subtitle={`${fundamentals.ticker} vs industry average`}
            >
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {["Metric", "Value", "Industry", "Verdict"].map((h) => (
                        <th
                          key={h}
                          style={{
                            padding: "5px 8px",
                            textAlign: h === "Metric" ? "left" : "center",
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
                    {fundamentals.metrics.map((m) => (
                      <tr
                        key={m.label}
                        style={{
                          borderBottom: "1px solid rgba(51,65,85,0.12)",
                        }}
                      >
                        <td
                          style={{
                            padding: "5px 8px",
                            fontSize: 12,
                            color: "#F1F5F9",
                          }}
                        >
                          {m.label}
                        </td>
                        <td
                          style={{
                            padding: "5px 8px",
                            textAlign: "center",
                            fontFamily: mono,
                            fontSize: 12,
                            fontWeight: 600,
                          }}
                        >
                          {m.value}
                        </td>
                        <td
                          style={{
                            padding: "5px 8px",
                            textAlign: "center",
                            fontFamily: mono,
                            fontSize: 12,
                            color: "#94A3B8",
                          }}
                        >
                          {m.industry}
                        </td>
                        <td style={{ padding: "5px 8px", textAlign: "center" }}>
                          <span
                            style={{
                              padding: "2px 8px",
                              borderRadius: 4,
                              fontSize: 10,
                              fontWeight: 600,
                              backgroundColor:
                                m.verdict.includes("Excellent") ||
                                m.verdict.includes("Strong")
                                  ? "rgba(16,185,129,0.15)"
                                  : m.verdict.includes("Expensive") ||
                                      m.verdict.includes("High") ||
                                      m.verdict.includes("Overvalued")
                                    ? "rgba(239,68,68,0.15)"
                                    : "rgba(245,158,11,0.15)",
                              color:
                                m.verdict.includes("Excellent") ||
                                m.verdict.includes("Strong")
                                  ? GREEN
                                  : m.verdict.includes("Expensive") ||
                                      m.verdict.includes("High") ||
                                      m.verdict.includes("Overvalued")
                                    ? RED
                                    : AMBER,
                            }}
                          >
                            {m.verdict}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
            <Card
              title="Revenue & EPS Trend"
              subtitle="Quarterly (Bn USD / $ per share)"
            >
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <ComposedChart data={revenueData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="quarter"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                    />
                    <YAxis
                      yAxisId="rev"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                    />
                    <YAxis
                      yAxisId="eps"
                      orientation="right"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                    />
                    <Tooltip contentStyle={ttStyle} />
                    <Bar
                      yAxisId="rev"
                      dataKey="revenue"
                      fill={CYAN}
                      opacity={0.4}
                      radius={[4, 4, 0, 0]}
                      name="Revenue ($B)"
                    />
                    <Line
                      yAxisId="eps"
                      type="monotone"
                      dataKey="earnings"
                      stroke={GOLD}
                      strokeWidth={2}
                      name="EPS ($)"
                    />
                    <Legend />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <Card title="Cash Flow Statement" subtitle="TTM in billions USD">
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Item", "Current (TTM)", "Previous", "Change"].map(
                      (h) => (
                        <th
                          key={h}
                          style={{
                            padding: "6px 10px",
                            textAlign: h === "Item" ? "left" : "right",
                            fontSize: 11,
                            color: "#94A3B8",
                            borderBottom: "1px solid rgba(51,65,85,0.3)",
                          }}
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {cashFlowData.map((c) => {
                    const chg = c.value - c.prev;
                    return (
                      <tr
                        key={c.item}
                        style={{
                          borderBottom: "1px solid rgba(51,65,85,0.15)",
                        }}
                      >
                        <td
                          style={{
                            padding: "6px 10px",
                            fontWeight: 600,
                            color: "#F1F5F9",
                          }}
                        >
                          {c.item}
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            textAlign: "right",
                            fontFamily: mono,
                            fontSize: 13,
                            color: c.value >= 0 ? GREEN : RED,
                          }}
                        >
                          ${c.value.toFixed(1)}B
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            textAlign: "right",
                            fontFamily: mono,
                            fontSize: 12,
                            color: "#94A3B8",
                          }}
                        >
                          ${c.prev.toFixed(1)}B
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            textAlign: "right",
                            fontFamily: mono,
                            fontSize: 12,
                            color: chg >= 0 ? GREEN : RED,
                          }}
                        >
                          {chg > 0 ? "+" : ""}
                          {chg.toFixed(1)}B
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ═══════════ Peer Comparison ═══════════ */}
      {tab === "Peer Comparison" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi("Top Score", "NVDA (94)", "highest composite", GOLD)}
            {kpi("Cheapest", "GOOGL (24.5x)", "lowest P/E", GREEN)}
            {kpi("Best Growth", "NVDA (+125%)", "revenue growth", CYAN)}
            {kpi("Best Margin", "NVDA (55.8%)", "net margin", PURPLE)}
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
              title="Quality Radar"
              subtitle="Multi-factor comparison (0-100)"
            >
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <RadarChart data={peerRadar}>
                    <PolarGrid stroke="rgba(51,65,85,0.3)" />
                    <PolarAngleAxis
                      dataKey="metric"
                      tick={{ fill: "#94A3B8", fontSize: 11 }}
                    />
                    <PolarRadiusAxis tick={{ fill: "#64748B", fontSize: 9 }} />
                    <Radar
                      name="AAPL"
                      dataKey="AAPL"
                      stroke={CYAN}
                      fill={CYAN}
                      fillOpacity={0.1}
                    />
                    <Radar
                      name="MSFT"
                      dataKey="MSFT"
                      stroke={GREEN}
                      fill={GREEN}
                      fillOpacity={0.1}
                    />
                    <Radar
                      name="NVDA"
                      dataKey="NVDA"
                      stroke={GOLD}
                      fill={GOLD}
                      fillOpacity={0.1}
                    />
                    <Radar
                      name="GOOGL"
                      dataKey="GOOGL"
                      stroke={PURPLE}
                      fill={PURPLE}
                      fillOpacity={0.1}
                    />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card
              title="Profitability vs Valuation"
              subtitle="Net Margin (%) vs P/E Ratio"
            >
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={peers}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="ticker"
                      tick={{ fill: "#F1F5F9", fontSize: 11 }}
                    />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip contentStyle={ttStyle} />
                    <Bar
                      dataKey="margin"
                      fill={GREEN}
                      name="Net Margin %"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="pe"
                      fill={CYAN}
                      name="P/E Ratio"
                      radius={[4, 4, 0, 0]}
                      opacity={0.5}
                    />
                    <Legend />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>

          <Card
            title="Peer Metrics Table"
            subtitle="Mega-cap technology comparison"
          >
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {[
                      "Ticker",
                      "P/E",
                      "P/S",
                      "ROE %",
                      "Margin %",
                      "Growth %",
                      "Beta",
                      "Div %",
                      "Mkt Cap",
                      "Score",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 8px",
                          textAlign: h === "Ticker" ? "left" : "center",
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
                  {peers.map((p) => (
                    <tr
                      key={p.ticker}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                    >
                      <td
                        style={{
                          padding: "6px 8px",
                          fontWeight: 700,
                          color: GOLD,
                          fontFamily: mono,
                        }}
                      >
                        {p.ticker}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                        }}
                      >
                        {p.pe.toFixed(1)}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                        }}
                      >
                        {p.ps.toFixed(1)}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          color: p.roe > 40 ? GREEN : "#F1F5F9",
                        }}
                      >
                        {p.roe.toFixed(1)}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          color: p.margin > 25 ? GREEN : "#F1F5F9",
                        }}
                      >
                        {p.margin.toFixed(1)}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          color: p.growth >= 0 ? GREEN : RED,
                        }}
                      >
                        {p.growth > 0 ? "+" : ""}
                        {p.growth.toFixed(1)}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          color: p.beta > 1.5 ? AMBER : "#F1F5F9",
                        }}
                      >
                        {p.beta.toFixed(2)}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                        }}
                      >
                        {p.div.toFixed(2)}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          color: "#94A3B8",
                        }}
                      >
                        {p.mcap}
                      </td>
                      <td style={{ padding: "6px 8px", textAlign: "center" }}>
                        <span
                          style={{
                            padding: "2px 10px",
                            borderRadius: 12,
                            fontFamily: mono,
                            fontSize: 12,
                            fontWeight: 700,
                            backgroundColor:
                              p.score >= 85
                                ? "rgba(16,185,129,0.15)"
                                : p.score >= 70
                                  ? "rgba(245,158,11,0.15)"
                                  : "rgba(239,68,68,0.15)",
                            color:
                              p.score >= 85
                                ? GREEN
                                : p.score >= 70
                                  ? AMBER
                                  : RED,
                          }}
                        >
                          {p.score}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ═══════════ Screener ═══════════ */}
      {tab === "Screener" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi(
              "Matches",
              `${screenerResults.length}`,
              "stocks passing filters",
              CYAN,
            )}
            {kpi(
              "Buy Signals",
              `${screenerResults.filter((s) => s.signal === "Buy").length}`,
              "strong conviction",
              GREEN,
            )}
            {kpi(
              "Sell Signals",
              `${screenerResults.filter((s) => s.signal === "Sell").length}`,
              "negative outlook",
              RED,
            )}
            {kpi(
              "Avg P/E",
              `${(screenerResults.reduce((a, s) => a + s.pe, 0) / screenerResults.length).toFixed(1)}`,
              "screened universe",
              GOLD,
            )}
          </div>

          <div
            style={{
              display: "flex",
              gap: 8,
              marginBottom: 16,
              alignItems: "center",
            }}
          >
            <span style={{ fontSize: 12, color: "#94A3B8" }}>Sector:</span>
            {["All", "Tech", "Finance", "Health", "Energy", "Staples"].map(
              (s) => (
                <button
                  key={s}
                  onClick={() => setScreenerSector(s)}
                  style={{
                    padding: "4px 12px",
                    borderRadius: 6,
                    fontSize: 12,
                    cursor: "pointer",
                    border: "none",
                    backgroundColor:
                      screenerSector === s ? CYAN : "rgba(30,41,59,0.5)",
                    color: screenerSector === s ? "#0A0E1A" : "#94A3B8",
                  }}
                >
                  {s}
                </button>
              ),
            )}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "3fr 1fr",
              gap: 16,
              marginBottom: 16,
            }}
          >
            <Card
              title="Screener Results"
              subtitle="Filtered & sortable stock screen"
            >
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr>
                      {th("Ticker", "ticker", "left")}
                      {th("Name", "name", "left")}
                      {th("Sector", "sector")}
                      {th("Price", "price")}
                      {th("P/E", "pe")}
                      {th("ROE %", "roe")}
                      {th("Growth %", "growth")}
                      {th("RSI", "rsi")}
                      {th("Signal", "signal")}
                    </tr>
                  </thead>
                  <tbody>
                    {sortedScreener.map((s) => (
                      <tr
                        key={s.ticker}
                        style={{
                          borderBottom: "1px solid rgba(51,65,85,0.15)",
                        }}
                      >
                        <td
                          style={{
                            padding: "6px 8px",
                            fontWeight: 700,
                            color: GOLD,
                            fontFamily: mono,
                          }}
                        >
                          {s.ticker}
                        </td>
                        <td
                          style={{
                            padding: "6px 8px",
                            fontSize: 12,
                            color: "#F1F5F9",
                          }}
                        >
                          {s.name}
                        </td>
                        <td
                          style={{
                            padding: "6px 8px",
                            textAlign: "center",
                            fontSize: 11,
                            color: "#94A3B8",
                          }}
                        >
                          {s.sector}
                        </td>
                        <td
                          style={{
                            padding: "6px 8px",
                            textAlign: "center",
                            fontFamily: mono,
                            fontSize: 12,
                          }}
                        >
                          ${s.price.toFixed(1)}
                        </td>
                        <td
                          style={{
                            padding: "6px 8px",
                            textAlign: "center",
                            fontFamily: mono,
                            fontSize: 12,
                          }}
                        >
                          {s.pe.toFixed(1)}
                        </td>
                        <td
                          style={{
                            padding: "6px 8px",
                            textAlign: "center",
                            fontFamily: mono,
                            fontSize: 12,
                            color: s.roe > 40 ? GREEN : "#F1F5F9",
                          }}
                        >
                          {s.roe.toFixed(1)}
                        </td>
                        <td
                          style={{
                            padding: "6px 8px",
                            textAlign: "center",
                            fontFamily: mono,
                            fontSize: 12,
                            color: s.growth >= 0 ? GREEN : RED,
                          }}
                        >
                          {s.growth > 0 ? "+" : ""}
                          {s.growth.toFixed(1)}
                        </td>
                        <td
                          style={{
                            padding: "6px 8px",
                            textAlign: "center",
                            fontFamily: mono,
                            fontSize: 12,
                            color:
                              s.rsi > 70 ? RED : s.rsi < 30 ? GREEN : AMBER,
                          }}
                        >
                          {s.rsi.toFixed(1)}
                        </td>
                        <td style={{ padding: "6px 8px", textAlign: "center" }}>
                          <span
                            style={{
                              padding: "2px 10px",
                              borderRadius: 12,
                              fontSize: 11,
                              fontWeight: 700,
                              backgroundColor:
                                s.signal === "Buy"
                                  ? "rgba(16,185,129,0.15)"
                                  : s.signal === "Sell"
                                    ? "rgba(239,68,68,0.15)"
                                    : "rgba(245,158,11,0.15)",
                              color:
                                s.signal === "Buy"
                                  ? GREEN
                                  : s.signal === "Sell"
                                    ? RED
                                    : AMBER,
                            }}
                          >
                            {s.signal}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
            <Card title="Sector Split" subtitle="Screened universe">
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={sectorDistribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={75}
                      paddingAngle={3}
                      dataKey="value"
                      label={({ name, value }) => `${name} (${value})`}
                    >
                      {sectorDistribution.map((s) => (
                        <Cell key={s.name} fill={s.color} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={ttStyle} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}

      {/* ═══════════ Quant Signals ═══════════ */}
      {tab === "Quant Signals" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi(
              "Active Signals",
              `${quantSignals.length}`,
              `${quantSignals.filter((s) => s.direction === "Long").length} long / ${quantSignals.filter((s) => s.direction === "Short").length} short`,
              CYAN,
            )}
            {kpi(
              "Avg Confidence",
              `${Math.round(quantSignals.reduce((a, s) => a + s.confidence, 0) / quantSignals.length)}%`,
              "across all signals",
              GOLD,
            )}
            {kpi("Best Strategy", "Momentum", "+8.2% YTD", GREEN)}
            {kpi("Win Rate", "68%", "last 90 days", PURPLE)}
          </div>

          <Card
            title="Active Trading Signals"
            subtitle="Algorithmic signal generation with entry/target/stop"
          >
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {[
                      "Ticker",
                      "Strategy",
                      "Direction",
                      "Confidence",
                      "Entry",
                      "Target",
                      "Stop",
                      "Timeframe",
                      "Open P&L",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 8px",
                          textAlign: h === "Strategy" ? "left" : "center",
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
                  {quantSignals.map((s) => (
                    <tr
                      key={s.ticker}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                    >
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontWeight: 700,
                          color: GOLD,
                          fontFamily: mono,
                        }}
                      >
                        {s.ticker}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          fontSize: 12,
                          color: "#F1F5F9",
                        }}
                      >
                        {s.strategy}
                      </td>
                      <td style={{ padding: "6px 8px", textAlign: "center" }}>
                        <span
                          style={{
                            padding: "2px 10px",
                            borderRadius: 12,
                            fontSize: 11,
                            fontWeight: 700,
                            backgroundColor:
                              s.direction === "Long"
                                ? "rgba(16,185,129,0.15)"
                                : "rgba(239,68,68,0.15)",
                            color: s.direction === "Long" ? GREEN : RED,
                          }}
                        >
                          {s.direction}
                        </span>
                      </td>
                      <td style={{ padding: "6px 8px", textAlign: "center" }}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 4,
                          }}
                        >
                          <div
                            style={{
                              width: 40,
                              height: 5,
                              borderRadius: 3,
                              backgroundColor: "rgba(51,65,85,0.3)",
                              overflow: "hidden",
                            }}
                          >
                            <div
                              style={{
                                width: `${s.confidence}%`,
                                height: "100%",
                                borderRadius: 3,
                                backgroundColor:
                                  s.confidence >= 80
                                    ? GREEN
                                    : s.confidence >= 65
                                      ? AMBER
                                      : RED,
                              }}
                            />
                          </div>
                          <span
                            style={{
                              fontFamily: mono,
                              fontSize: 11,
                              color:
                                s.confidence >= 80
                                  ? GREEN
                                  : s.confidence >= 65
                                    ? AMBER
                                    : RED,
                            }}
                          >
                            {s.confidence}%
                          </span>
                        </div>
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                        }}
                      >
                        ${s.entry.toFixed(1)}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          color: GREEN,
                        }}
                      >
                        ${s.target.toFixed(1)}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          color: RED,
                        }}
                      >
                        ${s.stop.toFixed(1)}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontSize: 11,
                          color: "#94A3B8",
                        }}
                      >
                        {s.timeframe}
                      </td>
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          fontWeight: 600,
                          color: s.pnl.startsWith("+") ? GREEN : RED,
                        }}
                      >
                        {s.pnl}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <div style={{ marginTop: 16 }}>
            <Card
              title="Strategy Performance (Monthly %)"
              subtitle="Backtested strategy returns"
            >
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <LineChart data={strategyPerf}>
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
                    <ReferenceLine y={0} stroke="rgba(100,116,139,0.3)" />
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
                      dataKey="meanRev"
                      stroke={GOLD}
                      strokeWidth={2}
                      dot={false}
                      name="Mean Reversion"
                    />
                    <Line
                      type="monotone"
                      dataKey="factor"
                      stroke={PURPLE}
                      strokeWidth={2}
                      dot={false}
                      name="Factor"
                    />
                    <Line
                      type="monotone"
                      dataKey="combined"
                      stroke={GREEN}
                      strokeWidth={2.5}
                      dot={false}
                      name="Combined"
                    />
                    <Legend />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
