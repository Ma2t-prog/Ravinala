import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { refreshCache } from "../../api/market";
import type {
  BondItem,
  Commodity,
  DataQuality,
  FullSnapshot,
  FXPair,
  IndexItem,
} from "../../api/types";
import { Badge, Card, DataQualityBadge, Spinner } from "../../components/ui";
import {
  marketKeys,
  useBonds,
  useCommodities,
  useFX,
  useIndices,
  useSnapshot,
} from "../../hooks/useMarketData";

// ─── Constants ────────────────────────────────────────────────────────────────

const MONO = "JetBrains Mono, monospace";

const REGION_ORDER = [
  "Americas",
  "Europe",
  "Asia Pacific",
  "Middle East/Other",
];

const COUNTRY_FLAGS: Record<string, string> = {
  US: "🇺🇸",
  DE: "🇩🇪",
  GB: "🇬🇧",
  FR: "🇫🇷",
  IT: "🇮🇹",
  ES: "🇪🇸",
  JP: "🇯🇵",
  CN: "🇨🇳",
  AU: "🇦🇺",
  CA: "🇨🇦",
  CH: "🇨🇭",
  NL: "🇳🇱",
  SE: "🇸🇪",
  NO: "🇳🇴",
  BR: "🇧🇷",
  MX: "🇲🇽",
  IN: "🇮🇳",
  KR: "🇰🇷",
  SG: "🇸🇬",
  NZ: "🇳🇿",
};

// Status bar tickers that map to symbolic lookups inside snapshot data
const STATUS_BAR_TICKERS = [
  "SPX",
  "NDX",
  "DJI",
  "VIX",
  "EUR/USD",
  "Gold",
] as const;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(n: number | undefined, decimals = 2): string {
  if (n === undefined || n === null || isNaN(n)) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtPrice(n: number): string {
  if (n >= 10_000) return fmt(n, 0);
  if (n >= 1_000) return fmt(n, 2);
  if (n >= 100) return fmt(n, 2);
  if (n >= 1) return fmt(n, 4);
  return fmt(n, 6);
}

function changeColor(pct: number): string {
  if (pct > 0) return "#10B981";
  if (pct < 0) return "#EF4444";
  return "#94A3B8";
}

function changeVariant(pct: number): "up" | "down" | "neutral" {
  if (pct > 0) return "up";
  if (pct < 0) return "down";
  return "neutral";
}

function isMarketOpen(): boolean {
  const now = new Date();
  const day = now.getUTCDay(); // 0=Sun, 6=Sat
  if (day === 0 || day === 6) return false;
  const h = now.getUTCHours();
  // NYSE: 14:30–21:00 UTC (approximate)
  return h >= 14 && h < 21;
}

function nowTimestamp(): string {
  return new Date().toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

// ─── Demo / Fallback Data ────────────────────────────────────────────────────
// Shown only when the backend is unreachable so the page is never empty.

const DEMO_INDICES: Record<string, IndexItem[]> = {
  Americas: [
    {
      symbol: "SPX",
      name: "S&P 500",
      region: "Americas",
      price: 5_234.18,
      change: { percent: 0.47, absolute: 24.52 },
      timestamp: "",
    },
    {
      symbol: "NDX",
      name: "Nasdaq 100",
      region: "Americas",
      price: 18_312.75,
      change: { percent: 0.63, absolute: 114.88 },
      timestamp: "",
    },
    {
      symbol: "DJI",
      name: "Dow Jones",
      region: "Americas",
      price: 39_150.33,
      change: { percent: 0.21, absolute: 81.23 },
      timestamp: "",
    },
  ],
  Europe: [
    {
      symbol: "SX5E",
      name: "Euro Stoxx 50",
      region: "Europe",
      price: 5_005.4,
      change: { percent: -0.15, absolute: -7.5 },
      timestamp: "",
    },
    {
      symbol: "UKX",
      name: "FTSE 100",
      region: "Europe",
      price: 8_160.22,
      change: { percent: 0.08, absolute: 6.53 },
      timestamp: "",
    },
    {
      symbol: "DAX",
      name: "DAX 40",
      region: "Europe",
      price: 18_450.88,
      change: { percent: -0.32, absolute: -59.04 },
      timestamp: "",
    },
  ],
  "Asia Pacific": [
    {
      symbol: "NKY",
      name: "Nikkei 225",
      region: "Asia Pacific",
      price: 39_740.5,
      change: { percent: 1.02, absolute: 401.2 },
      timestamp: "",
    },
    {
      symbol: "HSI",
      name: "Hang Seng",
      region: "Asia Pacific",
      price: 16_520.88,
      change: { percent: -0.44, absolute: -73.1 },
      timestamp: "",
    },
  ],
  "Middle East/Other": [
    {
      symbol: "TASI",
      name: "Tadawul",
      region: "Middle East/Other",
      price: 12_310.95,
      change: { percent: 0.18, absolute: 22.16 },
      timestamp: "",
    },
  ],
};

const DEMO_FX_PAIRS: FXPair[] = [
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
  {
    symbol: "USDCAD",
    base: "USD",
    quote: "CAD",
    rate: 1.359,
    change: { percent: -0.09, absolute: -0.0012 },
  },
];

const DEMO_COMMODITIES: Record<string, Commodity[]> = {
  metals: [
    {
      symbol: "GC=F",
      name: "Gold",
      category: "metals",
      price: 2_345.6,
      unit: "USD/oz",
      change: { percent: 0.55, absolute: 12.8 },
    },
    {
      symbol: "SI=F",
      name: "Silver",
      category: "metals",
      price: 27.92,
      unit: "USD/oz",
      change: { percent: 0.78, absolute: 0.216 },
    },
    {
      symbol: "HG=F",
      name: "Copper",
      category: "metals",
      price: 4.18,
      unit: "USD/lb",
      change: { percent: -0.31, absolute: -0.013 },
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

const DEMO_BONDS: BondItem[] = [
  {
    country: "United States",
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
  {
    country: "Italy",
    country_code: "IT",
    yield_2y: 3.55,
    yield_5y: 3.42,
    yield_10y: 3.82,
  },
  {
    country: "Canada",
    country_code: "CA",
    yield_2y: 4.12,
    yield_5y: 3.68,
    yield_10y: 3.52,
  },
  {
    country: "Australia",
    country_code: "AU",
    yield_2y: 3.95,
    yield_5y: 3.88,
    yield_10y: 4.15,
  },
];

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function SkeletonBlock({
  w = "100%",
  h = 18,
  radius = 4,
}: {
  w?: string | number;
  h?: number;
  radius?: number;
}) {
  return (
    <div
      style={{
        width: w,
        height: h,
        borderRadius: radius,
        background:
          "linear-gradient(90deg, rgba(51,65,85,0.25) 25%, rgba(51,65,85,0.45) 50%, rgba(51,65,85,0.25) 75%)",
        backgroundSize: "200% 100%",
        animation: "skeleton-shimmer 1.6s ease-in-out infinite",
        flexShrink: 0,
      }}
    />
  );
}

function SkeletonCard() {
  return (
    <div
      style={{
        backgroundColor: "#131823",
        border: "1px solid rgba(51,65,85,0.3)",
        borderRadius: 8,
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <SkeletonBlock w="60%" h={12} />
      <SkeletonBlock w="80%" h={22} />
      <SkeletonBlock w="40%" h={12} />
    </div>
  );
}

// ─── Sparkline (aesthetic 5-bar visual) ───────────────────────────────────────

function MiniSparkline({ pct }: { pct: number }) {
  // Generate a fake 5-bar pattern that trends in the direction of pct
  const seed = Math.abs(pct * 37) % 1;
  const bars = [
    0.4 + seed * 0.3,
    0.3 + ((seed * 7) % 0.4),
    0.5 + ((seed * 13) % 0.35),
    0.35 + ((seed * 19) % 0.4),
    pct > 0 ? 0.7 + ((seed * 11) % 0.3) : 0.2 + ((seed * 11) % 0.25),
  ];
  const accent = pct > 0 ? "#10B981" : pct < 0 ? "#EF4444" : "#475569";

  return (
    <div
      style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 20 }}
    >
      {bars.map((h, i) => (
        <div
          key={i}
          style={{
            width: 5,
            height: `${h * 100}%`,
            backgroundColor: i === 4 ? accent : `${accent}55`,
            borderRadius: "2px 2px 0 0",
            flexShrink: 0,
          }}
        />
      ))}
    </div>
  );
}

// ─── Market Status Bar ────────────────────────────────────────────────────────

interface TickerDisplay {
  label: string;
  price: string;
  pct: number;
}

function StatusBarTicker({ ticker }: { ticker: TickerDisplay }) {
  const color = changeColor(ticker.pct);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 1,
        padding: "0 14px",
        borderRight: "1px solid rgba(51,65,85,0.3)",
        minWidth: 90,
      }}
    >
      <span
        style={{
          fontFamily: MONO,
          fontSize: 10,
          fontWeight: 700,
          color: "#64748B",
          letterSpacing: "0.07em",
          textTransform: "uppercase",
        }}
      >
        {ticker.label}
      </span>
      <span
        style={{
          fontFamily: MONO,
          fontSize: 13,
          fontWeight: 600,
          color: "#F1F5F9",
          lineHeight: 1,
        }}
      >
        {ticker.price}
      </span>
      <span style={{ fontFamily: MONO, fontSize: 10, color, lineHeight: 1 }}>
        {ticker.pct > 0 ? "▲" : ticker.pct < 0 ? "▼" : "●"}{" "}
        {Math.abs(ticker.pct).toFixed(2)}%
      </span>
    </div>
  );
}

function MarketStatusBar({
  tickers,
  isFetching,
  onRefresh,
  isRefreshing,
  dataQuality,
}: {
  tickers: TickerDisplay[];
  isFetching: boolean;
  onRefresh: () => void;
  isRefreshing: boolean;
  dataQuality: DataQuality;
}) {
  const [timestamp, setTimestamp] = useState(nowTimestamp);
  const open = isMarketOpen();

  useEffect(() => {
    const id = setInterval(() => setTimestamp(nowTimestamp()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        backgroundColor: "#0D1117",
        border: "1px solid rgba(51,65,85,0.4)",
        borderRadius: 8,
        padding: "8px 16px",
        marginBottom: 24,
        gap: 12,
        overflowX: "auto",
        flexWrap: "nowrap",
        flexShrink: 0,
      }}
    >
      {/* Left: label + open/closed */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          flexShrink: 0,
        }}
      >
        <span
          style={{
            fontFamily: MONO,
            fontSize: 11,
            fontWeight: 700,
            color: "#94A3B8",
            letterSpacing: "0.1em",
          }}
        >
          MARKETS
        </span>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            backgroundColor: open
              ? "rgba(16,185,129,0.12)"
              : "rgba(239,68,68,0.12)",
            border: `1px solid ${open ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)"}`,
            color: open ? "#10B981" : "#EF4444",
            borderRadius: 9999,
            padding: "2px 8px",
            fontFamily: MONO,
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: "0.08em",
            flexShrink: 0,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              backgroundColor: open ? "#10B981" : "#EF4444",
              display: "inline-block",
              animation: open
                ? "pulse-green 1.5s ease-in-out infinite"
                : "none",
              flexShrink: 0,
            }}
          />
          {open ? "OPEN" : "CLOSED"}
        </span>
        <DataQualityBadge quality={dataQuality} />
      </div>

      {/* Center: tickers */}
      <div style={{ display: "flex", alignItems: "center", flexShrink: 0 }}>
        {tickers.length > 0
          ? tickers.map((t) => <StatusBarTicker key={t.label} ticker={t} />)
          : STATUS_BAR_TICKERS.map((label) => (
              <div
                key={label}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 3,
                  padding: "0 14px",
                  borderRight: "1px solid rgba(51,65,85,0.3)",
                  minWidth: 90,
                }}
              >
                <SkeletonBlock w={40} h={10} />
                <SkeletonBlock w={55} h={14} />
                <SkeletonBlock w={35} h={10} />
              </div>
            ))}
      </div>

      {/* Right: timestamp + refresh */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          flexShrink: 0,
        }}
      >
        {(isFetching || isRefreshing) && <Spinner size="sm" />}
        <span
          style={{
            fontFamily: MONO,
            fontSize: 11,
            color: "#64748B",
            whiteSpace: "nowrap",
          }}
        >
          {timestamp}
        </span>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh all market data"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            backgroundColor: "rgba(0,217,255,0.08)",
            border: "1px solid rgba(0,217,255,0.2)",
            color: isRefreshing ? "#64748B" : "#00D9FF",
            borderRadius: 6,
            padding: "5px 12px",
            fontFamily: MONO,
            fontSize: 11,
            fontWeight: 500,
            cursor: isRefreshing ? "not-allowed" : "pointer",
            transition: "background-color 0.15s",
            whiteSpace: "nowrap",
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
              width="11"
              height="11"
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
          Refresh
        </button>
      </div>
    </div>
  );
}

// ─── Section 1: Global Indices ─────────────────────────────────────────────────

function IndexMiniCard({ item }: { item: IndexItem }) {
  const pct = item.change.percent;
  const color = changeColor(pct);
  return (
    <div
      style={{
        backgroundColor: "rgba(10,14,26,0.5)",
        border: "1px solid rgba(51,65,85,0.2)",
        borderRadius: 6,
        padding: "10px 12px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        transition: "border-color 0.15s",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor =
          "rgba(0,217,255,0.2)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor =
          "rgba(51,65,85,0.2)";
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <span
          style={{
            fontFamily: MONO,
            fontSize: 11,
            fontWeight: 600,
            color: "#F1F5F9",
          }}
        >
          {item.name.length > 18 ? item.name.slice(0, 18) + "…" : item.name}
        </span>
        <span
          style={{
            fontFamily: MONO,
            fontSize: 10,
            color: "#64748B",
            flexShrink: 0,
            marginLeft: 4,
          }}
        >
          {item.symbol}
        </span>
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <span
            style={{
              fontFamily: MONO,
              fontSize: 14,
              fontWeight: 600,
              color: "#00D9FF",
            }}
          >
            {fmtPrice(item.price)}
          </span>
          <span style={{ fontFamily: MONO, fontSize: 10, color }}>
            {pct > 0 ? "▲" : pct < 0 ? "▼" : "●"} {Math.abs(pct).toFixed(2)}%
          </span>
        </div>
        <MiniSparkline pct={pct} />
      </div>
    </div>
  );
}

function RegionColumn({
  region,
  items,
}: {
  region: string;
  items: IndexItem[];
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {/* Region header */}
      <div
        style={{
          fontFamily: MONO,
          fontSize: 10,
          fontWeight: 700,
          color: "#00D9FF",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          paddingBottom: 6,
          borderBottom: "1px solid rgba(0,217,255,0.2)",
          marginBottom: 2,
        }}
      >
        {region}
      </div>
      {items.map((item) => (
        <IndexMiniCard key={item.symbol} item={item} />
      ))}
    </div>
  );
}

function DemoBanner() {
  return (
    <div
      style={{
        fontFamily: MONO,
        fontSize: 10,
        color: "#F59E0B",
        backgroundColor: "rgba(245,158,11,0.08)",
        border: "1px solid rgba(245,158,11,0.2)",
        borderRadius: 6,
        padding: "6px 12px",
        marginBottom: 16,
        letterSpacing: "0.04em",
      }}
    >
      Live data unavailable — showing demo values. Click Refresh to retry.
    </div>
  );
}

function GlobalIndicesSection() {
  const { data, isLoading, error } = useIndices();

  const usingDemo = !isLoading && (!!error || !data);
  const displayData = data ?? DEMO_INDICES;

  return (
    <section style={{ marginBottom: 28 }}>
      <SectionTitle label="Global Indices Overview" />
      {usingDemo && <DemoBanner />}
      {isLoading ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 16,
          }}
        >
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              style={{ display: "flex", flexDirection: "column", gap: 8 }}
            >
              <SkeletonBlock w="60%" h={10} />
              {[0, 1, 2].map((j) => (
                <SkeletonCard key={j} />
              ))}
            </div>
          ))}
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 16,
          }}
        >
          {REGION_ORDER.filter(
            (r) => displayData[r] && displayData[r].length > 0,
          ).map((region) => (
            <RegionColumn
              key={region}
              region={region}
              items={displayData[region]}
            />
          ))}
          {Object.keys(displayData)
            .filter(
              (r) => !REGION_ORDER.includes(r) && displayData[r].length > 0,
            )
            .map((region) => (
              <RegionColumn
                key={region}
                region={region}
                items={displayData[region]}
              />
            ))}
        </div>
      )}
    </section>
  );
}

// ─── Section 2: Watchlist Grid ─────────────────────────────────────────────────

function FXWatchCard({ pair }: { pair: FXPair }) {
  const pct = pair.change.percent;
  const variant = changeVariant(pct);
  const color = changeColor(pct);
  return (
    <div
      style={{
        backgroundColor: "#131823",
        border: "1px solid rgba(51,65,85,0.3)",
        borderRadius: 8,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
        transition: "border-color 0.15s",
        cursor: "default",
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
          alignItems: "center",
        }}
      >
        <span
          style={{
            fontFamily: MONO,
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
      <span
        style={{
          fontFamily: MONO,
          fontSize: 22,
          fontWeight: 600,
          color: "#00D9FF",
          lineHeight: 1,
        }}
      >
        {pair.rate.toFixed(4)}
      </span>
      <span style={{ fontFamily: MONO, fontSize: 11, color }}>
        {pair.change.absolute > 0 ? "+" : ""}
        {pair.change.absolute.toFixed(4)}
      </span>
    </div>
  );
}

function CommodityWatchCard({ commodity }: { commodity: Commodity }) {
  const pct = commodity.change.percent;
  const variant = changeVariant(pct);
  const color = changeColor(pct);
  return (
    <div
      style={{
        backgroundColor: "#131823",
        border: "1px solid rgba(51,65,85,0.3)",
        borderRadius: 8,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
        transition: "border-color 0.15s",
        cursor: "default",
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
          alignItems: "center",
        }}
      >
        <div>
          <div
            style={{
              fontFamily: MONO,
              fontSize: 13,
              fontWeight: 700,
              color: "#F1F5F9",
            }}
          >
            {commodity.name}
          </div>
          <div style={{ fontFamily: MONO, fontSize: 10, color: "#64748B" }}>
            {commodity.symbol} · {commodity.unit}
          </div>
        </div>
        <Badge variant={variant}>
          {pct > 0 ? "+" : ""}
          {pct.toFixed(2)}%
        </Badge>
      </div>
      <span
        style={{
          fontFamily: MONO,
          fontSize: 20,
          fontWeight: 600,
          color: "#00D9FF",
          lineHeight: 1,
        }}
      >
        {fmtPrice(commodity.price)}
      </span>
      <span style={{ fontFamily: MONO, fontSize: 11, color }}>
        {commodity.change.absolute > 0 ? "+" : ""}
        {commodity.change.absolute.toFixed(commodity.price >= 100 ? 2 : 4)}
      </span>
    </div>
  );
}

const COMMODITY_WATCHLIST = [
  "Gold",
  "Crude Oil",
  "WTI",
  "Silver",
  "Copper",
  "Natural Gas",
];

function WatchlistSection() {
  const { data: fxData, isLoading: fxLoading, error: fxError } = useFX();
  const {
    data: commData,
    isLoading: commLoading,
    error: commError,
  } = useCommodities();

  const fxUsingDemo = !fxLoading && (!!fxError || !fxData);
  const commUsingDemo = !commLoading && (!!commError || !commData);

  // Pull FX pairs — top 6 (fall back to demo)
  const fxPairs = (fxData?.pairs ?? (fxUsingDemo ? DEMO_FX_PAIRS : [])).slice(
    0,
    6,
  );

  // Pull commodities from watchlist names (fall back to demo)
  const allComm: Commodity[] = commData
    ? Object.values(commData).flat()
    : commUsingDemo
      ? Object.values(DEMO_COMMODITIES).flat()
      : [];
  const watchCommodities = allComm
    .filter((c) =>
      COMMODITY_WATCHLIST.some((n) =>
        c.name.toLowerCase().includes(n.toLowerCase()),
      ),
    )
    .slice(0, 5);

  const skeletonRow = (cols: number) => (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: 12,
      }}
    >
      {Array.from({ length: cols }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );

  return (
    <section style={{ marginBottom: 28 }}>
      <SectionTitle label="Watchlist" />
      {(fxUsingDemo || commUsingDemo) && <DemoBanner />}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* FX Row */}
        <div>
          <WatchRowLabel label="FX" />
          {fxLoading || fxPairs.length === 0 ? (
            skeletonRow(6)
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(6, 1fr)",
                gap: 12,
              }}
            >
              {fxPairs.map((pair) => (
                <FXWatchCard key={pair.symbol} pair={pair} />
              ))}
            </div>
          )}
        </div>

        {/* Commodities Row */}
        <div>
          <WatchRowLabel label="Commodities" />
          {commLoading || watchCommodities.length === 0 ? (
            skeletonRow(5)
          ) : (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(5, 1fr)",
                gap: 12,
              }}
            >
              {watchCommodities.map((c) => (
                <CommodityWatchCard key={c.symbol} commodity={c} />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function WatchRowLabel({ label }: { label: string }) {
  return (
    <div
      style={{
        fontFamily: MONO,
        fontSize: 10,
        fontWeight: 700,
        color: "#64748B",
        letterSpacing: "0.1em",
        textTransform: "uppercase",
        marginBottom: 8,
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}
    >
      <span
        style={{
          display: "inline-block",
          width: 3,
          height: 12,
          backgroundColor: "#00D9FF",
          borderRadius: 2,
        }}
      />
      {label}
    </div>
  );
}

// ─── Section 3: Market Movers ─────────────────────────────────────────────────

interface MoverItem {
  name: string;
  symbol: string;
  pct: number;
}

function MoverRow({ item, rank }: { item: MoverItem; rank: number }) {
  const variant = changeVariant(item.pct);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 10px",
        borderRadius: 6,
        transition: "background-color 0.12s",
        cursor: "default",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.backgroundColor =
          "rgba(255,255,255,0.04)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.backgroundColor =
          "transparent";
      }}
    >
      <span
        style={{
          fontFamily: MONO,
          fontSize: 10,
          color: "#475569",
          minWidth: 18,
          textAlign: "right",
          flexShrink: 0,
        }}
      >
        {rank}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontFamily: MONO,
            fontSize: 12,
            fontWeight: 600,
            color: "#F1F5F9",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {item.name}
        </div>
        <div style={{ fontFamily: MONO, fontSize: 10, color: "#64748B" }}>
          {item.symbol}
        </div>
      </div>
      <Badge variant={variant}>
        {item.pct > 0 ? "+" : ""}
        {item.pct.toFixed(2)}%
      </Badge>
    </div>
  );
}

function MoversColumn({
  title,
  items,
  accentColor,
}: {
  title: string;
  items: MoverItem[];
  accentColor: string;
}) {
  return (
    <Card>
      <div
        style={{
          fontFamily: MONO,
          fontSize: 11,
          fontWeight: 700,
          color: accentColor,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          marginBottom: 12,
          paddingBottom: 8,
          borderBottom: `1px solid ${accentColor}33`,
        }}
      >
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {items.map((item, i) => (
          <MoverRow key={item.symbol} item={item} rank={i + 1} />
        ))}
      </div>
    </Card>
  );
}

function MarketMoversSection() {
  const { data: indicesData, error: indicesError } = useIndices();
  const { data: fxData, error: fxError } = useFX();
  const { data: commData, error: commError } = useCommodities();

  // Fall back to demo data if backend is unreachable
  const indicesSource =
    indicesData ?? (indicesError ? DEMO_INDICES : undefined);
  const fxSource = fxData ?? (fxError ? { pairs: DEMO_FX_PAIRS } : undefined);
  const commSource = commData ?? (commError ? DEMO_COMMODITIES : undefined);

  // Build unified list of all assets with pct change
  const allMovers: MoverItem[] = [];

  if (indicesSource) {
    for (const items of Object.values(indicesSource)) {
      for (const item of items) {
        allMovers.push({
          name: item.name,
          symbol: item.symbol,
          pct: item.change.percent,
        });
      }
    }
  }
  if (fxSource) {
    for (const pair of fxSource.pairs ?? []) {
      allMovers.push({
        name: `${pair.base}/${pair.quote}`,
        symbol: pair.symbol,
        pct: pair.change.percent,
      });
    }
  }
  if (commSource) {
    for (const items of Object.values(commSource)) {
      for (const c of items) {
        allMovers.push({
          name: c.name,
          symbol: c.symbol,
          pct: c.change.percent,
        });
      }
    }
  }

  const sorted = [...allMovers].sort((a, b) => b.pct - a.pct);
  const gainers = sorted.slice(0, 5);
  const losers = [...allMovers].sort((a, b) => a.pct - b.pct).slice(0, 5);
  const volatile = [...allMovers]
    .sort((a, b) => Math.abs(b.pct) - Math.abs(a.pct))
    .slice(0, 5);

  const noData = allMovers.length === 0;

  return (
    <section style={{ marginBottom: 28 }}>
      <SectionTitle label="Market Movers" />
      {noData ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 16,
          }}
        >
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                backgroundColor: "#131823",
                border: "1px solid rgba(51,65,85,0.3)",
                borderRadius: 8,
                padding: 16,
                display: "flex",
                flexDirection: "column",
                gap: 10,
              }}
            >
              <SkeletonBlock w="50%" h={12} />
              {[0, 1, 2, 3, 4].map((j) => (
                <div
                  key={j}
                  style={{ display: "flex", gap: 8, alignItems: "center" }}
                >
                  <SkeletonBlock w={20} h={10} />
                  <SkeletonBlock w="60%" h={10} />
                  <SkeletonBlock w={50} h={18} />
                </div>
              ))}
            </div>
          ))}
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 16,
          }}
        >
          <MoversColumn
            title="Top Gainers"
            items={gainers}
            accentColor="#10B981"
          />
          <MoversColumn
            title="Top Losers"
            items={losers}
            accentColor="#EF4444"
          />
          <MoversColumn
            title="Most Volatile"
            items={volatile}
            accentColor="#F59E0B"
          />
        </div>
      )}
    </section>
  );
}

// ─── Section 4: Bonds Snapshot ────────────────────────────────────────────────

function yieldCurveShape(
  y2: number | undefined,
  y10: number | undefined,
): { label: string; color: string } {
  if (y2 === undefined || y10 === undefined)
    return { label: "—", color: "#64748B" };
  const spread = y10 - y2;
  if (spread > 0.5) return { label: "STEEP", color: "#10B981" };
  if (spread > 0) return { label: "NORMAL", color: "#94A3B8" };
  if (spread > -0.5) return { label: "FLAT", color: "#F59E0B" };
  return { label: "INVERTED", color: "#EF4444" };
}

function yieldColor(y: number | undefined): string {
  if (y === undefined) return "#64748B";
  if (y < 0) return "#A855F7";
  if (y > 5) return "#EF4444";
  if (y > 4) return "#F59E0B";
  return "#CBD5E1";
}

const TH: React.CSSProperties = {
  color: "#64748B",
  fontSize: 10,
  fontFamily: MONO,
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  padding: "8px 12px",
  textAlign: "left",
  borderBottom: "1px solid rgba(51,65,85,0.4)",
  whiteSpace: "nowrap",
  backgroundColor: "rgba(10,14,26,0.5)",
};

const TD: React.CSSProperties = {
  padding: "9px 12px",
  fontSize: 12,
  fontFamily: MONO,
  color: "#CBD5E1",
  borderBottom: "1px solid rgba(51,65,85,0.12)",
  whiteSpace: "nowrap",
};

function BondsSnapshotSection() {
  const { data, isLoading, error } = useBonds();

  const usingDemo = !isLoading && (!!error || !data);
  const bonds: BondItem[] = (
    data?.bonds ?? (usingDemo ? DEMO_BONDS : [])
  ).slice(0, 10);

  return (
    <section style={{ marginBottom: 28 }}>
      <SectionTitle label="Bonds Snapshot" />
      {usingDemo && <DemoBanner />}
      <Card>
        {isLoading || bonds.length === 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div
              style={{
                display: "flex",
                gap: 12,
                paddingBottom: 8,
                borderBottom: "1px solid rgba(51,65,85,0.3)",
              }}
            >
              {[80, 140, 80, 80, 100, 100].map((w, i) => (
                <SkeletonBlock key={i} w={w} h={10} />
              ))}
            </div>
            {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => (
              <div
                key={i}
                style={{ display: "flex", gap: 12, padding: "6px 0" }}
              >
                {[80, 140, 80, 80, 100, 100].map((w, j) => (
                  <SkeletonBlock key={j} w={w} h={12} />
                ))}
              </div>
            ))}
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={TH}>Flag</th>
                  <th style={TH}>Country</th>
                  <th style={{ ...TH, textAlign: "right" }}>2Y Yield</th>
                  <th style={{ ...TH, textAlign: "right" }}>10Y Yield</th>
                  <th style={{ ...TH, textAlign: "right" }}>2Y–10Y Spread</th>
                  <th style={{ ...TH, textAlign: "center" }}>Curve</th>
                </tr>
              </thead>
              <tbody>
                {bonds.map((bond, i) => {
                  const spread =
                    bond.yield_10y !== undefined && bond.yield_2y !== undefined
                      ? bond.yield_10y - bond.yield_2y
                      : undefined;
                  const curve = yieldCurveShape(bond.yield_2y, bond.yield_10y);
                  return (
                    <tr
                      key={bond.country_code}
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
                      <td style={{ ...TD, textAlign: "center", fontSize: 16 }}>
                        {COUNTRY_FLAGS[bond.country_code] ?? bond.country_code}
                      </td>
                      <td style={{ ...TD, color: "#F1F5F9", fontWeight: 500 }}>
                        {bond.country}
                      </td>
                      <td
                        style={{
                          ...TD,
                          textAlign: "right",
                          color: yieldColor(bond.yield_2y),
                        }}
                      >
                        {bond.yield_2y !== undefined
                          ? `${bond.yield_2y.toFixed(2)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          ...TD,
                          textAlign: "right",
                          color: yieldColor(bond.yield_10y),
                        }}
                      >
                        {bond.yield_10y !== undefined
                          ? `${bond.yield_10y.toFixed(2)}%`
                          : "—"}
                      </td>
                      <td
                        style={{
                          ...TD,
                          textAlign: "right",
                          color:
                            spread !== undefined
                              ? spread >= 0
                                ? "#10B981"
                                : "#EF4444"
                              : "#64748B",
                        }}
                      >
                        {spread !== undefined
                          ? `${spread >= 0 ? "+" : ""}${(spread * 100).toFixed(0)} bp`
                          : "—"}
                      </td>
                      <td style={{ ...TD, textAlign: "center" }}>
                        <span
                          style={{
                            fontFamily: MONO,
                            fontSize: 10,
                            fontWeight: 700,
                            color: curve.color,
                            backgroundColor: `${curve.color}18`,
                            border: `1px solid ${curve.color}30`,
                            borderRadius: 4,
                            padding: "2px 6px",
                            letterSpacing: "0.06em",
                          }}
                        >
                          {curve.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </section>
  );
}

// ─── Section Title helper ─────────────────────────────────────────────────────

function SectionTitle({ label }: { label: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        marginBottom: 14,
      }}
    >
      <span
        style={{
          display: "inline-block",
          width: 3,
          height: 16,
          backgroundColor: "#00D9FF",
          borderRadius: 2,
          flexShrink: 0,
        }}
      />
      <h2
        style={{
          fontFamily: MONO,
          fontSize: 13,
          fontWeight: 700,
          color: "#F1F5F9",
          margin: 0,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {label}
      </h2>
    </div>
  );
}

// ─── Status bar ticker builder ─────────────────────────────────────────────────

function buildStatusBarTickers(
  snapshot: FullSnapshot | null | undefined,
): TickerDisplay[] {
  if (!snapshot) return [];
  const result: TickerDisplay[] = [];

  // SPX, NDX, DJI, VIX from indices
  const symbolMap: Record<string, string> = {
    SPX: "S&P 500",
    NDX: "Nasdaq",
    DJI: "Dow Jones",
    VIX: "VIX",
  };
  const allIndices: IndexItem[] = Object.values(snapshot.indices ?? {}).flat();
  for (const [sym, _label] of Object.entries(symbolMap)) {
    const found = allIndices.find(
      (idx) =>
        idx.symbol === sym ||
        idx.symbol.includes(sym) ||
        idx.name.toLowerCase().includes(sym.toLowerCase()),
    );
    if (found) {
      result.push({
        label: sym,
        price: fmtPrice(found.price),
        pct: found.change.percent,
      });
    }
  }

  // EUR/USD from FX
  const eurusd = snapshot.fx?.pairs?.find(
    (p) =>
      (p.base === "EUR" && p.quote === "USD") ||
      p.symbol === "EUR/USD" ||
      p.symbol === "EURUSD",
  );
  if (eurusd) {
    result.push({
      label: "EUR/USD",
      price: eurusd.rate.toFixed(4),
      pct: eurusd.change.percent,
    });
  }

  // Gold from commodities
  const allComm: Commodity[] = Object.values(snapshot.commodities ?? {}).flat();
  const gold = allComm.find(
    (c) =>
      c.name.toLowerCase().includes("gold") ||
      c.symbol === "GC=F" ||
      c.symbol === "GOLD",
  );
  if (gold) {
    result.push({
      label: "Gold",
      price: fmtPrice(gold.price),
      pct: gold.change.percent,
    });
  }

  return result;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LiveMarket() {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const queryClient = useQueryClient();

  const snapshotQuery = useSnapshot();
  const indicesQuery = useIndices();
  const fxQuery = useFX();
  const commQuery = useCommodities();
  const bondsQuery = useBonds();

  const isFetching =
    snapshotQuery.isFetching ||
    indicesQuery.isFetching ||
    fxQuery.isFetching ||
    commQuery.isFetching ||
    bondsQuery.isFetching;

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await refreshCache();
      await queryClient.invalidateQueries({ queryKey: marketKeys.all });
    } catch {
      // individual sections surface their own errors
    } finally {
      setIsRefreshing(false);
    }
  }, [queryClient]);

  // Build status bar tickers — fall back to demo snapshot when backend unreachable
  const demoSnapshot: FullSnapshot = {
    indices: DEMO_INDICES,
    bonds: { bonds: DEMO_BONDS },
    fx: { pairs: DEMO_FX_PAIRS },
    commodities: DEMO_COMMODITIES,
    macro: { indicators: [] },
    timestamp: new Date().toISOString(),
    cache_hit: false,
    data_quality: "demo_static",
  };
  const snapshotData =
    snapshotQuery.data ?? (snapshotQuery.error ? demoSnapshot : undefined);
  const statusTickers = buildStatusBarTickers(snapshotData ?? null);
  const dataQuality: DataQuality = snapshotData?.data_quality ?? "unknown";

  return (
    <>
      <style>{`
        @keyframes pulse-green {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.35; }
        }
        @keyframes skeleton-shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>

      <div style={{ color: "#F1F5F9", minHeight: "100vh", maxWidth: "100%" }}>
        {/* ── Page header ─────────────────────────────────────── */}
        <div style={{ marginBottom: 20 }}>
          <h1
            style={{
              fontFamily: MONO,
              fontSize: 22,
              fontWeight: 700,
              color: "#F1F5F9",
              margin: 0,
              letterSpacing: "-0.01em",
            }}
          >
            Live Market
          </h1>
          <p
            style={{
              fontFamily: MONO,
              fontSize: 11,
              color: "#64748B",
              margin: "4px 0 0",
            }}
          >
            Real-time global cross-asset dashboard
          </p>
        </div>

        {/* ── Market Status Bar ────────────────────────────────── */}
        <MarketStatusBar
          tickers={statusTickers}
          isFetching={isFetching}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
          dataQuality={dataQuality}
        />

        {/* ── Section 1: Global Indices ────────────────────────── */}
        <GlobalIndicesSection />

        {/* ── Section 2: Watchlist ─────────────────────────────── */}
        <WatchlistSection />

        {/* ── Section 3: Market Movers ─────────────────────────── */}
        <MarketMoversSection />

        {/* ── Section 4: Bonds Snapshot ────────────────────────── */}
        <BondsSnapshotSection />
      </div>
    </>
  );
}
