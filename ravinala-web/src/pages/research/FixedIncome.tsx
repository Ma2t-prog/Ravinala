import { useState, useCallback } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Card } from '../../components/ui/Card'
import { useBonds } from '../../hooks/useMarketData'

// ── Demo yield curve data ────────────────────────────────────────────────────

const YIELD_CURVE_FALLBACK = [
  { maturity: '1M', yield: 5.33 },
  { maturity: '3M', yield: 5.35 },
  { maturity: '6M', yield: 5.30 },
  { maturity: '1Y', yield: 5.02 },
  { maturity: '2Y', yield: 4.60 },
  { maturity: '3Y', yield: 4.30 },
  { maturity: '5Y', yield: 4.15 },
  { maturity: '7Y', yield: 4.18 },
  { maturity: '10Y', yield: 4.25 },
  { maturity: '20Y', yield: 4.52 },
  { maturity: '30Y', yield: 4.40 },
]

const spreadData = [
  { rating: 'AAA', spread: 45, yield: 4.70, example: 'MSFT, JNJ' },
  { rating: 'AA', spread: 65, yield: 4.90, example: 'BRK, AAPL' },
  { rating: 'A', spread: 95, yield: 5.20, example: 'JPM, AMZN' },
  { rating: 'BBB', spread: 145, yield: 5.70, example: 'GM, FDX' },
  { rating: 'BB', spread: 250, yield: 6.75, example: 'DISH, CCL' },
  { rating: 'B', spread: 400, yield: 8.25, example: 'AMC, CAKE' },
]

// ── Bond Calculator Logic ────────────────────────────────────────────────────

interface CalcResult {
  price: number
  duration: number
  convexity: number
  currentYield: number
}

function calcBond(faceValue: number, couponRate: number, years: number, ytm: number): CalcResult {
  const coupon = faceValue * (couponRate / 100)
  const y = ytm / 100
  let price = 0
  let weightedTime = 0
  let convexitySum = 0

  for (let t = 1; t <= years; t++) {
    const pv = coupon / Math.pow(1 + y, t)
    price += pv
    weightedTime += t * pv
    convexitySum += (t * (t + 1) * coupon) / Math.pow(1 + y, t + 2)
  }
  const pvFace = faceValue / Math.pow(1 + y, years)
  price += pvFace
  weightedTime += years * pvFace
  convexitySum += (years * (years + 1) * faceValue) / Math.pow(1 + y, years + 2)

  const duration = weightedTime / price
  const convexity = convexitySum / price
  const currentYield = (coupon / price) * 100

  return { price, duration, convexity, currentYield }
}

// ── Component ────────────────────────────────────────────────────────────────

export default function FixedIncome() {
  const { data: bondsData } = useBonds()

  // Build yield curve from live bond data if available
  const liveYieldCurve = bondsData?.bonds
    ? bondsData.bonds
        .filter((b) => b.country_code === 'US')
        .flatMap((b) => {
          const points: { maturity: string; yield: number }[] = []
          if (b.yield_2y != null) points.push({ maturity: '2Y', yield: b.yield_2y })
          if (b.yield_5y != null) points.push({ maturity: '5Y', yield: b.yield_5y })
          if (b.yield_10y != null) points.push({ maturity: '10Y', yield: b.yield_10y })
          return points
        })
    : null

  const yieldCurveData = liveYieldCurve && liveYieldCurve.length > 0 ? liveYieldCurve : YIELD_CURVE_FALLBACK
  const usingFallback = !bondsData?.bonds

  const [faceValue, setFaceValue] = useState(1000)
  const [couponRate, setCouponRate] = useState(5.0)
  const [years, setYears] = useState(10)
  const [ytm, setYtm] = useState(4.5)
  const [result, setResult] = useState<CalcResult | null>(null)

  const handleCalc = useCallback(() => {
    setResult(calcBond(faceValue, couponRate, years, ytm))
  }, [faceValue, couponRate, years, ytm])

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '8px 12px',
    borderRadius: 6,
    border: '1px solid rgba(51,65,85,0.3)',
    backgroundColor: '#0A0E1A',
    color: '#F1F5F9',
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 13,
    outline: 'none',
  }

  const labelStyle: React.CSSProperties = {
    color: '#94A3B8',
    fontSize: 11,
    marginBottom: 4,
    display: 'block',
  }

  return (
    <div style={{ color: '#F1F5F9', minHeight: '100vh' }}>
      <h1 style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, marginBottom: 4 }}>
        Fixed Income
      </h1>
      <p style={{ color: '#94A3B8', fontSize: 14, marginBottom: 24 }}>
        Bond analytics, yield curves &amp; credit spreads
      </p>
      {usingFallback && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', marginBottom: 12, borderRadius: 8, backgroundColor: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#F59E0B' }}>
          <span>Backend unreachable — showing demo data</span>
        </div>
      )}

      {/* ── Yield Curve ── */}
      <Card title="US Treasury Yield Curve" subtitle="Current rates across maturities">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={yieldCurveData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
            <XAxis dataKey="maturity" tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis
              tick={{ fill: '#94A3B8', fontSize: 11 }} axisLine={false} tickLine={false}
              tickFormatter={(v: any) => `${v}%`}
              domain={[3.8, 5.6]}
            />
            <Tooltip
              contentStyle={{ backgroundColor: '#131823', border: '1px solid rgba(51,65,85,0.3)', borderRadius: 8, color: '#F1F5F9' }}
              formatter={(v: any) => [`${Number(v).toFixed(2)}%`, 'Yield']}
            />
            <Line
              type="monotone" dataKey="yield" stroke="#10B981" strokeWidth={2.5}
              dot={{ fill: '#10B981', r: 4 }} activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* ── Row: Bond Calculator + Spread Analysis ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
        {/* Bond Calculator */}
        <Card title="Bond Calculator" subtitle="Price, duration & convexity">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
            <div>
              <label style={labelStyle}>Face Value ($)</label>
              <input
                type="number" style={inputStyle} value={faceValue}
                onChange={(e) => setFaceValue(Number(e.target.value))}
              />
            </div>
            <div>
              <label style={labelStyle}>Coupon Rate (%)</label>
              <input
                type="number" step="0.1" style={inputStyle} value={couponRate}
                onChange={(e) => setCouponRate(Number(e.target.value))}
              />
            </div>
            <div>
              <label style={labelStyle}>Years to Maturity</label>
              <input
                type="number" style={inputStyle} value={years}
                onChange={(e) => setYears(Number(e.target.value))}
              />
            </div>
            <div>
              <label style={labelStyle}>Yield to Maturity (%)</label>
              <input
                type="number" step="0.1" style={inputStyle} value={ytm}
                onChange={(e) => setYtm(Number(e.target.value))}
              />
            </div>
          </div>
          <button
            onClick={handleCalc}
            style={{
              width: '100%', padding: '10px 0', borderRadius: 8, border: 'none',
              backgroundColor: '#10B981', color: '#0A0E1A', fontWeight: 700,
              fontFamily: 'JetBrains Mono, monospace', fontSize: 13, cursor: 'pointer',
            }}
          >
            Calculate
          </button>
          {result && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 16 }}>
              {([
                ['Price', `$${result.price.toFixed(2)}`],
                ['Duration', `${result.duration.toFixed(3)} yrs`],
                ['Convexity', result.convexity.toFixed(3)],
                ['Current Yield', `${result.currentYield.toFixed(2)}%`],
              ] as [string, string][]).map(([label, val]) => (
                <div key={label} style={{ padding: 12, borderRadius: 8, backgroundColor: 'rgba(16,185,129,0.08)' }}>
                  <div style={{ color: '#94A3B8', fontSize: 11, marginBottom: 2 }}>{label}</div>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 16, fontWeight: 600, color: '#10B981' }}>
                    {val}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Spread Analysis */}
        <Card title="Credit Spread Analysis" subtitle="OAS vs US Treasury 10Y">
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid rgba(51,65,85,0.3)' }}>
                  {['Rating', 'Spread (bps)', 'Yield (%)', 'Examples'].map((h) => (
                    <th key={h} style={{ textAlign: 'left', padding: '8px 10px', color: '#94A3B8', fontSize: 11, fontWeight: 600 }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {spreadData.map((row) => (
                  <tr key={row.rating} style={{ borderBottom: '1px solid rgba(51,65,85,0.15)' }}>
                    <td style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>
                      {row.rating}
                    </td>
                    <td style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace' }}>
                      <span style={{ color: row.spread > 200 ? '#EF4444' : row.spread > 100 ? '#F59E0B' : '#10B981' }}>
                        +{row.spread}
                      </span>
                    </td>
                    <td style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace' }}>
                      {row.yield.toFixed(2)}%
                    </td>
                    <td style={{ padding: '8px 10px', color: '#94A3B8' }}>
                      {row.example}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  )
}
