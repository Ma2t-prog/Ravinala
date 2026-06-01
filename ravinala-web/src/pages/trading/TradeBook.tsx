import { useMemo, useState } from "react";
import { Badge, Card } from "../../components/ui";
import { useIndices } from "../../hooks/useMarketData";

interface Trade {
  id: string;
  date: string;
  ticker: string;
  side: "Buy" | "Sell";
  qty: number;
  price: number;
  status: "Filled" | "Pending" | "Cancelled";
}

const TRADES: Trade[] = [
  {
    id: "T-001",
    date: "2026-03-22",
    ticker: "AAPL",
    side: "Buy",
    qty: 100,
    price: 198.5,
    status: "Filled",
  },
  {
    id: "T-002",
    date: "2026-03-22",
    ticker: "NVDA",
    side: "Buy",
    qty: 50,
    price: 875.2,
    status: "Filled",
  },
  {
    id: "T-003",
    date: "2026-03-21",
    ticker: "TSLA",
    side: "Sell",
    qty: 30,
    price: 248.0,
    status: "Filled",
  },
  {
    id: "T-004",
    date: "2026-03-21",
    ticker: "MSFT",
    side: "Buy",
    qty: 40,
    price: 425.2,
    status: "Filled",
  },
  {
    id: "T-005",
    date: "2026-03-21",
    ticker: "GOOGL",
    side: "Buy",
    qty: 80,
    price: 178.3,
    status: "Filled",
  },
  {
    id: "T-006",
    date: "2026-03-20",
    ticker: "SPY",
    side: "Buy",
    qty: 200,
    price: 524.8,
    status: "Filled",
  },
  {
    id: "T-007",
    date: "2026-03-20",
    ticker: "XOM",
    side: "Sell",
    qty: 60,
    price: 112.4,
    status: "Filled",
  },
  {
    id: "T-008",
    date: "2026-03-19",
    ticker: "AMD",
    side: "Buy",
    qty: 120,
    price: 178.8,
    status: "Filled",
  },
  {
    id: "T-009",
    date: "2026-03-19",
    ticker: "TLT",
    side: "Buy",
    qty: 150,
    price: 95.2,
    status: "Filled",
  },
  {
    id: "T-010",
    date: "2026-03-18",
    ticker: "META",
    side: "Buy",
    qty: 25,
    price: 520.1,
    status: "Filled",
  },
  {
    id: "T-011",
    date: "2026-03-18",
    ticker: "JPM",
    side: "Sell",
    qty: 45,
    price: 205.4,
    status: "Filled",
  },
  {
    id: "T-012",
    date: "2026-03-17",
    ticker: "GLD",
    side: "Buy",
    qty: 100,
    price: 222.5,
    status: "Filled",
  },
  {
    id: "T-013",
    date: "2026-03-22",
    ticker: "AMZN",
    side: "Buy",
    qty: 35,
    price: 192.8,
    status: "Pending",
  },
  {
    id: "T-014",
    date: "2026-03-22",
    ticker: "COIN",
    side: "Sell",
    qty: 50,
    price: 265.0,
    status: "Pending",
  },
  {
    id: "T-015",
    date: "2026-03-15",
    ticker: "V",
    side: "Buy",
    qty: 40,
    price: 285.6,
    status: "Cancelled",
  },
];

export default function TradeBook() {
  const { data: indicesData } = useIndices();
  const usingFallback = !indicesData;
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [sideFilter, setSideFilter] = useState("All");
  const [showForm, setShowForm] = useState(false);

  const keyIndices = useMemo(() => {
    if (!indicesData) return [];
    const targets = ["^GSPC", "^IXIC", "^DJI"];
    return Object.values(indicesData)
      .flat()
      .filter((idx) => targets.includes(idx.symbol));
  }, [indicesData]);

  const filtered = useMemo(() => {
    return TRADES.filter((t) => {
      const matchSearch =
        t.ticker.toLowerCase().includes(search.toLowerCase()) ||
        t.id.toLowerCase().includes(search.toLowerCase());
      const matchStatus = statusFilter === "All" || t.status === statusFilter;
      const matchSide = sideFilter === "All" || t.side === sideFilter;
      return matchSearch && matchStatus && matchSide;
    });
  }, [search, statusFilter, sideFilter]);

  const totalValue = filtered.reduce((s, t) => s + t.qty * t.price, 0);

  return (
    <div style={{ color: "#F1F5F9" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 4,
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <h1
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 24,
            color: "#F97316",
          }}
        >
          Trade Book
        </h1>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{
            backgroundColor: "#F97316",
            color: "#0A0E1A",
            border: "none",
            borderRadius: 8,
            padding: "8px 16px",
            fontWeight: 600,
            fontSize: 13,
            cursor: "pointer",
          }}
        >
          {showForm ? "Close Form" : "+ Add Trade"}
        </button>
      </div>
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        Order management & trade history
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
                backgroundColor: "rgba(249,115,22,0.06)",
                border: "1px solid rgba(249,115,22,0.15)",
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

      {/* Add Trade Form */}
      {showForm && (
        <Card className="mb-4">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
              gap: 12,
            }}
          >
            {["Ticker", "Side", "Quantity", "Price"].map((field) => (
              <div key={field}>
                <label
                  style={{
                    fontSize: 12,
                    color: "#94A3B8",
                    display: "block",
                    marginBottom: 4,
                  }}
                >
                  {field}
                </label>
                {field === "Side" ? (
                  <select
                    style={{
                      width: "100%",
                      backgroundColor: "#0A0E1A",
                      border: "1px solid rgba(51,65,85,0.5)",
                      borderRadius: 6,
                      color: "#F1F5F9",
                      padding: "8px 10px",
                      fontSize: 13,
                    }}
                  >
                    <option>Buy</option>
                    <option>Sell</option>
                  </select>
                ) : (
                  <input
                    type={field === "Ticker" ? "text" : "number"}
                    placeholder={field}
                    style={{
                      width: "100%",
                      backgroundColor: "#0A0E1A",
                      border: "1px solid rgba(51,65,85,0.5)",
                      borderRadius: 6,
                      color: "#F1F5F9",
                      padding: "8px 10px",
                      fontSize: 13,
                      outline: "none",
                    }}
                  />
                )}
              </div>
            ))}
            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <button
                style={{
                  backgroundColor: "#F97316",
                  color: "#0A0E1A",
                  border: "none",
                  borderRadius: 6,
                  padding: "8px 16px",
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: "pointer",
                  width: "100%",
                }}
              >
                Submit
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Filters */}
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
          placeholder="Search ticker or ID..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            backgroundColor: "#131823",
            border: "1px solid rgba(51,65,85,0.5)",
            borderRadius: 8,
            padding: "8px 14px",
            color: "#F1F5F9",
            fontSize: 13,
            flex: "1 1 180px",
            minWidth: 180,
            outline: "none",
          }}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{
            backgroundColor: "#131823",
            border: "1px solid rgba(51,65,85,0.5)",
            borderRadius: 8,
            padding: "8px 12px",
            color: "#F1F5F9",
            fontSize: 13,
          }}
        >
          {["All", "Filled", "Pending", "Cancelled"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          value={sideFilter}
          onChange={(e) => setSideFilter(e.target.value)}
          style={{
            backgroundColor: "#131823",
            border: "1px solid rgba(51,65,85,0.5)",
            borderRadius: 8,
            padding: "8px 12px",
            color: "#F1F5F9",
            fontSize: 13,
          }}
        >
          {["All", "Buy", "Sell"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <span style={{ fontSize: 12, color: "#64748B" }}>
          {filtered.length} trades | Total: ${totalValue.toLocaleString()}
        </span>
      </div>

      {/* Trades table */}
      <Card>
        <div style={{ overflowX: "auto" }}>
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
          >
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                {[
                  "ID",
                  "Date",
                  "Ticker",
                  "Side",
                  "Qty",
                  "Price",
                  "Value",
                  "Status",
                ].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "8px 10px",
                      textAlign:
                        h === "ID" ||
                        h === "Date" ||
                        h === "Ticker" ||
                        h === "Side" ||
                        h === "Status"
                          ? "left"
                          : "right",
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
              {filtered.map((t) => (
                <tr
                  key={t.id}
                  style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                >
                  <td
                    style={{
                      padding: "8px 10px",
                      fontFamily: "JetBrains Mono, monospace",
                      color: "#64748B",
                      fontSize: 12,
                    }}
                  >
                    {t.id}
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      fontFamily: "JetBrains Mono, monospace",
                      color: "#94A3B8",
                      fontSize: 12,
                    }}
                  >
                    {t.date}
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      fontFamily: "JetBrains Mono, monospace",
                      fontWeight: 700,
                      color: "#F97316",
                    }}
                  >
                    {t.ticker}
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    <Badge variant={t.side === "Buy" ? "up" : "down"}>
                      {t.side}
                    </Badge>
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      textAlign: "right",
                      fontFamily: "JetBrains Mono, monospace",
                      color: "#F1F5F9",
                    }}
                  >
                    {t.qty.toLocaleString()}
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      textAlign: "right",
                      fontFamily: "JetBrains Mono, monospace",
                      color: "#F1F5F9",
                    }}
                  >
                    ${t.price.toFixed(2)}
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      textAlign: "right",
                      fontFamily: "JetBrains Mono, monospace",
                      color: "#F1F5F9",
                    }}
                  >
                    ${(t.qty * t.price).toLocaleString()}
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    <Badge
                      variant={
                        t.status === "Filled"
                          ? "up"
                          : t.status === "Pending"
                            ? "warning"
                            : "neutral"
                      }
                    >
                      {t.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
