import api from "./client";
import type {
  BondItem,
  Commodity,
  DataQuality,
  FullSnapshot,
  FXPair,
  HealthCheck,
  IndexItem,
  MacroIndicator,
  ProductParams,
  RawCommodityItem,
  RawFXItem,
  RawSnapshot,
  RefreshResponse,
  ScenarioBookParams,
} from "./types";

// ─── Transform helpers ───────────────────────────────────────────────────────

function transformFXItem(raw: RawFXItem): FXPair {
  const parts = raw.pair.split("/");
  return {
    symbol: raw.pair.replace("/", ""),
    base: parts[0] ?? raw.pair.slice(0, 3),
    quote: parts[1] ?? raw.pair.slice(3),
    rate: raw.mid_price,
    change: {
      percent: raw.change_percent,
      absolute: (raw.mid_price * raw.change_percent) / 100,
    },
  };
}

function transformRawFXResponse(raw: {
  usd_base?: RawFXItem[];
  crosses?: RawFXItem[];
  [k: string]: unknown;
}): { pairs: FXPair[] } {
  const usd = (raw.usd_base ?? []).map(transformFXItem);
  const crosses = (raw.crosses ?? []).map(transformFXItem);
  return { pairs: [...usd, ...crosses] };
}

function transformRawCommodity(raw: RawCommodityItem): Commodity {
  return {
    symbol: raw.symbol,
    name: raw.name,
    category: raw.category,
    price: raw.price,
    unit: raw.unit,
    change: {
      percent: raw.change_percent,
      absolute: (raw.price * raw.change_percent) / 100,
    },
  };
}

function transformRawCommodities(
  raw: Record<string, unknown>,
): Record<string, Commodity[]> {
  const result: Record<string, Commodity[]> = {};
  for (const [key, value] of Object.entries(raw)) {
    if (key === "last_updated" || key === "cache_age_seconds") continue;
    if (Array.isArray(value)) {
      result[key] = value
        .filter(
          (item): item is RawCommodityItem =>
            item && typeof item === "object" && "symbol" in item,
        )
        .map(transformRawCommodity);
    }
  }
  return result;
}

function _stripMeta<T>(
  raw: Record<string, unknown>,
  isArray: boolean = false,
): T {
  if (!isArray) {
    const clean: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(raw)) {
      if (key === "last_updated" || key === "cache_age_seconds") continue;
      clean[key] = value;
    }
    return clean as T;
  }
  return raw as unknown as T;
}

// remap snake_case region keys like "asia_pacific" -> "Asia Pacific"
const REGION_MAP: Record<string, string> = {
  americas: "Americas",
  europe: "Europe",
  asia_pacific: "Asia Pacific",
  middle_east_other: "Middle East/Other",
};

function normalizeIndices(
  raw: Record<string, unknown>,
): Record<string, IndexItem[]> {
  const result: Record<string, IndexItem[]> = {};
  for (const [key, value] of Object.entries(raw)) {
    if (key === "last_updated" || key === "cache_age_seconds") continue;
    if (Array.isArray(value)) {
      const displayKey = REGION_MAP[key] ?? key;
      result[displayKey] = value as IndexItem[];
    }
  }
  return result;
}

// ─── Health ──────────────────────────────────────────────────────────────────

export async function fetchHealth(): Promise<HealthCheck> {
  const { data } = await api.get<HealthCheck>("/health", { baseURL: "" });
  return data;
}

// ─── Market data ─────────────────────────────────────────────────────────────

/**
 * GET /api/v1/snapshot
 * Returns the full dashboard payload for all sections.
 * Pass a comma-separated `sections` string to limit the response
 * (e.g. "indices,fx").
 */
export async function fetchSnapshot(sections?: string): Promise<FullSnapshot> {
  const params: Record<string, string> = {};
  if (sections) params["sections"] = sections;
  const { data } = await api.get<RawSnapshot>("/api/v1/snapshot", { params });
  return {
    indices: normalizeIndices(
      data.indices as unknown as Record<string, unknown>,
    ),
    bonds: { bonds: data.bonds?.bonds ?? [] },
    fx: transformRawFXResponse(
      data.fx as unknown as { usd_base?: RawFXItem[]; crosses?: RawFXItem[] },
    ),
    commodities: transformRawCommodities(
      data.commodities as unknown as Record<string, unknown>,
    ),
    macro: { indicators: data.macro?.indicators ?? [] },
    timestamp: data.timestamp,
    cache_hit: data.cache_hit,
    data_quality:
      ((data as unknown as Record<string, unknown>)
        .data_quality as DataQuality) ?? "unknown",
  };
}

/**
 * GET /api/v1/indices
 */
export async function fetchIndices(
  zones?: string,
  limit?: number,
): Promise<Record<string, IndexItem[]>> {
  const params: Record<string, string | number> = {};
  if (zones) params["zones"] = zones;
  if (limit !== undefined) params["limit"] = limit;
  const { data } = await api.get<Record<string, unknown>>("/api/v1/indices", {
    params,
  });
  return normalizeIndices(data);
}

/**
 * GET /api/v1/bonds
 */
export async function fetchBonds(
  countries?: string,
  maturities?: string,
): Promise<{ bonds: BondItem[] }> {
  const params: Record<string, string> = {};
  if (countries) params["countries"] = countries;
  if (maturities) params["maturities"] = maturities;
  const { data } = await api.get<{ bonds: BondItem[]; [k: string]: unknown }>(
    "/api/v1/bonds",
    { params },
  );
  return { bonds: data.bonds ?? [] };
}

/**
 * GET /api/v1/fx-pairs
 */
export async function fetchFX(
  base?: string,
  limit?: number,
): Promise<{ pairs: FXPair[] }> {
  const params: Record<string, string | number> = {};
  if (base) params["base"] = base;
  if (limit !== undefined) params["limit"] = limit;
  const { data } = await api.get<{
    usd_base?: RawFXItem[];
    crosses?: RawFXItem[];
    [k: string]: unknown;
  }>("/api/v1/fx-pairs", { params });
  return transformRawFXResponse(data);
}

/**
 * GET /api/v1/commodities
 */
export async function fetchCommodities(
  categories?: string,
): Promise<Record<string, Commodity[]>> {
  const params: Record<string, string> = {};
  if (categories) params["categories"] = categories;
  const { data } = await api.get<Record<string, unknown>>("/api/v1/commodities", {
    params,
  });
  return transformRawCommodities(data);
}

/**
 * GET /api/v1/macro
 */
export async function fetchMacro(
  countries?: string,
): Promise<{ indicators: MacroIndicator[] }> {
  const params: Record<string, string> = {};
  if (countries) params["countries"] = countries;
  const { data } = await api.get<{
    indicators: MacroIndicator[];
    [k: string]: unknown;
  }>("/api/v1/macro", { params });
  return { indicators: data.indicators ?? [] };
}

// ─── Cache ────────────────────────────────────────────────────────────────────

/**
 * POST /api/v1/refresh
 * Invalidates the server-side cache for the given section (or all sections
 * when omitted).
 */
export async function refreshCache(section?: string): Promise<RefreshResponse> {
  const params: Record<string, string> = {};
  if (section) params["section"] = section;
  const { data } = await api.post<RefreshResponse>("/api/v1/refresh", null, {
    params,
  });
  return data;
}

// ─── Exports ──────────────────────────────────────────────────────────────────

/**
 * POST /api/v1/export/excel
 * Returns a Blob that can be used to trigger a file download.
 */
export async function exportExcel(sheets: string[]): Promise<Blob> {
  const { data } = await api.post<Blob>(
    "/api/v1/export/excel",
    { sheets },
    { responseType: "blob" },
  );
  return data;
}

/**
 * POST /api/v1/export/pdf
 * Returns a Blob that can be used to trigger a file download.
 */
export async function exportPDF(): Promise<Blob> {
  const { data } = await api.post<Blob>("/api/v1/export/pdf", null, {
    responseType: "blob",
  });
  return data;
}

// ─── Document generation ──────────────────────────────────────────────────────

/**
 * POST /api/v1/generate/termsheet
 */
export async function generateTermsheet(params: ProductParams): Promise<Blob> {
  const { data } = await api.post<Blob>("/api/v1/generate/termsheet", params, {
    responseType: "blob",
  });
  return data;
}

/**
 * POST /api/v1/generate/scenariobook
 */
export async function generateScenarioBook(
  params: ScenarioBookParams,
): Promise<Blob> {
  const { data } = await api.post<Blob>("/api/v1/generate/scenariobook", params, {
    responseType: "blob",
  });
  return data;
}

/**
 * POST /api/v1/generate/risksummary
 */
export async function generateRiskSummary(
  products: ProductParams[],
): Promise<Blob> {
  const { data } = await api.post<Blob>("/api/v1/generate/risksummary", products, {
    responseType: "blob",
  });
  return data;
}
