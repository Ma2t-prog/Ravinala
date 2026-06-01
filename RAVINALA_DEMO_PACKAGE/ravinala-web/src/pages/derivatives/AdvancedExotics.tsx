import { useCallback, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "../../components/ui/Card";
import { useSnapshot } from "../../hooks/useMarketData";

// ─── Theme ───────────────────────────────────────────────────────────────────
const AMBER = "#F59E0B";
const BG = "#0A0E1A";
const ELEVATED = "#1A2332";
const TEXT = "#F1F5F9";
const MUTED = "#94A3B8";
const MONO = "JetBrains Mono, monospace";
const SANS = "Inter, system-ui, sans-serif";

// ─── Exotic types ────────────────────────────────────────────────────────────
type ExoticType =
  | "Barrier"
  | "Asian"
  | "Lookback"
  | "Digital"
  | "Rainbow"
  | "Cliquet";

interface ExoticDef {
  type: ExoticType;
  title: string;
  subtitle: string;
  description: string;
  formula: string;
  pricingNote: string;
  generatePayoff: (baseSpot: number) => { spot: number; payoff: number }[];
}

function makePayoff(
  fn: (s: number) => number,
  lo: number,
  hi: number,
): { spot: number; payoff: number }[] {
  const pts: { spot: number; payoff: number }[] = [];
  const step = (hi - lo) / 200;
  for (let s = lo; s <= hi; s += step) {
    pts.push({
      spot: Math.round(s * 10) / 10,
      payoff: Math.round(fn(s) * 100) / 100,
    });
  }
  return pts;
}

const EXOTICS: ExoticDef[] = [
  {
    type: "Barrier",
    title: "Barrier Options",
    subtitle: "Up-In / Down-Out / Up-Out / Down-In",
    description:
      "Barrier options are activated (knock-in) or extinguished (knock-out) when the underlying crosses a specified barrier level during the option's life. They are cheaper than vanilla options because the payoff is conditional on the path.",
    formula:
      "Down-Out Call: max(S-K, 0) if min(S_t) > B, else 0\nUp-In Put: max(K-S, 0) if max(S_t) > B, else 0",
    pricingNote:
      "Closed-form solutions exist (Merton 1973, Reiner & Rubinstein 1991). For discrete barriers, use continuity corrections or Monte Carlo simulation.",
    generatePayoff: (baseSpot: number) => {
      const K = baseSpot,
        B = baseSpot * 0.8;
      return makePayoff(
        (s) => {
          // Down-out call payoff (if never touched barrier)
          if (s <= B) return 0;
          return Math.max(s - K, 0);
        },
        baseSpot * 0.5,
        baseSpot * 1.5,
      );
    },
  },
  {
    type: "Asian",
    title: "Asian Options",
    subtitle: "Arithmetic / Geometric Average",
    description:
      "Asian options have payoffs that depend on the average price of the underlying over a specified period, rather than the spot at expiry. This averaging reduces volatility exposure and makes them cheaper than vanilla options.",
    formula:
      "Arithmetic Asian Call: max(A - K, 0) where A = (1/n) * sum(S_ti)\nGeometric Asian Call: max(G - K, 0) where G = (prod(S_ti))^(1/n)",
    pricingNote:
      "Geometric average has a closed-form solution (Kemna & Vorst 1990). Arithmetic average requires Monte Carlo or moment-matching approximations.",
    generatePayoff: (baseSpot: number) => {
      const K = baseSpot;
      return makePayoff(
        (s) => {
          // Approximate: average reduces extremes, payoff is dampened vs vanilla
          const avg = (s + baseSpot) / 2; // simplified: average between start and end
          return Math.max(avg - K, 0);
        },
        baseSpot * 0.5,
        baseSpot * 2,
      );
    },
  },
  {
    type: "Lookback",
    title: "Lookback Options",
    subtitle: "Fixed / Floating Strike",
    description:
      'Lookback options allow the holder to "look back" over the life of the option and exercise at the most favorable price. Floating-strike lookbacks set the strike at the minimum (call) or maximum (put) observed price.',
    formula: "Floating Call: S_T - min(S_t)\nFixed Call: max(max(S_t) - K, 0)",
    pricingNote:
      "Closed-form solutions by Goldman, Sosin & Gatto (1979). The premium is significantly higher than vanilla due to the hindsight advantage.",
    generatePayoff: (baseSpot: number) => {
      const K = baseSpot;
      return makePayoff(
        (s) => {
          // Fixed lookback call: the max is at least the final price
          const estimatedMax = Math.max(s, K * 1.1); // approximate the running max
          return Math.max(estimatedMax - K, 0);
        },
        baseSpot * 0.5,
        baseSpot * 2,
      );
    },
  },
  {
    type: "Digital",
    title: "Digital / Binary Options",
    subtitle: "Cash-or-Nothing / Asset-or-Nothing",
    description:
      "Digital options pay a fixed amount (cash-or-nothing) or deliver the asset (asset-or-nothing) if the option expires in the money. The payoff is discontinuous, creating challenges in hedging near the strike.",
    formula:
      "Cash-or-Nothing Call: Q * 1{S > K}\nAsset-or-Nothing Call: S * 1{S > K}",
    pricingNote:
      "Price = Q * exp(-rT) * N(d2) for cash-or-nothing call. The discontinuous payoff means delta and gamma are theoretically infinite at the strike near expiry.",
    generatePayoff: (baseSpot: number) => {
      const K = baseSpot,
        Q = baseSpot * 0.1;
      return makePayoff(
        (s) => {
          return s > K ? Q : 0;
        },
        baseSpot * 0.5,
        baseSpot * 1.5,
      );
    },
  },
  {
    type: "Rainbow",
    title: "Rainbow Options",
    subtitle: "Best-of / Worst-of / Spread",
    description:
      "Rainbow options depend on two or more underlying assets. Common types include best-of (pays the maximum return), worst-of (pays the minimum return), and spread options (pays the difference between two assets).",
    formula:
      "Best-of Call: max(S1_T, S2_T) - K\nWorst-of Call: min(S1_T, S2_T) - K\nSpread: max(S1_T - S2_T - K, 0)",
    pricingNote:
      "Margrabe (1978) formula for spread options. Multi-asset requires bivariate normal integration or Monte Carlo. Correlation is the key driver.",
    generatePayoff: (baseSpot: number) => {
      const K = baseSpot;
      return makePayoff(
        (s) => {
          // Best-of-two payoff (assume second asset = 105% of base)
          const s2 = baseSpot * 1.05;
          return Math.max(Math.max(s, s2) - K, 0);
        },
        baseSpot * 0.5,
        baseSpot * 2,
      );
    },
  },
  {
    type: "Cliquet",
    title: "Cliquet / Ratchet Options",
    subtitle: "Periodic Resets with Floors and Caps",
    description:
      "Cliquet options (also called ratchet or reset options) provide a series of at-the-money forward-starting options. Each period, the return is floored (often at 0%) and capped, then summed. Popular in insurance-linked structured products.",
    formula:
      "Payoff = sum( min(cap, max(floor, R_i)) ) where R_i = S(t_i)/S(t_{i-1}) - 1",
    pricingNote:
      "No closed-form; requires Monte Carlo simulation. The forward volatility smile is critical. The cliquet is long forward-starting options and short volatility of volatility.",
    generatePayoff: (baseSpot: number) => {
      return makePayoff(
        (s) => {
          // Simplified cliquet: 4 periods, floor=0%, cap=5%, assume linear path
          const periods = 4;
          const cap = 0.05,
            floor = 0;
          const totalReturn = (s - baseSpot) / baseSpot;
          const perPeriod = totalReturn / periods;
          let sum = 0;
          for (let i = 0; i < periods; i++) {
            sum += Math.min(cap, Math.max(floor, perPeriod));
          }
          return sum * baseSpot; // notional = baseSpot
        },
        baseSpot * 0.5,
        baseSpot * 2,
      );
    },
  },
];

// ─── Styles ──────────────────────────────────────────────────────────────────
const BG2 = "#131823";
const BORDER = "rgba(51,65,85,0.35)";
const inputSt: React.CSSProperties = {
  background: "#1A2332",
  border: `1px solid ${BORDER}`,
  borderRadius: 6,
  padding: "6px 10px",
  color: TEXT,
  fontSize: 13,
  width: "100%",
  outline: "none",
  fontFamily: MONO,
};
const lblSt: React.CSSProperties = {
  color: MUTED,
  fontSize: 11,
  fontWeight: 600,
  textTransform: "uppercase" as const,
  letterSpacing: "0.05em",
  marginBottom: 4,
  display: "block",
};
const btnSt: React.CSSProperties = {
  background: "linear-gradient(135deg, #F59E0B, #D97706)",
  color: "#0A0E1A",
  border: "none",
  borderRadius: 6,
  padding: "8px 22px",
  fontWeight: 700,
  fontSize: 13,
  cursor: "pointer",
  fontFamily: MONO,
};

// ─── Math helpers ─────────────────────────────────────────────────────────────
function _erf2(x: number): number {
  const t = 1 / (1 + 0.3275911 * Math.abs(x));
  const poly =
    t *
    (0.254829592 +
      t *
        (-0.284496736 +
          t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))));
  const sign = x < 0 ? -1 : 1;
  return sign * (1 - poly * Math.exp(-x * x));
}
function ncdf(x: number): number {
  return 0.5 * (1 + _erf2(x / Math.sqrt(2)));
}
function _npdf(x: number): number {
  return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}
function bsmCall(
  S: number,
  K: number,
  T: number,
  r: number,
  sigma: number,
): number {
  if (T <= 0 || sigma <= 0) return Math.max(S - K, 0);
  const d1 =
    (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));
  const d2 = d1 - sigma * Math.sqrt(T);
  return S * ncdf(d1) - K * Math.exp(-r * T) * ncdf(d2);
}
function _bsmDelta(
  S: number,
  K: number,
  T: number,
  r: number,
  sigma: number,
): number {
  if (T <= 0 || sigma <= 0) return S > K ? 1 : 0;
  const d1 =
    (Math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));
  return ncdf(d1);
}

// ─── Cliquet Monte Carlo (client-side, 5000 paths) ────────────────────────────
type CliquetType = "European" | "Memory" | "Ratchet";

function priceCliquet(
  S0: number,
  sigma: number,
  r: number,
  T: number,
  nDates: number,
  floor: number,
  cap: number,
  participation: number,
  cliqType: CliquetType,
  paths = 5000,
): {
  price: number;
  std: number;
  expectedReturn: number;
  histogram: { ret: number }[];
} {
  const dt = T / nDates;
  const sqdt = Math.sqrt(dt);
  let totalPayoff = 0;
  let totalPayoffSq = 0;
  const rets: number[] = [];
  for (let p = 0; p < paths; p++) {
    let S = S0;
    let payoff = 0;
    let runningFloor = 0;
    for (let i = 0; i < nDates; i++) {
      const z = _normalZ();
      const Snew =
        S * Math.exp((r - 0.5 * sigma * sigma) * dt + sigma * sqdt * z);
      const periodRet = Snew / S - 1;
      const clampedRet =
        Math.min(cap, Math.max(floor, periodRet)) * participation;
      if (cliqType === "European") {
        payoff += clampedRet;
      } else if (cliqType === "Memory") {
        const net = clampedRet + runningFloor;
        payoff += Math.min(cap, Math.max(0, net)) * participation;
        runningFloor = Math.min(0, runningFloor + clampedRet);
      } else {
        // Ratchet
        payoff += Math.max(clampedRet, 0);
      }
      S = Snew;
    }
    totalPayoff += payoff;
    totalPayoffSq += payoff * payoff;
    rets.push(payoff);
  }
  const mean = totalPayoff / paths;
  const variance = totalPayoffSq / paths - mean * mean;
  const std = Math.sqrt(variance / paths) * S0;
  const buckets = 40;
  const minR = Math.min(...rets),
    maxR = Math.max(...rets);
  const step = (maxR - minR) / buckets || 0.001;
  const hist: Record<number, number> = {};
  for (const r2 of rets) {
    const b = Math.round((r2 - minR) / step);
    hist[b] = (hist[b] || 0) + 1;
  }
  const histogram = Object.entries(hist)
    .map(([k, v]) => ({ ret: minR + Number(k) * step, count: v }))
    .sort((a, b) => a.ret - b.ret);
  return {
    price: mean * S0,
    std,
    expectedReturn: mean * 100,
    histogram: histogram as any,
  };
}

let _seed = 12345;
function _normalZ(): number {
  _seed = (_seed * 1664525 + 1013904223) & 0x7fffffff;
  const u1 = _seed / 0x7fffffff;
  _seed = (_seed * 1664525 + 1013904223) & 0x7fffffff;
  const u2 = _seed / 0x7fffffff;
  return (
    Math.sqrt(-2 * Math.log(Math.max(u1, 1e-10))) * Math.cos(2 * Math.PI * u2)
  );
}

// ─── Variance Swap ────────────────────────────────────────────────────────────
function priceVarianceSwap(
  realizedVol: number,
  varStrike: number,
  notional: number,
): {
  varPayoff: number;
  volPayoff: number;
  realizedVar: number;
  strikeVar: number;
} {
  const realizedVar = realizedVol * realizedVol;
  const strikeVar = varStrike * varStrike;
  return {
    varPayoff: notional * (realizedVar - strikeVar),
    volPayoff: notional * 100 * (realizedVol - varStrike),
    realizedVar: realizedVar * 10000,
    strikeVar: strikeVar * 10000,
  };
}

// ─── Convertible Bond ─────────────────────────────────────────────────────────
function priceConvertibleBond(
  face: number,
  coupon: number,
  T: number,
  S: number,
  convRatio: number,
  spread: number,
  r: number,
): {
  bondValue: number;
  convValue: number;
  callValue: number;
  convertiblePrice: number;
} {
  const rate = r + spread;
  let bondValue = 0;
  for (let t = 1; t <= Math.round(T); t++) {
    bondValue += (coupon * face) / Math.pow(1 + rate, t);
  }
  bondValue += face / Math.pow(1 + rate, T);
  const convValue = S * convRatio;
  const callValue = bsmCall(S, face / convRatio, T, r, 0.3) * convRatio;
  const convertiblePrice = bondValue + callValue;
  return { bondValue, convValue, callValue, convertiblePrice };
}

// ─── CLN ──────────────────────────────────────────────────────────────────────
function priceCLN(
  notional: number,
  coupon: number,
  T: number,
  spread: number,
  recovery: number,
  defaultProb: number,
  r: number,
): { fairValue: number; recoveryValue: number; oasSpread: number } {
  const discount_rate = r + spread;
  const expected_coupon = coupon * (1 - defaultProb) * notional;
  const expected_principal =
    (1 - defaultProb) * notional + defaultProb * recovery * notional;
  let pvCoupons = 0;
  for (let t = 1; t <= Math.round(T); t++) {
    pvCoupons += expected_coupon / Math.pow(1 + discount_rate, t);
  }
  const pvPrincipal = expected_principal / Math.pow(1 + discount_rate, T);
  const fairValue = pvCoupons + pvPrincipal;
  return {
    fairValue,
    recoveryValue: recovery * notional,
    oasSpread: spread * 10000,
  };
}

// ─── Range Accrual ────────────────────────────────────────────────────────────
function priceRangeAccrual(
  spot: number,
  lowerPct: number,
  upperPct: number,
  dailyCouponBps: number,
  days: number,
): {
  daysInRange: number;
  totalCoupon: number;
  effectiveYield: number;
  pricePath: { day: number; price: number }[];
} {
  const lower = (spot * lowerPct) / 100;
  const upper = (spot * upperPct) / 100;
  const dc = dailyCouponBps / 10000;
  let s = spot;
  let inRange = 0;
  let accrued = 0;
  const pricePath: { day: number; price: number }[] = [{ day: 0, price: spot }];
  _seed = 42;
  for (let i = 1; i <= days; i++) {
    s = s + _normalZ();
    pricePath.push({ day: i, price: Math.max(1, s) });
    if (s >= lower && s <= upper) {
      inRange++;
      accrued += dc;
    }
  }
  return {
    daysInRange: inRange,
    totalCoupon: accrued,
    effectiveYield: (accrued * 365) / days,
    pricePath,
  };
}

// ─── Component ───────────────────────────────────────────────────────────────
export default function AdvancedExotics() {
  const [selected, setSelected] = useState<ExoticType>("Barrier");
  const { data: liveData } = useSnapshot("indices");

  // ── Interactive Pricer state ─────────────────────────────────────────────
  const [activePricer, setActivePricer] = useState<
    "Cliquet" | "VarianceSwap" | "ConvertibleBond" | "CLN" | "RangeAccrual"
  >("Cliquet");

  // Cliquet state
  const [cqType, setCqType] = useState<CliquetType>("European");
  const [cqSpot, setCqSpot] = useState(100);
  const [cqSigma, setCqSigma] = useState(0.2);
  const [cqNDates, setCqNDates] = useState(4);
  const [cqFloor, setCqFloor] = useState(0);
  const [cqCap, setCqCap] = useState(0.05);
  const [cqParticip, setCqParticip] = useState(1.0);
  const [cqResult, setCqResult] = useState<ReturnType<
    typeof priceCliquet
  > | null>(null);

  // Variance Swap state
  const [vsRealVol, setVsRealVol] = useState(0.22);
  const [vsStrike, setVsStrike] = useState(0.2);
  const [vsNotional, setVsNotional] = useState(100000);
  const [vsResult, setVsResult] = useState<ReturnType<
    typeof priceVarianceSwap
  > | null>(null);

  // Convertible Bond state
  const [cbFace, setCbFace] = useState(1000);
  const [cbCoupon, setCbCoupon] = useState(0.05);
  const [cbT, setCbT] = useState(5);
  const [cbS, setCbS] = useState(100);
  const [cbRatio, setCbRatio] = useState(10);
  const [cbSpread, setCbSpread] = useState(0.02);
  const [cbResult, setCbResult] = useState<ReturnType<
    typeof priceConvertibleBond
  > | null>(null);

  // CLN state
  const [clnNotional, setClnNotional] = useState(1000000);
  const [clnCoupon, setClnCoupon] = useState(0.05);
  const [clnT, setClnT] = useState(5);
  const [clnSpread, setClnSpread] = useState(0.02);
  const [clnRecovery, setClnRecovery] = useState(0.4);
  const [clnDefProb, setClnDefProb] = useState(0.02);
  const [clnResult, setClnResult] = useState<ReturnType<
    typeof priceCLN
  > | null>(null);

  // Range Accrual state
  const [raSpot, setRaSpot] = useState(100);
  const [raLower, setRaLower] = useState(90);
  const [raUpper, setRaUpper] = useState(110);
  const [raDailyCoupon, setRaDailyCoupon] = useState(10);
  const [raDays, setRaDays] = useState(90);
  const [raResult, setRaResult] = useState<ReturnType<
    typeof priceRangeAccrual
  > | null>(null);

  const runCliquet = useCallback(() => {
    _seed = 12345;
    setCqResult(
      priceCliquet(
        cqSpot,
        cqSigma,
        0.05,
        1,
        cqNDates,
        cqFloor,
        cqCap,
        cqParticip,
        cqType,
        5000,
      ),
    );
  }, [cqSpot, cqSigma, cqNDates, cqFloor, cqCap, cqParticip, cqType]);

  const runVS = useCallback(() => {
    setVsResult(priceVarianceSwap(vsRealVol, vsStrike, vsNotional));
  }, [vsRealVol, vsStrike, vsNotional]);

  const runCB = useCallback(() => {
    setCbResult(
      priceConvertibleBond(cbFace, cbCoupon, cbT, cbS, cbRatio, cbSpread, 0.05),
    );
  }, [cbFace, cbCoupon, cbT, cbS, cbRatio, cbSpread]);

  const runCLN = useCallback(() => {
    setClnResult(
      priceCLN(
        clnNotional,
        clnCoupon,
        clnT,
        clnSpread,
        clnRecovery,
        clnDefProb,
        0.05,
      ),
    );
  }, [clnNotional, clnCoupon, clnT, clnSpread, clnRecovery, clnDefProb]);

  const runRA = useCallback(() => {
    _seed = 42;
    setRaResult(
      priceRangeAccrual(raSpot, raLower, raUpper, raDailyCoupon, raDays),
    );
  }, [raSpot, raLower, raUpper, raDailyCoupon, raDays]);

  // Extract a live equity spot price from the snapshot, fallback to 100
  const liveSpot = useMemo(() => {
    if (!liveData?.indices) return 100;
    const allIndices = Object.values(liveData.indices).flat();
    const first = allIndices[0];
    return first?.price ?? 100;
  }, [liveData]);

  const exotic = useMemo(
    () => EXOTICS.find((e) => e.type === selected)!,
    [selected],
  );
  const payoff = useMemo(
    () => exotic.generatePayoff(liveSpot),
    [exotic, liveSpot],
  );

  return (
    <div
      style={{
        background: BG,
        minHeight: "100vh",
        padding: 24,
        fontFamily: SANS,
      }}
    >
      {!liveData && (
        <div
          style={{
            background: "rgba(245,158,11,0.15)",
            border: "1px solid rgba(245,158,11,0.3)",
            borderRadius: 8,
            padding: "8px 16px",
            marginBottom: 16,
            fontSize: 13,
            color: "#F59E0B",
            fontFamily: "Inter, sans-serif",
          }}
        >
          ⚠ Backend unreachable — displaying demo data
        </div>
      )}
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: MONO, fontSize: 26, color: TEXT, margin: 0 }}>
          <span style={{ color: AMBER }}>&#9670;</span> Advanced Exotics
        </h1>
        <p style={{ color: MUTED, fontSize: 14, marginTop: 4 }}>
          Explore exotic option types with payoff diagrams and pricing insights
        </p>
      </div>

      {/* Grid of exotic types */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(6, 1fr)",
          gap: 10,
          marginBottom: 24,
        }}
      >
        {EXOTICS.map((e) => (
          <button
            key={e.type}
            onClick={() => setSelected(e.type)}
            style={{
              padding: "14px 8px",
              borderRadius: 8,
              border:
                selected === e.type
                  ? `1px solid ${AMBER}`
                  : "1px solid rgba(51,65,85,0.4)",
              background:
                selected === e.type ? "rgba(245,158,11,0.12)" : ELEVATED,
              cursor: "pointer",
              transition: "all 0.15s",
              textAlign: "center",
            }}
          >
            <div
              style={{
                fontSize: 13,
                fontWeight: selected === e.type ? 700 : 500,
                color: selected === e.type ? AMBER : TEXT,
                fontFamily: SANS,
              }}
            >
              {e.type}
            </div>
            <div
              style={{
                fontSize: 10,
                color: MUTED,
                marginTop: 3,
                fontFamily: SANS,
              }}
            >
              {e.subtitle}
            </div>
          </button>
        ))}
      </div>

      {/* Selected exotic detail */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Left: Info */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card title={exotic.title} subtitle={exotic.subtitle}>
            <p
              style={{
                color: TEXT,
                fontSize: 13,
                lineHeight: 1.7,
                margin: 0,
                fontFamily: SANS,
              }}
            >
              {exotic.description}
            </p>
          </Card>

          <Card title="Payoff Formula">
            <pre
              style={{
                color: AMBER,
                fontFamily: MONO,
                fontSize: 12,
                lineHeight: 1.8,
                margin: 0,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {exotic.formula}
            </pre>
          </Card>

          <Card title="Pricing Methodology">
            <p
              style={{
                color: TEXT,
                fontSize: 13,
                lineHeight: 1.7,
                margin: 0,
                fontFamily: SANS,
              }}
            >
              {exotic.pricingNote}
            </p>
          </Card>
        </div>

        {/* Right: Chart */}
        <Card title="Payoff Diagram" subtitle={exotic.title}>
          <div style={{ height: 400 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={payoff}
                margin={{ top: 10, right: 20, bottom: 20, left: 20 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(51,65,85,0.3)"
                />
                <XAxis
                  dataKey="spot"
                  stroke={MUTED}
                  tick={{ fill: MUTED, fontSize: 11, fontFamily: MONO }}
                  label={{
                    value: "Spot at Expiry",
                    position: "insideBottom",
                    offset: -10,
                    fill: MUTED,
                    fontSize: 11,
                  }}
                />
                <YAxis
                  stroke={MUTED}
                  tick={{ fill: MUTED, fontSize: 11, fontFamily: MONO }}
                  label={{
                    value: "Payoff",
                    angle: -90,
                    position: "insideLeft",
                    fill: MUTED,
                    fontSize: 11,
                  }}
                />
                <Tooltip
                  contentStyle={{
                    background: ELEVATED,
                    border: `1px solid ${AMBER}`,
                    borderRadius: 6,
                    fontFamily: MONO,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: MUTED }}
                  itemStyle={{ color: AMBER }}
                  formatter={(v: any) => [Number(v).toFixed(2), "Payoff"]}
                  labelFormatter={(v: any) => `Spot: ${v}`}
                />
                <Line
                  type="monotone"
                  dataKey="payoff"
                  stroke={AMBER}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Quick example pricing */}
          <div
            style={{
              marginTop: 16,
              padding: 12,
              background: "rgba(245,158,11,0.06)",
              borderRadius: 6,
              border: "1px solid rgba(245,158,11,0.15)",
            }}
          >
            <div
              style={{
                color: AMBER,
                fontSize: 12,
                fontWeight: 600,
                marginBottom: 6,
              }}
            >
              Example Parameters
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: 8,
              }}
            >
              {[
                { label: "Spot", value: liveSpot.toFixed(2) },
                { label: "Strike", value: liveSpot.toFixed(2) },
                { label: "Volatility", value: "20%" },
                { label: "Rate", value: "5%" },
                { label: "Maturity", value: "1Y" },
                { label: "Type", value: exotic.type },
              ].map((item) => (
                <div
                  key={item.label}
                  style={{ display: "flex", justifyContent: "space-between" }}
                >
                  <span style={{ color: MUTED, fontSize: 11 }}>
                    {item.label}
                  </span>
                  <span style={{ color: TEXT, fontFamily: MONO, fontSize: 12 }}>
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* ─────────────── Interactive Pricers ──────────────────────────────── */}
      <div style={{ marginTop: 32 }}>
        <div style={{ marginBottom: 16 }}>
          <h2
            style={{ fontFamily: MONO, fontSize: 18, color: TEXT, margin: 0 }}
          >
            <span style={{ color: AMBER }}>&#9632;</span> Interactive Pricers
          </h2>
          <p style={{ color: MUTED, fontSize: 13, marginTop: 4 }}>
            Monte Carlo &amp; analytic engines — Cliquet · Variance Swap ·
            Convertible Bond · CLN · Range Accrual
          </p>
        </div>

        {/* Pricer selector */}
        <div
          style={{
            display: "flex",
            gap: 8,
            marginBottom: 20,
            flexWrap: "wrap",
          }}
        >
          {(
            [
              "Cliquet",
              "VarianceSwap",
              "ConvertibleBond",
              "CLN",
              "RangeAccrual",
            ] as const
          ).map((p) => (
            <button
              key={p}
              onClick={() => setActivePricer(p)}
              style={{
                padding: "8px 18px",
                borderRadius: 6,
                border:
                  activePricer === p
                    ? `1px solid ${AMBER}`
                    : "1px solid rgba(51,65,85,0.4)",
                background:
                  activePricer === p ? "rgba(245,158,11,0.14)" : "#1A2332",
                color: activePricer === p ? AMBER : TEXT,
                fontWeight: activePricer === p ? 700 : 500,
                fontFamily: MONO,
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              {p === "VarianceSwap"
                ? "Variance Swap"
                : p === "ConvertibleBond"
                  ? "Convertible Bond"
                  : p === "RangeAccrual"
                    ? "Range Accrual"
                    : p}
            </button>
          ))}
        </div>

        {/* ── Cliquet Pricer ─────────────────────────────────────────────── */}
        {activePricer === "Cliquet" && (
          <Card
            title="Cliquet Options — Monte Carlo (5,000 paths)"
            subtitle="Periodic resets with floor and cap"
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                gap: 14,
                marginBottom: 16,
              }}
            >
              <div>
                <label style={lblSt}>Type</label>
                <select
                  value={cqType}
                  onChange={(e) => setCqType(e.target.value as CliquetType)}
                  style={{ ...inputSt, appearance: "none" as const }}
                >
                  <option>European</option>
                  <option>Memory</option>
                  <option>Ratchet</option>
                </select>
              </div>
              <div>
                <label style={lblSt}>Spot (S₀)</label>
                <input
                  type="number"
                  value={cqSpot}
                  onChange={(e) => setCqSpot(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>Volatility</label>
                <input
                  type="number"
                  step={0.01}
                  value={cqSigma}
                  onChange={(e) => setCqSigma(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>N Dates</label>
                <input
                  type="number"
                  min={1}
                  max={24}
                  value={cqNDates}
                  onChange={(e) => setCqNDates(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>Floor</label>
                <input
                  type="number"
                  step={0.01}
                  value={cqFloor}
                  onChange={(e) => setCqFloor(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>Cap</label>
                <input
                  type="number"
                  step={0.01}
                  value={cqCap}
                  onChange={(e) => setCqCap(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>Participation</label>
                <input
                  type="number"
                  step={0.05}
                  value={cqParticip}
                  onChange={(e) => setCqParticip(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <button onClick={runCliquet} style={btnSt}>
                  Price Cliquet
                </button>
              </div>
            </div>
            {cqResult && (
              <div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: 12,
                    marginBottom: 16,
                  }}
                >
                  {[
                    {
                      label: "MC Price",
                      value: `${cqResult.price.toFixed(4)}`,
                      color: AMBER,
                    },
                    {
                      label: "±1σ (stderr)",
                      value: `±${cqResult.std.toFixed(4)}`,
                      color: MUTED,
                    },
                    {
                      label: "Exp. Return",
                      value: `${cqResult.expectedReturn.toFixed(2)}%`,
                      color: "#10B981",
                    },
                  ].map((m) => (
                    <div
                      key={m.label}
                      style={{
                        background: BG2,
                        borderRadius: 6,
                        padding: "10px 14px",
                        border: `1px solid ${BORDER}`,
                      }}
                    >
                      <div
                        style={{
                          color: MUTED,
                          fontSize: 10,
                          fontWeight: 600,
                          textTransform: "uppercase" as const,
                        }}
                      >
                        {m.label}
                      </div>
                      <div
                        style={{
                          color: m.color,
                          fontFamily: MONO,
                          fontSize: 18,
                          fontWeight: 700,
                        }}
                      >
                        {m.value}
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={cqResult.histogram}
                      margin={{ top: 4, right: 16, bottom: 4, left: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke={BORDER} />
                      <XAxis
                        dataKey="ret"
                        stroke={MUTED}
                        tick={{ fill: MUTED, fontSize: 10, fontFamily: MONO }}
                        tickFormatter={(v: any) => `${(v * 100).toFixed(1)}%`}
                      />
                      <YAxis
                        stroke={MUTED}
                        tick={{ fill: MUTED, fontSize: 10, fontFamily: MONO }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#1A2332",
                          border: `1px solid ${AMBER}`,
                          borderRadius: 6,
                          fontFamily: MONO,
                          fontSize: 12,
                        }}
                        labelFormatter={(v: any) =>
                          `Return: ${(+v * 100).toFixed(2)}%`
                        }
                        formatter={(v: any) => [v, "Paths"]}
                      />
                      <Bar dataKey="count" fill={AMBER} radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </Card>
        )}

        {/* ── Variance Swap ─────────────────────────────────────────────── */}
        {activePricer === "VarianceSwap" && (
          <Card
            title="Variance Swap"
            subtitle="Realized variance vs strike — payoff metrics"
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                gap: 14,
                marginBottom: 16,
              }}
            >
              <div>
                <label style={lblSt}>Realized Vol</label>
                <input
                  type="number"
                  step={0.01}
                  value={vsRealVol}
                  onChange={(e) => setVsRealVol(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>Variance Strike (σ_K)</label>
                <input
                  type="number"
                  step={0.01}
                  value={vsStrike}
                  onChange={(e) => setVsStrike(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>Vega Notional (€)</label>
                <input
                  type="number"
                  value={vsNotional}
                  onChange={(e) => setVsNotional(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <button onClick={runVS} style={btnSt}>
                  Calculate
                </button>
              </div>
            </div>
            {vsResult && (
              <div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, 1fr)",
                    gap: 12,
                    marginBottom: 16,
                  }}
                >
                  {[
                    {
                      label: "Var Payoff (€)",
                      value: vsResult.varPayoff.toLocaleString("en", {
                        maximumFractionDigits: 0,
                      }),
                      color: vsResult.varPayoff >= 0 ? "#10B981" : "#EF4444",
                    },
                    {
                      label: "Vol Swap Payoff",
                      value: `€${vsResult.volPayoff.toLocaleString("en", { maximumFractionDigits: 0 })}`,
                      color: vsResult.volPayoff >= 0 ? "#10B981" : "#EF4444",
                    },
                    {
                      label: "Realized Var (vpts)",
                      value: vsResult.realizedVar.toFixed(2),
                      color: "#00D9FF",
                    },
                    {
                      label: "Strike Var (vpts)",
                      value: vsResult.strikeVar.toFixed(2),
                      color: MUTED,
                    },
                  ].map((m) => (
                    <div
                      key={m.label}
                      style={{
                        background: BG2,
                        borderRadius: 6,
                        padding: "10px 14px",
                        border: `1px solid ${BORDER}`,
                      }}
                    >
                      <div
                        style={{
                          color: MUTED,
                          fontSize: 10,
                          fontWeight: 600,
                          textTransform: "uppercase" as const,
                        }}
                      >
                        {m.label}
                      </div>
                      <div
                        style={{
                          color: m.color,
                          fontFamily: MONO,
                          fontSize: 18,
                          fontWeight: 700,
                        }}
                      >
                        {m.value}
                      </div>
                    </div>
                  ))}
                </div>
                <div
                  style={{
                    background: "rgba(245,158,11,0.06)",
                    borderRadius: 6,
                    padding: "10px 14px",
                    border: `1px solid rgba(245,158,11,0.15)`,
                    fontSize: 12,
                    color: TEXT,
                    fontFamily: MONO,
                  }}
                >
                  Payoff = N × (σ²_realized − σ²_strike) ={" "}
                  {vsNotional.toLocaleString()} × ({vsRealVol.toFixed(3)}² −{" "}
                  {vsStrike.toFixed(3)}²) = €
                  {vsResult.varPayoff.toLocaleString("en", {
                    maximumFractionDigits: 0,
                  })}
                </div>
              </div>
            )}
          </Card>
        )}

        {/* ── Convertible Bond ─────────────────────────────────────────── */}
        {activePricer === "ConvertibleBond" && (
          <Card
            title="Convertible Bond Pricing"
            subtitle="Bond floor + embedded call option on equity"
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                gap: 14,
                marginBottom: 16,
              }}
            >
              {[
                { label: "Face (€)", val: cbFace, set: setCbFace, step: 100 },
                {
                  label: "Coupon",
                  val: cbCoupon,
                  set: setCbCoupon,
                  step: 0.01,
                },
                { label: "Maturity (yr)", val: cbT, set: setCbT, step: 1 },
                { label: "Stock Price", val: cbS, set: setCbS, step: 1 },
                {
                  label: "Conv. Ratio",
                  val: cbRatio,
                  set: setCbRatio,
                  step: 1,
                },
                {
                  label: "Credit Spread",
                  val: cbSpread,
                  set: setCbSpread,
                  step: 0.005,
                },
              ].map((f) => (
                <div key={f.label}>
                  <label style={lblSt}>{f.label}</label>
                  <input
                    type="number"
                    step={f.step}
                    value={f.val}
                    onChange={(e) => f.set(+e.target.value)}
                    style={inputSt}
                  />
                </div>
              ))}
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <button onClick={runCB} style={btnSt}>
                  Price CB
                </button>
              </div>
            </div>
            {cbResult && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(4, 1fr)",
                  gap: 12,
                }}
              >
                {[
                  {
                    label: "Bond Value",
                    value: `€${cbResult.bondValue.toFixed(2)}`,
                    color: "#00D9FF",
                  },
                  {
                    label: "Conv. Value",
                    value: `€${cbResult.convValue.toFixed(2)}`,
                    color: "#10B981",
                  },
                  {
                    label: "Call Option",
                    value: `€${cbResult.callValue.toFixed(2)}`,
                    color: "#A855F7",
                  },
                  {
                    label: "Convertible Price",
                    value: `€${cbResult.convertiblePrice.toFixed(2)}`,
                    color: AMBER,
                  },
                ].map((m) => (
                  <div
                    key={m.label}
                    style={{
                      background: BG2,
                      borderRadius: 6,
                      padding: "10px 14px",
                      border: `1px solid ${BORDER}`,
                    }}
                  >
                    <div
                      style={{
                        color: MUTED,
                        fontSize: 10,
                        fontWeight: 600,
                        textTransform: "uppercase" as const,
                      }}
                    >
                      {m.label}
                    </div>
                    <div
                      style={{
                        color: m.color,
                        fontFamily: MONO,
                        fontSize: 16,
                        fontWeight: 700,
                      }}
                    >
                      {m.value}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* ── Credit-Linked Note ───────────────────────────────────────── */}
        {activePricer === "CLN" && (
          <Card
            title="Credit-Linked Note"
            subtitle="Fair value with default risk and recovery"
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
                gap: 14,
                marginBottom: 16,
              }}
            >
              {[
                {
                  label: "Notional (€)",
                  val: clnNotional,
                  set: setClnNotional,
                  step: 100000,
                },
                {
                  label: "Coupon",
                  val: clnCoupon,
                  set: setClnCoupon,
                  step: 0.005,
                },
                { label: "Maturity (yr)", val: clnT, set: setClnT, step: 1 },
                {
                  label: "Credit Spread",
                  val: clnSpread,
                  set: setClnSpread,
                  step: 0.005,
                },
                {
                  label: "Recovery Rate",
                  val: clnRecovery,
                  set: setClnRecovery,
                  step: 0.05,
                },
                {
                  label: "Default Prob",
                  val: clnDefProb,
                  set: setClnDefProb,
                  step: 0.005,
                },
              ].map((f) => (
                <div key={f.label}>
                  <label style={lblSt}>{f.label}</label>
                  <input
                    type="number"
                    step={f.step}
                    value={f.val}
                    onChange={(e) => f.set(+e.target.value)}
                    style={inputSt}
                  />
                </div>
              ))}
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <button onClick={runCLN} style={btnSt}>
                  Price CLN
                </button>
              </div>
            </div>
            {clnResult && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: 12,
                }}
              >
                {[
                  {
                    label: "CLN Par Value",
                    value: `€${clnNotional.toLocaleString()}`,
                    color: MUTED,
                  },
                  {
                    label: "Fair Value",
                    value: `€${clnResult.fairValue.toFixed(0)}`,
                    color: AMBER,
                  },
                  {
                    label: "Recovery (if default)",
                    value: `€${clnResult.recoveryValue.toLocaleString()}`,
                    color: "#10B981",
                  },
                  {
                    label: "OAS Spread",
                    value: `${clnResult.oasSpread.toFixed(0)} bps`,
                    color: "#00D9FF",
                  },
                  {
                    label: "Coupon PA",
                    value: `${(clnCoupon * 100).toFixed(1)}%`,
                    color: TEXT,
                  },
                  {
                    label: "Default Prob",
                    value: `${(clnDefProb * 100).toFixed(1)}%`,
                    color: "#EF4444",
                  },
                ].map((m) => (
                  <div
                    key={m.label}
                    style={{
                      background: BG2,
                      borderRadius: 6,
                      padding: "10px 14px",
                      border: `1px solid ${BORDER}`,
                    }}
                  >
                    <div
                      style={{
                        color: MUTED,
                        fontSize: 10,
                        fontWeight: 600,
                        textTransform: "uppercase" as const,
                      }}
                    >
                      {m.label}
                    </div>
                    <div
                      style={{
                        color: m.color,
                        fontFamily: MONO,
                        fontSize: 16,
                        fontWeight: 700,
                      }}
                    >
                      {m.value}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* ── Range Accrual ─────────────────────────────────────────────── */}
        {activePricer === "RangeAccrual" && (
          <Card
            title="Range Accrual"
            subtitle="Corridor coupon — days in range × daily coupon"
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
                gap: 14,
                marginBottom: 16,
              }}
            >
              <div>
                <label style={lblSt}>Spot Price</label>
                <input
                  type="number"
                  value={raSpot}
                  onChange={(e) => setRaSpot(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>Lower Barrier (%)</label>
                <input
                  type="number"
                  value={raLower}
                  onChange={(e) => setRaLower(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>Upper Barrier (%)</label>
                <input
                  type="number"
                  value={raUpper}
                  onChange={(e) => setRaUpper(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>Daily Coupon (bps)</label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={raDailyCoupon}
                  onChange={(e) => setRaDailyCoupon(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div>
                <label style={lblSt}>Period (days)</label>
                <input
                  type="number"
                  min={30}
                  max={252}
                  value={raDays}
                  onChange={(e) => setRaDays(+e.target.value)}
                  style={inputSt}
                />
              </div>
              <div style={{ display: "flex", alignItems: "flex-end" }}>
                <button onClick={runRA} style={btnSt}>
                  Simulate
                </button>
              </div>
            </div>
            {raResult && (
              <div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: 12,
                    marginBottom: 16,
                  }}
                >
                  {[
                    {
                      label: `Days in Range / ${raDays}`,
                      value: String(raResult.daysInRange),
                      color: "#10B981",
                    },
                    {
                      label: "Total Coupon Accrued",
                      value: `${(raResult.totalCoupon * 100).toFixed(2)}%`,
                      color: AMBER,
                    },
                    {
                      label: "Effective Annual Yield",
                      value: `${(raResult.effectiveYield * 100).toFixed(2)}%`,
                      color: "#00D9FF",
                    },
                  ].map((m) => (
                    <div
                      key={m.label}
                      style={{
                        background: BG2,
                        borderRadius: 6,
                        padding: "10px 14px",
                        border: `1px solid ${BORDER}`,
                      }}
                    >
                      <div
                        style={{
                          color: MUTED,
                          fontSize: 10,
                          fontWeight: 600,
                          textTransform: "uppercase" as const,
                        }}
                      >
                        {m.label}
                      </div>
                      <div
                        style={{
                          color: m.color,
                          fontFamily: MONO,
                          fontSize: 18,
                          fontWeight: 700,
                        }}
                      >
                        {m.value}
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{ height: 240 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={raResult.pricePath}
                      margin={{ top: 4, right: 16, bottom: 4, left: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke={BORDER} />
                      <XAxis
                        dataKey="day"
                        stroke={MUTED}
                        tick={{ fill: MUTED, fontSize: 10, fontFamily: MONO }}
                        label={{
                          value: "Day",
                          position: "insideBottom",
                          offset: -2,
                          fill: MUTED,
                          fontSize: 11,
                        }}
                      />
                      <YAxis
                        stroke={MUTED}
                        tick={{ fill: MUTED, fontSize: 10, fontFamily: MONO }}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#1A2332",
                          border: `1px solid ${AMBER}`,
                          borderRadius: 6,
                          fontFamily: MONO,
                          fontSize: 12,
                        }}
                      />
                      <ReferenceLine
                        y={(raSpot * raLower) / 100}
                        stroke="#EF4444"
                        strokeDasharray="4 3"
                        label={{
                          value: "Lower",
                          fill: "#EF4444",
                          fontSize: 10,
                        }}
                      />
                      <ReferenceLine
                        y={(raSpot * raUpper) / 100}
                        stroke="#EF4444"
                        strokeDasharray="4 3"
                        label={{
                          value: "Upper",
                          fill: "#EF4444",
                          fontSize: 10,
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="price"
                        stroke="#00D9FF"
                        strokeWidth={1.5}
                        dot={false}
                        name="Spot"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
