import api from "./client";

// ── Types ────────────────────────────────────────────────────────────────────

export interface OptimizeRequest {
  tickers: string[];
  method?: "mean_variance" | "risk_parity" | "max_sharpe" | "min_variance";
  constraints?: Record<string, unknown>;
}

export interface OptimizeResult {
  weights: Record<string, number>;
  expected_return: number;
  volatility: number;
  sharpe_ratio: number;
  method: string;
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function optimizePortfolio(
  request: OptimizeRequest,
): Promise<OptimizeResult> {
  const { data } = await api.post<{ data: OptimizeResult }>("/api/v1/portfolio/optimize", request);
  return data.data;
}

export async function optimizePortfolioAsync(request: OptimizeRequest) {
  const { data } = await api.post<{ data: { job_id: string } }>("/api/v1/portfolio/optimize/async", request);
  return data.data as { job_id: string };
}
