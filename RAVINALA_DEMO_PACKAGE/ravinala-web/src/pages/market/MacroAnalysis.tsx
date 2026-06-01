import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { refreshCache } from "../../api/market";
import type {
  BondItem,
  Commodity,
  FXPair,
  IndexItem,
  MacroIndicator,
} from "../../api/types";
import { Badge, Card, Spinner } from "../../components/ui";
import {
  marketKeys,
  useBonds,
  useCommodities,
  useFX,
  useIndices,
  useMacro,
} from "../../hooks/useMarketData";

// ─── Constants ────────────────────────────────────────────────────────────────

const TABS = [
  "Indices",
  "Bonds",
  "FX",
  "Commodities",
  "Macro Indicators",
] as const;
type Tab = (typeof TABS)[number];

const REGION_ORDER = [
  "Americas",
  "Europe",
  "Asia Pacific",
  "Middle East/Other",
];

const COMMODITY_SECTION_ORDER = ["metals", "energy", "agriculture", "crypto"];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(n: number | undefined, decimals = 2): string {
  if (n === undefined || n === null || isNaN(n)) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtYield(n: number | undefined): string {
  if (n === undefined || n === null || isNaN(n)) return "—";
  return `${n.toFixed(2)}%`;
}

function changeVariant(pct: number): "up" | "down" | "neutral" {
  if (pct > 0) return "up";
  if (pct < 0) return "down";
  return "neutral";
}

function ChangeCell({ pct }: { pct: number }) {
  const color = pct > 0 ? "#10B981" : pct < 0 ? "#EF4444" : "#94A3B8";
  const arrow = pct > 0 ? "▲" : pct < 0 ? "▼" : "●";
  return (
    <span
      style={{ color, fontFamily: "JetBrains Mono, monospace", fontSize: 13 }}
    >
      {arrow} {pct > 0 ? "+" : ""}
      {pct.toFixed(2)}%
    </span>
  );
}

function formatTimestamp(ts: string | undefined): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return ts;
  }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function LiveBadge() {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        backgroundColor: "rgba(16,185,129,0.15)",
        border: "1px solid rgba(16,185,129,0.3)",
        color: "#10B981",
        borderRadius: 9999,
        padding: "2px 10px",
        fontSize: 11,
        fontWeight: 700,
        fontFamily: "JetBrains Mono, monospace",
        letterSpacing: "0.08em",
      }}
    >
      <span
        style={{
          width: 7,
          height: 7,
          borderRadius: "50%",
          backgroundColor: "#10B981",
          display: "inline-block",
          animation: "pulse-green 1.5s ease-in-out infinite",
        }}
      />
      LIVE
    </span>
  );
}

function TabBar({
  active,
  onChange,
}: {
  active: Tab;
  onChange: (t: Tab) => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        borderBottom: "1px solid rgba(51,65,85,0.4)",
        marginBottom: 20,
        gap: 0,
      }}
    >
      {TABS.map((tab) => {
        const isActive = tab === active;
        return (
          <button
            key={tab}
            onClick={() => onChange(tab)}
            style={{
              background: "none",
              border: "none",
              borderBottom: isActive
                ? "2px solid #00D9FF"
                : "2px solid transparent",
              color: isActive ? "#00D9FF" : "#94A3B8",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13,
              fontWeight: isActive ? 600 : 400,
              padding: "10px 18px",
              cursor: "pointer",
              transition: "color 0.15s, border-color 0.15s",
              marginBottom: -1,
              whiteSpace: "nowrap",
            }}
            onMouseEnter={(e) => {
              if (!isActive)
                (e.currentTarget as HTMLButtonElement).style.color = "#CBD5E1";
            }}
            onMouseLeave={(e) => {
              if (!isActive)
                (e.currentTarget as HTMLButtonElement).style.color = "#94A3B8";
            }}
          >
            {tab}
          </button>
        );
      })}
    </div>
  );
}

function SectionHeader({
  title,
  count,
  collapsed,
  onToggle,
}: {
  title: string;
  count: number;
  collapsed: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        background: "none",
        border: "none",
        cursor: "pointer",
        padding: "8px 0",
        width: "100%",
        textAlign: "left",
      }}
    >
      <span
        style={{
          color: "#00D9FF",
          fontSize: 12,
          fontFamily: "JetBrains Mono, monospace",
          width: 14,
        }}
      >
        {collapsed ? "▶" : "▼"}
      </span>
      <span
        style={{
          color: "#F1F5F9",
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 13,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {title}
      </span>
      <span
        style={{
          color: "#64748B",
          fontSize: 11,
          fontFamily: "JetBrains Mono, monospace",
        }}
      >
        ({count})
      </span>
    </button>
  );
}

function LoadingPane() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: 200,
        gap: 12,
        color: "#94A3B8",
        fontSize: 13,
        fontFamily: "JetBrains Mono, monospace",
      }}
    >
      <Spinner size="md" />
      <span>Loading market data…</span>
    </div>
  );
}

function _ErrorPane({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: 200,
        gap: 14,
      }}
    >
      <span
        style={{
          color: "#EF4444",
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 13,
        }}
      >
        {message}
      </span>
      <button
        onClick={onRetry}
        style={{
          backgroundColor: "rgba(0,217,255,0.1)",
          border: "1px solid rgba(0,217,255,0.3)",
          color: "#00D9FF",
          borderRadius: 6,
          padding: "6px 16px",
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 12,
          cursor: "pointer",
        }}
      >
        Retry
      </button>
    </div>
  );
}

// ─── Table shared styles ──────────────────────────────────────────────────────

const TH_STYLE: React.CSSProperties = {
  color: "#64748B",
  fontSize: 11,
  fontFamily: "JetBrains Mono, monospace",
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.07em",
  padding: "8px 12px",
  textAlign: "left",
  borderBottom: "1px solid rgba(51,65,85,0.4)",
  whiteSpace: "nowrap",
};

const TD_STYLE: React.CSSProperties = {
  padding: "9px 12px",
  fontSize: 13,
  fontFamily: "JetBrains Mono, monospace",
  color: "#CBD5E1",
  borderBottom: "1px solid rgba(51,65,85,0.15)",
  whiteSpace: "nowrap",
};

// ─── Indices Tab ──────────────────────────────────────────────────────────────

const INDICES_FALLBACK: Record<string, IndexItem[]> = {
  Americas: [
    {
      symbol: "^GSPC",
      name: "S&P 500",
      region: "Americas",
      price: 5234.18,
      change: { percent: 0.47, absolute: 24.52 },
      timestamp: "",
    },
    {
      symbol: "^NDX",
      name: "NASDAQ-100",
      region: "Americas",
      price: 18312.75,
      change: { percent: 0.63, absolute: 114.88 },
      timestamp: "",
    },
    {
      symbol: "^DJI",
      name: "Dow Jones",
      region: "Americas",
      price: 39150.33,
      change: { percent: 0.21, absolute: 81.23 },
      timestamp: "",
    },
  ],
  Europe: [
    {
      symbol: "^STOXX50E",
      name: "Euro Stoxx 50",
      region: "Europe",
      price: 5005.4,
      change: { percent: -0.15, absolute: -7.5 },
      timestamp: "",
    },
    {
      symbol: "^FTSE",
      name: "FTSE 100",
      region: "Europe",
      price: 8160.22,
      change: { percent: 0.08, absolute: 6.53 },
      timestamp: "",
    },
    {
      symbol: "^GDAXI",
      name: "DAX 40",
      region: "Europe",
      price: 18450.88,
      change: { percent: -0.32, absolute: -59.04 },
      timestamp: "",
    },
  ],
  "Asia Pacific": [
    {
      symbol: "^N225",
      name: "Nikkei 225",
      region: "Asia Pacific",
      price: 39740.5,
      change: { percent: 1.02, absolute: 401.2 },
      timestamp: "",
    },
    {
      symbol: "^HSI",
      name: "Hang Seng",
      region: "Asia Pacific",
      price: 16520.88,
      change: { percent: -0.44, absolute: -73.1 },
      timestamp: "",
    },
  ],
};

const BONDS_FALLBACK: BondItem[] = [
  {
    country: "USA",
    country_code: "US",
    yield_2y: 4.72,
    yield_5y: 4.35,
    yield_10y: 4.28,
  },
  {
    country: "Germany",
    country_code: "DE",
    yield_2y: 2.92,
    yield_5y: 2.48,
    yield_10y: 2.35,
    spread_vs_bund_bp: 0,
  },
  {
    country: "United Kingdom",
    country_code: "GB",
    yield_2y: 4.38,
    yield_5y: 4.05,
    yield_10y: 4.12,
  },
  {
    country: "Japan",
    country_code: "JP",
    yield_2y: 0.18,
    yield_5y: 0.52,
    yield_10y: 0.88,
  },
  {
    country: "France",
    country_code: "FR",
    yield_2y: 3.08,
    yield_5y: 2.72,
    yield_10y: 2.92,
  },
];

const FX_FALLBACK: FXPair[] = [
  {
    symbol: "EURUSD",
    base: "EUR",
    quote: "USD",
    rate: 1.0845,
    change: { percent: -0.12, absolute: -0.0013 },
  },
  {
    symbol: "GBPUSD",
    base: "GBP",
    quote: "USD",
    rate: 1.2652,
    change: { percent: 0.08, absolute: 0.001 },
  },
  {
    symbol: "USDJPY",
    base: "USD",
    quote: "JPY",
    rate: 151.42,
    change: { percent: 0.22, absolute: 0.33 },
  },
  {
    symbol: "USDCHF",
    base: "USD",
    quote: "CHF",
    rate: 0.8815,
    change: { percent: -0.05, absolute: -0.0004 },
  },
  {
    symbol: "AUDUSD",
    base: "AUD",
    quote: "USD",
    rate: 0.6538,
    change: { percent: 0.15, absolute: 0.001 },
  },
];

const COMMODITIES_FALLBACK: Record<string, Commodity[]> = {
  metals: [
    {
      symbol: "GC=F",
      name: "Gold",
      category: "metals",
      price: 2345.6,
      unit: "USD/oz",
      change: { percent: 0.55, absolute: 12.8 },
    },
    {
      symbol: "SI=F",
      name: "Silver",
      category: "metals",
      price: 27.92,
      unit: "USD/oz",
      change: { percent: 0.78, absolute: 0.22 },
    },
  ],
  energy: [
    {
      symbol: "CL=F",
      name: "Crude Oil",
      category: "energy",
      price: 78.44,
      unit: "USD/bbl",
      change: { percent: -0.62, absolute: -0.49 },
    },
    {
      symbol: "NG=F",
      name: "Natural Gas",
      category: "energy",
      price: 1.78,
      unit: "USD/MMBtu",
      change: { percent: 1.14, absolute: 0.02 },
    },
  ],
};

function FallbackBanner() {
  return (
    <div
      style={{
        background: "rgba(245,158,11,0.08)",
        border: "1px solid rgba(245,158,11,0.2)",
        borderRadius: 8,
        padding: "8px 14px",
        marginBottom: 12,
        fontSize: 12,
        color: "#F59E0B",
      }}
    >
      ⚠ Backend unreachable — displaying demo data
    </div>
  );
}

function IndicesTab() {
  const { data, isLoading } = useIndices();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  if (isLoading) return <LoadingPane />;

  const displayData =
    data && Object.keys(data).length > 0 ? data : INDICES_FALLBACK;
  const usingFallback = !data || Object.keys(data).length === 0;

  // Build ordered region list: known regions first, then anything else
  const allRegions = Object.keys(displayData);
  const ordered = [
    ...REGION_ORDER.filter((r) => allRegions.includes(r)),
    ...allRegions.filter((r) => !REGION_ORDER.includes(r)),
  ];

  function toggleRegion(region: string) {
    setCollapsed((prev) => ({ ...prev, [region]: !prev[region] }));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {usingFallback && <FallbackBanner />}
      {ordered.map((region) => {
        const items: IndexItem[] = displayData[region] ?? [];
        const isCollapsed = collapsed[region] ?? false;
        return (
          <div
            key={region}
            style={{
              backgroundColor: "#131823",
              border: "1px solid rgba(51,65,85,0.3)",
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            <div style={{ padding: "4px 12px" }}>
              <SectionHeader
                title={region}
                count={items.length}
                collapsed={isCollapsed}
                onToggle={() => toggleRegion(region)}
              />
            </div>
            {!isCollapsed && (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ backgroundColor: "rgba(10,14,26,0.6)" }}>
                      <th style={TH_STYLE}>Name</th>
                      <th style={TH_STYLE}>Symbol</th>
                      <th style={{ ...TH_STYLE, textAlign: "right" }}>Price</th>
                      <th style={{ ...TH_STYLE, textAlign: "right" }}>
                        Change %
                      </th>
                      <th style={{ ...TH_STYLE, textAlign: "center" }}>
                        Status
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item, i) => {
                      const pct = item.change.percent;
                      const variant = changeVariant(pct);
                      return (
                        <tr
                          key={item.symbol}
                          style={{
                            backgroundColor:
                              i % 2 === 1
                                ? "rgba(255,255,255,0.015)"
                                : "transparent",
                            transition: "background-color 0.1s",
                          }}
                          onMouseEnter={(e) => {
                            (
                              e.currentTarget as HTMLTableRowElement
                            ).style.backgroundColor = "#1A2332";
                          }}
                          onMouseLeave={(e) => {
                            (
                              e.currentTarget as HTMLTableRowElement
                            ).style.backgroundColor =
                              i % 2 === 1
                                ? "rgba(255,255,255,0.015)"
                                : "transparent";
                          }}
                        >
                          <td
                            style={{
                              ...TD_STYLE,
                              color: "#F1F5F9",
                              fontWeight: 500,
                            }}
                          >
                            {item.name}
                          </td>
                          <td style={{ ...TD_STYLE, color: "#64748B" }}>
                            {item.symbol}
                          </td>
                          <td
                            style={{
                              ...TD_STYLE,
                              textAlign: "right",
                              color: "#F1F5F9",
                            }}
                          >
                            {fmt(item.price, item.price >= 1000 ? 0 : 2)}
                          </td>
                          <td style={{ ...TD_STYLE, textAlign: "right" }}>
                            <ChangeCell pct={pct} />
                          </td>
                          <td style={{ ...TD_STYLE, textAlign: "center" }}>
                            <Badge variant={variant}>
                              {variant === "up"
                                ? "UP"
                                : variant === "down"
                                  ? "DOWN"
                                  : "FLAT"}
                            </Badge>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Bonds Tab ────────────────────────────────────────────────────────────────

function BondsTab() {
  const { data, isLoading } = useBonds();

  if (isLoading) return <LoadingPane />;

  const bonds: BondItem[] = data?.bonds?.length ? data.bonds : BONDS_FALLBACK;
  const usingFallback = !data?.bonds?.length;

  function yieldColor(y: number | undefined): string {
    if (y === undefined) return "#94A3B8";
    if (y < 0) return "#A855F7"; // purple for negative
    if (y > 4) return "#F59E0B"; // amber for high yield
    return "#CBD5E1";
  }

  function spreadColor(bp: number | undefined): string {
    if (bp === undefined) return "#94A3B8";
    if (bp < 0) return "#A855F7";
    if (bp > 200) return "#EF4444";
    if (bp > 100) return "#F59E0B";
    return "#CBD5E1";
  }

  return (
    <Card>
      {usingFallback && <FallbackBanner />}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ backgroundColor: "rgba(10,14,26,0.6)" }}>
              <th style={TH_STYLE}>Country</th>
              <th style={{ ...TH_STYLE, textAlign: "right" }}>2Y Yield</th>
              <th style={{ ...TH_STYLE, textAlign: "right" }}>5Y Yield</th>
              <th style={{ ...TH_STYLE, textAlign: "right" }}>10Y Yield</th>
              <th style={{ ...TH_STYLE, textAlign: "right" }}>
                Spread vs Bund
              </th>
            </tr>
          </thead>
          <tbody>
            {bonds.map((bond, i) => (
              <tr
                key={bond.country_code}
                style={{
                  backgroundColor:
                    i % 2 === 1 ? "rgba(255,255,255,0.015)" : "transparent",
                  transition: "background-color 0.1s",
                }}
                onMouseEnter={(e) => {
                  (
                    e.currentTarget as HTMLTableRowElement
                  ).style.backgroundColor = "#1A2332";
                }}
                onMouseLeave={(e) => {
                  (
                    e.currentTarget as HTMLTableRowElement
                  ).style.backgroundColor =
                    i % 2 === 1 ? "rgba(255,255,255,0.015)" : "transparent";
                }}
              >
                <td style={{ ...TD_STYLE, color: "#F1F5F9", fontWeight: 500 }}>
                  <span
                    style={{ marginRight: 6, color: "#64748B", fontSize: 11 }}
                  >
                    {bond.country_code}
                  </span>
                  {bond.country}
                </td>
                <td
                  style={{
                    ...TD_STYLE,
                    textAlign: "right",
                    color: yieldColor(bond.yield_2y),
                  }}
                >
                  {fmtYield(bond.yield_2y)}
                </td>
                <td
                  style={{
                    ...TD_STYLE,
                    textAlign: "right",
                    color: yieldColor(bond.yield_5y),
                  }}
                >
                  {fmtYield(bond.yield_5y)}
                </td>
                <td
                  style={{
                    ...TD_STYLE,
                    textAlign: "right",
                    color: yieldColor(bond.yield_10y),
                  }}
                >
                  {fmtYield(bond.yield_10y)}
                </td>
                <td
                  style={{
                    ...TD_STYLE,
                    textAlign: "right",
                    color: spreadColor(bond.spread_vs_bund_bp),
                  }}
                >
                  {bond.spread_vs_bund_bp !== undefined
                    ? `${bond.spread_vs_bund_bp > 0 ? "+" : ""}${bond.spread_vs_bund_bp} bp`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── FX Tab ───────────────────────────────────────────────────────────────────

function FXCard({ pair }: { pair: FXPair }) {
  const pct = pair.change.percent;
  const variant = changeVariant(pct);

  return (
    <div
      style={{
        backgroundColor: "#131823",
        border: "1px solid rgba(51,65,85,0.3)",
        borderRadius: 8,
        padding: "16px 18px",
        transition: "border-color 0.15s",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor =
          "rgba(0,217,255,0.25)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor =
          "rgba(51,65,85,0.3)";
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 13,
            fontWeight: 700,
            color: "#F1F5F9",
            letterSpacing: "0.04em",
          }}
        >
          {pair.base}/{pair.quote}
        </span>
        <Badge variant={variant}>
          {pct > 0 ? "+" : ""}
          {pct.toFixed(2)}%
        </Badge>
      </div>

      {/* Rate */}
      <span
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 22,
          fontWeight: 600,
          color: "#00D9FF",
          lineHeight: 1,
        }}
      >
        {pair.rate.toFixed(4)}
      </span>

      {/* Absolute change */}
      <span
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 11,
          color: pct > 0 ? "#10B981" : pct < 0 ? "#EF4444" : "#64748B",
        }}
      >
        {pair.change.absolute > 0 ? "+" : ""}
        {pair.change.absolute.toFixed(4)}
      </span>
    </div>
  );
}

function FXTab() {
  const { data, isLoading } = useFX();

  if (isLoading) return <LoadingPane />;

  const pairs: FXPair[] = data?.pairs?.length ? data.pairs : FX_FALLBACK;
  const usingFallback = !data?.pairs?.length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {usingFallback && <FallbackBanner />}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 12,
        }}
      >
        {pairs.map((pair) => (
          <FXCard key={pair.symbol} pair={pair} />
        ))}
      </div>
    </div>
  );
}

// ─── Commodities Tab ──────────────────────────────────────────────────────────

function CommodityCard({ commodity }: { commodity: Commodity }) {
  const pct = commodity.change.percent;
  const variant = changeVariant(pct);

  return (
    <div
      style={{
        backgroundColor: "#131823",
        border: "1px solid rgba(51,65,85,0.3)",
        borderRadius: 8,
        padding: "14px 16px",
        transition: "border-color 0.15s",
        display: "flex",
        flexDirection: "column",
        gap: 6,
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor =
          "rgba(0,217,255,0.25)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor =
          "rgba(51,65,85,0.3)";
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div>
          <div
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 12,
              fontWeight: 600,
              color: "#F1F5F9",
              marginBottom: 2,
            }}
          >
            {commodity.name}
          </div>
          <div
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 10,
              color: "#64748B",
            }}
          >
            {commodity.symbol} · {commodity.unit}
          </div>
        </div>
        <Badge variant={variant}>
          {pct > 0 ? "+" : ""}
          {pct.toFixed(2)}%
        </Badge>
      </div>
      <div
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 18,
          fontWeight: 600,
          color: "#F1F5F9",
        }}
      >
        {fmt(
          commodity.price,
          commodity.price < 10 ? 4 : commodity.price < 100 ? 2 : 0,
        )}
      </div>
    </div>
  );
}

function CommoditiesTab() {
  const { data, isLoading } = useCommodities();

  if (isLoading) return <LoadingPane />;

  const displayData =
    data && Object.keys(data).length > 0 ? data : COMMODITIES_FALLBACK;
  const usingFallback = !data || Object.keys(data).length === 0;

  const allCategories = Object.keys(displayData);
  const ordered = [
    ...COMMODITY_SECTION_ORDER.filter((c) => allCategories.includes(c)),
    ...allCategories.filter((c) => !COMMODITY_SECTION_ORDER.includes(c)),
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {usingFallback && <FallbackBanner />}
      {ordered.map((category) => {
        const items: Commodity[] = displayData[category] ?? [];
        return (
          <div key={category}>
            <div
              style={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 11,
                fontWeight: 700,
                color: "#64748B",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                marginBottom: 10,
                paddingBottom: 6,
                borderBottom: "1px solid rgba(51,65,85,0.3)",
              }}
            >
              {category}
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                gap: 10,
              }}
            >
              {items.map((c) => (
                <CommodityCard key={c.symbol} commodity={c} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Macro Indicators Tab ─────────────────────────────────────────────────────

const MACRO_FALLBACK: MacroIndicator[] = [
  {
    country: "United States",
    indicator: "GDP Growth (QoQ)",
    value: 2.1,
    previous: 1.6,
    unit: "%",
    period: "Q4 2025",
  },
  {
    country: "United States",
    indicator: "CPI (YoY)",
    value: 3.0,
    previous: 2.9,
    unit: "%",
    period: "Feb 2026",
  },
  {
    country: "United States",
    indicator: "Unemployment Rate",
    value: 4.1,
    previous: 4.0,
    unit: "%",
    period: "Feb 2026",
  },
  {
    country: "United States",
    indicator: "Manufacturing PMI",
    value: 52.7,
    previous: 51.2,
    unit: "Index",
    period: "Mar 2026",
  },
  {
    country: "Eurozone",
    indicator: "GDP Growth (QoQ)",
    value: 0.3,
    previous: 0.2,
    unit: "%",
    period: "Q4 2025",
  },
  {
    country: "Eurozone",
    indicator: "CPI (YoY)",
    value: 2.4,
    previous: 2.6,
    unit: "%",
    period: "Feb 2026",
  },
  {
    country: "Eurozone",
    indicator: "Unemployment Rate",
    value: 6.4,
    previous: 6.5,
    unit: "%",
    period: "Jan 2026",
  },
  {
    country: "China",
    indicator: "GDP Growth (YoY)",
    value: 5.4,
    previous: 4.9,
    unit: "%",
    period: "Q4 2025",
  },
  {
    country: "China",
    indicator: "CPI (YoY)",
    value: 0.7,
    previous: 0.5,
    unit: "%",
    period: "Feb 2026",
  },
  {
    country: "China",
    indicator: "Manufacturing PMI",
    value: 50.2,
    previous: 49.8,
    unit: "Index",
    period: "Mar 2026",
  },
  {
    country: "Japan",
    indicator: "GDP Growth (QoQ)",
    value: 0.7,
    previous: 0.3,
    unit: "%",
    period: "Q4 2025",
  },
  {
    country: "Japan",
    indicator: "CPI (YoY)",
    value: 3.7,
    previous: 3.6,
    unit: "%",
    period: "Feb 2026",
  },
  {
    country: "United Kingdom",
    indicator: "GDP Growth (QoQ)",
    value: 0.1,
    previous: 0.0,
    unit: "%",
    period: "Q4 2025",
  },
  {
    country: "United Kingdom",
    indicator: "CPI (YoY)",
    value: 3.0,
    previous: 3.0,
    unit: "%",
    period: "Feb 2026",
  },
];

function indicatorColor(indicator: string): string {
  const lc = indicator.toLowerCase();
  if (lc.includes("cpi") || lc.includes("inflation")) return "#F59E0B";
  if (lc.includes("gdp") || lc.includes("growth")) return "#10B981";
  if (
    lc.includes("pmi") ||
    lc.includes("manufacturing") ||
    lc.includes("services")
  )
    return "#00D9FF";
  if (lc.includes("unemployment") || lc.includes("employment"))
    return "#A855F7";
  return "#94A3B8";
}

function MacroTab() {
  const { data: macroData, isLoading } = useMacro();

  if (isLoading) return <LoadingPane />;

  const indicators: MacroIndicator[] = macroData?.indicators ?? MACRO_FALLBACK;
  const usingFallback = !macroData?.indicators;

  return (
    <Card>
      {usingFallback && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 14px",
            backgroundColor: "rgba(245,158,11,0.08)",
            borderBottom: "1px solid rgba(245,158,11,0.2)",
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 11,
            color: "#F59E0B",
          }}
        >
          <span>Backend unreachable — showing demo data</span>
        </div>
      )}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ backgroundColor: "rgba(10,14,26,0.6)" }}>
              <th style={TH_STYLE}>Country</th>
              <th style={TH_STYLE}>Indicator</th>
              <th style={{ ...TH_STYLE, textAlign: "right" }}>Value</th>
              <th style={{ ...TH_STYLE, textAlign: "right" }}>Previous</th>
              <th style={TH_STYLE}>Unit</th>
              <th style={TH_STYLE}>Period</th>
            </tr>
          </thead>
          <tbody>
            {indicators.map((ind: MacroIndicator, i: number) => {
              const color = indicatorColor(ind.indicator);
              const hasPrev = ind.previous !== undefined;
              const diff = hasPrev ? ind.value - (ind.previous ?? 0) : 0;
              return (
                <tr
                  key={`${ind.country}-${ind.indicator}-${i}`}
                  style={{
                    backgroundColor:
                      i % 2 === 1 ? "rgba(255,255,255,0.015)" : "transparent",
                    transition: "background-color 0.1s",
                  }}
                  onMouseEnter={(e) => {
                    (
                      e.currentTarget as HTMLTableRowElement
                    ).style.backgroundColor = "#1A2332";
                  }}
                  onMouseLeave={(e) => {
                    (
                      e.currentTarget as HTMLTableRowElement
                    ).style.backgroundColor =
                      i % 2 === 1 ? "rgba(255,255,255,0.015)" : "transparent";
                  }}
                >
                  <td
                    style={{ ...TD_STYLE, color: "#F1F5F9", fontWeight: 500 }}
                  >
                    {ind.country}
                  </td>
                  <td style={{ ...TD_STYLE }}>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      <span
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          backgroundColor: color,
                          display: "inline-block",
                          flexShrink: 0,
                        }}
                      />
                      <span style={{ color: color, fontWeight: 500 }}>
                        {ind.indicator}
                      </span>
                    </span>
                  </td>
                  <td
                    style={{
                      ...TD_STYLE,
                      textAlign: "right",
                      color: "#F1F5F9",
                      fontWeight: 600,
                    }}
                  >
                    {fmt(ind.value)}
                  </td>
                  <td style={{ ...TD_STYLE, textAlign: "right" }}>
                    {hasPrev ? (
                      <span>
                        <span style={{ color: "#94A3B8" }}>
                          {fmt(ind.previous)}
                        </span>
                        {diff !== 0 && (
                          <span
                            style={{
                              marginLeft: 6,
                              fontSize: 11,
                              color: diff > 0 ? "#10B981" : "#EF4444",
                            }}
                          >
                            {diff > 0 ? "▲" : "▼"}
                          </span>
                        )}
                      </span>
                    ) : (
                      <span style={{ color: "#64748B" }}>—</span>
                    )}
                  </td>
                  <td style={{ ...TD_STYLE, color: "#64748B" }}>{ind.unit}</td>
                  <td style={{ ...TD_STYLE, color: "#64748B" }}>
                    {ind.period}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function MacroAnalysis() {
  const [activeTab, setActiveTab] = useState<Tab>("Indices");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const queryClient = useQueryClient();

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await refreshCache();
      await queryClient.invalidateQueries({ queryKey: marketKeys.all });
      setLastRefreshed(new Date());
    } catch {
      // silent — individual tabs surface their own errors
    } finally {
      setIsRefreshing(false);
    }
  }, [queryClient]);

  return (
    <>
      {/* Keyframe for live badge pulse */}
      <style>{`
        @keyframes pulse-green {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>

      <div style={{ color: "#F1F5F9", minHeight: "100vh" }}>
        {/* ── Page header ─────────────────────────────────────────── */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: 24,
            flexWrap: "wrap",
            gap: 12,
          }}
        >
          {/* Title block */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <h1
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 24,
                  fontWeight: 700,
                  color: "#F1F5F9",
                  margin: 0,
                  letterSpacing: "-0.01em",
                }}
              >
                Macro Analysis
              </h1>
              <LiveBadge />
            </div>
            <p
              style={{
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 12,
                color: "#64748B",
                margin: 0,
              }}
            >
              Global Cross-Asset Dashboard
            </p>
          </div>

          {/* Controls */}
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            {lastRefreshed && (
              <span
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 11,
                  color: "#64748B",
                }}
              >
                Updated {formatTimestamp(lastRefreshed.toISOString())}
              </span>
            )}
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 7,
                backgroundColor: "rgba(0,217,255,0.08)",
                border: "1px solid rgba(0,217,255,0.25)",
                color: isRefreshing ? "#64748B" : "#00D9FF",
                borderRadius: 6,
                padding: "7px 16px",
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 12,
                fontWeight: 500,
                cursor: isRefreshing ? "not-allowed" : "pointer",
                transition: "background-color 0.15s, border-color 0.15s",
              }}
              onMouseEnter={(e) => {
                if (!isRefreshing)
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                    "rgba(0,217,255,0.14)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                  "rgba(0,217,255,0.08)";
              }}
            >
              {isRefreshing ? (
                <Spinner size="sm" />
              ) : (
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 13 13"
                  fill="none"
                  aria-hidden="true"
                >
                  <path
                    d="M11.5 2A6 6 0 1 0 12 6.5"
                    stroke="#00D9FF"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                  />
                  <path
                    d="M12 2V5.5H8.5"
                    stroke="#00D9FF"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
              {isRefreshing ? "Refreshing…" : "Refresh"}
            </button>
          </div>
        </div>

        {/* ── Tabs ────────────────────────────────────────────────── */}
        <TabBar active={activeTab} onChange={setActiveTab} />

        {/* ── Tab content ─────────────────────────────────────────── */}
        {activeTab === "Indices" && <IndicesTab />}
        {activeTab === "Bonds" && <BondsTab />}
        {activeTab === "FX" && <FXTab />}
        {activeTab === "Commodities" && <CommoditiesTab />}
        {activeTab === "Macro Indicators" && <MacroTab />}
      </div>
    </>
  );
}
