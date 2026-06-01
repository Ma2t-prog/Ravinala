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
import { Badge, Card, StatCard } from "../../components/ui/index";
import { Tabs } from "../../components/ui/Tabs";
import { useIndices } from "../../hooks/useMarketData";

// ── Equity Research: Multi-stock data ────────────────────────────────────────

interface StockData {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  changePct: number;
  open: number;
  high: number;
  low: number;
  volume: string;
  marketCap: string;
  pe: number;
  eps: number;
  dividend: number;
  week52High: number;
  week52Low: number;
  analystRatings: { name: string; value: number; color: string }[];
  consensus: string;
  targetPrice: { low: number; median: number; high: number };
  quarterlyData: { quarter: string; revenue: number; eps: number }[];
  newsItems: { headline: string; sentiment: string; date: string }[];
  financials: { label: string; value: string }[];
}

const STOCKS: Record<string, StockData> = {
  AAPL: {
    ticker: "AAPL",
    name: "Apple Inc.",
    sector: "Technology",
    price: 178.72,
    change: +2.34,
    changePct: +1.33,
    open: 176.15,
    high: 179.63,
    low: 175.82,
    volume: "58.3M",
    marketCap: "2.78T",
    pe: 28.4,
    eps: 6.29,
    dividend: 0.96,
    week52High: 199.62,
    week52Low: 143.9,
    analystRatings: [
      { name: "Buy", value: 28, color: "#10B981" },
      { name: "Hold", value: 11, color: "#F59E0B" },
      { name: "Sell", value: 3, color: "#EF4444" },
    ],
    consensus: "Buy",
    targetPrice: { low: 155, median: 195, high: 225 },
    quarterlyData: [
      { quarter: "Q1 25", revenue: 94.8, eps: 1.52 },
      { quarter: "Q2 25", revenue: 85.8, eps: 1.4 },
      { quarter: "Q3 25", revenue: 89.5, eps: 1.46 },
      { quarter: "Q4 25", revenue: 119.6, eps: 2.18 },
    ],
    newsItems: [
      {
        headline: "Apple Vision Pro 2 entering mass production",
        sentiment: "positive",
        date: "Mar 22",
      },
      {
        headline: "AAPL upgraded to Outperform at Bernstein on AI catalyst",
        sentiment: "positive",
        date: "Mar 21",
      },
      {
        headline: "iPhone 17 supply chain shows strong component orders",
        sentiment: "positive",
        date: "Mar 20",
      },
      {
        headline: "EU antitrust probe may impose App Store restrictions",
        sentiment: "negative",
        date: "Mar 19",
      },
      {
        headline: "Apple Services revenue crosses $100B annual run-rate",
        sentiment: "positive",
        date: "Mar 18",
      },
    ],
    financials: [
      { label: "Revenue (TTM)", value: "$389.5B" },
      { label: "Gross Margin", value: "44.1%" },
      { label: "Operating Margin", value: "29.8%" },
      { label: "Net Income", value: "$97.0B" },
      { label: "Free Cash Flow", value: "$104.5B" },
      { label: "ROE", value: "147.9%" },
    ],
  },
  MSFT: {
    ticker: "MSFT",
    name: "Microsoft Corp.",
    sector: "Technology",
    price: 415.5,
    change: +3.2,
    changePct: +0.78,
    open: 412.3,
    high: 418.1,
    low: 411.85,
    volume: "21.4M",
    marketCap: "3.09T",
    pe: 35.2,
    eps: 11.8,
    dividend: 3.0,
    week52High: 430.82,
    week52Low: 309.98,
    analystRatings: [
      { name: "Buy", value: 45, color: "#10B981" },
      { name: "Hold", value: 8, color: "#F59E0B" },
      { name: "Sell", value: 1, color: "#EF4444" },
    ],
    consensus: "Strong Buy",
    targetPrice: { low: 370, median: 450, high: 500 },
    quarterlyData: [
      { quarter: "Q1 25", revenue: 61.9, eps: 2.94 },
      { quarter: "Q2 25", revenue: 65.6, eps: 3.23 },
      { quarter: "Q3 25", revenue: 64.7, eps: 3.1 },
      { quarter: "Q4 25", revenue: 69.1, eps: 3.3 },
    ],
    newsItems: [
      {
        headline: "Azure AI growth accelerates to 33% YoY in Q4",
        sentiment: "positive",
        date: "Mar 22",
      },
      {
        headline: "Microsoft Copilot 365 seats surpass 1M enterprise users",
        sentiment: "positive",
        date: "Mar 21",
      },
      {
        headline:
          "OpenAI partnership extended through 2030 with expanded GPU allocation",
        sentiment: "positive",
        date: "Mar 20",
      },
      {
        headline: "Activision integration costs weigh on near-term margins",
        sentiment: "negative",
        date: "Mar 19",
      },
      {
        headline: "MSFT announces $60B buyback, dividend increase of 10%",
        sentiment: "positive",
        date: "Mar 18",
      },
    ],
    financials: [
      { label: "Revenue (TTM)", value: "$261.3B" },
      { label: "Gross Margin", value: "69.4%" },
      { label: "Operating Margin", value: "43.1%" },
      { label: "Net Income", value: "$88.1B" },
      { label: "Free Cash Flow", value: "$74.1B" },
      { label: "ROE", value: "36.7%" },
    ],
  },
  GOOGL: {
    ticker: "GOOGL",
    name: "Alphabet Inc.",
    sector: "Communication Services",
    price: 175.05,
    change: -1.2,
    changePct: -0.68,
    open: 176.25,
    high: 177.4,
    low: 174.1,
    volume: "24.8M",
    marketCap: "2.19T",
    pe: 26.1,
    eps: 6.71,
    dividend: 0.0,
    week52High: 193.31,
    week52Low: 130.67,
    analystRatings: [
      { name: "Buy", value: 38, color: "#10B981" },
      { name: "Hold", value: 9, color: "#F59E0B" },
      { name: "Sell", value: 2, color: "#EF4444" },
    ],
    consensus: "Buy",
    targetPrice: { low: 155, median: 200, high: 230 },
    quarterlyData: [
      { quarter: "Q1 25", revenue: 80.5, eps: 1.89 },
      { quarter: "Q2 25", revenue: 84.7, eps: 1.95 },
      { quarter: "Q3 25", revenue: 88.3, eps: 2.12 },
      { quarter: "Q4 25", revenue: 96.5, eps: 2.15 },
    ],
    newsItems: [
      {
        headline: "Google Cloud revenue hits $12B quarterly milestone",
        sentiment: "positive",
        date: "Mar 22",
      },
      {
        headline: "Gemini Ultra integration driving Search engagement gains",
        sentiment: "positive",
        date: "Mar 21",
      },
      {
        headline: "DOJ antitrust remedies decision expected Q3 2025",
        sentiment: "negative",
        date: "Mar 20",
      },
      {
        headline: "YouTube Shorts monetization surpasses TikTok CPM rates",
        sentiment: "positive",
        date: "Mar 19",
      },
      {
        headline: "Waymo robotaxi expansion accelerating to 25 cities",
        sentiment: "positive",
        date: "Mar 18",
      },
    ],
    financials: [
      { label: "Revenue (TTM)", value: "$350.0B" },
      { label: "Gross Margin", value: "56.9%" },
      { label: "Operating Margin", value: "27.9%" },
      { label: "Net Income", value: "$73.8B" },
      { label: "Free Cash Flow", value: "$52.5B" },
      { label: "ROE", value: "31.5%" },
    ],
  },
  NVDA: {
    ticker: "NVDA",
    name: "NVIDIA Corp.",
    sector: "Semiconductors",
    price: 875.4,
    change: +22.1,
    changePct: +2.59,
    open: 853.3,
    high: 882.6,
    low: 850.1,
    volume: "42.1M",
    marketCap: "2.15T",
    pe: 67.3,
    eps: 13.01,
    dividend: 0.16,
    week52High: 974.0,
    week52Low: 373.62,
    analystRatings: [
      { name: "Buy", value: 52, color: "#10B981" },
      { name: "Hold", value: 5, color: "#F59E0B" },
      { name: "Sell", value: 1, color: "#EF4444" },
    ],
    consensus: "Strong Buy",
    targetPrice: { low: 700, median: 1000, high: 1200 },
    quarterlyData: [
      { quarter: "Q1 25", revenue: 26.0, eps: 5.98 },
      { quarter: "Q2 25", revenue: 30.0, eps: 6.8 },
      { quarter: "Q3 25", revenue: 35.1, eps: 8.1 },
      { quarter: "Q4 25", revenue: 39.3, eps: 9.2 },
    ],
    newsItems: [
      {
        headline: "Blackwell GPU demand exceeding supply by 3x into 2025",
        sentiment: "positive",
        date: "Mar 22",
      },
      {
        headline:
          "NVDA announces NIM microservices for enterprise AI deployment",
        sentiment: "positive",
        date: "Mar 21",
      },
      {
        headline: "US export controls to China may limit H20 chip sales",
        sentiment: "negative",
        date: "Mar 20",
      },
      {
        headline: "Sovereign AI deals with UAE and Saudi Arabia totaling $10B",
        sentiment: "positive",
        date: "Mar 19",
      },
      {
        headline: "CUDA ecosystem now has 4M developers globally",
        sentiment: "positive",
        date: "Mar 18",
      },
    ],
    financials: [
      { label: "Revenue (TTM)", value: "$130.4B" },
      { label: "Gross Margin", value: "74.6%" },
      { label: "Operating Margin", value: "54.1%" },
      { label: "Net Income", value: "$55.2B" },
      { label: "Free Cash Flow", value: "$43.1B" },
      { label: "ROE", value: "123.1%" },
    ],
  },
  TSLA: {
    ticker: "TSLA",
    name: "Tesla Inc.",
    sector: "EV & Clean Energy",
    price: 172.63,
    change: -4.55,
    changePct: -2.57,
    open: 177.18,
    high: 178.4,
    low: 171.9,
    volume: "108.7M",
    marketCap: "551.0B",
    pe: 52.8,
    eps: 3.27,
    dividend: 0.0,
    week52High: 299.29,
    week52Low: 138.8,
    analystRatings: [
      { name: "Buy", value: 14, color: "#10B981" },
      { name: "Hold", value: 18, color: "#F59E0B" },
      { name: "Sell", value: 12, color: "#EF4444" },
    ],
    consensus: "Hold",
    targetPrice: { low: 85, median: 185, high: 310 },
    quarterlyData: [
      { quarter: "Q1 25", revenue: 21.3, eps: 0.45 },
      { quarter: "Q2 25", revenue: 22.5, eps: 0.62 },
      { quarter: "Q3 25", revenue: 25.2, eps: 0.72 },
      { quarter: "Q4 25", revenue: 25.7, eps: 0.73 },
    ],
    newsItems: [
      {
        headline: "Robotaxi launch in Austin confirmed for June 2025",
        sentiment: "positive",
        date: "Mar 22",
      },
      {
        headline: "Q1 deliveries miss estimates by 8% amid Model Y transition",
        sentiment: "negative",
        date: "Mar 21",
      },
      {
        headline: "Optimus robot production target raised to 1M units in 2026",
        sentiment: "positive",
        date: "Mar 20",
      },
      {
        headline: "European sales -49% YoY in February on brand headwinds",
        sentiment: "negative",
        date: "Mar 19",
      },
      {
        headline:
          "Full Self-Driving v13 achieves record safety intervention rate",
        sentiment: "positive",
        date: "Mar 18",
      },
    ],
    financials: [
      { label: "Revenue (TTM)", value: "$94.7B" },
      { label: "Gross Margin", value: "17.4%" },
      { label: "Operating Margin", value: "6.7%" },
      { label: "Net Income", value: "$7.1B" },
      { label: "Free Cash Flow", value: "$2.9B" },
      { label: "ROE", value: "12.3%" },
    ],
  },
};

const TICKERS = Object.keys(STOCKS) as (keyof typeof STOCKS)[];

const eq_fmt = (n: number) =>
  n.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

const sentimentColor: Record<string, string> = {
  positive: "#10B981",
  negative: "#EF4444",
  neutral: "#94A3B8",
};

// ── Company Analyzer types & data ─────────────────────────────────────────────

interface CompanyData {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  exchange: string;
  description: string;
  price: number;
  marketCap: string;
  pe: number;
  forwardPe: number;
  pb: number;
  ps: number;
  dividendYield: number;
  beta: number;
  high52w: number;
  low52w: number;
  revenue: string;
  netIncome: string;
  eps: number;
  roe: number;
  roa: number;
  debtEquity: number;
  currentRatio: number;
  evEbitda: number;
  sectorMedianPe: number;
  sectorMedianEvEbitda: number;
  sectorMedianPs: number;
  revenueHistory: { year: string; value: number }[];
  netIncomeHistory: { year: string; value: number }[];
  marginHistory: {
    year: string;
    gross: number;
    operating: number;
    net: number;
  }[];
  incomeHighlights: { label: string; value: string }[];
  balanceHighlights: { label: string; value: string }[];
}

const DEMO_DATA: Record<string, CompanyData> = {
  AAPL: {
    ticker: "AAPL",
    name: "Apple Inc.",
    sector: "Technology",
    industry: "Consumer Electronics",
    exchange: "NASDAQ",
    description:
      "Apple designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. It is also the world's largest company by market capitalization.",
    price: 185.5,
    marketCap: "$2.87T",
    pe: 29.5,
    forwardPe: 27.2,
    pb: 45.8,
    ps: 7.5,
    dividendYield: 0.5,
    beta: 1.21,
    high52w: 199.62,
    low52w: 164.08,
    revenue: "$383B",
    netIncome: "$96.9B",
    eps: 6.13,
    roe: 147.9,
    roa: 28.3,
    debtEquity: 1.76,
    currentRatio: 0.99,
    evEbitda: 22.4,
    sectorMedianPe: 24.1,
    sectorMedianEvEbitda: 18.3,
    sectorMedianPs: 5.2,
    revenueHistory: [
      { year: "2019", value: 260 },
      { year: "2020", value: 274 },
      { year: "2021", value: 365 },
      { year: "2022", value: 394 },
      { year: "2023", value: 383 },
    ],
    netIncomeHistory: [
      { year: "2019", value: 55.3 },
      { year: "2020", value: 57.4 },
      { year: "2021", value: 94.7 },
      { year: "2022", value: 99.8 },
      { year: "2023", value: 96.9 },
    ],
    marginHistory: [
      { year: "2019", gross: 37.8, operating: 24.6, net: 21.2 },
      { year: "2020", gross: 38.2, operating: 24.1, net: 20.9 },
      { year: "2021", gross: 41.8, operating: 29.8, net: 25.9 },
      { year: "2022", gross: 43.3, operating: 30.3, net: 25.3 },
      { year: "2023", gross: 44.1, operating: 29.8, net: 25.3 },
    ],
    incomeHighlights: [
      { label: "Revenue (TTM)", value: "$383.3B" },
      { label: "Gross Profit", value: "$169.1B" },
      { label: "Operating Income", value: "$114.3B" },
      { label: "Net Income", value: "$96.9B" },
      { label: "EBITDA", value: "$125.8B" },
      { label: "EPS (Diluted)", value: "$6.13" },
    ],
    balanceHighlights: [
      { label: "Total Assets", value: "$352.6B" },
      { label: "Total Liabilities", value: "$290.0B" },
      { label: "Total Equity", value: "$62.1B" },
      { label: "Cash & Equivalents", value: "$29.9B" },
      { label: "Long-term Debt", value: "$95.3B" },
      { label: "Free Cash Flow", value: "$99.6B" },
    ],
  },
  MSFT: {
    ticker: "MSFT",
    name: "Microsoft Corporation",
    sector: "Technology",
    industry: "Software—Infrastructure",
    exchange: "NASDAQ",
    description:
      "Microsoft develops, licenses, and supports software, services, devices, and solutions. Its cloud platform Azure is the second-largest cloud provider globally.",
    price: 415.2,
    marketCap: "$3.09T",
    pe: 36.2,
    forwardPe: 31.8,
    pb: 13.1,
    ps: 13.8,
    dividendYield: 0.7,
    beta: 0.89,
    high52w: 430.82,
    low52w: 310.15,
    revenue: "$225B",
    netIncome: "$88.1B",
    eps: 11.86,
    roe: 38.5,
    roa: 18.4,
    debtEquity: 0.35,
    currentRatio: 1.77,
    evEbitda: 28.1,
    sectorMedianPe: 24.1,
    sectorMedianEvEbitda: 18.3,
    sectorMedianPs: 5.2,
    revenueHistory: [
      { year: "2019", value: 125.8 },
      { year: "2020", value: 143.0 },
      { year: "2021", value: 168.1 },
      { year: "2022", value: 198.3 },
      { year: "2023", value: 225.0 },
    ],
    netIncomeHistory: [
      { year: "2019", value: 39.2 },
      { year: "2020", value: 44.3 },
      { year: "2021", value: 61.3 },
      { year: "2022", value: 72.7 },
      { year: "2023", value: 88.1 },
    ],
    marginHistory: [
      { year: "2019", gross: 67.3, operating: 34.1, net: 31.2 },
      { year: "2020", gross: 68.0, operating: 37.0, net: 31.0 },
      { year: "2021", gross: 68.9, operating: 41.6, net: 36.5 },
      { year: "2022", gross: 68.4, operating: 42.1, net: 36.7 },
      { year: "2023", gross: 69.8, operating: 44.6, net: 39.2 },
    ],
    incomeHighlights: [
      { label: "Revenue (TTM)", value: "$225.0B" },
      { label: "Gross Profit", value: "$157.2B" },
      { label: "Operating Income", value: "$100.3B" },
      { label: "Net Income", value: "$88.1B" },
      { label: "EBITDA", value: "$109.4B" },
      { label: "EPS (Diluted)", value: "$11.86" },
    ],
    balanceHighlights: [
      { label: "Total Assets", value: "$411.9B" },
      { label: "Total Liabilities", value: "$205.8B" },
      { label: "Total Equity", value: "$206.2B" },
      { label: "Cash & Equivalents", value: "$111.3B" },
      { label: "Long-term Debt", value: "$47.2B" },
      { label: "Free Cash Flow", value: "$87.6B" },
    ],
  },
  GOOGL: {
    ticker: "GOOGL",
    name: "Alphabet Inc.",
    sector: "Technology",
    industry: "Internet Content & Information",
    exchange: "NASDAQ",
    description:
      "Alphabet is the parent company of Google, whose products include Search, YouTube, Maps, and Android. Google Cloud is a fast-growing segment in the enterprise market.",
    price: 175.4,
    marketCap: "$2.19T",
    pe: 23.8,
    forwardPe: 20.1,
    pb: 6.9,
    ps: 6.4,
    dividendYield: 0.0,
    beta: 1.05,
    high52w: 193.31,
    low52w: 130.67,
    revenue: "$307B",
    netIncome: "$73.8B",
    eps: 5.8,
    roe: 28.9,
    roa: 17.6,
    debtEquity: 0.08,
    currentRatio: 2.1,
    evEbitda: 17.2,
    sectorMedianPe: 24.1,
    sectorMedianEvEbitda: 18.3,
    sectorMedianPs: 5.2,
    revenueHistory: [
      { year: "2019", value: 161.9 },
      { year: "2020", value: 182.5 },
      { year: "2021", value: 257.6 },
      { year: "2022", value: 282.8 },
      { year: "2023", value: 307.4 },
    ],
    netIncomeHistory: [
      { year: "2019", value: 34.3 },
      { year: "2020", value: 40.3 },
      { year: "2021", value: 76.0 },
      { year: "2022", value: 59.9 },
      { year: "2023", value: 73.8 },
    ],
    marginHistory: [
      { year: "2019", gross: 55.6, operating: 21.2, net: 21.2 },
      { year: "2020", gross: 53.6, operating: 22.6, net: 22.1 },
      { year: "2021", gross: 56.9, operating: 30.6, net: 29.5 },
      { year: "2022", gross: 54.0, operating: 26.5, net: 21.2 },
      { year: "2023", gross: 56.5, operating: 27.4, net: 24.0 },
    ],
    incomeHighlights: [
      { label: "Revenue (TTM)", value: "$307.4B" },
      { label: "Gross Profit", value: "$174.1B" },
      { label: "Operating Income", value: "$84.3B" },
      { label: "Net Income", value: "$73.8B" },
      { label: "EBITDA", value: "$98.0B" },
      { label: "EPS (Diluted)", value: "$5.80" },
    ],
    balanceHighlights: [
      { label: "Total Assets", value: "$402.4B" },
      { label: "Total Liabilities", value: "$115.6B" },
      { label: "Total Equity", value: "$283.4B" },
      { label: "Cash & Equivalents", value: "$108.1B" },
      { label: "Long-term Debt", value: "$13.3B" },
      { label: "Free Cash Flow", value: "$69.5B" },
    ],
  },
};

const ca_POPULAR_TICKERS = ["AAPL", "MSFT", "GOOGL"];

const CA_TABS = [
  "Overview",
  "Financials",
  "Valuation",
  "Technical",
  "Options",
] as const;
type CATab = (typeof CA_TABS)[number];

const ca_GREEN = "#10B981";
const ca_CYAN = "#00D9FF";
const ca_SLATE_300 = "#CBD5E1";
const ca_SLATE_400 = "#94A3B8";
const ca_SLATE_600 = "#475569";
const ca_BG_CARD = "#131823";
const ca_BG_PAGE = "#0A0F1A";
const ca_BORDER = "rgba(51,65,85,0.3)";
const ca_GREEN_BORDER = "rgba(16,185,129,0.3)";

const CaCustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string | number;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        backgroundColor: "#1E293B",
        border: "1px solid rgba(16,185,129,0.3)",
        borderRadius: 6,
        padding: "8px 12px",
        fontSize: 12,
      }}
    >
      {label !== undefined && (
        <p style={{ color: ca_SLATE_400, marginBottom: 4, fontSize: 11 }}>
          {label}
        </p>
      )}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color || ca_SLATE_300, margin: "2px 0" }}>
          <span style={{ color: ca_SLATE_400 }}>{p.name}: </span>
          {typeof p.value === "number" ? p.value.toLocaleString() : p.value}
        </p>
      ))}
    </div>
  );
};

function CaSectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3
      style={{
        color: ca_SLATE_300,
        fontSize: 13,
        fontWeight: 600,
        fontFamily: "JetBrains Mono, monospace",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        marginBottom: 12,
        borderBottom: `1px solid ${ca_GREEN_BORDER}`,
        paddingBottom: 6,
      }}
    >
      {children}
    </h3>
  );
}

function CaKeyStatRow({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string | number;
  highlight?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "6px 0",
        borderBottom: "1px solid rgba(51,65,85,0.2)",
      }}
    >
      <span style={{ color: ca_SLATE_400, fontSize: 12 }}>{label}</span>
      <span
        style={{
          color: highlight ? ca_GREEN : ca_SLATE_300,
          fontSize: 12,
          fontWeight: 600,
          fontFamily: "JetBrains Mono, monospace",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function ca_generateRandomWalk(
  startPrice: number,
  days: number,
  volatility = 0.012,
): { day: number; price: number }[] {
  const data: { day: number; price: number }[] = [];
  let price = startPrice * 0.85;
  for (let i = 0; i < days; i++) {
    const change = price * volatility * (Math.random() - 0.48);
    price = Math.max(price + change, 1);
    data.push({ day: i + 1, price: parseFloat(price.toFixed(2)) });
  }
  data[days - 1].price = startPrice;
  return data;
}

function CaOverviewTab({ data }: { data: CompanyData }) {
  const priceData = useMemo(
    () => ca_generateRandomWalk(data.price, 252),
    [data.ticker],
  );
  return (
    <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 16 }}>
      <Card className="p-4">
        <CaSectionTitle>Price — 252 Trading Days</CaSectionTitle>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart
            data={priceData}
            margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
            <XAxis
              dataKey="day"
              tick={{ fill: ca_SLATE_600, fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: ca_BORDER }}
              tickFormatter={(v) => `D${v}`}
              interval={49}
            />
            <YAxis
              tick={{ fill: ca_SLATE_600, fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: ca_BORDER }}
              tickFormatter={(v) => `$${v}`}
              width={52}
            />
            <Tooltip content={<CaCustomTooltip />} />
            <Line
              type="monotone"
              dataKey="price"
              stroke={ca_GREEN}
              strokeWidth={1.5}
              dot={false}
              name="Price"
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>
      <Card className="p-4">
        <CaSectionTitle>Key Statistics</CaSectionTitle>
        <CaKeyStatRow label="Market Cap" value={data.marketCap} highlight />
        <CaKeyStatRow label="Revenue (TTM)" value={data.revenue} />
        <CaKeyStatRow label="Net Income" value={data.netIncome} />
        <CaKeyStatRow label="EPS (Diluted)" value={`$${data.eps}`} />
        <CaKeyStatRow label="P/E Ratio" value={data.pe} />
        <CaKeyStatRow label="Forward P/E" value={data.forwardPe} />
        <CaKeyStatRow label="P/B Ratio" value={data.pb} />
        <CaKeyStatRow label="P/S Ratio" value={data.ps} />
        <CaKeyStatRow label="Dividend Yield" value={`${data.dividendYield}%`} />
        <CaKeyStatRow label="Beta" value={data.beta} />
        <CaKeyStatRow label="52W High" value={`$${data.high52w}`} />
        <CaKeyStatRow label="52W Low" value={`$${data.low52w}`} />
        <CaKeyStatRow label="ROE" value={`${data.roe}%`} />
        <CaKeyStatRow label="ROA" value={`${data.roa}%`} />
        <CaKeyStatRow label="Debt/Equity" value={data.debtEquity} />
        <CaKeyStatRow label="Current Ratio" value={data.currentRatio} />
      </Card>
    </div>
  );
}

function CaFinancialsTab({ data }: { data: CompanyData }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card className="p-4">
          <CaSectionTitle>Revenue (B USD)</CaSectionTitle>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={data.revenueHistory}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(51,65,85,0.3)"
                vertical={false}
              />
              <XAxis
                dataKey="year"
                tick={{ fill: ca_SLATE_600, fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: ca_BORDER }}
              />
              <YAxis
                tick={{ fill: ca_SLATE_600, fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: ca_BORDER }}
                width={40}
              />
              <Tooltip content={<CaCustomTooltip />} />
              <Bar
                dataKey="value"
                fill="#3B82F6"
                radius={[3, 3, 0, 0]}
                name="Revenue ($B)"
              />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card className="p-4">
          <CaSectionTitle>Net Income (B USD)</CaSectionTitle>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={data.netIncomeHistory}
              margin={{ top: 4, right: 8, bottom: 4, left: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(51,65,85,0.3)"
                vertical={false}
              />
              <XAxis
                dataKey="year"
                tick={{ fill: ca_SLATE_600, fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: ca_BORDER }}
              />
              <YAxis
                tick={{ fill: ca_SLATE_600, fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: ca_BORDER }}
                width={40}
              />
              <Tooltip content={<CaCustomTooltip />} />
              <Bar
                dataKey="value"
                fill={ca_GREEN}
                radius={[3, 3, 0, 0]}
                name="Net Income ($B)"
              />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <Card className="p-4">
        <CaSectionTitle>Margins Over Time (%)</CaSectionTitle>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart
            data={data.marginHistory}
            margin={{ top: 4, right: 16, bottom: 4, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
            <XAxis
              dataKey="year"
              tick={{ fill: ca_SLATE_600, fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: ca_BORDER }}
            />
            <YAxis
              tick={{ fill: ca_SLATE_600, fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: ca_BORDER }}
              width={36}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip content={<CaCustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 11, color: ca_SLATE_400 }} />
            <Line
              type="monotone"
              dataKey="gross"
              stroke={ca_CYAN}
              strokeWidth={2}
              dot={false}
              name="Gross %"
            />
            <Line
              type="monotone"
              dataKey="operating"
              stroke="#F59E0B"
              strokeWidth={2}
              dot={false}
              name="Operating %"
            />
            <Line
              type="monotone"
              dataKey="net"
              stroke={ca_GREEN}
              strokeWidth={2}
              dot={false}
              name="Net %"
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card className="p-4">
          <CaSectionTitle>Income Statement Highlights</CaSectionTitle>
          {data.incomeHighlights.map((item) => (
            <CaKeyStatRow
              key={item.label}
              label={item.label}
              value={item.value}
            />
          ))}
        </Card>
        <Card className="p-4">
          <CaSectionTitle>Balance Sheet Highlights</CaSectionTitle>
          {data.balanceHighlights.map((item) => (
            <CaKeyStatRow
              key={item.label}
              label={item.label}
              value={item.value}
            />
          ))}
        </Card>
      </div>
    </div>
  );
}

interface DCFInputs {
  revenueGrowth: string;
  ebitdaMargin: string;
  discountRate: string;
  terminalGrowth: string;
}

function CaValuationTab({ data }: { data: CompanyData }) {
  const [dcf, setDcf] = useState<DCFInputs>({
    revenueGrowth: "8",
    ebitdaMargin: "30",
    discountRate: "10",
    terminalGrowth: "3",
  });
  const [dcfResult, setDcfResult] = useState<{
    intrinsic: number;
    upside: number;
  } | null>(null);

  function handleDcfChange(field: keyof DCFInputs, value: string) {
    setDcf((prev) => ({ ...prev, [field]: value }));
  }

  function calculateDCF() {
    let revB = 0;
    const revStr = data.revenue;
    if (revStr.includes("T"))
      revB = parseFloat(revStr.replace(/[$T]/g, "")) * 1000;
    else if (revStr.includes("B"))
      revB = parseFloat(revStr.replace(/[$B]/g, ""));
    const g = parseFloat(dcf.revenueGrowth) / 100;
    const margin = parseFloat(dcf.ebitdaMargin) / 100;
    const dr = parseFloat(dcf.discountRate) / 100;
    const tg = parseFloat(dcf.terminalGrowth) / 100;
    if (isNaN(g) || isNaN(margin) || isNaN(dr) || isNaN(tg) || dr <= tg) {
      setDcfResult(null);
      return;
    }
    let totalPV = 0;
    let rev = revB;
    for (let yr = 1; yr <= 5; yr++) {
      rev *= 1 + g;
      const fcf = rev * margin * 0.65;
      totalPV += fcf / Math.pow(1 + dr, yr);
    }
    const terminalFCF = rev * margin * 0.65 * (1 + tg);
    const terminalValue = terminalFCF / (dr - tg);
    totalPV += terminalValue / Math.pow(1 + dr, 5);
    let mcapB = 0;
    const mcStr = data.marketCap;
    if (mcStr.includes("T"))
      mcapB = parseFloat(mcStr.replace(/[$T]/g, "")) * 1000;
    else if (mcStr.includes("B"))
      mcapB = parseFloat(mcStr.replace(/[$B]/g, ""));
    const sharesB = mcapB / data.price;
    const intrinsic = (totalPV * 1e9) / (sharesB * 1e9);
    const upside = ((intrinsic - data.price) / data.price) * 100;
    setDcfResult({
      intrinsic: parseFloat(intrinsic.toFixed(2)),
      upside: parseFloat(upside.toFixed(1)),
    });
  }

  const compData = [
    { metric: "P/E", company: data.pe, sector: data.sectorMedianPe },
    {
      metric: "EV/EBITDA",
      company: data.evEbitda,
      sector: data.sectorMedianEvEbitda,
    },
    { metric: "P/S", company: data.ps, sector: data.sectorMedianPs },
  ];

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
      <Card className="p-4">
        <CaSectionTitle>DCF Calculator</CaSectionTitle>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {(
            [
              { label: "Revenue Growth (%)", field: "revenueGrowth" },
              { label: "EBITDA Margin (%)", field: "ebitdaMargin" },
              { label: "Discount Rate (%)", field: "discountRate" },
              { label: "Terminal Growth (%)", field: "terminalGrowth" },
            ] as { label: string; field: keyof DCFInputs }[]
          ).map(({ label, field }) => (
            <div key={field}>
              <label
                style={{
                  color: ca_SLATE_400,
                  fontSize: 11,
                  display: "block",
                  marginBottom: 4,
                }}
              >
                {label}
              </label>
              <input
                type="number"
                value={dcf[field]}
                onChange={(e) => handleDcfChange(field, e.target.value)}
                style={{
                  width: "100%",
                  backgroundColor: "#0D1420",
                  border: `1px solid ${ca_BORDER}`,
                  borderRadius: 6,
                  color: ca_SLATE_300,
                  padding: "6px 10px",
                  fontSize: 13,
                  fontFamily: "JetBrains Mono, monospace",
                  outline: "none",
                  boxSizing: "border-box",
                }}
              />
            </div>
          ))}
          <button
            onClick={calculateDCF}
            style={{
              marginTop: 4,
              padding: "8px 16px",
              backgroundColor: "rgba(16,185,129,0.15)",
              border: `1px solid ${ca_GREEN}`,
              borderRadius: 6,
              color: ca_GREEN,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "JetBrains Mono, monospace",
              letterSpacing: "0.04em",
            }}
          >
            Calculate Intrinsic Value
          </button>
          {dcfResult && (
            <div
              style={{
                marginTop: 8,
                padding: "12px 14px",
                backgroundColor: "rgba(16,185,129,0.07)",
                border: `1px solid ${ca_GREEN_BORDER}`,
                borderRadius: 8,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  marginBottom: 8,
                }}
              >
                <span style={{ color: ca_SLATE_400, fontSize: 12 }}>
                  Current Price
                </span>
                <span
                  style={{
                    color: ca_SLATE_300,
                    fontFamily: "JetBrains Mono, monospace",
                    fontWeight: 600,
                  }}
                >
                  ${data.price.toFixed(2)}
                </span>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  marginBottom: 8,
                }}
              >
                <span style={{ color: ca_SLATE_400, fontSize: 12 }}>
                  Intrinsic Value
                </span>
                <span
                  style={{
                    color: ca_GREEN,
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 18,
                    fontWeight: 700,
                  }}
                >
                  ${dcfResult.intrinsic.toFixed(2)}
                </span>
              </div>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                }}
              >
                <span style={{ color: ca_SLATE_400, fontSize: 12 }}>
                  Upside / Downside
                </span>
                <span
                  style={{
                    color: dcfResult.upside >= 0 ? ca_GREEN : "#EF4444",
                    fontFamily: "JetBrains Mono, monospace",
                    fontWeight: 600,
                    fontSize: 14,
                  }}
                >
                  {dcfResult.upside >= 0 ? "+" : ""}
                  {dcfResult.upside}%
                </span>
              </div>
            </div>
          )}
        </div>
      </Card>
      <Card className="p-4">
        <CaSectionTitle>Comparable Valuation (vs Sector Median)</CaSectionTitle>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={compData}
            layout="vertical"
            margin={{ top: 4, right: 16, bottom: 4, left: 40 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(51,65,85,0.3)"
              horizontal={false}
            />
            <XAxis
              type="number"
              tick={{ fill: ca_SLATE_600, fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: ca_BORDER }}
            />
            <YAxis
              dataKey="metric"
              type="category"
              tick={{ fill: ca_SLATE_400, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CaCustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: 11, color: ca_SLATE_400 }} />
            <Bar
              dataKey="company"
              name={data.ticker}
              fill={ca_GREEN}
              radius={[0, 3, 3, 0]}
              barSize={14}
            />
            <Bar
              dataKey="sector"
              name="Sector Median"
              fill="rgba(100,116,139,0.6)"
              radius={[0, 3, 3, 0]}
              barSize={14}
            />
          </BarChart>
        </ResponsiveContainer>
        <div style={{ marginTop: 16 }}>
          <CaSectionTitle>Multiple Summary</CaSectionTitle>
          <CaKeyStatRow label={`P/E — ${data.ticker}`} value={data.pe} />
          <CaKeyStatRow
            label="P/E — Sector Median"
            value={data.sectorMedianPe}
          />
          <CaKeyStatRow
            label={`EV/EBITDA — ${data.ticker}`}
            value={data.evEbitda}
          />
          <CaKeyStatRow
            label="EV/EBITDA — Sector Median"
            value={data.sectorMedianEvEbitda}
          />
          <CaKeyStatRow label={`P/S — ${data.ticker}`} value={data.ps} />
          <CaKeyStatRow
            label="P/S — Sector Median"
            value={data.sectorMedianPs}
          />
        </div>
      </Card>
    </div>
  );
}

// ── CompanyAnalyzer main content ──────────────────────────────────────────────

function CompanyAnalyzerContent() {
  const { data: indicesData } = useIndices();
  const usingFallback = !indicesData;
  const [searchInput, setSearchInput] = useState("");
  const [activeTicker, setActiveTicker] = useState<string>("AAPL");
  const [activeCATab, setActiveCATab] = useState<CATab>("Overview");

  const keyIndices = useMemo(() => {
    if (!indicesData) return [];
    const symbols = ["^GSPC", "^IXIC", "^DJI", "^RUT"];
    return Object.values(indicesData)
      .flat()
      .filter((idx) => symbols.includes(idx.symbol));
  }, [indicesData]);

  const data = DEMO_DATA[activeTicker] ?? null;

  function loadTicker(ticker: string) {
    const t = ticker.trim().toUpperCase();
    if (!t) return;
    setActiveTicker(t);
    setActiveCATab("Overview");
    setSearchInput("");
  }

  function handleSearchKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") loadTicker(searchInput);
  }

  const isKnown = activeTicker in DEMO_DATA;

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: ca_BG_PAGE,
        color: "#F1F5F9",
        fontFamily: "Inter, system-ui, sans-serif",
        padding: "24px 28px",
      }}
    >
      {usingFallback && (
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

      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 22,
            fontWeight: 700,
            color: ca_GREEN,
            letterSpacing: "0.04em",
            marginBottom: 2,
          }}
        >
          Company Analyzer
        </h1>
        <p style={{ color: ca_SLATE_400, fontSize: 13 }}>
          Fundamental analysis, valuation, and technicals for any publicly
          traded company.
        </p>
      </div>

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
                backgroundColor: ca_BG_CARD,
                borderRadius: 8,
                padding: "8px 14px",
                border: `1px solid ${ca_BORDER}`,
                minWidth: 140,
              }}
            >
              <div style={{ fontSize: 10, color: ca_SLATE_600 }}>
                {idx.name}
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span
                  style={{
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 14,
                    fontWeight: 700,
                    color: ca_SLATE_300,
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
                    color: idx.change.percent >= 0 ? ca_GREEN : "#EF4444",
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

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 12,
          marginBottom: 28,
          padding: "24px 20px",
          backgroundColor: ca_BG_CARD,
          border: `1px solid ${ca_BORDER}`,
          borderRadius: 12,
        }}
      >
        <div style={{ display: "flex", gap: 10, width: "100%", maxWidth: 580 }}>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value.toUpperCase())}
            onKeyDown={handleSearchKeyDown}
            placeholder="Enter ticker (e.g. AAPL, MSFT, TSLA)"
            style={{
              flex: 1,
              backgroundColor: "#0D1420",
              border: `1px solid ${ca_BORDER}`,
              borderRadius: 8,
              color: ca_SLATE_300,
              padding: "10px 16px",
              fontSize: 14,
              fontFamily: "JetBrains Mono, monospace",
              outline: "none",
              letterSpacing: "0.04em",
            }}
          />
          <button
            onClick={() => loadTicker(searchInput)}
            style={{
              padding: "10px 22px",
              backgroundColor: "rgba(16,185,129,0.15)",
              border: `1px solid ${ca_GREEN}`,
              borderRadius: 8,
              color: ca_GREEN,
              fontSize: 13,
              fontWeight: 700,
              cursor: "pointer",
              fontFamily: "JetBrains Mono, monospace",
              letterSpacing: "0.05em",
              whiteSpace: "nowrap",
            }}
          >
            Analyze
          </button>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          <span style={{ color: ca_SLATE_600, fontSize: 11, fontWeight: 500 }}>
            Popular:
          </span>
          {ca_POPULAR_TICKERS.map((t, i) => (
            <button
              key={t}
              onClick={() => loadTicker(t)}
              style={{
                background: "none",
                border: "none",
                color: activeTicker === t ? ca_GREEN : ca_SLATE_400,
                fontSize: 12,
                fontFamily: "JetBrains Mono, monospace",
                fontWeight: activeTicker === t ? 700 : 400,
                cursor: "pointer",
                padding: "2px 4px",
                borderBottom:
                  activeTicker === t
                    ? `1px solid ${ca_GREEN}`
                    : "1px solid transparent",
              }}
            >
              {t}
              {i < ca_POPULAR_TICKERS.length - 1 && (
                <span style={{ color: ca_SLATE_600, marginLeft: 8 }}>|</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {!isKnown && (
        <div
          style={{
            textAlign: "center",
            padding: "40px 20px",
            backgroundColor: ca_BG_CARD,
            border: `1px solid ${ca_BORDER}`,
            borderRadius: 12,
          }}
        >
          <p style={{ color: ca_SLATE_400, fontSize: 14, marginBottom: 8 }}>
            Demo data not available for{" "}
            <strong
              style={{
                color: ca_SLATE_300,
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              {activeTicker}
            </strong>
            .
          </p>
          <p style={{ color: ca_SLATE_600, fontSize: 12 }}>
            Select a popular ticker above or connect a backend to load live
            data.
          </p>
        </div>
      )}

      {isKnown && data && (
        <>
          <div
            style={{
              backgroundColor: ca_BG_CARD,
              border: `1px solid ${ca_BORDER}`,
              borderRadius: 12,
              padding: "20px 24px",
              marginBottom: 16,
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: 12,
              }}
            >
              <div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    gap: 12,
                    marginBottom: 6,
                  }}
                >
                  <h2
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 26,
                      fontWeight: 700,
                      color: "#F1F5F9",
                    }}
                  >
                    {data.name}
                  </h2>
                  <span
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 18,
                      fontWeight: 600,
                      color: ca_GREEN,
                      border: `1px solid ${ca_GREEN_BORDER}`,
                      backgroundColor: "rgba(16,185,129,0.08)",
                      padding: "2px 10px",
                      borderRadius: 6,
                    }}
                  >
                    {data.ticker}
                  </span>
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <Badge variant="info">{data.sector}</Badge>
                  <Badge variant="neutral">{data.industry}</Badge>
                  <Badge variant="neutral">{data.exchange}</Badge>
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div
                  style={{
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 32,
                    fontWeight: 700,
                    color: ca_GREEN,
                    lineHeight: 1,
                  }}
                >
                  ${data.price.toFixed(2)}
                </div>
                <div
                  style={{ color: ca_SLATE_400, fontSize: 12, marginTop: 4 }}
                >
                  USD · Demo Data
                </div>
              </div>
            </div>
            <p
              style={{
                color: ca_SLATE_400,
                fontSize: 13,
                lineHeight: 1.6,
                marginTop: 14,
                borderTop: `1px solid ${ca_BORDER}`,
                paddingTop: 12,
              }}
            >
              {data.description}
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 10,
              marginBottom: 16,
            }}
          >
            <StatCard
              label="Revenue TTM"
              value={data.revenue}
              color={ca_GREEN}
            />
            <StatCard label="Net Income" value={data.netIncome} />
            <StatCard label="52W High" value={`$${data.high52w}`} />
            <StatCard label="52W Low" value={`$${data.low52w}`} />
          </div>

          <div
            style={{
              display: "flex",
              gap: 2,
              marginBottom: 16,
              backgroundColor: ca_BG_CARD,
              border: `1px solid ${ca_BORDER}`,
              borderRadius: 10,
              padding: 4,
            }}
          >
            {CA_TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveCATab(tab)}
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  border: "none",
                  borderRadius: 7,
                  backgroundColor:
                    activeCATab === tab
                      ? "rgba(16,185,129,0.15)"
                      : "transparent",
                  color: activeCATab === tab ? ca_GREEN : ca_SLATE_400,
                  fontSize: 13,
                  fontWeight: activeCATab === tab ? 600 : 400,
                  fontFamily: "JetBrains Mono, monospace",
                  cursor: "pointer",
                  letterSpacing: "0.02em",
                  transition: "all 0.15s ease",
                  borderBottom:
                    activeCATab === tab
                      ? `2px solid ${ca_GREEN}`
                      : "2px solid transparent",
                }}
              >
                {tab}
              </button>
            ))}
          </div>

          <div>
            {activeCATab === "Overview" && <CaOverviewTab data={data} />}
            {activeCATab === "Financials" && <CaFinancialsTab data={data} />}
            {activeCATab === "Valuation" && <CaValuationTab data={data} />}
          </div>
        </>
      )}
    </div>
  );
}

// ── Equity Research content ───────────────────────────────────────────────────

function EquityResearchContent() {
  const { data: indicesData } = useIndices();
  const usingFallback = !indicesData;

  const [selectedTicker, setSelectedTicker] =
    useState<keyof typeof STOCKS>("AAPL");
  const stock = STOCKS[selectedTicker];

  const keyIndices = useMemo(() => {
    if (!indicesData) return [];
    const targets = ["^GSPC", "^IXIC", "^DJI", "^RUT"];
    return Object.values(indicesData)
      .flat()
      .filter((idx) => targets.includes(idx.symbol));
  }, [indicesData]);

  const pctBarWidth =
    ((stock.price - stock.targetPrice.low) /
      (stock.targetPrice.high - stock.targetPrice.low)) *
    100;

  return (
    <div style={{ color: "#F1F5F9", minHeight: "100vh" }}>
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 4,
        }}
      >
        Equity Research
      </h1>
      <p style={{ color: "#94A3B8", fontSize: 14, marginBottom: 16 }}>
        In-depth stock analysis &mdash; {stock.name} ({stock.sector})
      </p>

      <div
        style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}
      >
        {TICKERS.map((t) => (
          <button
            key={t}
            onClick={() => setSelectedTicker(t)}
            style={{
              padding: "6px 16px",
              borderRadius: 6,
              border:
                selectedTicker === t
                  ? "1px solid #00D9FF"
                  : "1px solid rgba(51,65,85,0.4)",
              backgroundColor:
                selectedTicker === t
                  ? "rgba(0,217,255,0.10)"
                  : "rgba(19,24,35,0.6)",
              color: selectedTicker === t ? "#00D9FF" : "#94A3B8",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13,
              fontWeight: selectedTicker === t ? 700 : 400,
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {usingFallback && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 14px",
            marginBottom: 12,
            borderRadius: 8,
            backgroundColor: "rgba(245,158,11,0.08)",
            border: "1px solid rgba(245,158,11,0.2)",
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 11,
            color: "#F59E0B",
          }}
        >
          <span>Backend unreachable — showing demo data</span>
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

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          marginBottom: 16,
        }}
      >
        <Card
          title={`${stock.ticker} — ${stock.name}`}
          subtitle="Price Summary"
        >
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: 12,
              marginBottom: 16,
            }}
          >
            <span
              style={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 32,
                fontWeight: 700,
                color: "#F1F5F9",
              }}
            >
              ${eq_fmt(stock.price)}
            </span>
            <span
              style={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 16,
                color: stock.change >= 0 ? "#10B981" : "#EF4444",
              }}
            >
              {stock.change >= 0 ? "+" : ""}
              {eq_fmt(stock.change)} ({stock.changePct >= 0 ? "+" : ""}
              {stock.changePct}%)
            </span>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: 12,
            }}
          >
            {(
              [
                ["Open", `$${eq_fmt(stock.open)}`],
                ["High", `$${eq_fmt(stock.high)}`],
                ["Low", `$${eq_fmt(stock.low)}`],
                ["Volume", stock.volume],
                ["Mkt Cap", stock.marketCap],
                ["P/E", stock.pe.toString()],
                ["EPS", `$${eq_fmt(stock.eps)}`],
                ["Dividend", `$${eq_fmt(stock.dividend)}`],
                ["52W Range", `$${stock.week52Low} — $${stock.week52High}`],
              ] as [string, string][]
            ).map(([label, val]) => (
              <div key={label}>
                <div
                  style={{ color: "#94A3B8", fontSize: 11, marginBottom: 2 }}
                >
                  {label}
                </div>
                <div
                  style={{
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 13,
                  }}
                >
                  {val}
                </div>
              </div>
            ))}
          </div>
        </Card>
        <Card
          title="Analyst Ratings"
          subtitle={`${stock.analystRatings.reduce((a, b) => a + b.value, 0)} analysts`}
        >
          <div style={{ display: "flex", alignItems: "center" }}>
            <ResponsiveContainer width="50%" height={180}>
              <PieChart>
                <Pie
                  data={stock.analystRatings}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  dataKey="value"
                  stroke="none"
                >
                  {stock.analystRatings.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Legend
                  verticalAlign="bottom"
                  formatter={(value: any) => (
                    <span style={{ color: "#94A3B8", fontSize: 12 }}>
                      {value}
                    </span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ flex: 1, paddingLeft: 16 }}>
              {stock.analystRatings.map((r) => (
                <div
                  key={r.name}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 8,
                  }}
                >
                  <span
                    style={{ color: r.color, fontSize: 14, fontWeight: 600 }}
                  >
                    {r.name}
                  </span>
                  <span
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 14,
                    }}
                  >
                    {r.value}
                  </span>
                </div>
              ))}
              <div
                style={{
                  marginTop: 12,
                  borderTop: "1px solid rgba(51,65,85,0.3)",
                  paddingTop: 8,
                }}
              >
                <div style={{ color: "#94A3B8", fontSize: 11 }}>Consensus</div>
                <div
                  style={{
                    color: "#10B981",
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 16,
                    fontWeight: 700,
                  }}
                >
                  {stock.consensus}
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          marginBottom: 16,
        }}
      >
        <Card title="Target Price Range" subtitle="12-month analyst targets">
          <div style={{ padding: "16px 0" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 12,
                color: "#94A3B8",
                marginBottom: 8,
              }}
            >
              <span>Low: ${stock.targetPrice.low}</span>
              <span>Median: ${stock.targetPrice.median}</span>
              <span>High: ${stock.targetPrice.high}</span>
            </div>
            <div
              style={{
                position: "relative",
                height: 24,
                backgroundColor: "rgba(51,65,85,0.3)",
                borderRadius: 12,
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  height: "100%",
                  width: `${Math.max(0, Math.min(100, pctBarWidth))}%`,
                  background: "linear-gradient(90deg, #10B981, #059669)",
                  borderRadius: 12,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  top: -6,
                  left: `${Math.max(0, Math.min(100, pctBarWidth))}%`,
                  transform: "translateX(-50%)",
                  width: 3,
                  height: 36,
                  backgroundColor: "#F1F5F9",
                  borderRadius: 2,
                }}
              />
            </div>
            <div style={{ textAlign: "center", marginTop: 12 }}>
              <span style={{ color: "#94A3B8", fontSize: 12 }}>Current: </span>
              <span
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 14,
                  fontWeight: 600,
                }}
              >
                ${eq_fmt(stock.price)}
              </span>
              {stock.targetPrice.median > stock.price ? (
                <span style={{ color: "#10B981", fontSize: 12, marginLeft: 8 }}>
                  Upside to median: +
                  {(
                    ((stock.targetPrice.median - stock.price) / stock.price) *
                    100
                  ).toFixed(1)}
                  %
                </span>
              ) : (
                <span style={{ color: "#EF4444", fontSize: 12, marginLeft: 8 }}>
                  Downside to median:{" "}
                  {(
                    ((stock.targetPrice.median - stock.price) / stock.price) *
                    100
                  ).toFixed(1)}
                  %
                </span>
              )}
            </div>
          </div>
        </Card>
        <Card title="Revenue & EPS" subtitle="Last 4 quarters">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stock.quarterlyData}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(51,65,85,0.3)"
              />
              <XAxis
                dataKey="quarter"
                tick={{ fill: "#94A3B8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                yAxisId="rev"
                tick={{ fill: "#94A3B8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: any) => `$${v}B`}
              />
              <YAxis
                yAxisId="eps"
                orientation="right"
                tick={{ fill: "#94A3B8", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: any) => `$${v}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#131823",
                  border: "1px solid rgba(51,65,85,0.3)",
                  borderRadius: 8,
                  color: "#F1F5F9",
                }}
              />
              <Bar
                yAxisId="rev"
                dataKey="revenue"
                name="Revenue ($B)"
                fill="#10B981"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                yAxisId="eps"
                dataKey="eps"
                name="EPS ($)"
                fill="#6EE7B7"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          marginBottom: 16,
        }}
      >
        <Card title="Key Financials" subtitle="Trailing twelve months">
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}
          >
            {stock.financials.map((f) => (
              <div
                key={f.label}
                style={{
                  padding: "10px 12px",
                  borderRadius: 8,
                  backgroundColor: "rgba(51,65,85,0.15)",
                }}
              >
                <div
                  style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}
                >
                  {f.label}
                </div>
                <div
                  style={{
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 15,
                    fontWeight: 600,
                    color: "#F1F5F9",
                  }}
                >
                  {f.value}
                </div>
              </div>
            ))}
          </div>
        </Card>
        <Card title="News Sentiment" subtitle="Latest headlines">
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {stock.newsItems.map((item, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 12px",
                  borderRadius: 8,
                  backgroundColor: "rgba(51,65,85,0.15)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    flex: 1,
                  }}
                >
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      backgroundColor: sentimentColor[item.sentiment],
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontSize: 13 }}>{item.headline}</span>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    flexShrink: 0,
                    marginLeft: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      textTransform: "capitalize",
                      color: sentimentColor[item.sentiment],
                    }}
                  >
                    {item.sentiment}
                  </span>
                  <span
                    style={{
                      color: "#94A3B8",
                      fontSize: 11,
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {item.date}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

const PAGE_TABS = ["Equity Overview", "Company Analyzer"];

export default function EquityResearch() {
  const [activeTab, setActiveTab] = useState(PAGE_TABS[0]);

  return (
    <div style={{ color: "#F1F5F9", minHeight: "100vh" }}>
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 4,
        }}
      >
        Equity Research
      </h1>
      <p style={{ color: "#94A3B8", fontSize: 14, marginBottom: 16 }}>
        In-depth stock analysis and company fundamentals
      </p>

      <div style={{ marginBottom: 20 }}>
        <Tabs tabs={PAGE_TABS} active={activeTab} onChange={setActiveTab} />
      </div>

      {activeTab === "Equity Overview" && <EquityResearchContent />}
      {activeTab === "Company Analyzer" && <CompanyAnalyzerContent />}
    </div>
  );
}
