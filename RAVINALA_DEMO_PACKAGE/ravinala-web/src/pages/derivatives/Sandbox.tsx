import { useState, useCallback, useRef, useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'
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
interface MCConfig {
  numPaths: number
  numSteps: number
  spot: number
  drift: number
  vol: number
  maturity: number
}

interface PathPoint {
  step: number
  [key: string]: number
}

interface HistBin {
  range: string
  count: number
}

interface MCStats {
  mean: number
  std: number
  min: number
  max: number
  median: number
  skew: number
}

const DEFAULT_CONFIG: MCConfig = {
  numPaths: 50,
  numSteps: 252,
  spot: 100,
  drift: 0.05,
  vol: 0.20,
  maturity: 1.0,
}

// ─── Monte Carlo engine ──────────────────────────────────────────────────────
function gaussianRandom(): number {
  // Box-Muller transform
  let u1 = 0, u2 = 0
  while (u1 === 0) u1 = Math.random()
  while (u2 === 0) u2 = Math.random()
  return Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2)
}

function runMC(config: MCConfig): { paths: PathPoint[]; terminals: number[] } {
  const { numPaths, numSteps, spot, drift, vol, maturity } = config
  const dt = maturity / numSteps
  const sqrtDt = Math.sqrt(dt)
  const driftAdj = (drift - 0.5 * vol * vol) * dt

  const paths: PathPoint[] = []
  const terminals: number[] = []

  // Initialize path data structure
  for (let t = 0; t <= numSteps; t++) {
    const point: PathPoint = { step: t }
    paths.push(point)
  }

  // Generate paths
  const displayPaths = Math.min(numPaths, 50)
  for (let p = 0; p < displayPaths; p++) {
    let s = spot
    paths[0][`p${p}`] = s
    for (let t = 1; t <= numSteps; t++) {
      const z = gaussianRandom()
      s = s * Math.exp(driftAdj + vol * sqrtDt * z)
      paths[t][`p${p}`] = Math.round(s * 100) / 100
    }
    terminals.push(s)
  }

  // Generate extra paths for statistics only (not displayed)
  for (let p = displayPaths; p < numPaths; p++) {
    let s = spot
    for (let t = 1; t <= numSteps; t++) {
      const z = gaussianRandom()
      s = s * Math.exp(driftAdj + vol * sqrtDt * z)
    }
    terminals.push(s)
  }

  return { paths, terminals }
}

function computeStats(terminals: number[]): MCStats {
  const n = terminals.length
  const sorted = [...terminals].sort((a, b) => a - b)
  const mean = terminals.reduce((s, v) => s + v, 0) / n
  const variance = terminals.reduce((s, v) => s + (v - mean) ** 2, 0) / (n - 1)
  const std = Math.sqrt(variance)
  const min = sorted[0]
  const max = sorted[n - 1]
  const median = n % 2 === 0 ? (sorted[n / 2 - 1] + sorted[n / 2]) / 2 : sorted[Math.floor(n / 2)]
  const skew = n > 2 ? (terminals.reduce((s, v) => s + ((v - mean) / std) ** 3, 0) * n) / ((n - 1) * (n - 2)) : 0
  return { mean, std, min, max, median, skew }
}

function buildHistogram(terminals: number[], bins: number): HistBin[] {
  const min = Math.min(...terminals)
  const max = Math.max(...terminals)
  const binWidth = (max - min) / bins
  const histogram: HistBin[] = []

  for (let i = 0; i < bins; i++) {
    const lo = min + i * binWidth
    const hi = lo + binWidth
    const count = terminals.filter(v => v >= lo && (i === bins - 1 ? v <= hi : v < hi)).length
    histogram.push({
      range: `${lo.toFixed(0)}-${hi.toFixed(0)}`,
      count,
    })
  }
  return histogram
}

// ─── PATH COLORS (amber palette) ────────────────────────────────────────────
const PATH_COLORS = [
  'rgba(245,158,11,0.6)', 'rgba(245,158,11,0.4)', 'rgba(245,158,11,0.3)',
  'rgba(251,191,36,0.5)', 'rgba(251,191,36,0.35)', 'rgba(251,191,36,0.25)',
  'rgba(252,211,77,0.4)', 'rgba(252,211,77,0.3)', 'rgba(217,119,6,0.5)',
  'rgba(217,119,6,0.35)',
]

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

export default function Sandbox() {
  const { data: liveData } = useSnapshot('indices')

  // Extract a live equity spot price from the snapshot, fallback to DEFAULT_CONFIG.spot
  const liveSpot = useMemo(() => {
    if (!liveData?.indices) return DEFAULT_CONFIG.spot
    const allIndices = Object.values(liveData.indices).flat()
    const first = allIndices[0]
    return first?.price ?? DEFAULT_CONFIG.spot
  }, [liveData])

  const [config, setConfig] = useState<MCConfig>(DEFAULT_CONFIG)
  const [paths, setPaths] = useState<PathPoint[] | null>(null)
  const [terminals, setTerminals] = useState<number[] | null>(null)
  const [stats, setStats] = useState<MCStats | null>(null)
  const [histogram, setHistogram] = useState<HistBin[] | null>(null)
  const [running, setRunning] = useState(false)
  const [elapsed, setElapsed] = useState<number | null>(null)
  const runCountRef = useRef(0)
  const appliedLiveSpotRef = useRef(false)

  // Apply live spot as default once when data arrives
  if (liveData && !appliedLiveSpotRef.current) {
    appliedLiveSpotRef.current = true
    setConfig(prev => ({ ...prev, spot: liveSpot }))
  }

  const updateConfig = <K extends keyof MCConfig>(key: K, value: MCConfig[K]) => {
    setConfig(prev => ({ ...prev, [key]: value }))
  }

  const runSimulation = useCallback(() => {
    setRunning(true)
    runCountRef.current += 1

    // Run in a setTimeout to allow UI to update
    setTimeout(() => {
      const t0 = performance.now()
      const result = runMC(config)
      const t1 = performance.now()

      const mcStats = computeStats(result.terminals)
      const hist = buildHistogram(result.terminals, 30)

      setPaths(result.paths)
      setTerminals(result.terminals)
      setStats(mcStats)
      setHistogram(hist)
      setElapsed(t1 - t0)
      setRunning(false)
    }, 50)
  }, [config])

  const displayPaths = Math.min(config.numPaths, 50)

  return (
    <div style={{ background: BG, minHeight: '100vh', padding: 24, fontFamily: SANS }}>
      {!liveData && (
        <div style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, padding: '8px 16px', marginBottom: 16, fontSize: 13, color: '#F59E0B', fontFamily: 'Inter, sans-serif' }}>
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: MONO, fontSize: 26, color: TEXT, margin: 0 }}>
          <span style={{ color: AMBER }}>&#9670;</span> Monte Carlo Sandbox
        </h1>
        <p style={{ color: MUTED, fontSize: 14, marginTop: 4 }}>
          Simulate GBM price paths with configurable parameters
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 20 }}>
        {/* Left: Config panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="Simulation Config" subtitle="Geometric Brownian Motion">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={labelStyle}>Number of Paths</label>
                <input style={inputStyle} type="number" min={1} max={10000} value={config.numPaths}
                  onChange={e => updateConfig('numPaths', Math.max(1, +e.target.value))} />
              </div>
              <div>
                <label style={labelStyle}>Steps per Path</label>
                <input style={inputStyle} type="number" min={10} max={1000} value={config.numSteps}
                  onChange={e => updateConfig('numSteps', Math.max(10, +e.target.value))} />
              </div>
              <div>
                <label style={labelStyle}>Initial Spot (S0)</label>
                <input style={inputStyle} type="number" step="1" value={config.spot}
                  onChange={e => updateConfig('spot', +e.target.value)} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <div>
                  <label style={labelStyle}>Drift (mu)</label>
                  <input style={inputStyle} type="number" step="0.01" value={config.drift}
                    onChange={e => updateConfig('drift', +e.target.value)} />
                </div>
                <div>
                  <label style={labelStyle}>Volatility (sigma)</label>
                  <input style={inputStyle} type="number" step="0.01" value={config.vol}
                    onChange={e => updateConfig('vol', +e.target.value)} />
                </div>
              </div>
              <div>
                <label style={labelStyle}>Maturity (years)</label>
                <input style={inputStyle} type="number" step="0.25" value={config.maturity}
                  onChange={e => updateConfig('maturity', +e.target.value)} />
              </div>
            </div>
          </Card>

          {/* Generate button */}
          <button
            onClick={runSimulation}
            disabled={running}
            style={{
              padding: '12px 20px',
              borderRadius: 8,
              border: `1px solid ${AMBER}`,
              background: running ? 'rgba(245,158,11,0.1)' : 'rgba(245,158,11,0.2)',
              color: AMBER,
              fontFamily: MONO,
              fontSize: 14,
              fontWeight: 700,
              cursor: running ? 'wait' : 'pointer',
              transition: 'all 0.2s',
              letterSpacing: 1,
            }}
          >
            {running ? 'SIMULATING...' : 'GENERATE PATHS'}
          </button>

          {/* Statistics */}
          {stats && (
            <Card title="Terminal Statistics" subtitle={`${config.numPaths} paths${elapsed ? ` | ${elapsed.toFixed(0)}ms` : ''}`}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {([
                  { label: 'Mean', value: stats.mean, color: TEXT },
                  { label: 'Std Dev', value: stats.std, color: AMBER },
                  { label: 'Median', value: stats.median, color: TEXT },
                  { label: 'Min', value: stats.min, color: '#EF4444' },
                  { label: 'Max', value: stats.max, color: '#10B981' },
                  { label: 'Skewness', value: stats.skew, color: MUTED },
                ] as const).map(row => (
                  <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: MUTED, fontSize: 12 }}>{row.label}</span>
                    <span style={{ color: row.color, fontFamily: MONO, fontSize: 13, fontWeight: 600 }}>
                      {row.value.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Right: Charts */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Price paths chart */}
          <Card
            title="Simulated Price Paths"
            subtitle={paths ? `Showing ${displayPaths} of ${config.numPaths} paths` : 'Click Generate to start'}
          >
            <div style={{ height: 400 }}>
              {paths ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={paths} margin={{ top: 10, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.2)" />
                    <XAxis
                      dataKey="step"
                      stroke={MUTED}
                      tick={{ fill: MUTED, fontSize: 10, fontFamily: MONO }}
                      label={{ value: 'Time Step', position: 'insideBottom', offset: -10, fill: MUTED, fontSize: 11 }}
                    />
                    <YAxis
                      stroke={MUTED}
                      tick={{ fill: MUTED, fontSize: 10, fontFamily: MONO }}
                      label={{ value: 'Price', angle: -90, position: 'insideLeft', fill: MUTED, fontSize: 11 }}
                      domain={['auto', 'auto']}
                    />
                    <Tooltip
                      contentStyle={{ background: ELEVATED, border: `1px solid ${AMBER}`, borderRadius: 6, fontFamily: MONO, fontSize: 11 }}
                      labelStyle={{ color: MUTED }}
                      labelFormatter={(v: any) => `Step ${v}`}
                    />
                    {Array.from({ length: displayPaths }, (_, i) => (
                      <Line
                        key={`p${i}`}
                        type="monotone"
                        dataKey={`p${i}`}
                        stroke={PATH_COLORS[i % PATH_COLORS.length]}
                        strokeWidth={1}
                        dot={false}
                        isAnimationActive={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div style={{
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: MUTED,
                  fontFamily: MONO,
                  fontSize: 14,
                  border: '1px dashed rgba(51,65,85,0.4)',
                  borderRadius: 8,
                }}>
                  Configure parameters and click Generate
                </div>
              )}
            </div>
          </Card>

          {/* Histogram */}
          {histogram && terminals && (
            <Card title="Terminal Distribution" subtitle={`Histogram of ${terminals.length} terminal prices`}>
              <div style={{ height: 280 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={histogram} margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.2)" />
                    <XAxis
                      dataKey="range"
                      stroke={MUTED}
                      tick={{ fill: MUTED, fontSize: 9, fontFamily: MONO }}
                      angle={-45}
                      textAnchor="end"
                      height={50}
                      interval={2}
                    />
                    <YAxis
                      stroke={MUTED}
                      tick={{ fill: MUTED, fontSize: 10, fontFamily: MONO }}
                      label={{ value: 'Frequency', angle: -90, position: 'insideLeft', fill: MUTED, fontSize: 11 }}
                    />
                    <Tooltip
                      contentStyle={{ background: ELEVATED, border: `1px solid ${AMBER}`, borderRadius: 6, fontFamily: MONO, fontSize: 12 }}
                      labelStyle={{ color: MUTED }}
                      itemStyle={{ color: AMBER }}
                      formatter={(v: any) => [v, 'Count']}
                    />
                    <Bar dataKey="count" fill={AMBER} fillOpacity={0.7} radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Distribution metrics */}
              <div style={{
                marginTop: 12,
                padding: 10,
                background: 'rgba(245,158,11,0.06)',
                borderRadius: 6,
                border: '1px solid rgba(245,158,11,0.15)',
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 12,
              }}>
                {[
                  { label: 'P5', value: [...terminals].sort((a, b) => a - b)[Math.floor(terminals.length * 0.05)] },
                  { label: 'P25', value: [...terminals].sort((a, b) => a - b)[Math.floor(terminals.length * 0.25)] },
                  { label: 'P75', value: [...terminals].sort((a, b) => a - b)[Math.floor(terminals.length * 0.75)] },
                  { label: 'P95', value: [...terminals].sort((a, b) => a - b)[Math.floor(terminals.length * 0.95)] },
                ].map(pct => (
                  <div key={pct.label} style={{ textAlign: 'center' }}>
                    <div style={{ color: MUTED, fontSize: 10, marginBottom: 2 }}>{pct.label}</div>
                    <div style={{ color: TEXT, fontFamily: MONO, fontSize: 13, fontWeight: 600 }}>
                      {pct.value?.toFixed(2) ?? 'N/A'}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
