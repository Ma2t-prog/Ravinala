import { useMemo, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Card } from "../../components/ui/Card";
import { Tabs } from "../../components/ui/Tabs";
import { useCommodities, useFX, useIndices } from "../../hooks/useMarketData";

// ── Types ────────────────────────────────────────────────────────────────────

interface Asset {
  name: string;
  ticker: string;
  price: string;
  change: number;
  trend: string;
}

type AssetClass = "Equities" | "Fixed Income" | "Commodities" | "FX" | "Crypto";

// ── ETF Types ─────────────────────────────────────────────────────────────────

interface ETFHolding {
  name: string;
  weight: number;
}

interface ETFSector {
  name: string;
  value: number;
  color: string;
}

interface ETF {
  ticker: string;
  name: string;
  assetClass: string;
  region: string;
  aum: string;
  expenseRatio: number;
  ytdReturn: number;
  oneYReturn: number;
  divYield: number;
  topHoldings: ETFHolding[];
  sectors: ETFSector[];
}

// ── Asset Explorer Demo Data ──────────────────────────────────────────────────

const assetData: Record<AssetClass, Asset[]> = {
  Equities: [
    {
      name: "S&P 500",
      ticker: "SPX",
      price: "5,234.18",
      change: 0.42,
      trend: "Grinding higher near ATH on tech strength",
    },
    {
      name: "Nasdaq 100",
      ticker: "NDX",
      price: "18,339.44",
      change: 0.68,
      trend: "AI momentum driving mega-cap rally",
    },
    {
      name: "Dow Jones",
      ticker: "DJI",
      price: "39,512.84",
      change: 0.12,
      trend: "Consolidating, rotation into value",
    },
    {
      name: "Russell 2000",
      ticker: "RUT",
      price: "2,072.53",
      change: -0.35,
      trend: "Lagging large caps, rate sensitivity",
    },
    {
      name: "Euro Stoxx 50",
      ticker: "SX5E",
      price: "4,987.32",
      change: 0.28,
      trend: "ECB cut expectations supporting EU equities",
    },
    {
      name: "Nikkei 225",
      ticker: "NKY",
      price: "40,168.07",
      change: 1.15,
      trend: "Weak yen tailwind, BOJ normalization",
    },
    {
      name: "FTSE 100",
      ticker: "UKX",
      price: "7,952.62",
      change: -0.18,
      trend: "Mining drag, defensive stance",
    },
    {
      name: "Hang Seng",
      ticker: "HSI",
      price: "16,721.38",
      change: -0.82,
      trend: "China stimulus hopes fading",
    },
  ],
  "Fixed Income": [
    {
      name: "US 10Y Treasury",
      ticker: "UST10Y",
      price: "4.25%",
      change: -0.02,
      trend: "Range-bound on mixed data",
    },
    {
      name: "US 2Y Treasury",
      ticker: "UST2Y",
      price: "4.60%",
      change: 0.03,
      trend: "Hawkish repricing on sticky inflation",
    },
    {
      name: "German 10Y Bund",
      ticker: "DE10Y",
      price: "2.42%",
      change: -0.04,
      trend: "ECB dovish tilt pulling yields",
    },
    {
      name: "UK 10Y Gilt",
      ticker: "GB10Y",
      price: "4.08%",
      change: 0.01,
      trend: "BOE hold expected, gilts stable",
    },
    {
      name: "Japan 10Y JGB",
      ticker: "JP10Y",
      price: "0.88%",
      change: 0.05,
      trend: "YCC band adjustment pressure",
    },
    {
      name: "US IG Corporate",
      ticker: "LQD",
      price: "$108.42",
      change: 0.12,
      trend: "Tight spreads, strong demand",
    },
    {
      name: "US HY Corporate",
      ticker: "HYG",
      price: "$77.85",
      change: 0.08,
      trend: "Spread compression continues",
    },
    {
      name: "EM Sovereign",
      ticker: "EMB",
      price: "$86.32",
      change: -0.22,
      trend: "USD strength weighing on EM debt",
    },
  ],
  Commodities: [
    {
      name: "Gold",
      ticker: "XAU",
      price: "$2,178.40",
      change: 0.65,
      trend: "Central bank buying & haven demand",
    },
    {
      name: "Silver",
      ticker: "XAG",
      price: "$24.92",
      change: 1.12,
      trend: "Industrial + monetary demand surge",
    },
    {
      name: "WTI Crude",
      ticker: "CL",
      price: "$78.34",
      change: -0.45,
      trend: "OPEC cuts vs demand concerns",
    },
    {
      name: "Brent Crude",
      ticker: "CO",
      price: "$82.56",
      change: -0.38,
      trend: "Geopolitical premium holding",
    },
    {
      name: "Natural Gas",
      ticker: "NG",
      price: "$1.82",
      change: -2.1,
      trend: "Warm weather crushing demand",
    },
    {
      name: "Copper",
      ticker: "HG",
      price: "$3.98",
      change: 0.92,
      trend: "Green transition demand thesis",
    },
    {
      name: "Platinum",
      ticker: "PL",
      price: "$912.50",
      change: 0.35,
      trend: "Auto catalyst demand recovering",
    },
    {
      name: "Wheat",
      ticker: "ZW",
      price: "$5.62",
      change: -1.25,
      trend: "Black Sea exports resuming",
    },
  ],
  FX: [
    {
      name: "EUR/USD",
      ticker: "EURUSD",
      price: "1.0862",
      change: -0.15,
      trend: "ECB-Fed divergence narrowing",
    },
    {
      name: "GBP/USD",
      ticker: "GBPUSD",
      price: "1.2645",
      change: -0.08,
      trend: "BOE pause priced in",
    },
    {
      name: "USD/JPY",
      ticker: "USDJPY",
      price: "151.42",
      change: 0.25,
      trend: "BOJ intervention watch at 152",
    },
    {
      name: "USD/CHF",
      ticker: "USDCHF",
      price: "0.8832",
      change: 0.12,
      trend: "SNB surprise cut weakened franc",
    },
    {
      name: "AUD/USD",
      ticker: "AUDUSD",
      price: "0.6538",
      change: 0.32,
      trend: "China stimulus optimism",
    },
    {
      name: "USD/CAD",
      ticker: "USDCAD",
      price: "1.3582",
      change: -0.1,
      trend: "Oil recovery supporting CAD",
    },
    {
      name: "NZD/USD",
      ticker: "NZDUSD",
      price: "0.6012",
      change: 0.18,
      trend: "RBNZ hawkish hold",
    },
    {
      name: "EUR/GBP",
      ticker: "EURGBP",
      price: "0.8592",
      change: -0.05,
      trend: "Range-bound cross",
    },
  ],
  Crypto: [
    {
      name: "Bitcoin",
      ticker: "BTC",
      price: "$67,842",
      change: 2.35,
      trend: "Halving approaching, ETF inflows strong",
    },
    {
      name: "Ethereum",
      ticker: "ETH",
      price: "$3,485",
      change: 1.82,
      trend: "Dencun upgrade, L2 scaling gains",
    },
    {
      name: "Solana",
      ticker: "SOL",
      price: "$182.40",
      change: 4.15,
      trend: "DeFi activity & meme coin mania",
    },
    {
      name: "BNB",
      ticker: "BNB",
      price: "$578.20",
      change: 0.95,
      trend: "Exchange token, steady utility",
    },
    {
      name: "Cardano",
      ticker: "ADA",
      price: "$0.642",
      change: -1.2,
      trend: "Hydra scaling, slow adoption",
    },
    {
      name: "Avalanche",
      ticker: "AVAX",
      price: "$52.18",
      change: 3.4,
      trend: "Subnet adoption & gaming push",
    },
    {
      name: "Polkadot",
      ticker: "DOT",
      price: "$8.42",
      change: 1.05,
      trend: "Parachain ecosystem maturing",
    },
    {
      name: "Chainlink",
      ticker: "LINK",
      price: "$18.95",
      change: 2.8,
      trend: "CCIP cross-chain adoption",
    },
  ],
};

// Correlation matrix between asset classes
const correlationLabels: AssetClass[] = [
  "Equities",
  "Fixed Income",
  "Commodities",
  "FX",
  "Crypto",
];
const correlationMatrix = [
  [1.0, -0.35, 0.25, 0.1, 0.45],
  [-0.35, 1.0, -0.1, -0.2, -0.15],
  [0.25, -0.1, 1.0, 0.3, 0.2],
  [0.1, -0.2, 0.3, 1.0, 0.05],
  [0.45, -0.15, 0.2, 0.05, 1.0],
];

function corrColor(v: number): string {
  if (v >= 0.8) return "#10B981";
  if (v >= 0.4) return "rgba(16,185,129,0.6)";
  if (v >= 0.1) return "rgba(16,185,129,0.3)";
  if (v > -0.1) return "rgba(51,65,85,0.3)";
  if (v > -0.4) return "rgba(239,68,68,0.3)";
  if (v > -0.8) return "rgba(239,68,68,0.6)";
  return "#EF4444";
}

// ── ETF Demo Data ─────────────────────────────────────────────────────────────

const SC = [
  "#10B981",
  "#6EE7B7",
  "#34D399",
  "#059669",
  "#047857",
  "#064E3B",
  "#A7F3D0",
  "#D1FAE5",
];

const etfs: ETF[] = [
  {
    ticker: "SPY",
    name: "SPDR S&P 500 ETF",
    assetClass: "Equity",
    region: "US",
    aum: "$502B",
    expenseRatio: 0.09,
    ytdReturn: 10.2,
    oneYReturn: 28.5,
    divYield: 1.32,
    topHoldings: [
      { name: "MSFT", weight: 7.2 },
      { name: "AAPL", weight: 6.8 },
      { name: "NVDA", weight: 5.1 },
      { name: "AMZN", weight: 3.8 },
      { name: "META", weight: 2.5 },
    ],
    sectors: [
      { name: "Tech", value: 31, color: SC[0] },
      { name: "Healthcare", value: 13, color: SC[1] },
      { name: "Financials", value: 13, color: SC[2] },
      { name: "Cons Disc", value: 11, color: SC[3] },
      { name: "Other", value: 32, color: SC[4] },
    ],
  },
  {
    ticker: "QQQ",
    name: "Invesco QQQ Trust",
    assetClass: "Equity",
    region: "US",
    aum: "$250B",
    expenseRatio: 0.2,
    ytdReturn: 12.8,
    oneYReturn: 35.2,
    divYield: 0.55,
    topHoldings: [
      { name: "MSFT", weight: 8.9 },
      { name: "AAPL", weight: 8.1 },
      { name: "NVDA", weight: 6.4 },
      { name: "AMZN", weight: 5.2 },
      { name: "AVGO", weight: 4.8 },
    ],
    sectors: [
      { name: "Tech", value: 58, color: SC[0] },
      { name: "Cons Disc", value: 15, color: SC[1] },
      { name: "Healthcare", value: 7, color: SC[2] },
      { name: "Telecom", value: 5, color: SC[3] },
      { name: "Other", value: 15, color: SC[4] },
    ],
  },
  {
    ticker: "IWM",
    name: "iShares Russell 2000",
    assetClass: "Equity",
    region: "US",
    aum: "$60B",
    expenseRatio: 0.19,
    ytdReturn: 2.1,
    oneYReturn: 15.8,
    divYield: 1.45,
    topHoldings: [
      { name: "SMCI", weight: 1.2 },
      { name: "MSTR", weight: 0.8 },
      { name: "SFM", weight: 0.5 },
      { name: "FN", weight: 0.4 },
      { name: "ONTO", weight: 0.4 },
    ],
    sectors: [
      { name: "Healthcare", value: 17, color: SC[0] },
      { name: "Industrials", value: 16, color: SC[1] },
      { name: "Financials", value: 16, color: SC[2] },
      { name: "Tech", value: 14, color: SC[3] },
      { name: "Other", value: 37, color: SC[4] },
    ],
  },
  {
    ticker: "VTI",
    name: "Vanguard Total Stock Mkt",
    assetClass: "Equity",
    region: "US",
    aum: "$380B",
    expenseRatio: 0.03,
    ytdReturn: 9.5,
    oneYReturn: 27.1,
    divYield: 1.38,
    topHoldings: [
      { name: "MSFT", weight: 6.3 },
      { name: "AAPL", weight: 5.9 },
      { name: "NVDA", weight: 4.5 },
      { name: "AMZN", weight: 3.4 },
      { name: "META", weight: 2.2 },
    ],
    sectors: [
      { name: "Tech", value: 30, color: SC[0] },
      { name: "Healthcare", value: 13, color: SC[1] },
      { name: "Financials", value: 13, color: SC[2] },
      { name: "Cons Disc", value: 10, color: SC[3] },
      { name: "Other", value: 34, color: SC[4] },
    ],
  },
  {
    ticker: "VXUS",
    name: "Vanguard Intl Stock",
    assetClass: "Equity",
    region: "International",
    aum: "$68B",
    expenseRatio: 0.07,
    ytdReturn: 5.2,
    oneYReturn: 12.4,
    divYield: 3.1,
    topHoldings: [
      { name: "TSM", weight: 2.1 },
      { name: "NOVO-B", weight: 1.5 },
      { name: "ASML", weight: 1.3 },
      { name: "SAP", weight: 1.0 },
      { name: "SHEL", weight: 0.9 },
    ],
    sectors: [
      { name: "Financials", value: 22, color: SC[0] },
      { name: "Tech", value: 14, color: SC[1] },
      { name: "Industrials", value: 14, color: SC[2] },
      { name: "Healthcare", value: 10, color: SC[3] },
      { name: "Other", value: 40, color: SC[4] },
    ],
  },
  {
    ticker: "BND",
    name: "Vanguard Total Bond Mkt",
    assetClass: "Fixed Income",
    region: "US",
    aum: "$105B",
    expenseRatio: 0.03,
    ytdReturn: -0.8,
    oneYReturn: 2.1,
    divYield: 4.52,
    topHoldings: [
      { name: "US Treas", weight: 46.2 },
      { name: "MBS", weight: 26.8 },
      { name: "Corp IG", weight: 18.5 },
      { name: "Agency", weight: 5.2 },
      { name: "Other", weight: 3.3 },
    ],
    sectors: [
      { name: "Treasury", value: 46, color: SC[0] },
      { name: "MBS", value: 27, color: SC[1] },
      { name: "Corporate", value: 19, color: SC[2] },
      { name: "Agency", value: 5, color: SC[3] },
      { name: "Other", value: 3, color: SC[4] },
    ],
  },
  {
    ticker: "GLD",
    name: "SPDR Gold Shares",
    assetClass: "Commodity",
    region: "Global",
    aum: "$58B",
    expenseRatio: 0.4,
    ytdReturn: 5.8,
    oneYReturn: 18.2,
    divYield: 0.0,
    topHoldings: [
      { name: "Gold Bullion", weight: 100.0 },
      { name: "", weight: 0 },
      { name: "", weight: 0 },
      { name: "", weight: 0 },
      { name: "", weight: 0 },
    ],
    sectors: [{ name: "Gold", value: 100, color: SC[0] }],
  },
  {
    ticker: "TLT",
    name: "iShares 20+ Yr Treasury",
    assetClass: "Fixed Income",
    region: "US",
    aum: "$42B",
    expenseRatio: 0.15,
    ytdReturn: -4.2,
    oneYReturn: -3.8,
    divYield: 4.28,
    topHoldings: [
      { name: "US 30Y", weight: 35.2 },
      { name: "US 25Y", weight: 28.4 },
      { name: "US 20Y", weight: 22.1 },
      { name: "US TIPS", weight: 8.5 },
      { name: "Cash", weight: 5.8 },
    ],
    sectors: [
      { name: "Long Treas", value: 86, color: SC[0] },
      { name: "TIPS", value: 9, color: SC[1] },
      { name: "Cash", value: 5, color: SC[2] },
    ],
  },
  {
    ticker: "XLF",
    name: "Financial Select SPDR",
    assetClass: "Equity",
    region: "US",
    aum: "$38B",
    expenseRatio: 0.09,
    ytdReturn: 8.4,
    oneYReturn: 32.1,
    divYield: 1.62,
    topHoldings: [
      { name: "BRK.B", weight: 13.8 },
      { name: "JPM", weight: 10.2 },
      { name: "V", weight: 8.1 },
      { name: "MA", weight: 6.9 },
      { name: "BAC", weight: 4.5 },
    ],
    sectors: [
      { name: "Banks", value: 30, color: SC[0] },
      { name: "Insurance", value: 20, color: SC[1] },
      { name: "Cap Mkts", value: 18, color: SC[2] },
      { name: "Fintech", value: 17, color: SC[3] },
      { name: "Other", value: 15, color: SC[4] },
    ],
  },
  {
    ticker: "XLK",
    name: "Technology Select SPDR",
    assetClass: "Equity",
    region: "US",
    aum: "$55B",
    expenseRatio: 0.09,
    ytdReturn: 11.2,
    oneYReturn: 38.5,
    divYield: 0.68,
    topHoldings: [
      { name: "MSFT", weight: 22.1 },
      { name: "AAPL", weight: 20.8 },
      { name: "NVDA", weight: 6.2 },
      { name: "AVGO", weight: 5.4 },
      { name: "CRM", weight: 3.1 },
    ],
    sectors: [
      { name: "Software", value: 38, color: SC[0] },
      { name: "Hardware", value: 28, color: SC[1] },
      { name: "Semis", value: 22, color: SC[2] },
      { name: "IT Svcs", value: 8, color: SC[3] },
      { name: "Other", value: 4, color: SC[4] },
    ],
  },
  {
    ticker: "VNQ",
    name: "Vanguard Real Estate",
    assetClass: "Equity",
    region: "US",
    aum: "$32B",
    expenseRatio: 0.12,
    ytdReturn: -2.1,
    oneYReturn: 8.5,
    divYield: 3.98,
    topHoldings: [
      { name: "PLD", weight: 8.2 },
      { name: "AMT", weight: 6.5 },
      { name: "EQIX", weight: 5.8 },
      { name: "WELL", weight: 4.2 },
      { name: "SPG", weight: 3.8 },
    ],
    sectors: [
      { name: "Specialized", value: 32, color: SC[0] },
      { name: "Residential", value: 18, color: SC[1] },
      { name: "Industrial", value: 15, color: SC[2] },
      { name: "Retail", value: 12, color: SC[3] },
      { name: "Other", value: 23, color: SC[4] },
    ],
  },
  {
    ticker: "EEM",
    name: "iShares MSCI EM",
    assetClass: "Equity",
    region: "Emerging",
    aum: "$18B",
    expenseRatio: 0.68,
    ytdReturn: 3.5,
    oneYReturn: 8.2,
    divYield: 2.55,
    topHoldings: [
      { name: "TSM", weight: 8.5 },
      { name: "TENCENT", weight: 4.2 },
      { name: "SAMSUNG", weight: 3.8 },
      { name: "ALIBABA", weight: 2.8 },
      { name: "RELIANCE", weight: 1.5 },
    ],
    sectors: [
      { name: "Tech", value: 28, color: SC[0] },
      { name: "Financials", value: 22, color: SC[1] },
      { name: "Cons Disc", value: 14, color: SC[2] },
      { name: "Materials", value: 8, color: SC[3] },
      { name: "Other", value: 28, color: SC[4] },
    ],
  },
  {
    ticker: "HYG",
    name: "iShares iBoxx HY Corp",
    assetClass: "Fixed Income",
    region: "US",
    aum: "$15B",
    expenseRatio: 0.49,
    ytdReturn: 1.8,
    oneYReturn: 10.2,
    divYield: 5.85,
    topHoldings: [
      { name: "CCL 5.75%", weight: 0.4 },
      { name: "T 4.75%", weight: 0.3 },
      { name: "F 6.1%", weight: 0.3 },
      { name: "HCA 5.5%", weight: 0.3 },
      { name: "DISH 7.75%", weight: 0.2 },
    ],
    sectors: [
      { name: "BB Rated", value: 50, color: SC[0] },
      { name: "B Rated", value: 35, color: SC[1] },
      { name: "CCC+", value: 12, color: SC[2] },
      { name: "Other", value: 3, color: SC[3] },
    ],
  },
  {
    ticker: "LQD",
    name: "iShares iBoxx IG Corp",
    assetClass: "Fixed Income",
    region: "US",
    aum: "$32B",
    expenseRatio: 0.14,
    ytdReturn: -0.5,
    oneYReturn: 4.2,
    divYield: 4.65,
    topHoldings: [
      { name: "JPM 4.5%", weight: 0.5 },
      { name: "AAPL 3.85%", weight: 0.4 },
      { name: "MSFT 3.5%", weight: 0.4 },
      { name: "GS 4.25%", weight: 0.3 },
      { name: "BAC 4.0%", weight: 0.3 },
    ],
    sectors: [
      { name: "A Rated", value: 42, color: SC[0] },
      { name: "BBB Rated", value: 48, color: SC[1] },
      { name: "AA Rated", value: 8, color: SC[2] },
      { name: "Other", value: 2, color: SC[3] },
    ],
  },
  {
    ticker: "ARKK",
    name: "ARK Innovation ETF",
    assetClass: "Equity",
    region: "US",
    aum: "$7.5B",
    expenseRatio: 0.75,
    ytdReturn: -5.2,
    oneYReturn: 22.8,
    divYield: 0.0,
    topHoldings: [
      { name: "TSLA", weight: 11.2 },
      { name: "COIN", weight: 8.5 },
      { name: "ROKU", weight: 7.8 },
      { name: "SQ", weight: 6.2 },
      { name: "PATH", weight: 5.5 },
    ],
    sectors: [
      { name: "Tech", value: 42, color: SC[0] },
      { name: "Healthcare", value: 28, color: SC[1] },
      { name: "Fintech", value: 18, color: SC[2] },
      { name: "Other", value: 12, color: SC[3] },
    ],
  },
];

const etfAssetClasses = ["All", "Equity", "Fixed Income", "Commodity"];
const etfRegions = ["All", "US", "International", "Emerging", "Global"];

// Map ETF tickers to underlying index symbols for live data enrichment
const ETF_INDEX_MAP: Record<string, string> = {
  SPY: "^GSPC",
  QQQ: "^IXIC",
  IWM: "^RUT",
  VTI: "^GSPC",
  VXUS: "^STOXX50E",
  EEM: "^HSI",
  XLF: "^GSPC",
  XLK: "^IXIC",
};

const BENCHMARK_SYMBOLS = ["^GSPC", "^IXIC", "^DJI", "^FTSE", "^N225"];

// ── Page Tabs ─────────────────────────────────────────────────────────────────

const PAGE_TABS = ["Asset Explorer", "ETF Explorer"];

// ── Sub-components ────────────────────────────────────────────────────────────

function AssetExplorerContent() {
  const { data: indicesData } = useIndices();
  const { data: _commoditiesData } = useCommodities();
  const { data: _fxData } = useFX();
  const usingFallback = !indicesData;
  const [activeAssetTab, setActiveAssetTab] = useState<AssetClass>("Equities");

  const tabs: AssetClass[] = [
    "Equities",
    "Fixed Income",
    "Commodities",
    "FX",
    "Crypto",
  ];

  return (
    <div>
      <p style={{ color: "#94A3B8", fontSize: 14, marginBottom: 16 }}>
        Cross-asset class overview &amp; correlations
      </p>

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

      {/* ── Asset Class Tabs ── */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveAssetTab(tab)}
            style={{
              padding: "8px 18px",
              borderRadius: 8,
              border:
                activeAssetTab === tab
                  ? "1px solid #10B981"
                  : "1px solid rgba(51,65,85,0.3)",
              backgroundColor:
                activeAssetTab === tab ? "rgba(16,185,129,0.12)" : "transparent",
              color: activeAssetTab === tab ? "#10B981" : "#94A3B8",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* ── Asset Grid ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {assetData[activeAssetTab].map((asset) => (
          <Card key={asset.ticker}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: 8,
              }}
            >
              <div>
                <div
                  style={{
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 12,
                    fontWeight: 700,
                    color: "#10B981",
                  }}
                >
                  {asset.ticker}
                </div>
                <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>
                  {asset.name}
                </div>
              </div>
              <span
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 11,
                  fontWeight: 600,
                  color: asset.change >= 0 ? "#10B981" : "#EF4444",
                }}
              >
                {asset.change >= 0 ? "+" : ""}
                {asset.change.toFixed(2)}%
              </span>
            </div>
            <div
              style={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 18,
                fontWeight: 700,
                marginBottom: 6,
              }}
            >
              {asset.price}
            </div>
            <div style={{ fontSize: 11, color: "#94A3B8", lineHeight: 1.4 }}>
              {asset.trend}
            </div>
          </Card>
        ))}
      </div>

      {/* ── Correlation Matrix ── */}
      <Card
        title="Asset Class Correlation Matrix"
        subtitle="Rolling 1-year correlations"
      >
        <div style={{ display: "inline-block" }}>
          {/* Header row */}
          <div style={{ display: "flex" }}>
            <div style={{ width: 100 }} />
            {correlationLabels.map((label) => (
              <div
                key={label}
                style={{
                  width: 90,
                  textAlign: "center",
                  fontSize: 10,
                  color: "#94A3B8",
                  fontFamily: "JetBrains Mono, monospace",
                  padding: "4px 0",
                }}
              >
                {label.length > 7 ? label.slice(0, 7) : label}
              </div>
            ))}
          </div>
          {/* Data rows */}
          {correlationMatrix.map((row, ri) => (
            <div key={ri} style={{ display: "flex", alignItems: "center" }}>
              <div
                style={{
                  width: 100,
                  fontSize: 11,
                  color: "#94A3B8",
                  fontFamily: "JetBrains Mono, monospace",
                  paddingRight: 8,
                  textAlign: "right",
                }}
              >
                {correlationLabels[ri].length > 10
                  ? correlationLabels[ri].slice(0, 10)
                  : correlationLabels[ri]}
              </div>
              {row.map((val, ci) => (
                <div
                  key={ci}
                  style={{
                    width: 90,
                    height: 40,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    backgroundColor: corrColor(val),
                    borderRadius: 4,
                    margin: 1,
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 12,
                    fontWeight: 600,
                    color: Math.abs(val) > 0.3 ? "#F1F5F9" : "#94A3B8",
                  }}
                >
                  {val.toFixed(2)}
                </div>
              ))}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function ETFExplorerContent() {
  const { data: indicesData } = useIndices();
  const usingFallback = !indicesData;

  const [search, setSearch] = useState("");
  const [assetClassFilter, setAssetClassFilter] = useState("All");
  const [regionFilter, setRegionFilter] = useState("All");
  const [maxER, setMaxER] = useState(1.0);
  const [expanded, setExpanded] = useState<string | null>(null);

  // Live daily change for ETFs mapped to indices
  const liveChanges = useMemo(() => {
    if (!indicesData) return new Map<string, number>();
    const allItems = Object.values(indicesData).flat();
    const map = new Map<string, number>();
    for (const [etfTicker, indexSymbol] of Object.entries(ETF_INDEX_MAP)) {
      const match = allItems.find((idx) => idx.symbol === indexSymbol);
      if (match) map.set(etfTicker, match.change.percent);
    }
    return map;
  }, [indicesData]);

  // Key market benchmarks for context
  const benchmarks = useMemo(() => {
    if (!indicesData) return [];
    return Object.values(indicesData)
      .flat()
      .filter((idx) => BENCHMARK_SYMBOLS.includes(idx.symbol));
  }, [indicesData]);

  const filtered = useMemo(() => {
    return etfs.filter((e) => {
      if (
        search &&
        !e.ticker.toLowerCase().includes(search.toLowerCase()) &&
        !e.name.toLowerCase().includes(search.toLowerCase())
      )
        return false;
      if (assetClassFilter !== "All" && e.assetClass !== assetClassFilter)
        return false;
      if (regionFilter !== "All" && e.region !== regionFilter) return false;
      if (e.expenseRatio > maxER) return false;
      return true;
    });
  }, [search, assetClassFilter, regionFilter, maxER]);

  const selectStyle: React.CSSProperties = {
    padding: "8px 12px",
    borderRadius: 6,
    border: "1px solid rgba(51,65,85,0.3)",
    backgroundColor: "#0A0E1A",
    color: "#F1F5F9",
    fontFamily: "JetBrains Mono, monospace",
    fontSize: 12,
    outline: "none",
  };

  return (
    <div>
      <p style={{ color: "#94A3B8", fontSize: 14, marginBottom: 16 }}>
        Screen &amp; analyze exchange-traded funds
      </p>

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

      {/* ── Market Benchmarks ── */}
      {benchmarks.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: 10,
            marginBottom: 16,
            flexWrap: "wrap",
          }}
        >
          {benchmarks.map((idx) => (
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
              <div style={{ fontSize: 11, color: "#94A3B8" }}>{idx.name}</div>
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
                    color: idx.change.percent >= 0 ? "#10B981" : "#EF4444",
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

      {/* ── Filters ── */}
      <Card>
        <div
          style={{
            display: "flex",
            gap: 12,
            alignItems: "flex-end",
            flexWrap: "wrap",
          }}
        >
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}>
              Search
            </div>
            <input
              placeholder="Ticker or name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ ...selectStyle, width: "100%" }}
            />
          </div>
          <div>
            <div style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}>
              Asset Class
            </div>
            <select
              value={assetClassFilter}
              onChange={(e) => setAssetClassFilter(e.target.value)}
              style={selectStyle}
            >
              {etfAssetClasses.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </div>
          <div>
            <div style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}>
              Region
            </div>
            <select
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value)}
              style={selectStyle}
            >
              {etfRegions.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div>
            <div style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}>
              Max ER: {maxER.toFixed(2)}%
            </div>
            <input
              type="range"
              min="0.01"
              max="1.0"
              step="0.01"
              value={maxER}
              onChange={(e) => setMaxER(Number(e.target.value))}
              style={{ width: 120, accentColor: "#10B981" }}
            />
          </div>
        </div>
      </Card>

      {/* ── Table ── */}
      <div style={{ marginTop: 16 }}>
        <Card>
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
                    "Ticker",
                    "Name",
                    "AUM",
                    "ER (%)",
                    "YTD (%)",
                    "1Y (%)",
                    "Live Δ%",
                    "Div Yield (%)",
                  ].map((h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: "left",
                        padding: "8px 10px",
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
                {filtered.map((etf) => {
                  const isExpanded = expanded === etf.ticker;
                  return (
                    <tr key={etf.ticker} style={{ verticalAlign: "top" }}>
                      <td colSpan={8} style={{ padding: 0 }}>
                        {/* Main row */}
                        <div
                          onClick={() =>
                            setExpanded(isExpanded ? null : etf.ticker)
                          }
                          style={{
                            display: "grid",
                            gridTemplateColumns:
                              "80px 1fr 80px 70px 80px 80px 80px 100px",
                            cursor: "pointer",
                            borderBottom: "1px solid rgba(51,65,85,0.15)",
                            backgroundColor: isExpanded
                              ? "rgba(16,185,129,0.05)"
                              : "transparent",
                          }}
                        >
                          <div
                            style={{
                              padding: "10px",
                              fontFamily: "JetBrains Mono, monospace",
                              fontWeight: 700,
                              color: "#10B981",
                            }}
                          >
                            {etf.ticker}
                          </div>
                          <div style={{ padding: "10px" }}>{etf.name}</div>
                          <div
                            style={{
                              padding: "10px",
                              fontFamily: "JetBrains Mono, monospace",
                            }}
                          >
                            {etf.aum}
                          </div>
                          <div
                            style={{
                              padding: "10px",
                              fontFamily: "JetBrains Mono, monospace",
                            }}
                          >
                            {etf.expenseRatio.toFixed(2)}
                          </div>
                          <div
                            style={{
                              padding: "10px",
                              fontFamily: "JetBrains Mono, monospace",
                              color:
                                etf.ytdReturn >= 0 ? "#10B981" : "#EF4444",
                            }}
                          >
                            {etf.ytdReturn >= 0 ? "+" : ""}
                            {etf.ytdReturn.toFixed(1)}
                          </div>
                          <div
                            style={{
                              padding: "10px",
                              fontFamily: "JetBrains Mono, monospace",
                              color:
                                etf.oneYReturn >= 0 ? "#10B981" : "#EF4444",
                            }}
                          >
                            {etf.oneYReturn >= 0 ? "+" : ""}
                            {etf.oneYReturn.toFixed(1)}
                          </div>
                          <div
                            style={{
                              padding: "10px",
                              fontFamily: "JetBrains Mono, monospace",
                              color: liveChanges.has(etf.ticker)
                                ? liveChanges.get(etf.ticker)! >= 0
                                  ? "#10B981"
                                  : "#EF4444"
                                : "#64748B",
                            }}
                          >
                            {liveChanges.has(etf.ticker)
                              ? `${liveChanges.get(etf.ticker)! >= 0 ? "+" : ""}${liveChanges.get(etf.ticker)!.toFixed(2)}`
                              : "—"}
                          </div>
                          <div
                            style={{
                              padding: "10px",
                              fontFamily: "JetBrains Mono, monospace",
                            }}
                          >
                            {etf.divYield.toFixed(2)}
                          </div>
                        </div>
                        {/* Expanded detail */}
                        {isExpanded && (
                          <div
                            style={{
                              padding: "12px 10px",
                              backgroundColor: "rgba(16,185,129,0.03)",
                              borderBottom: "1px solid rgba(51,65,85,0.15)",
                            }}
                          >
                            <div style={{ display: "flex", gap: 32 }}>
                              {/* Top Holdings */}
                              <div style={{ flex: 1 }}>
                                <div
                                  style={{
                                    fontSize: 12,
                                    fontWeight: 600,
                                    color: "#10B981",
                                    marginBottom: 8,
                                  }}
                                >
                                  Top 5 Holdings
                                </div>
                                {etf.topHoldings
                                  .filter((h) => h.name !== "")
                                  .map((h) => (
                                    <div
                                      key={h.name}
                                      style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        padding: "4px 0",
                                        fontSize: 12,
                                      }}
                                    >
                                      <span
                                        style={{
                                          fontFamily:
                                            "JetBrains Mono, monospace",
                                        }}
                                      >
                                        {h.name}
                                      </span>
                                      <span
                                        style={{
                                          color: "#94A3B8",
                                          fontFamily:
                                            "JetBrains Mono, monospace",
                                        }}
                                      >
                                        {h.weight.toFixed(1)}%
                                      </span>
                                    </div>
                                  ))}
                              </div>
                              {/* Sector Breakdown */}
                              <div style={{ width: 250 }}>
                                <div
                                  style={{
                                    fontSize: 12,
                                    fontWeight: 600,
                                    color: "#10B981",
                                    marginBottom: 8,
                                  }}
                                >
                                  Sector Breakdown
                                </div>
                                <ResponsiveContainer width="100%" height={150}>
                                  <PieChart>
                                    <Pie
                                      data={etf.sectors}
                                      cx="50%"
                                      cy="50%"
                                      innerRadius={35}
                                      outerRadius={60}
                                      dataKey="value"
                                      stroke="none"
                                    >
                                      {etf.sectors.map((s, i) => (
                                        <Cell key={i} fill={s.color} />
                                      ))}
                                    </Pie>
                                    <Tooltip
                                      contentStyle={{
                                        backgroundColor: "#131823",
                                        border:
                                          "1px solid rgba(51,65,85,0.3)",
                                        borderRadius: 8,
                                        color: "#F1F5F9",
                                        fontSize: 12,
                                      }}
                                      formatter={(v: any, name: any) => [
                                        `${v}%`,
                                        name,
                                      ]}
                                    />
                                  </PieChart>
                                </ResponsiveContainer>
                                <div
                                  style={{
                                    display: "flex",
                                    flexWrap: "wrap",
                                    gap: 8,
                                    marginTop: 4,
                                  }}
                                >
                                  {etf.sectors.map((s) => (
                                    <div
                                      key={s.name}
                                      style={{
                                        display: "flex",
                                        alignItems: "center",
                                        gap: 4,
                                        fontSize: 10,
                                      }}
                                    >
                                      <div
                                        style={{
                                          width: 8,
                                          height: 8,
                                          borderRadius: 2,
                                          backgroundColor: s.color,
                                        }}
                                      />
                                      <span style={{ color: "#94A3B8" }}>
                                        {s.name}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div
            style={{
              color: "#94A3B8",
              fontSize: 11,
              marginTop: 12,
              textAlign: "right",
            }}
          >
            Showing {filtered.length} of {etfs.length} ETFs
          </div>
        </Card>
      </div>
    </div>
  );
}

// ── Component ────────────────────────────────────────────────────────────────

export default function AssetExplorer() {
  const [activeTab, setActiveTab] = useState(PAGE_TABS[0]);

  return (
    <div style={{ color: "#F1F5F9", minHeight: "100vh" }}>
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 16,
        }}
      >
        Asset Explorer
      </h1>

      <Tabs tabs={PAGE_TABS} active={activeTab} onChange={setActiveTab} />

      <div style={{ marginTop: 20 }}>
        {activeTab === "Asset Explorer" && <AssetExplorerContent />}
        {activeTab === "ETF Explorer" && <ETFExplorerContent />}
      </div>
    </div>
  );
}
