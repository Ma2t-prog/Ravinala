import { useState, useEffect, useCallback, useRef } from 'react';

export interface AgentEvent {
  agent: string;
  event: string;
  data: Record<string, unknown>;
  status: 'idle' | 'running' | 'completed' | 'error' | 'waiting';
  progress: number;
  timestamp: number;
  dynamic?: boolean;
  spawned_agent?: string;
}

export interface AgentState {
  status: 'idle' | 'running' | 'completed' | 'error' | 'waiting';
  progress: number;
  lastEvent: string;
  lastData: Record<string, unknown>;
}

export interface SpawnedAgent {
  name: string;
  status: 'running' | 'completed' | 'error';
  progress: number;
  lastEvent: string;
  spawnedAt: number;
}

interface UseAgentMonitorReturn {
  connected: boolean;
  events: AgentEvent[];
  agentStates: Record<string, AgentState>;
  spawnedAgents: Record<string, SpawnedAgent>;
  missionStatus: 'idle' | 'running' | 'completed' | 'failed';
  missionId: string | null;
  startMission: (missionType: string, params?: Record<string, unknown>) => void;
  cancelMission: () => void;
  clearEvents: () => void;
}

const WS_PORT = import.meta.env.VITE_API_PORT ?? '8000';
const WS_URL = `ws://${window.location.hostname}:${WS_PORT}/api/v1/agents/stream`;
const MAX_EVENTS = 500;

const DEFAULT_AGENT_NAMES = [
  'OrchestratorAgent', 'MarketAgent', 'AnalysisAgent', 'RiskAgent',
  'PortfolioAgent', 'BacktestAgent', 'MLAgent', 'MonitoringAgent',
  'ErrorHandlerAgent', 'LoggerAgent', 'ReportAgent', 'AlertAgent',
  'SpawnerAgent',
];

function buildInitialStates(): Record<string, AgentState> {
  const initial: Record<string, AgentState> = {};
  for (const name of DEFAULT_AGENT_NAMES) {
    initial[name] = { status: 'idle', progress: 0, lastEvent: '', lastData: {} };
  }
  return initial;
}

export function useAgentMonitor(): UseAgentMonitorReturn {
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [missionStatus, setMissionStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [missionId, setMissionId] = useState<string | null>(null);
  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>(() => buildInitialStates());
  const [spawnedAgents, setSpawnedAgents] = useState<Record<string, SpawnedAgent>>({});

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (msg) => {
      try {
        const event: AgentEvent = JSON.parse(msg.data);

        setEvents(prev => {
          const next = [...prev, event];
          return next.length > MAX_EVENTS ? next.slice(-MAX_EVENTS) : next;
        });

        // Dynamic spawned agent event
        if (event.dynamic && event.spawned_agent) {
          const sName = event.spawned_agent;
          setSpawnedAgents(prev => ({
            ...prev,
            [sName]: {
              name:       sName,
              status:     event.status === 'completed' ? 'completed' : event.status === 'error' ? 'error' : 'running',
              progress:   event.progress,
              lastEvent:  event.event,
              spawnedAt:  prev[sName]?.spawnedAt ?? event.timestamp,
            },
          }));
        }

        // Regular agent state update
        if (event.agent && event.agent !== 'System' && !event.dynamic) {
          setAgentStates(prev => ({
            ...prev,
            [event.agent]: {
              status:    event.status,
              progress:  event.progress,
              lastEvent: event.event,
              lastData:  event.data,
            },
          }));
        }

        if (event.event === 'mission_accepted') {
          setMissionStatus('running');
          setMissionId(event.data.mission_id as string);
        } else if (event.event === 'mission_complete') {
          setMissionStatus('completed');
        } else if (event.event === 'mission_failed') {
          setMissionStatus('failed');
        }
      } catch (e) {
        console.warn('[AgentMonitor] Failed to parse WS message:', e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const startMission = useCallback((missionType: string, params: Record<string, unknown> = {}) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;

    setAgentStates(buildInitialStates());
    setSpawnedAgents({});
    setEvents([]);
    setMissionStatus('idle');

    wsRef.current.send(JSON.stringify({
      action: 'start',
      mission_type: missionType,
      params,
    }));
  }, []);

  const cancelMission = useCallback(() => {
    if (!wsRef.current || !missionId) return;
    wsRef.current.send(JSON.stringify({
      action: 'cancel',
      mission_id: missionId,
    }));
    setMissionStatus('idle');
  }, [missionId]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return {
    connected,
    events,
    agentStates,
    spawnedAgents,
    missionStatus,
    missionId,
    startMission,
    cancelMission,
    clearEvents,
  };
}
