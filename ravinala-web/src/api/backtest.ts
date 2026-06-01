import api from "./client";

// ── Types ────────────────────────────────────────────────────────────────────

export interface BacktestRequest {
  strategy: string;
  tickers: string[];
  start_date: string;
  end_date: string;
  initial_capital?: number;
  params?: Record<string, unknown>;
}

export interface BacktestRun {
  id: string;
  strategy: string;
  status: "running" | "completed" | "failed";
  created_at: string;
  metrics?: BacktestMetrics;
}

export interface BacktestMetrics {
  total_return: number;
  annualized_return: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  win_rate: number;
  profit_factor: number;
  total_trades: number;
}

export interface StrategyInfo {
  name: string;
  description: string;
  params: Record<
    string,
    { type: string; default: unknown; description: string }
  >;
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function runBacktest(request: BacktestRequest) {
  const { data } = await api.post<{ data: unknown }>("/api/v1/backtest/run", request);
  return data.data;
}

export async function runBacktestAsync(request: BacktestRequest) {
  const { data } = await api.post<{ data: { job_id: string } }>("/api/v1/backtest/run/async", request);
  return data.data as { job_id: string };
}

export async function fetchBacktestRuns(): Promise<BacktestRun[]> {
  const { data } = await api.get<{ data: BacktestRun[] }>("/api/v1/backtest/runs");
  return data.data ?? [];
}

export async function fetchBacktestRun(runId: string): Promise<BacktestRun> {
  const { data } = await api.get<{ data: BacktestRun }>(`/api/v1/backtest/runs/${runId}`);
  return data.data;
}

export async function fetchStrategies(): Promise<StrategyInfo[]> {
  const { data } = await api.get<{ data: StrategyInfo[] }>("/api/v1/backtest/strategies");
  return data.data ?? [];
}

export async function fetchLimitations() {
  const { data } = await api.get<{ data: unknown }>("/api/v1/backtest/limitations");
  return data.data;
}
