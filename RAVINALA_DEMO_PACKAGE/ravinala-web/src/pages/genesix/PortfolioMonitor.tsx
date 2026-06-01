import { useMemo, useState } from "react";
import {
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
import { Badge, Card } from "../../components/ui";
import { useIndices } from "../../hooks/useMarketData";

const TABS = [
  "Positions",
  "Performance",
  "Rebalancing",
  "Tax Harvesting",
] as const;
const PERIODS = [
  "1M",
  "3M",
  "6M",
  "YTD",
  "1Y",
  "3Y",
  "5Y",
  "Inception",
] as const;
const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
};

const POSITIONS = [
  {
    ticker: "AAPL",
    name: "Apple Inc.",
    qty: 150,
    avgCost: 178.5,
    current: 198.5,
    pnl: 3000,
    pnlPct: 11.2,
  },
  {
    ticker: "NVDA",
    name: "NVIDIA Corp.",
    qty: 80,
    avgCost: 680.0,
    current: 875.2,
    pnl: 15616,
    pnlPct: 28.7,
  },
  {
    ticker: "MSFT",
    name: "Microsoft Corp.",
    qty: 60,
    avgCost: 395.0,
    current: 425.2,
    pnl: 1812,
    pnlPct: 7.6,
  },
  {
    ticker: "GOOGL",
    name: "Alphabet Inc.",
    qty: 100,
    avgCost: 168.0,
    current: 178.3,
    pnl: 1030,
    pnlPct: 6.1,
  },
  {
    ticker: "AMZN",
    name: "Amazon.com",
    qty: 45,
    avgCost: 185.0,
    current: 192.8,
    pnl: 351,
    pnlPct: 4.2,
  },
  {
    ticker: "JPM",
    name: "JPMorgan Chase",
    qty: 70,
    avgCost: 198.0,
    current: 205.4,
    pnl: 518,
    pnlPct: 3.7,
  },
  {
    ticker: "TLT",
    name: "20+ Yr Treasury",
    qty: 200,
    avgCost: 98.5,
    current: 95.2,
    pnl: -660,
    pnlPct: -3.4,
  },
  {
    ticker: "GLD",
    name: "SPDR Gold",
    qty: 100,
    avgCost: 210.0,
    current: 222.5,
    pnl: 1250,
    pnlPct: 6.0,
  },
  {
    ticker: "TSLA",
    name: "Tesla Inc.",
    qty: 30,
    avgCost: 260.0,
    current: 242.8,
    pnl: -516,
    pnlPct: -6.6,
  },
  {
    ticker: "XOM",
    name: "Exxon Mobil",
    qty: 90,
    avgCost: 108.0,
    current: 112.4,
    pnl: 396,
    pnlPct: 4.1,
  },
];

const totalPnl = POSITIONS.reduce((s, p) => s + p.pnl, 0);
const totalValue = POSITIONS.reduce((s, p) => s + p.qty * p.current, 0);
const totalCost = POSITIONS.reduce((s, p) => s + p.qty * p.avgCost, 0);

// ── Allocation ──
const ALLOC_COLORS = [
  "#D4AF37",
  "#00D9FF",
  "#10B981",
  "#EF4444",
  "#A855F7",
  "#F59E0B",
  "#EC4899",
  "#3B82F6",
  "#84CC16",
  "#F97316",
];
const allocation = POSITIONS.map((p, i) => ({
  name: p.ticker,
  value: Math.round(p.qty * p.current),
  color: ALLOC_COLORS[i % ALLOC_COLORS.length],
}));

// ── Performance history ──
const PERF_DATA = Array.from({ length: 90 }, (_, i) => ({
  day: `D${i + 1}`,
  portfolio: +(100 + i * 0.12 + Math.sin(i * 0.08) * 4).toFixed(2),
  benchmark: +(100 + i * 0.09 + Math.sin(i * 0.06) * 3).toFixed(2),
}));

// ── Rebalancing targets ──
const REBALANCE = [
  {
    ticker: "AAPL",
    target: 12,
    current: +(
      ((POSITIONS[0].qty * POSITIONS[0].current) / totalValue) *
      100
    ).toFixed(1),
    action: "",
  },
  {
    ticker: "NVDA",
    target: 20,
    current: +(
      ((POSITIONS[1].qty * POSITIONS[1].current) / totalValue) *
      100
    ).toFixed(1),
    action: "",
  },
  {
    ticker: "MSFT",
    target: 10,
    current: +(
      ((POSITIONS[2].qty * POSITIONS[2].current) / totalValue) *
      100
    ).toFixed(1),
    action: "",
  },
  {
    ticker: "GOOGL",
    target: 8,
    current: +(
      ((POSITIONS[3].qty * POSITIONS[3].current) / totalValue) *
      100
    ).toFixed(1),
    action: "",
  },
  {
    ticker: "AMZN",
    target: 5,
    current: +(
      ((POSITIONS[4].qty * POSITIONS[4].current) / totalValue) *
      100
    ).toFixed(1),
    action: "",
  },
  {
    ticker: "JPM",
    target: 8,
    current: +(
      ((POSITIONS[5].qty * POSITIONS[5].current) / totalValue) *
      100
    ).toFixed(1),
    action: "",
  },
  {
    ticker: "TLT",
    target: 15,
    current: +(
      ((POSITIONS[6].qty * POSITIONS[6].current) / totalValue) *
      100
    ).toFixed(1),
    action: "",
  },
  {
    ticker: "GLD",
    target: 10,
    current: +(
      ((POSITIONS[7].qty * POSITIONS[7].current) / totalValue) *
      100
    ).toFixed(1),
    action: "",
  },
  {
    ticker: "TSLA",
    target: 4,
    current: +(
      ((POSITIONS[8].qty * POSITIONS[8].current) / totalValue) *
      100
    ).toFixed(1),
    action: "",
  },
  {
    ticker: "XOM",
    target: 8,
    current: +(
      ((POSITIONS[9].qty * POSITIONS[9].current) / totalValue) *
      100
    ).toFixed(1),
    action: "",
  },
].map((r) => ({
  ...r,
  action:
    +r.current - r.target > 0.5
      ? "SELL"
      : +r.current - r.target < -0.5
        ? "BUY"
        : "HOLD",
}));

// ── Tax harvesting candidates ──
const TAX_HARVEST = POSITIONS.filter((p) => p.pnl < 0).map((p) => ({
  ticker: p.ticker,
  loss: p.pnl,
  daysHeld: p.ticker === "TLT" ? 245 : 89,
  longTerm: p.ticker === "TLT",
  replacement: p.ticker === "TLT" ? "BND" : p.ticker === "TSLA" ? "RIVN" : "—",
}));

export default function PortfolioMonitor() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const [perfPeriod, setPerfPeriod] = useState<string>("1Y");
  const { data: indicesData } = useIndices();
  const usingFallback = !indicesData;

  const keyIndices = useMemo(() => {
    if (!indicesData) return [];
    const targets = ["^GSPC", "^IXIC", "^DJI"];
    return Object.values(indicesData)
      .flat()
      .filter((idx) => targets.includes(idx.symbol));
  }, [indicesData]);

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
        Portfolio Monitor
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        Live positions & P&L tracking
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

      {/* Summary cards (always visible) */}
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
            label: "Portfolio Value",
            value: `$${(totalValue / 1000).toFixed(0)}K`,
            color: "#F1F5F9",
          },
          {
            label: "Total P&L",
            value: `${totalPnl >= 0 ? "+" : ""}$${totalPnl.toLocaleString()}`,
            color: totalPnl >= 0 ? "#10B981" : "#EF4444",
          },
          {
            label: "Total Return",
            value: `${((totalPnl / totalCost) * 100).toFixed(1)}%`,
            color: totalPnl >= 0 ? "#10B981" : "#EF4444",
          },
          {
            label: "Positions",
            value: `${POSITIONS.length}`,
            color: "#D4AF37",
          },
          { label: "Day P&L", value: "+$2,840", color: "#10B981" },
        ].map((m) => (
          <Card key={m.label}>
            <div style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}>
              {m.label}
            </div>
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

      {/* ═══ Positions ═══ */}
      {tab === "Positions" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card title="Live Positions">
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
                      "Ticker",
                      "Name",
                      "Qty",
                      "Avg Cost",
                      "Current",
                      "Value",
                      "P&L",
                      "P&L %",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "8px 10px",
                          textAlign:
                            h === "Ticker" || h === "Name" ? "left" : "right",
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
                  {POSITIONS.map((p) => (
                    <tr
                      key={p.ticker}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td
                        style={{
                          padding: "8px 10px",
                          fontFamily: "JetBrains Mono, monospace",
                          fontWeight: 700,
                          color: "#D4AF37",
                        }}
                      >
                        {p.ticker}
                      </td>
                      <td style={{ padding: "8px 10px", color: "#F1F5F9" }}>
                        {p.name}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#94A3B8",
                        }}
                      >
                        {p.qty}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#94A3B8",
                        }}
                      >
                        ${p.avgCost.toFixed(2)}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#F1F5F9",
                        }}
                      >
                        ${p.current.toFixed(2)}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#F1F5F9",
                        }}
                      >
                        ${(p.qty * p.current).toLocaleString()}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: p.pnl >= 0 ? "#10B981" : "#EF4444",
                        }}
                      >
                        {p.pnl >= 0 ? "+" : ""}${p.pnl.toLocaleString()}
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "right" }}>
                        <Badge variant={p.pnlPct >= 0 ? "up" : "down"}>
                          {p.pnlPct >= 0 ? "+" : ""}
                          {p.pnlPct}%
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <Card title="Allocation">
            <div style={{ width: "100%", height: 280 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={allocation}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    dataKey="value"
                    nameKey="name"
                    paddingAngle={2}
                  >
                    {allocation.map((a, i) => (
                      <Cell key={i} fill={a.color} />
                    ))}
                  </Pie>
                  <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any) => `$${Number(v).toLocaleString()}`}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}

      {/* ═══ Performance ═══ */}
      {tab === "Performance" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPerfPeriod(p)}
                style={{
                  padding: "6px 14px",
                  borderRadius: 20,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                  border:
                    perfPeriod === p
                      ? "1px solid rgba(212,175,55,0.5)"
                      : "1px solid rgba(51,65,85,0.3)",
                  backgroundColor:
                    perfPeriod === p
                      ? "rgba(212,175,55,0.15)"
                      : "rgba(15,23,42,0.5)",
                  color: perfPeriod === p ? "#D4AF37" : "#94A3B8",
                }}
              >
                {p}
              </button>
            ))}
          </div>
          <Card
            title={`Portfolio vs Benchmark (${perfPeriod})`}
            subtitle="Normalized to 100"
          >
            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <LineChart data={PERF_DATA}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="day"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    interval={14}
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fill: "#64748B", fontSize: 10 }}
                  />
                  <Tooltip contentStyle={ttStyle} />
                  <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                  <Line
                    type="monotone"
                    dataKey="portfolio"
                    stroke="#D4AF37"
                    strokeWidth={2}
                    dot={false}
                    name="Portfolio"
                  />
                  <Line
                    type="monotone"
                    dataKey="benchmark"
                    stroke="#64748B"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                    name="S&P 500"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
              gap: 10,
            }}
          >
            {[
              { label: "Alpha (ann.)", value: "+3.2%", color: "#10B981" },
              { label: "Beta", value: "1.05", color: "#94A3B8" },
              { label: "Sharpe Ratio", value: "1.42", color: "#D4AF37" },
              { label: "Max Drawdown", value: "-6.8%", color: "#EF4444" },
              { label: "Ann. Return", value: "+18.4%", color: "#10B981" },
              { label: "Ann. Volatility", value: "14.2%", color: "#F59E0B" },
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
          <Card title="Impact & Income Metrics">
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                gap: 10,
              }}
            >
              {[
                {
                  label: "Carbon Avoidance",
                  value: "125 metric tons CO₂eq",
                  delta: "vs benchmark",
                  color: "#10B981",
                },
                {
                  label: "ESG Score",
                  value: "78/100",
                  delta: "vs benchmark 65/100",
                  color: "#A855F7",
                },
                {
                  label: "Dividend Yield",
                  value: "2.15%",
                  delta: "vs benchmark 1.84%",
                  color: "#D4AF37",
                },
              ].map((m) => (
                <div key={m.label}>
                  <div
                    style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}
                  >
                    {m.label}
                  </div>
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
                  <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>
                    {m.delta}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ═══ Rebalancing ═══ */}
      {tab === "Rebalancing" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card
            title="Rebalancing Analysis"
            subtitle="Current allocation vs model targets"
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
                    {["Ticker", "Current %", "Target %", "Drift", "Action"].map(
                      (h) => (
                        <th
                          key={h}
                          style={{
                            padding: "8px 10px",
                            textAlign: h === "Ticker" ? "left" : "right",
                            color: "#94A3B8",
                            fontWeight: 500,
                          }}
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {REBALANCE.map((r) => {
                    const drift = +(+r.current - r.target).toFixed(1);
                    return (
                      <tr
                        key={r.ticker}
                        style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                      >
                        <td
                          style={{
                            padding: "8px 10px",
                            fontFamily: "JetBrains Mono, monospace",
                            fontWeight: 700,
                            color: "#D4AF37",
                          }}
                        >
                          {r.ticker}
                        </td>
                        <td
                          style={{
                            padding: "8px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#F1F5F9",
                          }}
                        >
                          {r.current}%
                        </td>
                        <td
                          style={{
                            padding: "8px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color: "#94A3B8",
                          }}
                        >
                          {r.target}%
                        </td>
                        <td
                          style={{
                            padding: "8px 10px",
                            textAlign: "right",
                            fontFamily: "JetBrains Mono, monospace",
                            color:
                              Math.abs(drift) > 0.5
                                ? drift > 0
                                  ? "#F59E0B"
                                  : "#00D9FF"
                                : "#64748B",
                          }}
                        >
                          {drift > 0 ? "+" : ""}
                          {drift}%
                        </td>
                        <td style={{ padding: "8px 10px", textAlign: "right" }}>
                          <Badge
                            variant={
                              r.action === "SELL"
                                ? "down"
                                : r.action === "BUY"
                                  ? "up"
                                  : "neutral"
                            }
                          >
                            {r.action}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
          <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
            <button
              style={{
                padding: "10px 20px",
                borderRadius: 8,
                border: "none",
                fontWeight: 700,
                fontSize: 13,
                cursor: "pointer",
                backgroundColor: "#D4AF37",
                color: "#0A0E1A",
              }}
            >
              Rebalance Now
            </button>
            <button
              style={{
                padding: "10px 20px",
                borderRadius: 8,
                border: "1px solid #D4AF37",
                fontWeight: 700,
                fontSize: 13,
                cursor: "pointer",
                backgroundColor: "transparent",
                color: "#D4AF37",
              }}
            >
              Schedule Rebalancing
            </button>
          </div>
        </div>
      )}

      {/* ═══ Tax Harvesting ═══ */}
      {tab === "Tax Harvesting" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
              gap: 10,
            }}
          >
            {[
              {
                label: "Total Unrealized Losses",
                value: `$${Math.abs(TAX_HARVEST.reduce((a, b) => a + b.loss, 0)).toLocaleString()}`,
                color: "#EF4444",
              },
              {
                label: "Harvestable (Short-Term)",
                value: `$${Math.abs(TAX_HARVEST.filter((t) => !t.longTerm).reduce((a, b) => a + b.loss, 0)).toLocaleString()}`,
                color: "#F59E0B",
              },
              {
                label: "Harvestable (Long-Term)",
                value: `$${Math.abs(TAX_HARVEST.filter((t) => t.longTerm).reduce((a, b) => a + b.loss, 0)).toLocaleString()}`,
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
            title="Tax-Loss Harvesting Candidates"
            subtitle="Positions with unrealized losses"
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
                      "Ticker",
                      "Unrealized Loss",
                      "Days Held",
                      "Term",
                      "Replacement",
                      "Wash Sale Risk",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "8px 10px",
                          textAlign: h === "Ticker" ? "left" : "right",
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
                  {TAX_HARVEST.map((t) => (
                    <tr
                      key={t.ticker}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td
                        style={{
                          padding: "8px 10px",
                          fontFamily: "JetBrains Mono, monospace",
                          fontWeight: 700,
                          color: "#D4AF37",
                        }}
                      >
                        {t.ticker}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#EF4444",
                        }}
                      >
                        -${Math.abs(t.loss).toLocaleString()}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#94A3B8",
                        }}
                      >
                        {t.daysHeld}d
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "right" }}>
                        <Badge variant={t.longTerm ? "info" : "warning"}>
                          {t.longTerm ? "Long-Term" : "Short-Term"}
                        </Badge>
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#00D9FF",
                        }}
                      >
                        {t.replacement}
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "right" }}>
                        <Badge variant="neutral">None</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <div
            style={{
              padding: "10px 14px",
              backgroundColor: "rgba(245,158,11,0.08)",
              borderRadius: 8,
              fontSize: 12,
              color: "#94A3B8",
            }}
          >
            <strong style={{ color: "#F59E0B" }}>Wash Sale Rule:</strong> Cannot
            repurchase substantially identical securities within 30 days before
            or after realizing a loss. Suggested replacements maintain similar
            market exposure without triggering wash sale.
          </div>
          <button
            style={{
              padding: "10px 20px",
              borderRadius: 8,
              border: "none",
              fontWeight: 700,
              fontSize: 13,
              cursor: "pointer",
              backgroundColor: "#10B981",
              color: "#0A0E1A",
            }}
          >
            Execute Harvesting Trades
          </button>
        </div>
      )}
    </div>
  );
}
