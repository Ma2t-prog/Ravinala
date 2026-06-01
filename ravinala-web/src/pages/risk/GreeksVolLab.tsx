/**
 * GreeksVolLab.tsx
 * Fusion of Greeks.tsx and VolCalibration.tsx
 * Tabs: "Greeks Sensitivity" | "Vol Calibration"
 */

import { useState, useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import { Card, Badge } from '../../components/ui/index'
import { Tabs } from '../../components/ui/Tabs'
import {
  blackScholesPrice,
  blackScholesGreeks,
} from '../../hooks/usePricing'
import { useSnapshot } from '../../hooks/useMarketData'

// ─── Greeks colour palette ─────────────────────────────────────────────────────

const AMBER   = '#F59E0B'
const GREEN   = '#10B981'
const RED     = '#EF4444'
const PURPLE  = '#A78BFA'
const BLUE    = '#3B82F6'
const SLATE   = '#94A3B8'
const BG_PAGE = '#0B0F1A'
const BORDER  = 'rgba(51,65,85,0.3)'
const BG_CARD = '#131823'

// ─── VolCalibration theme ─────────────────────────────────────────────────────

const VC = {
  bg: '#0A0E1A',
  surface: '#131823',
  elevated: '#1A2332',
  text: '#F1F5F9',
  muted: '#94A3B8',
  red: '#EF4444',
  accent: '#EF4444',
  border: 'rgba(51,65,85,0.3)',
} as const

const vcInputStyle: React.CSSProperties = {
  backgroundColor: VC.elevated,
  border: `1px solid ${VC.border}`,
  borderRadius: 6,
  padding: '6px 10px',
  color: VC.text,
  fontSize: 13,
  width: '100%',
  outline: 'none',
  fontFamily: 'JetBrains Mono, monospace',
}

const vcLabelStyle: React.CSSProperties = {
  color: VC.muted,
  fontSize: 11,
  fontWeight: 600,
  textTransform: 'uppercase' as const,
  letterSpacing: '0.05em',
  marginBottom: 4,
  display: 'block',
}

const vcBtnStyle: React.CSSProperties = {
  background: `linear-gradient(135deg, ${VC.red}, #DC2626)`,
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '8px 20px',
  fontWeight: 600,
  fontSize: 13,
  cursor: 'pointer',
  fontFamily: 'JetBrains Mono, monospace',
}

// ─── Shared helpers ───────────────────────────────────────────────────────────

function normPDF(x: number): number {
  return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI)
}

function computeVanna(S: number, K: number, T: number, r: number, sigma: number): number {
  if (T <= 0 || sigma <= 0) return 0
  const sqrtT = Math.sqrt(T)
  const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
  const d2 = d1 - sigma * sqrtT
  return (-normPDF(d1) * d2) / (sigma * 100)
}

function computeVolga(S: number, K: number, T: number, r: number, sigma: number): number {
  if (T <= 0 || sigma <= 0) return 0
  const sqrtT = Math.sqrt(T)
  const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
  const d2 = d1 - sigma * sqrtT
  const vegaRaw = S * normPDF(d1) * sqrtT
  return (vegaRaw * d1 * d2) / (sigma * 10_000)
}

function fmt(v: number, decimals = 4): string {
  if (!isFinite(v)) return '—'
  return `${v.toFixed(decimals)}`
}

function fmtPct(v: number): string {
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

/** Parametric smile: σ(K) = σ_ATM + a*(K/S - 1)^2 + b*(K/S - 1) */
function smileVol(S: number, K: number, sigmaATM: number, a: number, b: number): number {
  const m = K / S - 1
  return sigmaATM + a * m * m + b * m
}

function volToColor(vol: number, minVol: number, maxVol: number): string {
  const t = maxVol > minVol ? (vol - minVol) / (maxVol - minVol) : 0.5
  const r = Math.round(30 + t * 209)
  const g = Math.round(40 + (1 - Math.abs(t - 0.5) * 2) * 60)
  const b2 = Math.round(180 - t * 150)
  return `rgb(${r},${g},${b2})`
}

const MATURITIES = [
  { label: '1M', T: 1 / 12 },
  { label: '3M', T: 3 / 12 },
  { label: '6M', T: 6 / 12 },
  { label: '9M', T: 9 / 12 },
  { label: '1Y', T: 1 },
  { label: '18M', T: 1.5 },
  { label: '2Y', T: 2 },
]

// ─── Greeks sub-components ────────────────────────────────────────────────────

function ChartTooltip({
  active,
  payload,
  label,
  color,
  decimals = 4,
}: {
  active?: boolean
  payload?: Array<{ value: number; name?: string }>
  label?: string | number
  color: string
  decimals?: number
}) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="rounded px-3 py-2 text-xs shadow-lg"
      style={{ backgroundColor: '#1E2536', border: `1px solid ${BORDER}`, color: '#F1F5F9' }}
    >
      {label !== undefined && (
        <p className="mb-1 font-semibold" style={{ color: SLATE }}>
          S = {Number(label).toFixed(2)}
        </p>
      )}
      {payload.map((p, i) => (
        <p key={i} style={{ color }}>
          {p.name ? `${p.name}: ` : ''}
          {p.value?.toFixed(decimals)}
        </p>
      ))}
    </div>
  )
}

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <span className="h-4 w-0.5 rounded-full" style={{ backgroundColor: AMBER }} />
      <h2
        className="text-sm font-semibold uppercase tracking-wider"
        style={{ color: '#F1F5F9', fontFamily: 'JetBrains Mono, monospace' }}
      >
        {title}
      </h2>
    </div>
  )
}

function ParamSlider({
  label,
  value,
  min,
  max,
  step,
  displayValue,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  displayValue: string
  onChange: (v: number) => void
}) {
  return (
    <div className="flex flex-col gap-0.5" style={{ minWidth: 110 }}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wider" style={{ color: SLATE }}>
          {label}
        </span>
        <span className="text-xs font-mono font-semibold" style={{ color: AMBER }}>
          {displayValue}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-full"
        style={{ accentColor: AMBER, height: 4 }}
      />
    </div>
  )
}

interface GreekChartProps {
  title: string
  symbol: string
  data: Array<{ spot: number; value: number }>
  color: string
  currentSpot: number
  currentValue: number
  decimals?: number
  yDomain?: [number, number] | ['auto', 'auto']
}

function GreekChart({
  title,
  symbol,
  data,
  color,
  currentSpot,
  currentValue,
  decimals = 4,
}: GreekChartProps) {
  return (
    <div
      className="rounded-lg p-3"
      style={{ backgroundColor: BG_CARD, border: `1px solid ${BORDER}` }}
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="text-sm font-bold"
            style={{ color, fontFamily: 'JetBrains Mono, monospace' }}
          >
            {symbol} {title}
          </span>
        </div>
        <span
          className="font-mono text-sm font-semibold"
          style={{ color }}
        >
          {currentValue.toFixed(decimals)}
        </span>
      </div>
      <div style={{ height: 160 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={BORDER} />
            <XAxis
              dataKey="spot"
              tick={{ fill: SLATE, fontSize: 9 }}
              axisLine={{ stroke: BORDER }}
              tickLine={false}
              tickFormatter={v => v.toFixed(0)}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: SLATE, fontSize: 9 }}
              axisLine={false}
              tickLine={false}
              width={44}
              tickFormatter={v => v.toFixed(decimals > 3 ? 3 : decimals)}
            />
            <Tooltip
              content={props => (
                <ChartTooltip
                  active={props.active}
                  payload={props.payload as unknown as Array<{ value: number; name?: string }>}
                  label={props.label}
                  color={color}
                  decimals={decimals}
                />
              )}
            />
            <ReferenceLine
              x={currentSpot}
              stroke={SLATE}
              strokeDasharray="4 2"
              strokeOpacity={0.7}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3, fill: color }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function VolSurface({
  S,
  r,
  sigma,
  type,
}: {
  S: number
  r: number
  sigma: number
  type: 'call' | 'put'
}) {
  const strikes = useMemo(() => {
    const arr: number[] = []
    for (let k = 0.80; k <= 1.201; k += 0.04) arr.push(Math.round(S * k * 100) / 100)
    return arr
  }, [S])

  const maturities = useMemo(() => [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0], [])

  const cells = useMemo(() => {
    let maxV = 0
    let minV = Infinity
    const raw = maturities.map(T =>
      strikes.map(K => {
        const v = blackScholesPrice(S, K, T, r, sigma, type)
        if (v > maxV) maxV = v
        if (v < minV) minV = v
        return v
      })
    )
    return { raw, minV, maxV }
  }, [S, r, sigma, type, strikes, maturities])

  const cellW = 52
  const cellH = 28
  const labelW = 36
  const labelH = 20
  const svgWidth = labelW + strikes.length * cellW
  const svgHeight = labelH + maturities.length * cellH

  function interpColor(v: number) {
    const { minV, maxV } = cells
    const t = maxV > minV ? (v - minV) / (maxV - minV) : 0.5
    const r_ = Math.round(30 + t * (245 - 30))
    const g_ = Math.round(37 + t * (158 - 37))
    const b_ = Math.round(54 + t * (11 - 54))
    return `rgb(${r_},${g_},${b_})`
  }

  return (
    <div
      className="rounded-lg p-3"
      style={{ backgroundColor: BG_CARD, border: `1px solid ${BORDER}` }}
    >
      <div className="mb-2 flex items-center justify-between">
        <span
          className="text-sm font-bold"
          style={{ color: AMBER, fontFamily: 'JetBrains Mono, monospace' }}
        >
          Vol Surface
        </span>
        <span className="text-[10px]" style={{ color: SLATE }}>
          Option Value Heatmap
        </span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <svg
          width={svgWidth}
          height={svgHeight}
          style={{ display: 'block', fontFamily: 'JetBrains Mono, monospace' }}
        >
          {strikes.map((K, j) => (
            <text
              key={j}
              x={labelW + j * cellW + cellW / 2}
              y={labelH - 4}
              textAnchor="middle"
              fontSize={8}
              fill={SLATE}
            >
              {K.toFixed(0)}
            </text>
          ))}
          {maturities.map((T, i) => (
            <g key={i}>
              <text
                x={labelW - 4}
                y={labelH + i * cellH + cellH / 2 + 3}
                textAnchor="end"
                fontSize={8}
                fill={SLATE}
              >
                {T}y
              </text>
              {strikes.map((_, j) => {
                const v = cells.raw[i][j]
                const bg = interpColor(v)
                const textColor = v > (cells.maxV + cells.minV) / 2 ? '#0B0F1A' : '#F1F5F9'
                return (
                  <g key={j}>
                    <rect
                      x={labelW + j * cellW}
                      y={labelH + i * cellH}
                      width={cellW - 1}
                      height={cellH - 1}
                      fill={bg}
                      rx={2}
                    />
                    <text
                      x={labelW + j * cellW + cellW / 2}
                      y={labelH + i * cellH + cellH / 2 + 3}
                      textAnchor="middle"
                      fontSize={8}
                      fill={textColor}
                    >
                      {v.toFixed(2)}
                    </text>
                  </g>
                )
              })}
            </g>
          ))}
        </svg>
      </div>
      <div className="mt-1 flex items-center justify-between text-[10px]" style={{ color: SLATE }}>
        <span>Strike (x-axis) · Maturity (y-axis)</span>
        <div className="flex items-center gap-1">
          <span
            style={{
              width: 40,
              height: 8,
              display: 'inline-block',
              background: 'linear-gradient(to right, #1E2536, #F59E0B)',
              borderRadius: 2,
            }}
          />
          <span>low → high</span>
        </div>
      </div>
    </div>
  )
}

interface GreekRow {
  name: string
  symbol: string
  value: number
  unit: string
  description: string
  color: string
  decimals: number
}

function GreeksSummaryTable({ rows }: { rows: GreekRow[] }) {
  return (
    <table className="w-full text-xs" style={{ borderCollapse: 'collapse' }}>
      <thead>
        <tr>
          {['Greek', 'Symbol', 'Value', 'Unit', 'Description'].map(h => (
            <th
              key={h}
              className="pb-2 text-left font-medium uppercase tracking-wider"
              style={{ color: SLATE, borderBottom: `1px solid ${BORDER}` }}
            >
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr
            key={i}
            style={{ borderBottom: `1px solid ${BORDER}` }}
          >
            <td className="py-2 font-semibold" style={{ color: '#F1F5F9' }}>
              {row.name}
            </td>
            <td
              className="py-2 font-mono font-bold text-sm"
              style={{ color: row.color }}
            >
              {row.symbol}
            </td>
            <td
              className="py-2 font-mono font-semibold"
              style={{ color: row.color }}
            >
              {row.value.toFixed(row.decimals)}
            </td>
            <td className="py-2" style={{ color: SLATE }}>
              {row.unit}
            </td>
            <td className="py-2" style={{ color: SLATE }}>
              {row.description}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function PnLBar({ label, value, maxAbs, color }: { label: string; value: number; maxAbs: number; color: string }) {
  const pct = maxAbs > 0 ? Math.abs(value) / maxAbs : 0
  const isPos = value >= 0
  return (
    <div className="flex items-center gap-3 py-1">
      <span className="w-28 text-xs font-medium" style={{ color: SLATE, flexShrink: 0 }}>
        {label}
      </span>
      <div className="relative flex-1 rounded" style={{ height: 18, backgroundColor: 'rgba(51,65,85,0.2)' }}>
        <div
          className="absolute top-0 bottom-0 rounded"
          style={{
            [isPos ? 'left' : 'right']: 0,
            width: `${(pct * 50).toFixed(1)}%`,
            backgroundColor: color,
            opacity: 0.8,
          }}
        />
      </div>
      <span
        className="w-24 text-right font-mono text-xs font-semibold"
        style={{ color: isPos ? GREEN : RED, flexShrink: 0 }}
      >
        {isPos ? '+' : ''}{value.toFixed(4)}
      </span>
    </div>
  )
}

// ─── Greeks Sensitivity tab content ──────────────────────────────────────────

function GreeksSensitivityContent() {
  const [S, setS]         = useState<number>(100)
  const [K, setK]         = useState<number>(100)
  const [T, setT]         = useState<number>(0.5)
  const [sigPct, setSig]  = useState<number>(20)
  const [rPct, setR]      = useState<number>(5)
  const [optType, setOptType] = useState<'call' | 'put'>('call')

  const sigma = sigPct / 100
  const r     = rPct  / 100

  const [spotMovePct, setSpotMovePct]   = useState<number>(0)
  const [volMovePct,  setVolMovePct]    = useState<number>(0)

  const spotRange = useMemo<number[]>(() => {
    const steps = 60
    const lo = S * 0.50
    const hi = S * 1.50
    return Array.from({ length: steps + 1 }, (_, i) => lo + (i / steps) * (hi - lo))
  }, [S])

  const currentGreeks = useMemo(
    () => blackScholesGreeks(S, K, T, r, sigma, optType),
    [S, K, T, r, sigma, optType]
  )
  const currentPrice = useMemo(
    () => blackScholesPrice(S, K, T, r, sigma, optType),
    [S, K, T, r, sigma, optType]
  )

  const deltaData = useMemo(
    () => spotRange.map(s => ({
      spot: s,
      value: blackScholesGreeks(s, K, T, r, sigma, optType).delta,
    })),
    [spotRange, K, T, r, sigma, optType]
  )

  const gammaData = useMemo(
    () => spotRange.map(s => ({
      spot: s,
      value: blackScholesGreeks(s, K, T, r, sigma, optType).gamma,
    })),
    [spotRange, K, T, r, sigma, optType]
  )

  const vegaData = useMemo(
    () => spotRange.map(s => ({
      spot: s,
      value: blackScholesGreeks(s, K, T, r, sigma, optType).vega,
    })),
    [spotRange, K, T, r, sigma, optType]
  )

  const thetaData = useMemo(
    () => spotRange.map(s => ({
      spot: s,
      value: blackScholesGreeks(s, K, T, r, sigma, optType).theta,
    })),
    [spotRange, K, T, r, sigma, optType]
  )

  const rhoData = useMemo(
    () => spotRange.map(s => ({
      spot: s,
      value: blackScholesGreeks(s, K, T, r, sigma, optType).rho,
    })),
    [spotRange, K, T, r, sigma, optType]
  )

  const vanna = useMemo(() => computeVanna(S, K, T, r, sigma), [S, K, T, r, sigma])
  const volga = useMemo(() => computeVolga(S, K, T, r, sigma), [S, K, T, r, sigma])

  const summaryRows: GreekRow[] = useMemo(() => [
    {
      name: 'Delta',
      symbol: 'Δ',
      value: currentGreeks.delta,
      unit: '$/$ spot',
      description: 'Option price sensitivity to ±$1 spot move',
      color: optType === 'call' ? GREEN : RED,
      decimals: 4,
    },
    {
      name: 'Gamma',
      symbol: 'Γ',
      value: currentGreeks.gamma,
      unit: 'Δ/$ spot',
      description: 'Rate of change of Delta per $1 spot move',
      color: AMBER,
      decimals: 6,
    },
    {
      name: 'Vega',
      symbol: 'ν',
      value: currentGreeks.vega,
      unit: '$/1% vol',
      description: 'Option price change per +1% absolute vol move',
      color: PURPLE,
      decimals: 4,
    },
    {
      name: 'Theta',
      symbol: 'Θ',
      value: currentGreeks.theta,
      unit: '$/day',
      description: 'Option price decay per calendar day',
      color: RED,
      decimals: 4,
    },
    {
      name: 'Rho',
      symbol: 'ρ',
      value: currentGreeks.rho,
      unit: '$/1bp rate',
      description: 'Option price sensitivity per +1bp rate move',
      color: BLUE,
      decimals: 6,
    },
    {
      name: 'Vanna',
      symbol: '∂Δ/∂σ',
      value: vanna,
      unit: 'Δ/1% vol',
      description: 'Change in Delta per +1% vol (cross-Greek)',
      color: '#F472B6',
      decimals: 6,
    },
    {
      name: 'Volga',
      symbol: '∂ν/∂σ',
      value: volga,
      unit: 'ν/1% vol',
      description: 'Change in Vega per +1% vol (vol convexity)',
      color: '#67E8F9',
      decimals: 6,
    },
  ], [currentGreeks, vanna, volga, optType])

  const pnlAttrib = useMemo(() => {
    const dS   = S * spotMovePct / 100
    const dVol = sigma * volMovePct / 100
    const dT   = 1 / 365

    const deltaPnl = currentGreeks.delta * dS
    const gammaPnl = 0.5 * currentGreeks.gamma * dS * dS
    const vegaPnl  = currentGreeks.vega * (dVol * 100)
    const thetaPnl = currentGreeks.theta * dT * 365

    const totalApprox = deltaPnl + gammaPnl + vegaPnl + thetaPnl

    const S2     = S + dS
    const sig2   = sigma + dVol
    const T2     = Math.max(T - dT, 0.0001)
    const newPrice = blackScholesPrice(S2, K, T2, r, Math.max(sig2, 0.001), optType)
    const actualPnl = newPrice - currentPrice

    return { deltaPnl, gammaPnl, vegaPnl, thetaPnl, totalApprox, actualPnl }
  }, [S, K, T, r, sigma, optType, spotMovePct, volMovePct, currentGreeks, currentPrice])

  const maxAbsPnl = useMemo(() => {
    const vals = [
      Math.abs(pnlAttrib.deltaPnl),
      Math.abs(pnlAttrib.gammaPnl),
      Math.abs(pnlAttrib.vegaPnl),
      Math.abs(pnlAttrib.thetaPnl),
      Math.abs(pnlAttrib.totalApprox),
      Math.abs(pnlAttrib.actualPnl),
    ]
    return Math.max(...vals, 0.0001)
  }, [pnlAttrib])

  return (
    <div>
      {/* Sticky params bar */}
      <div
        className="sticky top-0 z-10 mb-4 rounded-lg px-4 py-3"
        style={{
          backgroundColor: 'rgba(19,24,35,0.97)',
          border: `1px solid ${BORDER}`,
          backdropFilter: 'blur(8px)',
        }}
      >
        <div className="flex flex-wrap items-end gap-5">
          <div style={{ minWidth: 120 }}>
            <ParamSlider label="Spot S" value={S} min={50} max={200} step={0.5} displayValue={`$${S.toFixed(2)}`} onChange={setS} />
          </div>
          <div style={{ minWidth: 120 }}>
            <ParamSlider label="Strike K" value={K} min={50} max={200} step={0.5} displayValue={`$${K.toFixed(2)}`} onChange={setK} />
          </div>
          <div style={{ minWidth: 120 }}>
            <ParamSlider label="Maturity T" value={T} min={0.05} max={3} step={0.05} displayValue={`${T.toFixed(2)}y`} onChange={setT} />
          </div>
          <div style={{ minWidth: 120 }}>
            <ParamSlider label="Vol σ%" value={sigPct} min={1} max={100} step={0.5} displayValue={`${sigPct.toFixed(1)}%`} onChange={setSig} />
          </div>
          <div style={{ minWidth: 110 }}>
            <ParamSlider label="Rate r%" value={rPct} min={0} max={20} step={0.25} displayValue={`${rPct.toFixed(2)}%`} onChange={setR} />
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[11px] font-medium uppercase tracking-wider" style={{ color: SLATE }}>
              Type
            </span>
            <div className="flex rounded overflow-hidden" style={{ border: `1px solid ${BORDER}` }}>
              {(['call', 'put'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setOptType(t)}
                  className="px-4 py-1 text-xs font-semibold uppercase transition-colors"
                  style={{
                    backgroundColor: optType === t ? AMBER : 'transparent',
                    color: optType === t ? '#0B0F1A' : SLATE,
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div className="ml-auto flex flex-col items-end">
            <span className="text-[11px] font-medium uppercase tracking-wider" style={{ color: SLATE }}>
              Option Price
            </span>
            <span className="font-mono text-xl font-bold" style={{ color: AMBER }}>
              ${currentPrice.toFixed(4)}
            </span>
          </div>
        </div>
      </div>

      {/* 2×3 grid of charts */}
      <div className="mb-4 grid grid-cols-3 gap-3" style={{ gridTemplateRows: 'auto auto' }}>
        <GreekChart title="Delta" symbol="Δ" data={deltaData} color={optType === 'call' ? GREEN : RED} currentSpot={S} currentValue={currentGreeks.delta} decimals={4} />
        <GreekChart title="Gamma" symbol="Γ" data={gammaData} color={AMBER} currentSpot={S} currentValue={currentGreeks.gamma} decimals={6} />
        <GreekChart title="Vega" symbol="ν" data={vegaData} color={PURPLE} currentSpot={S} currentValue={currentGreeks.vega} decimals={4} />
        <GreekChart title="Theta" symbol="Θ" data={thetaData} color={RED} currentSpot={S} currentValue={currentGreeks.theta} decimals={4} />
        <GreekChart title="Rho" symbol="ρ" data={rhoData} color={BLUE} currentSpot={S} currentValue={currentGreeks.rho} decimals={6} />
        <VolSurface S={S} r={r} sigma={sigma} type={optType} />
      </div>

      {/* Greeks summary table */}
      <Card className="mb-4">
        <SectionHeader title="Greeks Summary" />
        <GreeksSummaryTable rows={summaryRows} />
      </Card>

      {/* P&L Attribution */}
      <Card>
        <SectionHeader title="P&L Attribution" />
        <div className="mb-4 flex flex-wrap gap-6">
          <div style={{ minWidth: 220 }}>
            <ParamSlider label="Spot Move ΔS" value={spotMovePct} min={-20} max={20} step={0.5} displayValue={fmtPct(spotMovePct)} onChange={setSpotMovePct} />
          </div>
          <div style={{ minWidth: 220 }}>
            <ParamSlider label="Vol Move Δσ (relative)" value={volMovePct} min={-50} max={50} step={1} displayValue={fmtPct(volMovePct)} onChange={setVolMovePct} />
          </div>
          <div className="ml-auto flex items-center gap-3 self-end">
            <div className="text-right">
              <p className="text-[11px] uppercase tracking-wider" style={{ color: SLATE }}>Greek approx</p>
              <p className="font-mono text-lg font-bold" style={{ color: pnlAttrib.totalApprox >= 0 ? GREEN : RED }}>
                {pnlAttrib.totalApprox >= 0 ? '+' : ''}{pnlAttrib.totalApprox.toFixed(4)}
              </p>
            </div>
            <div className="h-10 w-px" style={{ backgroundColor: BORDER }} />
            <div className="text-right">
              <p className="text-[11px] uppercase tracking-wider" style={{ color: SLATE }}>Actual BS Δprice</p>
              <p className="font-mono text-lg font-bold" style={{ color: pnlAttrib.actualPnl >= 0 ? GREEN : RED }}>
                {pnlAttrib.actualPnl >= 0 ? '+' : ''}{pnlAttrib.actualPnl.toFixed(4)}
              </p>
            </div>
            <div className="h-10 w-px" style={{ backgroundColor: BORDER }} />
            <div className="text-right">
              <p className="text-[11px] uppercase tracking-wider" style={{ color: SLATE }}>Approx error</p>
              <p className="font-mono text-lg font-bold" style={{ color: AMBER }}>
                {fmt(pnlAttrib.actualPnl - pnlAttrib.totalApprox, 4)}
              </p>
            </div>
          </div>
        </div>
        <div className="rounded-lg p-3" style={{ backgroundColor: '#0B0F1A', border: `1px solid ${BORDER}` }}>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider" style={{ color: SLATE }}>
            P&amp;L Components
          </p>
          <PnLBar label="Δ Delta P&L (Δ×ΔS)" value={pnlAttrib.deltaPnl} maxAbs={maxAbsPnl} color={optType === 'call' ? GREEN : RED} />
          <PnLBar label="Γ Gamma P&L (½Γ×ΔS²)" value={pnlAttrib.gammaPnl} maxAbs={maxAbsPnl} color={AMBER} />
          <PnLBar label="ν Vega P&L (ν×Δvol)" value={pnlAttrib.vegaPnl} maxAbs={maxAbsPnl} color={PURPLE} />
          <PnLBar label="Θ Theta P&L (Θ×1d)" value={pnlAttrib.thetaPnl} maxAbs={maxAbsPnl} color={RED} />
          <div className="mt-2 border-t" style={{ borderColor: BORDER }} />
          <PnLBar label="Total Approx" value={pnlAttrib.totalApprox} maxAbs={maxAbsPnl} color={AMBER} />
          <PnLBar label="Actual BS Δprice" value={pnlAttrib.actualPnl} maxAbs={maxAbsPnl} color="#00D9FF" />
        </div>
        <div
          className="mt-3 rounded px-4 py-2 text-xs"
          style={{ backgroundColor: 'rgba(245,158,11,0.05)', border: `1px solid rgba(245,158,11,0.15)`, color: SLATE }}
        >
          <span style={{ color: AMBER }} className="font-semibold">Formula: </span>
          ΔP ≈ Δ·ΔS + ½Γ·ΔS² + ν·Δσ + Θ·Δt &nbsp;|&nbsp;
          ΔS = {fmtPct(spotMovePct)} of S &nbsp;|&nbsp;
          Δσ = {fmtPct(volMovePct)} relative ({((sigma * volMovePct / 100) * 100).toFixed(2)}% abs) &nbsp;|&nbsp;
          Δt = 1/365 yr &nbsp;|&nbsp;
          Vega scaled per +1% vol
        </div>
      </Card>
    </div>
  )
}

// ─── Vol Calibration tab content ──────────────────────────────────────────────

function VolCalibrationContent() {
  const { data: snapshot, isLoading: snapshotLoading } = useSnapshot()
  const usingFallback = !snapshot

  const [spot, setSpot] = useState(100)
  const [sigmaATM, setSigmaATM] = useState(0.2)
  const [smileA, setSmileA] = useState(0.8)
  const [smileB, setSmileB] = useState(-0.15)

  const [sabrAlpha, setSabrAlpha] = useState(0.2)
  const [sabrBeta, setSabrBeta] = useState(0.5)
  const [sabrRho, setSabrRho] = useState(-0.3)
  const [sabrNu, setSabrNu] = useState(0.4)
  const [calibrated, setCalibrated] = useState(false)

  const strikes = useMemo(() => {
    const arr: number[] = []
    for (let pct = 80; pct <= 120; pct += 2) {
      arr.push(Math.round(spot * pct) / 100)
    }
    return arr
  }, [spot])

  const termMultiplier = (T: number) => 1 + 0.05 * Math.log(1 + T * 4)

  const smileData = useMemo(() => {
    const mats = [MATURITIES[0], MATURITIES[2], MATURITIES[4]]
    return strikes.map((K) => {
      const row: Record<string, number> = { strike: K }
      for (const m of mats) {
        const baseVol = sigmaATM * termMultiplier(m.T)
        row[m.label] = smileVol(spot, K, baseVol, smileA, smileB)
      }
      return row
    })
  }, [strikes, spot, sigmaATM, smileA, smileB])

  const termData = useMemo(() => {
    return MATURITIES.map((m) => ({
      maturity: m.label,
      atmVol: sigmaATM * termMultiplier(m.T),
    }))
  }, [sigmaATM])

  const surfaceData = useMemo(() => {
    const rows: { maturity: string; vols: { strike: number; vol: number }[] }[] = []
    for (const m of MATURITIES) {
      const baseVol = sigmaATM * termMultiplier(m.T)
      const vols = strikes.map((K) => ({
        strike: K,
        vol: smileVol(spot, K, baseVol, smileA, smileB),
      }))
      rows.push({ maturity: m.label, vols })
    }
    return rows
  }, [strikes, spot, sigmaATM, smileA, smileB])

  const allVols = useMemo(() => surfaceData.flatMap((r) => r.vols.map((v) => v.vol)), [surfaceData])
  const minVol = Math.min(...allVols)
  const maxVol = Math.max(...allVols)

  const sabrResult = useMemo(() => {
    if (!calibrated) return null
    return strikes.map((K) => {
      const m = K / spot - 1
      const vol = sabrAlpha * (1 + sabrNu * sabrNu * (1 / 24) + sabrRho * sabrNu * m * 0.5) *
        Math.pow(spot / K, 1 - sabrBeta) * (1 + 0.3 * m * m)
      return { strike: K, sabrVol: Math.max(vol, 0.01) }
    })
  }, [calibrated, strikes, spot, sabrAlpha, sabrBeta, sabrRho, sabrNu])

  const vcFmt = (n: number, digits = 2): string => {
    if (!isFinite(n)) return '—'
    return n.toFixed(digits)
  }

  return (
    <div>
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

      <Card className="mb-4">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16 }}>
          <div>
            <label style={vcLabelStyle}>Spot Price</label>
            <input type="number" value={spot} onChange={(e) => setSpot(Number(e.target.value) || 100)} style={vcInputStyle} />
          </div>
          <div>
            <label style={vcLabelStyle}>ATM Vol (σ)</label>
            <input type="number" step={0.01} value={sigmaATM} onChange={(e) => setSigmaATM(Number(e.target.value) || 0.2)} style={vcInputStyle} />
          </div>
          <div>
            <label style={vcLabelStyle}>Smile a (curvature)</label>
            <input type="number" step={0.1} value={smileA} onChange={(e) => setSmileA(Number(e.target.value))} style={vcInputStyle} />
          </div>
          <div>
            <label style={vcLabelStyle}>Smile b (skew)</label>
            <input type="number" step={0.05} value={smileB} onChange={(e) => setSmileB(Number(e.target.value))} style={vcInputStyle} />
          </div>
        </div>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        <Card title="Volatility Smile" subtitle="IV vs Strike for selected maturities">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={smileData} margin={{ top: 10, right: 30, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
              <XAxis dataKey="strike" stroke={VC.muted} tick={{ fill: VC.muted, fontSize: 11 }} tickFormatter={(v: any) => vcFmt(v, 0)} />
              <YAxis stroke={VC.muted} tick={{ fill: VC.muted, fontSize: 11 }} tickFormatter={(v: any) => `${(v * 100).toFixed(1)}%`} />
              <Tooltip
                contentStyle={{ backgroundColor: VC.elevated, border: `1px solid ${VC.border}`, borderRadius: 6 }}
                labelStyle={{ color: VC.text, fontWeight: 600 }}
                itemStyle={{ color: VC.muted }}
                formatter={(v: any) => `${(v * 100).toFixed(2)}%`}
                labelFormatter={(v: any) => `Strike: ${v}`}
              />
              <Legend wrapperStyle={{ color: VC.muted, fontSize: 11 }} />
              <Line type="monotone" dataKey="1M" stroke="#EF4444" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="6M" stroke="#F59E0B" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="1Y" stroke="#10B981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Volatility Term Structure" subtitle="ATM implied vol vs maturity">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={termData} margin={{ top: 10, right: 30, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
              <XAxis dataKey="maturity" stroke={VC.muted} tick={{ fill: VC.muted, fontSize: 11 }} />
              <YAxis stroke={VC.muted} tick={{ fill: VC.muted, fontSize: 11 }} tickFormatter={(v: any) => `${(v * 100).toFixed(1)}%`} />
              <Tooltip
                contentStyle={{ backgroundColor: VC.elevated, border: `1px solid ${VC.border}`, borderRadius: 6 }}
                labelStyle={{ color: VC.text, fontWeight: 600 }}
                itemStyle={{ color: VC.muted }}
                formatter={(v: any) => `${(v * 100).toFixed(2)}%`}
              />
              <Line type="monotone" dataKey="atmVol" stroke={VC.red} strokeWidth={2} dot={{ fill: VC.red, r: 4 }} name="ATM Vol" />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card className="mb-4" title="SABR Model Calibration" subtitle="Stochastic Alpha Beta Rho parameters">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 16, marginBottom: 16 }}>
          <div>
            <label style={vcLabelStyle}>Alpha (α)</label>
            <input type="number" step={0.01} value={sabrAlpha} onChange={(e) => setSabrAlpha(Number(e.target.value) || 0.2)} style={vcInputStyle} />
          </div>
          <div>
            <label style={vcLabelStyle}>Beta (β)</label>
            <input type="number" step={0.1} min={0} max={1} value={sabrBeta} onChange={(e) => setSabrBeta(Math.min(1, Math.max(0, Number(e.target.value))))} style={vcInputStyle} />
          </div>
          <div>
            <label style={vcLabelStyle}>Rho (ρ)</label>
            <input type="number" step={0.05} min={-1} max={1} value={sabrRho} onChange={(e) => setSabrRho(Math.min(1, Math.max(-1, Number(e.target.value))))} style={vcInputStyle} />
          </div>
          <div>
            <label style={vcLabelStyle}>Nu (ν)</label>
            <input type="number" step={0.05} value={sabrNu} onChange={(e) => setSabrNu(Number(e.target.value) || 0.4)} style={vcInputStyle} />
          </div>
          <div style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button onClick={() => setCalibrated(true)} style={vcBtnStyle}>Calibrate SABR</button>
          </div>
        </div>
        {sabrResult && (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={sabrResult} margin={{ top: 10, right: 30, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
              <XAxis dataKey="strike" stroke={VC.muted} tick={{ fill: VC.muted, fontSize: 11 }} tickFormatter={(v: any) => vcFmt(v, 0)} />
              <YAxis stroke={VC.muted} tick={{ fill: VC.muted, fontSize: 11 }} tickFormatter={(v: any) => `${(v * 100).toFixed(1)}%`} />
              <Tooltip
                contentStyle={{ backgroundColor: VC.elevated, border: `1px solid ${VC.border}`, borderRadius: 6 }}
                labelStyle={{ color: VC.text, fontWeight: 600 }}
                itemStyle={{ color: VC.muted }}
                formatter={(v: any) => `${(v * 100).toFixed(2)}%`}
                labelFormatter={(v: any) => `Strike: ${v}`}
              />
              <Line type="monotone" dataKey="sabrVol" stroke="#8B5CF6" strokeWidth={2} dot={false} name="SABR Vol" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card title="Volatility Surface" subtitle="Implied vol across strike x maturity">
        <div style={{ overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }}>
            <thead>
              <tr>
                <th style={{ padding: '6px 8px', color: VC.muted, textAlign: 'left', borderBottom: `1px solid ${VC.border}` }}>Maturity</th>
                {strikes.map((K) => (
                  <th key={K} style={{ padding: '6px 4px', color: VC.muted, textAlign: 'center', borderBottom: `1px solid ${VC.border}`, minWidth: 44 }}>
                    {vcFmt(K, 0)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {surfaceData.map((row) => (
                <tr key={row.maturity}>
                  <td style={{ padding: '6px 8px', color: VC.text, fontWeight: 600, borderBottom: `1px solid ${VC.border}` }}>{row.maturity}</td>
                  {row.vols.map((cell, idx) => (
                    <td key={idx} style={{ padding: '6px 4px', textAlign: 'center', color: '#fff', fontWeight: 500, backgroundColor: volToColor(cell.vol, minVol, maxVol), borderBottom: `1px solid ${VC.border}`, borderRadius: 2 }}>
                      {(cell.vol * 100).toFixed(1)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12, fontSize: 11, color: VC.muted }}>
          <span>Low vol</span>
          <div style={{ width: 200, height: 12, borderRadius: 4, background: `linear-gradient(to right, ${volToColor(minVol, minVol, maxVol)}, ${volToColor((minVol + maxVol) / 2, minVol, maxVol)}, ${volToColor(maxVol, minVol, maxVol)})` }} />
          <span>High vol</span>
          <span style={{ marginLeft: 8 }}>Range: {(minVol * 100).toFixed(1)}% – {(maxVol * 100).toFixed(1)}%</span>
        </div>
      </Card>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

const PAGE_TABS = ['Greeks Sensitivity', 'Vol Calibration']

export default function GreeksVolLab() {
  const [activeTab, setActiveTab] = useState(PAGE_TABS[0])

  return (
    <div
      className="min-h-screen p-4"
      style={{ backgroundColor: BG_PAGE, color: '#F1F5F9', fontFamily: 'Inter, sans-serif' }}
    >
      {/* Page header */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1
            className="text-2xl font-bold tracking-tight"
            style={{ fontFamily: 'JetBrains Mono, monospace', color: '#F1F5F9' }}
          >
            Greeks &amp; Vol Lab
          </h1>
          <p className="mt-1 text-sm" style={{ color: SLATE }}>
            Interactive Black-Scholes Greeks, P&amp;L attribution and volatility surface calibration
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="warning">LIVE CALC</Badge>
          <Badge variant="info">BSM</Badge>
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <Tabs tabs={PAGE_TABS} active={activeTab} onChange={setActiveTab} />
      </div>

      {activeTab === 'Greeks Sensitivity' && <GreeksSensitivityContent />}
      {activeTab === 'Vol Calibration' && <VolCalibrationContent />}
    </div>
  )
}
