import { useCallback, useMemo, useState } from "react";
import {
  Area,
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
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "../../components/ui/Card";
import { useIndices } from "../../hooks/useMarketData";

// ── Theme ────────────────────────────────────────────────────────────────────
const C = {
  bg: "#0A0E1A",
  card: "#0F1629",
  border: "#1E293B",
  gold: "#D4AF37",
  cyan: "#00D4FF",
  green: "#10B981",
  red: "#EF4444",
  orange: "#F59E0B",
  purple: "#A78BFA",
  text: "#F1F5F9",
  muted: "#94A3B8",
};
const mono = "JetBrains Mono, monospace";

// ── Demo company data ────────────────────────────────────────────────────────
const COMPANIES: Record<string, CompanyData> = {
  AAPL: {
    name: "Apple Inc.",
    sector: "Technology",
    spot: 198.11,
    beta: 1.24,
    marketCap: 3.08e12,
    ev: 3.06e12,
    totalDebt: 111.09e9,
    totalCash: 61.55e9,
    sharesOut: 15.55e9,
    ebitda: 130.54e9,
    revenue: 383.29e9,
    w52Low: 164.08,
    w52High: 199.62,
    pe: 33.24,
    fwdPe: 28.5,
    evEbitda: 23.44,
    evRev: 7.98,
    ps: 8.03,
    pb: 51.3,
    roe: 1.607,
    roa: 0.283,
    divYield: 0.005,
    debtEquity: 1.87,
    opMargin: 0.303,
    grossMargin: 0.461,
    fcfHistory: [92.95e9, 99.58e9, 111.44e9, 101.3e9, 110.54e9],
    revenueHistory: [274.52e9, 365.82e9, 394.33e9, 383.29e9, 391.04e9],
    grossProfitHistory: [104.96e9, 152.84e9, 170.78e9, 169.15e9, 180.68e9],
    ebitdaHistory: [77.34e9, 120.23e9, 130.54e9, 123.22e9, 130.54e9],
    netIncomeHistory: [57.41e9, 94.68e9, 99.8e9, 96.99e9, 101.13e9],
    opCashFlowHistory: [80.67e9, 104.04e9, 122.15e9, 110.54e9, 118.25e9],
    capexHistory: [7.31e9, 11.09e9, 10.71e9, 9.24e9, 7.71e9],
    totalAssets: 352.58e9,
    equity: 62.15e9,
    ltDebt: 98.96e9,
    cash: 29.97e9,
    currentRatio: 0.99,
    quickRatio: 0.94,
    altmanZ: 4.82,
    piotroskiF: 7,
    institutionalOwnership: 0.614,
    insiderOwnership: 0.007,
    analystTarget: 210,
    analystLow: 160,
    analystHigh: 250,
    analystCount: 42,
    recommendation: "Buy",
  },
  MSFT: {
    name: "Microsoft Corp.",
    sector: "Technology",
    spot: 420.55,
    beta: 0.89,
    marketCap: 3.13e12,
    ev: 3.09e12,
    totalDebt: 59.97e9,
    totalCash: 80.02e9,
    sharesOut: 7.43e9,
    ebitda: 119.38e9,
    revenue: 227.58e9,
    w52Low: 309.45,
    w52High: 428.49,
    pe: 37.2,
    fwdPe: 31.1,
    evEbitda: 25.88,
    evRev: 13.58,
    ps: 13.76,
    pb: 13.1,
    roe: 0.381,
    roa: 0.165,
    divYield: 0.007,
    debtEquity: 0.25,
    opMargin: 0.424,
    grossMargin: 0.695,
    fcfHistory: [45.23e9, 56.12e9, 65.15e9, 59.48e9, 67.2e9],
    revenueHistory: [143.02e9, 168.09e9, 198.27e9, 211.92e9, 227.58e9],
    grossProfitHistory: [96.94e9, 115.86e9, 135.62e9, 146.05e9, 158.24e9],
    ebitdaHistory: [69.92e9, 85.37e9, 100.36e9, 109.43e9, 119.38e9],
    netIncomeHistory: [44.28e9, 61.27e9, 72.74e9, 72.36e9, 86.18e9],
    opCashFlowHistory: [60.68e9, 76.74e9, 89.04e9, 87.58e9, 97.68e9],
    capexHistory: [15.44e9, 20.62e9, 23.89e9, 28.1e9, 30.48e9],
    totalAssets: 411.98e9,
    equity: 238.27e9,
    ltDebt: 47.03e9,
    cash: 34.7e9,
    currentRatio: 1.77,
    quickRatio: 1.54,
    altmanZ: 6.12,
    piotroskiF: 8,
    institutionalOwnership: 0.721,
    insiderOwnership: 0.014,
    analystTarget: 460,
    analystLow: 370,
    analystHigh: 530,
    analystCount: 55,
    recommendation: "Strong Buy",
  },
  GOOGL: {
    name: "Alphabet Inc.",
    sector: "Communication Services",
    spot: 170.28,
    beta: 1.06,
    marketCap: 2.11e12,
    ev: 1.99e12,
    totalDebt: 29.87e9,
    totalCash: 110.92e9,
    sharesOut: 12.38e9,
    ebitda: 97.97e9,
    revenue: 307.39e9,
    w52Low: 120.21,
    w52High: 174.72,
    pe: 25.7,
    fwdPe: 21.8,
    evEbitda: 20.3,
    evRev: 6.47,
    ps: 6.87,
    pb: 7.2,
    roe: 0.277,
    roa: 0.186,
    divYield: 0.0,
    debtEquity: 0.1,
    opMargin: 0.287,
    grossMargin: 0.567,
    fcfHistory: [42.84e9, 67.01e9, 60.01e9, 69.5e9, 73.77e9],
    revenueHistory: [182.53e9, 257.64e9, 282.84e9, 307.39e9, 327.82e9],
    grossProfitHistory: [97.8e9, 146.7e9, 156.63e9, 174.06e9, 185.85e9],
    ebitdaHistory: [54.92e9, 91.16e9, 84.3e9, 97.97e9, 107.28e9],
    netIncomeHistory: [40.27e9, 76.03e9, 59.97e9, 73.8e9, 83.67e9],
    opCashFlowHistory: [65.12e9, 91.65e9, 91.5e9, 101.75e9, 108.42e9],
    capexHistory: [22.28e9, 24.64e9, 31.49e9, 32.25e9, 34.65e9],
    totalAssets: 402.39e9,
    equity: 292.72e9,
    ltDebt: 14.7e9,
    cash: 110.92e9,
    currentRatio: 2.1,
    quickRatio: 1.98,
    altmanZ: 7.85,
    piotroskiF: 7,
    institutionalOwnership: 0.634,
    insiderOwnership: 0.058,
    analystTarget: 190,
    analystLow: 145,
    analystHigh: 220,
    analystCount: 48,
    recommendation: "Buy",
  },
};

interface CompanyData {
  name: string;
  sector: string;
  spot: number;
  beta: number;
  marketCap: number;
  ev: number;
  totalDebt: number;
  totalCash: number;
  sharesOut: number;
  ebitda: number;
  revenue: number;
  w52Low: number;
  w52High: number;
  pe: number;
  fwdPe: number;
  evEbitda: number;
  evRev: number;
  ps: number;
  pb: number;
  roe: number;
  roa: number;
  divYield: number;
  debtEquity: number;
  opMargin: number;
  grossMargin: number;
  fcfHistory: number[];
  revenueHistory: number[];
  grossProfitHistory: number[];
  ebitdaHistory: number[];
  netIncomeHistory: number[];
  opCashFlowHistory: number[];
  capexHistory: number[];
  totalAssets: number;
  equity: number;
  ltDebt: number;
  cash: number;
  currentRatio: number;
  quickRatio: number;
  altmanZ: number;
  piotroskiF: number;
  institutionalOwnership: number;
  insiderOwnership: number;
  analystTarget: number;
  analystLow: number;
  analystHigh: number;
  analystCount: number;
  recommendation: string;
}

// ── DCF calculation ──────────────────────────────────────────────────────────
function calcDCF(
  baseFcf: number,
  wacc: number,
  terminalGrowth: number,
  growthRates: number[],
  sharesOut: number,
  netDebt: number,
) {
  const projectedFcf: number[] = [];
  let fcf = baseFcf;
  for (const g of growthRates) {
    fcf *= 1 + g;
    projectedFcf.push(fcf);
  }
  let pvFcf = 0;
  for (let i = 0; i < projectedFcf.length; i++) {
    pvFcf += projectedFcf[i] / Math.pow(1 + wacc, i + 1);
  }
  const terminalFcf =
    projectedFcf[projectedFcf.length - 1] * (1 + terminalGrowth);
  const terminalValue = terminalFcf / (wacc - terminalGrowth);
  const pvTerminal = terminalValue / Math.pow(1 + wacc, projectedFcf.length);
  const enterpriseValue = pvFcf + pvTerminal;
  const equityValue = enterpriseValue - netDebt;
  const perShare = equityValue / sharesOut;
  const tvPct = (pvTerminal / enterpriseValue) * 100;
  return {
    projectedFcf,
    pvFcf,
    pvTerminal,
    enterpriseValue,
    equityValue,
    perShare,
    tvPct,
  };
}

// ── Monte Carlo simulation ───────────────────────────────────────────────────
function runMonteCarloDCF(
  baseFcf: number,
  waccMean: number,
  waccStd: number,
  growthMean: number,
  terminalGrowthMean: number,
  nSims: number,
  years: number,
  sharesOut: number,
  netDebt: number,
): number[] {
  const results: number[] = [];
  for (let s = 0; s < nSims; s++) {
    const w = waccMean + waccStd * boxMuller();
    const g = growthMean + 0.03 * boxMuller();
    const tg = Math.min(terminalGrowthMean + 0.005 * boxMuller(), w - 0.005);
    const rates = Array(years).fill(g);
    const r = calcDCF(
      baseFcf,
      Math.max(w, tg + 0.01),
      tg,
      rates,
      sharesOut,
      netDebt,
    );
    if (r.perShare > 0 && isFinite(r.perShare)) results.push(r.perShare);
  }
  return results.sort((a, b) => a - b);
}

function boxMuller() {
  let u = 0,
    v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function percentile(arr: number[], p: number) {
  const idx = (p / 100) * (arr.length - 1);
  const lo = Math.floor(idx),
    hi = Math.ceil(idx);
  return lo === hi ? arr[lo] : arr[lo] + (arr[hi] - arr[lo]) * (idx - lo);
}

// ── Reverse DCF (binary search for implied growth) ───────────────────────────
function reverseImpliedGrowth(
  baseFcf: number,
  targetPrice: number,
  wacc: number,
  terminalGrowth: number,
  years: number,
  sharesOut: number,
  netDebt: number,
): number | null {
  let lo = -0.3,
    hi = 0.8;
  for (let iter = 0; iter < 80; iter++) {
    const mid = (lo + hi) / 2;
    const r = calcDCF(
      baseFcf,
      wacc,
      terminalGrowth,
      Array(years).fill(mid),
      sharesOut,
      netDebt,
    );
    if (Math.abs(r.perShare - targetPrice) < 0.01) return mid;
    if (r.perShare < targetPrice) lo = mid;
    else hi = mid;
  }
  return (lo + hi) / 2;
}

// ── Helpers ──────────────────────────────────────────────────────────────────
const fmtB = (v: number) => `$${(v / 1e9).toFixed(1)}B`;
const fmtPct = (v: number) => `${(v * 100).toFixed(1)}%`;
const fmtPrice = (v: number) => `$${v.toFixed(2)}`;

const inputStyle: React.CSSProperties = {
  background: C.card,
  border: `1px solid ${C.border}`,
  borderRadius: 6,
  color: C.text,
  padding: "6px 10px",
  fontFamily: mono,
  fontSize: 13,
  width: "100%",
};
const labelStyle: React.CSSProperties = {
  color: C.muted,
  fontSize: 11,
  marginBottom: 4,
};
const btnStyle: React.CSSProperties = {
  background: `linear-gradient(135deg, ${C.gold}, #B8960C)`,
  color: "#000",
  border: "none",
  borderRadius: 6,
  padding: "8px 20px",
  fontWeight: 700,
  cursor: "pointer",
  fontFamily: mono,
  fontSize: 13,
};
const tabBtnStyle = (active: boolean): React.CSSProperties => ({
  background: active ? "rgba(0,217,255,0.12)" : "transparent",
  color: active ? C.cyan : C.muted,
  border: `1px solid ${active ? "rgba(0,217,255,0.3)" : C.border}`,
  borderRadius: 6,
  padding: "6px 14px",
  cursor: "pointer",
  fontSize: 12,
  fontFamily: mono,
  fontWeight: active ? 700 : 400,
});
const metricCard = (
  label: string,
  value: string,
  delta?: string,
  positive?: boolean,
) => (
  <div
    style={{
      background: C.card,
      border: `1px solid ${C.border}`,
      borderRadius: 8,
      padding: "10px 14px",
    }}
  >
    <div style={{ color: C.muted, fontSize: 11 }}>{label}</div>
    <div
      style={{ fontFamily: mono, fontSize: 18, color: C.text, marginTop: 2 }}
    >
      {value}
    </div>
    {delta && (
      <div
        style={{
          fontSize: 12,
          color: positive ? C.green : C.red,
          marginTop: 2,
        }}
      >
        {delta}
      </div>
    )}
  </div>
);

// ════════════════════════════════════════════════════════════════════════════
// COMPONENT
// ════════════════════════════════════════════════════════════════════════════

type Tab =
  | "dcf"
  | "montecarlo"
  | "multiples"
  | "reversedcf"
  | "trends"
  | "health"
  | "ownership"
  | "sensitivity";

export default function EnterpriseValuations() {
  const { data: indicesData } = useIndices();
  const [ticker, setTicker] = useState("AAPL");
  const [activeTab, setActiveTab] = useState<Tab>("dcf");
  const [company, setCompany] = useState<CompanyData>(COMPANIES.AAPL);

  // DCF state
  const [wacc, setWacc] = useState(8.0);
  const [stage1G, setStage1G] = useState(8.0);
  const [stage2G, setStage2G] = useState(4.0);
  const [termG, setTermG] = useState(2.5);
  const [dcfYears, setDcfYears] = useState(10);
  const [dcfResult, setDcfResult] = useState<ReturnType<typeof calcDCF> | null>(
    null,
  );

  // Monte Carlo state
  const [mcWacc, setMcWacc] = useState(8.0);
  const [mcGrowth, setMcGrowth] = useState(6.0);
  const [mcTermG, setMcTermG] = useState(2.5);
  const [mcSims, setMcSims] = useState(5000);
  const [mcWaccStd, setMcWaccStd] = useState(1.0);
  const [mcDist, setMcDist] = useState<number[]>([]);

  // Reverse DCF state
  const [rvWacc, setRvWacc] = useState(8.0);
  const [rvTermG, setRvTermG] = useState(2.5);
  const [rvYears, setRvYears] = useState(10);
  const [impliedGrowth, setImpliedGrowth] = useState<number | null>(null);

  const netDebt = company.totalDebt - company.totalCash;
  const baseFcf = company.fcfHistory[company.fcfHistory.length - 1];

  const handleAnalyze = useCallback(() => {
    const sym = ticker.toUpperCase().trim();
    if (COMPANIES[sym]) {
      setCompany(COMPANIES[sym]);
      setDcfResult(null);
      setMcDist([]);
      setImpliedGrowth(null);
    }
  }, [ticker]);

  const handleDCF = useCallback(() => {
    const rates = [
      ...Array(5).fill(stage1G / 100),
      ...Array(Math.max(0, dcfYears - 5)).fill(stage2G / 100),
    ];
    setDcfResult(
      calcDCF(
        baseFcf,
        wacc / 100,
        termG / 100,
        rates,
        company.sharesOut,
        netDebt,
      ),
    );
  }, [
    baseFcf,
    wacc,
    stage1G,
    stage2G,
    termG,
    dcfYears,
    company.sharesOut,
    netDebt,
  ]);

  const handleMC = useCallback(() => {
    const dist = runMonteCarloDCF(
      baseFcf,
      mcWacc / 100,
      mcWaccStd / 100,
      mcGrowth / 100,
      mcTermG / 100,
      mcSims,
      10,
      company.sharesOut,
      netDebt,
    );
    setMcDist(dist);
  }, [
    baseFcf,
    mcWacc,
    mcWaccStd,
    mcGrowth,
    mcTermG,
    mcSims,
    company.sharesOut,
    netDebt,
  ]);

  const handleReverse = useCallback(() => {
    const g = reverseImpliedGrowth(
      baseFcf,
      company.spot,
      rvWacc / 100,
      rvTermG / 100,
      rvYears,
      company.sharesOut,
      netDebt,
    );
    setImpliedGrowth(g);
  }, [
    baseFcf,
    company.spot,
    rvWacc,
    rvTermG,
    rvYears,
    company.sharesOut,
    netDebt,
  ]);

  // MC percentiles
  const mcStats = useMemo(() => {
    if (mcDist.length === 0) return null;
    return {
      p5: percentile(mcDist, 5),
      p25: percentile(mcDist, 25),
      p50: percentile(mcDist, 50),
      p75: percentile(mcDist, 75),
      p95: percentile(mcDist, 95),
      mean: mcDist.reduce((a, b) => a + b, 0) / mcDist.length,
      probAbove:
        (mcDist.filter((v) => v > company.spot).length / mcDist.length) * 100,
    };
  }, [mcDist, company.spot]);

  // MC histogram data
  const mcHistogram = useMemo(() => {
    if (mcDist.length === 0) return [];
    const min = mcDist[0],
      max = mcDist[mcDist.length - 1];
    const bins = 50;
    const binWidth = (max - min) / bins;
    const counts: { price: number; count: number }[] = [];
    for (let i = 0; i < bins; i++) {
      const lo = min + i * binWidth;
      const hi = lo + binWidth;
      const count = mcDist.filter((v) => v >= lo && v < hi).length;
      counts.push({ price: Math.round((lo + hi) / 2), count });
    }
    return counts;
  }, [mcDist]);

  // Sensitivity matrix
  const sensitivityMatrix = useMemo(() => {
    const waccRange = [6, 7, 8, 9, 10, 11, 12];
    const growthRange = [2, 4, 6, 8, 10, 12];
    return growthRange.map((g) => {
      const row: Record<string, number | string> = { growth: `${g}%` };
      for (const w of waccRange) {
        const rates = Array(10).fill(g / 100);
        const r = calcDCF(
          baseFcf,
          w / 100,
          termG / 100,
          rates,
          company.sharesOut,
          netDebt,
        );
        row[`w${w}`] = Math.round(r.perShare);
      }
      return row;
    });
  }, [baseFcf, termG, company.sharesOut, netDebt]);

  const w52Pct =
    company.w52High > company.w52Low
      ? ((company.spot - company.w52Low) / (company.w52High - company.w52Low)) *
        100
      : 0;

  const tabs: { key: Tab; label: string }[] = [
    { key: "dcf", label: "DCF" },
    { key: "montecarlo", label: "Monte Carlo" },
    { key: "multiples", label: "Multiples & Comps" },
    { key: "reversedcf", label: "Reverse DCF" },
    { key: "trends", label: "Financial Trends" },
    { key: "health", label: "Health & Risk" },
    { key: "ownership", label: "Ownership & Consensus" },
    { key: "sensitivity", label: "Sensitivity" },
  ];

  // Financial trends data
  const yearLabels = ["FY-4", "FY-3", "FY-2", "FY-1", "FY0"];
  const trendData = yearLabels.map((yr, i) => ({
    year: yr,
    revenue: company.revenueHistory[i] / 1e9,
    grossProfit: company.grossProfitHistory[i] / 1e9,
    ebitda: company.ebitdaHistory[i] / 1e9,
    netIncome: company.netIncomeHistory[i] / 1e9,
    fcf:
      (company.opCashFlowHistory[i] - Math.abs(company.capexHistory[i])) / 1e9,
    capex: Math.abs(company.capexHistory[i]) / 1e9,
    grossMargin:
      (company.grossProfitHistory[i] / company.revenueHistory[i]) * 100,
    ebitdaMargin: (company.ebitdaHistory[i] / company.revenueHistory[i]) * 100,
  }));

  // Implied prices at multiples
  const nd = company.totalDebt - company.totalCash;
  const ebitdaMultiples = [8, 10, 12, 15, 18, 20].map((m) => ({
    multiple: `${m}x`,
    implied: (company.ebitda * m - nd) / company.sharesOut,
  }));
  const revMultiples = [2, 3, 5, 8, 10, 15].map((m) => ({
    multiple: `${m}x`,
    implied: (company.revenue * m - nd) / company.sharesOut,
  }));

  // Football field data
  const footballField = useMemo(() => {
    const items: { label: string; low: number; high: number; mid: number }[] =
      [];
    if (dcfResult) {
      items.push({
        label: "DCF (±15%)",
        low: dcfResult.perShare * 0.85,
        high: dcfResult.perShare * 1.15,
        mid: dcfResult.perShare,
      });
    }
    if (mcStats) {
      items.push({
        label: "MC P25-P75",
        low: mcStats.p25,
        high: mcStats.p75,
        mid: mcStats.p50,
      });
    }
    if (company.ebitda > 0) {
      items.push({
        label: "EV/EBITDA 8-14x",
        low: (company.ebitda * 8 - nd) / company.sharesOut,
        high: (company.ebitda * 14 - nd) / company.sharesOut,
        mid: (company.ebitda * 11 - nd) / company.sharesOut,
      });
    }
    items.push({
      label: "Analyst Consensus",
      low: company.analystLow,
      high: company.analystHigh,
      mid: company.analystTarget,
    });
    items.push({
      label: "52-Week Range",
      low: company.w52Low,
      high: company.w52High,
      mid: company.spot,
    });
    return items;
  }, [dcfResult, mcStats, company, nd]);

  // Reverse DCF sensitivity curve
  const reverseSensitivity = useMemo(() => {
    if (impliedGrowth === null) return [];
    const points: { growth: number; price: number }[] = [];
    for (let g = -15; g <= 30; g += 1) {
      const r = calcDCF(
        baseFcf,
        rvWacc / 100,
        rvTermG / 100,
        Array(rvYears).fill(g / 100),
        company.sharesOut,
        netDebt,
      );
      if (
        r.perShare > 0 &&
        isFinite(r.perShare) &&
        r.perShare < company.spot * 5
      ) {
        points.push({ growth: g, price: Number(r.perShare.toFixed(2)) });
      }
    }
    return points;
  }, [
    impliedGrowth,
    baseFcf,
    rvWacc,
    rvTermG,
    rvYears,
    company.sharesOut,
    netDebt,
  ]);

  return (
    <div style={{ color: C.text }}>
      {!indicesData && (
        <div
          style={{
            background: "rgba(245,158,11,0.15)",
            border: "1px solid rgba(245,158,11,0.3)",
            borderRadius: 8,
            padding: "8px 16px",
            marginBottom: 16,
            fontSize: 13,
            color: "#F59E0B",
            fontFamily: "Inter, sans-serif",
          }}
        >
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      {/* Header */}
      <h1
        style={{
          fontFamily: mono,
          fontSize: 24,
          marginBottom: 4,
          color: C.gold,
        }}
      >
        Enterprise Valuations
      </h1>
      <p style={{ color: C.muted, marginBottom: 16, fontSize: 14 }}>
        DCF modelling, reverse DCF, financial trends, health scoring &amp; peer
        benchmarking
        {indicesData &&
          (() => {
            const allIndices = Object.values(indicesData).flat();
            const spx = allIndices.find(
              (idx) => idx.symbol === "SPX" || idx.name?.includes("S&P"),
            );
            const pct = spx?.change?.percent ?? 0;
            return spx ? (
              <span
                style={{ marginLeft: 12, color: pct >= 0 ? C.green : C.red }}
              >
                {spx.name}: {pct >= 0 ? "+" : ""}
                {pct.toFixed(2)}%
              </span>
            ) : null;
          })()}
      </p>

      {/* Ticker input */}
      <div
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 16,
          alignItems: "flex-end",
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={labelStyle}>Ticker</div>
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
            placeholder="AAPL, MSFT, GOOGL…"
            style={inputStyle}
          />
        </div>
        <button onClick={handleAnalyze} style={btnStyle}>
          Analyze
        </button>
        <div style={{ display: "flex", gap: 6 }}>
          {Object.keys(COMPANIES).map((s) => (
            <button
              key={s}
              onClick={() => {
                setTicker(s);
                setCompany(COMPANIES[s]);
                setDcfResult(null);
                setMcDist([]);
                setImpliedGrowth(null);
              }}
              style={{
                ...inputStyle,
                width: "auto",
                cursor: "pointer",
                padding: "6px 12px",
                fontSize: 12,
                opacity: company.name === COMPANIES[s].name ? 1 : 0.5,
                borderColor:
                  company.name === COMPANIES[s].name ? C.cyan : C.border,
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Company header metrics */}
      <Card
        title={`${company.name}  ·  ${ticker.toUpperCase()}`}
        subtitle={company.sector}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(7, 1fr)",
            gap: 12,
          }}
        >
          {metricCard("Price", fmtPrice(company.spot))}
          {metricCard("Market Cap", fmtB(company.marketCap))}
          {metricCard("EV", fmtB(company.ev))}
          {metricCard("Net Debt", fmtB(netDebt))}
          {metricCard("Beta", company.beta.toFixed(2))}
          {metricCard(
            "52W Position",
            `${w52Pct.toFixed(0)}%`,
            `$${company.w52Low.toFixed(0)}–$${company.w52High.toFixed(0)}`,
          )}
          {metricCard("Sector", company.sector)}
        </div>
      </Card>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: 6,
          margin: "20px 0 16px",
          flexWrap: "wrap",
        }}
      >
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            style={tabBtnStyle(activeTab === t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ═══ TAB: DCF ═══ */}
      {activeTab === "dcf" && (
        <Card title="2-Stage DCF Valuation">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            <div>
              <div style={labelStyle}>WACC (%)</div>
              <input
                type="number"
                value={wacc}
                onChange={(e) => setWacc(+e.target.value)}
                step={0.1}
                style={inputStyle}
              />
            </div>
            <div>
              <div style={labelStyle}>Stage 1 Growth % (Yr 1–5)</div>
              <input
                type="number"
                value={stage1G}
                onChange={(e) => setStage1G(+e.target.value)}
                step={0.5}
                style={inputStyle}
              />
            </div>
            <div>
              <div style={labelStyle}>Stage 2 Growth % (Yr 6–10)</div>
              <input
                type="number"
                value={stage2G}
                onChange={(e) => setStage2G(+e.target.value)}
                step={0.5}
                style={inputStyle}
              />
            </div>
            <div>
              <div style={labelStyle}>Terminal Growth (%)</div>
              <input
                type="number"
                value={termG}
                onChange={(e) => setTermG(+e.target.value)}
                step={0.1}
                style={inputStyle}
              />
            </div>
            <div>
              <div style={labelStyle}>Projection Years</div>
              <input
                type="number"
                value={dcfYears}
                onChange={(e) => setDcfYears(+e.target.value)}
                min={5}
                max={15}
                style={inputStyle}
              />
            </div>
          </div>
          <button onClick={handleDCF} style={btnStyle}>
            Calculate DCF
          </button>

          {dcfResult &&
            (() => {
              const upside = (dcfResult.perShare / company.spot - 1) * 100;
              return (
                <div style={{ marginTop: 20 }}>
                  <div
                    style={{
                      background:
                        upside > 15
                          ? "rgba(16,185,129,0.1)"
                          : upside < -15
                            ? "rgba(239,68,68,0.1)"
                            : "rgba(245,158,11,0.1)",
                      border: `1px solid ${upside > 15 ? C.green : upside < -15 ? C.red : C.orange}40`,
                      borderRadius: 8,
                      padding: "10px 16px",
                      marginBottom: 16,
                      fontSize: 14,
                    }}
                  >
                    <strong>
                      {upside > 15
                        ? "UNDERVALUED"
                        : upside < -15
                          ? "OVERVALUED"
                          : "FAIRLY VALUED"}
                    </strong>{" "}
                    — Intrinsic value {upside > 0 ? "+" : ""}
                    {upside.toFixed(1)}% vs market price
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(6, 1fr)",
                      gap: 12,
                      marginBottom: 20,
                    }}
                  >
                    {metricCard(
                      "Intrinsic Value/Share",
                      fmtPrice(dcfResult.perShare),
                      `${upside > 0 ? "+" : ""}${upside.toFixed(1)}%`,
                      upside > 0,
                    )}
                    {metricCard(
                      "Enterprise Value",
                      fmtB(dcfResult.enterpriseValue),
                    )}
                    {metricCard("PV of FCFs", fmtB(dcfResult.pvFcf))}
                    {metricCard(
                      "PV Terminal Value",
                      fmtB(dcfResult.pvTerminal),
                      `${dcfResult.tvPct.toFixed(0)}% of EV`,
                    )}
                    {metricCard("Net Debt", fmtB(netDebt))}
                    {metricCard("Base FCF", fmtB(baseFcf))}
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: 16,
                    }}
                  >
                    <div>
                      <h4
                        style={{
                          color: C.muted,
                          fontSize: 13,
                          marginBottom: 8,
                        }}
                      >
                        Projected Free Cash Flow
                      </h4>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart
                          data={dcfResult.projectedFcf.map((v, i) => ({
                            year: `Y${i + 1}`,
                            fcf: v / 1e9,
                          }))}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke={C.border}
                          />
                          <XAxis
                            dataKey="year"
                            stroke={C.muted}
                            fontSize={11}
                          />
                          <YAxis
                            stroke={C.muted}
                            fontSize={11}
                            tickFormatter={(v) => `$${v.toFixed(0)}B`}
                          />
                          <Tooltip
                            contentStyle={{
                              background: C.card,
                              border: `1px solid ${C.border}`,
                              borderRadius: 6,
                              color: C.text,
                            }}
                            formatter={(v: any) => [`$${v.toFixed(1)}B`, "FCF"]}
                          />
                          <ReferenceLine
                            x="Y5"
                            stroke={C.muted}
                            strokeDasharray="3 3"
                            label={{
                              value: "Stage 2",
                              fill: C.muted,
                              fontSize: 10,
                            }}
                          />
                          <Bar
                            dataKey="fcf"
                            fill={C.cyan}
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <div>
                      <h4
                        style={{
                          color: C.muted,
                          fontSize: 13,
                          marginBottom: 8,
                        }}
                      >
                        EV Bridge: PV(FCFs) + PV(TV) → Equity
                      </h4>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart
                          data={[
                            { label: "PV(FCFs)", value: dcfResult.pvFcf / 1e9 },
                            {
                              label: "PV(Terminal)",
                              value: dcfResult.pvTerminal / 1e9,
                            },
                            {
                              label: "Enterprise Value",
                              value: dcfResult.enterpriseValue / 1e9,
                            },
                            { label: "− Net Debt", value: -netDebt / 1e9 },
                            {
                              label: "Equity Value",
                              value: dcfResult.equityValue / 1e9,
                            },
                          ]}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke={C.border}
                          />
                          <XAxis
                            dataKey="label"
                            stroke={C.muted}
                            fontSize={10}
                          />
                          <YAxis
                            stroke={C.muted}
                            fontSize={11}
                            tickFormatter={(v) => `$${v}B`}
                          />
                          <Tooltip
                            contentStyle={{
                              background: C.card,
                              border: `1px solid ${C.border}`,
                              borderRadius: 6,
                              color: C.text,
                            }}
                            formatter={(v: any) => [`$${v.toFixed(1)}B`]}
                          />
                          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                            {[C.cyan, C.green, C.gold, C.red, C.cyan].map(
                              (color, i) => (
                                <Cell key={i} fill={color} />
                              ),
                            )}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              );
            })()}
        </Card>
      )}

      {/* ═══ TAB: Monte Carlo ═══ */}
      {activeTab === "montecarlo" && (
        <Card
          title="Monte Carlo DCF Simulation"
          subtitle="Randomises WACC, FCF growth and terminal growth to build a distribution of intrinsic values"
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            <div>
              <div style={labelStyle}>WACC Mean (%)</div>
              <input
                type="number"
                value={mcWacc}
                onChange={(e) => setMcWacc(+e.target.value)}
                step={0.1}
                style={inputStyle}
              />
            </div>
            <div>
              <div style={labelStyle}>FCF Growth Mean (%)</div>
              <input
                type="number"
                value={mcGrowth}
                onChange={(e) => setMcGrowth(+e.target.value)}
                step={0.5}
                style={inputStyle}
              />
            </div>
            <div>
              <div style={labelStyle}>Terminal Growth Mean (%)</div>
              <input
                type="number"
                value={mcTermG}
                onChange={(e) => setMcTermG(+e.target.value)}
                step={0.1}
                style={inputStyle}
              />
            </div>
            <div>
              <div style={labelStyle}>Simulations</div>
              <input
                type="number"
                value={mcSims}
                onChange={(e) => setMcSims(+e.target.value)}
                min={1000}
                max={20000}
                step={1000}
                style={inputStyle}
              />
            </div>
            <div>
              <div style={labelStyle}>WACC Std Dev (%)</div>
              <input
                type="number"
                value={mcWaccStd}
                onChange={(e) => setMcWaccStd(+e.target.value)}
                step={0.1}
                style={inputStyle}
              />
            </div>
          </div>
          <button onClick={handleMC} style={btnStyle}>
            Run Monte Carlo
          </button>

          {mcStats && (
            <div style={{ marginTop: 20 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(6, 1fr)",
                  gap: 12,
                  marginBottom: 20,
                }}
              >
                {metricCard(
                  "P5 (Bear)",
                  fmtPrice(mcStats.p5),
                  `${((mcStats.p5 / company.spot - 1) * 100).toFixed(1)}%`,
                  mcStats.p5 > company.spot,
                )}
                {metricCard(
                  "P25",
                  fmtPrice(mcStats.p25),
                  `${((mcStats.p25 / company.spot - 1) * 100).toFixed(1)}%`,
                  mcStats.p25 > company.spot,
                )}
                {metricCard(
                  "Median (P50)",
                  fmtPrice(mcStats.p50),
                  `${((mcStats.p50 / company.spot - 1) * 100).toFixed(1)}%`,
                  mcStats.p50 > company.spot,
                )}
                {metricCard(
                  "P75",
                  fmtPrice(mcStats.p75),
                  `${((mcStats.p75 / company.spot - 1) * 100).toFixed(1)}%`,
                  mcStats.p75 > company.spot,
                )}
                {metricCard(
                  "P95 (Bull)",
                  fmtPrice(mcStats.p95),
                  `${((mcStats.p95 / company.spot - 1) * 100).toFixed(1)}%`,
                  mcStats.p95 > company.spot,
                )}
                {metricCard(
                  "P(Undervalued)",
                  `${mcStats.probAbove.toFixed(1)}%`,
                  undefined,
                  mcStats.probAbove > 50,
                )}
              </div>
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={mcHistogram}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                  <XAxis
                    dataKey="price"
                    stroke={C.muted}
                    fontSize={10}
                    tickFormatter={(v) => `$${v}`}
                  />
                  <YAxis stroke={C.muted} fontSize={10} />
                  <Tooltip
                    contentStyle={{
                      background: C.card,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                      color: C.text,
                    }}
                    formatter={(v: any) => [v, "Count"]}
                    labelFormatter={(l) => `$${l}`}
                  />
                  <ReferenceLine
                    x={Math.round(company.spot)}
                    stroke="#fff"
                    strokeDasharray="5 5"
                    label={{
                      value: `Market $${company.spot.toFixed(0)}`,
                      fill: "#fff",
                      fontSize: 10,
                    }}
                  />
                  <Bar dataKey="count" fill={C.cyan} opacity={0.7} />
                </BarChart>
              </ResponsiveContainer>

              <div style={{ marginTop: 16 }}>
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    fontSize: 13,
                  }}
                >
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                      <th
                        style={{
                          textAlign: "left",
                          padding: 8,
                          color: C.muted,
                        }}
                      >
                        Scenario
                      </th>
                      <th
                        style={{
                          textAlign: "right",
                          padding: 8,
                          color: C.muted,
                        }}
                      >
                        Fair Value
                      </th>
                      <th
                        style={{
                          textAlign: "right",
                          padding: 8,
                          color: C.muted,
                        }}
                      >
                        Upside/Downside
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["Bear (P5)", mcStats.p5],
                      ["Conservative (P25)", mcStats.p25],
                      ["Base (P50)", mcStats.p50],
                      ["Optimistic (P75)", mcStats.p75],
                      ["Bull (P95)", mcStats.p95],
                      ["Mean", mcStats.mean],
                    ].map(([lbl, val]) => {
                      const v = val as number;
                      const up = (v / company.spot - 1) * 100;
                      return (
                        <tr
                          key={lbl as string}
                          style={{ borderBottom: `1px solid ${C.border}` }}
                        >
                          <td style={{ padding: 8, color: C.text }}>
                            {lbl as string}
                          </td>
                          <td
                            style={{
                              padding: 8,
                              textAlign: "right",
                              fontFamily: mono,
                              color: C.text,
                            }}
                          >
                            {fmtPrice(v)}
                          </td>
                          <td
                            style={{
                              padding: 8,
                              textAlign: "right",
                              fontFamily: mono,
                              color: up > 0 ? C.green : C.red,
                            }}
                          >
                            {up > 0 ? "+" : ""}
                            {up.toFixed(1)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>
      )}

      {/* ═══ TAB: Multiples & Comps ═══ */}
      {activeTab === "multiples" && (
        <Card title="Valuation Multiples & Football Field">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 24,
              marginBottom: 24,
            }}
          >
            <div>
              <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 12 }}>
                Current Trading Multiples
              </h4>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                    <th
                      style={{ textAlign: "left", padding: 8, color: C.muted }}
                    >
                      Metric
                    </th>
                    <th
                      style={{ textAlign: "right", padding: 8, color: C.muted }}
                    >
                      Value
                    </th>
                    <th
                      style={{ textAlign: "right", padding: 8, color: C.muted }}
                    >
                      Benchmark
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["Trailing P/E", `${company.pe.toFixed(1)}x`, "15–25x"],
                    ["Forward P/E", `${company.fwdPe.toFixed(1)}x`, "12–20x"],
                    ["EV/EBITDA", `${company.evEbitda.toFixed(1)}x`, "10–15x"],
                    ["EV/Revenue", `${company.evRev.toFixed(1)}x`, "2–5x"],
                    ["P/S", `${company.ps.toFixed(1)}x`, "1–4x"],
                    ["P/B", `${company.pb.toFixed(1)}x`, "2–4x"],
                    ["ROE", fmtPct(company.roe), ">15%"],
                    ["ROA", fmtPct(company.roa), ">5%"],
                    ["Div Yield", fmtPct(company.divYield), "2–4%"],
                    ["Debt/Equity", `${company.debtEquity.toFixed(2)}x`, "<1x"],
                  ].map(([m, v, b]) => (
                    <tr
                      key={m}
                      style={{ borderBottom: `1px solid ${C.border}` }}
                    >
                      <td style={{ padding: 8, color: C.text }}>{m}</td>
                      <td
                        style={{
                          padding: 8,
                          textAlign: "right",
                          fontFamily: mono,
                          color: C.text,
                        }}
                      >
                        {v}
                      </td>
                      <td
                        style={{
                          padding: 8,
                          textAlign: "right",
                          color: C.muted,
                        }}
                      >
                        {b}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div>
              <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 12 }}>
                Football Field Chart
              </h4>
              <ResponsiveContainer
                width="100%"
                height={Math.max(250, footballField.length * 55)}
              >
                <BarChart data={footballField} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                  <XAxis
                    type="number"
                    stroke={C.muted}
                    fontSize={10}
                    tickFormatter={(v) => `$${v}`}
                  />
                  <YAxis
                    type="category"
                    dataKey="label"
                    stroke={C.muted}
                    fontSize={10}
                    width={120}
                  />
                  <Tooltip
                    contentStyle={{
                      background: C.card,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                      color: C.text,
                    }}
                    formatter={(v: any) => [`$${v.toFixed(0)}`]}
                  />
                  <ReferenceLine
                    x={company.spot}
                    stroke="#fff"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    label={{
                      value: `Current $${company.spot.toFixed(0)}`,
                      fill: "#fff",
                      fontSize: 10,
                    }}
                  />
                  <Bar
                    dataKey="high"
                    fill="rgba(0,217,255,0.25)"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 12 }}>
            EV/EBITDA — Implied Price at Different Multiples
          </h4>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(6, 1fr)",
              gap: 12,
              marginBottom: 20,
            }}
          >
            {ebitdaMultiples.map(({ multiple, implied }) => {
              const up = (implied / company.spot - 1) * 100;
              return metricCard(
                `EV/EBITDA ${multiple}`,
                fmtPrice(implied),
                `${up > 0 ? "+" : ""}${up.toFixed(1)}%`,
                up > 0,
              );
            })}
          </div>

          <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 12 }}>
            EV/Revenue — Implied Price at Different Multiples
          </h4>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(6, 1fr)",
              gap: 12,
            }}
          >
            {revMultiples.map(({ multiple, implied }) => {
              const up = (implied / company.spot - 1) * 100;
              return metricCard(
                `EV/Rev ${multiple}`,
                fmtPrice(implied),
                `${up > 0 ? "+" : ""}${up.toFixed(1)}%`,
                up > 0,
              );
            })}
          </div>
        </Card>
      )}

      {/* ═══ TAB: Reverse DCF ═══ */}
      {activeTab === "reversedcf" && (
        <Card
          title="Reverse DCF — Market-Implied Growth Rate"
          subtitle="Solves for the FCF growth rate baked into the current share price via binary search"
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            <div>
              <div style={labelStyle}>WACC (%)</div>
              <input
                type="number"
                value={rvWacc}
                onChange={(e) => setRvWacc(+e.target.value)}
                step={0.1}
                style={inputStyle}
              />
            </div>
            <div>
              <div style={labelStyle}>Terminal Growth (%)</div>
              <input
                type="number"
                value={rvTermG}
                onChange={(e) => setRvTermG(+e.target.value)}
                step={0.1}
                style={inputStyle}
              />
            </div>
            <div>
              <div style={labelStyle}>Projection Years</div>
              <input
                type="number"
                value={rvYears}
                onChange={(e) => setRvYears(+e.target.value)}
                min={5}
                max={15}
                style={inputStyle}
              />
            </div>
          </div>
          <button onClick={handleReverse} style={btnStyle}>
            Find Implied Growth Rate
          </button>

          {impliedGrowth !== null && (
            <div style={{ marginTop: 20 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: 12,
                  marginBottom: 20,
                }}
              >
                {metricCard(
                  "Implied FCF Growth (Market)",
                  `${(impliedGrowth * 100).toFixed(1)}%`,
                )}
                {metricCard(
                  "Historical FCF CAGR",
                  (() => {
                    const h = company.fcfHistory;
                    if (h.length >= 2 && h[0] > 0)
                      return `${((Math.pow(h[h.length - 1] / h[0], 1 / (h.length - 1)) - 1) * 100).toFixed(1)}%`;
                    return "N/A";
                  })(),
                )}
                {metricCard(
                  "Interpretation",
                  `At WACC=${rvWacc}%, the market implies ${(impliedGrowth * 100).toFixed(1)}% FCF growth/yr`,
                )}
              </div>
              {reverseSensitivity.length > 0 && (
                <ResponsiveContainer width="100%" height={350}>
                  <ComposedChart data={reverseSensitivity}>
                    <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                    <XAxis
                      dataKey="growth"
                      stroke={C.muted}
                      fontSize={10}
                      tickFormatter={(v) => `${v}%`}
                      label={{
                        value: "FCF Growth Rate (%)",
                        fill: C.muted,
                        fontSize: 11,
                        position: "insideBottom",
                        offset: -5,
                      }}
                    />
                    <YAxis
                      stroke={C.muted}
                      fontSize={10}
                      tickFormatter={(v) => `$${v}`}
                      label={{
                        value: "Fair Value ($)",
                        fill: C.muted,
                        fontSize: 11,
                        angle: -90,
                        position: "insideLeft",
                      }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: C.card,
                        border: `1px solid ${C.border}`,
                        borderRadius: 6,
                        color: C.text,
                      }}
                      formatter={(v: any) => [fmtPrice(v), "Fair Value"]}
                      labelFormatter={(l) => `Growth: ${l}%`}
                    />
                    <ReferenceLine
                      y={company.spot}
                      stroke="#fff"
                      strokeDasharray="5 5"
                      label={{
                        value: `Market $${company.spot.toFixed(0)}`,
                        fill: "#fff",
                        fontSize: 10,
                      }}
                    />
                    <ReferenceLine
                      x={impliedGrowth * 100}
                      stroke={C.green}
                      strokeDasharray="3 3"
                      label={{
                        value: `Implied ${(impliedGrowth * 100).toFixed(1)}%`,
                        fill: C.green,
                        fontSize: 10,
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="price"
                      fill="rgba(0,217,255,0.08)"
                      stroke="none"
                    />
                    <Line
                      type="monotone"
                      dataKey="price"
                      stroke={C.cyan}
                      strokeWidth={2}
                      dot={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>
          )}
        </Card>
      )}

      {/* ═══ TAB: Financial Trends ═══ */}
      {activeTab === "trends" && (
        <Card title="Financial History & Trends">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 24,
            }}
          >
            <div>
              <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 8 }}>
                Revenue &amp; Gross Profit
              </h4>
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                  <XAxis dataKey="year" stroke={C.muted} fontSize={11} />
                  <YAxis
                    yAxisId="left"
                    stroke={C.muted}
                    fontSize={10}
                    tickFormatter={(v) => `$${v}B`}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    stroke={C.muted}
                    fontSize={10}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: C.card,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                      color: C.text,
                    }}
                  />
                  <Bar
                    yAxisId="left"
                    dataKey="revenue"
                    fill="#636efa"
                    name="Revenue ($B)"
                    radius={[3, 3, 0, 0]}
                  />
                  <Bar
                    yAxisId="left"
                    dataKey="grossProfit"
                    fill={C.cyan}
                    name="Gross Profit ($B)"
                    radius={[3, 3, 0, 0]}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="grossMargin"
                    stroke={C.green}
                    name="Gross Margin %"
                    strokeWidth={2}
                    dot
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div>
              <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 8 }}>
                EBITDA &amp; Net Income
              </h4>
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                  <XAxis dataKey="year" stroke={C.muted} fontSize={11} />
                  <YAxis
                    yAxisId="left"
                    stroke={C.muted}
                    fontSize={10}
                    tickFormatter={(v) => `$${v}B`}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    stroke={C.muted}
                    fontSize={10}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: C.card,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                      color: C.text,
                    }}
                  />
                  <Bar
                    yAxisId="left"
                    dataKey="ebitda"
                    fill="#4ecdc4"
                    name="EBITDA ($B)"
                    radius={[3, 3, 0, 0]}
                  />
                  <Bar
                    yAxisId="left"
                    dataKey="netIncome"
                    fill="#45b7d1"
                    name="Net Income ($B)"
                    radius={[3, 3, 0, 0]}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="ebitdaMargin"
                    stroke={C.red}
                    name="EBITDA Margin %"
                    strokeWidth={2}
                    dot
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div>
              <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 8 }}>
                Free Cash Flow &amp; CapEx
              </h4>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                  <XAxis dataKey="year" stroke={C.muted} fontSize={11} />
                  <YAxis
                    stroke={C.muted}
                    fontSize={10}
                    tickFormatter={(v) => `$${v}B`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: C.card,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                      color: C.text,
                    }}
                  />
                  <Bar
                    dataKey="fcf"
                    fill={C.green}
                    name="FCF ($B)"
                    radius={[3, 3, 0, 0]}
                  />
                  <Bar
                    dataKey="capex"
                    fill="#ff7eb9"
                    name="CapEx ($B)"
                    radius={[3, 3, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 8 }}>
                Balance Sheet Trends
              </h4>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart
                  data={yearLabels.map((yr) => ({
                    year: yr,
                    totalAssets: company.totalAssets / 1e9,
                    equity: company.equity / 1e9,
                    ltDebt: company.ltDebt / 1e9,
                    cash: company.cash / 1e9,
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                  <XAxis dataKey="year" stroke={C.muted} fontSize={11} />
                  <YAxis
                    stroke={C.muted}
                    fontSize={10}
                    tickFormatter={(v) => `$${v}B`}
                  />
                  <Tooltip
                    contentStyle={{
                      background: C.card,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                      color: C.text,
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="totalAssets"
                    stroke="#636efa"
                    name="Total Assets"
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="equity"
                    stroke={C.green}
                    name="Equity"
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="ltDebt"
                    stroke={C.red}
                    name="LT Debt"
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="cash"
                    stroke={C.gold}
                    name="Cash"
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 12 }}>
            Return &amp; Profitability Metrics
          </h4>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(6, 1fr)",
              gap: 12,
            }}
          >
            {metricCard("ROE", fmtPct(company.roe))}
            {metricCard("ROA", fmtPct(company.roa))}
            {metricCard("Operating Margin", fmtPct(company.opMargin))}
            {metricCard("Gross Margin", fmtPct(company.grossMargin))}
            {metricCard("D/E Ratio", `${company.debtEquity.toFixed(2)}x`)}
            {metricCard("Dividend Yield", fmtPct(company.divYield))}
          </div>
        </Card>
      )}

      {/* ═══ TAB: Health & Risk ═══ */}
      {activeTab === "health" && (
        <Card title="Financial Health & Risk Scoring">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 24,
              marginBottom: 24,
            }}
          >
            <div>
              <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 12 }}>
                Altman Z-Score — Bankruptcy Risk
              </h4>
              <div style={{ textAlign: "center", marginBottom: 12 }}>
                <div
                  style={{
                    fontFamily: mono,
                    fontSize: 48,
                    color:
                      company.altmanZ > 2.99
                        ? C.green
                        : company.altmanZ > 1.81
                          ? C.orange
                          : C.red,
                  }}
                >
                  {company.altmanZ.toFixed(2)}
                </div>
                <div style={{ color: C.muted, fontSize: 13 }}>
                  {company.altmanZ > 2.99
                    ? "Safe Zone"
                    : company.altmanZ > 1.81
                      ? "Grey Zone"
                      : "Distress Zone"}
                </div>
                <div
                  style={{
                    marginTop: 8,
                    height: 12,
                    background: `linear-gradient(90deg, ${C.red} 0%, ${C.orange} 30%, ${C.green} 50%, ${C.green} 100%)`,
                    borderRadius: 6,
                    position: "relative",
                  }}
                >
                  <div
                    style={{
                      position: "absolute",
                      left: `${Math.min((company.altmanZ / 6) * 100, 100)}%`,
                      top: -4,
                      width: 4,
                      height: 20,
                      background: "#fff",
                      borderRadius: 2,
                    }}
                  />
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    color: C.muted,
                    marginTop: 4,
                  }}
                >
                  <span>0 (Distress)</span>
                  <span>1.81</span>
                  <span>2.99</span>
                  <span>6 (Safe)</span>
                </div>
              </div>
            </div>
            <div>
              <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 12 }}>
                Piotroski F-Score — Earnings Quality
              </h4>
              <div style={{ textAlign: "center", marginBottom: 12 }}>
                <div
                  style={{
                    fontFamily: mono,
                    fontSize: 48,
                    color:
                      company.piotroskiF >= 7
                        ? C.green
                        : company.piotroskiF >= 4
                          ? C.orange
                          : C.red,
                  }}
                >
                  {company.piotroskiF}/9
                </div>
                <div style={{ color: C.muted, fontSize: 13 }}>
                  {company.piotroskiF >= 8
                    ? "Excellent"
                    : company.piotroskiF >= 5
                      ? "Good"
                      : company.piotroskiF >= 3
                        ? "Average"
                        : "Weak"}
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: 4,
                    justifyContent: "center",
                    marginTop: 12,
                  }}
                >
                  {Array.from({ length: 9 }, (_, i) => (
                    <div
                      key={i}
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: 6,
                        background:
                          i < company.piotroskiF
                            ? C.green
                            : "rgba(255,255,255,0.1)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 11,
                        fontFamily: mono,
                        color: i < company.piotroskiF ? "#000" : C.muted,
                      }}
                    >
                      {i + 1}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 12 }}>
            Capital Structure &amp; Credit Metrics
          </h4>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(6, 1fr)",
              gap: 12,
            }}
          >
            {metricCard(
              "Net Debt/EBITDA",
              `${(netDebt / company.ebitda).toFixed(1)}x`,
            )}
            {metricCard(
              "Interest Coverage",
              `${(company.ebitda / (company.totalDebt * 0.04)).toFixed(1)}x`,
            )}
            {metricCard("Debt/Equity", `${company.debtEquity.toFixed(2)}x`)}
            {metricCard("Current Ratio", `${company.currentRatio.toFixed(2)}x`)}
            {metricCard("Quick Ratio", `${company.quickRatio.toFixed(2)}x`)}
            {metricCard(
              "Net Debt/Total Capital",
              `${((netDebt / (company.marketCap + netDebt)) * 100).toFixed(1)}%`,
            )}
          </div>
        </Card>
      )}

      {/* ═══ TAB: Ownership & Consensus ═══ */}
      {activeTab === "ownership" && (
        <Card title="Analyst Consensus & Ownership">
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}
          >
            <div>
              <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 12 }}>
                Ownership Structure
              </h4>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={[
                      {
                        name: "Institutional",
                        value: company.institutionalOwnership * 100,
                      },
                      {
                        name: "Insider",
                        value: company.insiderOwnership * 100,
                      },
                      {
                        name: "Public Float",
                        value: Math.max(
                          0,
                          100 -
                            company.institutionalOwnership * 100 -
                            company.insiderOwnership * 100,
                        ),
                      },
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    dataKey="value"
                    label={({ name, percent = 0 }) =>
                      `${name} ${(percent * 100).toFixed(0)}%`
                    }
                  >
                    <Cell fill={C.cyan} />
                    <Cell fill={C.green} />
                    <Cell fill="#636efa" />
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: C.card,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                      color: C.text,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: 8,
                  marginTop: 8,
                }}
              >
                {metricCard(
                  "Institutional",
                  `${(company.institutionalOwnership * 100).toFixed(1)}%`,
                )}
                {metricCard(
                  "Insider",
                  `${(company.insiderOwnership * 100).toFixed(1)}%`,
                )}
                {metricCard(
                  "Float",
                  `${(100 - company.institutionalOwnership * 100 - company.insiderOwnership * 100).toFixed(1)}%`,
                )}
              </div>
            </div>
            <div>
              <h4 style={{ color: C.muted, fontSize: 13, marginBottom: 12 }}>
                Analyst Consensus
              </h4>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, 1fr)",
                  gap: 12,
                  marginBottom: 16,
                }}
              >
                {metricCard(
                  "Consensus Target",
                  fmtPrice(company.analystTarget),
                  `${((company.analystTarget / company.spot - 1) * 100).toFixed(1)}%`,
                  company.analystTarget > company.spot,
                )}
                {metricCard("Recommendation", company.recommendation)}
                {metricCard("Bull Target", fmtPrice(company.analystHigh))}
                {metricCard("Bear Target", fmtPrice(company.analystLow))}
                {metricCard("# Analysts", `${company.analystCount}`)}
              </div>
              <div
                style={{
                  marginTop: 12,
                  padding: "12px 16px",
                  background: "rgba(0,217,255,0.05)",
                  border: `1px solid rgba(0,217,255,0.15)`,
                  borderRadius: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div
                    style={{
                      flex: 1,
                      height: 8,
                      background: C.border,
                      borderRadius: 4,
                      position: "relative",
                    }}
                  >
                    <div
                      style={{
                        position: "absolute",
                        left: 0,
                        right: 0,
                        height: "100%",
                        background: `linear-gradient(90deg, ${C.red}, ${C.orange}, ${C.green})`,
                        borderRadius: 4,
                        opacity: 0.3,
                      }}
                    />
                    {[
                      company.analystLow,
                      company.analystTarget,
                      company.analystHigh,
                      company.spot,
                    ].map((v, i) => (
                      <div
                        key={i}
                        style={{
                          position: "absolute",
                          left: `${((v - company.analystLow) / (company.analystHigh - company.analystLow)) * 100}%`,
                          top: -6,
                          width: i === 3 ? 3 : 10,
                          height: 20,
                          borderRadius: i === 3 ? 2 : "50%",
                          background:
                            i === 3
                              ? "#fff"
                              : i === 0
                                ? C.red
                                : i === 1
                                  ? C.green
                                  : C.green,
                        }}
                      />
                    ))}
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10,
                    color: C.muted,
                    marginTop: 6,
                  }}
                >
                  <span>Bear ${company.analystLow}</span>
                  <span>Consensus ${company.analystTarget}</span>
                  <span>Bull ${company.analystHigh}</span>
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* ═══ TAB: Sensitivity ═══ */}
      {activeTab === "sensitivity" && (
        <Card
          title="Sensitivity Analysis — WACC vs Growth"
          subtitle="Fair value per share at different WACC and FCF growth rate combinations"
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
                <tr style={{ borderBottom: `2px solid ${C.border}` }}>
                  <th
                    style={{
                      padding: 10,
                      textAlign: "left",
                      color: C.gold,
                      fontFamily: mono,
                    }}
                  >
                    Growth ↓ \ WACC →
                  </th>
                  {[6, 7, 8, 9, 10, 11, 12].map((w) => (
                    <th
                      key={w}
                      style={{
                        padding: 10,
                        textAlign: "right",
                        color: C.cyan,
                        fontFamily: mono,
                      }}
                    >
                      {w}%
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sensitivityMatrix.map((row, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}` }}>
                    <td
                      style={{
                        padding: 10,
                        color: C.gold,
                        fontFamily: mono,
                        fontWeight: 700,
                      }}
                    >
                      {row.growth}
                    </td>
                    {[6, 7, 8, 9, 10, 11, 12].map((w) => {
                      const val = row[`w${w}`] as number;
                      const diff = val - company.spot;
                      const bg =
                        diff > company.spot * 0.15
                          ? "rgba(16,185,129,0.15)"
                          : diff < -company.spot * 0.15
                            ? "rgba(239,68,68,0.15)"
                            : "rgba(245,158,11,0.08)";
                      return (
                        <td
                          key={w}
                          style={{
                            padding: 10,
                            textAlign: "right",
                            fontFamily: mono,
                            background: bg,
                            color: diff > 0 ? C.green : C.red,
                          }}
                        >
                          ${val}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={{ color: C.muted, fontSize: 12, marginTop: 12 }}>
            Current market price:{" "}
            <strong style={{ color: C.text }}>
              ${company.spot.toFixed(2)}
            </strong>{" "}
            — Green cells indicate undervaluation, red cells overvaluation (±15%
            threshold)
          </p>
        </Card>
      )}
    </div>
  );
}
