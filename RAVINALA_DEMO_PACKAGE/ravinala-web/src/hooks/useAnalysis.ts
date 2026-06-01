import { useMutation } from "@tanstack/react-query";
import { analyzeCompany, type CompanyAnalysisRequest } from "../api/analysis";

export const analysisKeys = {
  all: ["analysis"] as const,
  company: (ticker: string) => ["analysis", "company", ticker] as const,
};

export function useAnalyzeCompany() {
  return useMutation({
    mutationFn: (request: CompanyAnalysisRequest) => analyzeCompany(request),
  });
}
