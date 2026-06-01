import { useState, useMemo, useCallback } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { Card } from '../../components/ui/Card'
import { useSnapshot } from '../../hooks/useMarketData'

// ─── Theme ───────────────────────────────────────────────────────────────────
const AMBER = '#F59E0B'
const BG = '#0A0E1A'
const ELEVATED = '#1A2332'
const TEXT = '#F1F5F9'
const MUTED = '#94A3B8'
const MONO = 'JetBrains Mono, monospace'
const SANS = 'Inter, system-ui, sans-serif'

// ─── Types ───────────────────────────────────────────────────────────────────
interface PayoffPoint {
  spot: number
  payoff: number
}

interface Params {
  spot: number
  strike1: number
  strike2: number
  premium: number
}

type PresetName = 'Bull Call Spread' | 'Bear Put Spread' | 'Straddle' | 'Strangle' | 'Iron Condor' | 'Butterfly'

interface PresetDef {
  name: PresetName
  description: string
  formula: string
  generate: (p: Params) => PayoffPoint[]
}

// ─── Payoff generators ───────────────────────────────────────────────────────
function makePoints(fn: (s: number, p: Params) => number, p: Params): PayoffPoint[] {
  const points: PayoffPoint[] = []
  const lo = Math.max(0, p.spot * 0.3)
  const hi = p.spot * 1.7
  const step = (hi - lo) / 200
  for (let s = lo; s <= hi; s += step) {
    points.push({ spot: Math.round(s * 100) / 100, payoff: Math.round(fn(s, p) * 100) / 100 })
  }
  return points
}

const PRESETS: PresetDef[] = [
  {
    name: 'Bull Call Spread',
    description: 'Buy call at K1, sell call at K2 (K2 > K1). Limited risk, limited reward bullish strategy.',
    formula: 'max(S-K1, 0) - max(S-K2, 0) - premium',
    generate: (p) => makePoints((s, { strike1, strike2, premium }) =>
      Math.max(s - strike1, 0) - Math.max(s - strike2, 0) - premium, p),
  },
  {
    name: 'Bear Put Spread',
    description: 'Buy put at K2, sell put at K1 (K2 > K1). Limited risk bearish strategy.',
    formula: 'max(K2-S, 0) - max(K1-S, 0) - premium',
    generate: (p) => makePoints((s, { strike1, strike2, premium }) =>
      Math.max(strike2 - s, 0) - Math.max(strike1 - s, 0) - premium, p),
  },
  {
    name: 'Straddle',
    description: 'Buy call and put at same strike K1. Profit from large moves in either direction.',
    formula: 'max(S-K1, 0) + max(K1-S, 0) - premium',
    generate: (p) => makePoints((s, { strike1, premium }) =>
      Math.max(s - strike1, 0) + Math.max(strike1 - s, 0) - premium, p),
  },
  {
    name: 'Strangle',
    description: 'Buy put at K1, buy call at K2 (K1 < K2). Cheaper than straddle, needs larger move.',
    formula: 'max(S-K2, 0) + max(K1-S, 0) - premium',
    generate: (p) => makePoints((s, { strike1, strike2, premium }) =>
      Math.max(s - strike2, 0) + Math.max(strike1 - s, 0) - premium, p),
  },
  {
    name: 'Iron Condor',
    description: 'Sell strangle, buy wider strangle. Profit from low volatility within a range.',
    formula: 'min(max(S-K1,0), w) - max(S-K2,0) + min(max(K2-S,0), w) - max(K1-S,0) + premium',
    generate: (p) => {
      const w = (p.strike2 - p.strike1) * 0.5
      const k1 = p.strike1
      const k2 = p.strike2
      const innerLow = k1 + w
      const innerHigh = k2 - w
      return makePoints((s) => {
        const putSpread = Math.max(innerLow - s, 0) - Math.max(k1 - s, 0)
        const callSpread = Math.max(s - innerHigh, 0) - Math.max(s - k2, 0)
        return p.premium - putSpread - callSpread
      }, p)
    },
  },
  {
    name: 'Butterfly',
    description: 'Buy 1 call at K1, sell 2 calls at mid, buy 1 call at K2. Profit from low vol near mid.',
    formula: 'max(S-K1,0) - 2*max(S-M,0) + max(S-K2,0) - premium',
    generate: (p) => {
      const mid = (p.strike1 + p.strike2) / 2
      return makePoints((s, { strike1, strike2, premium }) =>
        Math.max(s - strike1, 0) - 2 * Math.max(s - mid, 0) + Math.max(s - strike2, 0) - premium, p)
    },
  },
]

// ─── Custom formula parser (simple expressions) ─────────────────────────────
function parseCustomFormula(formula: string, p: Params): PayoffPoint[] {
  try {
    return makePoints((s, { strike1, strike2, premium }) => {
      // Replace variable names and evaluate
      const expr = formula
        .replace(/\bS\b/g, `(${s})`)
        .replace(/\bK1\b/gi, `(${strike1})`)
        .replace(/\bK2\b/gi, `(${strike2})`)
        .replace(/\bK\b/g, `(${strike1})`)
        .replace(/\bP\b/g, `(${premium})`)
        .replace(/\bmax\b/gi, 'Math.max')
        .replace(/\bmin\b/gi, 'Math.min')
        .replace(/\babs\b/gi, 'Math.abs')
      // eslint-disable-next-line no-new-func
      const fn = new Function('Math', `return ${expr}`)
      const result = fn(Math)
      return typeof result === 'number' && isFinite(result) ? result : 0
    }, p)
  } catch {
    return []
  }
}

// ─── Styles ──────────────────────────────────────────────────────────────────
const inputStyle: React.CSSProperties = {
  backgroundColor: ELEVATED,
  border: '1px solid rgba(51,65,85,0.5)',
  borderRadius: 6,
  padding: '6px 10px',
  color: TEXT,
  fontFamily: MONO,
  fontSize: 13,
  width: '100%',
  outline: 'none',
  boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  color: MUTED,
  fontSize: 11,
  fontFamily: SANS,
  marginBottom: 4,
  display: 'block',
}

export default function CustomProduct() {
  // ── Live market data ────────────────────────────────────────────────────────
  const { data: snapshot, isLoading: snapshotLoading } = useSnapshot()
  const usingFallback = !snapshot

  const [formula, setFormula] = useState('max(S-K1, 0) - max(S-K2, 0) - P')
  const [params, setParams] = useState<Params>({ spot: 100, strike1: 95, strike2: 110, premium: 3 })
  const [activePreset, setActivePreset] = useState<PresetName | null>('Bull Call Spread')

  const payoffData = useMemo(() => {
    if (activePreset) {
      const preset = PRESETS.find(p => p.name === activePreset)
      return preset ? preset.generate(params) : []
    }
    return parseCustomFormula(formula, params)
  }, [formula, params, activePreset])

  const stats = useMemo(() => {
    if (payoffData.length === 0) return null
    const payoffs = payoffData.map(p => p.payoff)
    const maxProfit = Math.max(...payoffs)
    const maxLoss = Math.min(...payoffs)
    const breakevens = payoffData.filter((p, i) => {
      if (i === 0) return false
      return (payoffData[i - 1].payoff <= 0 && p.payoff >= 0) || (payoffData[i - 1].payoff >= 0 && p.payoff <= 0)
    })
    return { maxProfit, maxLoss, breakevens: breakevens.map(b => b.spot) }
  }, [payoffData])

  const selectPreset = useCallback((name: PresetName) => {
    const preset = PRESETS.find(p => p.name === name)
    if (preset) {
      setActivePreset(name)
      setFormula(preset.formula)
    }
  }, [])

  const handleFormulaChange = useCallback((val: string) => {
    setFormula(val)
    setActivePreset(null)
  }, [])

  return (
    <div style={{ background: BG, minHeight: '100vh', padding: 24, fontFamily: SANS }}>
      {/* Fallback Banner */}
      {usingFallback && !snapshotLoading && (
        <div style={{
          backgroundColor: 'rgba(245,158,11,0.1)',
          border: '1px solid rgba(245,158,11,0.3)',
          borderRadius: 6,
          padding: '8px 16px',
          marginBottom: 16,
          color: AMBER,
          fontSize: 13,
          fontFamily: MONO,
        }}>
          Backend unreachable — showing demo data
        </div>
      )}

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: MONO, fontSize: 26, color: TEXT, margin: 0 }}>
          <span style={{ color: AMBER }}>&#9670;</span> Custom Payoff Builder
        </h1>
        <p style={{ color: MUTED, fontSize: 14, marginTop: 4 }}>
          Design custom derivative payoffs with formulas or strategy presets
        </p>
      </div>

      {/* Preset buttons */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {PRESETS.map(pr => (
          <button
            key={pr.name}
            onClick={() => selectPreset(pr.name)}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: activePreset === pr.name ? `1px solid ${AMBER}` : '1px solid rgba(51,65,85,0.5)',
              background: activePreset === pr.name ? 'rgba(245,158,11,0.15)' : ELEVATED,
              color: activePreset === pr.name ? AMBER : MUTED,
              fontFamily: SANS,
              fontSize: 13,
              fontWeight: activePreset === pr.name ? 600 : 400,
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {pr.name}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 20 }}>
        {/* Left panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="Payoff Formula" subtitle="Variables: S, K1, K2, P">
            <textarea
              style={{
                ...inputStyle,
                height: 80,
                resize: 'vertical',
              }}
              value={formula}
              onChange={e => handleFormulaChange(e.target.value)}
              placeholder="e.g. max(S-K1, 0) - P"
            />
            {activePreset && (
              <div style={{ marginTop: 10, padding: 10, background: 'rgba(245,158,11,0.08)', borderRadius: 6, border: '1px solid rgba(245,158,11,0.2)' }}>
                <div style={{ color: AMBER, fontSize: 12, fontWeight: 600, marginBottom: 4 }}>{activePreset}</div>
                <div style={{ color: MUTED, fontSize: 12 }}>
                  {PRESETS.find(p => p.name === activePreset)?.description}
                </div>
              </div>
            )}
          </Card>

          <Card title="Parameters">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={labelStyle}>Spot (S)</label>
                <input style={inputStyle} type="number" value={params.spot}
                  onChange={e => setParams(p => ({ ...p, spot: +e.target.value }))} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={labelStyle}>Strike 1 (K1)</label>
                  <input style={inputStyle} type="number" value={params.strike1}
                    onChange={e => setParams(p => ({ ...p, strike1: +e.target.value }))} />
                </div>
                <div>
                  <label style={labelStyle}>Strike 2 (K2)</label>
                  <input style={inputStyle} type="number" value={params.strike2}
                    onChange={e => setParams(p => ({ ...p, strike2: +e.target.value }))} />
                </div>
              </div>
              <div>
                <label style={labelStyle}>Premium (P)</label>
                <input style={inputStyle} type="number" step="0.5" value={params.premium}
                  onChange={e => setParams(p => ({ ...p, premium: +e.target.value }))} />
              </div>
            </div>
          </Card>

          {/* Stats */}
          {stats && (
            <Card title="Strategy Statistics">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: MUTED, fontSize: 12 }}>Max Profit</span>
                  <span style={{ color: '#10B981', fontFamily: MONO, fontSize: 13, fontWeight: 600 }}>
                    {stats.maxProfit.toFixed(2)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: MUTED, fontSize: 12 }}>Max Loss</span>
                  <span style={{ color: '#EF4444', fontFamily: MONO, fontSize: 13, fontWeight: 600 }}>
                    {stats.maxLoss.toFixed(2)}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: MUTED, fontSize: 12 }}>Breakevens</span>
                  <span style={{ color: TEXT, fontFamily: MONO, fontSize: 13 }}>
                    {stats.breakevens.length > 0 ? stats.breakevens.map(b => b.toFixed(1)).join(', ') : 'None'}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: MUTED, fontSize: 12 }}>Risk/Reward</span>
                  <span style={{ color: AMBER, fontFamily: MONO, fontSize: 13 }}>
                    {stats.maxLoss !== 0 ? Math.abs(stats.maxProfit / stats.maxLoss).toFixed(2) : 'Inf'}
                  </span>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Right: Chart */}
        <Card title="Payoff Diagram" subtitle={activePreset || 'Custom formula'}>
          <div style={{ height: 480 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={payoffData} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                <XAxis
                  dataKey="spot"
                  stroke={MUTED}
                  tick={{ fill: MUTED, fontSize: 11, fontFamily: MONO }}
                  label={{ value: 'Spot Price', position: 'insideBottom', offset: -10, fill: MUTED, fontSize: 11 }}
                />
                <YAxis
                  stroke={MUTED}
                  tick={{ fill: MUTED, fontSize: 11, fontFamily: MONO }}
                  label={{ value: 'P&L', angle: -90, position: 'insideLeft', fill: MUTED, fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{ background: ELEVATED, border: `1px solid ${AMBER}`, borderRadius: 6, fontFamily: MONO, fontSize: 12 }}
                  labelStyle={{ color: MUTED }}
                  itemStyle={{ color: AMBER }}
                  formatter={(v: any) => [Number(v).toFixed(2), 'P&L']}
                  labelFormatter={(v: any) => `Spot: ${v}`}
                />
                <ReferenceLine y={0} stroke={MUTED} strokeDasharray="3 3" />
                <ReferenceLine x={params.strike1} stroke="rgba(245,158,11,0.4)" strokeDasharray="5 5" label={{ value: 'K1', fill: MUTED, fontSize: 10 }} />
                <ReferenceLine x={params.strike2} stroke="rgba(245,158,11,0.4)" strokeDasharray="5 5" label={{ value: 'K2', fill: MUTED, fontSize: 10 }} />
                <ReferenceLine x={params.spot} stroke="rgba(16,185,129,0.4)" strokeDasharray="5 5" label={{ value: 'Spot', fill: '#10B981', fontSize: 10 }} />
                <Line type="monotone" dataKey="payoff" stroke={AMBER} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  )
}
