import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge, Card } from "../../components/ui";
import { useSnapshot } from "../../hooks/useMarketData";

// Seeded pseudo-random for deterministic paths
function seededRandom(seed: number) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return s / 2147483647;
  };
}

const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
};

const PATH_COLORS = [
  "#00D9FF",
  "#D4AF37",
  "#10B981",
  "#EF4444",
  "#A855F7",
  "#F59E0B",
  "#EC4899",
  "#06B6D4",
  "#84CC16",
  "#F97316",
  "rgba(0,217,255,0.5)",
  "rgba(212,175,55,0.5)",
  "rgba(16,185,129,0.5)",
  "rgba(239,68,68,0.5)",
  "rgba(168,85,247,0.5)",
  "rgba(245,158,11,0.5)",
  "rgba(236,72,153,0.5)",
  "rgba(6,182,212,0.5)",
  "rgba(132,204,22,0.5)",
  "rgba(249,115,22,0.5)",
];

const TABS = [
  "Simulation",
  "Seismology",
  "LPPL Bubbles",
  "Criticality",
  "Percolation",
  "Scaling",
] as const;

// Helper: error function approximation
function erf(x: number): number {
  const a1 = 0.254829592,
    a2 = -0.284496736,
    a3 = 1.421413741,
    a4 = -1.453152027,
    a5 = 1.061405429;
  const p = 0.3275911;
  const t = 1 / (1 + p * Math.abs(x));
  const y =
    1 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
  return x >= 0 ? y : -y;
}

// ── Seismology demo data ──
const SEISMO_METRICS = [
  {
    label: "Tail Exponent (α)",
    value: "3.12",
    color: "#D4AF37",
    sub: "Power-law tail",
  },
  {
    label: "X_min Threshold",
    value: "0.0215",
    color: "#94A3B8",
    sub: "Min tail observation",
  },
  {
    label: "Tail Size",
    value: "126 samples",
    color: "#00D9FF",
    sub: "of 504 returns",
  },
  { label: "KS p-value", value: "0.72", color: "#10B981", sub: "Good fit" },
  {
    label: "Seismic Risk Score",
    value: "34/100",
    color: "#F59E0B",
    sub: "Moderate",
  },
  {
    label: "Current Phase",
    value: "LIQUID",
    color: "#10B981",
    sub: "Normal regime",
  },
];

// ── LPPL demo data ──
const LPPL_PARAMS = [
  { label: "tc (critical time)", value: "~87 days", color: "#EF4444" },
  { label: "m (exponent)", value: "0.42", color: "#D4AF37" },
  { label: "ω (log-frequency)", value: "8.3", color: "#00D9FF" },
  { label: "R²", value: "0.89", color: "#10B981" },
  { label: "Confidence", value: "62%", color: "#F59E0B" },
  { label: "Risk Level", value: "MODERATE", color: "#F59E0B" },
];

// ── Criticality demo data ──
const PHASES = [
  {
    phase: "LIQUID",
    temp: 0.72,
    suscept: 0.35,
    vol: "14.2%",
    color: "#10B981",
    description: "Normal market — moderate vol, price discovery works",
  },
  {
    phase: "GAS",
    temp: 1.45,
    suscept: 0.78,
    vol: "28.5%",
    color: "#EF4444",
    description: "Euphoria — high vol, herding, momentum dominates",
  },
  {
    phase: "SOLID",
    temp: 0.18,
    suscept: 0.12,
    vol: "8.1%",
    color: "#3B82F6",
    description: "Frozen — no liquidity, everyone wants to sell",
  },
  {
    phase: "CRITICAL",
    temp: 1.0,
    suscept: 1.0,
    vol: "22.0%",
    color: "#D4AF37",
    description: "Phase boundary — maximum susceptibility to shocks",
  },
];

// ── Percolation demo data ──
const PERCOLATION = {
  R0: 1.42,
  R0_eff: 1.15,
  isSuperCritical: true,
  infectionRate: 0.18,
  threshold: 0.38,
  avgCorr: 0.52,
  giantComponent: 0.68,
  status: "HIGH — cascades can self-sustain.",
  assets: [
    { name: "SPY", state: "Infected", vol_ratio: 2.8, color: "#EF4444" },
    { name: "QQQ", state: "Infected", vol_ratio: 2.3, color: "#EF4444" },
    { name: "IWM", state: "Susceptible", vol_ratio: 1.1, color: "#10B981" },
    { name: "TLT", state: "Recovered", vol_ratio: 0.7, color: "#3B82F6" },
    { name: "GLD", state: "Susceptible", vol_ratio: 0.9, color: "#10B981" },
    { name: "USO", state: "Recovered", vol_ratio: 0.5, color: "#3B82F6" },
    { name: "FXI", state: "Susceptible", vol_ratio: 1.4, color: "#10B981" },
    { name: "EWJ", state: "Susceptible", vol_ratio: 1.0, color: "#10B981" },
  ],
};

// ── Scaling demo data ──
const SCALING = {
  hurst: 0.58,
  stableAlpha: 1.72,
  stableBeta: -0.12,
  volScaling: [
    { interval: "1D", realized: 1.0, sqrtT: 1.0 },
    { interval: "5D", realized: 2.45, sqrtT: 2.24 },
    { interval: "10D", realized: 3.68, sqrtT: 3.16 },
    { interval: "21D", realized: 5.91, sqrtT: 4.58 },
    { interval: "63D", realized: 11.2, sqrtT: 7.94 },
    { interval: "126D", realized: 17.8, sqrtT: 11.22 },
    { interval: "252D", realized: 28.3, sqrtT: 15.87 },
  ],
  universality: [
    { asset: "SPY", tailAlpha: 3.12, hurst: 0.58, stableAlpha: 1.72 },
    { asset: "AAPL", tailAlpha: 2.88, hurst: 0.61, stableAlpha: 1.65 },
    { asset: "EURUSD", tailAlpha: 3.41, hurst: 0.49, stableAlpha: 1.89 },
    { asset: "GLD", tailAlpha: 3.05, hurst: 0.52, stableAlpha: 1.78 },
    { asset: "BTC", tailAlpha: 2.15, hurst: 0.64, stableAlpha: 1.38 },
  ],
};

export default function PhysicsLab() {
  const [tab, setTab] = useState<(typeof TABS)[number]>(TABS[0]);
  const { data: snapshotData } = useSnapshot();
  const liveData = snapshotData ?? null;

  // Use live spot price as default GBM starting price when available
  const liveSpotPrice = useMemo(() => {
    if (!snapshotData?.indices) return null;
    const allIndices = Object.values(snapshotData.indices).flat();
    return allIndices[0]?.price ?? null;
  }, [snapshotData]);

  const gbmData = useMemo(() => {
    const S0 = liveSpotPrice ?? 100;
    const mu = 0.08;
    const sigma = 0.25;
    const T = 1;
    const steps = 100;
    const dt = T / steps;
    const nPaths = 20;

    const paths: Record<string, number>[][] = Array.from(
      { length: steps + 1 },
      (_, i) => {
        const point: Record<string, number> = { t: +(i * dt).toFixed(3) };
        return [point] as any;
      },
    );

    for (let p = 0; p < nPaths; p++) {
      const rand = seededRandom(42 + p * 7);
      let S = S0;
      (paths[0][0] as any)[`p${p}`] = S;
      for (let i = 1; i <= steps; i++) {
        const u1 = rand();
        const u2 = rand();
        const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
        S =
          S *
          Math.exp((mu - 0.5 * sigma * sigma) * dt + sigma * Math.sqrt(dt) * z);
        (paths[i][0] as any)[`p${p}`] = +S.toFixed(2);
      }
    }

    return paths.map((p) => p[0]);
  }, [liveSpotPrice]);

  // Black-Scholes surface data
  const bsData = useMemo(() => {
    const data: { strike: string; [key: string]: any }[] = [];
    for (let K = 80; K <= 120; K += 5) {
      const point: { strike: string; [key: string]: any } = {
        strike: `K=${K}`,
      };
      for (const T of [0.25, 0.5, 1.0]) {
        const S = 100,
          r = 0.05,
          sig = 0.25;
        const d1 =
          (Math.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * Math.sqrt(T));
        const d2 = d1 - sig * Math.sqrt(T);
        const Nd1 = 0.5 * (1 + erf(d1 / Math.sqrt(2)));
        const Nd2 = 0.5 * (1 + erf(d2 / Math.sqrt(2)));
        const price = S * Nd1 - K * Math.exp(-r * T) * Nd2;
        point[`T=${T}`] = +price.toFixed(2);
      }
      data.push(point);
    }
    return data;
  }, []);

  // Seismology: tail distribution (Gutenberg-Richter power law)
  const tailData = useMemo(() => {
    const rand = seededRandom(999);
    const returns: number[] = [];
    for (let i = 0; i < 504; i++) {
      const u1 = rand(),
        u2 = rand();
      const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
      returns.push(
        z * 0.015 + (rand() < 0.01 ? (rand() > 0.5 ? 1 : -1) * 0.05 : 0),
      );
    }
    const absRet = returns.map((r) => Math.abs(r)).sort((a, b) => b - a);
    const data: { x: number; logX: number; logP: number }[] = [];
    for (let i = 0; i < Math.min(100, absRet.length); i++) {
      if (absRet[i] > 0.002) {
        data.push({
          x: absRet[i],
          logX: +Math.log10(absRet[i]).toFixed(3),
          logP: +Math.log10((i + 1) / absRet.length).toFixed(3),
        });
      }
    }
    return data;
  }, []);

  // LPPL: fitted bubble curve
  const lpplData = useMemo(() => {
    const A = 5.2,
      B = -0.4,
      C = 0.08,
      tc = 300,
      m = 0.42,
      omega = 8.3,
      phi = 1.2;
    const data: { t: number; logPrice: number; lpplFit: number }[] = [];
    const rand = seededRandom(1234);
    for (let t = 0; t <= 250; t += 2) {
      const dt = tc - t;
      const base =
        A +
        B * Math.pow(dt, m) +
        C * Math.pow(dt, m) * Math.cos(omega * Math.log(dt) + phi);
      const noise = (rand() - 0.5) * 0.08;
      data.push({
        t,
        logPrice: +(base + noise).toFixed(3),
        lpplFit: +base.toFixed(3),
      });
    }
    return data;
  }, []);

  // Criticality: market temperature time series
  const tempData = useMemo(() => {
    const rand = seededRandom(555);
    const data: { day: number; temperature: number; susceptibility: number }[] =
      [];
    let temp = 0.7;
    for (let d = 0; d < 120; d++) {
      temp += (rand() - 0.48) * 0.06;
      temp = Math.max(0.1, Math.min(1.6, temp));
      const suscept =
        temp > 0.9
          ? 0.3 + (temp - 0.9) * 1.5 + (rand() - 0.5) * 0.1
          : 0.1 + temp * 0.25 + (rand() - 0.5) * 0.05;
      data.push({
        day: d,
        temperature: +temp.toFixed(3),
        susceptibility: +Math.max(0, suscept).toFixed(3),
      });
    }
    return data;
  }, []);

  return (
    <div style={{ color: "#F1F5F9" }}>
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
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 4,
          color: "#D4AF37",
        }}
      >
        Physics Lab
      </h1>
      <p style={{ color: "#94A3B8", marginBottom: 16, fontSize: 14 }}>
        Physics-inspired financial models & simulations
        {liveSpotPrice
          ? ` | Live spot: $${liveSpotPrice.toLocaleString()}`
          : ""}
      </p>

      {/* Tab bar */}
      <div
        style={{ display: "flex", gap: 4, marginBottom: 16, flexWrap: "wrap" }}
      >
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              padding: "8px 14px",
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              border:
                tab === t
                  ? "1px solid rgba(212,175,55,0.5)"
                  : "1px solid rgba(51,65,85,0.3)",
              backgroundColor:
                tab === t ? "rgba(212,175,55,0.15)" : "rgba(15,23,42,0.5)",
              color: tab === t ? "#D4AF37" : "#94A3B8",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ═══ Simulation ═══ */}
      {tab === "Simulation" && (
        <>
          <Card
            title="Geometric Brownian Motion"
            subtitle={`20 simulated price paths | S₀=${liveSpotPrice ?? 100}, μ=8%, σ=25%, T=1Y`}
            className="mb-4"
          >
            <div style={{ width: "100%", height: 360 }}>
              <ResponsiveContainer>
                <LineChart data={gbmData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="t"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    interval={19}
                    label={{
                      value: "Time (years)",
                      position: "insideBottom",
                      fill: "#64748B",
                      fontSize: 11,
                      offset: -2,
                    }}
                  />
                  <YAxis
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    label={{
                      value: "Price ($)",
                      angle: -90,
                      position: "insideLeft",
                      fill: "#64748B",
                      fontSize: 11,
                    }}
                  />
                  <Tooltip contentStyle={ttStyle} />
                  {Array.from({ length: 20 }, (_, i) => (
                    <Line
                      key={i}
                      type="monotone"
                      dataKey={`p${i}`}
                      stroke={PATH_COLORS[i]}
                      strokeWidth={1}
                      dot={false}
                      name={`Path ${i + 1}`}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div
              style={{
                marginTop: 12,
                padding: "10px 14px",
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 8,
                fontSize: 13,
                color: "#94A3B8",
              }}
            >
              <strong style={{ color: "#D4AF37" }}>dS = μ·S·dt + σ·S·dW</strong>
              <span style={{ marginLeft: 12 }}>
                where W is a Wiener process (Brownian motion)
              </span>
            </div>
          </Card>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
              gap: 16,
            }}
          >
            <Card
              title="Black-Scholes PDE"
              subtitle="European call option prices across strikes and maturities"
            >
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <LineChart data={bsData}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="rgba(51,65,85,0.3)"
                    />
                    <XAxis
                      dataKey="strike"
                      tick={{ fill: "#64748B", fontSize: 10 }}
                    />
                    <YAxis
                      tick={{ fill: "#64748B", fontSize: 10 }}
                      label={{
                        value: "Option Price ($)",
                        angle: -90,
                        position: "insideLeft",
                        fill: "#64748B",
                        fontSize: 11,
                      }}
                    />
                    <Tooltip contentStyle={ttStyle} />
                    <Line
                      type="monotone"
                      dataKey="T=0.25"
                      stroke="#EF4444"
                      strokeWidth={2}
                      dot
                      name="T=3M"
                    />
                    <Line
                      type="monotone"
                      dataKey="T=0.5"
                      stroke="#F59E0B"
                      strokeWidth={2}
                      dot
                      name="T=6M"
                    />
                    <Line
                      type="monotone"
                      dataKey="T=1"
                      stroke="#10B981"
                      strokeWidth={2}
                      dot
                      name="T=1Y"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div
                style={{
                  marginTop: 12,
                  padding: "10px 14px",
                  backgroundColor: "rgba(10,14,26,0.5)",
                  borderRadius: 8,
                  fontSize: 12,
                  color: "#94A3B8",
                }}
              >
                <div
                  style={{
                    color: "#D4AF37",
                    fontFamily: "JetBrains Mono, monospace",
                    marginBottom: 4,
                  }}
                >
                  ∂V/∂t + ½σ²S²·∂²V/∂S² + rS·∂V/∂S − rV = 0
                </div>
                <span>
                  S=100, r=5%, σ=25% | Shows option value decay as
                  time-to-expiry decreases
                </span>
              </div>
            </Card>

            <Card
              title="Heat Equation Analogy"
              subtitle="Connection between Black-Scholes and diffusion"
            >
              <div style={{ padding: 16 }}>
                <div
                  style={{
                    backgroundColor: "rgba(10,14,26,0.5)",
                    borderRadius: 10,
                    padding: 16,
                    marginBottom: 16,
                  }}
                >
                  <h4
                    style={{
                      color: "#D4AF37",
                      fontSize: 14,
                      marginBottom: 8,
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    The Transformation
                  </h4>
                  <p
                    style={{ color: "#94A3B8", fontSize: 13, lineHeight: 1.6 }}
                  >
                    The Black-Scholes PDE reduces to the{" "}
                    <span style={{ color: "#00D9FF" }}>heat equation</span> via
                    substitution:{" "}
                    <code style={{ color: "#D4AF37" }}>x = ln(S)</code>,
                    <code style={{ color: "#D4AF37" }}> τ = T − t</code>:
                  </p>
                  <div
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      color: "#F1F5F9",
                      fontSize: 14,
                      textAlign: "center",
                      margin: "12px 0",
                      padding: 8,
                      backgroundColor: "rgba(0,217,255,0.05)",
                      borderRadius: 6,
                    }}
                  >
                    ∂u/∂τ = ½σ²·∂²u/∂x²
                  </div>
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: 12,
                  }}
                >
                  {[
                    {
                      physics: "Temperature u(x,t)",
                      finance: "Option price V(S,t)",
                    },
                    {
                      physics: "Spatial coordinate x",
                      finance: "Log-price ln(S)",
                    },
                    { physics: "Thermal diffusivity k", finance: "σ²/2" },
                    {
                      physics: "Initial condition",
                      finance: "Payoff at expiry",
                    },
                  ].map((row, i) => (
                    <div key={i} style={{ display: "flex", gap: 8 }}>
                      <div
                        style={{
                          flex: 1,
                          backgroundColor: "rgba(0,217,255,0.05)",
                          borderRadius: 6,
                          padding: 8,
                          fontSize: 12,
                        }}
                      >
                        <div style={{ color: "#64748B", fontSize: 10 }}>
                          Physics
                        </div>
                        <div style={{ color: "#00D9FF" }}>{row.physics}</div>
                      </div>
                      <div
                        style={{
                          flex: 1,
                          backgroundColor: "rgba(212,175,55,0.05)",
                          borderRadius: 6,
                          padding: 8,
                          fontSize: 12,
                        }}
                      >
                        <div style={{ color: "#64748B", fontSize: 10 }}>
                          Finance
                        </div>
                        <div style={{ color: "#D4AF37" }}>{row.finance}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        </>
      )}

      {/* ═══ Seismology ═══ */}
      {tab === "Seismology" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              padding: "10px 14px",
              backgroundColor: "rgba(0,217,255,0.05)",
              borderRadius: 8,
              fontSize: 13,
              color: "#94A3B8",
            }}
          >
            <strong style={{ color: "#00D9FF" }}>
              Gutenberg-Richter Power Law:
            </strong>{" "}
            Market returns follow a power law distribution in the tails —
            extreme events are far more common than a Gaussian would predict.
            The tail exponent α ≈ 3 for equities (empirically validated).
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
              gap: 10,
            }}
          >
            {SEISMO_METRICS.map((m) => (
              <Card key={m.label}>
                <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    fontFamily: "JetBrains Mono, monospace",
                    color: m.color,
                  }}
                >
                  {m.value}
                </div>
                <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>
                  {m.sub}
                </div>
              </Card>
            ))}
          </div>
          <Card
            title="Tail Distribution (log-log)"
            subtitle="P(|r| > x) vs |r| — power law fit"
          >
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <ScatterChart>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="logX"
                    name="log₁₀|r|"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    label={{
                      value: "log₁₀|return|",
                      position: "insideBottom",
                      fill: "#64748B",
                      fontSize: 11,
                      offset: -2,
                    }}
                  />
                  <YAxis
                    dataKey="logP"
                    name="log₁₀ P(>x)"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    label={{
                      value: "log₁₀ P(>x)",
                      angle: -90,
                      position: "insideLeft",
                      fill: "#64748B",
                      fontSize: 11,
                    }}
                  />
                  <Tooltip
                    contentStyle={ttStyle}
                    formatter={(v: any) => (+v).toFixed(3)}
                  />
                  <Scatter data={tailData} fill="#D4AF37" />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <div
              style={{
                marginTop: 12,
                padding: "10px 14px",
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 8,
              }}
            >
              <div
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  color: "#D4AF37",
                  fontSize: 13,
                  marginBottom: 4,
                }}
              >
                P(|r| {">"} x) ∝ x^(−α), α ≈ 3.12
              </div>
              <div style={{ fontSize: 12, color: "#94A3B8" }}>
                Fat tails: 6σ events happen ~10× more often than Gaussian
                predicts
              </div>
            </div>
          </Card>
          <Card
            title="Omori Aftershock Analysis"
            subtitle="Volatility clustering after market shocks decays as t^(−p)"
          >
            <div style={{ padding: 16 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: 12,
                  marginBottom: 16,
                }}
              >
                <div
                  style={{
                    backgroundColor: "rgba(239,68,68,0.08)",
                    borderRadius: 8,
                    padding: 10,
                  }}
                >
                  <div style={{ fontSize: 11, color: "#64748B" }}>
                    Mainshocks Detected
                  </div>
                  <div
                    style={{
                      fontSize: 20,
                      fontWeight: 700,
                      color: "#EF4444",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    3
                  </div>
                  <div style={{ fontSize: 10, color: "#475569" }}>
                    |r| {">"} 4σ events
                  </div>
                </div>
                <div
                  style={{
                    backgroundColor: "rgba(245,158,11,0.08)",
                    borderRadius: 8,
                    padding: 10,
                  }}
                >
                  <div style={{ fontSize: 11, color: "#64748B" }}>
                    Omori Decay p
                  </div>
                  <div
                    style={{
                      fontSize: 20,
                      fontWeight: 700,
                      color: "#F59E0B",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    0.85
                  </div>
                  <div style={{ fontSize: 10, color: "#475569" }}>
                    Aftershock rate ∝ t^(−p)
                  </div>
                </div>
                <div
                  style={{
                    backgroundColor: "rgba(16,185,129,0.08)",
                    borderRadius: 8,
                    padding: 10,
                  }}
                >
                  <div style={{ fontSize: 11, color: "#64748B" }}>
                    Aftershock Status
                  </div>
                  <div
                    style={{
                      fontSize: 20,
                      fontWeight: 700,
                      color: "#10B981",
                      fontFamily: "JetBrains Mono, monospace",
                    }}
                  >
                    Normal
                  </div>
                  <div style={{ fontSize: 10, color: "#475569" }}>
                    No active aftershock
                  </div>
                </div>
              </div>
              <div style={{ fontSize: 13, color: "#94A3B8", lineHeight: 1.6 }}>
                Like physical earthquakes, large market moves trigger a sequence
                of aftershocks (volatility clustering) that decay following{" "}
                <span
                  style={{
                    color: "#D4AF37",
                    fontFamily: "JetBrains Mono, monospace",
                  }}
                >
                  Omori&apos;s law: n(t) = K / (c + t)^p
                </span>
                .
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ═══ LPPL Bubbles ═══ */}
      {tab === "LPPL Bubbles" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              padding: "10px 14px",
              backgroundColor: "rgba(239,68,68,0.05)",
              borderRadius: 8,
              fontSize: 13,
              color: "#94A3B8",
            }}
          >
            <strong style={{ color: "#EF4444" }}>
              Log-Periodic Power Law (Sornette):
            </strong>{" "}
            Financial bubbles exhibit log-periodic oscillations that accelerate
            as the crash approaches. The same pattern appears before earthquakes
            and material failure.
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
              gap: 10,
            }}
          >
            {LPPL_PARAMS.map((m) => (
              <Card key={m.label}>
                <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    fontFamily: "JetBrains Mono, monospace",
                    color: m.color,
                  }}
                >
                  {m.value}
                </div>
              </Card>
            ))}
          </div>
          <Card
            title="LPPL Fit"
            subtitle="Log-price with LPPL fitted curve — oscillations accelerate toward tc"
          >
            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <LineChart data={lpplData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="t"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    label={{
                      value: "Days",
                      position: "insideBottom",
                      fill: "#64748B",
                      fontSize: 11,
                      offset: -2,
                    }}
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    label={{
                      value: "ln(Price)",
                      angle: -90,
                      position: "insideLeft",
                      fill: "#64748B",
                      fontSize: 11,
                    }}
                  />
                  <Tooltip contentStyle={ttStyle} />
                  <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                  <Line
                    type="monotone"
                    dataKey="logPrice"
                    stroke="#94A3B8"
                    strokeWidth={1}
                    dot={false}
                    name="Observed ln(P)"
                  />
                  <Line
                    type="monotone"
                    dataKey="lpplFit"
                    stroke="#EF4444"
                    strokeWidth={2.5}
                    dot={false}
                    name="LPPL Fit"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div
              style={{
                marginTop: 12,
                padding: "10px 14px",
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 8,
              }}
            >
              <div
                style={{
                  fontFamily: "JetBrains Mono, monospace",
                  color: "#D4AF37",
                  fontSize: 12,
                  marginBottom: 4,
                }}
              >
                ln(p) = A + B(tc−t)^m + C(tc−t)^m·cos(ω·ln(tc−t) + φ)
              </div>
              <div style={{ fontSize: 12, color: "#94A3B8" }}>
                CAUTION: LPPL has ~30% false positive rate. Use alongside other
                indicators.
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* ═══ Criticality ═══ */}
      {tab === "Criticality" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              padding: "10px 14px",
              backgroundColor: "rgba(212,175,55,0.05)",
              borderRadius: 8,
              fontSize: 13,
              color: "#94A3B8",
            }}
          >
            <strong style={{ color: "#D4AF37" }}>
              Self-Organized Criticality:
            </strong>{" "}
            Markets naturally evolve toward a critical state where small
            perturbations can trigger cascades of all sizes. Near the critical
            point, susceptibility diverges — the system is maximally responsive
            to shocks.
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
              gap: 12,
            }}
          >
            {PHASES.map((p) => (
              <Card key={p.phase}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 16,
                      fontWeight: 700,
                      fontFamily: "JetBrains Mono, monospace",
                      color: p.color,
                    }}
                  >
                    {p.phase}
                  </span>
                  <Badge
                    variant={
                      p.phase === "LIQUID"
                        ? "up"
                        : p.phase === "CRITICAL"
                          ? "warning"
                          : p.phase === "GAS"
                            ? "down"
                            : "info"
                    }
                  >
                    {p.vol}
                  </Badge>
                </div>
                <div style={{ display: "flex", gap: 16, marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 10, color: "#64748B" }}>
                      Temperature
                    </div>
                    <div
                      style={{
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#F1F5F9",
                      }}
                    >
                      {p.temp}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, color: "#64748B" }}>
                      Susceptibility
                    </div>
                    <div
                      style={{
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#F1F5F9",
                      }}
                    >
                      {p.suscept}
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: "#94A3B8" }}>
                  {p.description}
                </div>
              </Card>
            ))}
          </div>
          <Card
            title="Market Temperature & Susceptibility"
            subtitle="120-day time series"
          >
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <LineChart data={tempData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="day"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                  />
                  <YAxis
                    yAxisId="temp"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    label={{
                      value: "Temperature",
                      angle: -90,
                      position: "insideLeft",
                      fill: "#D4AF37",
                      fontSize: 11,
                    }}
                  />
                  <YAxis
                    yAxisId="suscept"
                    orientation="right"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    label={{
                      value: "Susceptibility",
                      angle: 90,
                      position: "insideRight",
                      fill: "#EF4444",
                      fontSize: 11,
                    }}
                  />
                  <Tooltip contentStyle={ttStyle} />
                  <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                  <Line
                    yAxisId="temp"
                    type="monotone"
                    dataKey="temperature"
                    stroke="#D4AF37"
                    strokeWidth={2}
                    dot={false}
                    name="Market Temperature"
                  />
                  <Line
                    yAxisId="suscept"
                    type="monotone"
                    dataKey="susceptibility"
                    stroke="#EF4444"
                    strokeWidth={1.5}
                    strokeDasharray="4 4"
                    dot={false}
                    name="Susceptibility (χ)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div
              style={{
                marginTop: 12,
                padding: "10px 14px",
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 8,
                fontSize: 12,
                color: "#94A3B8",
              }}
            >
              When T → 1.0 (critical point), susceptibility χ diverges — maximum
              vulnerability to perturbations.
            </div>
          </Card>
        </div>
      )}

      {/* ═══ Percolation ═══ */}
      {tab === "Percolation" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              padding: "10px 14px",
              backgroundColor: "rgba(239,68,68,0.05)",
              borderRadius: 8,
              fontSize: 13,
              color: "#94A3B8",
            }}
          >
            <strong style={{ color: "#EF4444" }}>
              Financial Contagion (SIR Model):
            </strong>{" "}
            Assets &quot;infect&quot; each other through correlation. R₀ {">"} 1
            means cascades are self-sustaining. Percolation theory tells us the
            connectivity threshold above which local shocks go systemic.
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
              gap: 10,
            }}
          >
            {[
              {
                label: "Financial R₀",
                value: PERCOLATION.R0.toFixed(2),
                color: PERCOLATION.R0 > 1 ? "#EF4444" : "#10B981",
              },
              {
                label: "R₀ Effective",
                value: PERCOLATION.R0_eff.toFixed(2),
                color: "#F59E0B",
              },
              {
                label: "Infection Rate",
                value: `${(PERCOLATION.infectionRate * 100).toFixed(0)}%`,
                color: "#EF4444",
              },
              {
                label: "Perc. Threshold",
                value: PERCOLATION.threshold.toFixed(2),
                color: "#94A3B8",
              },
              {
                label: "Avg Correlation",
                value: PERCOLATION.avgCorr.toFixed(2),
                color:
                  PERCOLATION.avgCorr > PERCOLATION.threshold
                    ? "#EF4444"
                    : "#10B981",
              },
              {
                label: "Giant Component",
                value: `${(PERCOLATION.giantComponent * 100).toFixed(0)}%`,
                color: "#A855F7",
              },
            ].map((m) => (
              <Card key={m.label}>
                <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    fontFamily: "JetBrains Mono, monospace",
                    color: m.color,
                  }}
                >
                  {m.value}
                </div>
              </Card>
            ))}
          </div>
          <Card
            title="Asset SIR Classification"
            subtitle="Susceptible / Infected / Recovered"
          >
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    {["Asset", "State", "Vol Ratio", "Status"].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "8px 10px",
                          textAlign: h === "Asset" ? "left" : "right",
                          color: "#94A3B8",
                          fontWeight: 500,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {PERCOLATION.assets.map((a) => (
                    <tr
                      key={a.name}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td
                        style={{
                          padding: "8px 10px",
                          fontFamily: "JetBrains Mono, monospace",
                          fontWeight: 700,
                          color: "#F1F5F9",
                        }}
                      >
                        {a.name}
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "right" }}>
                        <Badge
                          variant={
                            a.state === "Infected"
                              ? "down"
                              : a.state === "Recovered"
                                ? "info"
                                : "up"
                          }
                        >
                          {a.state}
                        </Badge>
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: a.vol_ratio > 2 ? "#EF4444" : "#94A3B8",
                        }}
                      >
                        {a.vol_ratio}×
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontSize: 12,
                          color: a.color,
                        }}
                      >
                        {a.vol_ratio > 2
                          ? "Stressed"
                          : a.vol_ratio < 0.8
                            ? "Recovering"
                            : "Stable"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <div
            style={{
              padding: "12px 16px",
              backgroundColor: "rgba(10,14,26,0.5)",
              borderRadius: 8,
              fontSize: 13,
              color: "#94A3B8",
            }}
          >
            <strong style={{ color: "#EF4444" }}>Status: </strong>
            {PERCOLATION.status}
            <span style={{ display: "block", marginTop: 4 }}>
              System is{" "}
              {PERCOLATION.isSuperCritical ? (
                <span style={{ color: "#EF4444" }}>SUPERCRITICAL</span>
              ) : (
                <span style={{ color: "#10B981" }}>subcritical</span>
              )}{" "}
              —{" "}
              {PERCOLATION.isSuperCritical
                ? "cascades can self-sustain"
                : "shocks are likely to be contained"}
              .
            </span>
          </div>
        </div>
      )}

      {/* ═══ Scaling ═══ */}
      {tab === "Scaling" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              padding: "10px 14px",
              backgroundColor: "rgba(168,85,247,0.05)",
              borderRadius: 8,
              fontSize: 13,
              color: "#94A3B8",
            }}
          >
            <strong style={{ color: "#A855F7" }}>
              Scaling Laws & Universality:
            </strong>{" "}
            Markets exhibit universal power laws independent of asset or time
            period. The Hurst exponent reveals persistence (H {">"} 0.5) or
            mean-reversion (H {"<"} 0.5). Stable distribution α {"<"} 2
            indicates infinite variance.
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
              gap: 10,
            }}
          >
            {[
              {
                label: "Hurst Exponent H",
                value: SCALING.hurst.toFixed(2),
                color: "#D4AF37",
                sub:
                  SCALING.hurst > 0.55
                    ? "Persistent (trending)"
                    : SCALING.hurst < 0.45
                      ? "Mean-reverting"
                      : "Random walk",
              },
              {
                label: "Stable α",
                value: SCALING.stableAlpha.toFixed(2),
                color: "#A855F7",
                sub:
                  SCALING.stableAlpha < 2
                    ? "Fat tails — non-Gaussian"
                    : "Gaussian",
              },
              {
                label: "Stable β",
                value: SCALING.stableBeta.toFixed(2),
                color: "#94A3B8",
                sub: "Slight negative skew",
              },
            ].map((m) => (
              <Card key={m.label}>
                <div style={{ fontSize: 11, color: "#64748B" }}>{m.label}</div>
                <div
                  style={{
                    fontSize: 22,
                    fontWeight: 700,
                    fontFamily: "JetBrains Mono, monospace",
                    color: m.color,
                  }}
                >
                  {m.value}
                </div>
                <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>
                  {m.sub}
                </div>
              </Card>
            ))}
          </div>
          <Card
            title="Volatility Scaling"
            subtitle="Realized σ vs √T prediction — deviation reveals H ≠ 0.5"
          >
            <div style={{ width: "100%", height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={SCALING.volScaling}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="interval"
                    tick={{ fill: "#64748B", fontSize: 10 }}
                  />
                  <YAxis
                    tick={{ fill: "#64748B", fontSize: 10 }}
                    label={{
                      value: "σ (normalized)",
                      angle: -90,
                      position: "insideLeft",
                      fill: "#64748B",
                      fontSize: 11,
                    }}
                  />
                  <Tooltip contentStyle={ttStyle} />
                  <Legend wrapperStyle={{ color: "#94A3B8", fontSize: 12 }} />
                  <Bar
                    dataKey="realized"
                    fill="#D4AF37"
                    name="Realized Vol"
                    radius={[4, 4, 0, 0]}
                  />
                  <Bar
                    dataKey="sqrtT"
                    fill="rgba(100,116,139,0.4)"
                    name="√T Predicted"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div
              style={{
                marginTop: 12,
                padding: "10px 14px",
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 8,
                fontSize: 12,
                color: "#94A3B8",
              }}
            >
              <span
                style={{
                  color: "#D4AF37",
                  fontFamily: "JetBrains Mono, monospace",
                }}
              >
                σ(Δt) = σ₁ × Δt^H
              </span>{" "}
              — All bars above √T line: long-term risk is{" "}
              <strong>higher</strong> than standard √T rule suggests.
            </div>
          </Card>
          <Card
            title="Universality Test"
            subtitle="Do different assets share the same scaling exponents?"
          >
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    {["Asset", "Tail α", "Hurst H", "Stable α", "Class"].map(
                      (h) => (
                        <th
                          key={h}
                          style={{
                            padding: "8px 10px",
                            textAlign: h === "Asset" ? "left" : "right",
                            color: "#94A3B8",
                            fontWeight: 500,
                          }}
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {SCALING.universality.map((u) => (
                    <tr
                      key={u.asset}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td
                        style={{
                          padding: "8px 10px",
                          fontFamily: "JetBrains Mono, monospace",
                          fontWeight: 700,
                          color: "#F1F5F9",
                        }}
                      >
                        {u.asset}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#D4AF37",
                        }}
                      >
                        {u.tailAlpha}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: u.hurst > 0.55 ? "#F59E0B" : "#10B981",
                        }}
                      >
                        {u.hurst}
                      </td>
                      <td
                        style={{
                          padding: "8px 10px",
                          textAlign: "right",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#A855F7",
                        }}
                      >
                        {u.stableAlpha}
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "right" }}>
                        <Badge variant={u.asset === "BTC" ? "down" : "info"}>
                          {u.asset === "BTC" ? "Different" : "Equity-like"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div
              style={{
                marginTop: 12,
                padding: "10px 14px",
                backgroundColor: "rgba(10,14,26,0.5)",
                borderRadius: 8,
                fontSize: 12,
                color: "#94A3B8",
              }}
            >
              SPY, AAPL, GLD share similar scaling ≈ same universality class.
              BTC has fatter tails and higher persistence — different dynamics.
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
