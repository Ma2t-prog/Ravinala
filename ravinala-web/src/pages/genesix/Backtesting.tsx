import { useState } from "react";
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
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "../../components/ui";
import { useIndices } from "../../hooks/useMarketData";

const TABS = [
  "Equity Curve",
  "Drawdown",
  "Rolling Returns",
  "Attribution",
  "Risk Metrics",
  "Heatmap",
] as const;

// ── Seeded RNG ──
function sRng(s: number) {
  return () => {
    s = (s * 16807) % 2147483647;
    return s / 2147483647;
  };
}

const equityData = (() => {
  const rng = sRng(42);
  const data: { day: string; strategy: number; benchmark: number }[] = [];
  let strat = 10000,
    bench = 10000;
  for (let i = 0; i < 504; i++) {
    const u1 = rng(),
      u2 = rng();
    const z1 = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    const z2 = Math.sqrt(-2 * Math.log(u1)) * Math.sin(2 * Math.PI * u2);
    strat *= 1 + 0.0004 + 0.01 * z1;
    bench *= 1 + 0.0003 + 0.012 * z2;
    data.push({
      day: `D${i + 1}`,
      strategy: +strat.toFixed(0),
      benchmark: +bench.toFixed(0),
    });
  }
  return data;
})();

const drawdownData = equityData.map((d, i) => {
  const peak = Math.max(...equityData.slice(0, i + 1).map((e) => e.strategy));
  const dd = ((d.strategy - peak) / peak) * 100;
  const bPeak = Math.max(...equityData.slice(0, i + 1).map((e) => e.benchmark));
  const bDd = ((d.benchmark - bPeak) / bPeak) * 100;
  return { day: d.day, stratDD: +dd.toFixed(2), benchDD: +bDd.toFixed(2) };
});

// Rolling returns (21d, 63d, 252d)
const rollingData = equityData
  .map((d, i) => {
    const r21 =
      i >= 21 ? (d.strategy / equityData[i - 21].strategy - 1) * 100 : 0;
    const r63 =
      i >= 63
        ? (d.strategy / equityData[i - 63].strategy - 1) * (252 / 63) * 100
        : 0;
    const r252 =
      i >= 252 ? (d.strategy / equityData[i - 252].strategy - 1) * 100 : 0;
    return {
      day: d.day,
      "21d": +r21.toFixed(2),
      "63d": +r63.toFixed(2),
      "252d": +r252.toFixed(2),
    };
  })
  .filter((_, i) => i >= 63);

// Attribution data
const ATTRIBUTION = [
  { factor: "Stock Selection", contribution: 5.8, color: "#10B981" },
  { factor: "Sector Allocation", contribution: 3.2, color: "#00D9FF" },
  { factor: "Market Timing", contribution: 2.1, color: "#D4AF37" },
  { factor: "Currency Effect", contribution: -0.4, color: "#EF4444" },
  { factor: "Transaction Costs", contribution: -1.2, color: "#F97316" },
  { factor: "Management Fee", contribution: -0.8, color: "#A855F7" },
];

// Risk metrics over time
const riskTimeData = Array.from({ length: 24 }, (_, i) => ({
  month: `M${i + 1}`,
  vol: +(12 + Math.sin(i * 0.5) * 4 + Math.cos(i * 0.3) * 2).toFixed(1),
  sharpe: +(1.8 + Math.sin(i * 0.4) * 0.6).toFixed(2),
  beta: +(0.95 + Math.sin(i * 0.3) * 0.15).toFixed(2),
}));

const STATS = [
  { label: "Total Return", value: "+42.8%", bench: "+28.1%" },
  { label: "Ann. Return", value: "+38.2%", bench: "+24.6%" },
  { label: "Ann. Volatility", value: "14.8%", bench: "16.2%" },
  { label: "Sharpe Ratio", value: "2.12", bench: "1.34" },
  { label: "Sortino Ratio", value: "2.87", bench: "1.72" },
  { label: "Max Drawdown", value: "-8.4%", bench: "-12.1%" },
  { label: "Win Rate", value: "58.2%", bench: "52.4%" },
  { label: "Profit Factor", value: "1.84", bench: "1.42" },
  { label: "Calmar Ratio", value: "4.55", bench: "2.03" },
  { label: "Trades", value: "342", bench: "N/A" },
];

const MONTHS = [
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
];
const YEARS = [2024, 2025, 2026];
const monthlyReturns: Record<number, number[]> = {
  2024: [2.1, -0.8, 3.4, 1.2, -1.5, 2.8, 0.6, -2.1, 3.2, 1.8, 4.1, 2.5],
  2025: [1.8, 3.2, -0.4, 2.6, 1.1, -1.8, 3.5, 2.0, -0.7, 4.2, 1.5, 3.0],
  2026: [2.4, 1.6, 3.8, 0, 0, 0, 0, 0, 0, 0, 0, 0],
};

const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
};

export default function Backtesting() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const { data: indicesData } = useIndices();
  const liveData = indicesData ?? null;

  // Use live benchmark name if available
  const liveBenchmarkName = (() => {
    if (!indicesData) return null;
    const allIndices = Object.values(indicesData).flat();
    const spx = allIndices.find(
      (idx) =>
        idx.symbol?.includes("SPX") ||
        idx.symbol?.includes("GSPC") ||
        idx.name?.includes("S&P"),
    );
    return spx?.name ?? allIndices[0]?.name ?? null;
  })();
  const benchmarkLabel = liveBenchmarkName ?? "S&P 500";

  // Compute final stats
  const finalStrat = equityData[equityData.length - 1].strategy;
  const finalBench = equityData[equityData.length - 1].benchmark;
  const stratReturn = (((finalStrat - 10000) / 10000) * 100).toFixed(1);
  const benchReturn = (((finalBench - 10000) / 10000) * 100).toFixed(1);

  return (
    <div style={{ color: "#F1F5F9" }}>
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
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 4,
          color: "#D4AF37",
        }}
      >
        Backtesting
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 12, fontSize: 14 }}>
        Strategy backtest: Momentum + Mean Reversion Hybrid | 504 trading days
      </p>

      {/* Summary */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
          gap: 10,
          marginBottom: 16,
        }}
      >
        {[
          {
            label: "Total Return",
            value: `+${stratReturn}%`,
            color: "#10B981",
          },
          { label: "Benchmark", value: `+${benchReturn}%`, color: "#64748B" },
          {
            label: "Alpha",
            value: `+${(+stratReturn - +benchReturn).toFixed(1)}%`,
            color: "#D4AF37",
          },
          { label: "Sharpe", value: "2.12", color: "#00D9FF" },
          { label: "Sortino", value: "2.87", color: "#00D9FF" },
          {
            label: "Max DD",
            value: `${Math.min(...drawdownData.map((d) => d.stratDD)).toFixed(1)}%`,
            color: "#EF4444",
          },
          { label: "Win Rate", value: "58.2%", color: "#10B981" },
          { label: "Calmar", value: "4.55", color: "#D4AF37" },
        ].map((m) => (
          <Card key={m.label}>
            <div style={{ fontSize: 10, color: "#64748B" }}>{m.label}</div>
            <div
              style={{
                fontSize: 16,
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

      {/* Tabs */}
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

      {/* ═══ Equity Curve ═══ */}
      {tab === "Equity Curve" && (
        <Card
          title="Equity Curve"
          subtitle={`Strategy vs ${benchmarkLabel} Benchmark`}
        >
          <div style={{ width: "100%", height: 380 }}>
            <ResponsiveContainer>
              <LineChart data={equityData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(51,65,85,0.3)"
                />
                <XAxis
                  dataKey="day"
                  tick={{ fill: "#64748B", fontSize: 10 }}
                  interval={80}
                />
                <YAxis
                  tick={{ fill: "#64748B", fontSize: 10 }}
                  tickFormatter={(v: any) => `$${(v / 1000).toFixed(0)}K`}
                />
                <Tooltip
                  contentStyle={ttStyle}
                  formatter={(v: any) => `$${Number(v).toLocaleString()}`}
                />
                <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                <Line
                  type="monotone"
                  dataKey="strategy"
                  stroke="#D4AF37"
                  strokeWidth={2}
                  dot={false}
                  name="Strategy"
                />
                <Line
                  type="monotone"
                  dataKey="benchmark"
                  stroke="#64748B"
                  strokeWidth={1.5}
                  dot={false}
                  name={benchmarkLabel}
                  strokeDasharray="4 4"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* ═══ Drawdown ═══ */}
      {tab === "Drawdown" && (
        <Card
          title="Drawdown Comparison"
          subtitle="Strategy vs Benchmark peak-to-trough"
        >
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <AreaChart data={drawdownData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(51,65,85,0.3)"
                />
                <XAxis
                  dataKey="day"
                  tick={{ fill: "#64748B", fontSize: 10 }}
                  interval={80}
                />
                <YAxis
                  tick={{ fill: "#64748B", fontSize: 10 }}
                  tickFormatter={(v: any) => `${v}%`}
                />
                <Tooltip
                  contentStyle={ttStyle}
                  formatter={(v: any) => `${Number(v).toFixed(2)}%`}
                />
                <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                <Area
                  type="monotone"
                  dataKey="stratDD"
                  stroke="#EF4444"
                  fill="rgba(239,68,68,0.2)"
                  name="Strategy DD"
                />
                <Area
                  type="monotone"
                  dataKey="benchDD"
                  stroke="#64748B"
                  fill="rgba(100,116,139,0.1)"
                  name="Benchmark DD"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* ═══ Rolling Returns ═══ */}
      {tab === "Rolling Returns" && (
        <Card
          title="Rolling Returns"
          subtitle="21-day, 63-day (annualized), 252-day rolling returns"
        >
          <div style={{ width: "100%", height: 380 }}>
            <ResponsiveContainer>
              <LineChart data={rollingData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(51,65,85,0.3)"
                />
                <XAxis
                  dataKey="day"
                  tick={{ fill: "#64748B", fontSize: 10 }}
                  interval={60}
                />
                <YAxis
                  tick={{ fill: "#64748B", fontSize: 10 }}
                  tickFormatter={(v: any) => `${v}%`}
                />
                <Tooltip
                  contentStyle={ttStyle}
                  formatter={(v: any) => `${Number(v).toFixed(2)}%`}
                />
                <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                <Line
                  type="monotone"
                  dataKey="21d"
                  stroke="#00D9FF"
                  strokeWidth={1.5}
                  dot={false}
                  name="21-Day"
                />
                <Line
                  type="monotone"
                  dataKey="63d"
                  stroke="#D4AF37"
                  strokeWidth={1.5}
                  dot={false}
                  name="63-Day (Ann.)"
                />
                <Line
                  type="monotone"
                  dataKey="252d"
                  stroke="#10B981"
                  strokeWidth={2}
                  dot={false}
                  name="252-Day"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {/* ═══ Attribution ═══ */}
      {tab === "Attribution" && (
        <Card
          title="Performance Attribution"
          subtitle="Breakdown of excess return sources"
        >
          <div style={{ width: "100%", height: 350 }}>
            <ResponsiveContainer>
              <BarChart data={ATTRIBUTION}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(51,65,85,0.3)"
                />
                <XAxis
                  dataKey="factor"
                  tick={{ fill: "#F1F5F9", fontSize: 11 }}
                />
                <YAxis
                  tick={{ fill: "#64748B", fontSize: 10 }}
                  tickFormatter={(v: any) => `${v}%`}
                />
                <Tooltip
                  contentStyle={ttStyle}
                  formatter={(v: any) => `${v}%`}
                />
                <Bar
                  dataKey="contribution"
                  name="Contribution"
                  radius={[4, 4, 0, 0]}
                >
                  {ATTRIBUTION.map((a, i) => (
                    <Cell key={i} fill={a.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div style={{ marginTop: 12, fontSize: 13, color: "#94A3B8" }}>
            Total Alpha:{" "}
            <strong
              style={{
                color: "#D4AF37",
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              {ATTRIBUTION.reduce((s, a) => s + a.contribution, 0).toFixed(1)}%
            </strong>{" "}
            (sum of all attribution factors)
          </div>
        </Card>
      )}

      {/* ═══ Risk Metrics ═══ */}
      {tab === "Risk Metrics" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card
            title="Risk Metrics Over Time"
            subtitle="24-month rolling volatility, Sharpe, and beta"
          >
            <div style={{ width: "100%", height: 350 }}>
              <ResponsiveContainer>
                <LineChart data={riskTimeData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="month"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                  />
                  <YAxis
                    yAxisId="left"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                  />
                  <Tooltip contentStyle={ttStyle} />
                  <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="vol"
                    stroke="#EF4444"
                    strokeWidth={2}
                    dot={false}
                    name="Volatility (%)"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="sharpe"
                    stroke="#D4AF37"
                    strokeWidth={2}
                    dot={false}
                    name="Sharpe Ratio"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="beta"
                    stroke="#00D9FF"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                    name="Beta"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title="Performance Statistics">
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
                    <th
                      style={{
                        padding: "6px 10px",
                        textAlign: "left",
                        color: "#94A3B8",
                        fontWeight: 500,
                      }}
                    >
                      Metric
                    </th>
                    <th
                      style={{
                        padding: "6px 10px",
                        textAlign: "right",
                        color: "#D4AF37",
                        fontWeight: 500,
                      }}
                    >
                      Strategy
                    </th>
                    <th
                      style={{
                        padding: "6px 10px",
                        textAlign: "right",
                        color: "#64748B",
                        fontWeight: 500,
                      }}
                    >
                      Benchmark
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {STATS.map((s) => (
                    <tr
                      key={s.label}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td style={{ padding: "6px 10px", color: "#F1F5F9" }}>
                        {s.label}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#D4AF37",
                        }}
                      >
                        {s.value}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#64748B",
                        }}
                      >
                        {s.bench}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* ═══ Monthly Heatmap ═══ */}
      {tab === "Heatmap" && (
        <Card
          title="Monthly Returns (%)"
          subtitle="Calendar year returns heatmap"
        >
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "separate",
                borderSpacing: 3,
                fontSize: 12,
              }}
            >
              <thead>
                <tr>
                  <th style={{ padding: 6, color: "#94A3B8", fontWeight: 500 }}>
                    Year
                  </th>
                  {MONTHS.map((m) => (
                    <th
                      key={m}
                      style={{
                        padding: 6,
                        color: "#94A3B8",
                        fontWeight: 500,
                        textAlign: "center",
                      }}
                    >
                      {m}
                    </th>
                  ))}
                  <th
                    style={{
                      padding: 6,
                      color: "#94A3B8",
                      fontWeight: 500,
                      textAlign: "center",
                    }}
                  >
                    YTD
                  </th>
                </tr>
              </thead>
              <tbody>
                {YEARS.map((y) => {
                  const rets = monthlyReturns[y];
                  const ytd = rets.reduce((a, b) => a + b, 0);
                  return (
                    <tr key={y}>
                      <td
                        style={{
                          padding: 6,
                          color: "#F1F5F9",
                          fontWeight: 600,
                          fontFamily: "JetBrains Mono, monospace",
                        }}
                      >
                        {y}
                      </td>
                      {rets.map((r, i) => (
                        <td
                          key={i}
                          style={{
                            padding: 6,
                            textAlign: "center",
                            fontFamily: "JetBrains Mono, monospace",
                            backgroundColor:
                              r === 0
                                ? "transparent"
                                : r > 0
                                  ? `rgba(16,185,129,${Math.min(r / 5, 0.6)})`
                                  : `rgba(239,68,68,${Math.min(Math.abs(r) / 5, 0.6)})`,
                            color: r === 0 ? "#64748B" : "#F1F5F9",
                            borderRadius: 4,
                          }}
                        >
                          {r === 0 && y === 2026 && i > 2
                            ? "-"
                            : `${r > 0 ? "+" : ""}${r.toFixed(1)}`}
                        </td>
                      ))}
                      <td
                        style={{
                          padding: 6,
                          textAlign: "center",
                          fontFamily: "JetBrains Mono, monospace",
                          fontWeight: 700,
                          color: ytd >= 0 ? "#10B981" : "#EF4444",
                        }}
                      >
                        {ytd > 0 ? "+" : ""}
                        {ytd.toFixed(1)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
