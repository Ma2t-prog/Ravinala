import api from "./client";

// ── Types ────────────────────────────────────────────────────────────────────

export interface TrainRequest {
  model_type: string;
  ticker: string;
  features?: string[];
  params?: Record<string, unknown>;
}

export interface PredictRequest {
  model_id: string;
  ticker: string;
  horizon?: number;
}

export interface MLRun {
  id: string;
  model_type: string;
  ticker: string;
  status: "training" | "completed" | "failed";
  created_at: string;
  metrics?: {
    directional_accuracy: number;
    rmse: number;
    mae: number;
  };
}

export interface MLModel {
  id: string;
  model_type: string;
  ticker: string;
  version: string;
  created_at: string;
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function trainModel(request: TrainRequest) {
  const { data } = await api.post("/api/v1/ml/train", request);
  return (data as any).data;
}

export async function trainModelAsync(request: TrainRequest) {
  const { data } = await api.post("/api/v1/ml/train/async", request);
  return (data as any).data as { job_id: string };
}

export async function predict(request: PredictRequest) {
  const { data } = await api.post("/api/v1/ml/predict", request);
  return (data as any).data;
}

export async function fetchMLRuns(): Promise<MLRun[]> {
  const { data } = await api.get<{ data: MLRun[] }>("/api/v1/ml/runs");
  return data.data ?? [];
}

export async function fetchMLRun(runId: string): Promise<MLRun> {
  const { data } = await api.get<{ data: MLRun }>(`/api/v1/ml/runs/${runId}`);
  return data.data;
}

export async function fetchMLModels(): Promise<MLModel[]> {
  const { data } = await api.get<{ data: MLModel[] }>("/api/v1/ml/models");
  return data.data ?? [];
}
