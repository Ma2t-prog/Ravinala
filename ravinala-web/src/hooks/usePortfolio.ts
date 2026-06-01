import { useMutation } from "@tanstack/react-query";
import { optimizePortfolio, type OptimizeRequest } from "../api/portfolio";

export const portfolioKeys = {
  all: ["portfolio"] as const,
  optimize: () => ["portfolio", "optimize"] as const,
};

export function useOptimizePortfolio() {
  return useMutation({
    mutationFn: (request: OptimizeRequest) => optimizePortfolio(request),
  });
}
