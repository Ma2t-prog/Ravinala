import { useMemo, useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Badge, Card } from "../../components/ui";
import { Tabs } from "../../components/ui/Tabs";
import { useIndices } from "../../hooks/useMarketData";

/* ─── Universe Search data ─── */
const INSTRUMENTS = [
  { ticker: "AAPL", name: "Apple Inc.", type: "Stock", exchange: "NASDAQ", sector: "Technology", country: "US", price: 227.48, pe: 33.2, divYield: 0.44, vol1y: 22.1, beta: 1.21, mcap: 3420 },
  { ticker: "MSFT", name: "Microsoft Corp.", type: "Stock", exchange: "NASDAQ", sector: "Technology", country: "US", price: 454.12, pe: 37.5, divYield: 0.72, vol1y: 24.8, beta: 1.05, mcap: 3380 },
  { ticker: "GOOGL", name: "Alphabet Inc.", type: "Stock", exchange: "NASDAQ", sector: "Technology", country: "US", price: 178.34, pe: 24.1, divYield: 0.0, vol1y: 28.3, beta: 1.12, mcap: 2190 },
  { ticker: "AMZN", name: "Amazon.com Inc.", type: "Stock", exchange: "NASDAQ", sector: "Consumer Cyclical", country: "US", price: 211.05, pe: 62.4, divYield: 0.0, vol1y: 31.2, beta: 1.18, mcap: 2180 },
  { ticker: "NVDA", name: "NVIDIA Corp.", type: "Stock", exchange: "NASDAQ", sector: "Technology", country: "US", price: 135.72, pe: 55.8, divYield: 0.02, vol1y: 52.4, beta: 1.72, mcap: 3340 },
  { ticker: "JPM", name: "JPMorgan Chase & Co.", type: "Stock", exchange: "NYSE", sector: "Financials", country: "US", price: 248.9, pe: 13.1, divYield: 2.02, vol1y: 22.5, beta: 1.08, mcap: 712 },
  { ticker: "V", name: "Visa Inc.", type: "Stock", exchange: "NYSE", sector: "Financials", country: "US", price: 325.67, pe: 32.8, divYield: 0.72, vol1y: 18.9, beta: 0.94, mcap: 580 },
  { ticker: "LVMH.PA", name: "LVMH Moët Hennessy", type: "Stock", exchange: "Euronext", sector: "Consumer Cyclical", country: "FR", price: 684.2, pe: 22.5, divYield: 1.98, vol1y: 26.7, beta: 0.88, mcap: 342 },
  { ticker: "ASML.AS", name: "ASML Holding NV", type: "Stock", exchange: "Euronext", sector: "Technology", country: "NL", price: 728.5, pe: 42.3, divYield: 0.68, vol1y: 34.1, beta: 1.35, mcap: 295 },
  { ticker: "MC.PA", name: "LVMH (MC)", type: "Stock", exchange: "Euronext", sector: "Luxury", country: "FR", price: 684.2, pe: 22.5, divYield: 1.98, vol1y: 26.7, beta: 0.88, mcap: 342 },
  { ticker: "NESN.SW", name: "Nestlé SA", type: "Stock", exchange: "SIX", sector: "Consumer Defensive", country: "CH", price: 82.14, pe: 19.8, divYield: 3.52, vol1y: 16.2, beta: 0.55, mcap: 228 },
  { ticker: "TSLA", name: "Tesla Inc.", type: "Stock", exchange: "NASDAQ", sector: "Auto", country: "US", price: 178.22, pe: 68.5, divYield: 0.0, vol1y: 58.3, beta: 2.05, mcap: 568 },
  { ticker: "SPY", name: "SPDR S&P 500 ETF", type: "ETF", exchange: "NYSE Arca", sector: "Broad Market", country: "US", price: 532.18, pe: 0, divYield: 1.22, vol1y: 14.8, beta: 1.0, mcap: 540 },
  { ticker: "QQQ", name: "Invesco QQQ Trust", type: "ETF", exchange: "NASDAQ", sector: "Tech-heavy", country: "US", price: 462.3, pe: 0, divYield: 0.55, vol1y: 19.2, beta: 1.12, mcap: 280 },
  { ticker: "IWM", name: "iShares Russell 2000 ETF", type: "ETF", exchange: "NYSE Arca", sector: "Small Cap", country: "US", price: 218.44, pe: 0, divYield: 1.28, vol1y: 21.6, beta: 1.25, mcap: 72 },
  { ticker: "TLT", name: "iShares 20+ Year Treasury Bond ETF", type: "ETF", exchange: "NASDAQ", sector: "Bonds", country: "US", price: 88.92, pe: 0, divYield: 3.85, vol1y: 16.8, beta: -0.15, mcap: 54 },
  { ticker: "GLD", name: "SPDR Gold Shares", type: "ETF", exchange: "NYSE Arca", sector: "Commodities", country: "US", price: 242.1, pe: 0, divYield: 0.0, vol1y: 14.2, beta: 0.05, mcap: 68 },
  { ticker: "EEM", name: "iShares MSCI EM ETF", type: "ETF", exchange: "NYSE Arca", sector: "Emerging Markets", country: "US", price: 44.28, pe: 0, divYield: 2.15, vol1y: 18.5, beta: 0.82, mcap: 22 },
  { ticker: "UST10Y", name: "US Treasury 10-Year Note", type: "Bond", exchange: "OTC", sector: "Sovereign", country: "US", price: 96.42, pe: 0, divYield: 4.25, vol1y: 8.2, beta: 0, mcap: 0 },
  { ticker: "UST2Y", name: "US Treasury 2-Year Note", type: "Bond", exchange: "OTC", sector: "Sovereign", country: "US", price: 99.85, pe: 0, divYield: 4.68, vol1y: 3.1, beta: 0, mcap: 0 },
  { ticker: "BUND10Y", name: "German 10-Year Bund", type: "Bond", exchange: "Eurex", sector: "Sovereign", country: "DE", price: 131.22, pe: 0, divYield: 2.32, vol1y: 6.8, beta: 0, mcap: 0 },
  { ticker: "ES1!", name: "E-mini S&P 500 Future", type: "Future", exchange: "CME", sector: "Index", country: "US", price: 5324.5, pe: 0, divYield: 0, vol1y: 14.8, beta: 1.0, mcap: 0 },
  { ticker: "NQ1!", name: "E-mini NASDAQ 100 Future", type: "Future", exchange: "CME", sector: "Index", country: "US", price: 18620.0, pe: 0, divYield: 0, vol1y: 20.1, beta: 1.12, mcap: 0 },
  { ticker: "CL1!", name: "Crude Oil WTI Future", type: "Future", exchange: "NYMEX", sector: "Energy", country: "US", price: 72.85, pe: 0, divYield: 0, vol1y: 32.4, beta: 0, mcap: 0 },
  { ticker: "GC1!", name: "Gold Future", type: "Future", exchange: "COMEX", sector: "Precious Metals", country: "US", price: 2418.2, pe: 0, divYield: 0, vol1y: 14.5, beta: 0, mcap: 0 },
];

const TYPES = ["All", ...Array.from(new Set(INSTRUMENTS.map((i) => i.type)))];
const EXCHANGES = ["All", ...Array.from(new Set(INSTRUMENTS.map((i) => i.exchange)))];
const PIE_COLORS = ["#D4AF37", "#00D9FF", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"];

const typeBadge = (t: string) => {
  const variants: Record<string, "info" | "up" | "warning" | "neutral"> = {
    Stock: "info", ETF: "up", Bond: "warning", Future: "neutral",
  };
  return <Badge variant={variants[t] || "neutral"}>{t}</Badge>;
};

/* ─── Advanced Screener data ─── */
const ALL_STOCKS = [
  { ticker: "AAPL", name: "Apple Inc.", sector: "Technology", region: "US", mcap: 3200, pe: 28.5, divYield: 0.5 },
  { ticker: "MSFT", name: "Microsoft Corp.", sector: "Technology", region: "US", mcap: 2900, pe: 33.2, divYield: 0.8 },
  { ticker: "GOOGL", name: "Alphabet Inc.", sector: "Technology", region: "US", mcap: 2100, pe: 24.1, divYield: 0.0 },
  { ticker: "AMZN", name: "Amazon.com Inc.", sector: "Consumer Discretionary", region: "US", mcap: 1900, pe: 58.3, divYield: 0.0 },
  { ticker: "NVDA", name: "NVIDIA Corp.", sector: "Technology", region: "US", mcap: 3500, pe: 62.1, divYield: 0.02 },
  { ticker: "JPM", name: "JPMorgan Chase", sector: "Financials", region: "US", mcap: 580, pe: 11.8, divYield: 2.3 },
  { ticker: "V", name: "Visa Inc.", sector: "Financials", region: "US", mcap: 540, pe: 30.5, divYield: 0.7 },
  { ticker: "JNJ", name: "Johnson & Johnson", sector: "Healthcare", region: "US", mcap: 380, pe: 15.2, divYield: 3.0 },
  { ticker: "PG", name: "Procter & Gamble", sector: "Consumer Staples", region: "US", mcap: 360, pe: 24.8, divYield: 2.4 },
  { ticker: "XOM", name: "Exxon Mobil", sector: "Energy", region: "US", mcap: 450, pe: 12.5, divYield: 3.4 },
  { ticker: "NESN", name: "Nestle SA", sector: "Consumer Staples", region: "EU", mcap: 260, pe: 19.2, divYield: 3.1 },
  { ticker: "ASML", name: "ASML Holding", sector: "Technology", region: "EU", mcap: 350, pe: 38.5, divYield: 0.7 },
  { ticker: "NOVO", name: "Novo Nordisk", sector: "Healthcare", region: "EU", mcap: 420, pe: 42.0, divYield: 1.2 },
  { ticker: "SHEL", name: "Shell plc", sector: "Energy", region: "EU", mcap: 210, pe: 8.5, divYield: 3.8 },
  { ticker: "SAP", name: "SAP SE", sector: "Technology", region: "EU", mcap: 280, pe: 35.0, divYield: 1.0 },
  { ticker: "7203", name: "Toyota Motor", sector: "Consumer Discretionary", region: "APAC", mcap: 310, pe: 10.2, divYield: 2.5 },
  { ticker: "9984", name: "SoftBank Group", sector: "Technology", region: "APAC", mcap: 90, pe: 18.5, divYield: 0.5 },
  { ticker: "BHP", name: "BHP Group", sector: "Materials", region: "APAC", mcap: 150, pe: 13.0, divYield: 5.2 },
  { ticker: "TSM", name: "TSMC", sector: "Technology", region: "APAC", mcap: 800, pe: 22.5, divYield: 1.5 },
  { ticker: "RELIANCE", name: "Reliance Industries", sector: "Energy", region: "APAC", mcap: 200, pe: 26.0, divYield: 0.4 },
];

const SECTORS = ["All", ...Array.from(new Set(ALL_STOCKS.map((s) => s.sector)))];
const REGIONS = ["All", "US", "EU", "APAC"];

type SortKey = "ticker" | "mcap" | "pe" | "divYield";

/* ══════════════════════════════════════════════════════════════════ */
export default function UniverseScreener() {
  const [activeTab, setActiveTab] = useState("Universe Search");
  const { data: indicesData } = useIndices();
  const usingFallback = !indicesData;

  // ── Universe Search state ──
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [exchFilter, setExchFilter] = useState("All");
  const [selected, setSelected] = useState<string | null>(null);

  // ── Advanced Screener state ──
  const keyIndices = useMemo(() => {
    if (!indicesData) return [];
    const targets = ["^GSPC", "^IXIC", "^DJI"];
    return Object.values(indicesData).flat().filter((idx) => targets.includes(idx.symbol));
  }, [indicesData]);
  const [mcapMin, setMcapMin] = useState(0);
  const [peMin, setPeMin] = useState(0);
  const [peMax, setPeMax] = useState(100);
  const [divMin, setDivMin] = useState(0);
  const [divMax, setDivMax] = useState(10);
  const [sectorFilter, setSectorFilter] = useState("All");
  const [regionFilter, setRegionFilter] = useState("All");
  const [sortKey, setSortKey] = useState<SortKey>("mcap");
  const [sortAsc, setSortAsc] = useState(false);

  // ── Universe Search derived ──
  const results = useMemo(() => {
    let items = INSTRUMENTS;
    if (typeFilter !== "All") items = items.filter((i) => i.type === typeFilter);
    if (exchFilter !== "All") items = items.filter((i) => i.exchange === exchFilter);
    if (query.trim()) {
      const q = query.toLowerCase();
      items = items.filter(
        (i) => i.ticker.toLowerCase().includes(q) || i.name.toLowerCase().includes(q) || i.sector.toLowerCase().includes(q) || i.country.toLowerCase().includes(q),
      );
    }
    return items;
  }, [query, typeFilter, exchFilter]);

  const selectedInst = selected ? INSTRUMENTS.find((i) => i.ticker === selected) : null;
  const sectors = new Set(INSTRUMENTS.map((i) => i.sector));
  const countries = new Set(INSTRUMENTS.map((i) => i.country));
  const exchanges = new Set(INSTRUMENTS.map((i) => i.exchange));

  const typeBreakdown = useMemo(() => {
    const map: Record<string, number> = {};
    INSTRUMENTS.forEach((i) => { map[i.type] = (map[i.type] || 0) + 1; });
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  }, []);

  const stocks = INSTRUMENTS.filter((i) => i.type === "Stock" && i.mcap > 0);
  const mostValuable = [...stocks].sort((a, b) => b.mcap - a.mcap).slice(0, 3);
  const highestVol = [...stocks].sort((a, b) => b.vol1y - a.vol1y).slice(0, 3);
  const highDiv = [...INSTRUMENTS].filter((i) => i.divYield > 0).sort((a, b) => b.divYield - a.divYield).slice(0, 3);

  // ── Advanced Screener derived ──
  const filtered = useMemo(() => {
    return ALL_STOCKS.filter(
      (s) => s.mcap >= mcapMin && s.pe >= peMin && s.pe <= peMax && s.divYield >= divMin && s.divYield <= divMax,
    )
      .filter((s) => sectorFilter === "All" || s.sector === sectorFilter)
      .filter((s) => regionFilter === "All" || s.region === regionFilter)
      .sort((a, b) => {
        const diff = (a[sortKey] as number) - (b[sortKey] as number);
        return sortAsc ? diff : -diff;
      });
  }, [mcapMin, peMin, peMax, divMin, divMax, sectorFilter, regionFilter, sortKey, sortAsc]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  };
  const sortArrow = (key: SortKey) => sortKey === key ? (sortAsc ? " ▲" : " ▼") : "";

  return (
    <div style={{ color: "#F1F5F9" }}>
      <h1 style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 24, marginBottom: 4 }}>
        <span style={{ color: "#D4AF37" }}>Universe & Screener</span>
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        Explore instrument universe and screen with advanced criteria
      </p>

      {usingFallback && (
        <div style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)", borderRadius: 8, padding: "8px 14px", marginBottom: 16, fontSize: 12, color: "#F59E0B" }}>
          Backend unreachable — showing demo data
        </div>
      )}

      <div style={{ marginBottom: 20 }}>
        <Tabs
          tabs={["Universe Search", "Advanced Screener"]}
          active={activeTab}
          onChange={setActiveTab}
        />
      </div>

      {/* ════ Universe Search ════ */}
      {activeTab === "Universe Search" && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 10, marginBottom: 20 }}>
            {[
              { label: "Total Instruments", value: INSTRUMENTS.length, color: "#D4AF37" },
              { label: "Sectors", value: sectors.size, color: "#00D9FF" },
              { label: "Countries", value: countries.size, color: "#10B981" },
              { label: "Exchanges", value: exchanges.size, color: "#F59E0B" },
            ].map((s) => (
              <Card key={s.label}>
                <div style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}>{s.label}</div>
                <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "JetBrains Mono, monospace", color: s.color }}>{s.value}</div>
              </Card>
            ))}
          </div>

          <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ backgroundColor: "#131823", border: "2px solid rgba(212,175,55,0.3)", borderRadius: 12, padding: "4px 8px", display: "flex", alignItems: "center", gap: 8, flex: "1 1 300px" }}>
              <span style={{ color: "#64748B", fontSize: 14, padding: "0 4px" }}>🔍</span>
              <input
                type="text"
                placeholder="Search by ticker, name, sector, or country…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                autoFocus
                style={{ backgroundColor: "transparent", border: "none", color: "#F1F5F9", fontSize: 14, flex: 1, padding: "10px 4px", outline: "none" }}
              />
              {query && (
                <button onClick={() => setQuery("")} style={{ backgroundColor: "transparent", border: "none", color: "#64748B", cursor: "pointer", fontSize: 16 }}>&#x2715;</button>
              )}
            </div>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} style={{ backgroundColor: "#131823", border: "1px solid rgba(51,65,85,0.5)", borderRadius: 8, padding: "10px 12px", color: "#F1F5F9", fontSize: 13 }}>
              {TYPES.map((t) => <option key={t} value={t}>{t === "All" ? "All Types" : t}</option>)}
            </select>
            <select value={exchFilter} onChange={(e) => setExchFilter(e.target.value)} style={{ backgroundColor: "#131823", border: "1px solid rgba(51,65,85,0.5)", borderRadius: 8, padding: "10px 12px", color: "#F1F5F9", fontSize: 13 }}>
              {EXCHANGES.map((e) => <option key={e} value={e}>{e === "All" ? "All Exchanges" : e}</option>)}
            </select>
          </div>

          <p style={{ color: "#64748B", fontSize: 12, marginBottom: 12 }}>{results.length} instruments found</p>

          <div style={{ display: "grid", gridTemplateColumns: selectedInst ? "1fr 340px" : "1fr", gap: 16 }}>
            <Card>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                      {["Ticker", "Name", "Type", "Exchange", "Sector", "Country", "Price", "Vol 1Y"].map((h) => (
                        <th key={h} style={{ padding: "6px 8px", textAlign: h === "Price" || h === "Vol 1Y" ? "right" : "left", color: "#94A3B8", fontWeight: 500, fontSize: 12 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {results.map((inst) => (
                      <tr key={inst.ticker} onClick={() => setSelected(inst.ticker === selected ? null : inst.ticker)} style={{ borderBottom: "1px solid rgba(51,65,85,0.15)", cursor: "pointer", backgroundColor: inst.ticker === selected ? "rgba(212,175,55,0.06)" : "transparent" }}>
                        <td style={{ padding: "6px 8px", fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color: "#D4AF37" }}>{inst.ticker}</td>
                        <td style={{ padding: "6px 8px", color: "#F1F5F9" }}>{inst.name}</td>
                        <td style={{ padding: "6px 8px" }}>{typeBadge(inst.type)}</td>
                        <td style={{ padding: "6px 8px", color: "#64748B", fontSize: 12 }}>{inst.exchange}</td>
                        <td style={{ padding: "6px 8px", color: "#94A3B8", fontSize: 12 }}>{inst.sector}</td>
                        <td style={{ padding: "6px 8px", color: "#94A3B8", fontSize: 12 }}>{inst.country}</td>
                        <td style={{ padding: "6px 8px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#F1F5F9" }}>{inst.price > 0 ? `$${inst.price.toLocaleString()}` : "—"}</td>
                        <td style={{ padding: "6px 8px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: inst.vol1y > 30 ? "#EF4444" : inst.vol1y > 20 ? "#F59E0B" : "#10B981", fontSize: 12 }}>{inst.vol1y}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {results.length === 0 && <p style={{ color: "#64748B", textAlign: "center", padding: 40 }}>No instruments match your search.</p>}
            </Card>

            {selectedInst && (
              <Card title={`${selectedInst.ticker} Details`}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 16px", fontSize: 13 }}>
                  {[
                    ["Price", selectedInst.price > 0 ? `$${selectedInst.price.toLocaleString()}` : "—"],
                    ["Sector", selectedInst.sector],
                    ["Country", selectedInst.country],
                    ["Exchange", selectedInst.exchange],
                    ["P/E Ratio", selectedInst.pe > 0 ? selectedInst.pe.toFixed(1) : "—"],
                    ["Div Yield", selectedInst.divYield > 0 ? `${selectedInst.divYield.toFixed(2)}%` : "—"],
                    ["Vol 1Y", `${selectedInst.vol1y}%`],
                    ["Beta", selectedInst.beta !== 0 ? selectedInst.beta.toFixed(2) : "—"],
                    ["Mkt Cap", selectedInst.mcap > 0 ? `$${selectedInst.mcap}B` : "—"],
                  ].map(([label, value]) => (
                    <div key={label as string}>
                      <div style={{ color: "#64748B", fontSize: 11 }}>{label}</div>
                      <div style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: 600, color: "#F1F5F9" }}>{value}</div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16, marginTop: 20 }}>
            <Card title="Universe Composition">
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={typeBreakdown} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name, value }: any) => `${name} (${value})`}>
                    {typeBreakdown.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: "#1E293B", border: "1px solid #334155", borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Most Valuable">
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {mostValuable.map((s, i) => (
                  <div key={s.ticker} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 6, borderBottom: i < 2 ? "1px solid rgba(51,65,85,0.2)" : "none" }}>
                    <div>
                      <span style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color: "#D4AF37", marginRight: 8 }}>{s.ticker}</span>
                      <span style={{ color: "#94A3B8", fontSize: 12 }}>{s.name}</span>
                    </div>
                    <span style={{ fontFamily: "JetBrains Mono, monospace", color: "#00D9FF", fontSize: 13 }}>${s.mcap.toLocaleString()}B</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Highest Volatility">
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {highestVol.map((s, i) => (
                  <div key={s.ticker} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 6, borderBottom: i < 2 ? "1px solid rgba(51,65,85,0.2)" : "none" }}>
                    <div>
                      <span style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color: "#D4AF37", marginRight: 8 }}>{s.ticker}</span>
                      <span style={{ color: "#94A3B8", fontSize: 12 }}>{s.name}</span>
                    </div>
                    <span style={{ fontFamily: "JetBrains Mono, monospace", color: "#EF4444", fontSize: 13 }}>{s.vol1y}%</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="High Dividend Yield">
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {highDiv.map((s, i) => (
                  <div key={s.ticker} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 6, borderBottom: i < 2 ? "1px solid rgba(51,65,85,0.2)" : "none" }}>
                    <div>
                      <span style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color: "#D4AF37", marginRight: 8 }}>{s.ticker}</span>
                      <span style={{ color: "#94A3B8", fontSize: 12 }}>{s.name}</span>
                    </div>
                    <span style={{ fontFamily: "JetBrains Mono, monospace", color: "#10B981", fontSize: 13 }}>{s.divYield.toFixed(2)}%</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <p style={{ color: "#64748B", fontSize: 11, marginTop: 16, textAlign: "center" }}>
            Data as of {new Date().toISOString().slice(0, 10)} • {INSTRUMENTS.length} instruments across {exchanges.size} exchanges
          </p>
        </div>
      )}

      {/* ════ Advanced Screener ════ */}
      {activeTab === "Advanced Screener" && (
        <div>
          {keyIndices.length > 0 && (
            <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
              {keyIndices.map((idx) => (
                <div key={idx.symbol} style={{ padding: "6px 14px", borderRadius: 8, backgroundColor: "rgba(212,175,55,0.06)", border: "1px solid rgba(212,175,55,0.15)", fontFamily: "JetBrains Mono, monospace", fontSize: 12 }}>
                  <span style={{ color: "#94A3B8", marginRight: 8 }}>{idx.symbol.replace("^", "")}</span>
                  <span style={{ color: "#F1F5F9", fontWeight: 600 }}>{idx.price.toLocaleString()}</span>
                  <span style={{ color: idx.change.percent >= 0 ? "#10B981" : "#EF4444", marginLeft: 8, fontSize: 11 }}>
                    {idx.change.percent >= 0 ? "+" : ""}{idx.change.percent.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          )}

          <Card className="mb-4">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
              <div>
                <label style={{ fontSize: 12, color: "#94A3B8", display: "block", marginBottom: 4 }}>Min Market Cap ($B)</label>
                <input type="range" min={0} max={1000} step={10} value={mcapMin} onChange={(e) => setMcapMin(+e.target.value)} style={{ width: "100%" }} />
                <span style={{ fontSize: 12, color: "#00D9FF", fontFamily: "JetBrains Mono, monospace" }}>${mcapMin}B+</span>
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#94A3B8", display: "block", marginBottom: 4 }}>P/E Range</label>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input type="number" min={0} max={200} value={peMin} onChange={(e) => setPeMin(+e.target.value)} style={{ width: 60, backgroundColor: "#0A0E1A", border: "1px solid rgba(51,65,85,0.5)", borderRadius: 4, color: "#F1F5F9", padding: "4px 6px", fontSize: 12 }} />
                  <span style={{ color: "#64748B" }}>to</span>
                  <input type="number" min={0} max={200} value={peMax} onChange={(e) => setPeMax(+e.target.value)} style={{ width: 60, backgroundColor: "#0A0E1A", border: "1px solid rgba(51,65,85,0.5)", borderRadius: 4, color: "#F1F5F9", padding: "4px 6px", fontSize: 12 }} />
                </div>
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#94A3B8", display: "block", marginBottom: 4 }}>Dividend Yield (%)</label>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <input type="number" min={0} max={20} step={0.1} value={divMin} onChange={(e) => setDivMin(+e.target.value)} style={{ width: 60, backgroundColor: "#0A0E1A", border: "1px solid rgba(51,65,85,0.5)", borderRadius: 4, color: "#F1F5F9", padding: "4px 6px", fontSize: 12 }} />
                  <span style={{ color: "#64748B" }}>to</span>
                  <input type="number" min={0} max={20} step={0.1} value={divMax} onChange={(e) => setDivMax(+e.target.value)} style={{ width: 60, backgroundColor: "#0A0E1A", border: "1px solid rgba(51,65,85,0.5)", borderRadius: 4, color: "#F1F5F9", padding: "4px 6px", fontSize: 12 }} />
                </div>
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#94A3B8", display: "block", marginBottom: 4 }}>Sector</label>
                <select value={sectorFilter} onChange={(e) => setSectorFilter(e.target.value)} style={{ backgroundColor: "#0A0E1A", border: "1px solid rgba(51,65,85,0.5)", borderRadius: 4, color: "#F1F5F9", padding: "6px 8px", fontSize: 12, width: "100%" }}>
                  {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, color: "#94A3B8", display: "block", marginBottom: 4 }}>Region</label>
                <select value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)} style={{ backgroundColor: "#0A0E1A", border: "1px solid rgba(51,65,85,0.5)", borderRadius: 4, color: "#F1F5F9", padding: "6px 8px", fontSize: 12, width: "100%" }}>
                  {REGIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            </div>
          </Card>

          <p style={{ color: "#64748B", fontSize: 12, marginBottom: 8 }}>{filtered.length} results</p>

          <Card>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    <th onClick={() => handleSort("ticker")} style={{ padding: "8px 12px", textAlign: "left", color: "#94A3B8", fontWeight: 500, cursor: "pointer" }}>Ticker{sortArrow("ticker")}</th>
                    <th style={{ padding: "8px 12px", textAlign: "left", color: "#94A3B8", fontWeight: 500 }}>Name</th>
                    <th style={{ padding: "8px 12px", textAlign: "center", color: "#94A3B8", fontWeight: 500 }}>Sector</th>
                    <th style={{ padding: "8px 12px", textAlign: "center", color: "#94A3B8", fontWeight: 500 }}>Region</th>
                    <th onClick={() => handleSort("mcap")} style={{ padding: "8px 12px", textAlign: "right", color: "#94A3B8", fontWeight: 500, cursor: "pointer" }}>MCap ($B){sortArrow("mcap")}</th>
                    <th onClick={() => handleSort("pe")} style={{ padding: "8px 12px", textAlign: "right", color: "#94A3B8", fontWeight: 500, cursor: "pointer" }}>P/E{sortArrow("pe")}</th>
                    <th onClick={() => handleSort("divYield")} style={{ padding: "8px 12px", textAlign: "right", color: "#94A3B8", fontWeight: 500, cursor: "pointer" }}>Div Yield{sortArrow("divYield")}</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s) => (
                    <tr key={s.ticker} style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}>
                      <td style={{ padding: "8px 12px", fontFamily: "JetBrains Mono, monospace", fontWeight: 700, color: "#D4AF37" }}>{s.ticker}</td>
                      <td style={{ padding: "8px 12px", color: "#F1F5F9" }}>{s.name}</td>
                      <td style={{ padding: "8px 12px", textAlign: "center" }}><Badge variant="info">{s.sector}</Badge></td>
                      <td style={{ padding: "8px 12px", textAlign: "center", color: "#94A3B8" }}>{s.region}</td>
                      <td style={{ padding: "8px 12px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#F1F5F9" }}>{s.mcap.toLocaleString()}</td>
                      <td style={{ padding: "8px 12px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: "#F1F5F9" }}>{s.pe.toFixed(1)}</td>
                      <td style={{ padding: "8px 12px", textAlign: "right", fontFamily: "JetBrains Mono, monospace", color: s.divYield > 2 ? "#10B981" : "#F1F5F9" }}>{s.divYield.toFixed(1)}%</td>
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
