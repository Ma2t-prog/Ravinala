/**
 * MarketStrip — thin scrolling ticker bar below the TopBar.
 * Sits fixed at top: 56px (right below the 56px TopBar), height 54px.
 *
 * Uses live backend data via useIndices(); falls back to hardcoded demo data
 * when the backend is unreachable or still loading so the strip is never blank.
 */
import { useMemo } from 'react'
import { useIndices } from '../../hooks/useMarketData'

interface TickerEntry {
  symbol: string
  value: string
  change: string
  up: boolean
}

/** Static fallback so the strip is never empty. */
const DEMO_MARKET_DATA: TickerEntry[] = [
  { symbol: 'SPX', value: '5,248.32', change: '+0.62%', up: true },
  { symbol: 'NDX', value: '18,412.50', change: '+0.88%', up: true },
  { symbol: 'DJI', value: '39,781.10', change: '+0.35%', up: true },
  { symbol: 'VIX', value: '14.32', change: '-2.10%', up: false },
  { symbol: 'US10Y', value: '4.258%', change: '+1.2bp', up: true },
  { symbol: 'DXY', value: '104.18', change: '-0.15%', up: false },
  { symbol: 'EUR/USD', value: '1.0842', change: '+0.12%', up: true },
  { symbol: 'GBP/USD', value: '1.2645', change: '+0.08%', up: true },
  { symbol: 'BTC', value: '67,421', change: '+1.45%', up: true },
  { symbol: 'ETH', value: '3,512', change: '+2.10%', up: true },
  { symbol: 'Gold', value: '2,178.40', change: '+0.32%', up: true },
  { symbol: 'Oil WTI', value: '78.52', change: '-0.48%', up: false },
]

/** Format a number with locale-aware thousand separators. */
function fmtPrice(n: number): string {
  return n.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

/** Format a percentage change with sign and % suffix. */
function fmtPercent(n: number): string {
  const sign = n >= 0 ? '+' : ''
  return `${sign}${n.toFixed(2)}%`
}

export default function MarketStrip() {
  const { data: indicesData } = useIndices()

  const tickers: TickerEntry[] = useMemo(() => {
    if (!indicesData) return DEMO_MARKET_DATA

    const live: TickerEntry[] = Object.values(indicesData)
      .flat()
      .slice(0, 12)
      .map((idx) => ({
        symbol: idx.symbol,
        value: fmtPrice(idx.price),
        change: fmtPercent(idx.change.percent),
        up: idx.change.percent >= 0,
      }))

    return live.length > 0 ? live : DEMO_MARKET_DATA
  }, [indicesData])

  // Duplicate for seamless marquee loop
  const items = [...tickers, ...tickers]

  return (
    <div
      style={{
        position: 'fixed',
        top: 56,
        left: 280,
        right: 0,
        height: 54,
        backgroundColor: 'rgba(10,14,26,0.90)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        borderBottom: '1px solid rgba(51,65,85,0.2)',
        display: 'flex',
        alignItems: 'center',
        overflow: 'hidden',
        zIndex: 89,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 32,
          whiteSpace: 'nowrap',
          animation: 'marquee-scroll 60s linear infinite',
        }}
      >
        {items.map((t, i) => (
          <span
            key={i}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 11,
              letterSpacing: '0.04em',
            }}
          >
            <span style={{ color: '#94A3B8', fontWeight: 600 }}>{t.symbol}</span>
            <span style={{ color: '#F1F5F9' }}>{t.value}</span>
            <span style={{ color: t.up ? '#10B981' : '#EF4444', fontWeight: 500 }}>
              {t.change}
            </span>
          </span>
        ))}
      </div>
    </div>
  )
}
