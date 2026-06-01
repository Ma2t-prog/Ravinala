import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Card, Tabs } from "../components/ui";
import { useFX } from "../hooks/useMarketData";

// ─── Design tokens ────────────────────────────────────────────────────────────
const GOLD = "#D4AF37";
const CYAN = "#00D9FF";
const GREEN = "#10B981";
const RED = "#EF4444";
const AMBER = "#F59E0B";
const PURPLE = "#A855F7";
const BLUE = "#3B82F6";
const MUTED = "#94A3B8";
const DIM = "#64748B";
const _BG_CARD = "#131823";
const MONO = "JetBrains Mono, monospace";

const fmt = (n: number) =>
  n.toLocaleString("fr-FR", { maximumFractionDigits: 0 });
const fmtPct = (n: number) => `${(n * 100).toFixed(1)}%`;
const fmtEur = (n: number) => `€${fmt(n)}`;

// ─── TAX RULES DATABASE ──────────────────────────────────────────────────────
interface TaxRules {
  cgt_flat: number;
  social: number;
  div_flat: number;
  div_abatt: number;
  wash_sale: boolean;
  wash_days: number;
  envelopes: string[];
  brackets: number[];
  rates: number[];
  estate_exempt_child: number;
  estate_exempt_spouse: boolean;
  currency: string;
  flag: string;
}

const TAX_RULES: Record<string, TaxRules> = {
  France: {
    cgt_flat: 0.3,
    social: 0.172,
    div_flat: 0.3,
    div_abatt: 0.4,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["PEA", "PEA-PME", "AV", "PER", "CTO"],
    brackets: [0, 11294, 28797, 82341, 177106],
    rates: [0.0, 0.11, 0.3, 0.41, 0.45],
    estate_exempt_child: 100000,
    estate_exempt_spouse: true,
    currency: "EUR",
    flag: "🇫🇷",
  },
  USA: {
    cgt_flat: 0.2,
    social: 0.038,
    div_flat: 0.2,
    div_abatt: 0.0,
    wash_sale: true,
    wash_days: 30,
    envelopes: ["401(k)", "IRA", "Roth IRA", "HSA", "Taxable"],
    brackets: [0, 11600, 47150, 100525, 191950, 243725, 609350],
    rates: [0.1, 0.12, 0.22, 0.24, 0.32, 0.35, 0.37],
    estate_exempt_child: 13610000,
    estate_exempt_spouse: true,
    currency: "USD",
    flag: "🇺🇸",
  },
  UK: {
    cgt_flat: 0.2,
    social: 0.0,
    div_flat: 0.3375,
    div_abatt: 0.0,
    wash_sale: true,
    wash_days: 30,
    envelopes: ["ISA", "SIPP", "LISA", "GIA"],
    brackets: [0, 12570, 50270, 125140],
    rates: [0.0, 0.2, 0.4, 0.45],
    estate_exempt_child: 500000,
    estate_exempt_spouse: true,
    currency: "GBP",
    flag: "🇬🇧",
  },
  Germany: {
    cgt_flat: 0.26375,
    social: 0.0,
    div_flat: 0.26375,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["Riester", "Rürup", "Depot"],
    brackets: [0, 11604, 17006, 66761, 277826],
    rates: [0.0, 0.14, 0.2397, 0.42, 0.45],
    estate_exempt_child: 400000,
    estate_exempt_spouse: true,
    currency: "EUR",
    flag: "🇩🇪",
  },
  Switzerland: {
    cgt_flat: 0.0,
    social: 0.0,
    div_flat: 0.35,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["Pilier 2", "Pilier 3a", "Dépôt"],
    brackets: [
      0, 17800, 31600, 41400, 55200, 72500, 78100, 103600, 134600, 176000,
      755200,
    ],
    rates: [
      0.0, 0.0077, 0.0088, 0.0266, 0.0229, 0.0256, 0.0304, 0.0511, 0.0611,
      0.0833, 0.115,
    ],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "CHF",
    flag: "🇨🇭",
  },
  Singapore: {
    cgt_flat: 0.0,
    social: 0.0,
    div_flat: 0.0,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["CPF", "SRS", "Brokerage"],
    brackets: [
      0, 20000, 30000, 40000, 80000, 120000, 160000, 200000, 240000, 280000,
      320000,
    ],
    rates: [0.0, 0.02, 0.035, 0.07, 0.115, 0.15, 0.18, 0.19, 0.195, 0.2, 0.22],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "SGD",
    flag: "🇸🇬",
  },
  UAE: {
    cgt_flat: 0.0,
    social: 0.0,
    div_flat: 0.0,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["DIFC", "Brokerage"],
    brackets: [0],
    rates: [0.0],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "AED",
    flag: "🇦🇪",
  },
  Belgium: {
    cgt_flat: 0.0,
    social: 0.0,
    div_flat: 0.3,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["Épargne-pension", "Assurance-groupe", "CTO"],
    brackets: [0, 15200, 26830, 46440],
    rates: [0.25, 0.4, 0.45, 0.5],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "EUR",
    flag: "🇧🇪",
  },
  Netherlands: {
    cgt_flat: 0.36,
    social: 0.0,
    div_flat: 0.2617,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["Pensioen", "Brokerage"],
    brackets: [0, 75518, 0],
    rates: [0.3693, 0.495],
    estate_exempt_child: 22918,
    estate_exempt_spouse: true,
    currency: "EUR",
    flag: "🇳🇱",
  },
  Portugal: {
    cgt_flat: 0.28,
    social: 0.0,
    div_flat: 0.28,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["PPR", "CTO"],
    brackets: [0, 7703, 11623, 16472, 21321, 27146, 39791, 51997, 81199],
    rates: [0.1325, 0.18, 0.23, 0.26, 0.3275, 0.37, 0.435, 0.45, 0.48],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "EUR",
    flag: "🇵🇹",
  },
  Luxembourg: {
    cgt_flat: 0.2,
    social: 0.0,
    div_flat: 0.15,
    div_abatt: 0.5,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["Épargne-prévoyance", "AV", "CTO"],
    brackets: [
      0, 11265, 13173, 15081, 16989, 18897, 20805, 22713, 24621, 26529,
    ],
    rates: [0.0, 0.08, 0.1, 0.12, 0.14, 0.16, 0.18, 0.2, 0.22, 0.24],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "EUR",
    flag: "🇱🇺",
  },
  "Hong Kong": {
    cgt_flat: 0.0,
    social: 0.0,
    div_flat: 0.0,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["MPF", "Brokerage"],
    brackets: [0, 50000, 100000, 150000, 200000],
    rates: [0.02, 0.06, 0.1, 0.14, 0.17],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "HKD",
    flag: "🇭🇰",
  },
  Japan: {
    cgt_flat: 0.20315,
    social: 0.0,
    div_flat: 0.20315,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["NISA", "iDeCo", "Tokutei"],
    brackets: [0, 1950000, 3300000, 6950000, 9000000, 18000000, 40000000],
    rates: [0.05, 0.1, 0.2, 0.23, 0.33, 0.4, 0.45],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "JPY",
    flag: "🇯🇵",
  },
  Italy: {
    cgt_flat: 0.26,
    social: 0.0,
    div_flat: 0.26,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["PIR", "Fondo Pensione", "CTO"],
    brackets: [0, 15000, 28000, 50000, 75000],
    rates: [0.23, 0.25, 0.35, 0.43, 0.43],
    estate_exempt_child: 1000000,
    estate_exempt_spouse: true,
    currency: "EUR",
    flag: "🇮🇹",
  },
  Spain: {
    cgt_flat: 0.26,
    social: 0.0,
    div_flat: 0.26,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["Plan de Pensiones", "CTO"],
    brackets: [0, 12450, 20200, 35200, 60000, 300000],
    rates: [0.19, 0.24, 0.3, 0.37, 0.45, 0.47],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "EUR",
    flag: "🇪🇸",
  },
  Ireland: {
    cgt_flat: 0.33,
    social: 0.04,
    div_flat: 0.33,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["PRSA", "ARF", "CTO"],
    brackets: [0, 42000],
    rates: [0.2, 0.4],
    estate_exempt_child: 335000,
    estate_exempt_spouse: true,
    currency: "EUR",
    flag: "🇮🇪",
  },
  Canada: {
    cgt_flat: 0.267,
    social: 0.0,
    div_flat: 0.3912,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["RRSP", "TFSA", "FHSA", "Taxable"],
    brackets: [0, 55867, 111733, 154906, 220000],
    rates: [0.15, 0.205, 0.26, 0.29, 0.33],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "CAD",
    flag: "🇨🇦",
  },
  Australia: {
    cgt_flat: 0.235,
    social: 0.0,
    div_flat: 0.0,
    div_abatt: 0.0,
    wash_sale: false,
    wash_days: 0,
    envelopes: ["Super", "Taxable"],
    brackets: [0, 18200, 45000, 120000, 180000],
    rates: [0.0, 0.19, 0.325, 0.37, 0.45],
    estate_exempt_child: 0,
    estate_exempt_spouse: true,
    currency: "AUD",
    flag: "🇦🇺",
  },
};

const COUNTRIES = Object.keys(TAX_RULES);

// ─── PORTFOLIO DEMO DATA ──────────────────────────────────────────────────────
interface Position {
  ticker: string;
  name: string;
  shares: number;
  costBasis: number;
  current: number;
  sector: string;
  envelope: string;
  holdDays: number;
}

const POSITIONS: Position[] = [
  {
    ticker: "AAPL",
    name: "Apple Inc.",
    shares: 50,
    costBasis: 142.5,
    current: 198.3,
    sector: "Tech",
    envelope: "CTO",
    holdDays: 847,
  },
  {
    ticker: "MSFT",
    name: "Microsoft Corp.",
    shares: 30,
    costBasis: 285.0,
    current: 425.8,
    sector: "Tech",
    envelope: "CTO",
    holdDays: 612,
  },
  {
    ticker: "NVDA",
    name: "NVIDIA Corp.",
    shares: 20,
    costBasis: 480.0,
    current: 875.6,
    sector: "Tech",
    envelope: "PEA",
    holdDays: 389,
  },
  {
    ticker: "VOO",
    name: "Vanguard S&P 500",
    shares: 100,
    costBasis: 380.0,
    current: 502.4,
    sector: "ETF",
    envelope: "PEA",
    holdDays: 1204,
  },
  {
    ticker: "VWRL",
    name: "Vanguard FTSE All-World",
    shares: 80,
    costBasis: 92.0,
    current: 115.2,
    sector: "ETF",
    envelope: "PEA",
    holdDays: 965,
  },
  {
    ticker: "META",
    name: "Meta Platforms",
    shares: 15,
    costBasis: 290.0,
    current: 505.4,
    sector: "Tech",
    envelope: "CTO",
    holdDays: 478,
  },
  {
    ticker: "TSLA",
    name: "Tesla Inc.",
    shares: 25,
    costBasis: 245.0,
    current: 178.5,
    sector: "Auto",
    envelope: "CTO",
    holdDays: 534,
  },
  {
    ticker: "INTC",
    name: "Intel Corp.",
    shares: 80,
    costBasis: 38.5,
    current: 22.4,
    sector: "Semi",
    envelope: "CTO",
    holdDays: 756,
  },
  {
    ticker: "MMM",
    name: "3M Company",
    shares: 40,
    costBasis: 118.0,
    current: 95.6,
    sector: "Industrial",
    envelope: "CTO",
    holdDays: 445,
  },
  {
    ticker: "BNP.PA",
    name: "BNP Paribas",
    shares: 60,
    costBasis: 62.0,
    current: 54.8,
    sector: "Banks",
    envelope: "PEA",
    holdDays: 623,
  },
  {
    ticker: "ASML",
    name: "ASML Holding",
    shares: 10,
    costBasis: 720.0,
    current: 645.3,
    sector: "Semi",
    envelope: "PEA",
    holdDays: 312,
  },
  {
    ticker: "AMZN",
    name: "Amazon.com",
    shares: 20,
    costBasis: 145.0,
    current: 192.8,
    sector: "Tech",
    envelope: "CTO",
    holdDays: 289,
  },
  {
    ticker: "LVMH.PA",
    name: "LVMH",
    shares: 8,
    costBasis: 780.0,
    current: 856.4,
    sector: "Luxury",
    envelope: "PEA",
    holdDays: 1045,
  },
];

// TLH replacement database
const TLH_REPLACEMENTS: Record<string, { alt: string; corr: number }[]> = {
  TSLA: [
    { alt: "DRIV", corr: 0.78 },
    { alt: "KARS", corr: 0.74 },
  ],
  INTC: [
    { alt: "SOXX", corr: 0.82 },
    { alt: "SMH", corr: 0.84 },
  ],
  MMM: [
    { alt: "XLI", corr: 0.76 },
    { alt: "VIS", corr: 0.72 },
  ],
  "BNP.PA": [
    { alt: "EUFN", corr: 0.8 },
    { alt: "IXG", corr: 0.71 },
  ],
  ASML: [
    { alt: "SOXX", corr: 0.78 },
    { alt: "SEMI", corr: 0.8 },
  ],
};

// Envelope rules for France
const ENVELOPE_RULES = [
  {
    name: "PEA",
    limit: 150000,
    bestFor: "EU/EEA stocks, MSCI World synthetic ETFs",
    avoid: "US stocks directly, obligations, REITs",
    advantage: "0% IR after 5 years (only social 17.2%)",
    lockYears: 5,
  },
  {
    name: "PEA-PME",
    limit: 225000,
    bestFor: "French/EU SME stocks, innovation funds",
    avoid: "Large caps, non-EU",
    advantage: "Same as PEA for SME focus",
    lockYears: 5,
  },
  {
    name: "AV",
    limit: null,
    bestFor: "Bonds, dividend stocks, REITs, diversified",
    avoid: "Highly volatile assets",
    advantage: "€4,600/yr exemption after 8 years",
    lockYears: 8,
  },
  {
    name: "PER",
    limit: null,
    bestFor: "Growth stocks, long-term compounding",
    avoid: "Need for liquidity before retirement",
    advantage: "Contributions deductible from income (10%)",
    lockYears: 0,
  },
  {
    name: "CTO",
    limit: null,
    bestFor: "US stocks, TLH candidates, volatile assets",
    avoid: "High-dividend stocks (taxed 30%)",
    advantage: "No restrictions, no wash-sale in France",
    lockYears: 0,
  },
];

// Treaty database
const TREATIES: {
  from: string;
  to: string;
  div: number;
  interest: number;
  royalties: number;
}[] = [
  { from: "USA", to: "France", div: 0.15, interest: 0.0, royalties: 0.0 },
  { from: "USA", to: "UK", div: 0.15, interest: 0.0, royalties: 0.0 },
  { from: "Germany", to: "France", div: 0.15, interest: 0.0, royalties: 0.05 },
  { from: "France", to: "UK", div: 0.15, interest: 0.0, royalties: 0.0 },
  {
    from: "France",
    to: "Switzerland",
    div: 0.15,
    interest: 0.0,
    royalties: 0.05,
  },
  {
    from: "France",
    to: "Luxembourg",
    div: 0.15,
    interest: 0.0,
    royalties: 0.0,
  },
  { from: "UK", to: "USA", div: 0.15, interest: 0.0, royalties: 0.0 },
  { from: "Germany", to: "USA", div: 0.15, interest: 0.0, royalties: 0.0 },
  {
    from: "Switzerland",
    to: "France",
    div: 0.15,
    interest: 0.0,
    royalties: 0.05,
  },
  { from: "France", to: "Singapore", div: 0.15, interest: 0.0, royalties: 0.0 },
  { from: "France", to: "Belgium", div: 0.15, interest: 0.15, royalties: 0.0 },
  {
    from: "France",
    to: "Netherlands",
    div: 0.15,
    interest: 0.0,
    royalties: 0.0,
  },
  { from: "Italy", to: "France", div: 0.15, interest: 0.1, royalties: 0.05 },
  { from: "Spain", to: "France", div: 0.15, interest: 0.1, royalties: 0.05 },
];

// Exit tax rules
const EXIT_TAX: Record<
  string,
  { threshold: string; rate: string; notes: string }
> = {
  France: {
    threshold: "€800,000 unrealized gains",
    rate: "30% PFU (art. 150-0 B ter CGI)",
    notes:
      "Deferred if moving to EU/EEA. Definitive if >2 years out of France.",
  },
  Germany: {
    threshold: ">1% holding in any company",
    rate: "Standard income tax on deemed disposal",
    notes: "Wegzugsbesteuerung — can be deferred within EU.",
  },
  Spain: {
    threshold: "€4,000,000 net worth or 25%+ holding",
    rate: "26% on unrealized gains",
    notes: "Applies if resident ≥10 of last 15 years.",
  },
  Netherlands: {
    threshold: "Any unrealized gains",
    rate: "Box 2: 26.9%, Box 3: fictitious yield",
    notes: "Can be reclaimed if you return within 10 years.",
  },
  USA: {
    threshold: "$886,000 avg. tax liability (5yr) or NW >$2M",
    rate: "Mark-to-market on all assets",
    notes: "Covered expatriate rules, no return option.",
  },
  Norway: {
    threshold: "Any unrealized gains on shares",
    rate: "37.84% (2024)",
    notes: "5-year deferred payment plan if moving to EU/EEA.",
  },
};

// Succession brackets France
const SUCCESSION_FR = [
  { lo: 0, hi: 8072, rate: 0.05 },
  { lo: 8072, hi: 12109, rate: 0.1 },
  { lo: 12109, hi: 15932, rate: 0.15 },
  { lo: 15932, hi: 552324, rate: 0.2 },
  { lo: 552324, hi: 902838, rate: 0.3 },
  { lo: 902838, hi: 1805677, rate: 0.4 },
  { lo: 1805677, hi: Infinity, rate: 0.45 },
];

// ─── HELPER: French TMI ──────────────────────────────────────────────────────
function computeTMI(income: number, parts: number, rules: TaxRules) {
  const qi = income / parts;
  let tax = 0,
    tmi = 0;
  for (let i = 0; i < rules.rates.length; i++) {
    const lo = rules.brackets[i];
    const hi = i + 1 < rules.brackets.length ? rules.brackets[i + 1] : 1e9;
    if (qi > lo) {
      tax += (Math.min(qi, hi) - lo) * rules.rates[i];
      tmi = rules.rates[i];
    }
  }
  return { tax: tax * parts, tmi };
}

function computeSuccessionFR(netEstate: number, children: number) {
  if (children === 0) return netEstate * 0.6;
  const perChild = netEstate / children;
  const exempt = 100000;
  let totalTax = 0;
  for (let c = 0; c < children; c++) {
    const taxable = Math.max(0, perChild - exempt);
    let tax = 0;
    for (const b of SUCCESSION_FR) {
      if (taxable > b.lo) {
        tax += (Math.min(taxable, b.hi) - b.lo) * b.rate;
      }
    }
    totalTax += tax;
  }
  return totalTax;
}

// ─── Seeded RNG for Monte Carlo ───────────────────────────────────────────────
function seededRng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return s / 2147483647;
  };
}

// ─── Styled helpers ───────────────────────────────────────────────────────────
const MetricBox = ({
  label,
  value,
  color = CYAN,
}: {
  label: string;
  value: string;
  color?: string;
}) => (
  <div
    style={{
      background: "rgba(15,23,42,0.6)",
      border: "1px solid rgba(51,65,85,0.3)",
      borderRadius: 8,
      padding: "10px 16px",
      minWidth: 120,
    }}
  >
    <div style={{ fontSize: 11, color: DIM, marginBottom: 2 }}>{label}</div>
    <div style={{ fontFamily: MONO, fontSize: 18, fontWeight: 700, color }}>
      {value}
    </div>
  </div>
);

const _SectionTitle = ({ children }: { children: React.ReactNode }) => (
  <h3
    style={{
      fontFamily: MONO,
      fontSize: 14,
      color: GOLD,
      marginBottom: 8,
      marginTop: 20,
      letterSpacing: "0.03em",
    }}
  >
    {children}
  </h3>
);

const Select = ({
  value,
  onChange,
  options,
  width = 200,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  width?: number;
}) => (
  <select
    value={value}
    onChange={(e) => onChange(e.target.value)}
    style={{
      background: "#1E293B",
      border: "1px solid rgba(51,65,85,0.4)",
      borderRadius: 6,
      padding: "8px 12px",
      color: "#F1F5F9",
      fontSize: 13,
      width,
      fontFamily: MONO,
      cursor: "pointer",
      outline: "none",
    }}
  >
    {options.map((o) => (
      <option key={o} value={o}>
        {o}
      </option>
    ))}
  </select>
);

const Slider = ({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  fmt: fmtFn,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  fmt?: (n: number) => string;
}) => (
  <div style={{ marginBottom: 12 }}>
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        marginBottom: 4,
      }}
    >
      <span style={{ fontSize: 12, color: MUTED }}>{label}</span>
      <span style={{ fontSize: 12, fontFamily: MONO, color: CYAN }}>
        {fmtFn ? fmtFn(value) : value}
      </span>
    </div>
    <input
      type="range"
      min={min}
      max={max}
      step={step}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      style={{ width: "100%", accentColor: GOLD }}
    />
  </div>
);

const ChipButton = ({
  label,
  active,
  onClick,
  color = GOLD,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  color?: string;
}) => (
  <button
    onClick={onClick}
    style={{
      background: active ? `${color}22` : "rgba(51,65,85,0.2)",
      border: `1px solid ${active ? `${color}88` : "rgba(51,65,85,0.4)"}`,
      borderRadius: 20,
      padding: "5px 14px",
      fontSize: 12,
      cursor: "pointer",
      color: active ? color : MUTED,
      fontFamily: MONO,
      transition: "all 0.15s",
    }}
  >
    {label}
  </button>
);

const TT = ({ children }: { children: React.ReactNode }) => (
  <div
    style={{
      backgroundColor: "#131823",
      border: "1px solid rgba(51,65,85,0.4)",
      borderRadius: 8,
      padding: "8px 12px",
      boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
    }}
  >
    {children}
  </div>
);

// ─── TAB NAMES ────────────────────────────────────────────────────────────────
const TAB_NAMES = [
  "Tax Profile",
  "Dashboard",
  "Tax-Loss Harvesting",
  "Envelope Optimizer",
  "Scenario Lab",
  "Estate Planner",
  "Multi-Jurisdiction",
  "Compliance",
];

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════
export default function TaxLab() {
  const { data: _fxData } = useFX();
  const [activeTab, setActiveTab] = useState(TAB_NAMES[0]);

  // ─ Profile state
  const [country, setCountry] = useState("France");
  const [income, setIncome] = useState(85000);
  const [parts, setParts] = useState(2);
  const [investable, setInvestable] = useState(250000);

  // ─ TLH state
  const [lossThreshold, setLossThreshold] = useState(-10);
  const [txCostBps, setTxCostBps] = useState(10);

  // ─ Scenario state
  const [scenarioType, setScenarioType] = useState(0);
  const [mcVol, setMcVol] = useState(18);
  const [mcYears, setMcYears] = useState(20);

  // ─ Estate state
  const [estateValue, setEstateValue] = useState(2000000);
  const [numChildren, setNumChildren] = useState(2);
  const [avAmount, setAvAmount] = useState(400000);

  // ─ Multi-jurisdiction state
  const [daysCountry, setDaysCountry] = useState<Record<string, number>>({
    France: 200,
    USA: 80,
    UK: 50,
    Singapore: 35,
  });
  const [exitCountry, setExitCountry] = useState("France");
  const [exitGains, setExitGains] = useState(1500000);

  const rules = TAX_RULES[country];
  const { tax: incomeTax, tmi } = computeTMI(income, parts, rules);

  // ─ Portfolio calculations
  const positions = useMemo(
    () =>
      POSITIONS.map((p) => {
        const pnl = (p.current - p.costBasis) * p.shares;
        const pnlPct = (p.current - p.costBasis) / p.costBasis;
        const taxImpact = pnl > 0 ? pnl * rules.cgt_flat : 0;
        return { ...p, pnl, pnlPct, taxImpact };
      }),
    [rules],
  );

  const totalValue = positions.reduce((s, p) => s + p.current * p.shares, 0);
  const totalPnL = positions.reduce((s, p) => s + p.pnl, 0);
  const totalTax = positions
    .filter((p) => p.pnl > 0)
    .reduce((s, p) => s + p.taxImpact, 0);
  const harvestable = positions.filter((p) => p.pnlPct * 100 <= lossThreshold);
  const harvestableValue = harvestable.reduce((s, p) => s + Math.abs(p.pnl), 0);
  const taxSaved = harvestableValue * rules.cgt_flat;

  // Allocation by envelope
  const envelopeAlloc = useMemo(() => {
    const map: Record<string, number> = {};
    positions.forEach((p) => {
      map[p.envelope] = (map[p.envelope] || 0) + p.current * p.shares;
    });
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  }, [positions]);

  const PIE_COLORS = [GOLD, CYAN, GREEN, PURPLE, AMBER, BLUE, RED];

  return (
    <div style={{ color: "#F1F5F9" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 4,
        }}
      >
        <span style={{ fontSize: 28 }}>{rules.flag}</span>
        <h1 style={{ fontFamily: MONO, fontSize: 24, color: GOLD }}>
          Tax Lab Ω
        </h1>
        <Badge variant="warning">
          {country} · TMI {fmtPct(tmi)}
        </Badge>
      </div>
      <p style={{ color: MUTED, fontSize: 13, marginBottom: 16 }}>
        Fiscal intelligence engine — {COUNTRIES.length} jurisdictions ·
        Portfolio optimization · Estate planning
      </p>

      <Tabs tabs={TAB_NAMES} active={activeTab} onChange={setActiveTab} />
      <div style={{ marginTop: 16 }}>
        {/* ══════════════════════════════════════════════════════════════════════ */}
        {/* TAB 0: TAX PROFILE ENGINE                                            */}
        {/* ══════════════════════════════════════════════════════════════════════ */}
        {activeTab === "Tax Profile" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card title="Fiscal Identity">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                  gap: 16,
                }}
              >
                <div>
                  <div style={{ fontSize: 12, color: DIM, marginBottom: 6 }}>
                    Tax Residence
                  </div>
                  <Select
                    value={country}
                    onChange={setCountry}
                    options={COUNTRIES}
                    width={240}
                  />
                </div>
                <div>
                  <Slider
                    label="Annual Income"
                    value={income}
                    onChange={setIncome}
                    min={0}
                    max={500000}
                    step={5000}
                    fmt={fmtEur}
                  />
                </div>
                <div>
                  <Slider
                    label="Family Quotient (parts)"
                    value={parts}
                    onChange={setParts}
                    min={1}
                    max={5}
                    step={0.5}
                    fmt={(v) => `${v} parts`}
                  />
                </div>
                <div>
                  <Slider
                    label="Investable Wealth"
                    value={investable}
                    onChange={setInvestable}
                    min={10000}
                    max={5000000}
                    step={10000}
                    fmt={fmtEur}
                  />
                </div>
              </div>
            </Card>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                gap: 12,
              }}
            >
              <MetricBox
                label="Income Tax"
                value={fmtEur(incomeTax)}
                color={RED}
              />
              <MetricBox label="TMI Rate" value={fmtPct(tmi)} color={AMBER} />
              <MetricBox
                label="CGT Rate"
                value={fmtPct(rules.cgt_flat)}
                color={CYAN}
              />
              <MetricBox
                label="Dividend Tax"
                value={fmtPct(rules.div_flat)}
                color={PURPLE}
              />
              <MetricBox
                label="Social Charges"
                value={fmtPct(rules.social)}
                color={DIM}
              />
              <MetricBox
                label="Wash-Sale Rule"
                value={rules.wash_sale ? `${rules.wash_days}d` : "None"}
                color={rules.wash_sale ? RED : GREEN}
              />
            </div>

            <Card title="Tax Brackets">
              <div style={{ height: 280 }}>
                <ResponsiveContainer>
                  <BarChart
                    data={rules.brackets.map((b, i) => ({
                      bracket:
                        i === 0
                          ? `0 – ${fmt(rules.brackets[1] || 0)}`
                          : `${fmt(b)}+`,
                      rate: rules.rates[i] * 100,
                      active: income / parts > b,
                    }))}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="bracket"
                      tick={{ fill: DIM, fontSize: 10 }}
                    />
                    <YAxis
                      tick={{ fill: DIM, fontSize: 11 }}
                      tickFormatter={(v) => `${v}%`}
                    />
                    <Tooltip
                      content={({ active, payload }) =>
                        active && payload?.[0] ? (
                          <TT>
                            <span style={{ color: GOLD, fontFamily: MONO }}>
                              {payload[0].payload.bracket}: {payload[0].value}%
                            </span>
                          </TT>
                        ) : null
                      }
                    />
                    <Bar dataKey="rate" radius={[4, 4, 0, 0]}>
                      {rules.brackets.map((b, i) => (
                        <Cell
                          key={i}
                          fill={
                            income / parts > b ? GOLD : "rgba(51,65,85,0.4)"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card title="Available Fiscal Envelopes">
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {rules.envelopes.map((e) => (
                  <span
                    key={e}
                    style={{
                      background: `${GOLD}18`,
                      border: `1px solid ${GOLD}44`,
                      borderRadius: 16,
                      padding: "4px 14px",
                      fontSize: 12,
                      color: GOLD,
                      fontFamily: MONO,
                    }}
                  >
                    {e}
                  </span>
                ))}
              </div>
            </Card>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════════ */}
        {/* TAB 1: TAX DASHBOARD                                                 */}
        {/* ══════════════════════════════════════════════════════════════════════ */}
        {activeTab === "Dashboard" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                gap: 12,
              }}
            >
              <MetricBox
                label="Portfolio Value"
                value={fmtEur(totalValue)}
                color={CYAN}
              />
              <MetricBox
                label="Total P&L"
                value={fmtEur(totalPnL)}
                color={totalPnL >= 0 ? GREEN : RED}
              />
              <MetricBox
                label="Unrealized Tax"
                value={fmtEur(totalTax)}
                color={RED}
              />
              <MetricBox
                label="Tax-Loss Harvestable"
                value={fmtEur(harvestableValue)}
                color={AMBER}
              />
              <MetricBox
                label="Effective Tax Rate"
                value={fmtPct(totalTax / Math.max(1, totalValue))}
                color={PURPLE}
              />
              <MetricBox
                label="Net After Tax"
                value={fmtEur(totalValue - totalTax)}
                color={GREEN}
              />
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 16,
              }}
            >
              <Card title="P&L by Position">
                <div style={{ height: 320 }}>
                  <ResponsiveContainer>
                    <BarChart
                      data={positions.map((p) => ({
                        name: p.ticker,
                        pnl: Math.round(p.pnl),
                      }))}
                      layout="vertical"
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(51,65,85,0.3)"
                      />
                      <XAxis
                        type="number"
                        tick={{ fill: DIM, fontSize: 11 }}
                        tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fill: MUTED, fontSize: 11, fontFamily: MONO }}
                        width={60}
                      />
                      <Tooltip
                        content={({ active, payload }) =>
                          active && payload?.[0] ? (
                            <TT>
                              <span
                                style={{
                                  color:
                                    (payload[0].value as number) >= 0
                                      ? GREEN
                                      : RED,
                                  fontFamily: MONO,
                                }}
                              >
                                {payload[0].payload.name}:{" "}
                                {fmtEur(payload[0].value as number)}
                              </span>
                            </TT>
                          ) : null
                        }
                      />
                      <Bar dataKey="pnl" radius={[0, 4, 4, 0]}>
                        {positions.map((p, i) => (
                          <Cell key={i} fill={p.pnl >= 0 ? GREEN : RED} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              <Card title="Allocation by Envelope">
                <div style={{ height: 320 }}>
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={envelopeAlloc}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        outerRadius={110}
                        label={({ name, percent }) =>
                          `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                        }
                      >
                        {envelopeAlloc.map((_, i) => (
                          <Cell
                            key={i}
                            fill={PIE_COLORS[i % PIE_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        content={({ active, payload }) =>
                          active && payload?.[0] ? (
                            <TT>
                              <span
                                style={{ color: "#F1F5F9", fontFamily: MONO }}
                              >
                                {payload[0].name}:{" "}
                                {fmtEur(payload[0].value as number)}
                              </span>
                            </TT>
                          ) : null
                        }
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>

            <Card title="Portfolio Positions">
              <div style={{ overflowX: "auto" }}>
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    fontSize: 12,
                  }}
                >
                  <thead>
                    <tr
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}
                    >
                      {[
                        "Ticker",
                        "Name",
                        "Shares",
                        "Cost",
                        "Price",
                        "P&L",
                        "P&L %",
                        "Tax Impact",
                        "Envelope",
                        "Days",
                      ].map((h) => (
                        <th
                          key={h}
                          style={{
                            padding: "8px 10px",
                            textAlign: "left",
                            color: DIM,
                            fontWeight: 500,
                            whiteSpace: "nowrap",
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((p) => (
                      <tr
                        key={p.ticker}
                        style={{
                          borderBottom: "1px solid rgba(51,65,85,0.15)",
                        }}
                      >
                        <td
                          style={{
                            padding: "6px 10px",
                            fontFamily: MONO,
                            color: GOLD,
                          }}
                        >
                          {p.ticker}
                        </td>
                        <td style={{ padding: "6px 10px", color: MUTED }}>
                          {p.name}
                        </td>
                        <td style={{ padding: "6px 10px", fontFamily: MONO }}>
                          {p.shares}
                        </td>
                        <td style={{ padding: "6px 10px", fontFamily: MONO }}>
                          €{p.costBasis.toFixed(2)}
                        </td>
                        <td style={{ padding: "6px 10px", fontFamily: MONO }}>
                          €{p.current.toFixed(2)}
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            fontFamily: MONO,
                            color: p.pnl >= 0 ? GREEN : RED,
                          }}
                        >
                          {fmtEur(p.pnl)}
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            fontFamily: MONO,
                            color: p.pnlPct >= 0 ? GREEN : RED,
                          }}
                        >
                          {(p.pnlPct * 100).toFixed(1)}%
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            fontFamily: MONO,
                            color: RED,
                          }}
                        >
                          {p.taxImpact > 0 ? fmtEur(p.taxImpact) : "—"}
                        </td>
                        <td style={{ padding: "6px 10px" }}>
                          <span
                            style={{
                              background: `${GOLD}18`,
                              border: `1px solid ${GOLD}44`,
                              borderRadius: 10,
                              padding: "2px 8px",
                              fontSize: 11,
                              color: GOLD,
                            }}
                          >
                            {p.envelope}
                          </span>
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            fontFamily: MONO,
                            color: DIM,
                          }}
                        >
                          {p.holdDays}d
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════════ */}
        {/* TAB 2: TAX-LOSS HARVESTING                                           */}
        {/* ══════════════════════════════════════════════════════════════════════ */}
        {activeTab === "Tax-Loss Harvesting" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card title="Harvesting Parameters">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 20,
                }}
              >
                <Slider
                  label="Loss Threshold %"
                  value={lossThreshold}
                  onChange={setLossThreshold}
                  min={-50}
                  max={0}
                  step={1}
                  fmt={(v) => `${v}%`}
                />
                <Slider
                  label="Transaction Cost (bps)"
                  value={txCostBps}
                  onChange={setTxCostBps}
                  min={0}
                  max={50}
                  step={1}
                  fmt={(v) => `${v} bps`}
                />
              </div>
              <div style={{ marginTop: 8, display: "flex", gap: 12 }}>
                <MetricBox
                  label="Harvestable Losses"
                  value={fmtEur(harvestableValue)}
                  color={AMBER}
                />
                <MetricBox
                  label="Tax Savings (CGT offset)"
                  value={fmtEur(taxSaved)}
                  color={GREEN}
                />
                <MetricBox
                  label="Transaction Costs"
                  value={fmtEur((harvestableValue * txCostBps) / 10000)}
                  color={RED}
                />
                <MetricBox
                  label="Net Benefit"
                  value={fmtEur(
                    taxSaved - (harvestableValue * txCostBps) / 10000,
                  )}
                  color={CYAN}
                />
              </div>
              {rules.wash_sale && (
                <div
                  style={{
                    marginTop: 12,
                    background: `${RED}15`,
                    border: `1px solid ${RED}33`,
                    borderRadius: 8,
                    padding: "8px 14px",
                    fontSize: 12,
                    color: RED,
                  }}
                >
                  ⚠ Wash-sale rule applies in {country}: {rules.wash_days}-day
                  waiting period before repurchasing substantially identical
                  securities.
                </div>
              )}
              {!rules.wash_sale && (
                <div
                  style={{
                    marginTop: 12,
                    background: `${GREEN}15`,
                    border: `1px solid ${GREEN}33`,
                    borderRadius: 8,
                    padding: "8px 14px",
                    fontSize: 12,
                    color: GREEN,
                  }}
                >
                  ✓ No wash-sale rule in {country} — you can harvest losses and
                  immediately repurchase or buy a replacement.
                </div>
              )}
            </Card>

            <Card title="TLH Candidates">
              {harvestable.length === 0 ? (
                <p style={{ color: DIM, fontSize: 13 }}>
                  No positions below the {lossThreshold}% threshold.
                </p>
              ) : (
                <div
                  style={{ display: "flex", flexDirection: "column", gap: 12 }}
                >
                  {harvestable.map((p) => (
                    <div
                      key={p.ticker}
                      style={{
                        background: "rgba(15,23,42,0.6)",
                        border: "1px solid rgba(239,68,68,0.2)",
                        borderRadius: 10,
                        padding: 14,
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
                        <div>
                          <span
                            style={{
                              fontFamily: MONO,
                              fontSize: 16,
                              color: RED,
                              fontWeight: 700,
                            }}
                          >
                            {p.ticker}
                          </span>
                          <span
                            style={{ color: DIM, fontSize: 12, marginLeft: 8 }}
                          >
                            {p.name}
                          </span>
                        </div>
                        <Badge variant="down">
                          {(p.pnlPct * 100).toFixed(1)}%
                        </Badge>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          gap: 16,
                          fontSize: 12,
                          color: MUTED,
                          marginBottom: 8,
                        }}
                      >
                        <span>
                          Loss:{" "}
                          <span style={{ color: RED, fontFamily: MONO }}>
                            {fmtEur(p.pnl)}
                          </span>
                        </span>
                        <span>
                          Tax saved:{" "}
                          <span style={{ color: GREEN, fontFamily: MONO }}>
                            {fmtEur(Math.abs(p.pnl) * rules.cgt_flat)}
                          </span>
                        </span>
                        <span>
                          Envelope:{" "}
                          <span style={{ color: GOLD }}>{p.envelope}</span>
                        </span>
                      </div>
                      {TLH_REPLACEMENTS[p.ticker] && (
                        <div style={{ marginTop: 4 }}>
                          <span style={{ fontSize: 11, color: DIM }}>
                            Replacement options:
                          </span>
                          <div
                            style={{ display: "flex", gap: 8, marginTop: 4 }}
                          >
                            {TLH_REPLACEMENTS[p.ticker].map((r) => (
                              <span
                                key={r.alt}
                                style={{
                                  background: `${CYAN}15`,
                                  border: `1px solid ${CYAN}33`,
                                  borderRadius: 12,
                                  padding: "3px 10px",
                                  fontSize: 11,
                                  color: CYAN,
                                  fontFamily: MONO,
                                }}
                              >
                                {r.alt} ({(r.corr * 100).toFixed(0)}% corr.)
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card title="10-Year TLH Projection">
              <div style={{ height: 300 }}>
                <ResponsiveContainer>
                  <AreaChart
                    data={Array.from({ length: 11 }, (_, y) => {
                      const annualHarvest = taxSaved * (1 + y * 0.05);
                      return {
                        year: `Y${y}`,
                        withTLH: Math.round(annualHarvest * (y + 1)),
                        withoutTLH: 0,
                      };
                    })}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis dataKey="year" tick={{ fill: DIM, fontSize: 11 }} />
                    <YAxis
                      tick={{ fill: DIM, fontSize: 11 }}
                      tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      content={({ active, payload }) =>
                        active && payload?.[0] ? (
                          <TT>
                            <span style={{ color: GREEN, fontFamily: MONO }}>
                              Cumulative savings:{" "}
                              {fmtEur(payload[0].value as number)}
                            </span>
                          </TT>
                        ) : null
                      }
                    />
                    <Area
                      type="monotone"
                      dataKey="withTLH"
                      stroke={GREEN}
                      fill={`${GREEN}20`}
                      name="With TLH"
                    />
                    <Area
                      type="monotone"
                      dataKey="withoutTLH"
                      stroke={DIM}
                      fill="transparent"
                      name="Without TLH"
                      strokeDasharray="4 4"
                    />
                    <Legend />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════════ */}
        {/* TAB 3: ENVELOPE OPTIMIZER                                            */}
        {/* ══════════════════════════════════════════════════════════════════════ */}
        {activeTab === "Envelope Optimizer" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card title={`Asset Location Rules — ${country}`}>
              <div style={{ overflowX: "auto" }}>
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    fontSize: 12,
                  }}
                >
                  <thead>
                    <tr style={{ borderBottom: `2px solid ${GOLD}44` }}>
                      {[
                        "Envelope",
                        "Limit",
                        "Best For",
                        "Avoid",
                        "Tax Advantage",
                        "Lock",
                      ].map((h) => (
                        <th
                          key={h}
                          style={{
                            padding: "10px 12px",
                            textAlign: "left",
                            color: GOLD,
                            fontWeight: 600,
                            fontSize: 11,
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {ENVELOPE_RULES.map((e) => {
                      const used =
                        envelopeAlloc.find((a) => a.name === e.name)?.value ||
                        0;
                      const pct = e.limit
                        ? Math.min(100, (used / e.limit) * 100)
                        : 0;
                      return (
                        <tr
                          key={e.name}
                          style={{
                            borderBottom: "1px solid rgba(51,65,85,0.2)",
                          }}
                        >
                          <td
                            style={{
                              padding: "10px 12px",
                              fontFamily: MONO,
                              color: GOLD,
                              fontWeight: 700,
                            }}
                          >
                            {e.name}
                          </td>
                          <td
                            style={{ padding: "10px 12px", fontFamily: MONO }}
                          >
                            {e.limit ? fmtEur(e.limit) : "∞"}
                            {e.limit && (
                              <div style={{ marginTop: 4 }}>
                                <div
                                  style={{
                                    width: 80,
                                    height: 4,
                                    background: "rgba(51,65,85,0.3)",
                                    borderRadius: 2,
                                  }}
                                >
                                  <div
                                    style={{
                                      width: `${pct}%`,
                                      height: 4,
                                      borderRadius: 2,
                                      background:
                                        pct > 80
                                          ? RED
                                          : pct > 50
                                            ? AMBER
                                            : GREEN,
                                    }}
                                  />
                                </div>
                                <span style={{ fontSize: 10, color: DIM }}>
                                  {fmtEur(used)} used
                                </span>
                              </div>
                            )}
                          </td>
                          <td
                            style={{
                              padding: "10px 12px",
                              color: GREEN,
                              fontSize: 11,
                            }}
                          >
                            {e.bestFor}
                          </td>
                          <td
                            style={{
                              padding: "10px 12px",
                              color: RED,
                              fontSize: 11,
                            }}
                          >
                            {e.avoid}
                          </td>
                          <td
                            style={{
                              padding: "10px 12px",
                              color: CYAN,
                              fontSize: 11,
                            }}
                          >
                            {e.advantage}
                          </td>
                          <td
                            style={{
                              padding: "10px 12px",
                              fontFamily: MONO,
                              color: AMBER,
                            }}
                          >
                            {e.lockYears > 0 ? `${e.lockYears}y` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card title="Envelope Capacity Tracker">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                  gap: 12,
                }}
              >
                {ENVELOPE_RULES.filter((e) => e.limit).map((e) => {
                  const used =
                    envelopeAlloc.find((a) => a.name === e.name)?.value || 0;
                  const pct = Math.min(100, (used / e.limit!) * 100);
                  const remaining = Math.max(0, e.limit! - used);
                  const barColor = pct > 90 ? RED : pct > 60 ? AMBER : GREEN;
                  return (
                    <div
                      key={e.name}
                      style={{
                        background: "rgba(15,23,42,0.6)",
                        border: "1px solid rgba(51,65,85,0.3)",
                        borderRadius: 10,
                        padding: 14,
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: 4,
                        }}
                      >
                        <span
                          style={{
                            fontFamily: MONO,
                            color: GOLD,
                            fontWeight: 700,
                          }}
                        >
                          {e.name}
                        </span>
                        <span
                          style={{
                            fontFamily: MONO,
                            fontSize: 12,
                            color: barColor,
                          }}
                        >
                          {pct.toFixed(0)}%
                        </span>
                      </div>
                      <div
                        style={{
                          width: "100%",
                          height: 8,
                          background: "rgba(51,65,85,0.3)",
                          borderRadius: 4,
                          marginBottom: 6,
                        }}
                      >
                        <div
                          style={{
                            width: `${pct}%`,
                            height: 8,
                            borderRadius: 4,
                            background: barColor,
                            transition: "width 0.3s",
                          }}
                        />
                      </div>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          fontSize: 11,
                          color: DIM,
                        }}
                      >
                        <span>Used: {fmtEur(used)}</span>
                        <span>Remaining: {fmtEur(remaining)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            <Card title="Optimization Recommendations">
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {positions
                  .filter((p) => p.envelope === "CTO" && p.pnl > 0)
                  .map((p) => {
                    const peaCapacity = Math.max(
                      0,
                      150000 -
                        (envelopeAlloc.find((a) => a.name === "PEA")?.value ||
                          0),
                    );
                    const suggestion =
                      p.sector === "Tech" && !p.ticker.includes(".PA")
                        ? "Consider synthetic EU ETF equivalent in PEA"
                        : peaCapacity > 0
                          ? "Eligible for PEA transfer"
                          : "AV may reduce tax on dividends";
                    return (
                      <div
                        key={p.ticker}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 12,
                          padding: "8px 12px",
                          background: "rgba(15,23,42,0.4)",
                          borderRadius: 8,
                          border: "1px solid rgba(51,65,85,0.2)",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: MONO,
                            color: GOLD,
                            minWidth: 60,
                          }}
                        >
                          {p.ticker}
                        </span>
                        <span style={{ color: MUTED, fontSize: 12, flex: 1 }}>
                          {suggestion}
                        </span>
                        <span
                          style={{
                            fontFamily: MONO,
                            fontSize: 12,
                            color: GREEN,
                          }}
                        >
                          Save ~{fmtEur(p.taxImpact * 0.3)}/yr
                        </span>
                      </div>
                    );
                  })}
              </div>
            </Card>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════════ */}
        {/* TAB 4: SCENARIO LAB                                                  */}
        {/* ══════════════════════════════════════════════════════════════════════ */}
        {activeTab === "Scenario Lab" &&
          (() => {
            const scenarios = [
              "CGT Timing (Sell Now vs Later)",
              "Rachat AV — Abattement",
              "Déménagement Fiscal",
              "PFU vs Barème",
              "Monte Carlo 20yr",
            ];

            const rng = seededRng(42);
            const mcPaths = useMemo(() => {
              const paths: {
                year: number;
                median: number;
                p10: number;
                p90: number;
                noTax: number;
              }[] = [];
              const N = 200;
              const mu = 0.07;
              const sigma = mcVol / 100;
              for (let y = 0; y <= mcYears; y++) {
                const finals: number[] = [];
                for (let i = 0; i < N; i++) {
                  let v = totalValue;
                  for (let t = 0; t < y; t++) {
                    const z =
                      Math.sqrt(-2 * Math.log(rng())) *
                      Math.cos(2 * Math.PI * rng());
                    v *= Math.exp(mu - 0.5 * sigma * sigma + sigma * z);
                  }
                  finals.push(v);
                }
                finals.sort((a, b) => a - b);
                const taxRate = rules.cgt_flat;
                paths.push({
                  year: y,
                  median: Math.round(
                    finals[Math.floor(N * 0.5)] * (1 - taxRate * 0.7),
                  ),
                  p10: Math.round(
                    finals[Math.floor(N * 0.1)] * (1 - taxRate * 0.7),
                  ),
                  p90: Math.round(
                    finals[Math.floor(N * 0.9)] * (1 - taxRate * 0.7),
                  ),
                  noTax: Math.round(finals[Math.floor(N * 0.5)]),
                });
              }
              return paths;
            }, [mcVol, mcYears, totalValue, rules.cgt_flat]);

            return (
              <div
                style={{ display: "flex", flexDirection: "column", gap: 16 }}
              >
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                  {scenarios.map((s, i) => (
                    <ChipButton
                      key={s}
                      label={s}
                      active={scenarioType === i}
                      onClick={() => setScenarioType(i)}
                    />
                  ))}
                </div>

                {scenarioType === 0 && (
                  <Card title="CGT Timing — Sell Now vs. Hold">
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: 16,
                      }}
                    >
                      <div
                        style={{
                          background: `${RED}10`,
                          border: `1px solid ${RED}25`,
                          borderRadius: 10,
                          padding: 16,
                        }}
                      >
                        <h4
                          style={{
                            color: RED,
                            fontFamily: MONO,
                            marginBottom: 8,
                          }}
                        >
                          Sell Now
                        </h4>
                        <div style={{ fontSize: 13, color: MUTED }}>
                          <div>
                            Gross gain:{" "}
                            <span style={{ color: GREEN, fontFamily: MONO }}>
                              {fmtEur(totalPnL)}
                            </span>
                          </div>
                          <div>
                            CGT ({fmtPct(rules.cgt_flat)}):{" "}
                            <span style={{ color: RED, fontFamily: MONO }}>
                              -{fmtEur(totalTax)}
                            </span>
                          </div>
                          <div
                            style={{
                              marginTop: 8,
                              fontWeight: 700,
                              color: "#F1F5F9",
                            }}
                          >
                            Net: {fmtEur(totalPnL - totalTax)}
                          </div>
                        </div>
                      </div>
                      <div
                        style={{
                          background: `${GREEN}10`,
                          border: `1px solid ${GREEN}25`,
                          borderRadius: 10,
                          padding: 16,
                        }}
                      >
                        <h4
                          style={{
                            color: GREEN,
                            fontFamily: MONO,
                            marginBottom: 8,
                          }}
                        >
                          Hold 5+ Years (PEA)
                        </h4>
                        <div style={{ fontSize: 13, color: MUTED }}>
                          <div>
                            Projected gain (7% CAGR):{" "}
                            <span style={{ color: GREEN, fontFamily: MONO }}>
                              {fmtEur(totalPnL * 1.4)}
                            </span>
                          </div>
                          <div>
                            Tax in PEA:{" "}
                            <span style={{ color: GREEN, fontFamily: MONO }}>
                              17.2% social only
                            </span>
                          </div>
                          <div
                            style={{
                              marginTop: 8,
                              fontWeight: 700,
                              color: "#F1F5F9",
                            }}
                          >
                            Net: {fmtEur(totalPnL * 1.4 * (1 - 0.172))}
                          </div>
                        </div>
                      </div>
                    </div>
                    <div
                      style={{
                        marginTop: 12,
                        padding: "8px 14px",
                        background: `${CYAN}10`,
                        borderRadius: 8,
                        fontSize: 12,
                        color: CYAN,
                      }}
                    >
                      💡 Tax saving by holding in PEA:{" "}
                      <span style={{ fontFamily: MONO, fontWeight: 700 }}>
                        {fmtEur(
                          totalPnL * 1.4 * (1 - 0.172) - (totalPnL - totalTax),
                        )}
                      </span>
                    </div>
                  </Card>
                )}

                {scenarioType === 1 && (
                  <Card title="Rachat AV — Abattement Optimization (France)">
                    <p style={{ color: MUTED, fontSize: 13, marginBottom: 12 }}>
                      After 8 years, Assurance-Vie allows €4,600/year (single)
                      or €9,200 (couple) in gains exempt from income tax.
                    </p>
                    <div style={{ height: 280 }}>
                      <ResponsiveContainer>
                        <BarChart
                          data={Array.from({ length: 10 }, (_, y) => {
                            const annualWithdraw = 4600 * parts;
                            const gainPortion = annualWithdraw * 0.6;
                            const taxWithout = gainPortion * rules.cgt_flat;
                            return {
                              year: `Y${y + 1}`,
                              exempt: Math.round(annualWithdraw),
                              taxSaved: Math.round(taxWithout * (y + 1)),
                            };
                          })}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="rgba(51,65,85,0.3)"
                          />
                          <XAxis
                            dataKey="year"
                            tick={{ fill: DIM, fontSize: 11 }}
                          />
                          <YAxis
                            tick={{ fill: DIM, fontSize: 11 }}
                            tickFormatter={(v) => `€${v}`}
                          />
                          <Tooltip
                            content={({ active, payload }) =>
                              active && payload ? (
                                <TT>
                                  <div
                                    style={{ fontFamily: MONO, fontSize: 12 }}
                                  >
                                    <div style={{ color: GREEN }}>
                                      Cumulative tax saved:{" "}
                                      {fmtEur(
                                        (payload[1]?.value as number) || 0,
                                      )}
                                    </div>
                                  </div>
                                </TT>
                              ) : null
                            }
                          />
                          <Bar
                            dataKey="exempt"
                            fill={GOLD}
                            name="Annual Exempt Withdrawal"
                            radius={[4, 4, 0, 0]}
                          />
                          <Bar
                            dataKey="taxSaved"
                            fill={GREEN}
                            name="Cumulative Tax Saved"
                            radius={[4, 4, 0, 0]}
                          />
                          <Legend />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>
                )}

                {scenarioType === 2 && (
                  <Card title="Fiscal Relocation — Country Comparison">
                    <p style={{ color: MUTED, fontSize: 13, marginBottom: 12 }}>
                      Net wealth after income tax + CGT for {fmtEur(income)}{" "}
                      income and {fmtEur(totalPnL)} capital gains.
                    </p>
                    <div style={{ height: 340 }}>
                      <ResponsiveContainer>
                        <BarChart
                          data={COUNTRIES.map((c) => {
                            const r = TAX_RULES[c];
                            const { tax } = computeTMI(income, parts, r);
                            const cgt = Math.max(0, totalPnL) * r.cgt_flat;
                            const netWealth = income - tax + totalPnL - cgt;
                            return {
                              country: `${r.flag} ${c}`,
                              net: Math.round(netWealth),
                              tax: Math.round(tax + cgt),
                            };
                          }).sort((a, b) => b.net - a.net)}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="rgba(51,65,85,0.3)"
                          />
                          <XAxis
                            dataKey="country"
                            tick={{ fill: DIM, fontSize: 9 }}
                            angle={-30}
                            textAnchor="end"
                            height={60}
                          />
                          <YAxis
                            tick={{ fill: DIM, fontSize: 11 }}
                            tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`}
                          />
                          <Tooltip
                            content={({ active, payload }) =>
                              active && payload?.[0] ? (
                                <TT>
                                  <div
                                    style={{ fontFamily: MONO, fontSize: 12 }}
                                  >
                                    <div style={{ color: GREEN }}>
                                      Net: {fmtEur(payload[0]?.value as number)}
                                    </div>
                                    <div style={{ color: RED }}>
                                      Total tax:{" "}
                                      {fmtEur(payload[1]?.value as number)}
                                    </div>
                                  </div>
                                </TT>
                              ) : null
                            }
                          />
                          <Bar
                            dataKey="net"
                            fill={GREEN}
                            name="Net Wealth"
                            radius={[4, 4, 0, 0]}
                          />
                          <Bar
                            dataKey="tax"
                            fill={RED}
                            name="Total Tax"
                            radius={[4, 4, 0, 0]}
                          />
                          <Legend />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>
                )}

                {scenarioType === 3 && (
                  <Card title="PFU (30% flat) vs Barème Progressif">
                    {(() => {
                      const gain = Math.max(0, totalPnL);
                      const pfuTax = gain * 0.3;
                      const baremeTax = gain * (tmi + rules.social);
                      const winner = pfuTax < baremeTax ? "PFU" : "Barème";
                      return (
                        <div>
                          <div
                            style={{
                              display: "grid",
                              gridTemplateColumns: "1fr 1fr",
                              gap: 16,
                              marginBottom: 16,
                            }}
                          >
                            <div
                              style={{
                                background:
                                  winner === "PFU"
                                    ? `${GREEN}12`
                                    : "rgba(15,23,42,0.4)",
                                border: `1px solid ${winner === "PFU" ? GREEN : "rgba(51,65,85,0.3)"}`,
                                borderRadius: 10,
                                padding: 16,
                              }}
                            >
                              <h4 style={{ color: GOLD, fontFamily: MONO }}>
                                PFU (Flat Tax 30%)
                              </h4>
                              <div
                                style={{
                                  fontSize: 24,
                                  fontFamily: MONO,
                                  color: RED,
                                  margin: "8px 0",
                                }}
                              >
                                {fmtEur(pfuTax)}
                              </div>
                              <div style={{ fontSize: 12, color: MUTED }}>
                                12.8% income tax + 17.2% social
                              </div>
                              {winner === "PFU" && (
                                <Badge variant="up">✓ Optimal</Badge>
                              )}
                            </div>
                            <div
                              style={{
                                background:
                                  winner === "Barème"
                                    ? `${GREEN}12`
                                    : "rgba(15,23,42,0.4)",
                                border: `1px solid ${winner === "Barème" ? GREEN : "rgba(51,65,85,0.3)"}`,
                                borderRadius: 10,
                                padding: 16,
                              }}
                            >
                              <h4 style={{ color: GOLD, fontFamily: MONO }}>
                                Barème Progressif
                              </h4>
                              <div
                                style={{
                                  fontSize: 24,
                                  fontFamily: MONO,
                                  color: RED,
                                  margin: "8px 0",
                                }}
                              >
                                {fmtEur(baremeTax)}
                              </div>
                              <div style={{ fontSize: 12, color: MUTED }}>
                                TMI {fmtPct(tmi)} + 17.2% social
                              </div>
                              {winner === "Barème" && (
                                <Badge variant="up">✓ Optimal</Badge>
                              )}
                            </div>
                          </div>
                          <div
                            style={{
                              padding: "8px 14px",
                              background: `${GREEN}10`,
                              borderRadius: 8,
                              fontSize: 13,
                              color: GREEN,
                            }}
                          >
                            💡 {winner} saves you{" "}
                            <span style={{ fontFamily: MONO, fontWeight: 700 }}>
                              {fmtEur(Math.abs(pfuTax - baremeTax))}
                            </span>{" "}
                            on {fmtEur(gain)} of gains.
                            {tmi <= 0.11 &&
                              " With a low TMI, barème is typically more favorable."}
                            {tmi >= 0.41 &&
                              " With a high TMI, PFU is almost always better."}
                          </div>
                        </div>
                      );
                    })()}
                  </Card>
                )}

                {scenarioType === 4 && (
                  <Card
                    title={`Monte Carlo ${mcYears}-Year Projection (${N} paths)`}
                    subtitle="Post-tax wealth trajectory with uncertainty bands"
                  >
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: 16,
                        marginBottom: 12,
                      }}
                    >
                      <Slider
                        label="Volatility (%)"
                        value={mcVol}
                        onChange={setMcVol}
                        min={5}
                        max={40}
                        step={1}
                        fmt={(v) => `${v}%`}
                      />
                      <Slider
                        label="Time Horizon (years)"
                        value={mcYears}
                        onChange={setMcYears}
                        min={5}
                        max={30}
                        step={1}
                        fmt={(v) => `${v}yr`}
                      />
                    </div>
                    <div style={{ height: 340 }}>
                      <ResponsiveContainer>
                        <AreaChart data={mcPaths}>
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="rgba(51,65,85,0.3)"
                          />
                          <XAxis
                            dataKey="year"
                            tick={{ fill: DIM, fontSize: 11 }}
                            tickFormatter={(v) => `Y${v}`}
                          />
                          <YAxis
                            tick={{ fill: DIM, fontSize: 11 }}
                            tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`}
                          />
                          <Tooltip
                            content={({ active, payload }) =>
                              active && payload?.[0] ? (
                                <TT>
                                  <div
                                    style={{ fontFamily: MONO, fontSize: 12 }}
                                  >
                                    <div style={{ color: GREEN }}>
                                      Median (after tax):{" "}
                                      {fmtEur(payload[0]?.value as number)}
                                    </div>
                                    <div style={{ color: AMBER }}>
                                      P10: {fmtEur(payload[1]?.value as number)}
                                    </div>
                                    <div style={{ color: CYAN }}>
                                      P90: {fmtEur(payload[2]?.value as number)}
                                    </div>
                                    <div style={{ color: DIM }}>
                                      Pre-tax median:{" "}
                                      {fmtEur(payload[3]?.value as number)}
                                    </div>
                                  </div>
                                </TT>
                              ) : null
                            }
                          />
                          <Area
                            type="monotone"
                            dataKey="median"
                            stroke={GREEN}
                            fill={`${GREEN}15`}
                            strokeWidth={2}
                            name="Median"
                          />
                          <Area
                            type="monotone"
                            dataKey="p10"
                            stroke={AMBER}
                            fill={`${AMBER}08`}
                            strokeDasharray="3 3"
                            name="P10"
                          />
                          <Area
                            type="monotone"
                            dataKey="p90"
                            stroke={CYAN}
                            fill={`${CYAN}08`}
                            strokeDasharray="3 3"
                            name="P90"
                          />
                          <Line
                            type="monotone"
                            dataKey="noTax"
                            stroke={DIM}
                            strokeDasharray="6 3"
                            name="Pre-tax"
                            dot={false}
                          />
                          <Legend />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </Card>
                )}
              </div>
            );
          })()}

        {/* ══════════════════════════════════════════════════════════════════════ */}
        {/* TAB 5: ESTATE & SUCCESSION PLANNER                                   */}
        {/* ══════════════════════════════════════════════════════════════════════ */}
        {activeTab === "Estate Planner" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card title="Estate & Succession Parameters">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: 16,
                }}
              >
                <Slider
                  label="Estate Value"
                  value={estateValue}
                  onChange={setEstateValue}
                  min={100000}
                  max={10000000}
                  step={50000}
                  fmt={fmtEur}
                />
                <Slider
                  label="Number of Children"
                  value={numChildren}
                  onChange={setNumChildren}
                  min={0}
                  max={6}
                  step={1}
                />
                <Slider
                  label="Assurance-Vie (AV) allocation"
                  value={avAmount}
                  onChange={setAvAmount}
                  min={0}
                  max={estateValue}
                  step={10000}
                  fmt={fmtEur}
                />
              </div>
            </Card>

            {(() => {
              const avExempt = Math.min(avAmount, numChildren * 152500);
              const taxableEstate = estateValue - avExempt;
              const successionTax = computeSuccessionFR(
                taxableEstate,
                numChildren,
              );
              const withoutAV = computeSuccessionFR(estateValue, numChildren);
              const avSaving = withoutAV - successionTax;

              return (
                <>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns:
                        "repeat(auto-fill, minmax(180px, 1fr))",
                      gap: 12,
                    }}
                  >
                    <MetricBox
                      label="Gross Estate"
                      value={fmtEur(estateValue)}
                      color={CYAN}
                    />
                    <MetricBox
                      label="AV Exemption"
                      value={fmtEur(avExempt)}
                      color={GREEN}
                    />
                    <MetricBox
                      label="Taxable Estate"
                      value={fmtEur(taxableEstate)}
                      color={AMBER}
                    />
                    <MetricBox
                      label="Succession Tax"
                      value={fmtEur(successionTax)}
                      color={RED}
                    />
                    <MetricBox
                      label="Effective Rate"
                      value={fmtPct(successionTax / estateValue)}
                      color={PURPLE}
                    />
                    <MetricBox
                      label="AV Tax Saving"
                      value={fmtEur(avSaving)}
                      color={GREEN}
                    />
                  </div>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: 16,
                    }}
                  >
                    <Card title="Succession Tax Brackets (France)">
                      <div style={{ height: 260 }}>
                        <ResponsiveContainer>
                          <BarChart
                            data={SUCCESSION_FR.filter(
                              (b) => b.hi !== Infinity,
                            ).map((b) => ({
                              bracket: `${fmt(b.lo)}–${fmt(b.hi)}`,
                              rate: b.rate * 100,
                            }))}
                          >
                            <CartesianGrid
                              strokeDasharray="3 3"
                              stroke="rgba(51,65,85,0.3)"
                            />
                            <XAxis
                              dataKey="bracket"
                              tick={{ fill: DIM, fontSize: 9 }}
                              angle={-20}
                              textAnchor="end"
                              height={50}
                            />
                            <YAxis
                              tick={{ fill: DIM, fontSize: 11 }}
                              tickFormatter={(v) => `${v}%`}
                            />
                            <Bar
                              dataKey="rate"
                              fill={RED}
                              radius={[4, 4, 0, 0]}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </Card>

                    <Card title="With vs Without AV">
                      <div style={{ height: 260 }}>
                        <ResponsiveContainer>
                          <BarChart
                            data={[
                              {
                                scenario: "Without AV",
                                tax: Math.round(withoutAV),
                                net: Math.round(estateValue - withoutAV),
                              },
                              {
                                scenario: "With AV",
                                tax: Math.round(successionTax),
                                net: Math.round(estateValue - successionTax),
                              },
                            ]}
                          >
                            <CartesianGrid
                              strokeDasharray="3 3"
                              stroke="rgba(51,65,85,0.3)"
                            />
                            <XAxis
                              dataKey="scenario"
                              tick={{ fill: MUTED, fontSize: 12 }}
                            />
                            <YAxis
                              tick={{ fill: DIM, fontSize: 11 }}
                              tickFormatter={(v) =>
                                `€${(v / 1000).toFixed(0)}k`
                              }
                            />
                            <Bar
                              dataKey="net"
                              fill={GREEN}
                              name="Net to Heirs"
                              radius={[4, 4, 0, 0]}
                            />
                            <Bar
                              dataKey="tax"
                              fill={RED}
                              name="Tax"
                              radius={[4, 4, 0, 0]}
                            />
                            <Legend />
                            <Tooltip
                              content={({ active, payload }) =>
                                active && payload ? (
                                  <TT>
                                    <div
                                      style={{ fontFamily: MONO, fontSize: 12 }}
                                    >
                                      <div style={{ color: GREEN }}>
                                        Net:{" "}
                                        {fmtEur(payload[0]?.value as number)}
                                      </div>
                                      <div style={{ color: RED }}>
                                        Tax:{" "}
                                        {fmtEur(payload[1]?.value as number)}
                                      </div>
                                    </div>
                                  </TT>
                                ) : null
                              }
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </Card>
                  </div>

                  <Card title="Transmission Strategies">
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(auto-fill, minmax(280px, 1fr))",
                        gap: 12,
                      }}
                    >
                      {[
                        {
                          name: "Donation-Partage",
                          desc: "€100k per child exempt, renewable every 15 years. Simple, flexible, well-established.",
                          impact: fmtEur(numChildren * 100000),
                          risk: "low",
                          color: GREEN,
                        },
                        {
                          name: "Démembrement de Propriété",
                          desc: "Split usufruct (income rights) vs. nue-propriété (ownership). Tax base reduced by age.",
                          impact: "30-40% reduction",
                          risk: "low",
                          color: CYAN,
                        },
                        {
                          name: "Assurance-Vie",
                          desc: "€152,500/beneficiary exempt outside succession (if funded before 70). Flexible designation.",
                          impact: fmtEur(numChildren * 152500),
                          risk: "low",
                          color: GOLD,
                        },
                        {
                          name: "SCI Familiale",
                          desc: "Family real estate company with equity discounts (15-30%). Complex but powerful for property.",
                          impact: "15-30% discount",
                          risk: "medium",
                          color: PURPLE,
                        },
                        {
                          name: "Pacte Dutreil",
                          desc: "75% exemption on business assets if held 4+ years. Major tool for entrepreneurs.",
                          impact: "75% exempt",
                          risk: "medium",
                          color: AMBER,
                        },
                      ].map((s) => (
                        <div
                          key={s.name}
                          style={{
                            background: "rgba(15,23,42,0.6)",
                            border: `1px solid ${s.color}33`,
                            borderRadius: 10,
                            padding: 14,
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              marginBottom: 6,
                            }}
                          >
                            <span
                              style={{
                                fontFamily: MONO,
                                color: s.color,
                                fontWeight: 700,
                              }}
                            >
                              {s.name}
                            </span>
                            <Badge
                              variant={s.risk === "low" ? "up" : "warning"}
                            >
                              {s.risk} risk
                            </Badge>
                          </div>
                          <p
                            style={{
                              color: MUTED,
                              fontSize: 12,
                              lineHeight: 1.5,
                              marginBottom: 6,
                            }}
                          >
                            {s.desc}
                          </p>
                          <div style={{ fontSize: 12, color: GREEN }}>
                            Impact:{" "}
                            <span style={{ fontFamily: MONO }}>{s.impact}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>

                  <Card title="Estate Rules by Country">
                    <div style={{ overflowX: "auto" }}>
                      <table
                        style={{
                          width: "100%",
                          borderCollapse: "collapse",
                          fontSize: 12,
                        }}
                      >
                        <thead>
                          <tr style={{ borderBottom: `2px solid ${GOLD}44` }}>
                            {[
                              "Country",
                              "Child Exemption",
                              "Spouse Exempt",
                              "Top Rate",
                              "Notes",
                            ].map((h) => (
                              <th
                                key={h}
                                style={{
                                  padding: "8px 12px",
                                  textAlign: "left",
                                  color: GOLD,
                                  fontWeight: 600,
                                  fontSize: 11,
                                }}
                              >
                                {h}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {[
                            {
                              c: "🇫🇷 France",
                              exempt: "€100,000",
                              spouse: "Yes",
                              rate: "45%",
                              notes: "Renewable every 15 years per child",
                            },
                            {
                              c: "🇺🇸 USA",
                              exempt: "$13,610,000",
                              spouse: "Yes",
                              rate: "40%",
                              notes:
                                "Lifetime exemption + step-up in basis at death",
                            },
                            {
                              c: "🇬🇧 UK",
                              exempt: "£500,000",
                              spouse: "Yes",
                              rate: "40%",
                              notes: "7-year rule for lifetime gifts (PETs)",
                            },
                            {
                              c: "🇩🇪 Germany",
                              exempt: "€400,000",
                              spouse: "Yes",
                              rate: "30%",
                              notes: "10-year renewal period",
                            },
                            {
                              c: "🇨🇭 Switzerland",
                              exempt: "Cantonal",
                              spouse: "Yes",
                              rate: "0-7% (children)",
                              notes:
                                "Varies by canton; 0-36% for third parties",
                            },
                            {
                              c: "🇸🇬 Singapore",
                              exempt: "N/A",
                              spouse: "N/A",
                              rate: "0%",
                              notes: "No estate duty since 2008",
                            },
                            {
                              c: "🇦🇪 UAE",
                              exempt: "N/A",
                              spouse: "N/A",
                              rate: "0%",
                              notes: "DIFC wills recommended for expats",
                            },
                            {
                              c: "🇮🇹 Italy",
                              exempt: "€1,000,000",
                              spouse: "Yes",
                              rate: "4-8%",
                              notes: "Among the lowest in Europe",
                            },
                          ].map((r) => (
                            <tr
                              key={r.c}
                              style={{
                                borderBottom: "1px solid rgba(51,65,85,0.2)",
                              }}
                            >
                              <td
                                style={{
                                  padding: "8px 12px",
                                  fontFamily: MONO,
                                }}
                              >
                                {r.c}
                              </td>
                              <td
                                style={{
                                  padding: "8px 12px",
                                  fontFamily: MONO,
                                  color: GREEN,
                                }}
                              >
                                {r.exempt}
                              </td>
                              <td
                                style={{
                                  padding: "8px 12px",
                                  color: r.spouse === "Yes" ? GREEN : DIM,
                                }}
                              >
                                {r.spouse}
                              </td>
                              <td
                                style={{
                                  padding: "8px 12px",
                                  fontFamily: MONO,
                                  color: RED,
                                }}
                              >
                                {r.rate}
                              </td>
                              <td style={{ padding: "8px 12px", color: MUTED }}>
                                {r.notes}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                </>
              );
            })()}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════════ */}
        {/* TAB 6: MULTI-JURISDICTION                                            */}
        {/* ══════════════════════════════════════════════════════════════════════ */}
        {activeTab === "Multi-Jurisdiction" &&
          (() => {
            const totalDays = Object.values(daysCountry).reduce(
              (s, d) => s + d,
              0,
            );
            const primary = Object.entries(daysCountry).sort(
              (a, b) => b[1] - a[1],
            )[0];
            const dayData = Object.entries(daysCountry).map(([c, d]) => ({
              name: `${TAX_RULES[c]?.flag || ""} ${c}`,
              value: d,
            }));

            return (
              <div
                style={{ display: "flex", flexDirection: "column", gap: 16 }}
              >
                {/* Day Counter */}
                <Card title="183-Day Residency Tracker">
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: 16,
                    }}
                  >
                    <div>
                      {Object.keys(daysCountry).map((c) => (
                        <Slider
                          key={c}
                          label={`${TAX_RULES[c]?.flag || ""} ${c}`}
                          value={daysCountry[c]}
                          onChange={(v) =>
                            setDaysCountry((prev) => ({ ...prev, [c]: v }))
                          }
                          min={0}
                          max={365}
                          step={1}
                          fmt={(v) => `${v} days`}
                        />
                      ))}
                      <div
                        style={{
                          marginTop: 8,
                          padding: "8px 14px",
                          background:
                            totalDays > 365 ? `${RED}15` : `${GREEN}15`,
                          borderRadius: 8,
                          fontSize: 12,
                          color: totalDays > 365 ? RED : GREEN,
                        }}
                      >
                        {totalDays > 365
                          ? `⚠ Total ${totalDays} days exceeds 365!`
                          : `✓ ${totalDays}/365 days allocated`}
                      </div>
                      {primary && primary[1] >= 183 && (
                        <div
                          style={{
                            marginTop: 8,
                            padding: "8px 14px",
                            background: `${CYAN}10`,
                            borderRadius: 8,
                            fontSize: 12,
                            color: CYAN,
                          }}
                        >
                          🏠 Tax residence:{" "}
                          <span style={{ fontFamily: MONO, fontWeight: 700 }}>
                            {primary[0]}
                          </span>{" "}
                          ({primary[1]} days ≥ 183)
                        </div>
                      )}
                    </div>
                    <div style={{ height: 280 }}>
                      <ResponsiveContainer>
                        <PieChart>
                          <Pie
                            data={dayData}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            outerRadius={100}
                            label={({ name, percent }) =>
                              `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                            }
                          >
                            {dayData.map((_, i) => (
                              <Cell
                                key={i}
                                fill={PIE_COLORS[i % PIE_COLORS.length]}
                              />
                            ))}
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </Card>

                {/* Treaty Navigator */}
                <Card title="Tax Treaty Navigator">
                  <div style={{ overflowX: "auto" }}>
                    <table
                      style={{
                        width: "100%",
                        borderCollapse: "collapse",
                        fontSize: 12,
                      }}
                    >
                      <thead>
                        <tr style={{ borderBottom: `2px solid ${GOLD}44` }}>
                          {[
                            "Source",
                            "Destination",
                            "Dividend WHT",
                            "Interest WHT",
                            "Royalties WHT",
                          ].map((h) => (
                            <th
                              key={h}
                              style={{
                                padding: "8px 12px",
                                textAlign: "left",
                                color: GOLD,
                                fontWeight: 600,
                                fontSize: 11,
                              }}
                            >
                              {h}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {TREATIES.map((t, i) => (
                          <tr
                            key={i}
                            style={{
                              borderBottom: "1px solid rgba(51,65,85,0.2)",
                            }}
                          >
                            <td
                              style={{ padding: "8px 12px", fontFamily: MONO }}
                            >
                              {TAX_RULES[t.from]?.flag} {t.from}
                            </td>
                            <td
                              style={{ padding: "8px 12px", fontFamily: MONO }}
                            >
                              {TAX_RULES[t.to]?.flag} {t.to}
                            </td>
                            <td
                              style={{
                                padding: "8px 12px",
                                fontFamily: MONO,
                                color: t.div === 0 ? GREEN : AMBER,
                              }}
                            >
                              {fmtPct(t.div)}
                            </td>
                            <td
                              style={{
                                padding: "8px 12px",
                                fontFamily: MONO,
                                color: t.interest === 0 ? GREEN : AMBER,
                              }}
                            >
                              {fmtPct(t.interest)}
                            </td>
                            <td
                              style={{
                                padding: "8px 12px",
                                fontFamily: MONO,
                                color: t.royalties === 0 ? GREEN : AMBER,
                              }}
                            >
                              {fmtPct(t.royalties)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>

                {/* Exit Tax */}
                <Card title="Exit Tax Simulator">
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: 16,
                      marginBottom: 12,
                    }}
                  >
                    <div>
                      <div
                        style={{ fontSize: 12, color: DIM, marginBottom: 6 }}
                      >
                        Departure Country
                      </div>
                      <Select
                        value={exitCountry}
                        onChange={setExitCountry}
                        options={Object.keys(EXIT_TAX)}
                        width={200}
                      />
                    </div>
                    <Slider
                      label="Unrealized Gains"
                      value={exitGains}
                      onChange={setExitGains}
                      min={0}
                      max={5000000}
                      step={50000}
                      fmt={fmtEur}
                    />
                  </div>
                  {EXIT_TAX[exitCountry] && (
                    <div
                      style={{
                        background: "rgba(15,23,42,0.6)",
                        border: `1px solid ${RED}33`,
                        borderRadius: 10,
                        padding: 16,
                      }}
                    >
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr 1fr",
                          gap: 16,
                          marginBottom: 12,
                        }}
                      >
                        <div>
                          <div style={{ fontSize: 11, color: DIM }}>
                            Threshold
                          </div>
                          <div
                            style={{
                              fontFamily: MONO,
                              fontSize: 14,
                              color: AMBER,
                            }}
                          >
                            {EXIT_TAX[exitCountry].threshold}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 11, color: DIM }}>Rate</div>
                          <div
                            style={{
                              fontFamily: MONO,
                              fontSize: 14,
                              color: RED,
                            }}
                          >
                            {EXIT_TAX[exitCountry].rate}
                          </div>
                        </div>
                        <div>
                          <div style={{ fontSize: 11, color: DIM }}>
                            Estimated Tax
                          </div>
                          <div
                            style={{
                              fontFamily: MONO,
                              fontSize: 18,
                              color: RED,
                              fontWeight: 700,
                            }}
                          >
                            {exitCountry === "France"
                              ? fmtEur(exitGains > 800000 ? exitGains * 0.3 : 0)
                              : exitCountry === "USA"
                                ? fmtEur(exitGains * 0.238)
                                : exitCountry === "Germany"
                                  ? fmtEur(exitGains * 0.26375)
                                  : exitCountry === "Spain"
                                    ? fmtEur(
                                        exitGains > 4000000
                                          ? exitGains * 0.26
                                          : 0,
                                      )
                                    : exitCountry === "Netherlands"
                                      ? fmtEur(exitGains * 0.269)
                                      : fmtEur(exitGains * 0.3784)}
                          </div>
                        </div>
                      </div>
                      <div
                        style={{
                          padding: "8px 14px",
                          background: `${AMBER}10`,
                          borderRadius: 8,
                          fontSize: 12,
                          color: AMBER,
                        }}
                      >
                        ℹ️ {EXIT_TAX[exitCountry].notes}
                      </div>
                    </div>
                  )}
                </Card>

                {/* Flag Theory */}
                <Card title="Flag Theory — Optimal Jurisdiction Mix">
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns:
                        "repeat(auto-fill, minmax(240px, 1fr))",
                      gap: 12,
                    }}
                  >
                    {[
                      {
                        flag: "Personal Residence",
                        options: "🇵🇹 Portugal (IFICI)",
                        color: CYAN,
                        detail: "10yr NHR+ program, 20% flat on foreign income",
                      },
                      {
                        flag: "Corporate Structure",
                        options: "🇮🇪 Ireland 12.5% / 🇱🇺 Luxembourg",
                        color: GREEN,
                        detail: "IP box regimes, holding company structures",
                      },
                      {
                        flag: "Banking",
                        options: "🇨🇭 Switzerland / 🇸🇬 Singapore",
                        color: GOLD,
                        detail: "Wealth management, private banking, stability",
                      },
                      {
                        flag: "Investments",
                        options: "🇦🇪 UAE / 🇭🇰 Hong Kong",
                        color: PURPLE,
                        detail: "0% CGT, 0% dividend tax, no wealth tax",
                      },
                      {
                        flag: "Citizenship",
                        options: "🇲🇹 Malta / 🇵🇹 Portugal",
                        color: AMBER,
                        detail: "EU passport through investment or residence",
                      },
                    ].map((f) => (
                      <div
                        key={f.flag}
                        style={{
                          background: "rgba(15,23,42,0.6)",
                          border: `1px solid ${f.color}33`,
                          borderRadius: 10,
                          padding: 14,
                        }}
                      >
                        <div
                          style={{
                            fontFamily: MONO,
                            fontSize: 13,
                            color: f.color,
                            fontWeight: 700,
                            marginBottom: 4,
                          }}
                        >
                          {f.flag}
                        </div>
                        <div
                          style={{
                            fontSize: 15,
                            fontWeight: 600,
                            color: "#F1F5F9",
                            marginBottom: 6,
                          }}
                        >
                          {f.options}
                        </div>
                        <div style={{ fontSize: 12, color: MUTED }}>
                          {f.detail}
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            );
          })()}

        {/* ══════════════════════════════════════════════════════════════════════ */}
        {/* TAB 7: COMPLIANCE & REPORTING                                        */}
        {/* ══════════════════════════════════════════════════════════════════════ */}
        {activeTab === "Compliance" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Card title="Anti-Abuse Strategy Checker">
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  {
                    strategy: "PEA with synthetic MSCI World ETF",
                    risk: "safe",
                    detail:
                      "Legal. Amundi / Lyxor synthetic ETFs are PEA-eligible.",
                  },
                  {
                    strategy: "Tax-Loss Harvesting in France (CTO)",
                    risk: "safe",
                    detail:
                      "No wash-sale rule in France. Fully legal, harvest aggressively.",
                  },
                  {
                    strategy: "AV partial withdrawal (abattement)",
                    risk: "safe",
                    detail:
                      "€4,600/yr exemption after 8 years. Well-established regime.",
                  },
                  {
                    strategy: "Donation-partage to children",
                    risk: "safe",
                    detail:
                      "€100k/child every 15 years. Standard estate planning.",
                  },
                  {
                    strategy: "Luxembourg AV (cross-border)",
                    risk: "safe",
                    detail:
                      "Legal under FPS regime. Super-privilege on assets.",
                  },
                  {
                    strategy: "Apport-cession (150-0 B ter CGI)",
                    risk: "medium",
                    detail:
                      "Must reinvest 60% in economic activity within 2 years. Scrutinized.",
                  },
                  {
                    strategy: "SCI with minority discount",
                    risk: "medium",
                    detail:
                      "15-30% discount accepted but regularly challenged by fisc.",
                  },
                  {
                    strategy: "Pre-exit tax planning (timing)",
                    risk: "high",
                    detail:
                      "Requalification risk. Must prove genuine economic substance.",
                  },
                  {
                    strategy: "Offshore undeclared structure",
                    risk: "high",
                    detail:
                      "Illegal. CRS/FATCA automatic exchange, heavy penalties.",
                  },
                ].map((s) => (
                  <div
                    key={s.strategy}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "10px 14px",
                      background:
                        s.risk === "safe"
                          ? `${GREEN}08`
                          : s.risk === "medium"
                            ? `${AMBER}08`
                            : `${RED}08`,
                      border: `1px solid ${s.risk === "safe" ? `${GREEN}25` : s.risk === "medium" ? `${AMBER}25` : `${RED}25`}`,
                      borderRadius: 8,
                    }}
                  >
                    <span style={{ fontSize: 18, minWidth: 24 }}>
                      {s.risk === "safe"
                        ? "✅"
                        : s.risk === "medium"
                          ? "⚠️"
                          : "❌"}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: "#F1F5F9",
                        }}
                      >
                        {s.strategy}
                      </div>
                      <div style={{ fontSize: 12, color: MUTED }}>
                        {s.detail}
                      </div>
                    </div>
                    <Badge
                      variant={
                        s.risk === "safe"
                          ? "up"
                          : s.risk === "medium"
                            ? "warning"
                            : "down"
                      }
                    >
                      {s.risk}
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Déclaration Assistant (France)">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
                  gap: 12,
                }}
              >
                {[
                  {
                    form: "Formulaire 2074",
                    title: "Plus-values mobilières",
                    fields: [
                      {
                        label: "PV brutes",
                        value: fmtEur(totalPnL > 0 ? totalPnL : 0),
                      },
                      {
                        label: "MV imputables",
                        value: fmtEur(
                          Math.abs(
                            positions
                              .filter((p) => p.pnl < 0)
                              .reduce((s, p) => s + p.pnl, 0),
                          ),
                        ),
                      },
                      {
                        label: "PV nette imposable",
                        value: fmtEur(Math.max(0, totalPnL)),
                      },
                    ],
                  },
                  {
                    form: "Formulaire 2042",
                    title: "Revenus & dividendes",
                    fields: [
                      { label: "Revenus (1AJ)", value: fmtEur(income) },
                      {
                        label: "PV nette (3VG)",
                        value: fmtEur(Math.max(0, totalPnL)),
                      },
                      { label: "Impôt estimé (IR)", value: fmtEur(incomeTax) },
                    ],
                  },
                  {
                    form: "Formulaire 3916",
                    title: "Comptes à l'étranger",
                    fields: [
                      { label: "Nb comptes étrangers", value: "2" },
                      { label: "Interactive Brokers (US)", value: "✓ déclaré" },
                      { label: "Revolut (UK)", value: "✓ déclaré" },
                    ],
                  },
                ].map((f) => (
                  <div
                    key={f.form}
                    style={{
                      background: "rgba(15,23,42,0.6)",
                      border: "1px solid rgba(51,65,85,0.3)",
                      borderRadius: 10,
                      padding: 14,
                    }}
                  >
                    <div
                      style={{
                        fontFamily: MONO,
                        fontSize: 13,
                        color: GOLD,
                        fontWeight: 700,
                        marginBottom: 2,
                      }}
                    >
                      {f.form}
                    </div>
                    <div
                      style={{ fontSize: 12, color: MUTED, marginBottom: 10 }}
                    >
                      {f.title}
                    </div>
                    {f.fields.map((fld) => (
                      <div
                        key={fld.label}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          padding: "4px 0",
                          borderBottom: "1px solid rgba(51,65,85,0.15)",
                        }}
                      >
                        <span style={{ fontSize: 12, color: MUTED }}>
                          {fld.label}
                        </span>
                        <span
                          style={{
                            fontFamily: MONO,
                            fontSize: 12,
                            color: CYAN,
                          }}
                        >
                          {fld.value}
                        </span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </Card>

            <Card title="CRS / FATCA Monitoring">
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  {
                    standard: "CRS (Common Reporting Standard)",
                    status: "Active",
                    jurisdictions: "100+ countries",
                    detail:
                      "Automatic exchange of financial account info. All bank/brokerage accounts reported to tax authority.",
                  },
                  {
                    standard: "FATCA (US Foreign Account Tax)",
                    status: "Active",
                    jurisdictions: "USA + IGA partners",
                    detail:
                      "US persons must report foreign accounts >$10k (FBAR) and >$50k (Form 8938).",
                  },
                  {
                    standard: "CARF (Crypto Asset Reporting)",
                    status: "Coming 2026",
                    jurisdictions: "48 countries (initial)",
                    detail:
                      "Will require crypto exchanges to report user transactions. Similar to CRS but for digital assets.",
                  },
                  {
                    standard: "DAC7 (EU Digital Platforms)",
                    status: "Active",
                    jurisdictions: "EU member states",
                    detail:
                      "Platforms report seller income (>€2k or >30 transactions). Covers marketplaces, gig economy.",
                  },
                ].map((s) => (
                  <div
                    key={s.standard}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "10px 14px",
                      background: "rgba(15,23,42,0.4)",
                      borderRadius: 8,
                      border: "1px solid rgba(51,65,85,0.2)",
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          fontFamily: MONO,
                          fontSize: 13,
                          color: "#F1F5F9",
                          fontWeight: 600,
                        }}
                      >
                        {s.standard}
                      </div>
                      <div style={{ fontSize: 12, color: MUTED }}>
                        {s.detail}
                      </div>
                    </div>
                    <div style={{ textAlign: "right", minWidth: 100 }}>
                      <Badge variant={s.status === "Active" ? "up" : "warning"}>
                        {s.status}
                      </Badge>
                      <div style={{ fontSize: 10, color: DIM, marginTop: 2 }}>
                        {s.jurisdictions}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Audit Trail">
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {[
                  {
                    date: "2026-03-15",
                    action: "TLH: Sold INTC (80 shares) — Loss €1,288",
                    type: "harvest",
                    savings: "€386",
                  },
                  {
                    date: "2026-03-10",
                    action: "TLH: Sold MMM (40 shares) — Loss €896",
                    type: "harvest",
                    savings: "€269",
                  },
                  {
                    date: "2026-02-28",
                    action: "Replacement: Bought SOXX (12 shares) for INTC",
                    type: "replace",
                    savings: "—",
                  },
                  {
                    date: "2026-02-15",
                    action: "AV withdrawal: €4,600 (within abattement)",
                    type: "withdrawal",
                    savings: "€690",
                  },
                  {
                    date: "2026-01-20",
                    action: "PEA contribution: €10,000",
                    type: "contribution",
                    savings: "—",
                  },
                  {
                    date: "2026-01-05",
                    action: "Dividend received: AAPL €380 (CTO, PFU applied)",
                    type: "dividend",
                    savings: "—",
                  },
                  {
                    date: "2025-12-15",
                    action: "TLH: Sold TSLA (25 shares) — Loss €1,663",
                    type: "harvest",
                    savings: "€499",
                  },
                  {
                    date: "2025-11-30",
                    action: "Form 3916 filed (foreign accounts declaration)",
                    type: "compliance",
                    savings: "—",
                  },
                ].map((e, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "8px 12px",
                      borderLeft: `3px solid ${e.type === "harvest" ? GREEN : e.type === "replace" ? CYAN : e.type === "withdrawal" ? GOLD : e.type === "compliance" ? PURPLE : DIM}`,
                      background: "rgba(15,23,42,0.3)",
                    }}
                  >
                    <span
                      style={{
                        fontFamily: MONO,
                        fontSize: 11,
                        color: DIM,
                        minWidth: 80,
                      }}
                    >
                      {e.date}
                    </span>
                    <span style={{ fontSize: 12, color: MUTED, flex: 1 }}>
                      {e.action}
                    </span>
                    {e.savings !== "—" && (
                      <span
                        style={{ fontFamily: MONO, fontSize: 12, color: GREEN }}
                      >
                        {e.savings}
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <div
                style={{
                  marginTop: 12,
                  padding: "8px 14px",
                  background: `${GREEN}10`,
                  borderRadius: 8,
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ fontSize: 13, color: GREEN }}>
                  YTD Net Tax Savings
                </span>
                <span
                  style={{
                    fontFamily: MONO,
                    fontSize: 20,
                    fontWeight: 700,
                    color: GREEN,
                  }}
                >
                  €1,844
                </span>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

const N = 200;
