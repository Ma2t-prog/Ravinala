import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Card } from "../../components/ui";
import { useIndices } from "../../hooks/useMarketData";

// Seeded PRNG
function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return s / 2147483647;
  };
}

const TABS = [
  "Models",
  "Scenarios",
  "Regime Detection",
  "Anomaly Detection",
] as const;

const MODELS = [
  {
    name: "Random Forest",
    abbr: "RF",
    accuracy: 72.4,
    precision: 71.8,
    recall: 73.1,
    f1: 72.4,
    auc: 0.78,
    color: "#10B981",
    description: "Ensemble tree-based model for daily direction prediction",
  },
  {
    name: "XGBoost",
    abbr: "XGB",
    accuracy: 75.1,
    precision: 74.6,
    recall: 75.8,
    f1: 75.2,
    auc: 0.81,
    color: "#00D9FF",
    description: "Gradient boosting with optimized hyperparameters",
  },
  {
    name: "LSTM Network",
    abbr: "LSTM",
    accuracy: 68.9,
    precision: 69.2,
    recall: 68.5,
    f1: 68.8,
    auc: 0.74,
    color: "#D4AF37",
    description: "Recurrent neural network for sequence prediction",
  },
];

const predictionData = Array.from({ length: 60 }, (_, i) => ({
  day: `D${i + 1}`,
  actual: +(185 + Math.sin(i * 0.1) * 12 + i * 0.12).toFixed(2),
  rf: +(
    185 +
    Math.sin(i * 0.1) * 11 +
    i * 0.12 +
    Math.sin(i * 0.4) * 1.5
  ).toFixed(2),
  xgb: +(
    185 +
    Math.sin(i * 0.1) * 11.5 +
    i * 0.12 +
    Math.sin(i * 0.5) * 1
  ).toFixed(2),
  lstm: +(
    185 +
    Math.sin(i * 0.1) * 10 +
    i * 0.12 +
    Math.sin(i * 0.3) * 2.5
  ).toFixed(2),
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

// ── Regime Detection data ──
const REGIMES = [
  {
    name: "Bull (Low Vol)",
    color: "#10B981",
    prob: 42,
    vol: "12.1%",
    sharpe: "1.85",
    avgRet: "+0.08%/d",
  },
  {
    name: "Bull (High Vol)",
    color: "#F59E0B",
    prob: 18,
    vol: "22.4%",
    sharpe: "0.91",
    avgRet: "+0.05%/d",
  },
  {
    name: "Bear (Low Vol)",
    color: "#3B82F6",
    prob: 15,
    vol: "15.8%",
    sharpe: "-0.42",
    avgRet: "-0.03%/d",
  },
  {
    name: "Bear (High Vol)",
    color: "#EF4444",
    prob: 25,
    vol: "31.2%",
    sharpe: "-1.15",
    avgRet: "-0.12%/d",
  },
];

const TRANSITION_MATRIX = [
  {
    from: "Bull LoVol",
    bullLo: 0.82,
    bullHi: 0.08,
    bearLo: 0.06,
    bearHi: 0.04,
  },
  {
    from: "Bull HiVol",
    bullLo: 0.25,
    bullHi: 0.55,
    bearLo: 0.05,
    bearHi: 0.15,
  },
  { from: "Bear LoVol", bullLo: 0.15, bullHi: 0.1, bearLo: 0.6, bearHi: 0.15 },
  {
    from: "Bear HiVol",
    bullLo: 0.05,
    bullHi: 0.12,
    bearLo: 0.18,
    bearHi: 0.65,
  },
];

const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
};

export default function MLEngine() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const { data: indicesData } = useIndices();
  const liveData = indicesData ?? null;

  // Derive live feature inputs from index data when available
  const liveFeatureInputs = useMemo(() => {
    if (!indicesData) return null;
    const allIndices = Object.values(indicesData).flat();
    if (allIndices.length === 0) return null;
    return allIndices
      .map((idx) => ({
        feature: idx.name ?? idx.symbol,
        importance: Math.abs(idx.change?.percent ?? 0) / 100,
      }))
      .sort((a, b) => b.importance - a.importance)
      .slice(0, 10);
  }, [indicesData]);

  const displayFeatureImportance = liveFeatureInputs ?? featureImportance;

  // Scenario distribution (5000 MC sims)
  const scenarioData = useMemo(() => {
    const rand = seededRandom(77);
    const returns: number[] = [];
    for (let i = 0; i < 5000; i++) {
      const u1 = rand(),
        u2 = rand();
      const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
      returns.push(z * 0.045 + 0.005); // 5-day returns
    }
    returns.sort((a, b) => a - b);
    // Histogram bins
    const nBins = 60;
    const min = returns[0],
      max = returns[returns.length - 1];
    const binW = (max - min) / nBins;
    const bins: { ret: number; count: number }[] = [];
    for (let b = 0; b < nBins; b++) {
      const lo = min + b * binW,
        hi = lo + binW;
      const c = returns.filter((r) => r >= lo && r < hi).length;
      bins.push({ ret: +(((lo + hi) / 2) * 100).toFixed(1), count: c });
    }
    const p5 = +(returns[250] * 100).toFixed(2);
    const p25 = +(returns[1250] * 100).toFixed(2);
    const p50 = +(returns[2500] * 100).toFixed(2);
    const p75 = +(returns[3750] * 100).toFixed(2);
    const p95 = +(returns[4750] * 100).toFixed(2);
    const probProfit = +(
      (returns.filter((r) => r > 0).length / returns.length) *
      100
    ).toFixed(1);
    return { bins, p5, p25, p50, p75, p95, probProfit };
  }, []);

  // Anomaly detection data
  const anomalyData = useMemo(() => {
    const rand = seededRandom(321);
    const data: {
      day: number;
      ret: number;
      zscore: number;
      anomaly: boolean;
    }[] = [];
    const returns: number[] = [];
    for (let d = 0; d < 252; d++) {
      const u1 = rand(),
        u2 = rand();
      let z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
      // inject anomalies
      if (d === 45 || d === 120 || d === 185 || d === 230) z *= 3.5;
      const ret = z * 0.015;
      returns.push(ret);
      const w = Math.min(d, 21);
      const slice = returns.slice(Math.max(0, d - w));
      const mu = slice.reduce((a, b) => a + b, 0) / slice.length;
      const sd =
        Math.sqrt(
          slice.reduce((a, b) => a + (b - mu) ** 2, 0) / slice.length,
        ) || 0.01;
      const zscore = (ret - mu) / sd;
      data.push({
        day: d,
        ret: +(ret * 100).toFixed(2),
        zscore: +zscore.toFixed(2),
        anomaly: Math.abs(zscore) > 2.5,
      });
    }
    const recentVol = +(
      Math.sqrt(252) *
      Math.sqrt(returns.slice(-21).reduce((a, b) => a + b * b, 0) / 21) *
      100
    ).toFixed(1);
    const longVol = +(
      Math.sqrt(252) *
      Math.sqrt(returns.reduce((a, b) => a + b * b, 0) / returns.length) *
      100
    ).toFixed(1);
    const bubbleScore = +((recentVol / longVol - 1) * 100).toFixed(1);
    const nAnomalies = data.filter((d) => d.anomaly).length;
    return { data, recentVol, longVol, bubbleScore, nAnomalies };
  }, []);

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
        ML Engine — Lab (Experimental)
      </h1>
      {/* ÉTAPE 1 — RESEARCH DISCLAIMER: all model metrics are illustrative demo values */}
      <div
        style={{
          background: "rgba(168,85,247,0.12)",
          border: "1px solid rgba(168,85,247,0.35)",
          borderRadius: 8,
          padding: "8px 16px",
          marginBottom: 12,
          fontSize: 12,
          color: "#C084FC",
          fontFamily: "JetBrains Mono, monospace",
        }}
      >
        ⚗ RESEARCH / EXPERIMENTAL — Model accuracy figures (RF 72%, XGB 75%,
        LSTM) are illustrative demo values. No model is fitted to live data. Not
        valid for trading decisions.
      </div>
      {!liveData && (
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
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        Machine learning models for market prediction
      </p>

      <div
        style={{ display: "flex", gap: 4, marginBottom: 16, flexWrap: "wrap" }}
      >
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "8px 14px",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              border:
                tab === t
                  ? "1px solid rgba(212,175,55,0.5)"
                  : "1px solid rgba(51,65,85,0.3)",
              backgroundColor:
                tab === t ? "rgba(212,175,55,0.15)" : "rgba(15,23,42,0.5)",
              color: tab === t ? "#D4AF37" : "#94A3B8",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ═══ Models ═══ */}
      {tab === "Models" && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: 16,
              marginBottom: 16,
            }}
          >
            {MODELS.map((m) => (
              <Card key={m.abbr}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 8,
                  }}
                >
                  <div
                    style={{
                      fontSize: 16,
                      fontWeight: 700,
                      color: m.color,
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {m.name}
                  </div>
                  <Badge
                    variant={
                      m.accuracy >= 74
                        ? "up"
                        : m.accuracy >= 70
                          ? "warning"
                          : "neutral"
                    }
                  >
                    {m.accuracy}% Acc
                  </Badge>
                </div>
                <p style={{ color: "#94A3B8", fontSize: 12, marginBottom: 12 }}>
                  {m.description}
                </p>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 8,
                  }}
                >
                  {[
                    { label: "Precision", value: m.precision },
                    { label: "Recall", value: m.recall },
                    { label: "F1 Score", value: m.f1 },
                    { label: "AUC-ROC", value: m.auc },
                  ].map((metric) => (
                    <div
                      key={metric.label}
                      style={{
                        backgroundColor: "rgba(10,14,26,0.5)",
                        borderRadius: 6,
                        padding: "6px 8px",
                      }}
                    >
                      <div style={{ fontSize: 10, color: "#64748B" }}>
                        {metric.label}
                      </div>
                      <div
                        style={{
                          fontSize: 14,
                          fontWeight: 600,
                          color: m.color,
                          fontFamily: "JetBrains Mono, monospace",
                        }}
                      >
                        {typeof metric.value === "number" && metric.value < 1
                          ? metric.value.toFixed(2)
                          : `${metric.value}%`}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
              gap: 16,
            }}
          >
            <Card
              title="Prediction vs Actual"
              subtitle="60-day out-of-sample comparison"
            >
              <div style={{ width: "100%", height: 300 }}>
                <ResponsiveContainer>
                  <LineChart data={predictionData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="day"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                      interval={9}
                    />
                    <YAxis
                      domain={["auto", "auto"]}
                      tick={{ fill: "#64748B", fontSize: 10 }}
                    />
                    <Tooltip
                      contentStyle={ttStyle}
                      formatter={(v: any) => `$${Number(v).toFixed(2)}`}
                    />
                    <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                    <Line
                      type="monotone"
                      dataKey="actual"
                      stroke="#F1F5F9"
                      strokeWidth={2}
                      dot={false}
                      name="Actual"
                    />
                    <Line
                      type="monotone"
                      dataKey="rf"
                      stroke="#10B981"
                      strokeWidth={1.5}
                      dot={false}
                      name="RF"
                      strokeDasharray="4 4"
                    />
                    <Line
                      type="monotone"
                      dataKey="xgb"
                      stroke="#00D9FF"
                      strokeWidth={1.5}
                      dot={false}
                      name="XGBoost"
                      strokeDasharray="4 4"
                    />
                    <Line
                      type="monotone"
                      dataKey="lstm"
                      stroke="#D4AF37"
                      strokeWidth={1.5}
                      dot={false}
                      name="LSTM"
                      strokeDasharray="4 4"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <Card
              title="Feature Importance"
              subtitle={
                liveFeatureInputs
                  ? "Live index change magnitudes — top 10"
                  : "XGBoost model — top 10 features"
              }
            >
              <div style={{ width: "100%", height: 300 }}>
                <ResponsiveContainer>
                  <BarChart data={displayFeatureImportance} layout="vertical">
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      type="number"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                      tickFormatter={(v: any) => `${(v * 100).toFixed(0)}%`}
                    />
                    <YAxis
                      type="category"
                      dataKey="feature"
                      tick={{ fill: "#F1F5F9", fontSize: 11 }}
                      width={110}
                    />
                    <Tooltip
                      contentStyle={ttStyle}
                      formatter={(v: any) => `${(Number(v) * 100).toFixed(1)}%`}
                    />
                    <Bar
                      dataKey="importance"
                      fill="#00D9FF"
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}

      {/* ═══ Scenarios ═══ */}
      {tab === "Scenarios" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
              gap: 10,
            }}
          >
            {[
              {
                label: "Prob. of Profit",
                value: `${scenarioData.probProfit}%`,
                color: "#10B981",
              },
              {
                label: "Crash (P5)",
                value: `${scenarioData.p5}%`,
                color: "#EF4444",
              },
              {
                label: "Bear (P25)",
                value: `${scenarioData.p25}%`,
                color: "#F59E0B",
              },
              {
                label: "Base (P50)",
                value: `${scenarioData.p50}%`,
                color: "#94A3B8",
              },
              {
                label: "Bull (P75)",
                value: `${scenarioData.p75}%`,
                color: "#3B82F6",
              },
              {
                label: "Extreme Bull (P95)",
                value: `${scenarioData.p95}%`,
                color: "#A855F7",
              },
            ].map((m) => (
              <Card key={m.label}>
                <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
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
              </Card>
            ))}
          </div>
          <Card
            title="Monte Carlo Return Distribution"
            subtitle="5,000 simulations — 5-day horizon"
          >
            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <BarChart data={scenarioData.bins}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="ret"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    tickFormatter={(v: any) => `${v}%`}
                    interval={9}
                  />
                  <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any) => v}
                    labelFormatter={(l: any) => `Return: ${l}%`}
                  />
                  <Bar
                    dataKey="count"
                    fill="rgba(0,217,255,0.5)"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}

      {/* ═══ Regime Detection ═══ */}
      {tab === "Regime Detection" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
              gap: 12,
            }}
          >
            {REGIMES.map((r) => (
              <Card key={r.name}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 14,
                      fontWeight: 700,
                      color: r.color,
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {r.name}
                  </span>
                  <Badge variant={r.name.startsWith("Bull") ? "up" : "down"}>
                    {r.prob}%
                  </Badge>
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr 1fr",
                    gap: 8,
                  }}
                >
                  {[
                    { label: "Ann. Vol", value: r.vol },
                    { label: "Sharpe", value: r.sharpe },
                    { label: "Avg Return", value: r.avgRet },
                  ].map((m) => (
                    <div
                      key={m.label}
                      style={{
                        backgroundColor: "rgba(10,14,26,0.5)",
                        borderRadius: 6,
                        padding: "4px 6px",
                      }}
                    >
                      <div style={{ fontSize: 9, color: "#64748B" }}>
                        {m.label}
                      </div>
                      <div
                        style={{
                          fontSize: 12,
                          fontWeight: 600,
                          color: "#F1F5F9",
                          fontFamily: "JetBrains Mono, monospace",
                        }}
                      >
                        {m.value}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
          <Card
            title="Regime Transition Matrix"
            subtitle="Probability of transitioning between regimes"
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
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    {[
                      "From \\ To",
                      "Bull LoVol",
                      "Bull HiVol",
                      "Bear LoVol",
                      "Bear HiVol",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 10px",
                          textAlign: h.startsWith("From") ? "left" : "right",
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
                  {TRANSITION_MATRIX.map((r) => (
                    <tr
                      key={r.from}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td
                        style={{
                          padding: "6px 10px",
                          fontWeight: 600,
                          color: "#F1F5F9",
                        }}
                      >
                        {r.from}
                      </td>
                      {[r.bullLo, r.bullHi, r.bearLo, r.bearHi].map((v, i) => (
                        <td
                          key={i}
                          style={{
                            padding: "6px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color:
                              v > 0.5
                                ? "#D4AF37"
                                : v > 0.15
                                  ? "#F1F5F9"
                                  : "#64748B",
                          }}
                        >
                          {(v * 100).toFixed(0)}%
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <div
            style={{
              padding: "10px 14px",
              backgroundColor: "rgba(16,185,129,0.08)",
              borderRadius: 8,
              fontSize: 13,
              color: "#94A3B8",
            }}
          >
            <span style={{ color: "#10B981", fontWeight: 600 }}>
              Current Regime: Bull (Low Vol)
            </span>{" "}
            — Market is in the most favorable regime with low volatility and
            positive drift. Transition probability to bear regime: ~10%.
          </div>
        </div>
      )}

      {/* ═══ Anomaly Detection ═══ */}
      {tab === "Anomaly Detection" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
              gap: 10,
            }}
          >
            {[
              {
                label: "Anomalies Detected",
                value: anomalyData.nAnomalies.toString(),
                color: "#EF4444",
              },
              {
                label: "Recent Vol (21d)",
                value: `${anomalyData.recentVol}%`,
                color: "#F59E0B",
              },
              {
                label: "Long-Run Vol",
                value: `${anomalyData.longVol}%`,
                color: "#94A3B8",
              },
              {
                label: "Bubble Score",
                value: `${anomalyData.bubbleScore}%`,
                color: anomalyData.bubbleScore > 20 ? "#EF4444" : "#10B981",
              },
            ].map((m) => (
              <Card key={m.label}>
                <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
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
              </Card>
            ))}
          </div>
          <Card
            title="Return Z-Scores"
            subtitle="Rolling 21-day z-score — anomalies highlighted (|z| > 2.5)"
          >
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <AreaChart data={anomalyData.data}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="day"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    interval={29}
                  />
                  <YAxis tick={{ fill: "#64748B", fontSize: 10 }} />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any, name: any) => [
                      Number(v).toFixed(2),
                      name,
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="zscore"
                    stroke="#00D9FF"
                    fill="rgba(0,217,255,0.15)"
                    strokeWidth={1.5}
                    dot={false}
                    name="Z-Score"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title="Anomaly Events" subtitle="Days with |z-score| > 2.5">
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    {["Day", "Return", "Z-Score", "Type"].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 10px",
                          textAlign: h === "Day" ? "left" : "right",
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
                  {anomalyData.data
                    .filter((d) => d.anomaly)
                    .map((d) => (
                      <tr
                        key={d.day}
                        style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                      >
                        <td
                          style={{
                            padding: "6px 10px",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#F1F5F9",
                          }}
                        >
                          D{d.day}
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color: d.ret >= 0 ? "#10B981" : "#EF4444",
                          }}
                        >
                          {d.ret}%
                        </td>
                        <td
                          style={{
                            padding: "6px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#F59E0B",
                          }}
                        >
                          {d.zscore}
                        </td>
                        <td style={{ padding: "6px 10px", textAlign: "right" }}>
                          <Badge variant={d.zscore > 0 ? "up" : "down"}>
                            {d.zscore > 0 ? "Spike" : "Crash"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
