import api from "./client";

// ── Types ────────────────────────────────────────────────────────────────────

export interface HealthDeep {
  status: string;
  database: string;
  redis: string;
  celery: string;
  uptime_seconds: number;
}

export interface MonitoringMetrics {
  requests_total: number;
  requests_per_minute: number;
  avg_response_time_ms: number;
  error_rate: number;
}

export interface DataQualityReport {
  sources: Record<
    string,
    { status: string; last_update: string; staleness_seconds: number }
  >;
  overall_quality: string;
}

export interface Alert {
  id: string;
  severity: "info" | "warning" | "critical";
  message: string;
  source: string;
  created_at: string;
  resolved: boolean;
}

export interface SystemStatus {
  version: string;
  environment: string;
  features: Record<string, boolean>;
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function fetchDeepHealth(): Promise<HealthDeep> {
  const { data } = await api.get("/api/v1/monitoring/health/deep");
  return data;
}

export async function fetchMonitoringMetrics(): Promise<MonitoringMetrics> {
  const { data } = await api.get("/api/v1/monitoring/metrics/json");
  return data;
}

export async function fetchDataQuality(): Promise<DataQualityReport> {
  const { data } = await api.get("/api/v1/monitoring/data-quality");
  return data;
}

export async function fetchAlerts(): Promise<Alert[]> {
  const { data } = await api.get("/api/v1/monitoring/alerts");
  return data;
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const { data } = await api.get("/api/v1/monitoring/status");
  return data;
}
