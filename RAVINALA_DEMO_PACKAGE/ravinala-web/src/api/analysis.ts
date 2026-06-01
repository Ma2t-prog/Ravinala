import api from "./client";

// ── Types ────────────────────────────────────────────────────────────────────

export interface CompanyAnalysisRequest {
  ticker: string;
  modules?: string[];
}

export interface CompanyAnalysisResult {
  ticker: string;
  company_name: string;
  analysis: Record<string, unknown>;
}

// ── API Functions ────────────────────────────────────────────────────────────

export async function analyzeCompany(
  request: CompanyAnalysisRequest,
): Promise<CompanyAnalysisResult> {
  const { data } = await api.post<{ data: CompanyAnalysisResult }>("/api/v1/analysis/company", request);
  return data.data;
}

export async function analyzeCompanyAsync(request: CompanyAnalysisRequest) {
  const { data } = await api.post<{ data: { job_id: string; status: string } }>("/api/v1/analysis/company/async", request);
  return data.data as { job_id: string };
}
