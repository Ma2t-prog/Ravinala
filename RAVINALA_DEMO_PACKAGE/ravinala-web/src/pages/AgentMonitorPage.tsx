import { useState } from 'react';
import { useAgentMonitor, type SpawnedAgent } from '../hooks/useAgentMonitor';
import { AgentCanvas } from '../components/agents/AgentCanvas';
import { AGENT_COLORS } from '../components/agents/AgentSprite';

const MISSION_TYPES = [
  { value: 'full_analysis',      label: 'Full Analysis',      desc: 'Market → Analysis → Risk → Portfolio → Spawner → Alert → Report → Logger' },
  { value: 'quick_scan',         label: 'Quick Scan',         desc: 'Market → Analysis → Logger' },
  { value: 'risk_check',         label: 'Risk Check',         desc: 'Market → Risk → Alert → Logger' },
  { value: 'backtest_run',       label: 'Backtest Run',       desc: 'Market → Backtest → Logger' },
  { value: 'ml_predict',         label: 'ML Predict',         desc: 'Market → ML → Logger' },
  { value: 'portfolio_optimize', label: 'Portfolio Optimize', desc: 'Market → Analysis → Risk → Portfolio → Spawner → Alert → Report → Logger' },
  { value: 'health_check',       label: 'Health Check',       desc: 'Monitoring → Alert → Logger' },
  { value: 'deep_analysis',      label: 'Deep Analysis',      desc: 'All agents + Spawner + full post-processing' },
  { value: 'signal_hunt',        label: 'Signal Hunt',        desc: 'Market → Analysis → Spawner → Alert → Logger' },
];

export default function AgentMonitorPage() {
  const {
    connected,
    events,
    agentStates,
    spawnedAgents,
    missionStatus,
    startMission,
    cancelMission,
    clearEvents,
  } = useAgentMonitor();

  const [selectedMission, setSelectedMission] = useState('full_analysis');
  const [tickerInput, setTickerInput] = useState('AAPL,MSFT,GOOGL');
  const [sideOpen, setSideOpen] = useState(true);

  const handleStart = () => {
    const tickers = tickerInput.split(',').map(t => t.trim()).filter(Boolean);
    startMission(selectedMission, { tickers });
  };

  const runningCount = Object.values(agentStates).filter(s => s.status === 'running').length;
  const completedCount = Object.values(agentStates).filter(s => s.status === 'completed').length;
  const errorCount = Object.values(agentStates).filter(s => s.status === 'error').length;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: '#060911',
        fontFamily: '"JetBrains Mono", monospace',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* ── Top bar ──────────────────────────────────────────────────── */}
      <header
        style={{
          height: 48,
          borderBottom: '1px solid rgba(26,35,50,0.6)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          gap: 16,
          flexShrink: 0,
          background: 'linear-gradient(180deg, rgba(10,14,26,0.9) 0%, rgba(6,9,17,1) 100%)',
        }}
      >
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16, color: '#D4AF37' }}>&#937;</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#F1F5F9', letterSpacing: '0.08em' }}>
            AGENT MONITOR
          </span>
        </div>

        {/* Separator */}
        <div style={{ width: 1, height: 24, backgroundColor: 'rgba(51,65,85,0.4)' }} />

        {/* Status chips */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Chip color={connected ? '#10B981' : '#EF4444'} pulse={connected}>
            {connected ? 'WS Connected' : 'Disconnected'}
          </Chip>
          <Chip color="#D4AF37">
            {missionStatus === 'running' ? 'MISSION ACTIVE' : missionStatus === 'completed' ? 'COMPLETE' : missionStatus === 'failed' ? 'FAILED' : 'IDLE'}
          </Chip>
        </div>

        {/* Counters */}
        <div style={{ flex: 1 }} />
        <div style={{ display: 'flex', gap: 12, fontSize: 10, color: '#94A3B8' }}>
          <span><b style={{ color: '#00D9FF' }}>{runningCount}</b> running</span>
          <span><b style={{ color: '#10B981' }}>{completedCount}</b> done</span>
          <span><b style={{ color: '#EF4444' }}>{errorCount}</b> errors</span>
          <span><b style={{ color: '#64748B' }}>{events.length}</b> events</span>
        </div>

        {/* Toggle side panel */}
        <button
          onClick={() => setSideOpen(p => !p)}
          style={{
            background: 'none',
            border: '1px solid rgba(51,65,85,0.4)',
            borderRadius: 4,
            padding: '4px 8px',
            color: '#94A3B8',
            fontSize: 10,
            cursor: 'pointer',
          }}
        >
          {sideOpen ? 'Hide Panel' : 'Show Panel'}
        </button>
      </header>

      {/* ── Main area ────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

        {/* Canvas area */}
        <div style={{ flex: 1, padding: 12, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0 }}>
          <AgentCanvas agentStates={agentStates} />

          {/* Spawn Deck — dynamic agents created by SpawnerAgent */}
          <SpawnDeck spawnedAgents={spawnedAgents} />

          {/* Quick agent status bar under canvas */}
          <div style={{
            display: 'flex', gap: 4, flexWrap: 'wrap', padding: '4px 0',
          }}>
            {Object.entries(agentStates).map(([name, state]) => (
              <div
                key={name}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '3px 8px',
                  borderRadius: 4,
                  background: 'rgba(19,24,35,0.7)',
                  border: `1px solid ${state.status === 'running' ? AGENT_COLORS[name] || '#1A2332' : 'rgba(26,35,50,0.5)'}`,
                  fontSize: 9,
                }}
              >
                <span style={{
                  width: 6, height: 6, borderRadius: 2,
                  backgroundColor: AGENT_COLORS[name] || '#94A3B8',
                  opacity: state.status === 'idle' ? 0.3 : 1,
                }} />
                <span style={{ color: '#CBD5E1' }}>{name.replace('Agent', '')}</span>
                <span style={{
                  color:
                    state.status === 'running'   ? '#00D9FF' :
                    state.status === 'completed' ? '#10B981' :
                    state.status === 'error'     ? '#EF4444' :
                    state.status === 'waiting'   ? '#F59E0B' :
                    '#475569',
                  fontWeight: 600,
                }}>{state.status}</span>
                {state.progress > 0 && state.progress < 1 && (
                  <span style={{ color: '#64748B' }}>{Math.round(state.progress * 100)}%</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ── Side panel ─────────────────────────────────────────────── */}
        {sideOpen && (
          <aside style={{
            width: 320,
            borderLeft: '1px solid rgba(26,35,50,0.6)',
            display: 'flex',
            flexDirection: 'column',
            flexShrink: 0,
            overflow: 'hidden',
            background: 'rgba(10,14,26,0.5)',
          }}>

            {/* Mission Control */}
            <div style={{ padding: 12, borderBottom: '1px solid rgba(26,35,50,0.5)' }}>
              <SectionTitle color="#D4AF37">Mission Control</SectionTitle>
              <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
                <div>
                  <Label>Mission Type</Label>
                  <select
                    value={selectedMission}
                    onChange={e => setSelectedMission(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#0A0E1A',
                      border: '1px solid rgba(26,35,50,0.8)',
                      borderRadius: 4,
                      padding: '6px 8px',
                      fontSize: 11,
                      color: '#F1F5F9',
                      fontFamily: 'inherit',
                    }}
                  >
                    {MISSION_TYPES.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                  <p style={{ fontSize: 9, color: '#64748B', marginTop: 4 }}>
                    {MISSION_TYPES.find(m => m.value === selectedMission)?.desc}
                  </p>
                </div>
                <div>
                  <Label>Tickers</Label>
                  <input
                    type="text"
                    value={tickerInput}
                    onChange={e => setTickerInput(e.target.value)}
                    placeholder="AAPL,MSFT,GOOGL"
                    style={{
                      width: '100%',
                      background: '#0A0E1A',
                      border: '1px solid rgba(26,35,50,0.8)',
                      borderRadius: 4,
                      padding: '6px 8px',
                      fontSize: 11,
                      color: '#F1F5F9',
                      fontFamily: 'inherit',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    onClick={handleStart}
                    disabled={missionStatus === 'running' || !connected}
                    style={{
                      flex: 1,
                      padding: '7px 0',
                      borderRadius: 4,
                      border: 'none',
                      fontFamily: 'inherit',
                      fontSize: 11,
                      fontWeight: 700,
                      cursor: missionStatus === 'running' || !connected ? 'not-allowed' : 'pointer',
                      background: missionStatus === 'running' || !connected ? 'rgba(212,175,55,0.3)' : '#D4AF37',
                      color: '#0A0E1A',
                    }}
                  >
                    {missionStatus === 'running' ? 'Running...' : 'Start Mission'}
                  </button>
                  {missionStatus === 'running' && (
                    <button
                      onClick={cancelMission}
                      style={{
                        padding: '7px 12px',
                        borderRadius: 4,
                        border: '1px solid rgba(239,68,68,0.3)',
                        background: 'rgba(239,68,68,0.1)',
                        color: '#EF4444',
                        fontFamily: 'inherit',
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Event Log — fills remaining space */}
            <div style={{
              flex: 1,
              padding: 12,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <SectionTitle color="#94A3B8">Event Log</SectionTitle>
                <button
                  onClick={clearEvents}
                  style={{
                    background: 'none', border: 'none', color: '#475569',
                    fontSize: 9, cursor: 'pointer', fontFamily: 'inherit',
                  }}
                >
                  Clear
                </button>
              </div>
              <div style={{
                flex: 1,
                overflowY: 'auto',
                fontSize: 9,
                lineHeight: '16px',
              }}>
                {events.length === 0 && (
                  <p style={{ color: '#475569', fontStyle: 'italic' }}>No events yet. Start a mission.</p>
                )}
                {events.slice(-80).reverse().map((evt, i) => (
                  <div key={i} style={{ display: 'flex', gap: 6, color: '#94A3B8' }}>
                    <span style={{
                      color: AGENT_COLORS[evt.agent] || '#94A3B8',
                      flexShrink: 0,
                    }}>
                      [{evt.agent?.replace('Agent', '') || 'SYS'}]
                    </span>
                    <span style={{ color: '#CBD5E1' }}>{evt.event}</span>
                    {evt.data && Object.keys(evt.data).length > 0 && (
                      <span style={{
                        color: '#475569',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: 120,
                      }}>
                        {JSON.stringify(evt.data).slice(0, 60)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

/* ── Spawn Deck ──────────────────────────────────────────────────────── */

const SPAWN_COLORS: Record<string, string> = {
  CorrelationAgent:  '#06B6D4',
  StressDetailAgent: '#EF4444',
  MomentumAgent:     '#F59E0B',
  SummaryAgent:      '#10B981',
};

function SpawnDeck({ spawnedAgents }: { spawnedAgents: Record<string, SpawnedAgent> }) {
  const entries = Object.values(spawnedAgents);
  if (entries.length === 0) return null;

  return (
    <div style={{
      borderTop: '1px solid rgba(139,92,246,0.3)',
      paddingTop: 8,
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{
          fontSize: 8, fontWeight: 700, color: '#8B5CF6',
          letterSpacing: '0.12em', textTransform: 'uppercase',
        }}>
          ◈  Spawn Deck  ◈
        </span>
        <span style={{
          fontSize: 8, color: '#64748B',
          background: 'rgba(139,92,246,0.1)',
          border: '1px solid rgba(139,92,246,0.25)',
          borderRadius: 999, padding: '1px 6px',
        }}>
          {entries.length} agent{entries.length > 1 ? 's' : ''} dynamiques
        </span>
      </div>

      {/* Cards */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {entries.map(ag => {
          const col = SPAWN_COLORS[ag.name] ?? '#8B5CF6';
          const done = ag.status === 'completed';
          return (
            <div
              key={ag.name}
              style={{
                padding: '6px 10px',
                borderRadius: 6,
                background: 'rgba(13,18,30,0.85)',
                border: `1px solid ${done ? col : `${col}66`}`,
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
                minWidth: 140,
              }}
            >
              {/* Name + status dot */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  backgroundColor: col,
                  boxShadow: done ? 'none' : `0 0 5px ${col}`,
                }} />
                <span style={{ fontSize: 9, fontWeight: 700, color: '#F1F5F9' }}>
                  {ag.name.replace('Agent', '')}
                </span>
                <span style={{
                  marginLeft: 'auto', fontSize: 8, fontWeight: 600,
                  color: done ? '#10B981' : ag.status === 'error' ? '#EF4444' : col,
                }}>
                  {ag.status}
                </span>
              </div>

              {/* Progress bar */}
              <div style={{
                height: 3, borderRadius: 2,
                background: 'rgba(255,255,255,0.06)',
                overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${Math.round(ag.progress * 100)}%`,
                  background: col,
                  borderRadius: 2,
                  transition: 'width 0.3s ease',
                }} />
              </div>

              {/* Last event */}
              <span style={{ fontSize: 8, color: '#475569', fontStyle: 'italic' }}>
                {ag.lastEvent || 'waiting…'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Tiny sub-components ─────────────────────────────────────────────── */

function Chip({ color, pulse, children }: { color: string; pulse?: boolean; children: React.ReactNode }) {
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      padding: '2px 8px',
      borderRadius: 999,
      fontSize: 9,
      fontWeight: 600,
      color,
      border: `1px solid ${color}33`,
      background: `${color}10`,
      letterSpacing: '0.04em',
    }}>
      <span style={{
        width: 5, height: 5, borderRadius: '50%',
        backgroundColor: color,
        boxShadow: pulse ? `0 0 6px ${color}` : 'none',
        animation: pulse ? 'pulse 2s infinite' : 'none',
      }} />
      {children}
    </span>
  );
}

function SectionTitle({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <h2 style={{
      fontSize: 9,
      fontWeight: 700,
      color,
      textTransform: 'uppercase',
      letterSpacing: '0.12em',
      margin: 0,
    }}>
      {children}
    </h2>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <label style={{ display: 'block', fontSize: 9, color: '#94A3B8', marginBottom: 4 }}>
      {children}
    </label>
  );
}
