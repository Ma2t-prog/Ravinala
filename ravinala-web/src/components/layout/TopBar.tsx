import { useEffect, useState, useRef } from 'react'
import { useLocation } from 'react-router-dom'

/* ─── Constants ─── */
export const TOPBAR_HEIGHT = 56
export const MARKET_STRIP_HEIGHT = 54

/* ─── Route Labels ─── */
const routeLabels: Record<string, { title: string; subtitle: string }> = {
  '/':                          { title: 'Home',                subtitle: 'Dashboard Overview' },
  '/market/live':               { title: 'Live Market',         subtitle: 'Real-time Market Data' },
  '/market/news':               { title: 'Market News',         subtitle: 'Breaking News & Analysis' },
  '/market/macro':              { title: 'Macro Analysis',      subtitle: 'Macroeconomic Indicators' },
  '/market/alt-data':           { title: 'Alt Data',            subtitle: 'Alternative Data Sources' },
  '/market/intelligence':       { title: 'Intelligence',        subtitle: 'Market Intelligence Feed' },
  '/market/financial-analysis': { title: 'Financial Analysis',  subtitle: 'Financial Statement Analysis' },
  '/derivatives/pricing':       { title: 'Pricing Center',      subtitle: 'Derivatives Pricing Engine' },
  '/derivatives/structuring':   { title: 'Structuring Suite',   subtitle: 'Structured Products Builder' },
  '/derivatives/custom':        { title: 'Custom Product',      subtitle: 'Custom Payoff Designer' },
  '/derivatives/exotics':       { title: 'Advanced Exotics',    subtitle: 'Exotic Options Pricing' },
  '/derivatives/museum':        { title: 'Museum of Exotics',   subtitle: 'Historical Exotic Structures' },
  '/derivatives/sandbox':       { title: 'The Sandbox',         subtitle: 'Experimental Playground' },
  '/research/valuations':       { title: 'Enterprise Valuations', subtitle: 'DCF & Multiples Analysis' },
  '/research/equity':           { title: 'Equity Research',     subtitle: 'Equity Analysis Platform' },
  '/research/fixed-income':     { title: 'Fixed Income',        subtitle: 'Bond & Rate Analysis' },
  '/research/assets':           { title: 'Asset Explorer',      subtitle: 'Cross-Asset Browser' },
  '/research/company':          { title: 'Company Analyzer',    subtitle: 'Fundamental Analysis' },
  '/research/etf':              { title: 'ETF Explorer',        subtitle: 'ETF Screening & Analytics' },
  '/risk/management':           { title: 'Risk Management',     subtitle: 'Enterprise Risk Dashboard' },
  '/risk/greeks':               { title: 'Greeks & Sensitivity', subtitle: 'Greeks Analysis Engine' },
  '/risk/vol-calibration':      { title: 'Vol Calibration',     subtitle: 'Volatility Surface Calibration' },
  '/risk/backtesting':          { title: 'Backtesting',         subtitle: 'Strategy Backtesting Engine' },
  '/risk/ml-pricing':           { title: 'ML Pricing',          subtitle: 'Machine Learning Models' },
  '/risk/hedging':              { title: 'Hedging',             subtitle: 'Hedge Strategy Optimizer' },
  '/portfolio/optimizer':       { title: 'Portfolio Optimizer',  subtitle: 'Mean-Variance Optimization' },
  '/portfolio/strategy':        { title: 'Strategy Lab',        subtitle: 'Strategy Research Lab' },
  '/portfolio/scenarios':       { title: 'Scenario Matrix',     subtitle: 'Multi-Scenario Analysis' },
  '/portfolio/pnl':             { title: 'P&L Attribution',     subtitle: 'Performance Attribution' },
  '/portfolio/positions':       { title: 'Position Book',       subtitle: 'Position Management' },
  '/tax':                       { title: 'TAX LAB \u03A9',      subtitle: 'Full Tax Analysis Suite' },
  '/genesix/universe':          { title: 'Universe Search',     subtitle: 'Instrument Universe' },
  '/genesix/screener':          { title: 'Advanced Screener',   subtitle: 'Multi-Factor Screening' },
  '/genesix/instrument':        { title: 'Instrument Analysis', subtitle: 'Deep Instrument Analysis' },
  '/genesix/portfolio':         { title: '\u03A9 Portfolio Omega', subtitle: 'Portfolio Construction' },
  '/genesix/risk':              { title: 'Risk Engine',         subtitle: 'Quantitative Risk Engine' },
  '/genesix/backtest':          { title: 'Backtesting',         subtitle: 'Historical Backtesting' },
  '/genesix/ml':                { title: 'ML Engine',           subtitle: 'Machine Learning Pipeline' },
  '/genesix/analysis':          { title: 'Advanced Analysis',   subtitle: 'Quantitative Analytics' },
  '/genesix/intelligence':      { title: 'Market Intelligence', subtitle: 'Sentiment & Flow Analysis' },
  '/genesix/monitor':           { title: 'Portfolio Monitor',   subtitle: 'Real-time Monitoring' },
  '/genesix/signals':           { title: 'Signal Intelligence', subtitle: 'Trading Signal Engine' },
  '/genesix/data':              { title: 'Data Layer',          subtitle: 'Data Management' },
  '/genesix/physics':           { title: 'Physics Lab',         subtitle: 'Quantitative Physics Models' },
  '/compliance/esg':            { title: 'ESG & Green Lab',     subtitle: 'ESG Scoring & Analysis' },
  '/compliance/regulatory':     { title: 'Regulatory Capital',  subtitle: 'Capital Requirements' },
  '/compliance/reports':        { title: 'Report Generator',    subtitle: 'Automated Reporting' },
  '/compliance/legal':          { title: 'Legal & Compliance',  subtitle: 'Compliance Framework' },
  '/learning/academy':          { title: 'Quantum Academy',     subtitle: 'Educational Platform' },
  '/learning/probability':      { title: 'Probability Bible',   subtitle: 'Probability & Statistics' },
  '/learning/hub':              { title: 'Learning Hub',        subtitle: 'Knowledge Center' },
  '/trading/tradebook':         { title: 'Trade Book',          subtitle: 'Order Management System' },
  '/trading/admin':             { title: 'Admin Panel',         subtitle: 'System Administration' },
}

/* ─── Date / Time Helpers ─── */
const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function formatDate(d: Date): string {
  return `${DAY_NAMES[d.getDay()]}, ${d.getDate()} ${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`
}

function formatTime(d: Date): string {
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  const s = String(d.getSeconds()).padStart(2, '0')
  return `${h}:${m}:${s}`
}

/* ─── Market Status Logic ─── */
function isWeekday(d: Date): boolean {
  const day = d.getDay()
  return day >= 1 && day <= 5
}

function getMarketStatus(now: Date): { us: boolean; eu: boolean; asia: boolean } {
  // US Markets — NYSE: 9:30-16:00 ET
  const et = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }))
  const etMinutes = et.getHours() * 60 + et.getMinutes()
  const usOpen = isWeekday(et) && etMinutes >= 570 && etMinutes < 960

  // EU Markets — LSE: 8:00-16:30 GMT
  const gmt = new Date(now.toLocaleString('en-US', { timeZone: 'Europe/London' }))
  const gmtMinutes = gmt.getHours() * 60 + gmt.getMinutes()
  const euOpen = isWeekday(gmt) && gmtMinutes >= 480 && gmtMinutes < 990

  // Asia Markets — TSE: 9:00-15:00 JST
  const jst = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Tokyo' }))
  const jstMinutes = jst.getHours() * 60 + jst.getMinutes()
  const asiaOpen = isWeekday(jst) && jstMinutes >= 540 && jstMinutes < 900

  return { us: usOpen, eu: euOpen, asia: asiaOpen }
}

/* ─── Market Data ─── */
interface MarketIndex {
  venue: string
  name: string
  level: string
  change: string
  region: 'us' | 'eu' | 'asia'
  tz: string
}

const MARKET_INDICES: MarketIndex[] = [
  { venue: 'NYSE',     name: 'S&P 500',    level: '5,234.18',  change: '+0.47%', region: 'us',   tz: 'America/New_York' },
  { venue: 'NYSE',     name: 'DOW 30',     level: '39,127.14', change: '+0.32%', region: 'us',   tz: 'America/New_York' },
  { venue: 'NASDAQ',   name: 'NASDAQ',     level: '16,277.46', change: '+0.65%', region: 'us',   tz: 'America/New_York' },
  { venue: 'XETRA',    name: 'DAX 40',     level: '18,430.05', change: '+0.28%', region: 'eu',   tz: 'Europe/Berlin' },
  { venue: 'EURONEXT', name: 'CAC 40',     level: '8,061.31',  change: '-0.14%', region: 'eu',   tz: 'Europe/Paris' },
  { venue: 'LSE',      name: 'FTSE 100',   level: '7,930.96',  change: '+0.18%', region: 'eu',   tz: 'Europe/London' },
  { venue: 'TSE',      name: 'NIKKEI 225', level: '38,460.08', change: '+1.12%', region: 'asia', tz: 'Asia/Tokyo' },
  { venue: 'HKEX',     name: 'HANG SENG',  level: '17,651.15', change: '-0.53%', region: 'asia', tz: 'Asia/Hong_Kong' },
]

interface Ticker {
  symbol: string
  price: string
  change: string
}

const TOP_TICKERS: Ticker[] = [
  { symbol: 'AAPL',  price: '$198.50', change: '+1.24%' },
  { symbol: 'MSFT',  price: '$425.20', change: '+0.87%' },
  { symbol: 'NVDA',  price: '$875.30', change: '+2.15%' },
  { symbol: 'GOOGL', price: '$178.40', change: '+0.62%' },
  { symbol: 'AMZN',  price: '$185.60', change: '+1.43%' },
  { symbol: 'META',  price: '$502.80', change: '+0.95%' },
  { symbol: 'TSLA',  price: '$248.42', change: '-1.87%' },
  { symbol: 'BRK.B', price: '$412.55', change: '+0.34%' },
]

function fmtTZ(now: Date, tz: string): string {
  return now.toLocaleTimeString('en-GB', { timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false })
}

function isPositive(change: string): boolean {
  return change.startsWith('+')
}

/* ─── MarketCard Component ─── */
function MarketCard({ idx, now, marketStatus }: { idx: MarketIndex; now: Date; marketStatus: { us: boolean; eu: boolean; asia: boolean } }) {
  const [hovered, setHovered] = useState(false)
  const open = marketStatus[idx.region]
  const positive = isPositive(idx.change)

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        flex: '0 0 auto',
        minWidth: 196,
        background: 'linear-gradient(135deg, rgba(19,24,35,0.6), rgba(15,18,24,0.6))',
        border: `1px solid ${hovered ? 'rgba(0,217,255,0.2)' : 'rgba(51,65,85,0.3)'}`,
        borderRadius: 10,
        padding: '6px 10px',
        transition: 'all 200ms ease',
        transform: hovered ? 'translateY(-1px)' : 'none',
        cursor: 'default',
      }}
    >
      {/* Top row: venue + local time */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 10, color: '#00D9FF', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' as const }}>
          {idx.venue}
        </span>
        <span style={{ fontSize: 10, color: '#94A3B8', fontFamily: 'JetBrains Mono, monospace' }}>
          {fmtTZ(now, idx.tz)}
        </span>
      </div>

      {/* Index name */}
      <div style={{ fontSize: 10, color: '#94A3B8', letterSpacing: '0.03em', textTransform: 'uppercase' as const }}>
        {idx.name}
      </div>

      {/* Level */}
      <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: '#F1F5F9', fontVariantNumeric: 'tabular-nums', marginTop: 2 }}>
        {idx.level}
      </div>

      {/* Bottom row: status + change */}
      <div style={{ display: 'flex', alignItems: 'center', marginTop: 2 }}>
        <span
          className="rvn-live-dot"
          style={{
            display: 'inline-block',
            width: 7,
            height: 7,
            borderRadius: '50%',
            backgroundColor: open ? '#10B981' : '#EF4444',
            boxShadow: open ? '0 0 6px rgba(16,185,129,0.6)' : 'none',
            marginRight: 5,
          }}
        />
        <span style={{ fontSize: 10, color: '#CBD5E1', textTransform: 'uppercase' as const }}>
          {open ? 'OPEN' : 'CLOSED'}
        </span>
        <span
          style={{
            marginLeft: 'auto',
            fontSize: 10,
            fontWeight: 700,
            fontFamily: 'JetBrains Mono, monospace',
            color: positive ? '#10B981' : '#EF4444',
          }}
        >
          {idx.change}
        </span>
      </div>
    </div>
  )
}

/* ─── StatusTag Component ─── */
function StatusTag({ label, open }: { label: string; open: boolean }) {
  return (
    <span
      style={{
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: '0.06em',
        textTransform: 'uppercase' as const,
        padding: '4px 10px',
        borderRadius: 9999,
        background: open ? 'rgba(16,185,129,0.08)' : 'rgba(59,130,246,0.06)',
        border: `1px solid ${open ? 'rgba(16,185,129,0.20)' : 'rgba(59,130,246,0.16)'}`,
        color: open ? '#10B981' : '#3B82F6',
        whiteSpace: 'nowrap' as const,
      }}
    >
      {label} {open ? 'OPEN' : 'CLOSED'}
    </span>
  )
}

/* ─── TickerMarquee Component ─── */
function TickerMarquee({ tickers }: { tickers: Ticker[] }) {
  const doubled = [...tickers, ...tickers]

  return (
    <div style={{ overflow: 'hidden', flex: '0 0 auto', maxWidth: 420, position: 'relative' }}>
      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 16, background: 'linear-gradient(to right, rgba(13,18,30,0.92), transparent)', zIndex: 2, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 16, background: 'linear-gradient(to left, rgba(13,18,30,0.92), transparent)', zIndex: 2, pointerEvents: 'none' }} />
      <div className="rvn-marquee-track" style={{ display: 'flex', gap: 20, whiteSpace: 'nowrap' as const }}>
        {doubled.map((t, i) => {
          const pos = isPositive(t.change)
          return (
            <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}>
              <span style={{ color: '#94A3B8', fontWeight: 600 }}>{t.symbol}</span>
              <span style={{ color: '#CBD5E1' }}>{t.price}</span>
              <span style={{ color: pos ? '#10B981' : '#EF4444', fontWeight: 700 }}>{t.change}</span>
            </span>
          )
        })}
      </div>
    </div>
  )
}

/* ─── Separator ─── */
function Separator() {
  return <div style={{ width: 1, height: 16, backgroundColor: 'rgba(51,65,85,0.3)', flexShrink: 0 }} />
}

/* ═══════════════════════════════════════════════════════════
   TopBar Component — 56px fixed header
   ═══════════════════════════════════════════════════════════ */
function TopBar() {
  const location = useLocation()
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const route = routeLabels[location.pathname] ?? { title: 'Ravinala', subtitle: 'Financial Terminal' }
  const status = getMarketStatus(now)

  return (
    <header
      style={{
        position: 'fixed',
        top: 0,
        left: 280,
        right: 0,
        height: TOPBAR_HEIGHT,
        zIndex: 1000,
        background: 'rgba(10,14,26,0.82)',
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
        borderBottom: '1px solid rgba(51,65,85,0.3)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        gap: 12,
      }}
    >
      {/* Page title */}
      <span
        style={{
          fontSize: 16,
          fontWeight: 700,
          letterSpacing: '0.12em',
          textTransform: 'uppercase' as const,
          color: '#00D9FF',
          whiteSpace: 'nowrap' as const,
        }}
      >
        {route.title}
      </span>

      <Separator />

      {/* Subtitle */}
      <span
        style={{
          fontSize: 11,
          fontWeight: 400,
          color: '#94A3B8',
          whiteSpace: 'nowrap' as const,
        }}
      >
        {route.subtitle}
      </span>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Market status tags */}
      <StatusTag label="US" open={status.us} />
      <StatusTag label="EU" open={status.eu} />
      <StatusTag label="ASIA" open={status.asia} />

      <Separator />

      {/* Date */}
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11,
          color: '#94A3B8',
          whiteSpace: 'nowrap' as const,
        }}
      >
        {formatDate(now)}
      </span>

      {/* Time */}
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 13,
          fontWeight: 500,
          color: '#00D9FF',
          minWidth: 70,
          textAlign: 'right' as const,
          whiteSpace: 'nowrap' as const,
        }}
      >
        {formatTime(now)}
      </span>
    </header>
  )
}

/* ═══════════════════════════════════════════════════════════
   MarketStrip Component — 54px fixed strip below TopBar
   ═══════════════════════════════════════════════════════════ */
function MarketStrip() {
  const [now, setNow] = useState(new Date())
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const status = getMarketStatus(now)

  return (
    <div
      style={{
        position: 'fixed',
        top: TOPBAR_HEIGHT,
        left: 280,
        right: 0,
        height: MARKET_STRIP_HEIGHT,
        zIndex: 900,
        background: 'rgba(13,18,30,0.92)',
        borderBottom: '1px solid rgba(51,65,85,0.2)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
      }}
    >
      {/* Label */}
      <span
        style={{
          fontSize: 10,
          color: '#64748B',
          letterSpacing: '0.08em',
          textTransform: 'uppercase' as const,
          fontWeight: 600,
          marginRight: 12,
          flexShrink: 0,
        }}
      >
        MARKETS
      </span>

      {/* Scrollable market cards */}
      <div
        ref={scrollRef}
        className="rvn-mkt-scroll"
        style={{
          display: 'flex',
          gap: 8,
          overflowX: 'auto',
          whiteSpace: 'nowrap' as const,
          flex: 1,
        }}
      >
        {MARKET_INDICES.map((idx) => (
          <MarketCard key={idx.venue + idx.name} idx={idx} now={now} marketStatus={status} />
        ))}
      </div>

      {/* Separator */}
      <div style={{ width: 1, height: 28, backgroundColor: 'rgba(51,65,85,0.3)', margin: '0 12px', flexShrink: 0 }} />

      {/* Ticker marquee */}
      <TickerMarquee tickers={TOP_TICKERS} />

      {/* Injected styles */}
      <style>{`
        .rvn-mkt-scroll::-webkit-scrollbar { display: none; }
        .rvn-mkt-scroll { scrollbar-width: none; -ms-overflow-style: none; }

        @keyframes rvn-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        .rvn-live-dot {
          animation: rvn-pulse 2s ease-in-out infinite;
        }

        @keyframes rvn-marquee {
          0%   { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .rvn-marquee-track {
          animation: rvn-marquee 25s linear infinite;
        }
      `}</style>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Exports
   ═══════════════════════════════════════════════════════════ */
export default TopBar

export { MarketStrip }
