import { useState } from "react";
import {
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
import { useSnapshot } from "../../hooks/useMarketData";

const TABS = [
  "Overview",
  "Fundamentals",
  "Risk",
  "Peers",
  "ESG",
  "News",
] as const;

const priceData = Array.from({ length: 90 }, (_, i) => ({
  date: `Day ${i + 1}`,
  price: +(
    185 +
    Math.sin(i * 0.07) * 15 +
    i * 0.15 +
    Math.sin(i * 0.2) * 3
  ).toFixed(2),
}));

const METRICS = [
  { label: "Market Cap", value: "$3.2T", color: "#D4AF37" },
  { label: "P/E Ratio", value: "28.5x", color: "#00D9FF" },
  { label: "EPS (TTM)", value: "$6.73", color: "#10B981" },
  { label: "Div Yield", value: "0.51%", color: "#F59E0B" },
  { label: "Revenue (TTM)", value: "$391B", color: "#A855F7" },
  { label: "Gross Margin", value: "45.6%", color: "#00D9FF" },
  { label: "Debt/Equity", value: "1.87", color: "#EF4444" },
  { label: "ROE", value: "160.9%", color: "#10B981" },
];

const PEERS = [
  { ticker: "AAPL", price: 198.5, pe: 28.5, mcap: "3.2T", ytd: 12.4 },
  { ticker: "MSFT", price: 425.2, pe: 33.2, mcap: "2.9T", ytd: 8.7 },
  { ticker: "GOOGL", price: 178.3, pe: 24.1, mcap: "2.1T", ytd: 15.2 },
  { ticker: "AMZN", price: 192.8, pe: 58.3, mcap: "1.9T", ytd: 22.1 },
  { ticker: "META", price: 520.1, pe: 25.8, mcap: "1.3T", ytd: 42.5 },
];

const analystData = [
  { label: "Strong Buy", count: 18, color: "#10B981" },
  { label: "Buy", count: 12, color: "#22C55E" },
  { label: "Hold", count: 8, color: "#F59E0B" },
  { label: "Sell", count: 2, color: "#F97316" },
  { label: "Strong Sell", count: 0, color: "#EF4444" },
];

const totalAnalysts = analystData.reduce((s, a) => s + a.count, 0);

// ── Income Statement (quarterly) ──
const INCOME_Q = [
  {
    q: "Q1 2024",
    revenue: 119.6,
    netIncome: 33.9,
    grossMargin: 46.6,
    opMargin: 30.7,
  },
  {
    q: "Q2 2024",
    revenue: 117.0,
    netIncome: 32.5,
    grossMargin: 45.5,
    opMargin: 29.8,
  },
  {
    q: "Q3 2024",
    revenue: 123.4,
    netIncome: 35.2,
    grossMargin: 46.2,
    opMargin: 31.2,
  },
  {
    q: "Q4 2024",
    revenue: 130.8,
    netIncome: 38.1,
    grossMargin: 47.1,
    opMargin: 32.4,
  },
];

// ── Balance Sheet ──
const BALANCE_ITEMS = [
  { item: "Total Assets", value: "$352.6B" },
  { item: "Total Liabilities", value: "$290.4B" },
  { item: "Total Equity", value: "$62.2B" },
  { item: "Cash & Equivalents", value: "$29.9B" },
  { item: "Long-term Debt", value: "$98.1B" },
  { item: "Current Ratio", value: "0.99" },
  { item: "Debt/Equity", value: "1.87" },
  { item: "Book Value/Share", value: "$4.38" },
];

// ── Risk metrics ──
const RISK_METRICS = [
  { label: "Beta (5Y)", value: "1.24", color: "#00D9FF" },
  { label: "Sharpe (1Y)", value: "1.82", color: "#D4AF37" },
  { label: "Volatility (1Y)", value: "22.4%", color: "#EF4444" },
  { label: "Max Drawdown", value: "-14.2%", color: "#EF4444" },
  { label: "VaR 95% (1D)", value: "-2.14%", color: "#F97316" },
  { label: "Sortino", value: "2.41", color: "#10B981" },
];

const volHistory = Array.from({ length: 90 }, (_, i) => ({
  date: `D${i + 1}`,
  vol30: +(20 + Math.sin(i * 0.1) * 5 + Math.cos(i * 0.05) * 3).toFixed(1),
  vol60: +(22 + Math.sin(i * 0.08) * 4).toFixed(1),
}));

// ── ESG ──
const ESG = {
  overall: 72,
  env: 68,
  social: 75,
  governance: 78,
  peers: [
    { ticker: "AAPL", score: 72, rating: "AA" },
    { ticker: "MSFT", score: 80, rating: "AAA" },
    { ticker: "GOOGL", score: 65, rating: "A" },
    { ticker: "AMZN", score: 55, rating: "BBB" },
    { ticker: "META", score: 48, rating: "BB" },
  ],
};

// ── News ──
const NEWS = [
  {
    time: "2h ago",
    title: "Apple Intelligence rollout boosts iPhone 16 demand in Asia",
    source: "Bloomberg",
    sentiment: "positive" as const,
  },
  {
    time: "5h ago",
    title: "Apple reaches $3.5T market cap milestone",
    source: "Reuters",
    sentiment: "positive" as const,
  },
  {
    time: "8h ago",
    title: "EU Commission probes Apple's App Store fees post-DMA",
    source: "FT",
    sentiment: "negative" as const,
  },
  {
    time: "1d ago",
    title: "Supply chain signals strong Mac refresh cycle in Q1 2025",
    source: "Nikkei Asia",
    sentiment: "positive" as const,
  },
  {
    time: "1d ago",
    title: "Analyst roundup: 30 of 40 rate AAPL as Buy or Strong Buy",
    source: "MarketWatch",
    sentiment: "neutral" as const,
  },
  {
    time: "2d ago",
    title: "Apple Services revenue hits record $24.8B in Q4",
    source: "CNBC",
    sentiment: "positive" as const,
  },
];

const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
};

export default function InstrumentAnalysis() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const { data: snapshotData } = useSnapshot();
  const usingFallback = !snapshotData;

  return (
    <div style={{ color: "#F1F5F9" }}>
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
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 12,
          marginBottom: 4,
        }}
      >
        <h1
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 24,
            color: "#D4AF37",
          }}
        >
          AAPL
        </h1>
        <span style={{ color: "#94A3B8", fontSize: 16 }}>Apple Inc.</span>
        <Badge variant="info">NASDAQ</Badge>
      </div>
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
            fontSize: 28,
            fontWeight: 700,
            color: "#F1F5F9",
          }}
        >
          $198.50
        </span>
        <Badge variant="up">+2.35 (+1.20%)</Badge>
      </div>

      {/* Tab bar */}
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

      {/* ═══ Overview ═══ */}
      {tab === "Overview" && (
        <>
          <Card title="Price Chart (90D)" className="mb-4">
            <div style={{ width: "100%", height: 280 }}>
              <ResponsiveContainer>
                <LineChart data={priceData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    interval={14}
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fill: "#64748B", fontSize: 10 }}
                  />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any) => `$${Number(v).toFixed(2)}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="price"
                    stroke="#D4AF37"
                    strokeWidth={2}
                    dot={false}
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
            {METRICS.map((m) => (
              <Card key={m.label}>
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
              </Card>
            ))}
          </div>
        </>
      )}

      {/* ═══ Fundamentals ═══ */}
      {tab === "Fundamentals" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card title="Quarterly Income Statement" subtitle="Last 4 quarters">
            <div style={{ width: "100%", height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={INCOME_Q}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis dataKey="q" tick={{ fill: "#64748B", fontSize: 11 }} />
                  <YAxis
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    tickFormatter={(v: any) => `$${v}B`}
                  />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any) => `$${v}B`}
                  />
                  <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                  <Bar
                    dataKey="revenue"
                    fill="#D4AF37"
                    name="Revenue"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="netIncome"
                    fill="#10B981"
                    name="Net Income"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div style={{ overflowX: "auto", marginTop: 12 }}>
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
                      "Quarter",
                      "Revenue ($B)",
                      "Net Income ($B)",
                      "Gross Margin",
                      "Op Margin",
                    ].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 10px",
                          textAlign: h === "Quarter" ? "left" : "right",
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
                  {INCOME_Q.map((q) => (
                    <tr
                      key={q.q}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td style={{ padding: "6px 10px", color: "#F1F5F9" }}>
                        {q.q}
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#D4AF37",
                        }}
                      >
                        ${q.revenue}B
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#10B981",
                        }}
                      >
                        ${q.netIncome}B
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#94A3B8",
                        }}
                      >
                        {q.grossMargin}%
                      </td>
                      <td
                        style={{
                          padding: "6px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#94A3B8",
                        }}
                      >
                        {q.opMargin}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <Card title="Balance Sheet Summary">
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 8,
              }}
            >
              {BALANCE_ITEMS.map((b) => (
                <div
                  key={b.item}
                  style={{
                    backgroundColor: "rgba(10,14,26,0.5)",
                    borderRadius: 6,
                    padding: "8px 10px",
                  }}
                >
                  <div style={{ fontSize: 11, color: "#64748B" }}>{b.item}</div>
                  <div
                    style={{
                      fontSize: 15,
                      fontWeight: 600,
                      color: "#F1F5F9",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    {b.value}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* ═══ Risk ═══ */}
      {tab === "Risk" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
              gap: 10,
            }}
          >
            {RISK_METRICS.map((m) => (
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
            title="Historical Volatility"
            subtitle="30-day and 60-day rolling volatility (annualized)"
          >
            <div style={{ width: "100%", height: 280 }}>
              <ResponsiveContainer>
                <LineChart data={volHistory}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    interval={14}
                  />
                  <YAxis
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    tickFormatter={(v: any) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any) => `${v}%`}
                  />
                  <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                  <Line
                    type="monotone"
                    dataKey="vol30"
                    stroke="#EF4444"
                    strokeWidth={2}
                    dot={false}
                    name="30-Day Vol"
                  />
                  <Line
                    type="monotone"
                    dataKey="vol60"
                    stroke="#F59E0B"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                    name="60-Day Vol"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
      )}

      {/* ═══ Peers ═══ */}
      {tab === "Peers" && (
        <Card title="Peer Comparison" subtitle="Mega-cap tech peers">
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
                  {["Ticker", "Price", "P/E", "MCap", "YTD"].map((h) => (
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
                {PEERS.map((p) => (
                  <tr
                    key={p.ticker}
                    style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                  >
                    <td
                      style={{
                        padding: "8px 10px",
                        fontFamily: "JetBrains Mono, monospace",
                        fontWeight: 700,
                        color: p.ticker === "AAPL" ? "#D4AF37" : "#F1F5F9",
                      }}
                    >
                      {p.ticker}
                    </td>
                    <td
                      style={{
                        padding: "8px 10px",
                        textAlign: "right",
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#F1F5F9",
                      }}
                    >
                      ${p.price}
                    </td>
                    <td
                      style={{
                        padding: "8px 10px",
                        textAlign: "right",
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#94A3B8",
                      }}
                    >
                      {p.pe}x
                    </td>
                    <td
                      style={{
                        padding: "8px 10px",
                        textAlign: "right",
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#94A3B8",
                      }}
                    >
                      ${p.mcap}
                    </td>
                    <td style={{ padding: "8px 10px", textAlign: "right" }}>
                      <Badge variant={p.ytd >= 0 ? "up" : "down"}>
                        {p.ytd > 0 ? "+" : ""}
                        {p.ytd}%
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ═══ ESG ═══ */}
      {tab === "ESG" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
              gap: 10,
            }}
          >
            {[
              { label: "ESG Overall", value: ESG.overall, color: "#D4AF37" },
              { label: "Environmental", value: ESG.env, color: "#10B981" },
              { label: "Social", value: ESG.social, color: "#00D9FF" },
              { label: "Governance", value: ESG.governance, color: "#A855F7" },
            ].map((m) => (
              <Card key={m.label}>
                <div
                  style={{ fontSize: 11, color: "#64748B", marginBottom: 4 }}
                >
                  {m.label}
                </div>
                <div
                  style={{
                    fontSize: 24,
                    fontWeight: 700,
                    fontFamily: "JetBrains Mono, monospace",
                    color: m.color,
                  }}
                >
                  {m.value}
                </div>
                <div
                  style={{
                    marginTop: 6,
                    height: 6,
                    backgroundColor: "rgba(51,65,85,0.3)",
                    borderRadius: 3,
                  }}
                >
                  <div
                    style={{
                      width: `${m.value}%`,
                      height: 6,
                      backgroundColor: m.color,
                      borderRadius: 3,
                    }}
                  />
                </div>
              </Card>
            ))}
          </div>
          <Card title="ESG Peer Comparison">
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
                    {["Ticker", "ESG Score", "Rating"].map((h) => (
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
                  {ESG.peers.map((p) => (
                    <tr
                      key={p.ticker}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td
                        style={{
                          padding: "8px 10px",
                          fontFamily: "JetBrains Mono, monospace",
                          fontWeight: 700,
                          color: p.ticker === "AAPL" ? "#D4AF37" : "#F1F5F9",
                        }}
                      >
                        {p.ticker}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#F1F5F9",
                        }}
                      >
                        {p.score}/100
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "right" }}>
                        <Badge
                          variant={
                            p.score >= 70
                              ? "up"
                              : p.score >= 50
                                ? "warning"
                                : "down"
                          }
                        >
                          {p.rating}
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

      {/* ═══ News ═══ */}
      {tab === "News" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card
            title="Analyst Consensus"
            subtitle={`${totalAnalysts} analysts covering`}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {analystData.map((a) => (
                <div
                  key={a.label}
                  style={{ display: "flex", alignItems: "center", gap: 12 }}
                >
                  <span
                    style={{
                      fontSize: 12,
                      color: "#94A3B8",
                      width: 80,
                      textAlign: "right",
                    }}
                  >
                    {a.label}
                  </span>
                  <div
                    style={{
                      flex: 1,
                      height: 20,
                      backgroundColor: "rgba(51,65,85,0.2)",
                      borderRadius: 4,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${totalAnalysts > 0 ? (a.count / totalAnalysts) * 100 : 0}%`,
                        height: "100%",
                        backgroundColor: a.color,
                        borderRadius: 4,
                        display: "flex",
                        alignItems: "center",
                        paddingLeft: 6,
                      }}
                    >
                      {a.count > 0 && (
                        <span
                          style={{
                            fontSize: 11,
                            color: "#0A0E1A",
                            fontWeight: 600,
                          }}
                        >
                          {a.count}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
          <Card title="Latest News" subtitle="AAPL-related headlines">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {NEWS.map((n, i) => (
                <div
                  key={i}
                  style={{
                    backgroundColor: "rgba(10,14,26,0.5)",
                    borderRadius: 8,
                    padding: "10px 14px",
                    borderLeft: `3px solid ${n.sentiment === "positive" ? "#10B981" : n.sentiment === "negative" ? "#EF4444" : "#64748B"}`,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 4,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 13,
                        color: "#F1F5F9",
                        fontWeight: 500,
                      }}
                    >
                      {n.title}
                    </span>
                    <Badge
                      variant={
                        n.sentiment === "positive"
                          ? "up"
                          : n.sentiment === "negative"
                            ? "down"
                            : "neutral"
                      }
                    >
                      {n.sentiment}
                    </Badge>
                  </div>
                  <div style={{ fontSize: 11, color: "#64748B" }}>
                    {n.source} • {n.time}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
