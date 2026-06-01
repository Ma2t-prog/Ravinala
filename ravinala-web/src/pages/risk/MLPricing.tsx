/**
 * MLPricing.tsx
 * ML-based pricing models — model comparison, feature importance, predicted vs actual, SHAP.
 * All demo data generated client-side.
 */

import { useState, useMemo } from 'react'
import { useSnapshot } from '../../hooks/useMarketData'
import {
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
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
  blue: '#3B82F6',
  purple: '#8B5CF6',
  amber: '#F59E0B',
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

// ─── Types ───────────────────────────────────────────────────────────────────

type ModelType = 'Random Forest' | 'XGBoost' | 'Neural Network'

interface ModelMetrics {
  name: string
  rmse: number
  mae: number
  r2: number
  color: string
}

interface FeatureImportance {
  feature: string
  importance: number
}

interface ScatterPoint {
  actual: number
  predicted: number
}

interface ShapValue {
  feature: string
  contribution: number
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(n: number, digits = 4): string {
  if (!isFinite(n)) return '—'
  return n.toFixed(digits)
}

function seededRandom(seed: number): () => number {
  let s = seed
  return () => {
    s = (s * 1664525 + 1013904223) & 0x7fffffff
    return s / 0x7fffffff
  }
}

function normalRandom(rng: () => number): number {
  const u1 = rng()
  const u2 = rng()
  return Math.sqrt(-2 * Math.log(Math.max(u1, 1e-10))) * Math.cos(2 * Math.PI * u2)
}

// ─── Demo data generators ────────────────────────────────────────────────────

function generateModelComparison(): ModelMetrics[] {
  return [
    { name: 'Random Forest', rmse: 0.0342, mae: 0.0251, r2: 0.9847, color: C.green },
    { name: 'XGBoost', rmse: 0.0287, mae: 0.0198, r2: 0.9912, color: C.blue },
    { name: 'Neural Network', rmse: 0.0315, mae: 0.0223, r2: 0.9879, color: C.purple },
  ]
}

function generateFeatureImportance(model: ModelType): FeatureImportance[] {
  const base: Record<ModelType, number[]> = {
    'Random Forest': [0.35, 0.25, 0.18, 0.12, 0.10],
    'XGBoost': [0.38, 0.22, 0.20, 0.11, 0.09],
    'Neural Network': [0.30, 0.28, 0.19, 0.13, 0.10],
  }
  const features = ['Moneyness', 'Volatility', 'Time to Expiry', 'Spot Price', 'Risk-free Rate']
  const vals = base[model]
  return features.map((f, i) => ({ feature: f, importance: vals[i] }))
    .sort((a, b) => b.importance - a.importance)
}

function generateScatterData(): ScatterPoint[] {
  const rng = seededRandom(123)
  const points: ScatterPoint[] = []
  for (let i = 0; i < 50; i++) {
    const actual = 2 + rng() * 18
    const noise = normalRandom(rng) * 0.4
    const predicted = actual + noise
    points.push({ actual, predicted })
  }
  return points
}

function generateShapValues(): ShapValue[] {
  return [
    { feature: 'Moneyness', contribution: 3.42 },
    { feature: 'Volatility', contribution: 2.18 },
    { feature: 'Time to Expiry', contribution: 1.56 },
    { feature: 'Spot Price', contribution: -0.87 },
    { feature: 'Risk-free Rate', contribution: -0.34 },
  ]
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function MLPricing() {
  const { data: snapshotData } = useSnapshot()
  const [selectedModel, setSelectedModel] = useState<ModelType>('XGBoost')
  const [features, setFeatures] = useState({
    spot: 100,
    vol: 0.2,
    time: 0.5,
    rate: 0.05,
    moneyness: 1.0,
  })

  // Seed spot price from live data when available
  const liveSpot = snapshotData?.indices
    ? Object.values(snapshotData.indices).flat()[0]?.price
    : snapshotData?.fx?.pairs?.[0]?.rate
  const [training, setTraining] = useState(false)
  const [progress, setProgress] = useState(0)
  const [trained, setTrained] = useState(false)

  const modelComparison = useMemo(() => generateModelComparison(), [])
  const featureImportance = useMemo(() => generateFeatureImportance(selectedModel), [selectedModel])
  const scatterData = useMemo(() => generateScatterData(), [])
  const shapValues = useMemo(() => generateShapValues(), [])

  const handleTrain = () => {
    setTraining(true)
    setTrained(false)
    setProgress(0)

    let p = 0
    const interval = setInterval(() => {
      p += Math.random() * 15 + 5
      if (p >= 100) {
        p = 100
        clearInterval(interval)
        setTraining(false)
        setTrained(true)
      }
      setProgress(Math.min(p, 100))
    }, 200)
  }

  return (
    <div style={{ backgroundColor: C.bg, minHeight: '100vh', padding: 24 }}>
      {!snapshotData && (
        <div style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, padding: '8px 16px', marginBottom: 16, fontSize: 13, color: '#F59E0B', fontFamily: 'Inter, sans-serif' }}>
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, color: C.text, margin: 0 }}>
          ML-Based Pricing Models
        </h1>
        <p style={{ color: C.muted, fontSize: 14, marginTop: 4 }}>
          Machine learning approach to derivatives pricing
          {liveSpot !== undefined && (
            <span style={{ marginLeft: 12, color: C.green }}>Live spot: {liveSpot.toFixed(2)}</span>
          )}
        </p>
      </div>

      {/* Model Selection + Feature Inputs */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16, marginBottom: 16 }}>
        <Card title="Model Selection" subtitle="Choose ML algorithm">
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>Model</label>
            <select
              value={selectedModel}
              onChange={(e) => { setSelectedModel(e.target.value as ModelType); setTrained(false) }}
              style={selectStyle}
            >
              <option value="Random Forest">Random Forest</option>
              <option value="XGBoost">XGBoost</option>
              <option value="Neural Network">Neural Network</option>
            </select>
          </div>
          <button onClick={handleTrain} disabled={training} style={{ ...btnStyle, opacity: training ? 0.6 : 1, width: '100%' }}>
            {training ? 'Training...' : 'Train Model'}
          </button>

          {/* Progress bar */}
          {(training || trained) && (
            <div style={{ marginTop: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: C.muted, marginBottom: 4 }}>
                <span>{training ? 'Training in progress...' : 'Training complete'}</span>
                <span>{Math.round(progress)}%</span>
              </div>
              <div style={{ width: '100%', height: 8, backgroundColor: C.elevated, borderRadius: 4, overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${progress}%`,
                    height: '100%',
                    backgroundColor: trained ? C.green : C.red,
                    borderRadius: 4,
                    transition: 'width 0.2s ease-out',
                  }}
                />
              </div>
            </div>
          )}
        </Card>

        <Card title="Feature Inputs" subtitle="Model input parameters">
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: 'JetBrains Mono, monospace' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: C.muted, fontSize: 11, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>Feature</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: C.muted, fontSize: 11, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>Value</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: C.muted, fontSize: 11, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                { key: 'spot' as const, label: 'Spot Price', desc: 'Current underlying price', step: 1 },
                { key: 'vol' as const, label: 'Volatility', desc: 'Annualized implied vol', step: 0.01 },
                { key: 'time' as const, label: 'Time to Expiry', desc: 'Years to maturity', step: 0.1 },
                { key: 'rate' as const, label: 'Risk-free Rate', desc: 'Annualized rate', step: 0.01 },
                { key: 'moneyness' as const, label: 'Moneyness', desc: 'Strike / Spot ratio', step: 0.05 },
              ].map((f) => (
                <tr key={f.key}>
                  <td style={{ padding: '8px 12px', color: C.text, borderBottom: `1px solid ${C.border}` }}>{f.label}</td>
                  <td style={{ padding: '8px 12px', borderBottom: `1px solid ${C.border}` }}>
                    <input
                      type="number"
                      step={f.step}
                      value={features[f.key]}
                      onChange={(e) => setFeatures((prev) => ({ ...prev, [f.key]: Number(e.target.value) }))}
                      style={{ ...inputStyle, width: 100 }}
                    />
                  </td>
                  <td style={{ padding: '8px 12px', color: C.muted, borderBottom: `1px solid ${C.border}`, fontSize: 12 }}>{f.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      {/* Model Comparison Table */}
      <Card className="mb-4" title="Model Comparison" subtitle="Performance metrics across algorithms">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, fontFamily: 'JetBrains Mono, monospace' }}>
          <thead>
            <tr>
              {['Model', 'RMSE', 'MAE', 'R²', 'Status'].map((h) => (
                <th
                  key={h}
                  style={{
                    textAlign: 'left',
                    padding: '10px 16px',
                    color: C.muted,
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    borderBottom: `1px solid ${C.border}`,
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {modelComparison.map((m) => (
              <tr key={m.name}>
                <td style={{ padding: '10px 16px', color: C.text, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>
                  <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', backgroundColor: m.color, marginRight: 8 }} />
                  {m.name}
                </td>
                <td style={{ padding: '10px 16px', color: C.text, borderBottom: `1px solid ${C.border}` }}>{fmt(m.rmse)}</td>
                <td style={{ padding: '10px 16px', color: C.text, borderBottom: `1px solid ${C.border}` }}>{fmt(m.mae)}</td>
                <td style={{ padding: '10px 16px', color: C.green, fontWeight: 600, borderBottom: `1px solid ${C.border}` }}>{fmt(m.r2)}</td>
                <td style={{ padding: '10px 16px', borderBottom: `1px solid ${C.border}` }}>
                  <span style={{
                    display: 'inline-block',
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    backgroundColor: m.name === selectedModel && trained ? 'rgba(16,185,129,0.15)' : 'rgba(148,163,184,0.1)',
                    color: m.name === selectedModel && trained ? C.green : C.muted,
                  }}>
                    {m.name === selectedModel && trained ? 'Trained' : 'Ready'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Charts Row: Feature Importance + Predicted vs Actual */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
        {/* Feature Importance (horizontal bar) */}
        <Card title="Feature Importance" subtitle={`${selectedModel} — relative importance`}>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart
              data={featureImportance}
              layout="vertical"
              margin={{ top: 10, right: 30, bottom: 10, left: 80 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" horizontal={false} />
              <XAxis
                type="number"
                stroke={C.muted}
                tick={{ fill: C.muted, fontSize: 11 }}
                tickFormatter={(v: any) => `${(v * 100).toFixed(0)}%`}
              />
              <YAxis
                type="category"
                dataKey="feature"
                stroke={C.muted}
                tick={{ fill: C.muted, fontSize: 11 }}
                width={80}
              />
              <Tooltip
                contentStyle={{ backgroundColor: C.elevated, border: `1px solid ${C.border}`, borderRadius: 6 }}
                labelStyle={{ color: C.text, fontWeight: 600 }}
                itemStyle={{ color: C.muted }}
                formatter={(v: any) => `${(Number(v) * 100).toFixed(1)}%`}
              />
              <Bar dataKey="importance" radius={[0, 4, 4, 0]} name="Importance">
                {featureImportance.map((_, idx) => (
                  <Cell key={idx} fill={[C.red, C.amber, C.blue, C.green, C.purple][idx % 5]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Predicted vs Actual */}
        <Card title="Predicted vs Actual" subtitle="50 demo option prices">
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 10, right: 30, bottom: 10, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
              <XAxis
                type="number"
                dataKey="actual"
                name="Actual"
                stroke={C.muted}
                tick={{ fill: C.muted, fontSize: 11 }}
                tickFormatter={(v: any) => `$${Number(v).toFixed(0)}`}
                label={{ value: 'Actual Price', position: 'bottom', offset: -5, fill: C.muted, fontSize: 11 }}
              />
              <YAxis
                type="number"
                dataKey="predicted"
                name="Predicted"
                stroke={C.muted}
                tick={{ fill: C.muted, fontSize: 11 }}
                tickFormatter={(v: any) => `$${Number(v).toFixed(0)}`}
                label={{ value: 'Predicted', angle: -90, position: 'insideLeft', fill: C.muted, fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: C.elevated, border: `1px solid ${C.border}`, borderRadius: 6 }}
                labelStyle={{ color: C.text }}
                formatter={(v: any) => `$${Number(v).toFixed(2)}`}
              />
              <Scatter data={scatterData} fill={C.blue} fillOpacity={0.7} r={5} name="Predictions" />
            </ScatterChart>
          </ResponsiveContainer>
          {/* Diagonal reference note */}
          <div style={{ textAlign: 'center', fontSize: 11, color: C.muted, marginTop: 4 }}>
            Points near the diagonal indicate accurate predictions
          </div>
        </Card>
      </div>

      {/* SHAP-style Feature Contributions */}
      <Card title="Feature Contributions (SHAP-style)" subtitle="Impact of each feature on prediction">
        <ResponsiveContainer width="100%" height={280}>
          <BarChart
            data={shapValues}
            layout="vertical"
            margin={{ top: 10, right: 30, bottom: 10, left: 100 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" horizontal={false} />
            <XAxis
              type="number"
              stroke={C.muted}
              tick={{ fill: C.muted, fontSize: 11 }}
              tickFormatter={(v: any) => `${Number(v) > 0 ? '+' : ''}${Number(v).toFixed(2)}`}
            />
            <YAxis
              type="category"
              dataKey="feature"
              stroke={C.muted}
              tick={{ fill: C.muted, fontSize: 11 }}
              width={100}
            />
            <Tooltip
              contentStyle={{ backgroundColor: C.elevated, border: `1px solid ${C.border}`, borderRadius: 6 }}
              labelStyle={{ color: C.text, fontWeight: 600 }}
              itemStyle={{ color: C.muted }}
              formatter={(v: any) => `${Number(v) > 0 ? '+' : ''}${Number(v).toFixed(3)}`}
            />
            <Bar dataKey="contribution" name="Contribution" radius={[0, 4, 4, 0]}>
              {shapValues.map((entry, idx) => (
                <Cell key={idx} fill={entry.contribution >= 0 ? C.red : C.blue} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        {/* Explanation */}
        <div style={{ marginTop: 12, padding: 12, backgroundColor: C.elevated, borderRadius: 6, fontSize: 12, color: C.muted }}>
          <strong style={{ color: C.text }}>Interpretation:</strong>{' '}
          Red bars indicate features that push the predicted price <strong style={{ color: C.red }}>higher</strong>,
          while blue bars indicate features that push it <strong style={{ color: C.blue }}>lower</strong>.
          Moneyness and volatility are the dominant drivers for the current prediction.
        </div>
      </Card>
    </div>
  )
}
