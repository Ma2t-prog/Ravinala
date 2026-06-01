import { useState, useMemo } from 'react'
import { Card } from '../../components/ui/Card'
import { useIndices } from '../../hooks/useMarketData'

// ── Types ────────────────────────────────────────────────────────────────────

interface Preset {
  name: string
  equityWeight: number
  bondWeight: number
  altWeight: number
}

// ── Constants ────────────────────────────────────────────────────────────────

const equityReturns = [-30, -20, -10, 0, 10, 20, 30]
const rateChanges = [-2, -1, 0, 1, 2]

const presets: Preset[] = [
  { name: 'Base Case', equityWeight: 60, bondWeight: 30, altWeight: 10 },
  { name: 'Risk-Off', equityWeight: 20, bondWeight: 60, altWeight: 20 },
  { name: 'Reflation', equityWeight: 75, bondWeight: 10, altWeight: 15 },
]

// Bond return approximation: duration ~6, so rate change * -6 = bond return
// Alts: 0.3 * equity return + some diversification
function computePnl(eqRet: number, rateChg: number, eqW: number, bondW: number, altW: number): number {
  const bondReturn = rateChg * -6 // simplified duration effect
  const altReturn = eqRet * 0.3 + rateChg * -1.5
  return (eqW / 100) * eqRet + (bondW / 100) * bondReturn + (altW / 100) * altReturn
}

function pnlColor(v: number): string {
  if (v > 15) return 'rgba(16,185,129,0.8)'
  if (v > 8) return 'rgba(16,185,129,0.5)'
  if (v > 2) return 'rgba(16,185,129,0.25)'
  if (v > -2) return 'rgba(51,65,85,0.3)'
  if (v > -8) return 'rgba(239,68,68,0.25)'
  if (v > -15) return 'rgba(239,68,68,0.5)'
  return 'rgba(239,68,68,0.8)'
}

// ── Component ────────────────────────────────────────────────────────────────

export default function ScenarioMatrix() {
  const { data: indicesData } = useIndices()
  const liveData = indicesData ?? null

  const [equityWeight, setEquityWeight] = useState(60)
  const [bondWeight, setBondWeight] = useState(30)
  const [altWeight, setAltWeight] = useState(10)

  const matrix = useMemo(() => {
    return rateChanges.map((rate) =>
      equityReturns.map((eq) => computePnl(eq, rate, equityWeight, bondWeight, altWeight))
    )
  }, [equityWeight, bondWeight, altWeight])

  const applyPreset = (p: Preset) => {
    setEquityWeight(p.equityWeight)
    setBondWeight(p.bondWeight)
    setAltWeight(p.altWeight)
  }

  const sliderLabel: React.CSSProperties = {
    color: '#94A3B8', fontSize: 11, marginBottom: 4, display: 'flex', justifyContent: 'space-between',
  }

  return (
    <div style={{ color: '#F1F5F9', minHeight: '100vh' }}>
      {!liveData && (
        <div style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, padding: '8px 16px', marginBottom: 16, fontSize: 13, color: '#F59E0B', fontFamily: 'Inter, sans-serif' }}>
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      <h1 style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, marginBottom: 4 }}>
        Scenario Matrix
      </h1>
      <p style={{ color: '#94A3B8', fontSize: 14, marginBottom: 24 }}>
        Stress-test portfolio across equity &amp; rate scenarios
      </p>

      {liveData && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          {Object.values(liveData).flat().slice(0, 6).map((idx) => (
            <div key={idx.symbol} style={{
              padding: '6px 14px', borderRadius: 8,
              backgroundColor: 'rgba(139,92,246,0.08)', border: '1px solid rgba(139,92,246,0.2)',
              fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
            }}>
              <span style={{ color: '#94A3B8', marginRight: 8 }}>{idx.symbol}</span>
              <span style={{ color: '#F1F5F9', fontWeight: 600 }}>{idx.price.toLocaleString()}</span>
              <span style={{ color: idx.change.percent >= 0 ? '#10B981' : '#EF4444', marginLeft: 8, fontSize: 11 }}>
                {idx.change.percent >= 0 ? '+' : ''}{idx.change.percent.toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16 }}>
        {/* ── Left: Controls ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="Portfolio Weights">
            <div style={{ marginBottom: 16 }}>
              <div style={sliderLabel}>
                <span>Equity</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', color: '#8B5CF6' }}>{equityWeight}%</span>
              </div>
              <input type="range" min={0} max={100} value={equityWeight}
                onChange={(e) => setEquityWeight(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#8B5CF6' }}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={sliderLabel}>
                <span>Bonds</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', color: '#8B5CF6' }}>{bondWeight}%</span>
              </div>
              <input type="range" min={0} max={100} value={bondWeight}
                onChange={(e) => setBondWeight(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#8B5CF6' }}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={sliderLabel}>
                <span>Alternatives</span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', color: '#8B5CF6' }}>{altWeight}%</span>
              </div>
              <input type="range" min={0} max={100} value={altWeight}
                onChange={(e) => setAltWeight(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#8B5CF6' }}
              />
            </div>
            <div style={{ fontSize: 11, color: equityWeight + bondWeight + altWeight === 100 ? '#10B981' : '#EF4444' }}>
              Total: {equityWeight + bondWeight + altWeight}%
              {equityWeight + bondWeight + altWeight !== 100 && ' (should be 100%)'}
            </div>
          </Card>

          <Card title="Preset Scenarios">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {presets.map((p) => (
                <button
                  key={p.name}
                  onClick={() => applyPreset(p)}
                  style={{
                    padding: '10px 14px', borderRadius: 8, border: '1px solid rgba(139,92,246,0.3)',
                    backgroundColor: 'rgba(139,92,246,0.08)', color: '#F1F5F9',
                    fontFamily: 'JetBrains Mono, monospace', fontSize: 12, cursor: 'pointer',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: 2 }}>{p.name}</div>
                  <div style={{ color: '#94A3B8', fontSize: 10 }}>
                    EQ {p.equityWeight}% / BD {p.bondWeight}% / ALT {p.altWeight}%
                  </div>
                </button>
              ))}
            </div>
          </Card>
        </div>

        {/* ── Right: Matrix ── */}
        <Card title="P&L Scenario Grid" subtitle="Equity Return (x-axis) vs Interest Rate Change (y-axis)">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ padding: '8px 12px', color: '#94A3B8', fontSize: 11, fontWeight: 600, textAlign: 'right' }}>
                    Rate \ Equity
                  </th>
                  {equityReturns.map((eq) => (
                    <th key={eq} style={{
                      padding: '8px 12px', color: '#94A3B8', fontSize: 11, fontWeight: 600, textAlign: 'center',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}>
                      {eq >= 0 ? '+' : ''}{eq}%
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {matrix.map((row, ri) => (
                  <tr key={ri}>
                    <td style={{
                      padding: '8px 12px', fontFamily: 'JetBrains Mono, monospace', fontSize: 11,
                      color: '#94A3B8', textAlign: 'right', fontWeight: 600, whiteSpace: 'nowrap',
                    }}>
                      {rateChanges[ri] >= 0 ? '+' : ''}{rateChanges[ri]}%
                    </td>
                    {row.map((val, ci) => (
                      <td
                        key={ci}
                        style={{
                          padding: '10px 14px', textAlign: 'center',
                          backgroundColor: pnlColor(val),
                          borderRadius: 4, margin: 1,
                          fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 600,
                          color: '#F1F5F9',
                        }}
                      >
                        {val >= 0 ? '+' : ''}{val.toFixed(1)}%
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', gap: 16, marginTop: 16, justifyContent: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94A3B8' }}>
              <div style={{ width: 16, height: 16, borderRadius: 3, backgroundColor: 'rgba(239,68,68,0.8)' }} />
              Large Loss
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94A3B8' }}>
              <div style={{ width: 16, height: 16, borderRadius: 3, backgroundColor: 'rgba(239,68,68,0.25)' }} />
              Small Loss
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94A3B8' }}>
              <div style={{ width: 16, height: 16, borderRadius: 3, backgroundColor: 'rgba(51,65,85,0.3)' }} />
              Neutral
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94A3B8' }}>
              <div style={{ width: 16, height: 16, borderRadius: 3, backgroundColor: 'rgba(16,185,129,0.25)' }} />
              Small Gain
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#94A3B8' }}>
              <div style={{ width: 16, height: 16, borderRadius: 3, backgroundColor: 'rgba(16,185,129,0.8)' }} />
              Large Gain
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
