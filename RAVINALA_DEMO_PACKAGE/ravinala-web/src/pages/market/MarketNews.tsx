import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
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
import { Badge, Card } from "../../components/ui";
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
  "Headlines",
  "Earnings Calendar",
  "Economic Calendar",
  "Sector Heatmap",
  "Sentiment",
] as const;
type Tab = (typeof TABS)[number];

/* ═══════════════════════════════════════════
   DATA
═══════════════════════════════════════════ */

const NEWS_DATA = [
  {
    id: 1,
    headline: "Fed Signals Pause on Rate Hikes Amid Cooling Inflation",
    source: "Reuters",
    time: "2 min ago",
    sentiment: "Bullish" as const,
    category: "Macro",
    impact: "High" as const,
  },
  {
    id: 2,
    headline: "NVIDIA Surpasses $4T Market Cap on AI Chip Demand Surge",
    source: "Bloomberg",
    time: "15 min ago",
    sentiment: "Bullish" as const,
    category: "Tech",
    impact: "High" as const,
  },
  {
    id: 3,
    headline: "Oil Prices Drop 3% as OPEC+ Increases Production Quotas",
    source: "Reuters",
    time: "28 min ago",
    sentiment: "Bearish" as const,
    category: "Commodities",
    impact: "Medium" as const,
  },
  {
    id: 4,
    headline: "ECB Holds Rates Steady, Warns of Persistent Core Inflation",
    source: "Bloomberg",
    time: "45 min ago",
    sentiment: "Neutral" as const,
    category: "Macro",
    impact: "High" as const,
  },
  {
    id: 5,
    headline: "Apple Announces $110B Stock Buyback, Largest in History",
    source: "CNBC",
    time: "1 hr ago",
    sentiment: "Bullish" as const,
    category: "Tech",
    impact: "High" as const,
  },
  {
    id: 6,
    headline: "China Manufacturing PMI Contracts for Third Straight Month",
    source: "Reuters",
    time: "1.5 hr ago",
    sentiment: "Bearish" as const,
    category: "Macro",
    impact: "Medium" as const,
  },
  {
    id: 7,
    headline: "Tesla Recalls 1.2M Vehicles Over Steering Software Issue",
    source: "CNBC",
    time: "2 hr ago",
    sentiment: "Bearish" as const,
    category: "Auto",
    impact: "Medium" as const,
  },
  {
    id: 8,
    headline: "Gold Hits Record $2,850/oz as Geopolitical Tensions Rise",
    source: "Bloomberg",
    time: "2.5 hr ago",
    sentiment: "Bullish" as const,
    category: "Commodities",
    impact: "High" as const,
  },
  {
    id: 9,
    headline: "US Jobs Report Beats Expectations: 275K Added in February",
    source: "Reuters",
    time: "3 hr ago",
    sentiment: "Bullish" as const,
    category: "Macro",
    impact: "High" as const,
  },
  {
    id: 10,
    headline: "Microsoft Cloud Revenue Growth Slows to 22% YoY",
    source: "Bloomberg",
    time: "3.5 hr ago",
    sentiment: "Neutral" as const,
    category: "Tech",
    impact: "Medium" as const,
  },
  {
    id: 11,
    headline: "Bank of Japan Hints at Further Rate Normalization in Q2",
    source: "Reuters",
    time: "4 hr ago",
    sentiment: "Neutral" as const,
    category: "Macro",
    impact: "High" as const,
  },
  {
    id: 12,
    headline: "Pfizer Cuts 2026 Revenue Guidance by $2B on Patent Cliff",
    source: "CNBC",
    time: "5 hr ago",
    sentiment: "Bearish" as const,
    category: "Healthcare",
    impact: "Medium" as const,
  },
  {
    id: 13,
    headline: "Bitcoin ETF Inflows Hit $1.2B in Single Day, New Record",
    source: "Bloomberg",
    time: "5.5 hr ago",
    sentiment: "Bullish" as const,
    category: "Crypto",
    impact: "Medium" as const,
  },
  {
    id: 14,
    headline: "EU Proposes New Carbon Border Tax Expansion to Services",
    source: "Reuters",
    time: "6 hr ago",
    sentiment: "Neutral" as const,
    category: "Regulation",
    impact: "Low" as const,
  },
  {
    id: 15,
    headline: "JPMorgan Warns of Commercial Real Estate Stress in Q3",
    source: "CNBC",
    time: "7 hr ago",
    sentiment: "Bearish" as const,
    category: "Financials",
    impact: "High" as const,
  },
  {
    id: 16,
    headline: "AMD Announces Next-Gen MI400 AI Accelerator at GTC",
    source: "Bloomberg",
    time: "8 hr ago",
    sentiment: "Bullish" as const,
    category: "Tech",
    impact: "Medium" as const,
  },
  {
    id: 17,
    headline: "Germany Factory Orders Surge 4.2% MoM, Beating Forecasts",
    source: "Reuters",
    time: "9 hr ago",
    sentiment: "Bullish" as const,
    category: "Macro",
    impact: "Medium" as const,
  },
  {
    id: 18,
    headline: "Stripe Confidentially Files S-1 for 2026 IPO",
    source: "CNBC",
    time: "10 hr ago",
    sentiment: "Bullish" as const,
    category: "Tech",
    impact: "Medium" as const,
  },
  {
    id: 19,
    headline: "India RBI Cuts Repo Rate by 25bps to 6.0%",
    source: "Reuters",
    time: "11 hr ago",
    sentiment: "Bullish" as const,
    category: "Macro",
    impact: "Medium" as const,
  },
  {
    id: 20,
    headline: "Rio Tinto Reports Q1 Iron Ore Shipments Down 6% YoY",
    source: "Bloomberg",
    time: "12 hr ago",
    sentiment: "Bearish" as const,
    category: "Commodities",
    impact: "Low" as const,
  },
];

const CATEGORIES = [
  "All",
  ...Array.from(new Set(NEWS_DATA.map((n) => n.category))),
];
const SENTIMENTS = ["All", "Bullish", "Bearish", "Neutral"];

/* ── earnings calendar ── */
const earningsCalendar = [
  {
    date: "Mar 24",
    ticker: "NVDA",
    company: "NVIDIA Corp",
    eps_est: 5.82,
    eps_prev: 5.16,
    revenue_est: "28.4B",
    time: "AMC",
    surprise_hist: [12.3, 8.7, 15.2, 6.4],
  },
  {
    date: "Mar 24",
    ticker: "MU",
    company: "Micron Technology",
    eps_est: 1.26,
    eps_prev: 0.87,
    revenue_est: "8.6B",
    time: "AMC",
    surprise_hist: [22.1, -5.3, 18.4, 9.8],
  },
  {
    date: "Mar 25",
    ticker: "GME",
    company: "GameStop",
    eps_est: -0.03,
    eps_prev: 0.01,
    revenue_est: "1.8B",
    time: "AMC",
    surprise_hist: [-45.2, 120.0, -12.5, 8.3],
  },
  {
    date: "Mar 25",
    ticker: "CHWY",
    company: "Chewy Inc",
    eps_est: 0.18,
    eps_prev: 0.14,
    revenue_est: "3.0B",
    time: "BMO",
    surprise_hist: [5.6, 12.8, -2.1, 7.9],
  },
  {
    date: "Mar 26",
    ticker: "LULU",
    company: "Lululemon",
    eps_est: 5.85,
    eps_prev: 5.29,
    revenue_est: "3.2B",
    time: "AMC",
    surprise_hist: [3.4, 6.1, 8.9, 2.3],
  },
  {
    date: "Mar 26",
    ticker: "PAYX",
    company: "Paychex",
    eps_est: 1.12,
    eps_prev: 1.08,
    revenue_est: "1.5B",
    time: "BMO",
    surprise_hist: [2.1, 1.8, 3.5, 4.2],
  },
  {
    date: "Mar 27",
    ticker: "WBA",
    company: "Walgreens Boots",
    eps_est: 0.68,
    eps_prev: 0.72,
    revenue_est: "37.1B",
    time: "BMO",
    surprise_hist: [-8.2, -12.5, 3.1, -5.6],
  },
  {
    date: "Mar 27",
    ticker: "BABA",
    company: "Alibaba Group",
    eps_est: 2.34,
    eps_prev: 2.21,
    revenue_est: "38.2B",
    time: "BMO",
    surprise_hist: [4.5, -2.8, 7.1, 11.3],
  },
  {
    date: "Mar 28",
    ticker: "NKE",
    company: "Nike Inc",
    eps_est: 0.52,
    eps_prev: 0.77,
    revenue_est: "11.6B",
    time: "AMC",
    surprise_hist: [-18.3, 2.1, -8.5, -4.2],
  },
  {
    date: "Mar 28",
    ticker: "FDX",
    company: "FedEx Corp",
    eps_est: 4.54,
    eps_prev: 3.86,
    revenue_est: "22.1B",
    time: "AMC",
    surprise_hist: [6.8, 12.4, -3.2, 8.9],
  },
];

/* ── economic calendar ── */
const economicCalendar = [
  {
    date: "Mar 24",
    time: "08:30",
    event: "Chicago Fed National Activity Index",
    country: "US",
    prev: "0.23",
    forecast: "0.18",
    importance: "Low" as const,
  },
  {
    date: "Mar 24",
    time: "09:45",
    event: "S&P Global US Manufacturing PMI",
    country: "US",
    prev: "52.2",
    forecast: "51.8",
    importance: "High" as const,
  },
  {
    date: "Mar 24",
    time: "09:45",
    event: "S&P Global US Services PMI",
    country: "US",
    prev: "51.0",
    forecast: "51.2",
    importance: "High" as const,
  },
  {
    date: "Mar 25",
    time: "09:00",
    event: "Case-Shiller Home Price Index",
    country: "US",
    prev: "4.5%",
    forecast: "4.2%",
    importance: "Medium" as const,
  },
  {
    date: "Mar 25",
    time: "10:00",
    event: "Consumer Confidence Index",
    country: "US",
    prev: "104.7",
    forecast: "103.8",
    importance: "High" as const,
  },
  {
    date: "Mar 25",
    time: "10:00",
    event: "New Home Sales",
    country: "US",
    prev: "657K",
    forecast: "680K",
    importance: "Medium" as const,
  },
  {
    date: "Mar 26",
    time: "08:30",
    event: "Durable Goods Orders",
    country: "US",
    prev: "-6.2%",
    forecast: "+1.5%",
    importance: "High" as const,
  },
  {
    date: "Mar 26",
    time: "10:30",
    event: "EIA Crude Oil Inventories",
    country: "US",
    prev: "-1.9M",
    forecast: "-0.5M",
    importance: "Medium" as const,
  },
  {
    date: "Mar 27",
    time: "08:30",
    event: "Advance GDP (Q4 Final)",
    country: "US",
    prev: "3.2%",
    forecast: "3.2%",
    importance: "High" as const,
  },
  {
    date: "Mar 27",
    time: "08:30",
    event: "Initial Jobless Claims",
    country: "US",
    prev: "215K",
    forecast: "220K",
    importance: "High" as const,
  },
  {
    date: "Mar 27",
    time: "10:00",
    event: "Pending Home Sales",
    country: "US",
    prev: "-5.0%",
    forecast: "+1.2%",
    importance: "Medium" as const,
  },
  {
    date: "Mar 28",
    time: "08:30",
    event: "PCE Price Index (Feb)",
    country: "US",
    prev: "2.5%",
    forecast: "2.5%",
    importance: "High" as const,
  },
  {
    date: "Mar 28",
    time: "08:30",
    event: "Personal Income (Feb)",
    country: "US",
    prev: "0.9%",
    forecast: "0.4%",
    importance: "Medium" as const,
  },
  {
    date: "Mar 28",
    time: "10:00",
    event: "U Michigan Consumer Sentiment (Final)",
    country: "US",
    prev: "64.7",
    forecast: "57.9",
    importance: "High" as const,
  },
  {
    date: "Mar 24",
    time: "03:15",
    event: "HCOB France Manufacturing PMI",
    country: "FR",
    prev: "45.8",
    forecast: "46.2",
    importance: "Medium" as const,
  },
  {
    date: "Mar 24",
    time: "03:30",
    event: "HCOB Germany Manufacturing PMI",
    country: "DE",
    prev: "46.5",
    forecast: "47.0",
    importance: "High" as const,
  },
  {
    date: "Mar 25",
    time: "04:00",
    event: "IFO Business Climate (Germany)",
    country: "DE",
    prev: "85.2",
    forecast: "86.0",
    importance: "High" as const,
  },
  {
    date: "Mar 27",
    time: "07:00",
    event: "ECB Economic Bulletin",
    country: "EU",
    prev: "—",
    forecast: "—",
    importance: "Medium" as const,
  },
];

/* ── sector heatmap ── */
const sectorPerformance = [
  {
    sector: "Technology",
    d1: 1.42,
    w1: 3.21,
    m1: 5.87,
    m3: 12.4,
    ytd: 8.9,
    y1: 28.3,
    mcap: "14.2T",
  },
  {
    sector: "Healthcare",
    d1: -0.38,
    w1: 0.82,
    m1: -1.24,
    m3: 2.1,
    ytd: 1.8,
    y1: 8.5,
    mcap: "7.1T",
  },
  {
    sector: "Financials",
    d1: 0.72,
    w1: 1.54,
    m1: 3.18,
    m3: 8.2,
    ytd: 6.4,
    y1: 22.1,
    mcap: "5.8T",
  },
  {
    sector: "Consumer Disc.",
    d1: 0.21,
    w1: -0.45,
    m1: 1.92,
    m3: 5.8,
    ytd: 4.2,
    y1: 15.7,
    mcap: "4.9T",
  },
  {
    sector: "Industrials",
    d1: -0.15,
    w1: 0.62,
    m1: 2.45,
    m3: 6.1,
    ytd: 5.1,
    y1: 18.3,
    mcap: "4.2T",
  },
  {
    sector: "Energy",
    d1: -1.82,
    w1: -3.14,
    m1: -5.21,
    m3: -2.4,
    ytd: -4.8,
    y1: -8.2,
    mcap: "3.1T",
  },
  {
    sector: "Consumer Staples",
    d1: 0.12,
    w1: 0.38,
    m1: 0.95,
    m3: 2.8,
    ytd: 2.1,
    y1: 6.4,
    mcap: "3.4T",
  },
  {
    sector: "Comm. Services",
    d1: 0.95,
    w1: 2.18,
    m1: 4.52,
    m3: 10.5,
    ytd: 7.8,
    y1: 24.6,
    mcap: "4.5T",
  },
  {
    sector: "Utilities",
    d1: 0.08,
    w1: -0.22,
    m1: 1.12,
    m3: 4.2,
    ytd: 3.5,
    y1: 12.8,
    mcap: "1.5T",
  },
  {
    sector: "Real Estate",
    d1: -0.55,
    w1: -1.82,
    m1: -2.85,
    m3: -1.2,
    ytd: -2.4,
    y1: 2.1,
    mcap: "1.2T",
  },
  {
    sector: "Materials",
    d1: -0.28,
    w1: 0.15,
    m1: 1.38,
    m3: 3.5,
    ytd: 2.8,
    y1: 9.2,
    mcap: "1.8T",
  },
];

/* ── sentiment data ── */
const sentimentTimeline = Array.from({ length: 30 }, (_, i) => ({
  day: `Mar ${i + 1}`,
  bullish: 35 + Math.round(Math.sin(i * 0.3) * 12 + Math.random() * 5),
  bearish: 28 + Math.round(Math.cos(i * 0.25) * 10 + Math.random() * 4),
  neutral: 30 + Math.round(Math.sin(i * 0.2) * 6),
}));

const newsSentByCategory = [
  { category: "Tech", bullish: 62, bearish: 18, neutral: 20 },
  { category: "Macro", bullish: 38, bearish: 32, neutral: 30 },
  { category: "Commodities", bullish: 28, bearish: 45, neutral: 27 },
  { category: "Financials", bullish: 42, bearish: 35, neutral: 23 },
  { category: "Healthcare", bullish: 30, bearish: 38, neutral: 32 },
  { category: "Crypto", bullish: 58, bearish: 22, neutral: 20 },
];

const sourceBreakdown = [
  { name: "Reuters", value: 32, color: "#FF8C00" },
  { name: "Bloomberg", value: 28, color: "#FF6600" },
  { name: "CNBC", value: 18, color: "#0A7CFF" },
  { name: "WSJ", value: 12, color: "#94A3B8" },
  { name: "FT", value: 10, color: GOLD },
];

/* ═══════════════════════════════════════════
   HELPERS
═══════════════════════════════════════════ */
const sourceColor: Record<string, string> = {
  Reuters: "#FF8C00",
  Bloomberg: "#FF6600",
  CNBC: "#0A7CFF",
};
const impColor = (i: string) =>
  i === "High" ? RED : i === "Medium" ? AMBER : "#64748B";

function heatColor(v: number): string {
  if (v > 3) return "rgba(16,185,129,0.6)";
  if (v > 1) return "rgba(16,185,129,0.3)";
  if (v > 0) return "rgba(16,185,129,0.12)";
  if (v > -1) return "rgba(239,68,68,0.12)";
  if (v > -3) return "rgba(239,68,68,0.3)";
  return "rgba(239,68,68,0.6)";
}

/* ═══════════════════════════════════════════
   COMPONENT
═══════════════════════════════════════════ */
export default function MarketNews() {
  const { data: snapshotData } = useSnapshot();
  const usingFallback = !snapshotData;
  const [tab, setTab] = useState<Tab>("Headlines");
  const [search, setSearch] = useState("");
  const [catFilter, setCatFilter] = useState("All");
  const [sentFilter, setSentFilter] = useState("All");
  const [impFilter, setImpFilter] = useState("All");

  const filtered = useMemo(() => {
    return NEWS_DATA.filter((n) => {
      const matchSearch =
        n.headline.toLowerCase().includes(search.toLowerCase()) ||
        n.source.toLowerCase().includes(search.toLowerCase());
      const matchCat = catFilter === "All" || n.category === catFilter;
      const matchSent = sentFilter === "All" || n.sentiment === sentFilter;
      return matchSearch && matchCat && matchSent;
    });
  }, [search, catFilter, sentFilter]);

  const filteredEcon = useMemo(() => {
    if (impFilter === "All") return economicCalendar;
    return economicCalendar.filter((e) => e.importance === impFilter);
  }, [impFilter]);

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
        Market News & Calendar
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        Real-time news, earnings & economic events, sector heatmap
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

      {/* tabs */}
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

      {/* ═══════════ Headlines ═══════════ */}
      {tab === "Headlines" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi("Breaking", "3", "high-impact stories", RED)}
            {kpi(
              "Bullish",
              `${NEWS_DATA.filter((n) => n.sentiment === "Bullish").length}`,
              "positive articles",
              GREEN,
            )}
            {kpi(
              "Bearish",
              `${NEWS_DATA.filter((n) => n.sentiment === "Bearish").length}`,
              "negative articles",
              RED,
            )}
            {kpi("Sources", "4", "wire services", CYAN)}
          </div>

          <div
            style={{
              display: "flex",
              gap: 12,
              marginBottom: 16,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <input
              type="text"
              placeholder="Search headlines..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                backgroundColor: "#131823",
                border: "1px solid rgba(51,65,85,0.5)",
                borderRadius: 8,
                padding: "8px 14px",
                color: "#F1F5F9",
                fontSize: 13,
                flex: "1 1 200px",
                minWidth: 200,
                outline: "none",
              }}
            />
            <select
              value={catFilter}
              onChange={(e) => setCatFilter(e.target.value)}
              style={{
                backgroundColor: "#131823",
                border: "1px solid rgba(51,65,85,0.5)",
                borderRadius: 8,
                padding: "8px 12px",
                color: "#F1F5F9",
                fontSize: 12,
              }}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c === "All" ? "All Categories" : c}
                </option>
              ))}
            </select>
            <select
              value={sentFilter}
              onChange={(e) => setSentFilter(e.target.value)}
              style={{
                backgroundColor: "#131823",
                border: "1px solid rgba(51,65,85,0.5)",
                borderRadius: 8,
                padding: "8px 12px",
                color: "#F1F5F9",
                fontSize: 12,
              }}
            >
              {SENTIMENTS.map((s) => (
                <option key={s} value={s}>
                  {s === "All" ? "All Sentiments" : s}
                </option>
              ))}
            </select>
          </div>

          <p style={{ color: "#94A3B8", fontSize: 12, marginBottom: 10 }}>
            {filtered.length} articles
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {filtered.map((n) => (
              <Card key={n.id}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    gap: 12,
                  }}
                >
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginBottom: 6,
                      }}
                    >
                      <span
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          padding: "2px 6px",
                          borderRadius: 4,
                          backgroundColor:
                            n.impact === "High"
                              ? "rgba(239,68,68,0.15)"
                              : n.impact === "Medium"
                                ? "rgba(245,158,11,0.15)"
                                : "rgba(100,116,139,0.15)",
                          color: impColor(n.impact),
                        }}
                      >
                        {n.impact}
                      </span>
                      <span
                        style={{
                          fontSize: 11,
                          color: "#00D9FF",
                          backgroundColor: "rgba(0,217,255,0.1)",
                          padding: "2px 8px",
                          borderRadius: 4,
                        }}
                      >
                        {n.category}
                      </span>
                    </div>
                    <p
                      style={{
                        color: "#F1F5F9",
                        fontSize: 14,
                        fontWeight: 600,
                        lineHeight: 1.4,
                        marginBottom: 6,
                      }}
                    >
                      {n.headline}
                    </p>
                    <div
                      style={{ display: "flex", gap: 10, alignItems: "center" }}
                    >
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: 600,
                          color: sourceColor[n.source] || "#94A3B8",
                        }}
                      >
                        {n.source}
                      </span>
                      <span style={{ fontSize: 12, color: "#64748B" }}>
                        {n.time}
                      </span>
                    </div>
                  </div>
                  <Badge
                    variant={
                      n.sentiment === "Bullish"
                        ? "up"
                        : n.sentiment === "Bearish"
                          ? "down"
                          : "neutral"
                    }
                  >
                    {n.sentiment}
                  </Badge>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* ═══════════ Earnings Calendar ═══════════ */}
      {tab === "Earnings Calendar" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi("This Week", "10", "reporting companies", CYAN)}
            {kpi("EPS Beats (avg)", "+8.2%", "last quarter avg", GREEN)}
            {kpi("Revenue Beats", "72%", "of S&P 500", GOLD)}
            {kpi("Guidance Raised", "35%", "of reporters", PURPLE)}
          </div>
          <Card title="Upcoming Earnings" subtitle="Next 5 trading days">
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {[
                      "Date",
                      "Ticker",
                      "Company",
                      "EPS Est.",
                      "EPS Prev.",
                      "Rev. Est.",
                      "Time",
                      "Surprise Hist (4Q)",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 10px",
                          textAlign: h === "Company" ? "left" : "center",
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
                  {earningsCalendar.map((e) => (
                    <tr
                      key={e.ticker}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                    >
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontSize: 12,
                          color: "#94A3B8",
                        }}
                      >
                        {e.date}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontWeight: 700,
                          color: GOLD,
                          fontFamily: mono,
                        }}
                      >
                        {e.ticker}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          fontSize: 13,
                          color: "#F1F5F9",
                        }}
                      >
                        {e.company}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                        }}
                      >
                        ${e.eps_est.toFixed(2)}
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
                        ${e.eps_prev.toFixed(2)}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                        }}
                      >
                        {e.revenue_est}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontSize: 11,
                        }}
                      >
                        <span
                          style={{
                            padding: "2px 8px",
                            borderRadius: 4,
                            backgroundColor:
                              e.time === "AMC"
                                ? "rgba(168,85,247,0.15)"
                                : "rgba(0,217,255,0.15)",
                            color: e.time === "AMC" ? PURPLE : CYAN,
                          }}
                        >
                          {e.time}
                        </span>
                      </td>
                      <td style={{ padding: "6px 10px" }}>
                        <div
                          style={{
                            display: "flex",
                            gap: 3,
                            justifyContent: "center",
                          }}
                        >
                          {e.surprise_hist.map((s, i) => (
                            <div
                              key={i}
                              style={{
                                width: 28,
                                height: 18,
                                borderRadius: 3,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontSize: 9,
                                fontFamily: mono,
                                fontWeight: 600,
                                backgroundColor:
                                  s >= 0
                                    ? "rgba(16,185,129,0.15)"
                                    : "rgba(239,68,68,0.15)",
                                color: s >= 0 ? GREEN : RED,
                              }}
                            >
                              {s > 0 ? "+" : ""}
                              {s.toFixed(0)}
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {/* ═══════════ Economic Calendar ═══════════ */}
      {tab === "Economic Calendar" && (
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
              "Events This Week",
              `${economicCalendar.length}`,
              "scheduled releases",
              CYAN,
            )}
            {kpi(
              "High Impact",
              `${economicCalendar.filter((e) => e.importance === "High").length}`,
              "market-moving events",
              RED,
            )}
            {kpi("Key Release", "PCE (Fri)", "Fed preferred gauge", GOLD)}
            {kpi("Next FOMC", "May 7", "35 days away", PURPLE)}
          </div>

          <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
            {["All", "High", "Medium", "Low"].map((f) => (
              <button
                key={f}
                onClick={() => setImpFilter(f)}
                style={{
                  padding: "5px 14px",
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                  border: "none",
                  backgroundColor:
                    impFilter === f
                      ? f === "High"
                        ? RED
                        : f === "Medium"
                          ? AMBER
                          : f === "Low"
                            ? "#64748B"
                            : CYAN
                      : "rgba(30,41,59,0.5)",
                  color: impFilter === f ? "#0A0E1A" : "#94A3B8",
                }}
              >
                {f === "All" ? "All Importance" : f}
              </button>
            ))}
          </div>

          <Card
            title="Economic Events"
            subtitle="US & Europe releases this week"
          >
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {[
                      "Date",
                      "Time (ET)",
                      "Event",
                      "Country",
                      "Previous",
                      "Forecast",
                      "Importance",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 10px",
                          textAlign: h === "Event" ? "left" : "center",
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
                  {filteredEcon.map((e, i) => (
                    <tr
                      key={i}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                    >
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontSize: 12,
                          color: "#94A3B8",
                        }}
                      >
                        {e.date}
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
                        {e.time}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          fontSize: 13,
                          color: "#F1F5F9",
                          fontWeight: e.importance === "High" ? 600 : 400,
                        }}
                      >
                        {e.event}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontSize: 12,
                        }}
                      >
                        {e.country}
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
                        {e.prev}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          color: CYAN,
                        }}
                      >
                        {e.forecast}
                      </td>
                      <td style={{ padding: "6px 10px", textAlign: "center" }}>
                        <span
                          style={{
                            padding: "2px 10px",
                            borderRadius: 12,
                            fontSize: 10,
                            fontWeight: 700,
                            backgroundColor:
                              e.importance === "High"
                                ? "rgba(239,68,68,0.15)"
                                : e.importance === "Medium"
                                  ? "rgba(245,158,11,0.15)"
                                  : "rgba(100,116,139,0.15)",
                            color: impColor(e.importance),
                          }}
                        >
                          {e.importance}
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

      {/* ═══════════ Sector Heatmap ═══════════ */}
      {tab === "Sector Heatmap" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi("Best Sector", "Technology", "+1.42% today", GREEN)}
            {kpi("Worst Sector", "Energy", "-1.82% today", RED)}
            {kpi("Avg S&P 500", "+0.12%", "11 GICS sectors", CYAN)}
            {kpi("Sectors Green", "6 / 11", "positive today", GOLD)}
          </div>
          <Card
            title="GICS Sector Returns Heatmap"
            subtitle="Performance across multiple time horizons"
          >
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "separate",
                  borderSpacing: 2,
                }}
              >
                <thead>
                  <tr>
                    {[
                      "Sector",
                      "1D",
                      "1W",
                      "1M",
                      "3M",
                      "YTD",
                      "1Y",
                      "Mkt Cap",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 8px",
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
                  {sectorPerformance.map((s) => (
                    <tr key={s.sector}>
                      <td
                        style={{
                          padding: "6px 8px",
                          fontWeight: 600,
                          fontSize: 13,
                          color: "#F1F5F9",
                        }}
                      >
                        {s.sector}
                      </td>
                      {[s.d1, s.w1, s.m1, s.m3, s.ytd, s.y1].map((v, i) => (
                        <td
                          key={i}
                          style={{
                            padding: "4px 6px",
                            textAlign: "center",
                            borderRadius: 4,
                            backgroundColor: heatColor(v),
                          }}
                        >
                          <span
                            style={{
                              fontFamily: mono,
                              fontSize: 12,
                              fontWeight: 600,
                              color: v >= 0 ? GREEN : RED,
                            }}
                          >
                            {v > 0 ? "+" : ""}
                            {v.toFixed(2)}%
                          </span>
                        </td>
                      ))}
                      <td
                        style={{
                          padding: "6px 8px",
                          textAlign: "center",
                          fontFamily: mono,
                          fontSize: 12,
                          color: "#94A3B8",
                        }}
                      >
                        {s.mcap}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
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
            <Card
              title="Sector YTD Performance"
              subtitle="Year-to-date returns ranked"
            >
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <BarChart
                    data={[...sectorPerformance].sort((a, b) => b.ytd - a.ytd)}
                    layout="vertical"
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      type="number"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                    />
                    <YAxis
                      type="category"
                      dataKey="sector"
                      width={100}
                      tick={{ fill: "#F1F5F9", fontSize: 10 }}
                    />
                    <Tooltip contentStyle={ttStyle} />
                    <Bar dataKey="ytd" radius={[0, 4, 4, 0]} name="YTD %">
                      {[...sectorPerformance]
                        .sort((a, b) => b.ytd - a.ytd)
                        .map((s, i) => (
                          <Cell key={i} fill={s.ytd >= 0 ? GREEN : RED} />
                        ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card
              title="Sector Rotation"
              subtitle="1-month vs 3-month performance"
            >
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={sectorPerformance}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="sector"
                      tick={{ fill: "#64748B", fontSize: 9 }}
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip contentStyle={ttStyle} />
                    <Bar
                      dataKey="m1"
                      fill={CYAN}
                      name="1M %"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="m3"
                      fill={GOLD}
                      name="3M %"
                      radius={[4, 4, 0, 0]}
                    />
                    <Legend />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}

      {/* ═══════════ Sentiment ═══════════ */}
      {tab === "Sentiment" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4,1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            {kpi("Avg Sentiment", "+0.24", "across all sources", GREEN)}
            {kpi("Most Bullish", "Tech", "62% positive", CYAN)}
            {kpi("Most Bearish", "Commodities", "45% negative", RED)}
            {kpi("Articles Today", "148", "12 sources scanned", GOLD)}
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
              title="Sentiment Timeline"
              subtitle="30-day bullish/bearish/neutral breakdown"
            >
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <AreaChart data={sentimentTimeline}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="day"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                      interval={4}
                    />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip contentStyle={ttStyle} />
                    <Area
                      type="monotone"
                      dataKey="bullish"
                      stackId="1"
                      stroke={GREEN}
                      fill={GREEN}
                      fillOpacity={0.3}
                      name="Bullish %"
                    />
                    <Area
                      type="monotone"
                      dataKey="neutral"
                      stackId="1"
                      stroke="#94A3B8"
                      fill="#94A3B8"
                      fillOpacity={0.15}
                      name="Neutral %"
                    />
                    <Area
                      type="monotone"
                      dataKey="bearish"
                      stackId="1"
                      stroke={RED}
                      fill={RED}
                      fillOpacity={0.25}
                      name="Bearish %"
                    />
                    <Legend />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card
              title="Source Distribution"
              subtitle="News coverage by wire service"
            >
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={sourceBreakdown}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={90}
                      paddingAngle={3}
                      dataKey="value"
                      label={({ name, value }) => `${name} ${value}%`}
                    >
                      {sourceBreakdown.map((s) => (
                        <Cell key={s.name} fill={s.color} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={ttStyle} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
          <Card
            title="Sentiment by Sector"
            subtitle="Bullish vs bearish tone in news coverage"
          >
            <div style={{ width: "100%", height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={newsSentByCategory}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="category"
                    tick={{ fill: "#64748B", fontSize: 11 }}
                  />
                  <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                  <Tooltip contentStyle={ttStyle} />
                  <Bar
                    dataKey="bullish"
                    fill={GREEN}
                    name="Bullish %"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="neutral"
                    fill="#94A3B8"
                    name="Neutral %"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="bearish"
                    fill={RED}
                    name="Bearish %"
                    radius={[4, 4, 0, 0]}
                  />
                  <Legend />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
