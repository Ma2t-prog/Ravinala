import { useState, useMemo } from 'react';
import { useSnapshot } from '../../hooks/useMarketData';
import { Card } from '../../components/ui';
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';

/* ── colour palette ── */
const GOLD = '#D4AF37', CYAN = '#00D9FF', GREEN = '#10B981', RED = '#EF4444', PURPLE = '#A855F7', AMBER = '#F59E0B';
const ttStyle = { backgroundColor: '#131823', border: '1px solid rgba(51,65,85,0.5)', borderRadius: 8, color: '#F1F5F9' } as const;
const mono = 'JetBrains Mono, monospace';

/* ── tabs ── */
const TABS = ['Social Sentiment', 'Web & Search', 'Satellite & Geo', 'Credit Card & Txn', 'NLP & Filings'] as const;
type Tab = typeof TABS[number];

/* ═══════════════════════════════════════════
   DATA
═══════════════════════════════════════════ */

/* ── Social Sentiment ── */
const sentimentHistory = Array.from({ length: 30 }, (_, i) => ({
  day: `Mar ${i + 1}`,
  fear: Math.round(25 + Math.sin(i * 0.25) * 18 + Math.random() * 6),
  greed: Math.round(55 + Math.cos(i * 0.2) * 15 + Math.random() * 5),
  neutral: Math.round(20 + Math.sin(i * 0.3) * 8),
}));

const mentionsData = [
  { ticker: 'NVDA', reddit: 1842, twitter: 5320, sentiment: 0.72 },
  { ticker: 'TSLA', reddit: 1520, twitter: 4180, sentiment: -0.15 },
  { ticker: 'AAPL', reddit: 980, twitter: 3640, sentiment: 0.45 },
  { ticker: 'GME', reddit: 2100, twitter: 1850, sentiment: 0.88 },
  { ticker: 'PLTR', reddit: 760, twitter: 2210, sentiment: 0.31 },
  { ticker: 'AMD', reddit: 650, twitter: 1920, sentiment: 0.56 },
  { ticker: 'AMZN', reddit: 540, twitter: 2840, sentiment: 0.22 },
  { ticker: 'META', reddit: 420, twitter: 2100, sentiment: 0.38 },
];

const platformBreakdown = [
  { name: 'Reddit', value: 35, color: '#FF4500' },
  { name: 'Twitter/X', value: 30, color: '#1DA1F2' },
  { name: 'StockTwits', value: 15, color: GREEN },
  { name: 'Discord', value: 12, color: PURPLE },
  { name: 'Telegram', value: 8, color: AMBER },
];

/* ── Web & Search ── */
const trendData = Array.from({ length: 30 }, (_, i) => ({
  day: `Mar ${i + 1}`,
  'AI Stocks': Math.round(60 + Math.sin(i * 0.3) * 20 + i * 0.5),
  'Rate Cuts': Math.round(40 + Math.cos(i * 0.2) * 15 + i * 0.3),
  'Recession': Math.round(25 + Math.sin(i * 0.15) * 10),
  'Crypto': Math.round(35 + Math.cos(i * 0.35) * 12 + i * 0.2),
}));

const webTrafficData = [
  { site: 'Amazon', traffic: 92, change: 3.2 },
  { site: 'Shopify stores', traffic: 78, change: -1.5 },
  { site: 'Uber', traffic: 85, change: 5.1 },
  { site: 'Airbnb', traffic: 71, change: 2.8 },
  { site: 'DoorDash', traffic: 66, change: -0.8 },
  { site: 'Netflix', traffic: 88, change: 1.9 },
];

const jobPostings = [
  { company: 'Apple', posts: 4200, delta: 12, sector: 'Tech' },
  { company: 'Google', posts: 3800, delta: -8, sector: 'Tech' },
  { company: 'JPM', posts: 2900, delta: 5, sector: 'Finance' },
  { company: 'Amazon', posts: 5100, delta: 18, sector: 'Tech' },
  { company: 'Tesla', posts: 1800, delta: -15, sector: 'Auto' },
  { company: 'Meta', posts: 2200, delta: 22, sector: 'Tech' },
];

/* ── Satellite & Geo ── */
const parkingLotData = Array.from({ length: 12 }, (_, i) => ({
  month: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][i],
  walmart: 72 + Math.round(Math.sin(i * 0.5) * 12 + Math.random() * 5),
  target: 65 + Math.round(Math.cos(i * 0.4) * 10 + Math.random() * 4),
  costco: 80 + Math.round(Math.sin(i * 0.6) * 8 + Math.random() * 3),
}));

const oilStorageData = Array.from({ length: 20 }, (_, i) => ({
  week: `W${i + 1}`,
  cushing: 25 + Math.round(Math.sin(i * 0.3) * 8 + Math.random() * 3),
  spr: 350 + Math.round(Math.cos(i * 0.15) * 20),
  floating: 80 + Math.round(Math.sin(i * 0.25) * 15 + Math.random() * 5),
}));

const shippingData = [
  { route: 'Trans-Pacific', vessels: 342, change: 5.2, congestion: 'Low' },
  { route: 'Asia-Europe', vessels: 218, change: -3.1, congestion: 'Medium' },
  { route: 'Suez Canal', vessels: 156, change: -18.4, congestion: 'High' },
  { route: 'Panama Canal', vessels: 89, change: -12.7, congestion: 'High' },
  { route: 'US Gulf-Asia', vessels: 134, change: 8.6, congestion: 'Low' },
  { route: 'Intra-Asia', vessels: 428, change: 2.1, congestion: 'Low' },
];

/* ── Credit Card & Txn ── */
const spendingData = Array.from({ length: 12 }, (_, i) => ({
  month: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][i],
  retail: 100 + Math.round(Math.sin(i * 0.5) * 15 + i * 1.2),
  travel: 80 + Math.round(Math.cos(i * 0.4) * 20 + i * 0.8),
  dining: 60 + Math.round(Math.sin(i * 0.6) * 10 + i * 0.5),
  ecommerce: 110 + Math.round(Math.cos(i * 0.3) * 12 + i * 1.5),
}));

const sectorSpend = [
  { name: 'Discretionary', value: 28, color: CYAN },
  { name: 'Staples', value: 22, color: GREEN },
  { name: 'Travel', value: 18, color: GOLD },
  { name: 'Healthcare', value: 12, color: PURPLE },
  { name: 'Tech/SaaS', value: 14, color: AMBER },
  { name: 'Other', value: 6, color: '#64748B' },
];

const receiptInsights = [
  { merchant: 'Walmart', avgTicket: 67.4, yoy: 3.2, visits: '12.4M' },
  { merchant: 'Amazon', avgTicket: 52.1, yoy: 8.7, visits: '28.1M' },
  { merchant: 'Costco', avgTicket: 142.8, yoy: 5.1, visits: '6.8M' },
  { merchant: 'Target', avgTicket: 54.3, yoy: -1.2, visits: '8.2M' },
  { merchant: 'Home Depot', avgTicket: 89.6, yoy: -4.5, visits: '5.1M' },
  { merchant: 'Starbucks', avgTicket: 7.2, yoy: 6.3, visits: '42.0M' },
];

/* ── NLP & Filings ── */
const filingsSentiment = Array.from({ length: 8 }, (_, i) => {
  const qs = ['Q1 22','Q2 22','Q3 22','Q4 22','Q1 23','Q2 23','Q3 23','Q4 23'];
  return {
    quarter: qs[i],
    positive: 35 + Math.round(Math.sin(i * 0.8) * 10 + Math.random() * 5),
    negative: 20 + Math.round(Math.cos(i * 0.6) * 8 + Math.random() * 4),
    uncertainty: 15 + Math.round(Math.sin(i * 0.5) * 6 + Math.random() * 3),
  };
});

const earningsCallKeywords = [
  { word: 'AI/Machine Learning', freq: 342, delta: 85, sentiment: 0.78 },
  { word: 'Cost Reduction', freq: 289, delta: 12, sentiment: 0.42 },
  { word: 'Macro Headwinds', freq: 198, delta: -5, sentiment: -0.35 },
  { word: 'Supply Chain', freq: 156, delta: -28, sentiment: -0.12 },
  { word: 'Guidance Raised', freq: 134, delta: 18, sentiment: 0.91 },
  { word: 'Restructuring', freq: 112, delta: 32, sentiment: -0.55 },
  { word: 'Share Buyback', freq: 98, delta: 8, sentiment: 0.65 },
  { word: 'Regulatory Risk', freq: 87, delta: 14, sentiment: -0.48 },
];

const topicRadar = [
  { topic: 'Growth', sp500: 72, nasdaq: 85, russell: 58 },
  { topic: 'Margins', sp500: 65, nasdaq: 70, russell: 52 },
  { topic: 'Capex', sp500: 58, nasdaq: 82, russell: 45 },
  { topic: 'Leverage', sp500: 40, nasdaq: 35, russell: 55 },
  { topic: 'Innovation', sp500: 55, nasdaq: 90, russell: 42 },
  { topic: 'Risk', sp500: 48, nasdaq: 42, russell: 62 },
];

/* ═══════════════════════════════════════════
   GAUGE COMPONENT
═══════════════════════════════════════════ */
function SentimentGauge({ score }: { score: number }) {
  const label = score < 25 ? 'Extreme Fear' : score < 40 ? 'Fear' : score < 60 ? 'Neutral' : score < 75 ? 'Greed' : 'Extreme Greed';
  const color = score < 25 ? RED : score < 40 ? '#F97316' : score < 60 ? '#94A3B8' : score < 75 ? GREEN : '#22C55E';
  const pct = score / 100;
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ position: 'relative', width: 180, height: 100, margin: '0 auto' }}>
        <svg viewBox="0 0 200 110" width="180" height="100">
          <path d="M10,100 A90,90 0 0,1 190,100" fill="none" stroke="rgba(51,65,85,0.4)" strokeWidth="14" strokeLinecap="round" />
          <path d="M10,100 A90,90 0 0,1 190,100" fill="none" stroke={color} strokeWidth="14" strokeLinecap="round"
            strokeDasharray={`${pct * 283} 283`} />
        </svg>
        <div style={{ position: 'absolute', bottom: 2, left: '50%', transform: 'translateX(-50%)' }}>
          <div style={{ fontSize: 26, fontWeight: 700, color, fontFamily: mono }}>{score}</div>
        </div>
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color, marginTop: 2 }}>{label}</div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   MAIN COMPONENT
═══════════════════════════════════════════ */
export default function AltData() {
  const { data: snapshotData } = useSnapshot();
  const [tab, setTab] = useState<Tab>('Social Sentiment');
  const [sortCol, setSortCol] = useState<string>('');
  const [sortAsc, setSortAsc] = useState(true);

  const toggleSort = (col: string) => { setSortAsc(sortCol === col ? !sortAsc : true); setSortCol(col); };

  /* ── sorted helpers ── */
  const sortedMentions = useMemo(() => {
    if (!sortCol) return mentionsData;
    return [...mentionsData].sort((a, b) => {
      const va = (a as Record<string, unknown>)[sortCol], vb = (b as Record<string, unknown>)[sortCol];
      const cmp = typeof va === 'number' && typeof vb === 'number' ? va - vb : String(va).localeCompare(String(vb));
      return sortAsc ? cmp : -cmp;
    });
  }, [sortCol, sortAsc]);

  const th = (label: string, col: string) => (
    <th onClick={() => toggleSort(col)} style={{ cursor: 'pointer', padding: '6px 10px', textAlign: 'left', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>
      {label} {sortCol === col ? (sortAsc ? '▲' : '▼') : ''}
    </th>
  );

  const kpi = (label: string, value: string, sub: string, color: string) => (
    <div style={{ backgroundColor: 'rgba(10,14,26,0.5)', borderRadius: 10, padding: 14, border: '1px solid rgba(51,65,85,0.2)' }}>
      <div style={{ fontSize: 11, color: '#64748B', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color, fontFamily: mono }}>{value}</div>
      <div style={{ fontSize: 11, color: '#64748B', marginTop: 2 }}>{sub}</div>
    </div>
  );

  return (
    <div style={{ color: '#F1F5F9' }}>
      {!snapshotData && (
        <div style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, padding: '8px 16px', marginBottom: 16, fontSize: 13, color: '#F59E0B', fontFamily: 'Inter, sans-serif' }}>
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      <h1 style={{ fontFamily: mono, fontSize: 24, marginBottom: 4 }}>Alternative Data</h1>
      <p style={{ color: '#94A3B8', marginBottom: 16, fontSize: 14 }}>
        Non-traditional data sources for alpha generation
        {snapshotData?.timestamp && (
          <span style={{ marginLeft: 12, fontSize: 12, color: '#64748B' }}>Market snapshot: {new Date(snapshotData.timestamp).toLocaleTimeString()}</span>
        )}
      </p>

      {/* tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 18, flexWrap: 'wrap' }}>
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ padding: '7px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer', border: 'none',
              backgroundColor: tab === t ? GOLD : 'rgba(30,41,59,0.5)', color: tab === t ? '#0A0E1A' : '#94A3B8', transition: 'all .2s' }}>
            {t}
          </button>
        ))}
      </div>

      {/* ═══════════ Social Sentiment ═══════════ */}
      {tab === 'Social Sentiment' && <>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }}>
          {kpi('Composite Score', '68', 'Greed', GREEN)}
          {kpi('Reddit Activity', '+24%', 'vs 7d avg', CYAN)}
          {kpi('Twitter Volume', '142K', 'fin tweets/hr', '#1DA1F2')}
          {kpi('Put/Call Ratio', '0.82', 'mildly bullish', AMBER)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <Card title="Sentiment Index History" subtitle="Fear & greed decomposition (30d)">
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <AreaChart data={sentimentHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                  <XAxis dataKey="day" tick={{ fill: '#64748B', fontSize: 10 }} interval={4} />
                  <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                  <Tooltip contentStyle={ttStyle} />
                  <Area type="monotone" dataKey="greed" stackId="1" stroke={GREEN} fill={GREEN} fillOpacity={0.3} />
                  <Area type="monotone" dataKey="neutral" stackId="1" stroke="#94A3B8" fill="#94A3B8" fillOpacity={0.15} />
                  <Area type="monotone" dataKey="fear" stackId="1" stroke={RED} fill={RED} fillOpacity={0.25} />
                  <Legend />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title="Aggregate Gauge" subtitle="Current market sentiment reading">
            <SentimentGauge score={68} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 12 }}>
              {platformBreakdown.map(p => (
                <div key={p.name} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 8px', fontSize: 12 }}>
                  <span style={{ color: p.color }}>{p.name}</span>
                  <span style={{ fontFamily: mono, color: '#F1F5F9' }}>{p.value}%</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
        <Card title="Ticker Mentions & Sentiment" subtitle="Reddit + Twitter/X last 24 hours">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr>{th('Ticker','ticker')}{th('Reddit','reddit')}{th('Twitter','twitter')}{th('Sentiment','sentiment')}{th('Total','total')}</tr></thead>
              <tbody>
                {sortedMentions.map(m => (
                  <tr key={m.ticker} style={{ borderBottom: '1px solid rgba(51,65,85,0.15)' }}>
                    <td style={{ padding: '6px 10px', fontWeight: 700, fontFamily: mono, color: GOLD }}>{m.ticker}</td>
                    <td style={{ padding: '6px 10px', fontFamily: mono, color: '#FF4500' }}>{m.reddit.toLocaleString()}</td>
                    <td style={{ padding: '6px 10px', fontFamily: mono, color: '#1DA1F2' }}>{m.twitter.toLocaleString()}</td>
                    <td style={{ padding: '6px 10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ width: 50, height: 6, borderRadius: 3, backgroundColor: 'rgba(51,65,85,0.3)', overflow: 'hidden' }}>
                          <div style={{ width: `${Math.abs(m.sentiment) * 100}%`, height: '100%', borderRadius: 3, backgroundColor: m.sentiment >= 0 ? GREEN : RED }} />
                        </div>
                        <span style={{ fontFamily: mono, fontSize: 12, color: m.sentiment >= 0 ? GREEN : RED }}>{m.sentiment > 0 ? '+' : ''}{m.sentiment.toFixed(2)}</span>
                      </div>
                    </td>
                    <td style={{ padding: '6px 10px', fontFamily: mono, fontSize: 12 }}>{(m.reddit + m.twitter).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </>}

      {/* ═══════════ Web & Search ═══════════ */}
      {tab === 'Web & Search' && <>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }}>
          {kpi('Top Trend', 'AI Stocks', 'Google Trends #1', CYAN)}
          {kpi('Web Traffic Idx', '87.3', '+2.1% WoW', GREEN)}
          {kpi('Job Postings', '18.1K', 'Tech sector', PURPLE)}
          {kpi('App Downloads', '+14%', 'Finance apps', GOLD)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <Card title="Google Trends" subtitle="Search interest indices (30d)">
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                  <XAxis dataKey="day" tick={{ fill: '#64748B', fontSize: 10 }} interval={4} />
                  <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                  <Tooltip contentStyle={ttStyle} />
                  <Line type="monotone" dataKey="AI Stocks" stroke={CYAN} strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="Rate Cuts" stroke={GOLD} strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="Recession" stroke={RED} strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="Crypto" stroke={PURPLE} strokeWidth={2} dot={false} />
                  <Legend />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title="Company Web Traffic" subtitle="Relative traffic index & weekly change">
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={webTrafficData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                  <XAxis dataKey="site" tick={{ fill: '#64748B', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                  <Tooltip contentStyle={ttStyle} />
                  <Bar dataKey="traffic" fill={CYAN} radius={[4, 4, 0, 0]} name="Traffic Index" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
        <Card title="Job Postings Tracker" subtitle="Company hiring activity as leading indicator">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Company</th>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Sector</th>
                <th style={{ padding: '6px 10px', textAlign: 'right', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Open Positions</th>
                <th style={{ padding: '6px 10px', textAlign: 'right', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>30d Change %</th>
              </tr></thead>
              <tbody>
                {jobPostings.map(j => (
                  <tr key={j.company} style={{ borderBottom: '1px solid rgba(51,65,85,0.15)' }}>
                    <td style={{ padding: '6px 10px', fontWeight: 600, color: '#F1F5F9' }}>{j.company}</td>
                    <td style={{ padding: '6px 10px', fontSize: 12, color: '#94A3B8' }}>{j.sector}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: mono, fontSize: 13 }}>{j.posts.toLocaleString()}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: mono, fontSize: 13, color: j.delta >= 0 ? GREEN : RED }}>{j.delta > 0 ? '+' : ''}{j.delta}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </>}

      {/* ═══════════ Satellite & Geo ═══════════ */}
      {tab === 'Satellite & Geo' && <>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }}>
          {kpi('Cushing Storage', '28.4 Mb', '-2.1 Mb WoW', AMBER)}
          {kpi('Parking Occupancy', '76%', 'Walmart avg', GREEN)}
          {kpi('Global Shipping', '1,367', 'vessels tracked', CYAN)}
          {kpi('Crop Health Index', '82.1', 'Midwest corn', GREEN)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <Card title="Retail Parking Lot Occupancy" subtitle="Satellite-derived foot traffic proxy (monthly %)">
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <LineChart data={parkingLotData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                  <XAxis dataKey="month" tick={{ fill: '#64748B', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#64748B', fontSize: 10 }} domain={[50, 100]} />
                  <Tooltip contentStyle={ttStyle} />
                  <Line type="monotone" dataKey="walmart" stroke={CYAN} strokeWidth={2} name="Walmart" />
                  <Line type="monotone" dataKey="target" stroke={RED} strokeWidth={2} name="Target" />
                  <Line type="monotone" dataKey="costco" stroke={GOLD} strokeWidth={2} name="Costco" />
                  <Legend />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title="Oil Storage Levels" subtitle="Cushing + SPR + floating storage (Mb)">
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <AreaChart data={oilStorageData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                  <XAxis dataKey="week" tick={{ fill: '#64748B', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                  <Tooltip contentStyle={ttStyle} />
                  <Area type="monotone" dataKey="cushing" stackId="1" stroke={AMBER} fill={AMBER} fillOpacity={0.3} name="Cushing" />
                  <Area type="monotone" dataKey="floating" stackId="1" stroke={CYAN} fill={CYAN} fillOpacity={0.2} name="Floating" />
                  <Legend />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
        <Card title="Shipping Route Monitor" subtitle="AIS vessel tracking data">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Route</th>
                <th style={{ padding: '6px 10px', textAlign: 'right', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Vessels</th>
                <th style={{ padding: '6px 10px', textAlign: 'right', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>7d Change %</th>
                <th style={{ padding: '6px 10px', textAlign: 'center', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Congestion</th>
              </tr></thead>
              <tbody>
                {shippingData.map(s => (
                  <tr key={s.route} style={{ borderBottom: '1px solid rgba(51,65,85,0.15)' }}>
                    <td style={{ padding: '6px 10px', fontWeight: 600, color: '#F1F5F9' }}>{s.route}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: mono }}>{s.vessels}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: mono, color: s.change >= 0 ? GREEN : RED }}>{s.change > 0 ? '+' : ''}{s.change}%</td>
                    <td style={{ padding: '6px 10px', textAlign: 'center' }}>
                      <span style={{ padding: '2px 10px', borderRadius: 12, fontSize: 11, fontWeight: 600,
                        backgroundColor: s.congestion === 'Low' ? 'rgba(16,185,129,0.15)' : s.congestion === 'Medium' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                        color: s.congestion === 'Low' ? GREEN : s.congestion === 'Medium' ? AMBER : RED }}>{s.congestion}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </>}

      {/* ═══════════ Credit Card & Txn ═══════════ */}
      {tab === 'Credit Card & Txn' && <>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }}>
          {kpi('Spending Index', '112.4', '+3.8% MoM', GREEN)}
          {kpi('Avg Ticket Size', '$72.30', '+1.2% YoY', CYAN)}
          {kpi('Top Sector', 'E-Commerce', '+14% growth', PURPLE)}
          {kpi('Consumer Conf.', '102.8', 'vs 99.1 prior', GOLD)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <Card title="Consumer Spending Trends" subtitle="Indexed spending by category (monthly)">
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <LineChart data={spendingData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                  <XAxis dataKey="month" tick={{ fill: '#64748B', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                  <Tooltip contentStyle={ttStyle} />
                  <Line type="monotone" dataKey="retail" stroke={CYAN} strokeWidth={2} name="Retail" />
                  <Line type="monotone" dataKey="travel" stroke={GOLD} strokeWidth={2} name="Travel" />
                  <Line type="monotone" dataKey="dining" stroke={PURPLE} strokeWidth={2} name="Dining" />
                  <Line type="monotone" dataKey="ecommerce" stroke={GREEN} strokeWidth={2} name="E-Commerce" />
                  <Legend />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title="Sector Allocation" subtitle="Consumer spend by sector">
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={sectorSpend} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="value"
                    label={({ name, value }) => `${name} ${value}%`}>
                    {sectorSpend.map(s => <Cell key={s.name} fill={s.color} />)}
                  </Pie>
                  <Tooltip contentStyle={ttStyle} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
        <Card title="Receipt-Level Insights" subtitle="Aggregated transaction data (anonymised)">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Merchant</th>
                <th style={{ padding: '6px 10px', textAlign: 'right', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Avg Ticket</th>
                <th style={{ padding: '6px 10px', textAlign: 'right', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>YoY %</th>
                <th style={{ padding: '6px 10px', textAlign: 'right', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Monthly Visits</th>
              </tr></thead>
              <tbody>
                {receiptInsights.map(r => (
                  <tr key={r.merchant} style={{ borderBottom: '1px solid rgba(51,65,85,0.15)' }}>
                    <td style={{ padding: '6px 10px', fontWeight: 600, color: '#F1F5F9' }}>{r.merchant}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: mono }}>${r.avgTicket.toFixed(2)}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: mono, color: r.yoy >= 0 ? GREEN : RED }}>{r.yoy > 0 ? '+' : ''}{r.yoy}%</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: mono, color: '#94A3B8' }}>{r.visits}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </>}

      {/* ═══════════ NLP & Filings ═══════════ */}
      {tab === 'NLP & Filings' && <>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }}>
          {kpi('10-K/Q Processed', '2,847', 'last 90 days', CYAN)}
          {kpi('Earnings Calls', '486', 'transcripts parsed', PURPLE)}
          {kpi('Top Keyword', 'AI/ML', '+85% frequency', GOLD)}
          {kpi('Avg Tone', '+0.12', 'slightly positive', GREEN)}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
          <Card title="Filings Sentiment Over Time" subtitle="10-K/Q tone analysis by quarter">
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={filingsSentiment}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                  <XAxis dataKey="quarter" tick={{ fill: '#64748B', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                  <Tooltip contentStyle={ttStyle} />
                  <Bar dataKey="positive" fill={GREEN} name="Positive" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="negative" fill={RED} name="Negative" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="uncertainty" fill={AMBER} name="Uncertainty" radius={[4, 4, 0, 0]} />
                  <Legend />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title="Topic Emphasis Radar" subtitle="Earnings call topic prevalence by index">
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <RadarChart data={topicRadar}>
                  <PolarGrid stroke="rgba(51,65,85,0.3)" />
                  <PolarAngleAxis dataKey="topic" tick={{ fill: '#94A3B8', fontSize: 11 }} />
                  <PolarRadiusAxis tick={{ fill: '#64748B', fontSize: 9 }} />
                  <Radar name="S&P 500" dataKey="sp500" stroke={CYAN} fill={CYAN} fillOpacity={0.15} />
                  <Radar name="NASDAQ" dataKey="nasdaq" stroke={GOLD} fill={GOLD} fillOpacity={0.15} />
                  <Radar name="Russell 2000" dataKey="russell" stroke={PURPLE} fill={PURPLE} fillOpacity={0.15} />
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>
        <Card title="Earnings Call Keywords" subtitle="NLP-extracted keyword frequency & sentiment">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr>
                <th style={{ padding: '6px 10px', textAlign: 'left', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Keyword</th>
                <th style={{ padding: '6px 10px', textAlign: 'right', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Frequency</th>
                <th style={{ padding: '6px 10px', textAlign: 'right', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>QoQ Change</th>
                <th style={{ padding: '6px 10px', textAlign: 'right', fontSize: 11, color: '#94A3B8', borderBottom: '1px solid rgba(51,65,85,0.3)' }}>Sentiment</th>
              </tr></thead>
              <tbody>
                {earningsCallKeywords.map(k => (
                  <tr key={k.word} style={{ borderBottom: '1px solid rgba(51,65,85,0.15)' }}>
                    <td style={{ padding: '6px 10px', fontWeight: 600, color: '#F1F5F9' }}>{k.word}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: mono }}>{k.freq}</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: mono, color: k.delta >= 0 ? GREEN : RED }}>{k.delta > 0 ? '+' : ''}{k.delta}%</td>
                    <td style={{ padding: '6px 10px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 6 }}>
                        <div style={{ width: 50, height: 6, borderRadius: 3, backgroundColor: 'rgba(51,65,85,0.3)', overflow: 'hidden' }}>
                          <div style={{ width: `${Math.abs(k.sentiment) * 100}%`, height: '100%', borderRadius: 3, backgroundColor: k.sentiment >= 0 ? GREEN : RED }} />
                        </div>
                        <span style={{ fontFamily: mono, fontSize: 12, color: k.sentiment >= 0 ? GREEN : RED }}>{k.sentiment > 0 ? '+' : ''}{k.sentiment.toFixed(2)}</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </>}
    </div>
  );
}