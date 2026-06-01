import { useQuery } from "@tanstack/react-query";
import {
  fetchAlerts,
  fetchDataQuality,
  fetchDeepHealth,
  fetchMonitoringMetrics,
  fetchSystemStatus,
} from "../api/monitoring";

export const monitoringKeys = {
  all: ["monitoring"] as const,
  health: () => ["monitoring", "health"] as const,
  metrics: () => ["monitoring", "metrics"] as const,
  quality: () => ["monitoring", "quality"] as const,
  alerts: () => ["monitoring", "alerts"] as const,
  status: () => ["monitoring", "status"] as const,
};

export function useDeepHealth() {
  return useQuery({
    queryKey: monitoringKeys.health(),
    queryFn: fetchDeepHealth,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function useMonitoringMetrics() {
  return useQuery({
    queryKey: monitoringKeys.metrics(),
    queryFn: fetchMonitoringMetrics,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useDataQuality() {
  return useQuery({
    queryKey: monitoringKeys.quality(),
    queryFn: fetchDataQuality,
    staleTime: 5 * 60_000,
  });
}

export function useAlerts() {
  return useQuery({
    queryKey: monitoringKeys.alerts(),
    queryFn: fetchAlerts,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function useSystemStatus() {
  return useQuery({
    queryKey: monitoringKeys.status(),
    queryFn: fetchSystemStatus,
    staleTime: 5 * 60_000,
  });
}
