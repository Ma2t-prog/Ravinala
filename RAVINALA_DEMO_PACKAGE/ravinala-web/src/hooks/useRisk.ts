import { useMutation, useQuery } from "@tanstack/react-query";
import {
  computeRisk,
  fetchGovernanceLevels,
  fetchRiskConventions,
  fetchRiskIncoherences,
  fetchRiskMetrics,
  fetchRiskSnapshots,
  type VaRRequest,
} from "../api/risk";

export const riskKeys = {
  all: ["risk"] as const,
  conventions: () => ["risk", "conventions"] as const,
  metrics: () => ["risk", "metrics"] as const,
  snapshots: () => ["risk", "snapshots"] as const,
  governance: () => ["risk", "governance"] as const,
  incoherences: () => ["risk", "incoherences"] as const,
};

export function useRiskConventions() {
  return useQuery({
    queryKey: riskKeys.conventions(),
    queryFn: fetchRiskConventions,
    staleTime: 24 * 60 * 60_000,
  });
}

export function useRiskMetrics() {
  return useQuery({
    queryKey: riskKeys.metrics(),
    queryFn: fetchRiskMetrics,
    staleTime: 5 * 60_000,
  });
}

export function useRiskSnapshots() {
  return useQuery({
    queryKey: riskKeys.snapshots(),
    queryFn: fetchRiskSnapshots,
    staleTime: 5 * 60_000,
  });
}

export function useGovernanceLevels() {
  return useQuery({
    queryKey: riskKeys.governance(),
    queryFn: fetchGovernanceLevels,
    staleTime: 60 * 60_000,
  });
}

export function useRiskIncoherences() {
  return useQuery({
    queryKey: riskKeys.incoherences(),
    queryFn: fetchRiskIncoherences,
    staleTime: 5 * 60_000,
  });
}

export function useComputeRisk() {
  return useMutation({
    mutationFn: (request: VaRRequest) => computeRisk(request),
  });
}
