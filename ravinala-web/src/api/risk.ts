import api from "./client";

// ── Types ────────────────────────────────────────────────────────────────────

export interface VaRRequest {
  portfolio: string[];
  weights?: number[];
  method?: "historical" | "parametric" | "montecarlo";
  confidence?: number;
  horizon_days?: number;
}

export interface RiskMetrics {
  var_95: number;
  var_99: number;
  cvar_95: number;
  cvar_99: number;
  volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
  beta: number;
}

export interface RiskConventions {
  trading_days: number;
  risk_free_rate: number;
  var_methods: string[];
  confidence_levels: number[];
}

export interface RiskSnapshot {
  id: string;
  computed_at: string;
  metrics: RiskMetrics;
  portfolio: string[];
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function computeRisk(request: VaRRequest) {
  const { data } = await api.post("/api/v1/risk/compute", request);
  return data.data;
}

export async function computeRiskAsync(request: VaRRequest) {
  const { data } = await api.post("/api/v1/risk/compute/async", request);
  return (data as any).data as { job_id: string };
}

export async function fetchRiskConventions(): Promise<RiskConventions> {
  const { data } = await api.get<{ data: RiskConventions }>("/api/v1/risk/conventions");
  return data.data;
}

export async function fetchRiskMetrics() {
  const { data } = await api.get("/api/v1/risk/metrics");
  return data.data;
}

export async function fetchRiskMetricByName(name: string) {
  const { data } = await api.get(`/api/v1/risk/metrics/${name}`);
  return data.data;
}

export async function fetchGovernanceLevels() {
  const { data } = await api.get("/api/v1/risk/governance-levels");
  return data.data;
}

export async function fetchRiskIncoherences() {
  const { data } = await api.get("/api/v1/risk/incoherences");
  return data.data;
}

export async function fetchRiskSnapshots(): Promise<RiskSnapshot[]> {
  const { data } = await api.get<{ data: RiskSnapshot[] }>("/api/v1/risk/snapshots");
  return data.data ?? [];
}
