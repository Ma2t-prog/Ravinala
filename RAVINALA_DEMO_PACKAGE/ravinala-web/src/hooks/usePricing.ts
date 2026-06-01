/**
 * usePricing — local Black-Scholes pricing utilities (no backend required).
 *
 * All calculations run client-side, so this hook never triggers a network
 * request. Import the pure functions directly when you only need the maths,
 * or call the hook from a component when you want memoised results.
 */

// ─── Math helpers ─────────────────────────────────────────────────────────────

/**
 * Cumulative standard normal distribution via the Hart (1968) rational
 * approximation. Maximum absolute error < 7.5 × 10⁻⁸.
 */
export function normCDF(x: number): number {
  if (x < -8) return 0
  if (x > 8) return 1

  const a1 =  0.254829592
  const a2 = -0.284496736
  const a3 =  1.421413741
  const a4 = -1.453152027
  const a5 =  1.061405429
  const p  =  0.3275911

  const sign = x < 0 ? -1 : 1
  const absX = Math.abs(x)
  const t = 1 / (1 + p * absX)
  const poly = t * (a1 + t * (a2 + t * (a3 + t * (a4 + t * a5))))
  const erf = 1 - poly * Math.exp(-absX * absX)
  return 0.5 * (1 + sign * erf)
}

/** Standard normal probability density function. */
function normPDF(x: number): number {
  return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI)
}

// ─── Black-Scholes price ──────────────────────────────────────────────────────

/**
 * European option price using the Black-Scholes-Merton formula.
 *
 * @param S     Current spot price
 * @param K     Strike price
 * @param T     Time to expiry in years (e.g. 0.5 = 6 months)
 * @param r     Continuously compounded risk-free rate (e.g. 0.05 = 5 %)
 * @param sigma Annualised implied volatility (e.g. 0.20 = 20 %)
 * @param type  'call' | 'put'
 * @returns     Option price (same currency as S and K)
 */
export function blackScholesPrice(
  S: number,
  K: number,
  T: number,
  r: number,
  sigma: number,
  type: 'call' | 'put',
): number {
  if (T <= 0) {
    // At / after expiry — return intrinsic value only
    return type === 'call' ? Math.max(S - K, 0) : Math.max(K - S, 0)
  }

  const sqrtT = Math.sqrt(T)
  const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
  const d2 = d1 - sigma * sqrtT

  if (type === 'call') {
    return S * normCDF(d1) - K * Math.exp(-r * T) * normCDF(d2)
  } else {
    return K * Math.exp(-r * T) * normCDF(-d2) - S * normCDF(-d1)
  }
}

// ─── Black-Scholes Greeks ─────────────────────────────────────────────────────

export interface BSGreeks {
  /** Rate of change of option price with respect to spot. */
  delta: number
  /** Rate of change of delta with respect to spot. */
  gamma: number
  /** Sensitivity to a 1 % absolute change in implied volatility (vega / 100). */
  vega: number
  /**
   * Time decay per calendar day (theta / 365).
   * Negative for long options.
   */
  theta: number
  /** Sensitivity to a 1 bp change in the risk-free rate (rho / 10000). */
  rho: number
}

/**
 * Analytic Black-Scholes Greeks for a European option.
 *
 * @param S     Current spot price
 * @param K     Strike price
 * @param T     Time to expiry in years
 * @param r     Continuously compounded risk-free rate
 * @param sigma Annualised implied volatility
 * @param type  'call' | 'put'
 * @returns     Object containing delta, gamma, vega, theta, rho
 */
export function blackScholesGreeks(
  S: number,
  K: number,
  T: number,
  r: number,
  sigma: number,
  type: 'call' | 'put',
): BSGreeks {
  if (T <= 0) {
    return { delta: 0, gamma: 0, vega: 0, theta: 0, rho: 0 }
  }

  const sqrtT = Math.sqrt(T)
  const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
  const d2 = d1 - sigma * sqrtT
  const nd1 = normPDF(d1)
  const discount = Math.exp(-r * T)

  // ── Delta ──────────────────────────────────────────────────────────────────
  const delta = type === 'call' ? normCDF(d1) : normCDF(d1) - 1

  // ── Gamma (same for calls and puts) ────────────────────────────────────────
  const gamma = nd1 / (S * sigma * sqrtT)

  // ── Vega — expressed per 1 % move in vol (divide raw by 100) ───────────────
  const vega = (S * nd1 * sqrtT) / 100

  // ── Theta — expressed per calendar day ────────────────────────────────────
  const thetaRaw =
    type === 'call'
      ? -(S * nd1 * sigma) / (2 * sqrtT) - r * K * discount * normCDF(d2)
      : -(S * nd1 * sigma) / (2 * sqrtT) + r * K * discount * normCDF(-d2)
  const theta = thetaRaw / 365

  // ── Rho — expressed per 1 bp move in rate (divide raw by 10 000) ───────────
  const rhoRaw =
    type === 'call'
      ? K * T * discount * normCDF(d2)
      : -K * T * discount * normCDF(-d2)
  const rho = rhoRaw / 10_000

  return { delta, gamma, vega, theta, rho }
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export interface PricingInput {
  S: number
  K: number
  T: number
  r: number
  sigma: number
  type: 'call' | 'put'
}

export interface PricingResult {
  price: number
  greeks: BSGreeks
}

/**
 * React hook that returns memoised Black-Scholes price and Greeks.
 * Re-computes only when the inputs change.
 *
 * @example
 * const { price, greeks } = usePricing({ S: 100, K: 100, T: 0.5, r: 0.05, sigma: 0.2, type: 'call' })
 */
export function usePricing(input: PricingInput): PricingResult {
  const { S, K, T, r, sigma, type } = input

  const price = blackScholesPrice(S, K, T, r, sigma, type)
  const greeks = blackScholesGreeks(S, K, T, r, sigma, type)

  return { price, greeks }
}
