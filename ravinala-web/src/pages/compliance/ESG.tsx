import { Card, Badge } from '../../components/ui'
import { useIndices } from '../../hooks/useMarketData'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const ESG_SCORE = 72
const E_SCORE = 68
const S_SCORE = 75
const G_SCORE = 74

const peerData = [
  { name: 'Portfolio', E: 68, S: 75, G: 74 },
  { name: 'Peer Avg', E: 62, S: 68, G: 70 },
  { name: 'Benchmark', E: 58, S: 65, G: 67 },
  { name: 'Industry', E: 55, S: 60, G: 65 },
]

const CONTROVERSIES = [
  { company: 'TotalEnergies', issue: 'Carbon emissions exceeding targets', severity: 'High', date: '2026-03-15', category: 'Environmental' },
  { company: 'Meta Platforms', issue: 'Data privacy concerns in EU markets', severity: 'Medium', date: '2026-03-10', category: 'Social' },
  { company: 'Amazon', issue: 'Labor practice complaints in warehouses', severity: 'Medium', date: '2026-03-08', category: 'Social' },
  { company: 'Goldman Sachs', issue: 'Board diversity below threshold', severity: 'Low', date: '2026-02-28', category: 'Governance' },
  { company: 'ExxonMobil', issue: 'Greenwashing allegations on net-zero claims', severity: 'High', date: '2026-02-20', category: 'Environmental' },
]

function ScoreGauge({ score, label, color }: { score: number; label: string; color: string }) {
  const pct = score / 100
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ position: 'relative', width: 120, height: 70, margin: '0 auto' }}>
        <svg viewBox="0 0 120 70" width="120" height="70">
          <path d="M10,60 A50,50 0 0,1 110,60" fill="none" stroke="rgba(51,65,85,0.4)" strokeWidth="10" strokeLinecap="round" />
          <path d="M10,60 A50,50 0 0,1 110,60" fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
            strokeDasharray={`${pct * 157} 157`} />
        </svg>
        <div style={{ position: 'absolute', bottom: 2, left: '50%', transform: 'translateX(-50%)' }}>
          <div style={{ fontSize: 20, fontWeight: 700, color, fontFamily: 'JetBrains Mono, monospace' }}>{score}</div>
        </div>
      </div>
      <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 4 }}>{label}</div>
    </div>
  )
}

const ttStyle = { backgroundColor: '#131823', border: '1px solid rgba(51,65,85,0.5)', borderRadius: 8, color: '#F1F5F9' }

export default function ESG() {
  const { data: indicesData } = useIndices()
  const usingFallback = !indicesData

  return (
    <div style={{ color: '#F1F5F9' }}>
      <h1 style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, marginBottom: 4 }}>ESG & Green Lab</h1>
      <p style={{ color: '#94A3B8', marginBottom: 20, fontSize: 14 }}>Environmental, Social & Governance analytics</p>

      {usingFallback && (
        <div style={{background:'rgba(245,158,11,0.08)',border:'1px solid rgba(245,158,11,0.2)',borderRadius:8,padding:'8px 14px',marginBottom:16,fontSize:12,color:'#F59E0B'}}>Backend unreachable — showing demo data</div>
      )}

      {/* Overall + Breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16, marginBottom: 16 }}>
        <Card title="Overall ESG Score">
          <div style={{ textAlign: 'center', padding: 12 }}>
            <div style={{ position: 'relative', width: 180, height: 100, margin: '0 auto' }}>
              <svg viewBox="0 0 180 100" width="180" height="100">
                <path d="M10,90 A80,80 0 0,1 170,90" fill="none" stroke="rgba(51,65,85,0.4)" strokeWidth="14" strokeLinecap="round" />
                <path d="M10,90 A80,80 0 0,1 170,90" fill="none" stroke="#00D9FF" strokeWidth="14" strokeLinecap="round"
                  strokeDasharray={`${(ESG_SCORE / 100) * 251} 251`} />
              </svg>
              <div style={{ position: 'absolute', bottom: 5, left: '50%', transform: 'translateX(-50%)' }}>
                <div style={{ fontSize: 32, fontWeight: 700, color: '#00D9FF', fontFamily: 'JetBrains Mono, monospace' }}>{ESG_SCORE}</div>
              </div>
            </div>
            <div style={{ fontSize: 14, color: '#10B981', fontWeight: 600, marginTop: 4 }}>Above Average</div>
            <div style={{ fontSize: 12, color: '#64748B' }}>MSCI ESG Rating: AA</div>
          </div>
        </Card>

        <Card title="E / S / G Breakdown">
          <div style={{ display: 'flex', justifyContent: 'space-around', padding: '12px 0' }}>
            <ScoreGauge score={E_SCORE} label="Environmental" color="#10B981" />
            <ScoreGauge score={S_SCORE} label="Social" color="#00D9FF" />
            <ScoreGauge score={G_SCORE} label="Governance" color="#D4AF37" />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8, marginTop: 12 }}>
            {[
              { label: 'Carbon Intensity', value: '142 tCO2e/$M', color: '#10B981' },
              { label: 'Gender Diversity', value: '38%', color: '#00D9FF' },
              { label: 'Board Independence', value: '82%', color: '#D4AF37' },
            ].map(m => (
              <div key={m.label} style={{ backgroundColor: 'rgba(10,14,26,0.5)', borderRadius: 6, padding: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 10, color: '#64748B' }}>{m.label}</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: m.color, fontFamily: 'JetBrains Mono, monospace' }}>{m.value}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 16 }}>
        {/* Peer Comparison */}
        <Card title="Peer Comparison" subtitle="E/S/G scores vs peers and benchmark">
          <div style={{ width: '100%', height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={peerData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(51,65,85,0.3)" />
                <XAxis dataKey="name" tick={{ fill: '#94A3B8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10 }} domain={[0, 100]} />
                <Tooltip contentStyle={ttStyle} />
                <Bar dataKey="E" fill="#10B981" name="Environmental" radius={[4, 4, 0, 0]} />
                <Bar dataKey="S" fill="#00D9FF" name="Social" radius={[4, 4, 0, 0]} />
                <Bar dataKey="G" fill="#D4AF37" name="Governance" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Controversy Flags */}
        <Card title="Controversy Flags" subtitle="Active ESG controversies in portfolio">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {CONTROVERSIES.map((c, i) => (
              <div key={i} style={{
                backgroundColor: 'rgba(10,14,26,0.5)', borderRadius: 8, padding: '10px 14px',
                borderLeft: `3px solid ${c.severity === 'High' ? '#EF4444' : c.severity === 'Medium' ? '#F59E0B' : '#94A3B8'}`,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, color: '#F1F5F9', fontSize: 13 }}>{c.company}</span>
                  <Badge variant={c.severity === 'High' ? 'down' : c.severity === 'Medium' ? 'warning' : 'neutral'}>{c.severity}</Badge>
                </div>
                <div style={{ color: '#94A3B8', fontSize: 12 }}>{c.issue}</div>
                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <span style={{ fontSize: 11, color: '#00D9FF' }}>{c.category}</span>
                  <span style={{ fontSize: 11, color: '#64748B' }}>{c.date}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
