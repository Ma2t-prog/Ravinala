import { useMutation, useQuery } from "@tanstack/react-query";
import {
  fetchBacktestRun,
  fetchBacktestRuns,
  fetchLimitations,
  fetchStrategies,
  runBacktest,
  type BacktestRequest,
} from "../api/backtest";

export const backtestKeys = {
  all: ["backtest"] as const,
  runs: () => ["backtest", "runs"] as const,
  run: (id: string) => ["backtest", "runs", id] as const,
  strategies: () => ["backtest", "strategies"] as const,
  limitations: () => ["backtest", "limitations"] as const,
};

export function useBacktestRuns() {
  return useQuery({
    queryKey: backtestKeys.runs(),
    queryFn: fetchBacktestRuns,
    staleTime: 30_000,
  });
}

export function useBacktestRun(runId: string) {
  return useQuery({
    queryKey: backtestKeys.run(runId),
    queryFn: () => fetchBacktestRun(runId),
    enabled: !!runId,
    staleTime: 10_000,
  });
}

export function useStrategies() {
  return useQuery({
    queryKey: backtestKeys.strategies(),
    queryFn: fetchStrategies,
    staleTime: 60 * 60_000,
  });
}

export function useLimitations() {
  return useQuery({
    queryKey: backtestKeys.limitations(),
    queryFn: fetchLimitations,
    staleTime: 24 * 60 * 60_000,
  });
}

export function useRunBacktest() {
  return useMutation({
    mutationFn: (request: BacktestRequest) => runBacktest(request),
  });
}
