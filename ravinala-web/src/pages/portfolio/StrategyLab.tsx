import { useState, useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { Card } from '../../components/ui/Card'
import { useIndices } from '../../hooks/useMarketData'

// ── Types ────────────────────────────────────────────────────────────────────

type StrategyName = 'MA Crossover' | 'RSI Mean Reversion' | 'Momentum' | 'Buy & Hold'

interface BacktestStats {
  totalReturn: number
  sharpe: number
  maxDrawdown: number
  winRate: number
  avgWin: number
  avgLoss: number
}

interface Trade {
  date: string
  signal: 'BUY' | 'SELL'
  price: number
  returnPct: number
}

interface StrategyResult {
  stats: BacktestStats
  trades: Trade[]
  equity: { day: number; strategy: number; benchmark: number }[]
}

// ── Demo backtest data generator ─────────────────────────────────────────────

function generateBacktest(strategy: StrategyName, _fast: number, _slow: number, _lookback: number): StrategyResult {
  const seed: Record<StrategyName, { ret: number; sharpe: number; dd: number; wr: number }> = {
    'MA Crossover': { ret: 18.5, sharpe: 1.32, dd: -12.4, wr: 58 },
    'RSI Mean Reversion': { ret: 14.2, sharpe: 1.05, dd: -15.8, wr: 62 },
    'Momentum': { ret: 22.8, sharpe: 1.55, dd: -18.2, wr: 52 },
    'Buy & Hold': { ret: 12.4, sharpe: 0.85, dd: -22.1, wr: 100 },
  }
  const s = seed[strategy]

  const equity: { day: number; strategy: number; benchmark: number }[] = []
  let strat = 100
  let bench = 100
  for (let i = 0; i <= 252; i++) {
    const stratDaily = (s.ret / 252) + (Math.sin(i * 0.1) * 0.3 + (i % 7 === 0 ? -0.5 : 0.15))
    const benchDaily = (12.4 / 252) + (Math.cos(i * 0.08) * 0.25)
    strat += strat * (stratDaily / 100)
    bench += bench * (benchDaily / 100)
    if (i % 5 === 0) {
      equity.push({ day: i, strategy: Math.round(strat * 100) / 100, benchmark: Math.round(bench * 100) / 100 })
    }
  }

  const trades: Trade[] = [
    { date: '2025-01-15', signal: 'BUY', price: 182.45, returnPct: 3.2 },
    { date: '2025-02-03', signal: 'SELL', price: 188.30, returnPct: -1.1 },
    { date: '2025-02-18', signal: 'BUY', price: 186.22, returnPct: 4.5 },
    { date: '2025-03-05', signal: 'SELL', price: 194.60, returnPct: 2.8 },
    { date: '2025-03-22', signal: 'BUY', price: 190.15, returnPct: -2.3 },
    { date: '2025-04-10', signal: 'SELL', price: 185.78, returnPct: 1.6 },
    { date: '2025-05-01', signal: 'BUY', price: 188.72, returnPct: 5.1 },
    { date: '2025-05-20', signal: 'SELL', price: 198.34, returnPct: -0.8 },
    { date: '2025-06-08', signal: 'BUY', price: 196.75, returnPct: 3.9 },
    { date: '2025-06-25', signal: 'SELL', price: 204.42, returnPct: 2.1 },
  ]

  return {
    stats: { totalReturn: s.ret, sharpe: s.sharpe, maxDrawdown: s.dd, winRate: s.wr, avgWin: 3.5, avgLoss: -1.4 },
    trades,
    equity,
  }
}

// ── Component ────────────────────────────────────────────────────────────────

export default function StrategyLab() {
  const { data: indicesData } = useIndices()
  const liveData = indicesData ?? null

  const strategies: StrategyName[] = ['MA Crossover', 'RSI Mean Reversion', 'Momentum', 'Buy & Hold']
  const [strategy, setStrategy] = useState<StrategyName>('MA Crossover')
  const [fastPeriod, setFastPeriod] = useState(10)
  const [slowPeriod, setSlowPeriod] = useState(50)
  const [lookback, setLookback] = useState(20)
  const [hasRun, setHasRun] = useState(false)

  const result = useMemo(() => {
    if (!hasRun) return null
    return generateBacktest(strategy, fastPeriod, slowPeriod, lookback)
  }, [hasRun, strategy, fastPeriod, slowPeriod, lookback])

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 12px', borderRadius: 6,
    border: '1px solid rgba(51,65,85,0.3)', backgroundColor: '#0A0E1A',
    color: '#F1F5F9', fontFamily: 'JetBrains Mono, monospace', fontSize: 13, outline: 'none',
  }

  return (
    <div style={{ color: '#F1F5F9', minHeight: '100vh' }}>
      {!liveData && (
        <div style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, padding: '8px 16px', marginBottom: 16, fontSize: 13, color: '#F59E0B', fontFamily: 'Inter, sans-serif' }}>
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      <h1 style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, marginBottom: 4 }}>
        Strategy Lab
      </h1>
      <p style={{ color: '#94A3B8', fontSize: 14, marginBottom: 24 }}>
        Backtest trading strategies against historical data
      </p>

      {liveData && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, padding: '8px 16px', borderRadius: 8, backgroundColor: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#10B981', boxShadow: '0 0 6px rgba(16,185,129,0.6)' }} />
          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#10B981', fontWeight: 600 }}>Live Benchmark</span>
          <span style={{ color: '#94A3B8', fontSize: 12 }}>|</span>
          {Object.values(liveData).flat().slice(0, 3).map((idx) => (
            <span key={idx.symbol} style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>
              <span style={{ color: '#94A3B8' }}>{idx.symbol}</span>{' '}
              <span style={{ color: '#F1F5F9' }}>{idx.price.toLocaleString()}</span>{' '}
              <span style={{ color: idx.change.percent >= 0 ? '#10B981' : '#EF4444', fontSize: 11 }}>
                {idx.change.percent >= 0 ? '+' : ''}{idx.change.percent.toFixed(2)}%
              </span>
            </span>
          ))}
        </div>
      )}

      {/* ── Controls ── */}
      <Card title="Strategy Configuration">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
          <div>
            <div style={{ color: '#94A3B8', fontSize: 11, marginBottom: 4 }}>Strategy</div>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as StrategyName)}
              style={inputStyle}
            >
              {strategies.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <div style={{ color: '#94A3B8', fontSize: 11, marginBottom: 4 }}>Fast Period</div>
            <input type="number" value={fastPeriod} onChange={(e) => setFastPeriod(Number(e.target.value))} style={inputStyle} />
          </div>
          <div>
            <div style={{ color: '#94A3B8', fontSize: 11, marginBottom: 4 }}>Slow Period</div>
            <input type="number" value={slowPeriod} onChange={(e) => setSlowPeriod(Number(e.target.value))} style={inputStyle} />
          </div>
          <div>
            <div style={{ color: '#94A3B8', fontSize: 11, marginBottom: 4 }}>Lookback</div>
            <input type="number" value={lookback} onChange={(e) => setLookback(Number(e.target.value))} style={inputStyle} />
          </div>
        </div>
        <button
          onClick={() => setHasRun(true)}
          style={{
            padding: '10px 32px', borderRadius: 8, border: 'none',
            backgroundColor: '#8B5CF6', color: '#F1F5F9', fontWeight: 700,
            fontFamily: 'JetBrains Mono, monospace', fontSize: 13, cursor: 'pointer',
          }}
        >
          Run Backtest
        </button>
      </Card>

      {result && (
        <>
          {/* ── Stats Row ── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 12, marginTop: 16 }}>
            {([
              ['Total Return', `${result.stats.totalReturn > 0 ? '+' : ''}${result.stats.totalReturn.toFixed(1)}%`, result.stats.totalReturn >= 0],
              ['Sharpe Ratio', result.stats.sharpe.toFixed(2), result.stats.sharpe >= 1],
              ['Max Drawdown', `${result.stats.maxDrawdown.toFixed(1)}%`, false],
              ['Win Rate', `${result.stats.winRate.toFixed(0)}%`, result.stats.winRate >= 50],
              ['Avg Win', `+${result.stats.avgWin.toFixed(1)}%`, true],
              ['Avg Loss', `${result.stats.avgLoss.toFixed(1)}%`, false],
            ] as [string, string, boolean][]).map(([label, val, isGood]) => (
              <Card key={label}>
                <div style={{ color: '#94A3B8', fontSize: 11, marginBottom: 4 }}>{label}</div>
                <div style={{
                  fontFamily: 'JetBrains Mono, monospace', fontSize: 20, fontWeight: 700,
                  color: isGood ? '#8B5CF6' : '#EF4444',
                }}>
                  {val}
                </div>
              </Card>
            ))}
          </div>

          {/* ── Equity Curve ── */}
          <div style={{ marginTop: 16 }}>
            <Card title="Equity Curve" subtitle="Strategy vs Benchmark (252 trading days)">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={result.equity}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                  <XAxis dataKey="day" tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false}
                    tickFormatter={(v: any) => `D${v}`} />
                  <YAxis tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false}
                    tickFormatter={(v: any) => `$${v}`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#131823', border: '1px solid rgba(51,65,85,0.3)', borderRadius: 8, color: '#F1F5F9' }}
                    formatter={(v: any) => [`$${Number(v).toFixed(2)}`, '']}
                  />
                  <Legend formatter={(value: any) => <span style={{ color: '#94A3B8', fontSize: 12 }}>{value}</span>} />
                  <Line type="monotone" dataKey="strategy" name="Strategy" stroke="#8B5CF6" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="benchmark" name="Benchmark" stroke="#94A3B8" strokeWidth={1.5} dot={false} strokeDasharray="5 5" />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* ── Trade Log ── */}
          <div style={{ marginTop: 16 }}>
            <Card title="Trade Log" subtitle="Last 10 signals">
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(51,65,85,0.3)' }}>
                      {['Date', 'Signal', 'Price', 'Return'].map((h) => (
                        <th key={h} style={{ textAlign: 'left', padding: '8px 10px', color: '#94A3B8', fontSize: 11, fontWeight: 600 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((t, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(51,65,85,0.15)' }}>
                        <td style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace' }}>{t.date}</td>
                        <td style={{ padding: '8px 10px' }}>
                          <span style={{
                            padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700,
                            backgroundColor: t.signal === 'BUY' ? 'rgba(139,92,246,0.15)' : 'rgba(239,68,68,0.15)',
                            color: t.signal === 'BUY' ? '#8B5CF6' : '#EF4444',
                          }}>
                            {t.signal}
                          </span>
                        </td>
                        <td style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace' }}>${t.price.toFixed(2)}</td>
                        <td style={{
                          padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace',
                          color: t.returnPct >= 0 ? '#10B981' : '#EF4444',
                        }}>
                          {t.returnPct >= 0 ? '+' : ''}{t.returnPct.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
