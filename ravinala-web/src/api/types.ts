export interface IndexItem {
  symbol: string;
  name: string;
  region: string;
  price: number;
  change: {
    percent: number;
    absolute: number;
    direction?: string;
    color?: string;
  };
  timestamp: string;
  is_stale?: boolean;
  data_source?: string;
}

/**
 * Data quality level propagated from the backend's data_fetcher.py.
 * Mirrors the DataQuality Literal in app/schemas/envelope.py.
 */
export type DataQuality =
  | "live"
  | "demo_static"
  | "stale_cache"
  | "error"
  | "mixed"
  | "unknown";

export interface BondItem {
  country: string;
  country_code: string;
  yield_2y?: number;
  yield_5y?: number;
  yield_10y?: number;
  spread_vs_bund_bp?: number;
}

export interface FXPair {
  symbol: string;
  base: string;
  quote: string;
  rate: number;
  change: { percent: number; absolute: number };
}

/** Raw FX item as returned by the backend */
export interface RawFXItem {
  pair: string;
  bid: number;
  ask: number;
  mid_price: number;
  change_percent: number;
  volatility_percent: number;
  last_updated: string;
}

/** Raw commodity item as returned by the backend */
export interface RawCommodityItem {
  symbol: string;
  name: string;
  category: string;
  price: number;
  unit: string;
  change_percent: number;
  timestamp: string;
}

export interface Commodity {
  symbol: string;
  name: string;
  category: string;
  price: number;
  unit: string;
  change: { percent: number; absolute: number };
}

export interface MacroIndicator {
  country: string;
  indicator: string;
  value: number;
  previous?: number;
  unit: string;
  period: string;
}

export interface FullSnapshot {
  indices: Record<string, IndexItem[]>;
  bonds: { bonds: BondItem[] };
  fx: { pairs: FXPair[] };
  commodities: Record<string, Commodity[]>;
  macro: { indicators: MacroIndicator[] };
  timestamp: string;
  cache_hit: boolean;
  data_quality: DataQuality;
}

/** Raw snapshot as returned by the backend (before normalization) */
export interface RawSnapshot {
  indices: Record<string, IndexItem[]>;
  bonds: {
    bonds: BondItem[];
    benchmark_country?: string;
    last_updated?: string;
    cache_age_seconds?: number;
  };
  fx: {
    usd_base: RawFXItem[];
    crosses: RawFXItem[];
    last_updated?: string;
    cache_age_seconds?: number;
  };
  commodities: Record<
    string,
    (RawCommodityItem | { last_updated?: string; cache_age_seconds?: number })[]
  >;
  macro: {
    indicators: MacroIndicator[];
    last_updated?: string;
    cache_age_seconds?: number;
  };
  timestamp: string;
  cache_hit: boolean;
}

export interface ProductParams {
  product_type: string;
  product_name?: string;
  underlying?: string;
  strike?: number;
  barrier?: number;
  maturity?: string;
  notional?: number;
  currency?: string;
  coupon?: number;
  participation?: number;
  protection_level?: number;
  observation_frequency?: string;
  client_name?: string;
  notes?: string;
}

export interface ScenarioBookParams {
  product: ProductParams;
  spot_range?: [number, number];
  vol_range?: [number, number];
  steps?: number;
  client_name?: string;
  notes?: string;
}

export interface HealthCheck {
  status: string;
  timestamp: string;
  redis_connected: boolean;
  data_service_ok: boolean;
}

export interface ExportExcelPayload {
  sheets: string[];
}

export interface RefreshResponse {
  success: boolean;
  section?: string;
  message?: string;
}
