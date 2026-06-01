import React, { useMemo, useState } from "react";
import { Card } from "../../components/ui/Card";
import { useIndices } from "../../hooks/useMarketData";

// ── Types ────────────────────────────────────────────────────────────────────

interface Position {
  ticker: string;
  name: string;
  assetClass: string;
  qty: number;
  avgPrice: number;
  currentPrice: number;
}

type SortKey =
  | "ticker"
  | "name"
  | "qty"
  | "avgPrice"
  | "currentPrice"
  | "pnl"
  | "pnlPct"
  | "weight";
type SortDir = "asc" | "desc";
type PnLFilter = "all" | "winners" | "losers";

// ── Initial Demo Data ────────────────────────────────────────────────────────

const INITIAL_POSITIONS: Position[] = [
  {
    ticker: "AAPL",
    name: "Apple Inc.",
    assetClass: "Equity",
    qty: 150,
    avgPrice: 168.42,
    currentPrice: 178.72,
  },
  {
    ticker: "MSFT",
    name: "Microsoft Corp.",
    assetClass: "Equity",
    qty: 100,
    avgPrice: 380.15,
    currentPrice: 415.8,
  },
  {
    ticker: "NVDA",
    name: "NVIDIA Corp.",
    assetClass: "Equity",
    qty: 80,
    avgPrice: 720.3,
    currentPrice: 878.35,
  },
  {
    ticker: "AMZN",
    name: "Amazon.com Inc.",
    assetClass: "Equity",
    qty: 60,
    avgPrice: 175.2,
    currentPrice: 182.45,
  },
  {
    ticker: "GOOGL",
    name: "Alphabet Inc.",
    assetClass: "Equity",
    qty: 90,
    avgPrice: 142.5,
    currentPrice: 155.2,
  },
  {
    ticker: "META",
    name: "Meta Platforms",
    assetClass: "Equity",
    qty: 45,
    avgPrice: 485.6,
    currentPrice: 502.3,
  },
  {
    ticker: "BND",
    name: "Vanguard Total Bond",
    assetClass: "Fixed Income",
    qty: 200,
    avgPrice: 72.8,
    currentPrice: 71.45,
  },
  {
    ticker: "TLT",
    name: "iShares 20+ Yr Treasury",
    assetClass: "Fixed Income",
    qty: 120,
    avgPrice: 98.5,
    currentPrice: 92.18,
  },
  {
    ticker: "GLD",
    name: "SPDR Gold Shares",
    assetClass: "Commodity",
    qty: 50,
    avgPrice: 188.2,
    currentPrice: 202.35,
  },
  {
    ticker: "XLE",
    name: "Energy Select SPDR",
    assetClass: "Equity",
    qty: 100,
    avgPrice: 88.4,
    currentPrice: 85.72,
  },
  {
    ticker: "JPM",
    name: "JPMorgan Chase",
    assetClass: "Equity",
    qty: 70,
    avgPrice: 182.3,
    currentPrice: 198.45,
  },
  {
    ticker: "TSLA",
    name: "Tesla Inc.",
    assetClass: "Equity",
    qty: 40,
    avgPrice: 245.8,
    currentPrice: 172.5,
  },
];

function getPositionData(p: Position) {
  const marketValue = p.qty * p.currentPrice;
  const costBasis = p.qty * p.avgPrice;
  const pnl = marketValue - costBasis;
  const pnlPct = ((p.currentPrice - p.avgPrice) / p.avgPrice) * 100;
  return { marketValue, costBasis, pnl, pnlPct };
}

// ── Component ────────────────────────────────────────────────────────────────

const ASSET_CLASSES = ["Equity", "Fixed Income", "Commodity", "Crypto", "FX"];

export default function PositionBook() {
  // ── Live market data ────────────────────────────────────────────────────────
  const { data: indicesData, isLoading: indicesLoading } = useIndices();
  const usingFallback = !indicesData;

  // ── Mutable positions state ───────────────────────────────────────────────
  const [positions, setPositions] = useState<Position[]>(INITIAL_POSITIONS);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTicker, setNewTicker] = useState("");
  const [newName, setNewName] = useState("");
  const [newClass, setNewClass] = useState("Equity");
  const [newQty, setNewQty] = useState("");
  const [newAvgPrice, setNewAvgPrice] = useState("");
  const [newCurrentPrice, setNewCurrentPrice] = useState("");
  const [addError, setAddError] = useState("");

  const handleAddPosition = () => {
    const ticker = newTicker.trim().toUpperCase();
    const qty = parseFloat(newQty);
    const avgP = parseFloat(newAvgPrice);
    const curP = parseFloat(newCurrentPrice) || avgP;
    if (
      !ticker ||
      !newName.trim() ||
      isNaN(qty) ||
      qty <= 0 ||
      isNaN(avgP) ||
      avgP <= 0
    ) {
      setAddError("Please fill all required fields with valid values.");
      return;
    }
    setPositions((prev) => [
      ...prev,
      {
        ticker,
        name: newName.trim(),
        assetClass: newClass,
        qty,
        avgPrice: avgP,
        currentPrice: curP,
      },
    ]);
    setNewTicker("");
    setNewName("");
    setNewClass("Equity");
    setNewQty("");
    setNewAvgPrice("");
    setNewCurrentPrice("");
    setAddError("");
    setShowAddForm(false);
  };

  const handleRemove = (ticker: string) => {
    setPositions((prev) => prev.filter((p) => p.ticker !== ticker));
  };

  // Merge live prices into positions when available
  const displayPositions = useMemo(() => {
    if (!indicesData) return positions;
    const allItems = Object.values(indicesData).flat();
    return positions.map((p) => {
      const match = allItems.find(
        (idx) => idx.symbol.toUpperCase() === p.ticker.toUpperCase(),
      );
      return match ? { ...p, currentPrice: match.price } : p;
    });
  }, [indicesData]);

  const [sortKey, setSortKey] = useState<SortKey>("weight");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [pnlFilter, setPnlFilter] = useState<PnLFilter>("all");
  const [classFilter, setClassFilter] = useState("All");

  const totalPortfolioValue = useMemo(() => {
    return displayPositions.reduce((sum, p) => sum + p.qty * p.currentPrice, 0);
  }, [displayPositions]);

  const enriched = useMemo(() => {
    return displayPositions.map((p) => {
      const d = getPositionData(p);
      return {
        ...p,
        ...d,
        weight: (d.marketValue / totalPortfolioValue) * 100,
      };
    });
  }, [totalPortfolioValue]);

  const filtered = useMemo(() => {
    return enriched.filter((p) => {
      if (classFilter !== "All" && p.assetClass !== classFilter) return false;
      if (pnlFilter === "winners" && p.pnl <= 0) return false;
      if (pnlFilter === "losers" && p.pnl >= 0) return false;
      return true;
    });
  }, [enriched, classFilter, pnlFilter]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      const aVal = a[sortKey as keyof typeof a] as number;
      const bVal = b[sortKey as keyof typeof b] as number;
      if (typeof aVal === "string") {
        return sortDir === "asc"
          ? (aVal as string).localeCompare(bVal as unknown as string)
          : (bVal as unknown as string).localeCompare(aVal as string);
      }
      return sortDir === "asc"
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    });
  }, [filtered, sortKey, sortDir]);

  const totals = useMemo(() => {
    const totalValue = filtered.reduce((s, p) => s + p.marketValue, 0);
    const totalCost = filtered.reduce((s, p) => s + p.costBasis, 0);
    const totalPnl = totalValue - totalCost;
    const totalPnlPct =
      totalCost > 0 ? ((totalValue - totalCost) / totalCost) * 100 : 0;
    return { totalValue, totalPnl, totalPnlPct };
  }, [filtered]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const fmt = (n: number) =>
    n.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

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

  const headerColumns: { key: SortKey; label: string; align?: "right" }[] = [
    { key: "ticker", label: "Ticker" },
    { key: "name", label: "Name" },
    { key: "qty", label: "Qty", align: "right" },
    { key: "avgPrice", label: "Avg Price", align: "right" },
    { key: "currentPrice", label: "Current", align: "right" },
    { key: "pnl", label: "P&L ($)", align: "right" },
    { key: "pnlPct", label: "P&L %", align: "right" },
    { key: "weight", label: "Weight", align: "right" },
  ];

  const removeBtnStyle: React.CSSProperties = {
    background: "none",
    border: "none",
    cursor: "pointer",
    color: "#EF4444",
    fontSize: 18,
    lineHeight: 1,
    padding: "2px 6px",
    borderRadius: 4,
    opacity: 0.55,
  };

  return (
    <div style={{ color: "#F1F5F9", minHeight: "100vh" }}>
      {/* Fallback Banner */}
      {usingFallback && !indicesLoading && (
        <div
          style={{
            backgroundColor: "rgba(245,158,11,0.1)",
            border: "1px solid rgba(245,158,11,0.3)",
            borderRadius: 6,
            padding: "8px 16px",
            marginBottom: 16,
            color: "#F59E0B",
            fontSize: 13,
            fontFamily: "JetBrains Mono, monospace",
          }}
        >
          Backend unreachable — showing demo data
        </div>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 4,
        }}
      >
        <h1 style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 24 }}>
          Position Book
        </h1>
        <button
          onClick={() => {
            setShowAddForm((v) => !v);
            setAddError("");
          }}
          style={{
            padding: "8px 18px",
            borderRadius: 6,
            cursor: "pointer",
            border: "1px solid rgba(0,217,255,0.4)",
            backgroundColor: showAddForm
              ? "rgba(0,217,255,0.12)"
              : "rgba(0,217,255,0.06)",
            color: "#00D9FF",
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          {showAddForm ? "✕ Cancel" : "+ Add Position"}
        </button>
      </div>
      <p style={{ color: "#94A3B8", fontSize: 14, marginBottom: 16 }}>
        Portfolio positions &amp; P&amp;L tracking
      </p>

      {/* ── Add Position Form ── */}
      {showAddForm && (
        <div
          style={{
            marginBottom: 16,
            padding: "20px 20px 16px",
            borderRadius: 10,
            border: "1px solid rgba(0,217,255,0.2)",
            backgroundColor: "rgba(0,217,255,0.04)",
          }}
        >
          <div
            style={{
              color: "#00D9FF",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13,
              fontWeight: 700,
              marginBottom: 14,
            }}
          >
            New Position
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(6, 1fr)",
              gap: 12,
              marginBottom: 14,
            }}
          >
            {(
              [
                ["Ticker *", newTicker, setNewTicker, "text", "e.g. AAPL"],
                ["Name *", newName, setNewName, "text", "e.g. Apple Inc."],
                ["Qty *", newQty, setNewQty, "number", "0"],
                ["Avg Price *", newAvgPrice, setNewAvgPrice, "number", "0.00"],
                [
                  "Current Price",
                  newCurrentPrice,
                  setNewCurrentPrice,
                  "number",
                  "= Avg",
                ],
              ] as [string, string, (v: string) => void, string, string][]
            ).map(([label, val, setter, type, placeholder]) => (
              <div key={label}>
                <div
                  style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}
                >
                  {label}
                </div>
                <input
                  type={type}
                  value={val}
                  onChange={(e) => setter(e.target.value)}
                  placeholder={placeholder}
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    padding: "8px 10px",
                    borderRadius: 6,
                    border: "1px solid rgba(51,65,85,0.4)",
                    backgroundColor: "#0A0E1A",
                    color: "#F1F5F9",
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 13,
                    outline: "none",
                  }}
                />
              </div>
            ))}
            <div>
              <div style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}>
                Asset Class
              </div>
              <select
                value={newClass}
                onChange={(e) => setNewClass(e.target.value)}
                style={selectStyle}
              >
                {ASSET_CLASSES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {addError && (
            <div style={{ color: "#EF4444", fontSize: 12, marginBottom: 10 }}>
              {addError}
            </div>
          )}
          <button
            onClick={handleAddPosition}
            style={{
              padding: "9px 24px",
              borderRadius: 6,
              cursor: "pointer",
              border: "none",
              backgroundColor: "#10B981",
              color: "#0A0E1A",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13,
              fontWeight: 700,
            }}
          >
            Add to Book
          </button>
        </div>
      )}

      {/* ── Summary Cards ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <Card>
          <div style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}>
            Portfolio Value
          </div>
          <div
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 24,
              fontWeight: 700,
              color: "#8B5CF6",
            }}
          >
            ${fmt(totals.totalValue)}
          </div>
        </Card>
        <Card>
          <div style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}>
            Total P&amp;L
          </div>
          <div
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 24,
              fontWeight: 700,
              color: totals.totalPnl >= 0 ? "#10B981" : "#EF4444",
            }}
          >
            {totals.totalPnl >= 0 ? "+" : ""}${fmt(totals.totalPnl)}
          </div>
        </Card>
        <Card>
          <div style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}>
            Total P&amp;L %
          </div>
          <div
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 24,
              fontWeight: 700,
              color: totals.totalPnlPct >= 0 ? "#10B981" : "#EF4444",
            }}
          >
            {totals.totalPnlPct >= 0 ? "+" : ""}
            {totals.totalPnlPct.toFixed(2)}%
          </div>
        </Card>
      </div>

      {/* ── Filters ── */}
      <Card>
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <div>
            <div style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}>
              Asset Class
            </div>
            <select
              value={classFilter}
              onChange={(e) => setClassFilter(e.target.value)}
              style={selectStyle}
            >
              {["All", "Equity", "Fixed Income", "Commodity"].map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <div style={{ color: "#94A3B8", fontSize: 11, marginBottom: 4 }}>
              P&amp;L Status
            </div>
            <select
              value={pnlFilter}
              onChange={(e) => setPnlFilter(e.target.value as PnLFilter)}
              style={selectStyle}
            >
              <option value="all">All</option>
              <option value="winners">Winners</option>
              <option value="losers">Losers</option>
            </select>
          </div>
          <div style={{ marginLeft: "auto", color: "#94A3B8", fontSize: 12 }}>
            {filtered.length} position{filtered.length !== 1 ? "s" : ""}
          </div>
        </div>
      </Card>

      {/* ── Position Table ── */}
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
                  {headerColumns.map((col) => (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      style={{
                        textAlign: col.align || "left",
                        padding: "10px 12px",
                        color: "#94A3B8",
                        fontSize: 11,
                        fontWeight: 600,
                        cursor: "pointer",
                        userSelect: "none",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {col.label}
                      {sortKey === col.key && (
                        <span style={{ marginLeft: 4, color: "#8B5CF6" }}>
                          {sortDir === "asc" ? "▲" : "▼"}
                        </span>
                      )}
                    </th>
                  ))}
                  <th style={{ padding: "10px 12px", width: 40 }} />
                </tr>
              </thead>
              <tbody>
                {sorted.map((p) => (
                  <tr
                    key={p.ticker}
                    style={{ borderBottom: "1px solid rgba(51,65,85,0.15)" }}
                  >
                    <td
                      style={{
                        padding: "10px 12px",
                        fontFamily: "JetBrains Mono, monospace",
                        fontWeight: 700,
                        color: "#8B5CF6",
                      }}
                    >
                      {p.ticker}
                    </td>
                    <td style={{ padding: "10px 12px" }}>{p.name}</td>
                    <td
                      style={{
                        padding: "10px 12px",
                        textAlign: "right",
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                    >
                      {p.qty.toLocaleString()}
                    </td>
                    <td
                      style={{
                        padding: "10px 12px",
                        textAlign: "right",
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                    >
                      ${fmt(p.avgPrice)}
                    </td>
                    <td
                      style={{
                        padding: "10px 12px",
                        textAlign: "right",
                        fontFamily: "JetBrains Mono, monospace",
                      }}
                    >
                      ${fmt(p.currentPrice)}
                    </td>
                    <td
                      style={{
                        padding: "10px 12px",
                        textAlign: "right",
                        fontFamily: "JetBrains Mono, monospace",
                        color: p.pnl >= 0 ? "#10B981" : "#EF4444",
                      }}
                    >
                      {p.pnl >= 0 ? "+" : ""}
                      {fmt(p.pnl)}
                    </td>
                    <td
                      style={{
                        padding: "10px 12px",
                        textAlign: "right",
                        fontFamily: "JetBrains Mono, monospace",
                        color: p.pnlPct >= 0 ? "#10B981" : "#EF4444",
                      }}
                    >
                      {p.pnlPct >= 0 ? "+" : ""}
                      {p.pnlPct.toFixed(2)}%
                    </td>
                    <td
                      style={{
                        padding: "10px 12px",
                        textAlign: "right",
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#94A3B8",
                      }}
                    >
                      {p.weight.toFixed(1)}%
                    </td>
                    <td style={{ padding: "4px 8px", textAlign: "center" }}>
                      <button
                        onClick={() => handleRemove(p.ticker)}
                        style={removeBtnStyle}
                        title={`Remove ${p.ticker}`}
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
              {/* Summary row */}
              <tfoot>
                <tr style={{ borderTop: "2px solid rgba(51,65,85,0.3)" }}>
                  <td style={{ padding: "10px 12px", fontWeight: 700 }}>
                    TOTAL
                  </td>
                  <td />
                  <td />
                  <td />
                  <td
                    style={{
                      padding: "10px 12px",
                      textAlign: "right",
                      fontFamily: "JetBrains Mono, monospace",
                      fontWeight: 700,
                    }}
                  >
                    ${fmt(totals.totalValue)}
                  </td>
                  <td
                    style={{
                      padding: "10px 12px",
                      textAlign: "right",
                      fontFamily: "JetBrains Mono, monospace",
                      fontWeight: 700,
                      color: totals.totalPnl >= 0 ? "#10B981" : "#EF4444",
                    }}
                  >
                    {totals.totalPnl >= 0 ? "+" : ""}
                    {fmt(totals.totalPnl)}
                  </td>
                  <td
                    style={{
                      padding: "10px 12px",
                      textAlign: "right",
                      fontFamily: "JetBrains Mono, monospace",
                      fontWeight: 700,
                      color: totals.totalPnlPct >= 0 ? "#10B981" : "#EF4444",
                    }}
                  >
                    {totals.totalPnlPct >= 0 ? "+" : ""}
                    {totals.totalPnlPct.toFixed(2)}%
                  </td>
                  <td
                    style={{
                      padding: "10px 12px",
                      textAlign: "right",
                      fontFamily: "JetBrains Mono, monospace",
                      fontWeight: 700,
                    }}
                  >
                    100.0%
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
