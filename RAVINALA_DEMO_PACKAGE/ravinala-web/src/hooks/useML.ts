import { useMutation, useQuery } from "@tanstack/react-query";
import {
  fetchMLModels,
  fetchMLRun,
  fetchMLRuns,
  predict,
  trainModel,
  type PredictRequest,
  type TrainRequest,
} from "../api/ml";

export const mlKeys = {
  all: ["ml"] as const,
  runs: () => ["ml", "runs"] as const,
  run: (id: string) => ["ml", "runs", id] as const,
  models: () => ["ml", "models"] as const,
};

export function useMLRuns() {
  return useQuery({
    queryKey: mlKeys.runs(),
    queryFn: fetchMLRuns,
    staleTime: 30_000,
  });
}

export function useMLRun(runId: string) {
  return useQuery({
    queryKey: mlKeys.run(runId),
    queryFn: () => fetchMLRun(runId),
    enabled: !!runId,
    staleTime: 10_000,
  });
}

export function useMLModels() {
  return useQuery({
    queryKey: mlKeys.models(),
    queryFn: fetchMLModels,
    staleTime: 5 * 60_000,
  });
}

export function useTrainModel() {
  return useMutation({
    mutationFn: (request: TrainRequest) => trainModel(request),
  });
}

export function usePredict() {
  return useMutation({
    mutationFn: (request: PredictRequest) => predict(request),
  });
}
