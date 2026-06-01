import { useHealth } from '../../hooks/useMarketData'
import { Card } from '../../components/ui'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

// Generate distribution data
function normalPDF(x: number, mu: number, sigma: number) {
  return Math.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * Math.sqrt(2 * Math.PI))
}

function logNormalPDF(x: number, mu: number, sigma: number) {
  if (x <= 0) return 0
  return Math.exp(-0.5 * ((Math.log(x) - mu) / sigma) ** 2) / (x * sigma * Math.sqrt(2 * Math.PI))
}

function studentTPDF(x: number, nu: number) {
  const coeff = (gamma(((nu + 1) / 2)) / (Math.sqrt(nu * Math.PI) * gamma(nu / 2)))
  return coeff * Math.pow(1 + (x * x) / nu, -(nu + 1) / 2)
}

function chiSquarePDF(x: number, k: number) {
  if (x <= 0) return 0
  return (Math.pow(x, k / 2 - 1) * Math.exp(-x / 2)) / (Math.pow(2, k / 2) * gamma(k / 2))
}

// Lanczos approximation for gamma function
function gamma(z: number): number {
  if (z < 0.5) return Math.PI / (Math.sin(Math.PI * z) * gamma(1 - z))
  z -= 1
  const g = 7
  const c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7]
  let x = c[0]
  for (let i = 1; i < g + 2; i++) x += c[i] / (z + i)
  const t = z + g + 0.5
  return Math.sqrt(2 * Math.PI) * Math.pow(t, z + 0.5) * Math.exp(-t) * x
}

const normalData = Array.from({ length: 80 }, (_, i) => {
  const x = -4 + i * 0.1
  return { x: +x.toFixed(1), 'N(0,1)': +normalPDF(x, 0, 1).toFixed(4), 'N(0,2)': +normalPDF(x, 0, 2).toFixed(4), 'N(1,0.5)': +normalPDF(x, 1, 0.5).toFixed(4) }
})

const logNormData = Array.from({ length: 60 }, (_, i) => {
  const x = 0.05 + i * 0.1
  return { x: +x.toFixed(2), 'LN(0,1)': +logNormalPDF(x, 0, 1).toFixed(4), 'LN(0,0.5)': +logNormalPDF(x, 0, 0.5).toFixed(4) }
})

const studentTData = Array.from({ length: 80 }, (_, i) => {
  const x = -4 + i * 0.1
  return { x: +x.toFixed(1), 'v=3': +studentTPDF(x, 3).toFixed(4), 'v=10': +studentTPDF(x, 10).toFixed(4), Normal: +normalPDF(x, 0, 1).toFixed(4) }
})

const chiData = Array.from({ length: 60 }, (_, i) => {
  const x = 0.1 + i * 0.3
  return { x: +x.toFixed(1), 'k=2': +chiSquarePDF(x, 2).toFixed(4), 'k=5': +chiSquarePDF(x, 5).toFixed(4), 'k=10': +chiSquarePDF(x, 10).toFixed(4) }
})

const ttStyle = { backgroundColor: '#131823', border: '1px solid rgba(51,65,85,0.5)', borderRadius: 8, color: '#F1F5F9' }

const THEOREMS = [
  {
    name: 'Central Limit Theorem (CLT)',
    statement: 'The sum of n independent, identically distributed random variables with finite mean and variance converges in distribution to a normal distribution as n approaches infinity.',
    formula: '(X-bar - mu) / (sigma / sqrt(n))  -->  N(0, 1)  as  n --> infinity',
    significance: 'Fundamental to statistical inference. Justifies using normal distribution for sample means regardless of population distribution.',
  },
  {
    name: "Bayes' Theorem",
    statement: 'Describes the probability of an event based on prior knowledge of conditions related to the event.',
    formula: 'P(A|B) = P(B|A) * P(A) / P(B)',
    significance: 'Foundation of Bayesian statistics. Used in risk modeling, signal processing, and machine learning for updating beliefs with new evidence.',
  },
  {
    name: 'Law of Large Numbers (LLN)',
    statement: 'The sample average of a sequence of iid random variables converges to the expected value as the number of trials increases.',
    formula: 'X-bar_n  -->  E[X]  as  n --> infinity  (in probability)',
    significance: 'Ensures that empirical averages are reliable estimators. Critical for insurance, Monte Carlo simulation, and empirical finance.',
  },
]

export default function ProbabilityBible() {
  const { data: healthData } = useHealth()

  return (
    <div style={{ color: '#F1F5F9' }}>
      {!healthData && (
        <div style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, padding: '8px 16px', marginBottom: 16, fontSize: 13, color: '#F59E0B', fontFamily: 'Inter, sans-serif' }}>
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      <h1 style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, marginBottom: 4, color: '#6366F1' }}>Probability Bible</h1>
      <p style={{ color: '#94A3B8', marginBottom: 20, fontSize: 14 }}>
        Essential probability distributions & theorems for quantitative finance
        {healthData && (
          <span style={{ marginLeft: 12, fontSize: 12, color: healthData.status === 'ok' ? '#10B981' : '#EF4444' }}>
            · Backend {healthData.status === 'ok' ? 'connected' : 'disconnected'}
          </span>
        )}
      </p>

      {/* Distributions */}
      <h2 style={{ fontSize: 16, fontWeight: 600, color: '#6366F1', marginBottom: 12 }}>Key Distributions</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 16, marginBottom: 24 }}>
        <Card title="Normal Distribution" subtitle="f(x) = (1/sigma*sqrt(2*pi)) * exp(-0.5*((x-mu)/sigma)^2)">
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <LineChart data={normalData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                <XAxis dataKey="x" tick={{ fill: '#64748B', fontSize: 10 }} interval={9} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                <Tooltip contentStyle={ttStyle} />
                <Line type="monotone" dataKey="N(0,1)" stroke="#6366F1" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="N(0,2)" stroke="#00D9FF" strokeWidth={1.5} dot={false} />
                <Line type="monotone" dataKey="N(1,0.5)" stroke="#10B981" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Log-Normal Distribution" subtitle="f(x) = (1/x*sigma*sqrt(2*pi)) * exp(-0.5*((ln(x)-mu)/sigma)^2)">
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <LineChart data={logNormData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                <XAxis dataKey="x" tick={{ fill: '#64748B', fontSize: 10 }} interval={9} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                <Tooltip contentStyle={ttStyle} />
                <Line type="monotone" dataKey="LN(0,1)" stroke="#D4AF37" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="LN(0,0.5)" stroke="#F97316" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Student-t Distribution" subtitle="Heavier tails than normal; converges to N(0,1) as v -> inf">
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <LineChart data={studentTData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                <XAxis dataKey="x" tick={{ fill: '#64748B', fontSize: 10 }} interval={9} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                <Tooltip contentStyle={ttStyle} />
                <Line type="monotone" dataKey="v=3" stroke="#EF4444" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="v=10" stroke="#F59E0B" strokeWidth={1.5} dot={false} />
                <Line type="monotone" dataKey="Normal" stroke="#6366F1" strokeWidth={1} dot={false} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Chi-Square Distribution" subtitle="f(x) = x^(k/2-1) * exp(-x/2) / (2^(k/2) * Gamma(k/2))">
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <LineChart data={chiData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                <XAxis dataKey="x" tick={{ fill: '#64748B', fontSize: 10 }} interval={9} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                <Tooltip contentStyle={ttStyle} />
                <Line type="monotone" dataKey="k=2" stroke="#A855F7" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="k=5" stroke="#EC4899" strokeWidth={1.5} dot={false} />
                <Line type="monotone" dataKey="k=10" stroke="#06B6D4" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Theorems */}
      <h2 style={{ fontSize: 16, fontWeight: 600, color: '#6366F1', marginBottom: 12 }}>Fundamental Theorems</h2>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {THEOREMS.map(t => (
          <Card key={t.name}>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#6366F1', marginBottom: 6 }}>{t.name}</h3>
            <p style={{ color: '#F1F5F9', fontSize: 13, lineHeight: 1.5, marginBottom: 8 }}>{t.statement}</p>
            <div style={{
              backgroundColor: 'rgba(99,102,241,0.08)', borderRadius: 8, padding: '10px 14px', marginBottom: 8,
              fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color: '#6366F1',
            }}>
              {t.formula}
            </div>
            <p style={{ color: '#94A3B8', fontSize: 12, lineHeight: 1.5 }}>
              <strong style={{ color: '#D4AF37' }}>Significance: </strong>{t.significance}
            </p>
          </Card>
        ))}
      </div>
    </div>
  )
}
