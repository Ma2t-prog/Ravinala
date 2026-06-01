import { useQuery } from '@tanstack/react-query'
import {
  fetchHealth,
  fetchSnapshot,
  fetchIndices,
  fetchBonds,
  fetchFX,
  fetchCommodities,
  fetchMacro,
} from '../api/market'
import type {
  FullSnapshot,
  IndexItem,
  BondItem,
  FXPair,
  Commodity,
  MacroIndicator,
  HealthCheck,
} from '../api/types'

// ─── Query key factory ────────────────────────────────────────────────────────
// Centralising keys makes targeted cache invalidation straightforward.

export const marketKeys = {
  all: ['market'] as const,
  health: () => ['health'] as const,
  snapshot: (sections?: string) => ['market', 'snapshot', sections ?? 'all'] as const,
  indices: (zones?: string) => ['market', 'indices', zones ?? 'all'] as const,
  bonds: (countries?: string, maturities?: string) =>
    ['market', 'bonds', countries ?? 'all', maturities ?? 'all'] as const,
  fx: (base?: string, limit?: number) =>
    ['market', 'fx', base ?? 'USD', limit ?? 'default'] as const,
  commodities: (categories?: string) =>
    ['market', 'commodities', categories ?? 'all'] as const,
  macro: (countries?: string) => ['market', 'macro', countries ?? 'all'] as const,
}

// ─── Hooks ────────────────────────────────────────────────────────────────────

/**
 * Full market snapshot. Refreshed every 60 seconds.
 */
export function useSnapshot(sections?: string) {
  return useQuery<FullSnapshot, Error>({
    queryKey: marketKeys.snapshot(sections),
    queryFn: () => fetchSnapshot(sections),
    refetchInterval: 60_000,
    staleTime: 30_000,
  })
}

/**
 * Equity indices by zone. Refreshed every 5 minutes.
 */
export function useIndices(zones?: string, limit?: number) {
  return useQuery<Record<string, IndexItem[]>, Error>({
    queryKey: marketKeys.indices(zones),
    queryFn: () => fetchIndices(zones, limit),
    refetchInterval: 300_000,
    staleTime: 150_000,
  })
}

/**
 * Government bond yields. Refreshed every hour.
 */
export function useBonds(countries?: string, maturities?: string) {
  return useQuery<{ bonds: BondItem[] }, Error>({
    queryKey: marketKeys.bonds(countries, maturities),
    queryFn: () => fetchBonds(countries, maturities),
    refetchInterval: 3_600_000,
    staleTime: 1_800_000,
  })
}

/**
 * FX spot rates. Refreshed every 5 minutes.
 */
export function useFX(base?: string, limit?: number) {
  return useQuery<{ pairs: FXPair[] }, Error>({
    queryKey: marketKeys.fx(base, limit),
    queryFn: () => fetchFX(base, limit),
    refetchInterval: 300_000,
    staleTime: 150_000,
  })
}

/**
 * Commodity prices by category. Refreshed every 5 minutes.
 */
export function useCommodities(categories?: string) {
  return useQuery<Record<string, Commodity[]>, Error>({
    queryKey: marketKeys.commodities(categories),
    queryFn: () => fetchCommodities(categories),
    refetchInterval: 300_000,
    staleTime: 150_000,
  })
}

/**
 * Macroeconomic indicators. Refreshed once per day.
 */
export function useMacro(countries?: string) {
  return useQuery<{ indicators: MacroIndicator[] }, Error>({
    queryKey: marketKeys.macro(countries),
    queryFn: () => fetchMacro(countries),
    refetchInterval: 86_400_000,
    staleTime: 43_200_000,
  })
}

/**
 * Backend health check. Refreshed every 30 seconds.
 */
export function useHealth() {
  return useQuery<HealthCheck, Error>({
    queryKey: marketKeys.health(),
    queryFn: fetchHealth,
    refetchInterval: 30_000,
    staleTime: 15_000,
    // Do not retry aggressively — a failed health check should surface quickly.
    retry: 1,
  })
}
