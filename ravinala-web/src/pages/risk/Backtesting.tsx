/**
 * Backtesting.tsx
 * Strategy backtesting engine — equity curve, drawdown, stats, monthly heatmap, rolling Sharpe.
 * All demo data generated client-side.
 */

import { useState, useCallback } from 'react'
import { useIndices } from '../../hooks/useMarketData'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Card } from '../../components/ui/Card'

// ─── Theme ───────────────────────────────────────────────────────────────────

const C = {
  bg: '#0A0E1A',
  surface: '#131823',
  elevated: '#1A2332',
  text: '#F1F5F9',
  muted: '#94A3B8',
  red: '#EF4444',
  green: '#10B981',
  accent: '#EF4444',
  border: 'rgba(51,65,85,0.3)',
} as const

const inputStyle: React.CSSProperties = {
  backgroundColor: C.elevated,
  border: `1px solid ${C.border}`,
  borderRadius: 6,
  padding: '6px 10px',
  color: C.text,
  fontSize: 13,
  width: '100%',
  outline: 'none',
  fontFamily: 'JetBrains Mono, monospace',
}

const labelStyle: React.CSSProperties = {
  color: C.muted,
  fontSize: 11,
  fontWeight: 600,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.05em',
  marginBottom: 4,
  display: 'block',
}

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  appearance: 'none' as const,
  cursor: 'pointer',
}

const btnStyle: React.CSSProperties = {
  background: `linear-gradient(135deg, ${C.red}, #DC2626)`,
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '8px 20px',
  fontWeight: 600,
  fontSize: 13,
  cursor: 'pointer',
  fontFamily: 'JetBrains Mono, monospace',
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(n: number, digits = 2): string {
  if (!isFinite(n)) return '—'
  return n.toFixed(digits)
}

function pct(n: number): string {
  if (!isFinite(n)) return '—'
  return `${(n * 100).toFixed(2)}%`
}

/** Seeded pseudo-random (simple LCG) for reproducible demo data. */
function seededRandom(seed: number): () => number {
  let s = seed
  return () => {
    s = (s * 1664525 + 1013904223) & 0x7fffffff
    return s / 0x7fffffff
  }
}

/** Box-Muller transform for normal random variates. */
function normalRandom(rng: () => number): number {
  const u1 = rng()
  const u2 = rng()
  return Math.sqrt(-2 * Math.log(Math.max(u1, 1e-10))) * Math.cos(2 * Math.PI * u2)
}

type StrategyType = 'Trend Following' | 'Mean Reversion' | 'Carry'

interface BacktestResult {
  equityCurve: { day: number; equity: number; price: number }[]
  drawdownCurve: { day: number; drawdown: number }[]
  monthlyReturns: { month: string; ret: number }[]
  rollingSharpe: { day: number; sharpe: number }[]
  stats: {
    cagr: number
    sharpe: number
    sortino: number
    maxDrawdown: number
    calmar: number
    winRate: number
    profitFactor: number
  }
}

function runBacktest(
  strategy: StrategyType,
  lookback: number,
  entryThresh: number,
  exitThresh: number,
): BacktestResult {
  const days = 252
  const rng = seededRandom(42)

  // Generate price path (random walk with drift)
  const prices: number[] = [100]
  for (let i = 1; i < days; i++) {
    const drift = 0.0003
    const vol = 0.015
    prices.push(prices[i - 1] * Math.exp(drift + vol * normalRandom(rng)))
  }

  // Generate signals and equity curve
  const equity: number[] = [10000]
  const dailyReturns: number[] = []
  let position = 0
  let wins = 0
  let losses = 0
  let grossProfit = 0
  let grossLoss = 0

  for (let i = 1; i < days; i++) {
    const lb = Math.min(lookback, i)
    const avg = prices.slice(i - lb, i).reduce((a, b) => a + b, 0) / lb
    const priceReturn = (prices[i] - prices[i - 1]) / prices[i - 1]

    if (strategy === 'Trend Following') {
      if (prices[i] > avg * (1 + entryThresh / 100) && position <= 0) position = 1
      else if (prices[i] < avg * (1 - exitThresh / 100) && position >= 0) position = -1
    } else if (strategy === 'Mean Reversion') {
      if (prices[i] < avg * (1 - entryThresh / 100) && position <= 0) position = 1
      else if (prices[i] > avg * (1 + exitThresh / 100) && position >= 0) position = -1
    } else {
      // Carry: always long with variable sizing
      position = prices[i] > avg ? 1 : 0.5
    }

    const pnl = position * priceReturn
    dailyReturns.push(pnl)
    equity.push(equity[i - 1] * (1 + pnl))

    if (pnl > 0) { wins++; grossProfit += pnl }
    else if (pnl < 0) { losses++; grossLoss += Math.abs(pnl) }
  }

  // Equity curve data
  const equityCurve = equity.map((eq, i) => ({
    day: i,
    equity: eq,
    price: prices[Math.min(i, prices.length - 1)],
  }))

  // Drawdown
  let peak = equity[0]
  const drawdownCurve = equity.map((eq, i) => {
    peak = Math.max(peak, eq)
    return { day: i, drawdown: (eq - peak) / peak }
  })

  // Stats
  const totalReturn = equity[days - 1] / equity[0] - 1
  const cagr = totalReturn // ~1 year
  const meanDaily = dailyReturns.reduce((a, b) => a + b, 0) / dailyReturns.length
  const stdDaily = Math.sqrt(dailyReturns.reduce((a, b) => a + (b - meanDaily) ** 2, 0) / dailyReturns.length)
  const downside = dailyReturns.filter((r) => r < 0)
  const downsideStd = downside.length > 0
    ? Math.sqrt(downside.reduce((a, b) => a + b * b, 0) / downside.length)
    : 0.01
  const sharpe = (meanDaily / Math.max(stdDaily, 0.0001)) * Math.sqrt(252)
  const sortino = (meanDaily / Math.max(downsideStd, 0.0001)) * Math.sqrt(252)
  const maxDrawdown = Math.min(...drawdownCurve.map((d) => d.drawdown))
  const calmar = Math.abs(maxDrawdown) > 0 ? cagr / Math.abs(maxDrawdown) : 0
  const winRate = wins / Math.max(wins + losses, 1)
  const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit > 0 ? Infinity : 0

  // Monthly returns (21 trading days per month)
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const monthlyReturns: { month: string; ret: number }[] = []
  for (let m = 0; m < 12; m++) {
    const start = m * 21
    const end = Math.min(start + 21, days)
    if (start >= days) break
    const mRet = equity[end] / equity[start] - 1
    monthlyReturns.push({ month: months[m], ret: mRet })
  }

  // Rolling Sharpe (63-day window)
  const rollingSharpe: { day: number; sharpe: number }[] = []
  const window = 63
  for (let i = window; i < dailyReturns.length; i++) {
    const slice = dailyReturns.slice(i - window, i)
    const mean = slice.reduce((a, b) => a + b, 0) / slice.length
    const std = Math.sqrt(slice.reduce((a, b) => a + (b - mean) ** 2, 0) / slice.length)
    rollingSharpe.push({ day: i, sharpe: std > 0 ? (mean / std) * Math.sqrt(252) : 0 })
  }

  return {
    equityCurve,
    drawdownCurve,
    monthlyReturns,
    rollingSharpe,
    stats: { cagr, sharpe, sortino, maxDrawdown, calmar, winRate, profitFactor },
  }
}

// ─── Stat Card ───────────────────────────────────────────────────────────────

function StatBox({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ padding: '12px 16px', backgroundColor: C.elevated, borderRadius: 8, textAlign: 'center' }}>
      <div style={{ fontSize: 11, color: C.muted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontSize: 18, fontWeight: 700, color: color || C.text, fontFamily: 'JetBrains Mono, monospace' }}>
        {value}
      </div>
    </div>
  )
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function Backtesting() {
  const { data: indicesData } = useIndices()
  const [strategy, setStrategy] = useState<StrategyType>('Trend Following')
  const [lookback, setLookback] = useState(20)
  const [entryThresh, setEntryThresh] = useState(2)
  const [exitThresh, setExitThresh] = useState(1)
  const [result, setResult] = useState<BacktestResult | null>(null)

  // Use live index data for benchmark context when available
  const benchmarkIdx = indicesData
    ? Object.values(indicesData).flat().find(idx => idx.symbol === 'SPX' || idx.name?.includes('S&P'))
    : undefined
  const benchmarkLabel = benchmarkIdx?.name ?? 'S&P 500'
  const benchmarkChange = benchmarkIdx?.change?.percent

  const handleRun = useCallback(() => {
    setResult(runBacktest(strategy, lookback, entryThresh, exitThresh))
  }, [strategy, lookback, entryThresh, exitThresh])

  return (
    <div style={{ backgroundColor: C.bg, minHeight: '100vh', padding: 24 }}>
      {!indicesData && (
        <div style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, padding: '8px 16px', marginBottom: 16, fontSize: 13, color: '#F59E0B', fontFamily: 'Inter, sans-serif' }}>
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, color: C.text, margin: 0 }}>
          Backtesting Engine
        </h1>
        <p style={{ color: C.muted, fontSize: 14, marginTop: 4 }}>
          Strategy simulation with performance analytics
          {benchmarkChange !== undefined && (
            <span style={{ marginLeft: 12, color: benchmarkChange >= 0 ? C.green : C.red }}>
              {benchmarkLabel}: {benchmarkChange >= 0 ? '+' : ''}{benchmarkChange.toFixed(2)}%
            </span>
          )}
        </p>
      </div>

      {/* Inputs */}
      <Card className="mb-4">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16, alignItems: 'end' }}>
          <div>
            <label style={labelStyle}>Strategy Type</label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as StrategyType)}
              style={selectStyle}
            >
              <option value="Trend Following">Trend Following</option>
              <option value="Mean Reversion">Mean Reversion</option>
              <option value="Carry">Carry</option>
            </select>
          </div>
          <div>
            <label style={labelStyle}>Lookback Period (days)</label>
            <input
              type="number"
              value={lookback}
              onChange={(e) => setLookback(Math.max(5, Number(e.target.value) || 20))}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Entry Threshold (%)</label>
            <input
              type="number"
              step={0.5}
              value={entryThresh}
              onChange={(e) => setEntryThresh(Number(e.target.value) || 2)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Exit Threshold (%)</label>
            <input
              type="number"
              step={0.5}
              value={exitThresh}
              onChange={(e) => setExitThresh(Number(e.target.value) || 1)}
              style={inputStyle}
            />
          </div>
          <div>
            <button onClick={handleRun} style={btnStyle}>
              Run Backtest
            </button>
          </div>
        </div>
      </Card>

      {result && (
        <>
          {/* Stats Dashboard */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 12, marginBottom: 16 }}>
            <StatBox label="CAGR" value={pct(result.stats.cagr)} color={result.stats.cagr >= 0 ? C.green : C.red} />
            <StatBox label="Sharpe" value={fmt(result.stats.sharpe)} color={result.stats.sharpe >= 1 ? C.green : C.red} />
            <StatBox label="Sortino" value={fmt(result.stats.sortino)} />
            <StatBox label="Max Drawdown" value={pct(result.stats.maxDrawdown)} color={C.red} />
            <StatBox label="Calmar" value={fmt(result.stats.calmar)} />
            <StatBox label="Win Rate" value={pct(result.stats.winRate)} color={result.stats.winRate >= 0.5 ? C.green : C.red} />
            <StatBox label="Profit Factor" value={fmt(result.stats.profitFactor)} />
          </div>

          {/* Charts Row 1: Equity Curve + Drawdown */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
            <Card title="Equity Curve" subtitle="Portfolio value over time">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={result.equityCurve} margin={{ top: 10, right: 30, bottom: 10, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                  <XAxis dataKey="day" stroke={C.muted} tick={{ fill: C.muted, fontSize: 11 }} />
                  <YAxis stroke={C.muted} tick={{ fill: C.muted, fontSize: 11 }} tickFormatter={(v: any) => `$${(v / 1000).toFixed(1)}k`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: C.elevated, border: `1px solid ${C.border}`, borderRadius: 6 }}
                    labelStyle={{ color: C.text }}
                    itemStyle={{ color: C.muted }}
                    formatter={(v: any) => `$${Number(v).toFixed(0)}`}
                    labelFormatter={(v: any) => `Day ${v}`}
                  />
                  <Legend wrapperStyle={{ color: C.muted, fontSize: 11 }} />
                  <Line type="monotone" dataKey="equity" stroke={C.green} strokeWidth={2} dot={false} name="Equity" />
                </LineChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Drawdown" subtitle="Peak-to-trough decline">
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={result.drawdownCurve} margin={{ top: 10, right: 30, bottom: 10, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                  <XAxis dataKey="day" stroke={C.muted} tick={{ fill: C.muted, fontSize: 11 }} />
                  <YAxis stroke={C.muted} tick={{ fill: C.muted, fontSize: 11 }} tickFormatter={(v: any) => `${(v * 100).toFixed(1)}%`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: C.elevated, border: `1px solid ${C.border}`, borderRadius: 6 }}
                    labelStyle={{ color: C.text }}
                    itemStyle={{ color: C.muted }}
                    formatter={(v: any) => `${(Number(v) * 100).toFixed(2)}%`}
                    labelFormatter={(v: any) => `Day ${v}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="drawdown"
                    stroke={C.red}
                    fill={C.red}
                    fillOpacity={0.3}
                    strokeWidth={2}
                    name="Drawdown"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* Monthly Returns Heatmap */}
          <Card className="mb-4" title="Monthly Returns" subtitle="Performance by month">
            <div style={{ display: 'grid', gridTemplateColumns: `repeat(${result.monthlyReturns.length}, 1fr)`, gap: 6 }}>
              {result.monthlyReturns.map((m) => {
                const absMax = Math.max(...result.monthlyReturns.map((x) => Math.abs(x.ret)), 0.01)
                const intensity = Math.min(Math.abs(m.ret) / absMax, 1)
                const bg = m.ret >= 0
                  ? `rgba(16,185,129,${0.15 + intensity * 0.6})`
                  : `rgba(239,68,68,${0.15 + intensity * 0.6})`
                return (
                  <div
                    key={m.month}
                    style={{
                      backgroundColor: bg,
                      borderRadius: 6,
                      padding: '12px 8px',
                      textAlign: 'center',
                    }}
                  >
                    <div style={{ fontSize: 11, color: C.muted, fontWeight: 600, marginBottom: 4 }}>{m.month}</div>
                    <div
                      style={{
                        fontSize: 14,
                        fontWeight: 700,
                        color: m.ret >= 0 ? C.green : C.red,
                        fontFamily: 'JetBrains Mono, monospace',
                      }}
                    >
                      {(m.ret * 100).toFixed(1)}%
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>

          {/* Rolling Sharpe */}
          <Card title="Rolling Sharpe Ratio" subtitle="63-day rolling window, annualized">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={result.rollingSharpe} margin={{ top: 10, right: 30, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                <XAxis dataKey="day" stroke={C.muted} tick={{ fill: C.muted, fontSize: 11 }} />
                <YAxis stroke={C.muted} tick={{ fill: C.muted, fontSize: 11 }} tickFormatter={(v: any) => fmt(v, 1)} />
                <Tooltip
                  contentStyle={{ backgroundColor: C.elevated, border: `1px solid ${C.border}`, borderRadius: 6 }}
                  labelStyle={{ color: C.text }}
                  itemStyle={{ color: C.muted }}
                  formatter={(v: any) => fmt(Number(v))}
                  labelFormatter={(v: any) => `Day ${v}`}
                />
                <Line type="monotone" dataKey="sharpe" stroke="#F59E0B" strokeWidth={2} dot={false} name="Rolling Sharpe" />
                {/* Reference line at 0 */}
                <Line
                  type="monotone"
                  dataKey={() => 0}
                  stroke={C.muted}
                  strokeWidth={1}
                  strokeDasharray="5 5"
                  dot={false}
                  name="Zero"
                  legendType="none"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </>
      )}
    </div>
  )
}
