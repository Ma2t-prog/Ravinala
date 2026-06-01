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
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Card } from "../../components/ui";
import { Tabs } from "../../components/ui/Tabs";
import { useIndices, useSnapshot } from "../../hooks/useMarketData";

// ── Shared tooltip style ──
const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
};

/* ════════════════════════════════════════════════════════════
   ML ENGINE DATA
════════════════════════════════════════════════════════════ */
function seededRandomML(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return s / 2147483647;
  };
}

const ML_TABS = ["Models", "Scenarios", "Regime Detection", "Anomaly Detection"] as const;

const MODELS = [
  { name: "Random Forest", abbr: "RF", accuracy: 72.4, precision: 71.8, recall: 73.1, f1: 72.4, auc: 0.78, color: "#10B981", description: "Ensemble tree-based model for daily direction prediction" },
  { name: "XGBoost", abbr: "XGB", accuracy: 75.1, precision: 74.6, recall: 75.8, f1: 75.2, auc: 0.81, color: "#00D9FF", description: "Gradient boosting with optimized hyperparameters" },
  { name: "LSTM Network", abbr: "LSTM", accuracy: 68.9, precision: 69.2, recall: 68.5, f1: 68.8, auc: 0.74, color: "#D4AF37", description: "Recurrent neural network for sequence prediction" },
];

const predictionData = Array.from({ length: 60 }, (_, i) => ({
  day: `D${i + 1}`,
  actual: +(185 + Math.sin(i * 0.1) * 12 + i * 0.12).toFixed(2),
  rf: +(185 + Math.sin(i * 0.1) * 11 + i * 0.12 + Math.sin(i * 0.4) * 1.5).toFixed(2),
  xgb: +(185 + Math.sin(i * 0.1) * 11.5 + i * 0.12 + Math.sin(i * 0.5) * 1).toFixed(2),
  lstm: +(185 + Math.sin(i * 0.1) * 10 + i * 0.12 + Math.sin(i * 0.3) * 2.5).toFixed(2),
}));

const featureImportance = [
  { feature: "RSI (14)", importance: 0.18 },
  { feature: "MACD Signal", importance: 0.15 },
  { feature: "Volume MA Ratio", importance: 0.13 },
  { feature: "Bollinger %B", importance: 0.11 },
  { feature: "ATR (14)", importance: 0.09 },
  { feature: "Price/MA50", importance: 0.08 },
  { feature: "Stochastic %K", importance: 0.07 },
  { feature: "OBV Slope", importance: 0.06 },
  { feature: "Sector Momentum", importance: 0.05 },
  { feature: "VIX Level", importance: 0.04 },
];

const ML_REGIMES = [
  { name: "Bull (Low Vol)", color: "#10B981", prob: 42, vol: "12.1%", sharpe: "1.85", avgRet: "+0.08%/d" },
  { name: "Bull (High Vol)", color: "#F59E0B", prob: 18, vol: "22.4%", sharpe: "0.91", avgRet: "+0.05%/d" },
  { name: "Bear (Low Vol)", color: "#3B82F6", prob: 15, vol: "15.8%", sharpe: "-0.42", avgRet: "-0.03%/d" },
  { name: "Bear (High Vol)", color: "#EF4444", prob: 25, vol: "31.2%", sharpe: "-1.15", avgRet: "-0.12%/d" },
];

const ML_TRANSITION_MATRIX = [
  { from: "Bull LoVol", bullLo: 0.82, bullHi: 0.08, bearLo: 0.06, bearHi: 0.04 },
  { from: "Bull HiVol", bullLo: 0.25, bullHi: 0.55, bearLo: 0.05, bearHi: 0.15 },
  { from: "Bear LoVol", bullLo: 0.15, bullHi: 0.1, bearLo: 0.6, bearHi: 0.15 },
  { from: "Bear HiVol", bullLo: 0.05, bullHi: 0.12, bearLo: 0.18, bearHi: 0.65 },
];

/* ════════════════════════════════════════════════════════════
   ADVANCED ANALYSIS DATA
════════════════════════════════════════════════════════════ */
function sRng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807) % 2147483647;
    return s / 2147483647;
  };
}

const ADV_TABS = ["Efficient Frontier", "Monte Carlo", "Factor Analysis", "Statistical Tests", "Distribution", "Backtest", "Optimization", "Drawdown"] as const;

const EF_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "JPM", "XOM", "GLD", "TLT"];
const MU = [0.18, 0.15, 0.22, 0.2, 0.12, 0.1, 0.06, 0.03];
const VOL = [0.24, 0.22, 0.28, 0.3, 0.2, 0.25, 0.14, 0.12];

const FACTORS = [
  { name: "Market (Mkt-RF)", beta: 1.08, tStat: 12.45, pValue: 0.0, sig: true },
  { name: "Size (SMB)", beta: -0.12, tStat: -1.82, pValue: 0.071, sig: false },
  { name: "Value (HML)", beta: 0.24, tStat: 3.15, pValue: 0.002, sig: true },
  { name: "Momentum (UMD)", beta: 0.18, tStat: 2.68, pValue: 0.008, sig: true },
  { name: "Quality (QMJ)", beta: 0.31, tStat: 4.22, pValue: 0.0, sig: true },
  { name: "Low Volatility", beta: 0.15, tStat: 1.95, pValue: 0.053, sig: false },
];

const REGRESSION = [
  { metric: "R-squared", value: "0.847" }, { metric: "Adj. R-squared", value: "0.841" },
  { metric: "F-statistic", value: "142.6" }, { metric: "Prob (F-stat)", value: "< 0.001" },
  { metric: "Durbin-Watson", value: "2.04" }, { metric: "AIC", value: "-1,245.8" },
  { metric: "BIC", value: "-1,218.3" }, { metric: "Observations", value: "252" },
];

const STAT_TESTS = [
  { test: "Jarque-Bera Normality", statistic: "4.82", pValue: "0.090", result: "Fail to reject" as const },
  { test: "Breusch-Pagan (Heteroskedasticity)", statistic: "6.21", pValue: "0.045", result: "Reject" as const },
  { test: "Ljung-Box (Autocorrelation)", statistic: "12.8", pValue: "0.235", result: "Fail to reject" as const },
  { test: "Augmented Dickey-Fuller", statistic: "-8.42", pValue: "0.000", result: "Reject" as const },
  { test: "ARCH-LM (GARCH effects)", statistic: "18.5", pValue: "0.002", result: "Reject" as const },
];

const ALLOCATION_COMPARISON = [
  { asset: "AAPL", current: 15, optimized: 18 }, { asset: "MSFT", current: 12, optimized: 16 },
  { asset: "GOOGL", current: 10, optimized: 8 }, { asset: "AMZN", current: 10, optimized: 12 },
  { asset: "JPM", current: 8, optimized: 5 }, { asset: "XOM", current: 5, optimized: 3 },
  { asset: "GLD", current: 20, optimized: 22 }, { asset: "TLT", current: 20, optimized: 16 },
];

const TOP_DRAWDOWNS = [
  { start: "Mar 2023", depth: -8.4, duration: "18 days", recovery: "32 days" },
  { start: "Aug 2023", depth: -6.2, duration: "12 days", recovery: "21 days" },
  { start: "Oct 2023", depth: -11.8, duration: "25 days", recovery: "45 days" },
  { start: "Apr 2024", depth: -5.1, duration: "8 days", recovery: "15 days" },
  { start: "Sep 2024", depth: -7.6, duration: "14 days", recovery: "28 days" },
];

const distributionData = Array.from({ length: 40 }, (_, i) => {
  const x = -4 + i * 0.2;
  const normal = Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
  const actual = normal * (1 + 0.15 * Math.sin(x * 2)) * (1 + 0.1 * (x > 0 ? -1 : 1));
  return { bin: x.toFixed(1), normal: +(normal * 100).toFixed(2), actual: +(actual * 100).toFixed(2) };
});

/* ════════════════════════════════════════════════════════════
   MAIN COMPONENT
════════════════════════════════════════════════════════════ */
export default function AIResearch() {
  const [activeTab, setActiveTab] = useState("ML Engine");

  // ── ML Engine state ──
  const [mlTab, setMlTab] = useState<(typeof ML_TABS)[number]>(ML_TABS[0]);
  const { data: indicesData } = useIndices();
  const { data: snapshotData } = useSnapshot();
  const liveData = indicesData ?? snapshotData ?? null;

  const liveFeatureInputs = useMemo(() => {
    if (!indicesData) return null;
    const allIndices = Object.values(indicesData).flat();
    if (allIndices.length === 0) return null;
    return allIndices.map((idx) => ({ feature: idx.name ?? idx.symbol, importance: Math.abs(idx.change?.percent ?? 0) / 100 })).sort((a, b) => b.importance - a.importance).slice(0, 10);
  }, [indicesData]);

  const displayFeatureImportance = liveFeatureInputs ?? featureImportance;

  const scenarioData = useMemo(() => {
    const rand = seededRandomML(77);
    const returns: number[] = [];
    for (let i = 0; i < 5000; i++) {
      const u1 = rand(), u2 = rand();
      const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
      returns.push(z * 0.045 + 0.005);
    }
    returns.sort((a, b) => a - b);
    const nBins = 60;
    const min = returns[0], max = returns[returns.length - 1];
    const binW = (max - min) / nBins;
    const bins: { ret: number; count: number }[] = [];
    for (let b = 0; b < nBins; b++) {
      const lo = min + b * binW, hi = lo + binW;
      const c = returns.filter((r) => r >= lo && r < hi).length;
      bins.push({ ret: +(((lo + hi) / 2) * 100).toFixed(1), count: c });
    }
    const p5 = +(returns[250] * 100).toFixed(2);
    const p25 = +(returns[1250] * 100).toFixed(2);
    const p50 = +(returns[2500] * 100).toFixed(2);
    const p75 = +(returns[3750] * 100).toFixed(2);
    const p95 = +(returns[4750] * 100).toFixed(2);
    const probProfit = +((returns.filter((r) => r > 0).length / returns.length) * 100).toFixed(1);
    return { bins, p5, p25, p50, p75, p95, probProfit };
  }, []);

  const anomalyData = useMemo(() => {
    const rand = seededRandomML(321);
    const data: { day: number; ret: number; zscore: number; anomaly: boolean }[] = [];
    const returns: number[] = [];
    for (let d = 0; d < 252; d++) {
      const u1 = rand(), u2 = rand();
      let z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
      if (d === 45 || d === 120 || d === 185 || d === 230) z *= 3.5;
      const ret = z * 0.015;
      returns.push(ret);
      const w = Math.min(d, 21);
      const slice = returns.slice(Math.max(0, d - w));
      const mu = slice.reduce((a, b) => a + b, 0) / slice.length;
      const sd = Math.sqrt(slice.reduce((a, b) => a + (b - mu) ** 2, 0) / slice.length) || 0.01;
      const zscore = (ret - mu) / sd;
      data.push({ day: d, ret: +(ret * 100).toFixed(2), zscore: +zscore.toFixed(2), anomaly: Math.abs(zscore) > 2.5 });
    }
    const recentVol = +(Math.sqrt(252) * Math.sqrt(returns.slice(-21).reduce((a, b) => a + b * b, 0) / 21) * 100).toFixed(1);
    const longVol = +(Math.sqrt(252) * Math.sqrt(returns.reduce((a, b) => a + b * b, 0) / returns.length) * 100).toFixed(1);
    const bubbleScore = +((recentVol / longVol - 1) * 100).toFixed(1);
    const nAnomalies = data.filter((d) => d.anomaly).length;
    return { data, recentVol, longVol, bubbleScore, nAnomalies };
  }, []);

  // ── Advanced Analysis state ──
  const [advTab, setAdvTab] = useState<(typeof ADV_TABS)[number]>(ADV_TABS[0]);

  const { portfolios, minVar, maxSharpe, equalWeight } = useMemo(() => {
    const rng = sRng(42);
    const n = EF_TICKERS.length;
    const pts: { vol: number; ret: number; sharpe: number; weights: number[] }[] = [];
    for (let i = 0; i < 5000; i++) {
      const raw = Array.from({ length: n }, () => rng());
      const sum = raw.reduce((a, b) => a + b, 0);
      const w = raw.map((v) => v / sum);
      const ret = w.reduce((s, wi, j) => s + wi * MU[j], 0);
      const vol = Math.sqrt(w.reduce((s, wi, j) => s + (wi * VOL[j]) ** 2, 0) * (1 + 0.3 * (rng() - 0.5)));
      pts.push({ vol: +vol.toFixed(4), ret: +ret.toFixed(4), sharpe: +(ret / vol).toFixed(3), weights: w });
    }
    const mv = pts.reduce((best, p) => (p.vol < best.vol ? p : best), pts[0]);
    const ms = pts.reduce((best, p) => (p.sharpe > best.sharpe ? p : best), pts[0]);
    const ew = { vol: +Math.sqrt(VOL.reduce((s, v) => s + (v / n) ** 2, 0)).toFixed(4), ret: +MU.reduce((s, m) => s + m / n, 0).toFixed(4), sharpe: 0, weights: Array(n).fill(1 / n) };
    ew.sharpe = +(ew.ret / ew.vol).toFixed(3);
    return { portfolios: pts, minVar: mv, maxSharpe: ms, equalWeight: ew };
  }, []);

  const mcPaths = useMemo(() => {
    const rng = sRng(99);
    const nPaths = 200, steps = 252 * 5, dt = 1 / 252, mu = 0.07, sigma = 0.15, S0 = 100000;
    const percentiles: { day: number; p5: number; p25: number; p50: number; p75: number; p95: number }[] = [];
    const allPaths: number[][] = Array.from({ length: nPaths }, () => [S0]);
    for (let d = 1; d <= steps; d++) {
      for (let p = 0; p < nPaths; p++) {
        const u1 = rng(), u2 = rng();
        const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
        allPaths[p][d] = allPaths[p][d - 1] * Math.exp((mu - 0.5 * sigma ** 2) * dt + sigma * Math.sqrt(dt) * z);
      }
      if (d % 21 === 0 || d === steps) {
        const vals = allPaths.map((p) => p[d]).sort((a, b) => a - b);
        percentiles.push({ day: d, p5: +vals[Math.floor(nPaths * 0.05)].toFixed(0), p25: +vals[Math.floor(nPaths * 0.25)].toFixed(0), p50: +vals[Math.floor(nPaths * 0.5)].toFixed(0), p75: +vals[Math.floor(nPaths * 0.75)].toFixed(0), p95: +vals[Math.floor(nPaths * 0.95)].toFixed(0) });
      }
    }
    const finals = allPaths.map((p) => p[steps]);
    return { percentiles, finalMedian: +finals.sort((a, b) => a - b)[100].toFixed(0), finals };
  }, []);

  const backtestData = useMemo(() => {
    const rngS = sRng(42), rngB = sRng(99), days = 504;
    const strategy: number[] = [100000], benchmark: number[] = [100000], drawdown: number[] = [0];
    let maxS = 100000;
    for (let i = 1; i < days; i++) {
      strategy[i] = strategy[i - 1] * (1 + 0.0004 + 0.01 * (rngS() - 0.5) * 2);
      benchmark[i] = benchmark[i - 1] * (1 + 0.0003 + 0.008 * (rngB() - 0.5) * 2);
      if (strategy[i] > maxS) maxS = strategy[i];
      drawdown[i] = strategy[i] / maxS - 1;
    }
    const totalReturnS = ((strategy[days - 1] - strategy[0]) / strategy[0]) * 100;
    const totalReturnB = ((benchmark[days - 1] - benchmark[0]) / benchmark[0]) * 100;
    const alpha = totalReturnS - totalReturnB;
    const annReturn = ((1 + totalReturnS / 100) ** (252 / days) - 1) * 100;
    const equityCurve = strategy.map((s, i) => ({ day: i, strategy: +s.toFixed(0), benchmark: +benchmark[i].toFixed(0) }));
    const drawdownCurve = drawdown.map((d, i) => ({ day: i, drawdown: +(d * 100).toFixed(2) }));
    const cumulativeReturn = strategy.map((s, i) => ({ day: i, value: +((s / strategy[0]) * 100).toFixed(2) }));
    return { equityCurve, drawdownCurve, cumulativeReturn, totalReturnS: +totalReturnS.toFixed(1), totalReturnB: +totalReturnB.toFixed(1), alpha: +alpha.toFixed(1), annReturn: +annReturn.toFixed(1), maxDrawdown: +(Math.min(...drawdown) * 100).toFixed(1), currentDrawdown: +(drawdown[days - 1] * 100).toFixed(1) };
  }, []);

  const scatterData = useMemo(() => portfolios.filter((_, i) => i % 10 === 0).map((p) => ({ vol: +(p.vol * 100).toFixed(1), ret: +(p.ret * 100).toFixed(1), sharpe: p.sharpe })), [portfolios]);

  return (
    <div style={{ color: "#F1F5F9" }}>
      <h1 style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 24, marginBottom: 4, color: "#D4AF37" }}>
        AI Research Lab
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        Machine learning models, factor analysis, efficient frontier & statistical testing
      </p>

      <div style={{ marginBottom: 20 }}>
        <Tabs
          tabs={["ML Engine", "Advanced Analysis"]}
          active={activeTab}
          onChange={setActiveTab}
        />
      </div>

      {/* ════ ML Engine ════ */}
      {activeTab === "ML Engine" && (
        <div>
          <div style={{ background: "rgba(168,85,247,0.12)", border: "1px solid rgba(168,85,247,0.35)", borderRadius: 8, padding: "8px 16px", marginBottom: 12, fontSize: 12, color: "#C084FC", fontFamily: "JetBrains Mono, monospace" }}>
            ⚗ RESEARCH / EXPERIMENTAL — Model accuracy figures (RF 72%, XGB 75%, LSTM) are illustrative demo values. No model is fitted to live data. Not valid for trading decisions.
          </div>
          {!liveData && (
            <div style={{ background: "rgba(245,158,11,0.15)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: 8, padding: "8px 16px", marginBottom: 16, fontSize: 13, color: "#F59E0B" }}>
              ⚠ Backend unreachable — displaying demo data
            </div>
          )}

          <div style={{ display: "flex", gap: 4, marginBottom: 16, flexWrap: "wrap" }}>
            {ML_TABS.map((t) => (
              <button key={t} onClick={() => setMlTab(t)} style={{ padding: "8px 14px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer", border: mlTab === t ? "1px solid rgba(212,175,55,0.5)" : "1px solid rgba(51,65,85,0.3)", backgroundColor: mlTab === t ? "rgba(212,175,55,0.15)" : "rgba(15,23,42,0.5)", color: mlTab === t ? "#D4AF37" : "#94A3B8" }}>
                {t}
              </button>
            ))}
          </div>

          {mlTab === "Models" && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16, marginBottom: 16 }}>
                {MODELS.map((m) => (
                  <Card key={m.abbr}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                      <div style={{ fontSize: 16, fontWeight: 700, color: m.color, fontFamily: "JetBrains Mono, monospace" }}>{m.name}</div>
                      <Badge variant={m.accuracy >= 74 ? "up" : m.accuracy >= 70 ? "warning" : "neutral"}>{m.accuracy}% Acc</Badge>
                    </div>
                    <p style={{ color: "#94A3B8", fontSize: 12, marginBottom: 12 }}>{m.description}</p>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                      {[{ label: "Precision", value: m.precision }, { label: "Recall", value: m.recall }, { label: "F1 Score", value: m.f1 }, { label: "AUC-ROC", value: m.auc }].map((metric) => (
                        <div key={metric.label} style={{ backgroundColor: "rgba(10,14,26,0.5)", borderRadius: 6, padding: "6px 8px" }}>
                          <div style={{ fontSize: 10, color: "#64748B" }}>{metric.label}</div>
                          <div style={{ fontSize: 14, fontWeight: 600, color: m.color, fontFamily: "JetBrains Mono, monospace" }}>
                            {typeof metric.value === "number" && metric.value < 1 ? metric.value.toFixed(2) : `${metric.value}%`}
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: 16 }}>
                <Card title="Prediction vs Actual" subtitle="60-day out-of-sample comparison">
                  <div style={{ width: "100%", height: 300 }}>
                    <ResponsiveContainer>
                      <LineChart data={predictionData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                        <XAxis dataKey="day" tick={{ fill: "#64748B", fontSize: 10 }} interval={9} />
                        <YAxis domain={["auto", "auto"]} tick={{ fill: "#64748B", fontSize: 10 }} />
                        <Tooltip contentStyle={ttStyle} formatter={(v: any) => `$${Number(v).toFixed(2)}`} />
                        <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                        <Line type="monotone" dataKey="actual" stroke="#F1F5F9" strokeWidth={2} dot={false} name="Actual" />
                        <Line type="monotone" dataKey="rf" stroke="#10B981" strokeWidth={1.5} dot={false} name="RF" strokeDasharray="4 4" />
                        <Line type="monotone" dataKey="xgb" stroke="#00D9FF" strokeWidth={1.5} dot={false} name="XGBoost" strokeDasharray="4 4" />
                        <Line type="monotone" dataKey="lstm" stroke="#D4AF37" strokeWidth={1.5} dot={false} name="LSTM" strokeDasharray="4 4" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
                <Card title="Feature Importance" subtitle={liveFeatureInputs ? "Live index change magnitudes — top 10" : "XGBoost model — top 10 features"}>
                  <div style={{ width: "100%", height: 300 }}>
                    <ResponsiveContainer>
                      <BarChart data={displayFeatureImportance} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                        <XAxis type="number" tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: any) => `${(v * 100).toFixed(0)}%`} />
                        <YAxis type="category" dataKey="feature" tick={{ fill: "#F1F5F9", fontSize: 11 }} width={110} />
                        <Tooltip contentStyle={ttStyle} formatter={(v: any) => `${(Number(v) * 100).toFixed(1)}%`} />
                        <Bar dataKey="importance" fill="#00D9FF" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
              </div>
            </>
          )}

          {mlTab === "Scenarios" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 10 }}>
                {[
                  { label: "Prob. of Profit", value: `${scenarioData.probProfit}%`, color: "#10B981" },
                  { label: "Crash (P5)", value: `${scenarioData.p5}%`, color: "#EF4444" },
                  { label: "Bear (P25)", value: `${scenarioData.p25}%`, color: "#F59E0B" },
                  { label: "Base (P50)", value: `${scenarioData.p50}%`, color: "#94A3B8" },
                  { label: "Bull (P75)", value: `${scenarioData.p75}%`, color: "#3B82F6" },
                  { label: "Extreme Bull (P95)", value: `${scenarioData.p95}%`, color: "#A855F7" },
                ].map((m) => (
                  <Card key={m.label}>
                    <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: m.color }}>{m.value}</div>
                  </Card>
                ))}
              </div>
              <Card title="Monte Carlo Return Distribution" subtitle="5,000 simulations — 5-day horizon">
                <div style={{ width: "100%", height: 320 }}>
                  <ResponsiveContainer>
                    <BarChart data={scenarioData.bins}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                      <XAxis dataKey="ret" tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: any) => `${v}%`} interval={9} />
                      <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                      <Tooltip contentStyle={ttStyle} formatter={(v: any) => v} labelFormatter={(l: any) => `Return: ${l}%`} />
                      <Bar dataKey="count" fill="rgba(0,217,255,0.5)" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          )}

          {mlTab === "Regime Detection" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: 12 }}>
                {ML_REGIMES.map((r) => (
                  <Card key={r.name}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                      <span style={{ fontSize: 14, fontWeight: 700, color: r.color, fontFamily: "JetBrains Mono, monospace" }}>{r.name}</span>
                      <Badge variant={r.name.startsWith("Bull") ? "up" : "down"}>{r.prob}%</Badge>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                      {[{ label: "Ann. Vol", value: r.vol }, { label: "Sharpe", value: r.sharpe }, { label: "Avg Return", value: r.avgRet }].map((m) => (
                        <div key={m.label} style={{ backgroundColor: "rgba(10,14,26,0.5)", borderRadius: 6, padding: "4px 6px" }}>
                          <div style={{ fontSize: 9, color: "#64748B" }}>{m.label}</div>
                          <div style={{ fontSize: 12, fontWeight: 600, color: "#F1F5F9", fontFamily: "JetBrains Mono, monospace" }}>{m.value}</div>
                        </div>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
              <Card title="Regime Transition Matrix" subtitle="Probability of transitioning between regimes">
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                        {["From \\ To", "Bull LoVol", "Bull HiVol", "Bear LoVol", "Bear HiVol"].map((h) => (
                          <th key={h} style={{ padding: "6px 10px", textAlign: h.startsWith("From") ? "left" : "right", color: "#94A3B8", fontWeight: 500 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {ML_TRANSITION_MATRIX.map((r) => (
                        <tr key={r.from} style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}>
                          <td style={{ padding: "6px 10px", fontWeight: 600, color: "#F1F5F9" }}>{r.from}</td>
                          {[r.bullLo, r.bullHi, r.bearLo, r.bearHi].map((v, i) => (
                            <td key={i} style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: v > 0.5 ? "#D4AF37" : v > 0.15 ? "#F1F5F9" : "#64748B" }}>
                              {(v * 100).toFixed(0)}%
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
              <div style={{ padding: "10px 14px", backgroundColor: "rgba(16,185,129,0.08)", borderRadius: 8, fontSize: 13, color: "#94A3B8" }}>
                <span style={{ color: "#10B981", fontWeight: 600 }}>Current Regime: Bull (Low Vol)</span>{" "}— Market is in the most favorable regime with low volatility and positive drift. Transition probability to bear regime: ~10%.
              </div>
            </div>
          )}

          {mlTab === "Anomaly Detection" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 10 }}>
                {[
                  { label: "Anomalies Detected", value: anomalyData.nAnomalies.toString(), color: "#EF4444" },
                  { label: "Recent Vol (21d)", value: `${anomalyData.recentVol}%`, color: "#F59E0B" },
                  { label: "Long-Run Vol", value: `${anomalyData.longVol}%`, color: "#94A3B8" },
                  { label: "Bubble Score", value: `${anomalyData.bubbleScore}%`, color: anomalyData.bubbleScore > 20 ? "#EF4444" : "#10B981" },
                ].map((m) => (
                  <Card key={m.label}>
                    <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: m.color }}>{m.value}</div>
                  </Card>
                ))}
              </div>
              <Card title="Return Z-Scores" subtitle="Rolling 21-day z-score — anomalies highlighted (|z| > 2.5)">
                <div style={{ width: "100%", height: 300 }}>
                  <ResponsiveContainer>
                    <AreaChart data={anomalyData.data}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                      <XAxis dataKey="day" tick={{ fill: "#64748B", fontSize: 10 }} interval={29} />
                      <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                      <Tooltip contentStyle={ttStyle} formatter={(v: any, name: any) => [Number(v).toFixed(2), name]} />
                      <Area type="monotone" dataKey="zscore" stroke="#00D9FF" fill="rgba(0,217,255,0.15)" strokeWidth={1.5} dot={false} name="Z-Score" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <Card title="Anomaly Events" subtitle="Days with |z-score| > 2.5">
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                        {["Day", "Return", "Z-Score", "Type"].map((h) => (
                          <th key={h} style={{ padding: "6px 10px", textAlign: h === "Day" ? "left" : "right", color: "#94A3B8", fontWeight: 500 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {anomalyData.data.filter((d) => d.anomaly).map((d) => (
                        <tr key={d.day} style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}>
                          <td style={{ padding: "6px 10px", fontFamily: "JetBrains Mono, monospace", color: "#F1F5F9" }}>D{d.day}</td>
                          <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: d.ret >= 0 ? "#10B981" : "#EF4444" }}>{d.ret}%</td>
                          <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#F59E0B" }}>{d.zscore}</td>
                          <td style={{ padding: "6px 10px", textAlign: "right" }}><Badge variant={d.zscore > 0 ? "up" : "down"}>{d.zscore > 0 ? "Spike" : "Crash"}</Badge></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* ════ Advanced Analysis ════ */}
      {activeTab === "Advanced Analysis" && (
        <div>
          {!liveData && (
            <div style={{ background: "rgba(245,158,11,0.15)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: 8, padding: "8px 16px", marginBottom: 16, fontSize: 13, color: "#F59E0B" }}>
              ⚠ Backend unreachable — displaying demo data
            </div>
          )}

          <div style={{ display: "flex", gap: 4, marginBottom: 16, flexWrap: "wrap" }}>
            {ADV_TABS.map((t) => (
              <button key={t} onClick={() => setAdvTab(t)} style={{ padding: "8px 16px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer", border: advTab === t ? "1px solid rgba(212,175,55,0.5)" : "1px solid rgba(51,65,85,0.3)", backgroundColor: advTab === t ? "rgba(212,175,55,0.15)" : "rgba(15,23,42,0.5)", color: advTab === t ? "#D4AF37" : "#94A3B8" }}>
                {t}
              </button>
            ))}
          </div>

          {advTab === "Efficient Frontier" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Card title="Efficient Frontier" subtitle={`5,000 random portfolios across ${EF_TICKERS.length} assets`}>
                <div style={{ width: "100%", height: 420 }}>
                  <ResponsiveContainer>
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                      <XAxis type="number" dataKey="vol" name="Volatility" tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: any) => `${v}%`} label={{ value: "Annualized Volatility (%)", position: "insideBottom", fill: "#64748B", fontSize: 11, offset: -2 }} />
                      <YAxis type="number" dataKey="ret" name="Return" tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: any) => `${v}%`} label={{ value: "Expected Return (%)", angle: -90, position: "insideLeft", fill: "#64748B", fontSize: 11 }} />
                      <Tooltip contentStyle={ttStyle} formatter={(v: any, name: any) => [`${v}%`, name]} />
                      <Scatter data={scatterData} name="Portfolios">
                        {scatterData.map((d, i) => <Cell key={i} fill={d.sharpe > 0.8 ? "#10B981" : d.sharpe > 0.5 ? "#D4AF37" : "rgba(100,116,139,0.4)"} />)}
                      </Scatter>
                      <Scatter data={[{ vol: +(minVar.vol * 100).toFixed(1), ret: +(minVar.ret * 100).toFixed(1), sharpe: minVar.sharpe }]} name="Min Variance" fill="#00D9FF" shape="diamond" />
                      <Scatter data={[{ vol: +(maxSharpe.vol * 100).toFixed(1), ret: +(maxSharpe.ret * 100).toFixed(1), sharpe: maxSharpe.sharpe }]} name="Max Sharpe" fill="#EF4444" shape="star" />
                      <Scatter data={[{ vol: +(equalWeight.vol * 100).toFixed(1), ret: +(equalWeight.ret * 100).toFixed(1), sharpe: equalWeight.sharpe }]} name="Equal Weight" fill="#F59E0B" shape="triangle" />
                      <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
                {[{ label: "Min Variance", data: minVar, color: "#00D9FF" }, { label: "Max Sharpe", data: maxSharpe, color: "#EF4444" }, { label: "Equal Weight", data: equalWeight, color: "#F59E0B" }].map((sp) => (
                  <Card key={sp.label} title={sp.label}>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 10 }}>
                      <div><div style={{ fontSize: 10, color: "#64748B" }}>Return</div><div style={{ fontFamily: "JetBrains Mono, monospace", color: "#10B981", fontWeight: 700 }}>{(sp.data.ret * 100).toFixed(1)}%</div></div>
                      <div><div style={{ fontSize: 10, color: "#64748B" }}>Volatility</div><div style={{ fontFamily: "JetBrains Mono, monospace", color: sp.color, fontWeight: 700 }}>{(sp.data.vol * 100).toFixed(1)}%</div></div>
                      <div><div style={{ fontSize: 10, color: "#64748B" }}>Sharpe</div><div style={{ fontFamily: "JetBrains Mono, monospace", color: "#D4AF37", fontWeight: 700 }}>{sp.data.sharpe}</div></div>
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                      {EF_TICKERS.map((t, i) => <span key={t} style={{ fontSize: 11, fontFamily: "JetBrains Mono, monospace", color: "#94A3B8", backgroundColor: "rgba(10,14,26,0.5)", padding: "2px 6px", borderRadius: 4 }}>{t}: {(sp.data.weights[i] * 100).toFixed(1)}%</span>)}
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {advTab === "Monte Carlo" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Card title="Monte Carlo Portfolio Simulation" subtitle="200 paths, 5-year horizon | mu=7%, sigma=15%, $100K initial">
                <div style={{ width: "100%", height: 400 }}>
                  <ResponsiveContainer>
                    <LineChart data={mcPaths.percentiles}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                      <XAxis dataKey="day" tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: any) => `Y${(v / 252).toFixed(1)}`} label={{ value: "Time", position: "insideBottom", fill: "#64748B", fontSize: 11, offset: -2 }} />
                      <YAxis tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: any) => `$${(v / 1000).toFixed(0)}K`} />
                      <Tooltip contentStyle={ttStyle} formatter={(v: any) => `$${Number(v).toLocaleString()}`} />
                      <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                      <Line type="monotone" dataKey="p95" stroke="rgba(16,185,129,0.4)" strokeWidth={1} dot={false} name="95th pct" />
                      <Line type="monotone" dataKey="p75" stroke="rgba(16,185,129,0.6)" strokeWidth={1.5} dot={false} name="75th pct" />
                      <Line type="monotone" dataKey="p50" stroke="#D4AF37" strokeWidth={2.5} dot={false} name="Median" />
                      <Line type="monotone" dataKey="p25" stroke="rgba(239,68,68,0.6)" strokeWidth={1.5} dot={false} name="25th pct" />
                      <Line type="monotone" dataKey="p5" stroke="rgba(239,68,68,0.4)" strokeWidth={1} dot={false} name="5th pct" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
                {[
                  { label: "Median Final", value: `$${(mcPaths.finalMedian / 1000).toFixed(0)}K`, color: "#D4AF37" },
                  { label: "5th Pct Final", value: `$${(mcPaths.percentiles[mcPaths.percentiles.length - 1]?.p5 / 1000 || 0).toFixed(0)}K`, color: "#EF4444" },
                  { label: "95th Pct Final", value: `$${(mcPaths.percentiles[mcPaths.percentiles.length - 1]?.p95 / 1000 || 0).toFixed(0)}K`, color: "#10B981" },
                  { label: "Simulations", value: "200", color: "#00D9FF" },
                  { label: "Horizon", value: "5 Years", color: "#94A3B8" },
                ].map((m) => (
                  <Card key={m.label}>
                    <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: m.color }}>{m.value}</div>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {advTab === "Factor Analysis" && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: 16 }}>
              <Card title="Factor Exposures" subtitle="Fama-French 5-factor + Momentum + Quality">
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                        {["Factor", "Beta", "t-Stat", "p-Value", "Sig."].map((h) => (
                          <th key={h} style={{ padding: "6px 10px", textAlign: h === "Factor" ? "left" : "right", color: "#94A3B8", fontWeight: 500 }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {FACTORS.map((f) => (
                        <tr key={f.name} style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}>
                          <td style={{ padding: "6px 10px", color: "#F1F5F9", fontSize: 12 }}>{f.name}</td>
                          <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: f.beta > 0 ? "#10B981" : "#EF4444" }}>{f.beta > 0 ? "+" : ""}{f.beta}</td>
                          <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#94A3B8" }}>{f.tStat}</td>
                          <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#94A3B8" }}>{f.pValue}</td>
                          <td style={{ padding: "6px 10px", textAlign: "right" }}><Badge variant={f.sig ? "up" : "neutral"}>{f.sig ? "★" : "—"}</Badge></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
              <Card title="Regression Summary" subtitle="OLS regression statistics">
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                  {REGRESSION.map((r) => (
                    <div key={r.metric} style={{ backgroundColor: "rgba(10,14,26,0.5)", borderRadius: 6, padding: "8px 10px" }}>
                      <div style={{ fontSize: 11, color: "#64748B" }}>{r.metric}</div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: "#F1F5F9", fontFamily: "JetBrains Mono, monospace" }}>{r.value}</div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {advTab === "Statistical Tests" && (
            <Card title="Statistical Tests" subtitle="Residual diagnostics & stationarity">
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                      {["Test", "Statistic", "p-Value", "H0"].map((h) => (
                        <th key={h} style={{ padding: "6px 10px", textAlign: h === "Test" ? "left" : "right", color: "#94A3B8", fontWeight: 500 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {STAT_TESTS.map((t) => (
                      <tr key={t.test} style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}>
                        <td style={{ padding: "6px 10px", color: "#F1F5F9", fontSize: 12 }}>{t.test}</td>
                        <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#94A3B8" }}>{t.statistic}</td>
                        <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#94A3B8" }}>{t.pValue}</td>
                        <td style={{ padding: "6px 10px", textAlign: "right" }}><Badge variant={t.result === "Reject" ? "down" : "up"}>{t.result}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {advTab === "Distribution" && (
            <Card title="Return Distribution" subtitle="Actual vs Normal distribution">
              <div style={{ width: "100%", height: 320 }}>
                <ResponsiveContainer>
                  <BarChart data={distributionData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                    <XAxis dataKey="bin" tick={{ fill: "#64748B", fontSize: 10 }} interval={4} label={{ value: "Std Dev", position: "insideBottom", fill: "#64748B", fontSize: 11, offset: -2 }} />
                    <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                    <Tooltip contentStyle={ttStyle} />
                    <Bar dataKey="actual" fill="rgba(0,217,255,0.5)" name="Actual" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="normal" fill="rgba(212,175,55,0.3)" name="Normal" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div style={{ display: "flex", justifyContent: "center", gap: 16, marginTop: 8 }}>
                {[{ label: "Skewness", value: "-0.32" }, { label: "Kurtosis", value: "3.85" }, { label: "Mean", value: "0.04%" }, { label: "Std Dev", value: "1.12%" }].map((s) => (
                  <div key={s.label} style={{ textAlign: "center" }}>
                    <div style={{ fontSize: 10, color: "#64748B" }}>{s.label}</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: "#F1F5F9", fontFamily: "JetBrains Mono, monospace" }}>{s.value}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {advTab === "Backtest" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <Card title="Backtest Parameters" subtitle="Strategy configuration">
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
                  {[{ label: "Start Date", value: "2023-01-01" }, { label: "End Date", value: "2024-12-31" }, { label: "Strategy", value: "Momentum + Mean Reversion" }].map((p) => (
                    <div key={p.label} style={{ backgroundColor: "rgba(10,14,26,0.5)", borderRadius: 6, padding: "8px 10px" }}>
                      <div style={{ fontSize: 11, color: "#64748B" }}>{p.label}</div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: "#F1F5F9", fontFamily: "JetBrains Mono, monospace" }}>{p.value}</div>
                    </div>
                  ))}
                  <div style={{ backgroundColor: "rgba(10,14,26,0.5)", borderRadius: 6, padding: "8px 10px" }}>
                    <div style={{ fontSize: 11, color: "#64748B", marginBottom: 4 }}>Rebalance Frequency</div>
                    <select defaultValue="Monthly" style={{ background: "#131823", border: "1px solid rgba(51,65,85,0.3)", borderRadius: 6, color: "#F1F5F9", padding: "4px 8px", fontSize: 13, fontFamily: "JetBrains Mono, monospace" }}>
                      <option>Monthly</option><option>Quarterly</option><option>Annual</option>
                    </select>
                  </div>
                </div>
              </Card>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
                {[
                  { label: "Total Return", value: `${backtestData.totalReturnS}%`, color: "#10B981" },
                  { label: "Benchmark Return", value: `${backtestData.totalReturnB}%`, color: "#00D9FF" },
                  { label: "Alpha", value: `${backtestData.alpha > 0 ? "+" : ""}${backtestData.alpha}%`, color: backtestData.alpha >= 0 ? "#10B981" : "#EF4444" },
                  { label: "Annualized Return", value: `${backtestData.annReturn}%`, color: "#D4AF37" },
                ].map((m) => (
                  <Card key={m.label}><div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div><div style={{ fontSize: 18, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: m.color }}>{m.value}</div></Card>
                ))}
              </div>
              <Card title="Equity Curve" subtitle="Strategy vs Benchmark ($100K initial)">
                <div style={{ width: "100%", height: 360 }}>
                  <ResponsiveContainer>
                    <LineChart data={backtestData.equityCurve}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                      <XAxis dataKey="day" tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: number) => `D${v}`} />
                      <YAxis tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}K`} />
                      <Tooltip contentStyle={ttStyle} formatter={(v: any) => `$${Number(v).toLocaleString()}`} />
                      <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                      <Line type="monotone" dataKey="strategy" stroke="#D4AF37" strokeWidth={2} dot={false} name="Strategy" />
                      <Line type="monotone" dataKey="benchmark" stroke="#00D9FF" strokeWidth={1.5} dot={false} name="Benchmark" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <Card title="Drawdown Overlay" subtitle="Drawdown % from peak">
                <div style={{ width: "100%", height: 200 }}>
                  <ResponsiveContainer>
                    <AreaChart data={backtestData.drawdownCurve}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                      <XAxis dataKey="day" tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: number) => `D${v}`} />
                      <YAxis tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: number) => `${v}%`} />
                      <Tooltip contentStyle={ttStyle} formatter={(v: any) => `${v}%`} />
                      <Area type="monotone" dataKey="drawdown" stroke="#EF4444" fill="rgba(239,68,68,0.2)" name="Drawdown" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>
          )}

          {advTab === "Optimization" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {[
                  { label: "Current Portfolio", sharpe: "0.62", ret: "8.1%", vol: "13.1%", maxDD: "-12.1%", accent: "#94A3B8" },
                  { label: "Optimized Portfolio", sharpe: "0.78", ret: "10.4%", vol: "13.3%", maxDD: "-9.8%", accent: "#D4AF37" },
                ].map((pf) => (
                  <Card key={pf.label}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: pf.accent, fontFamily: "JetBrains Mono, monospace", marginBottom: 10 }}>{pf.label}</div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                      {[{ k: "Sharpe", v: pf.sharpe }, { k: "Return", v: pf.ret }, { k: "Volatility", v: pf.vol }, { k: "Max Drawdown", v: pf.maxDD }].map((m) => (
                        <div key={m.k} style={{ backgroundColor: "rgba(10,14,26,0.5)", borderRadius: 6, padding: "6px 8px" }}>
                          <div style={{ fontSize: 10, color: "#64748B" }}>{m.k}</div>
                          <div style={{ fontSize: 15, fontWeight: 600, color: "#F1F5F9", fontFamily: "JetBrains Mono, monospace" }}>{m.v}</div>
                        </div>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
              <div style={{ display: "flex", justifyContent: "center" }}><Badge variant="up">+25.8% Sharpe improvement</Badge></div>
              <Card title="Allocation Comparison" subtitle="Current vs Optimized weights">
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                        {["Asset", "Current", "Optimized", "Change"].map((h) => <th key={h} style={{ padding: "6px 10px", textAlign: h === "Asset" ? "left" : "right", color: "#94A3B8", fontWeight: 500 }}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {ALLOCATION_COMPARISON.map((a) => {
                        const diff = a.optimized - a.current;
                        return (
                          <tr key={a.asset} style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}>
                            <td style={{ padding: "6px 10px", color: "#F1F5F9", fontFamily: "JetBrains Mono, monospace" }}>{a.asset}</td>
                            <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#94A3B8" }}>{a.current}%</td>
                            <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#D4AF37" }}>{a.optimized}%</td>
                            <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: diff > 0 ? "#10B981" : diff < 0 ? "#EF4444" : "#94A3B8" }}>{diff > 0 ? "+" : ""}{diff}%</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}

          {advTab === "Drawdown" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
                {[
                  { label: "Max Drawdown", value: `${backtestData.maxDrawdown}%`, color: "#EF4444" },
                  { label: "Current Drawdown", value: `${backtestData.currentDrawdown}%`, color: backtestData.currentDrawdown < -2 ? "#EF4444" : "#10B981" },
                  { label: "Avg Recovery Time", value: "28 days", color: "#D4AF37" },
                  { label: "Calmar Ratio", value: (backtestData.annReturn / Math.abs(backtestData.maxDrawdown)).toFixed(2), color: "#00D9FF" },
                ].map((m) => (
                  <Card key={m.label}><div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div><div style={{ fontSize: 18, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: m.color }}>{m.value}</div></Card>
                ))}
              </div>
              <Card title="Drawdown Chart" subtitle="Portfolio drawdown from peak over 504 days">
                <div style={{ width: "100%", height: 280 }}>
                  <ResponsiveContainer>
                    <AreaChart data={backtestData.drawdownCurve}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                      <XAxis dataKey="day" tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: number) => `D${v}`} />
                      <YAxis tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: number) => `${v}%`} />
                      <Tooltip contentStyle={ttStyle} formatter={(v: any) => `${v}%`} />
                      <Area type="monotone" dataKey="drawdown" stroke="#EF4444" fill="rgba(239,68,68,0.2)" name="Drawdown" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <Card title="Cumulative Return" subtitle="Portfolio value rebased to 100">
                <div style={{ width: "100%", height: 280 }}>
                  <ResponsiveContainer>
                    <LineChart data={backtestData.cumulativeReturn}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                      <XAxis dataKey="day" tick={{ fill: "#64748B", fontSize: 10 }} tickFormatter={(v: number) => `D${v}`} />
                      <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                      <Tooltip contentStyle={ttStyle} />
                      <Line type="monotone" dataKey="value" stroke="#10B981" strokeWidth={2} dot={false} name="Cumulative Return" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <Card title="Top 5 Drawdown Events" subtitle="Largest historical drawdowns">
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                        {["Period", "Depth", "Duration", "Recovery"].map((h) => <th key={h} style={{ padding: "6px 10px", textAlign: h === "Period" ? "left" : "right", color: "#94A3B8", fontWeight: 500 }}>{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {TOP_DRAWDOWNS.map((d) => (
                        <tr key={d.start} style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}>
                          <td style={{ padding: "6px 10px", color: "#F1F5F9" }}>{d.start}</td>
                          <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#EF4444" }}>{d.depth}%</td>
                          <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#94A3B8" }}>{d.duration}</td>
                          <td style={{ padding: "6px 10px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#D4AF37" }}>{d.recovery}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
