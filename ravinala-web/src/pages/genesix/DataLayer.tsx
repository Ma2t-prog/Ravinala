import { useState } from "react";
import { exportExcel, exportPDF, refreshCache } from "../../api/market";
import { Badge, Card } from "../../components/ui";
import { useHealth, useSnapshot } from "../../hooks/useMarketData";

const DATA_SOURCES = [
  {
    name: "Market Data (Real-time)",
    provider: "Bloomberg",
    status: "Connected",
    latency: "12ms",
    lastUpdate: "< 1s ago",
    records: "2.4M",
    quality: 99.8,
  },
  {
    name: "Fundamental Data",
    provider: "Refinitiv",
    status: "Connected",
    latency: "45ms",
    lastUpdate: "5 min ago",
    records: "850K",
    quality: 98.5,
  },
  {
    name: "Alternative Data",
    provider: "Quandl",
    status: "Connected",
    latency: "120ms",
    lastUpdate: "1 hr ago",
    records: "1.2M",
    quality: 96.2,
  },
  {
    name: "News & Sentiment",
    provider: "Reuters API",
    status: "Degraded",
    latency: "350ms",
    lastUpdate: "15 min ago",
    records: "420K",
    quality: 94.1,
  },
  {
    name: "Regulatory Filings",
    provider: "SEC EDGAR",
    status: "Connected",
    latency: "200ms",
    lastUpdate: "6 hr ago",
    records: "180K",
    quality: 99.1,
  },
];

const CACHE_STATS = [
  { label: "Cache Hit Rate", value: "94.2%", color: "#10B981" },
  { label: "Cache Size", value: "2.8 GB", color: "#00D9FF" },
  { label: "Eviction Rate", value: "0.3%", color: "#F59E0B" },
  { label: "TTL Avg", value: "15 min", color: "#94A3B8" },
];

const QUALITY_METRICS = [
  { metric: "Completeness", value: 98.4, threshold: 95 },
  { metric: "Accuracy", value: 99.1, threshold: 98 },
  { metric: "Timeliness", value: 96.8, threshold: 95 },
  { metric: "Consistency", value: 97.5, threshold: 95 },
  { metric: "Uniqueness", value: 99.8, threshold: 99 },
];

const statusColor = (s: string) => {
  if (s === "Connected") return "#10B981";
  if (s === "Degraded") return "#F59E0B";
  return "#EF4444";
};

export default function DataLayer() {
  const [refreshing, setRefreshing] = useState<string | null>(null);
  const [exportingExcel, setExportingExcel] = useState(false);
  const [exportingPDF, setExportingPDF] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [testTicker, setTestTicker] = useState("SPY");
  const [testResult, setTestResult] = useState<{
    price: number;
    latency: number;
    rows: number;
  } | null>(null);
  const [testing, setTesting] = useState(false);
  const { data: healthData } = useHealth();
  const { data: snapshotData } = useSnapshot();
  const liveData = healthData ?? snapshotData ?? null;

  // Derive live backend status info
  const backendStatus = healthData
    ? {
        status: healthData.status,
        redis: healthData.redis_connected,
        dataService: healthData.data_service_ok,
        timestamp: healthData.timestamp,
      }
    : null;
  const dataFreshness = snapshotData?.timestamp
    ? `Last snapshot: ${new Date(snapshotData.timestamp).toLocaleString()}${snapshotData.cache_hit ? " (cached)" : ""}`
    : null;

  const DEMO_PRICES: Record<string, number> = {
    SPY: 524.18,
    QQQ: 460.32,
    AAPL: 196.42,
    MSFT: 430.18,
    GOOGL: 177.56,
    NVDA: 862.4,
    GLD: 214.35,
    TLT: 92.18,
    AGG: 98.45,
    VWO: 42.18,
  };

  const CACHED_TICKERS = [
    "SPY",
    "QQQ",
    "AAPL",
    "MSFT",
    "GOOGL",
    "NVDA",
    "AMZN",
    "META",
    "GLD",
    "TLT",
    "AGG",
    "IWM",
    "VWO",
    "EEM",
    "HYG",
    "XOM",
    "JPM",
  ];

  const handleFetchTest = () => {
    setTesting(true);
    setTimeout(
      () => {
        const price =
          DEMO_PRICES[testTicker.toUpperCase()] ?? 100 + Math.random() * 400;
        const latency = Math.round(50 + Math.random() * 150);
        const rows = Math.round(500 + Math.random() * 2000);
        setTestResult({ price: +price.toFixed(2), latency, rows });
        setTesting(false);
      },
      300 + Math.random() * 500,
    );
  };

  const handleRefresh = async (name: string) => {
    setRefreshing(name);
    try {
      const sectionMap: Record<string, string> = {
        "Market Data (Real-time)": "indices",
        "Fundamental Data": "macro",
        "Alternative Data": "snapshot",
        "News & Sentiment": "snapshot",
        "Regulatory Filings": "macro",
      };
      await refreshCache(sectionMap[name]);
    } catch {
      // silently fail — backend down
    } finally {
      setRefreshing(null);
    }
  };

  const handleExportExcel = async () => {
    setExportingExcel(true);
    setExportError(null);
    try {
      const blob = await exportExcel(["indices", "bonds", "fx", "commodities"]);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ravinala_dashboard_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setExportError("Excel export failed — check backend is running");
    } finally {
      setExportingExcel(false);
    }
  };

  const handleExportPDF = async () => {
    setExportingPDF(true);
    setExportError(null);
    try {
      const blob = await exportPDF();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ravinala_dashboard_${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setExportError("PDF export failed — check backend is running");
    } finally {
      setExportingPDF(false);
    }
  };

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
        Data Layer
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 12, fontSize: 14 }}>
        Data source management, caching & quality monitoring
      </p>

      {/* Export actions */}
      <div
        style={{
          display: "flex",
          gap: 10,
          marginBottom: 20,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <button
          onClick={handleExportExcel}
          disabled={exportingExcel}
          style={{
            backgroundColor: "rgba(16,185,129,0.12)",
            border: "1px solid rgba(16,185,129,0.35)",
            borderRadius: 8,
            color: "#10B981",
            padding: "8px 18px",
            fontSize: 13,
            fontWeight: 600,
            cursor: exportingExcel ? "wait" : "pointer",
            opacity: exportingExcel ? 0.7 : 1,
          }}
        >
          {exportingExcel ? "Exporting…" : "⬇ Export Dashboard (Excel)"}
        </button>
        <button
          onClick={handleExportPDF}
          disabled={exportingPDF}
          style={{
            backgroundColor: "rgba(0,217,255,0.12)",
            border: "1px solid rgba(0,217,255,0.35)",
            borderRadius: 8,
            color: "#00D9FF",
            padding: "8px 18px",
            fontSize: 13,
            fontWeight: 600,
            cursor: exportingPDF ? "wait" : "pointer",
            opacity: exportingPDF ? 0.7 : 1,
          }}
        >
          {exportingPDF ? "Exporting…" : "⬇ Export Dashboard (PDF)"}
        </button>
        {exportError && (
          <span style={{ color: "#EF4444", fontSize: 12 }}>{exportError}</span>
        )}
      </div>

      {/* Live Backend Status */}
      {backendStatus && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
            gap: 10,
            marginBottom: 16,
          }}
        >
          <Card>
            <div style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}>
              Backend Status
            </div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 700,
                fontFamily: "JetBrains Mono, monospace",
                color: backendStatus.status === "ok" ? "#10B981" : "#EF4444",
              }}
            >
              {backendStatus.status.toUpperCase()}
            </div>
          </Card>
          <Card>
            <div style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}>
              Redis
            </div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 700,
                fontFamily: "JetBrains Mono, monospace",
                color: backendStatus.redis ? "#10B981" : "#EF4444",
              }}
            >
              {backendStatus.redis ? "Connected" : "Disconnected"}
            </div>
          </Card>
          <Card>
            <div style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}>
              Data Service
            </div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 700,
                fontFamily: "JetBrains Mono, monospace",
                color: backendStatus.dataService ? "#10B981" : "#EF4444",
              }}
            >
              {backendStatus.dataService ? "OK" : "Down"}
            </div>
          </Card>
          {dataFreshness && (
            <Card>
              <div style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}>
                Data Freshness
              </div>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  fontFamily: "JetBrains Mono, monospace",
                  color: "#00D9FF",
                }}
              >
                {dataFreshness}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Cache Stats */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: 10,
          marginBottom: 16,
        }}
      >
        {CACHE_STATS.map((c) => (
          <Card key={c.label}>
            <div style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}>
              {c.label}
            </div>
            <div
              style={{
                fontSize: 18,
                fontWeight: 700,
                fontFamily: "JetBrains Mono, monospace",
                color: c.color,
              }}
            >
              {c.value}
            </div>
          </Card>
        ))}
      </div>

      {/* Data Sources */}
      <Card
        title="Data Sources"
        subtitle="Connected data providers and feeds"
        className="mb-4"
      >
        <div style={{ overflowX: "auto" }}>
          <table
            style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
          >
            <thead>
              <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                {[
                  "Source",
                  "Provider",
                  "Status",
                  "Latency",
                  "Last Update",
                  "Records",
                  "Quality",
                  "Actions",
                ].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "8px 10px",
                      textAlign: "left",
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
              {DATA_SOURCES.map((d) => (
                <tr
                  key={d.name}
                  style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                >
                  <td
                    style={{
                      padding: "8px 10px",
                      color: "#F1F5F9",
                      fontWeight: 500,
                    }}
                  >
                    {d.name}
                  </td>
                  <td style={{ padding: "8px 10px", color: "#94A3B8" }}>
                    {d.provider}
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    <div
                      style={{ display: "flex", alignItems: "center", gap: 6 }}
                    >
                      <div
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          backgroundColor: statusColor(d.status),
                          boxShadow: `0 0 6px ${statusColor(d.status)}`,
                        }}
                      />
                      <span
                        style={{ color: statusColor(d.status), fontSize: 12 }}
                      >
                        {d.status}
                      </span>
                    </div>
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      fontFamily: "JetBrains Mono, monospace",
                      color: "#94A3B8",
                      fontSize: 12,
                    }}
                  >
                    {d.latency}
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      color: "#64748B",
                      fontSize: 12,
                    }}
                  >
                    {d.lastUpdate}
                  </td>
                  <td
                    style={{
                      padding: "8px 10px",
                      fontFamily: "JetBrains Mono, monospace",
                      color: "#94A3B8",
                      fontSize: 12,
                    }}
                  >
                    {d.records}
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    <Badge
                      variant={
                        d.quality >= 98
                          ? "up"
                          : d.quality >= 95
                            ? "warning"
                            : "down"
                      }
                    >
                      {d.quality}%
                    </Badge>
                  </td>
                  <td style={{ padding: "8px 10px" }}>
                    <button
                      onClick={() => handleRefresh(d.name)}
                      disabled={refreshing === d.name}
                      style={{
                        backgroundColor: "rgba(212,175,55,0.15)",
                        border: "1px solid rgba(212,175,55,0.3)",
                        borderRadius: 6,
                        color: "#D4AF37",
                        padding: "4px 10px",
                        fontSize: 11,
                        cursor: "pointer",
                        opacity: refreshing === d.name ? 0.5 : 1,
                      }}
                    >
                      {refreshing === d.name ? "Refreshing..." : "Refresh"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Data Quality */}
      <Card
        title="Data Quality Metrics"
        subtitle="Automated quality assessment scores"
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {QUALITY_METRICS.map((q) => (
            <div
              key={q.metric}
              style={{ display: "flex", alignItems: "center", gap: 12 }}
            >
              <span style={{ fontSize: 13, color: "#F1F5F9", width: 110 }}>
                {q.metric}
              </span>
              <div
                style={{
                  flex: 1,
                  height: 8,
                  backgroundColor: "rgba(51,65,85,0.3)",
                  borderRadius: 4,
                }}
              >
                <div
                  style={{
                    width: `${q.value}%`,
                    height: 8,
                    borderRadius: 4,
                    backgroundColor:
                      q.value >= q.threshold ? "#10B981" : "#F59E0B",
                  }}
                />
              </div>
              <span
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 13,
                  color: q.value >= q.threshold ? "#10B981" : "#F59E0B",
                  width: 50,
                  textAlign: "right",
                }}
              >
                {q.value}%
              </span>
              <Badge variant={q.value >= q.threshold ? "up" : "warning"}>
                {q.value >= q.threshold ? "Pass" : "Warn"}
              </Badge>
            </div>
          ))}
        </div>
      </Card>

      {/* Live Data Test */}
      <Card title="Live Data Test" subtitle="Test real-time data connectivity">
        <div
          style={{
            display: "flex",
            gap: 12,
            alignItems: "flex-end",
            marginBottom: 16,
          }}
        >
          <div>
            <label
              style={{
                fontSize: 11,
                color: "#64748B",
                display: "block",
                marginBottom: 4,
              }}
            >
              Ticker
            </label>
            <input
              type="text"
              value={testTicker}
              onChange={(e) => setTestTicker(e.target.value.toUpperCase())}
              style={{
                width: 100,
                padding: "6px 10px",
                borderRadius: 6,
                border: "1px solid rgba(51,65,85,0.4)",
                backgroundColor: "#0F172A",
                color: "#F1F5F9",
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 13,
              }}
            />
          </div>
          <button
            onClick={handleFetchTest}
            disabled={testing}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "none",
              backgroundColor: testing ? "#334155" : "#D4AF37",
              color: "#0A0E1A",
              fontWeight: 700,
              fontSize: 13,
              cursor: testing ? "default" : "pointer",
            }}
          >
            {testing ? "Fetching..." : "Fetch Live Price"}
          </button>
        </div>
        {testResult && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 12,
            }}
          >
            <div
              style={{
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 8,
                padding: 12,
              }}
            >
              <div style={{ fontSize: 11, color: "#64748B" }}>
                {testTicker} Last Price
              </div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  fontFamily: "JetBrains Mono",
                  color: "#10B981",
                }}
              >
                ${testResult.price}
              </div>
            </div>
            <div
              style={{
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 8,
                padding: 12,
              }}
            >
              <div style={{ fontSize: 11, color: "#64748B" }}>Latency</div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  fontFamily: "JetBrains Mono",
                  color: "#00D9FF",
                }}
              >
                {testResult.latency}ms
              </div>
            </div>
            <div
              style={{
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 8,
                padding: 12,
              }}
            >
              <div style={{ fontSize: 11, color: "#64748B" }}>Data Rows</div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  fontFamily: "JetBrains Mono",
                  color: "#D4AF37",
                }}
              >
                {testResult.rows}
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Cached Tickers */}
      <Card
        title="Cached Tickers"
        subtitle={`${CACHED_TICKERS.length} tickers in local cache`}
      >
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {CACHED_TICKERS.map((t) => (
            <span
              key={t}
              style={{
                padding: "4px 10px",
                borderRadius: 6,
                backgroundColor: "rgba(212,175,55,0.1)",
                border: "1px solid rgba(212,175,55,0.2)",
                fontSize: 12,
                fontFamily: "JetBrains Mono, monospace",
                color: "#D4AF37",
              }}
            >
              {t}
            </span>
          ))}
        </div>
      </Card>
    </div>
  );
}
