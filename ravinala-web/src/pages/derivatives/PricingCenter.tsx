/**
 * PricingCenter.tsx
 * Derivatives pricing calculator — Black-Scholes, Greeks, Payoff Chart, Sensitivity Table.
 * All calculations are client-side via usePricing (no backend required for pricing).
 * Term-sheet generation calls POST /api/v1/generate/termsheet.
 */

import { useState, useMemo, useCallback, useEffect } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { blackScholesPrice, blackScholesGreeks } from '../../hooks/usePricing'
import { Card, Badge } from '../../components/ui/index'
import api from '../../api/client'
import { useSnapshot } from '../../hooks/useMarketData'

// ─── Types ─────────────────────────────────────────────────────────────────────

type OptionType = 'call' | 'put'
type MCSimCount = 1000 | 10000 | 100000

interface Inputs {
  ticker: string
  S: number
  type: OptionType
  K: number
  T: number       // years
  r: number       // percent e.g. 5 → 0.05 internally
  sigma: number   // percent e.g. 20 → 0.20 internally
  q: number       // dividend yield percent
}

interface MCState {
  open: boolean
  simCount: MCSimCount
  timeSteps: number
  running: boolean
  result: number | null
}

// ─── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number, digits = 4): string {
  if (!isFinite(n)) return '—'
  return n.toFixed(digits)
}

function fmtSigned(n: number, digits = 4): string {
  if (!isFinite(n)) return '—'
  const s = n.toFixed(digits)
  return n > 0 ? `+${s}` : s
}

/** Convert years → human-readable days / weeks. */
function yearsToCalendar(T: number): string {
  const days = Math.round(T * 365)
  const weeks = Math.round(T * 52)
  return `~${days} day${days !== 1 ? 's' : ''} / ~${weeks} week${weeks !== 1 ? 's' : ''}`
}

/**
 * Naive Monte-Carlo pricer (GBM, no dividends correction for simplicity).
 * Runs synchronously — acceptable for up to 100 k paths at 252 steps.
 */
function runMonteCarlo(
  S: number,
  K: number,
  T: number,
  r: number,
  sigma: number,
  type: OptionType,
  simCount: number,
  timeSteps: number,
): number {
  if (T <= 0 || sigma <= 0) {
    return type === 'call' ? Math.max(S - K, 0) : Math.max(K - S, 0)
  }
  const dt = T / timeSteps
  const drift = (r - 0.5 * sigma * sigma) * dt
  const diffusion = sigma * Math.sqrt(dt)
  let payoffSum = 0
  for (let i = 0; i < simCount; i++) {
    let spot = S
    for (let t = 0; t < timeSteps; t++) {
      // Box-Muller for standard normal
      const u1 = Math.random() || 1e-12
      const u2 = Math.random() || 1e-12
      const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)
      spot *= Math.exp(drift + diffusion * z)
    }
    payoffSum += type === 'call' ? Math.max(spot - K, 0) : Math.max(K - spot, 0)
  }
  return Math.exp(-r * T) * (payoffSum / simCount)
}

// ─── Sub-components ─────────────────────────────────────────────────────────────

interface SectionHeaderProps {
  label: string
  accent?: string
}
function SectionHeader({ label, accent = '#00D9FF' }: SectionHeaderProps) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <span
        style={{
          display: 'inline-block',
          width: 3,
          height: 14,
          borderRadius: 2,
          backgroundColor: accent,
          flexShrink: 0,
        }}
      />
      <span
        className="text-xs font-semibold uppercase tracking-widest"
        style={{ color: '#94A3B8', letterSpacing: '0.12em' }}
      >
        {label}
      </span>
    </div>
  )
}

interface NumberInputProps {
  label: string
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
  step?: number
  suffix?: string
}
function NumberInput({ label, value, onChange, min, max, step = 1, suffix }: NumberInputProps) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs" style={{ color: '#64748B' }}>
        {label}
      </label>
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={e => {
            const v = parseFloat(e.target.value)
            if (isFinite(v)) onChange(v)
          }}
          className="w-full rounded px-2 py-1.5 text-sm font-mono outline-none"
          style={{
            backgroundColor: '#0A0E1A',
            border: '1px solid rgba(51,65,85,0.5)',
            color: '#F1F5F9',
          }}
          onFocus={e => {
            e.currentTarget.style.borderColor = 'rgba(0,217,255,0.5)'
          }}
          onBlur={e => {
            e.currentTarget.style.borderColor = 'rgba(51,65,85,0.5)'
          }}
        />
        {suffix && (
          <span className="text-xs shrink-0" style={{ color: '#64748B' }}>
            {suffix}
          </span>
        )}
      </div>
    </div>
  )
}

interface GreekCardProps {
  label: string
  value: number
  description: string
  color: string
  digits?: number
  signed?: boolean
}
function GreekCard({ label, value, description, color, digits = 6, signed = false }: GreekCardProps) {
  const display = signed ? fmtSigned(value, digits) : fmt(value, digits)
  return (
    <div
      className="rounded-lg p-3 flex flex-col gap-1"
      style={{
        backgroundColor: '#0A0E1A',
        border: `1px solid ${color}30`,
      }}
    >
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-lg font-bold" style={{ color }}>
          {display}
        </span>
        <span
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: '#94A3B8' }}
        >
          {label}
        </span>
      </div>
      <span className="text-xs leading-snug" style={{ color: '#475569' }}>
        {description}
      </span>
    </div>
  )
}

// ─── Payoff chart data builder ─────────────────────────────────────────────────

interface ChartPoint {
  spot: number
  payoff: number
  value: number
}

function buildChartData(
  S: number,
  K: number,
  T: number,
  r: number,
  sigma: number,
  q: number,
  type: OptionType,
  entryPrice: number,
): ChartPoint[] {
  const points: ChartPoint[] = []
  const lo = S * 0.5
  const hi = S * 1.5
  const steps = 80
  const step = (hi - lo) / steps
  // adjust r for dividend yield in pricing
  const rAdj = r - q
  for (let i = 0; i <= steps; i++) {
    const spot = lo + i * step
    // Payoff at maturity (intrinsic) minus entry cost → P&L
    const intrinsic = type === 'call' ? Math.max(spot - K, 0) : Math.max(K - spot, 0)
    const payoff = intrinsic - entryPrice
    // Current theoretical value at this spot level minus entry cost → P&L
    const currentVal = blackScholesPrice(spot, K, T, rAdj, sigma, type) - entryPrice
    points.push({ spot: parseFloat(spot.toFixed(2)), payoff, value: currentVal })
  }
  return points
}

// ─── Sensitivity table ─────────────────────────────────────────────────────────

/** 3 vol levels × 5 spot levels grid */
function buildSensitivityTable(
  S: number,
  K: number,
  T: number,
  r: number,
  sigma: number,
  type: OptionType,
) {
  const volOffsets = [-0.1, 0, 0.1] // ±10% from base vol
  const spotMultipliers = [0.85, 0.925, 1.0, 1.075, 1.15]
  return {
    vols: volOffsets.map(dv => sigma + dv),
    spots: spotMultipliers.map(m => S * m),
    prices: volOffsets.map(dv => {
      const v = Math.max(sigma + dv, 0.001)
      return spotMultipliers.map(m => {
        const s = S * m
        return blackScholesPrice(s, K, T, r, v, type)
      })
    }),
  }
}

// ─── Term-sheet handler ────────────────────────────────────────────────────────

async function fetchTermSheet(inputs: Inputs, bsPrice: number): Promise<void> {
  const payload = {
    product_type: `European ${inputs.type === 'call' ? 'Call' : 'Put'} Option`,
    product_name: `${inputs.ticker} ${inputs.type.toUpperCase()} K=${inputs.K} T=${inputs.T}Y`,
    underlying: inputs.ticker,
    strike: inputs.K,
    maturity: `${inputs.T}Y`,
    notional: 1000000,
    currency: 'USD',
    notes: `BS Price: ${fmt(bsPrice, 4)} | σ=${inputs.sigma}% | r=${inputs.r}% | q=${inputs.q}%`,
  }
  const response = await api.post('/v1/generate/termsheet', payload, {
    responseType: 'blob',
  })
  const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `termsheet_${inputs.ticker}_${inputs.type}_K${inputs.K}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}

// ─── Main component ─────────────────────────────────────────────────────────────

const AMBER = '#F59E0B'
const CYAN  = '#00D9FF'
const BG    = '#0A0E1A'
const SURF  = '#131823'

export default function PricingCenter() {
  // ── Live market data ────────────────────────────────────────────────────────
  const { data: snapshot, isLoading: snapshotLoading } = useSnapshot()
  const usingFallback = !snapshot

  // ── Inputs state ─────────────────────────────────────────────────────────────
  const [inputs, setInputs] = useState<Inputs>({
    ticker: 'AAPL',
    S: 100,
    type: 'call',
    K: 100,
    T: 1.0,
    r: 5,
    sigma: 20,
    q: 0,
  })

  // Auto-populate spot price from live data when available
  useEffect(() => {
    if (!snapshot) return
    const allIndices = Object.values(snapshot.indices).flat()
    const match = allIndices.find(
      (idx) => idx.symbol.toUpperCase() === inputs.ticker.toUpperCase(),
    )
    if (match) {
      setInputs((prev) => ({ ...prev, S: match.price }))
    }
  }, [snapshot, inputs.ticker])

  // ── Monte Carlo state ─────────────────────────────────────────────────────────
  const [mc, setMC] = useState<MCState>({
    open: false,
    simCount: 10000,
    timeSteps: 252,
    running: false,
    result: null,
  })

  // ── Term-sheet state ──────────────────────────────────────────────────────────
  const [tsLoading, setTsLoading] = useState(false)
  const [tsError, setTsError] = useState<string | null>(null)

  // ── Derived pricing (live, memoised) ─────────────────────────────────────────
  const { bsPrice, greeks, intrinsic, timeValue } = useMemo(() => {
    const r = inputs.r / 100
    const sigma = inputs.sigma / 100
    const q = inputs.q / 100
    const rAdj = Math.max(r - q, -10) // dividend-adjusted rate
    const T = Math.max(inputs.T, 0)

    const price = blackScholesPrice(inputs.S, inputs.K, T, rAdj, sigma, inputs.type)
    const gks = blackScholesGreeks(inputs.S, inputs.K, T, rAdj, sigma, inputs.type)

    const intr =
      inputs.type === 'call'
        ? Math.max(inputs.S - inputs.K, 0)
        : Math.max(inputs.K - inputs.S, 0)
    const tv = Math.max(price - intr, 0)

    return { bsPrice: price, greeks: gks, intrinsic: intr, timeValue: tv }
  }, [inputs])

  // ── Payoff chart data ─────────────────────────────────────────────────────────
  const chartData = useMemo(
    () =>
      buildChartData(
        inputs.S,
        inputs.K,
        Math.max(inputs.T, 0),
        inputs.r / 100,
        inputs.sigma / 100,
        inputs.q / 100,
        inputs.type,
        bsPrice,
      ),
    [inputs, bsPrice],
  )

  // ── Sensitivity table ─────────────────────────────────────────────────────────
  const sensitivity = useMemo(
    () =>
      buildSensitivityTable(
        inputs.S,
        inputs.K,
        Math.max(inputs.T, 0),
        inputs.r / 100,
        inputs.sigma / 100,
        inputs.type,
      ),
    [inputs],
  )

  // ── Handlers ──────────────────────────────────────────────────────────────────
  const set = useCallback(
    <K extends keyof Inputs>(key: K, value: Inputs[K]) =>
      setInputs(prev => ({ ...prev, [key]: value })),
    [],
  )

  const handleRunMC = useCallback(() => {
    setMC(prev => ({ ...prev, running: true, result: null }))
    // Use setTimeout so the running state renders before the heavy loop
    setTimeout(() => {
      const result = runMonteCarlo(
        inputs.S,
        inputs.K,
        Math.max(inputs.T, 0),
        inputs.r / 100,
        inputs.sigma / 100,
        inputs.type,
        mc.simCount,
        mc.timeSteps,
      )
      setMC(prev => ({ ...prev, running: false, result }))
    }, 20)
  }, [inputs, mc.simCount, mc.timeSteps])

  const handleTermSheet = useCallback(async () => {
    setTsLoading(true)
    setTsError(null)
    try {
      await fetchTermSheet(inputs, bsPrice)
    } catch {
      setTsError('Term-sheet generation failed. Is the backend running?')
    } finally {
      setTsLoading(false)
    }
  }, [inputs, bsPrice])

  // ── Delta color helper ────────────────────────────────────────────────────────
  const deltaColor = useMemo(() => {
    const abs = Math.abs(greeks.delta)
    if (abs < 0.2) return '#64748B'
    if (abs < 0.5) return '#94A3B8'
    if (abs < 0.8) return '#10B981'
    return '#00D9FF'
  }, [greeks.delta])

  // ─── Tooltip formatter ───────────────────────────────────────────────────────
  const tooltipFormatter = useCallback(
    (value: number, name: string) => [
      `${value >= 0 ? '+' : ''}${value.toFixed(4)}`,
      name === 'value' ? 'Current Value P&L' : 'Maturity Payoff P&L',
    ],
    [],
  )

  const inputPanelStyle: React.CSSProperties = {
    backgroundColor: SURF,
    border: '1px solid rgba(51,65,85,0.4)',
    borderRadius: 12,
    padding: 20,
  }

  const labelStyle: React.CSSProperties = { color: '#64748B', fontSize: 12 }

  const inputStyle: React.CSSProperties = {
    backgroundColor: BG,
    border: '1px solid rgba(51,65,85,0.5)',
    color: '#F1F5F9',
    borderRadius: 6,
    padding: '6px 10px',
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 13,
    outline: 'none',
    width: '100%',
  }

  const radioButtonStyle = (active: boolean, accent: string): React.CSSProperties => ({
    padding: '6px 16px',
    borderRadius: 6,
    border: `1px solid ${active ? accent : 'rgba(51,65,85,0.4)'}`,
    backgroundColor: active ? `${accent}22` : 'transparent',
    color: active ? accent : '#64748B',
    fontSize: 13,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s',
  })

  const dividerStyle: React.CSSProperties = {
    border: 'none',
    borderTop: '1px solid rgba(51,65,85,0.3)',
    margin: '16px 0',
  }

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: BG,
        color: '#F1F5F9',
        fontFamily: 'Inter, system-ui, sans-serif',
        padding: '24px 20px',
      }}
    >
      {/* ── Fallback Banner ── */}
      {usingFallback && !snapshotLoading && (
        <div style={{
          backgroundColor: 'rgba(245,158,11,0.1)',
          border: '1px solid rgba(245,158,11,0.3)',
          borderRadius: 6,
          padding: '8px 16px',
          marginBottom: 16,
          color: '#F59E0B',
          fontSize: 13,
          fontFamily: 'JetBrains Mono, monospace',
        }}>
          Backend unreachable — showing demo data
        </div>
      )}

      {/* ── Page Header ── */}
      <div style={{ marginBottom: 24 }}>
        <div className="flex items-center gap-3 mb-1">
          <span
            style={{
              fontSize: 22,
              fontFamily: 'JetBrains Mono, monospace',
              fontWeight: 700,
              color: AMBER,
            }}
          >
            ◈
          </span>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              fontFamily: 'JetBrains Mono, monospace',
              color: '#F1F5F9',
              margin: 0,
            }}
          >
            Pricing Center
          </h1>
          <Badge variant="warning">Derivatives</Badge>
          <Badge variant="info">Black-Scholes</Badge>
        </div>
        <p style={{ color: '#64748B', fontSize: 13, margin: 0 }}>
          Real-time European option pricing · client-side Black-Scholes-Merton
        </p>
      </div>

      {/* ── Two-column layout ── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(300px, 360px) 1fr',
          gap: 20,
          alignItems: 'start',
        }}
      >
        {/* ══════════════════════════ LEFT PANEL — INPUTS ══════════════════════════ */}
        <div style={{ position: 'sticky', top: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Section 1: Underlying */}
          <div style={inputPanelStyle}>
            <SectionHeader label="Underlying" accent={CYAN} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {/* Ticker */}
              <div>
                <label style={labelStyle}>Ticker</label>
                <input
                  type="text"
                  value={inputs.ticker}
                  onChange={e => set('ticker', e.target.value.toUpperCase())}
                  placeholder="AAPL"
                  style={{ ...inputStyle, marginTop: 4, textTransform: 'uppercase' }}
                  onFocus={e => { e.currentTarget.style.borderColor = `${CYAN}80` }}
                  onBlur={e => { e.currentTarget.style.borderColor = 'rgba(51,65,85,0.5)' }}
                />
              </div>

              {/* Spot price + fetch button */}
              <div>
                <label style={labelStyle}>Spot price S</label>
                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <input
                    type="number"
                    value={inputs.S}
                    min={0.01}
                    step={0.5}
                    onChange={e => {
                      const v = parseFloat(e.target.value)
                      if (isFinite(v) && v > 0) set('S', v)
                    }}
                    style={inputStyle}
                    onFocus={e => { e.currentTarget.style.borderColor = `${CYAN}80` }}
                    onBlur={e => { e.currentTarget.style.borderColor = 'rgba(51,65,85,0.5)' }}
                  />
                  <button
                    title="Live price fetch (backend required)"
                    onClick={() => alert('Live fetch requires the backend to be running.')}
                    style={{
                      flexShrink: 0,
                      padding: '6px 12px',
                      borderRadius: 6,
                      border: `1px solid ${AMBER}40`,
                      backgroundColor: `${AMBER}15`,
                      color: AMBER,
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    ↻ Live
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Option Parameters */}
          <div style={inputPanelStyle}>
            <SectionHeader label="Option Parameters" accent={AMBER} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {/* Call / Put */}
              <div>
                <label style={labelStyle}>Type</label>
                <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
                  {(['call', 'put'] as OptionType[]).map(t => (
                    <button
                      key={t}
                      onClick={() => set('type', t)}
                      style={radioButtonStyle(inputs.type === t, inputs.type === t && t === 'call' ? CYAN : AMBER)}
                    >
                      {t.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              <hr style={dividerStyle} />

              {/* Strike */}
              <NumberInput
                label="Strike K"
                value={inputs.K}
                onChange={v => set('K', v)}
                min={0.01}
                step={0.5}
              />

              {/* Maturity slider */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <label style={labelStyle}>Maturity T (years)</label>
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 13,
                      color: CYAN,
                      fontWeight: 600,
                    }}
                  >
                    {inputs.T.toFixed(2)}Y
                  </span>
                </div>
                <input
                  type="range"
                  min={0.01}
                  max={5}
                  step={0.01}
                  value={inputs.T}
                  onChange={e => set('T', parseFloat(e.target.value))}
                  style={{ width: '100%', accentColor: CYAN, cursor: 'pointer' }}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3 }}>
                  <span style={{ fontSize: 10, color: '#475569' }}>0.01Y</span>
                  <span style={{ fontSize: 11, color: '#64748B', fontStyle: 'italic' }}>
                    {yearsToCalendar(inputs.T)}
                  </span>
                  <span style={{ fontSize: 10, color: '#475569' }}>5Y</span>
                </div>
              </div>

              <hr style={dividerStyle} />

              {/* Risk-free rate, vol, dividend yield */}
              <NumberInput
                label="Risk-free rate r"
                value={inputs.r}
                onChange={v => set('r', v)}
                min={-10}
                max={50}
                step={0.1}
                suffix="%"
              />
              <NumberInput
                label="Volatility σ"
                value={inputs.sigma}
                onChange={v => set('sigma', Math.max(v, 0))}
                min={0}
                max={300}
                step={0.5}
                suffix="%"
              />
              <NumberInput
                label="Dividend yield q"
                value={inputs.q}
                onChange={v => set('q', Math.max(v, 0))}
                min={0}
                max={50}
                step={0.1}
                suffix="%"
              />
            </div>
          </div>

          {/* Section 3: Monte Carlo (collapsible) */}
          <div style={inputPanelStyle}>
            <button
              onClick={() => setMC(prev => ({ ...prev, open: !prev.open }))}
              style={{
                width: '100%',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <SectionHeader label="Monte Carlo" accent="#A855F7" />
              <span style={{ color: '#64748B', fontSize: 16, marginTop: -12 }}>
                {mc.open ? '▲' : '▼'}
              </span>
            </button>

            {mc.open && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 4 }}>
                {/* Simulation count */}
                <div>
                  <label style={labelStyle}>Simulations</label>
                  <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
                    {([1000, 10000, 100000] as MCSimCount[]).map(n => (
                      <button
                        key={n}
                        onClick={() => setMC(prev => ({ ...prev, simCount: n }))}
                        style={radioButtonStyle(mc.simCount === n, '#A855F7')}
                      >
                        {n >= 100000 ? '100k' : n >= 10000 ? '10k' : '1k'}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Time steps */}
                <NumberInput
                  label="Time steps"
                  value={mc.timeSteps}
                  onChange={v => setMC(prev => ({ ...prev, timeSteps: Math.max(Math.round(v), 1) }))}
                  min={1}
                  max={1000}
                  step={1}
                />

                {/* Run button */}
                <button
                  onClick={handleRunMC}
                  disabled={mc.running}
                  style={{
                    padding: '8px 0',
                    borderRadius: 8,
                    border: `1px solid #A855F760`,
                    backgroundColor: mc.running ? '#A855F720' : '#A855F730',
                    color: '#A855F7',
                    fontWeight: 700,
                    fontSize: 13,
                    cursor: mc.running ? 'not-allowed' : 'pointer',
                    transition: 'background 0.15s',
                  }}
                >
                  {mc.running ? '⟳ Running…' : '▶ Run Monte Carlo'}
                </button>

                {mc.result !== null && !mc.running && (
                  <div
                    style={{
                      borderRadius: 8,
                      padding: '10px 12px',
                      backgroundColor: '#A855F715',
                      border: '1px solid #A855F730',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 2,
                    }}
                  >
                    <span style={{ fontSize: 11, color: '#A855F7', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                      MC Price
                    </span>
                    <span
                      style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 22, fontWeight: 700, color: '#A855F7' }}
                    >
                      {fmt(mc.result, 4)}
                    </span>
                    <span style={{ fontSize: 11, color: '#64748B' }}>
                      Δ vs BS: {fmtSigned(mc.result - bsPrice, 4)} ({mc.simCount.toLocaleString()} paths · {mc.timeSteps} steps)
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ══════════════════════════ RIGHT PANEL — RESULTS ══════════════════════════ */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Section 1: Option Price */}
          <Card>
            <SectionHeader label="Option Price" accent={CYAN} />
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginBottom: 12 }}>
              <span
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 48,
                  fontWeight: 700,
                  color: CYAN,
                  lineHeight: 1,
                }}
              >
                {fmt(bsPrice, 4)}
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Badge variant={inputs.type === 'call' ? 'info' : 'warning'}>
                  {inputs.type.toUpperCase()}
                </Badge>
                <span style={{ fontSize: 12, color: '#64748B' }}>Black-Scholes</span>
              </div>
            </div>

            {/* Intrinsic / Time value bar */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 10,
                padding: '12px 0',
                borderTop: '1px solid rgba(51,65,85,0.3)',
              }}
            >
              <div>
                <span style={{ fontSize: 11, color: '#64748B', display: 'block', marginBottom: 2 }}>
                  Intrinsic Value
                </span>
                <span
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 18,
                    fontWeight: 600,
                    color: intrinsic > 0 ? '#10B981' : '#475569',
                  }}
                >
                  {fmt(intrinsic, 4)}
                </span>
              </div>
              <div>
                <span style={{ fontSize: 11, color: '#64748B', display: 'block', marginBottom: 2 }}>
                  Time Value
                </span>
                <span
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 18,
                    fontWeight: 600,
                    color: AMBER,
                  }}
                >
                  {fmt(timeValue, 4)}
                </span>
              </div>
            </div>

            {/* Value breakdown bar */}
            {bsPrice > 0 && (
              <div style={{ marginTop: 4 }}>
                <div
                  style={{
                    height: 6,
                    borderRadius: 3,
                    backgroundColor: 'rgba(51,65,85,0.3)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.min((intrinsic / bsPrice) * 100, 100)}%`,
                      backgroundColor: '#10B981',
                      borderRadius: 3,
                    }}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3 }}>
                  <span style={{ fontSize: 10, color: '#10B981' }}>
                    Intrinsic {((intrinsic / bsPrice) * 100).toFixed(1)}%
                  </span>
                  <span style={{ fontSize: 10, color: AMBER }}>
                    Time {((timeValue / bsPrice) * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            )}

            {inputs.T <= 0 && (
              <div
                style={{
                  marginTop: 8,
                  padding: '6px 10px',
                  borderRadius: 6,
                  backgroundColor: '#EF444415',
                  border: '1px solid #EF444430',
                  fontSize: 12,
                  color: '#EF4444',
                }}
              >
                T = 0: showing intrinsic value only — option is at/past expiry.
              </div>
            )}
          </Card>

          {/* Section 2: Greeks */}
          <Card>
            <SectionHeader label="Greeks" accent={AMBER} />
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 10,
              }}
            >
              <GreekCard
                label="Delta"
                value={greeks.delta}
                description="∂Price/∂Spot — hedge ratio"
                color={deltaColor}
                digits={4}
              />
              <GreekCard
                label="Gamma"
                value={greeks.gamma}
                description="∂²Price/∂Spot² — convexity"
                color={AMBER}
                digits={6}
              />
              <GreekCard
                label="Vega"
                value={greeks.vega}
                description="per 1% vol change"
                color="#A855F7"
                digits={4}
              />
              <GreekCard
                label="Theta"
                value={greeks.theta}
                description="per calendar day"
                color="#EF4444"
                digits={4}
                signed
              />
              <GreekCard
                label="Rho"
                value={greeks.rho}
                description="per 1bp rate change"
                color="#3B82F6"
                digits={6}
                signed
              />
              <GreekCard
                label="Vanna"
                value={greeks.gamma * inputs.S * (inputs.sigma / 100)}
                description="∂Delta/∂σ (approx)"
                color="#64748B"
                digits={6}
              />
            </div>
          </Card>

          {/* Section 3: Payoff Chart */}
          <Card>
            <SectionHeader label="Payoff Chart" accent={CYAN} />
            <div style={{ marginBottom: 8, fontSize: 12, color: '#64748B' }}>
              P&L vs spot price at entry (50%–150% of current spot ={' '}
              <span style={{ color: CYAN, fontFamily: 'JetBrains Mono, monospace' }}>
                {inputs.S.toFixed(2)}
              </span>
              )
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                <XAxis
                  dataKey="spot"
                  stroke="#475569"
                  tick={{ fill: '#64748B', fontSize: 11 }}
                  tickFormatter={v => `${v.toFixed(0)}`}
                  label={{ value: 'Spot', position: 'insideRight', fill: '#64748B', fontSize: 11, dx: 4 }}
                />
                <YAxis
                  stroke="#475569"
                  tick={{ fill: '#64748B', fontSize: 11 }}
                  tickFormatter={v => v.toFixed(2)}
                  width={52}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: SURF,
                    border: '1px solid rgba(51,65,85,0.5)',
                    borderRadius: 8,
                    fontSize: 12,
                    fontFamily: 'JetBrains Mono, monospace',
                  }}
                  labelStyle={{ color: '#94A3B8' }}
                  formatter={tooltipFormatter as never}
                />
                <Legend
                  wrapperStyle={{ fontSize: 12, color: '#94A3B8' }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={CYAN}
                  dot={false}
                  strokeWidth={2}
                  name="Current Value P&L"
                />
                <Line
                  type="monotone"
                  dataKey="payoff"
                  stroke={AMBER}
                  dot={false}
                  strokeWidth={2}
                  strokeDasharray="5 3"
                  name="Maturity Payoff P&L"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          {/* Section 4: Sensitivity Table */}
          <Card>
            <SectionHeader label="Sensitivity Table" accent="#A855F7" />
            <div style={{ fontSize: 12, color: '#64748B', marginBottom: 10 }}>
              BS price across spot (±15%) × volatility (±10% absolute)
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr>
                    <th
                      style={{
                        textAlign: 'left',
                        padding: '6px 10px',
                        color: '#64748B',
                        borderBottom: '1px solid rgba(51,65,85,0.4)',
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      σ \ Spot
                    </th>
                    {sensitivity.spots.map(s => (
                      <th
                        key={s}
                        style={{
                          textAlign: 'right',
                          padding: '6px 10px',
                          color: Math.abs(s - inputs.S) < 0.5 ? CYAN : '#64748B',
                          borderBottom: '1px solid rgba(51,65,85,0.4)',
                          fontFamily: 'JetBrains Mono, monospace',
                          fontWeight: Math.abs(s - inputs.S) < 0.5 ? 700 : 500,
                        }}
                      >
                        {s.toFixed(1)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sensitivity.vols.map((vol, vi) => (
                    <tr
                      key={vol}
                      style={{
                        backgroundColor: vi % 2 === 0 ? 'rgba(255,255,255,0.015)' : 'transparent',
                      }}
                    >
                      <td
                        style={{
                          padding: '5px 10px',
                          color: Math.abs(vol - inputs.sigma / 100) < 0.001 ? AMBER : '#64748B',
                          fontFamily: 'JetBrains Mono, monospace',
                          borderBottom: '1px solid rgba(51,65,85,0.2)',
                          fontWeight: Math.abs(vol - inputs.sigma / 100) < 0.001 ? 700 : 400,
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {(vol * 100).toFixed(0)}%
                      </td>
                      {sensitivity.prices[vi].map((price, si) => {
                        const isCurrentCell =
                          Math.abs(sensitivity.spots[si] - inputs.S) < 0.5 &&
                          Math.abs(vol - inputs.sigma / 100) < 0.001
                        return (
                          <td
                            key={si}
                            style={{
                              textAlign: 'right',
                              padding: '5px 10px',
                              fontFamily: 'JetBrains Mono, monospace',
                              color: isCurrentCell ? CYAN : '#94A3B8',
                              fontWeight: isCurrentCell ? 700 : 400,
                              borderBottom: '1px solid rgba(51,65,85,0.2)',
                              backgroundColor: isCurrentCell ? `${CYAN}12` : 'transparent',
                            }}
                          >
                            {fmt(price, 3)}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Section 5: Generate Term Sheet */}
          <Card>
            <SectionHeader label="Export" accent={AMBER} />
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 12,
              }}
            >
              <div>
                <p style={{ margin: 0, fontSize: 13, color: '#94A3B8' }}>
                  Generate a PDF term-sheet for the current option structure.
                </p>
                {tsError && (
                  <p style={{ margin: '4px 0 0', fontSize: 12, color: '#EF4444' }}>{tsError}</p>
                )}
              </div>
              <button
                onClick={handleTermSheet}
                disabled={tsLoading}
                style={{
                  padding: '10px 24px',
                  borderRadius: 8,
                  border: `1px solid ${AMBER}60`,
                  backgroundColor: tsLoading ? `${AMBER}20` : `${AMBER}25`,
                  color: AMBER,
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: tsLoading ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                  whiteSpace: 'nowrap',
                }}
                onMouseEnter={e => {
                  if (!tsLoading) e.currentTarget.style.backgroundColor = `${AMBER}35`
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.backgroundColor = tsLoading ? `${AMBER}20` : `${AMBER}25`
                }}
              >
                {tsLoading ? '⟳ Generating…' : '⬇ Generate Term Sheet (PDF)'}
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
