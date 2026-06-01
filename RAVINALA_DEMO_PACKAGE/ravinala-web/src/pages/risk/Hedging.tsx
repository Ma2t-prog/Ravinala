/**
 * Hedging.tsx
 * Delta hedging simulator — price path, hedging P&L, portfolio value, delta evolution.
 * All calculations use the Black-Scholes functions from usePricing.
 */

import { useCallback, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card } from "../../components/ui/Card";
import { blackScholesGreeks, blackScholesPrice } from "../../hooks/usePricing";

// ─── Theme ───────────────────────────────────────────────────────────────────

const C = {
  bg: "#0A0E1A",
  surface: "#131823",
  elevated: "#1A2332",
  text: "#F1F5F9",
  muted: "#94A3B8",
  red: "#EF4444",
  green: "#10B981",
  blue: "#3B82F6",
  purple: "#8B5CF6",
  amber: "#F59E0B",
  accent: "#EF4444",
  border: "rgba(51,65,85,0.3)",
} as const;

const inputStyle: React.CSSProperties = {
  backgroundColor: C.elevated,
  border: `1px solid ${C.border}`,
  borderRadius: 6,
  padding: "6px 10px",
  color: C.text,
  fontSize: 13,
  width: "100%",
  outline: "none",
  fontFamily: "JetBrains Mono, monospace",
};

const labelStyle: React.CSSProperties = {
  color: C.muted,
  fontSize: 11,
  fontWeight: 600,
  textTransform: "uppercase" as const,
  letterSpacing: "0.05em",
  marginBottom: 4,
  display: "block",
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  appearance: "none" as const,
  cursor: "pointer",
};

const btnStyle: React.CSSProperties = {
  background: `linear-gradient(135deg, ${C.red}, #DC2626)`,
  color: "#fff",
  border: "none",
  borderRadius: 6,
  padding: "8px 20px",
  fontWeight: 600,
  fontSize: 13,
  cursor: "pointer",
  fontFamily: "JetBrains Mono, monospace",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function fmt(n: number, digits = 2): string {
  if (!isFinite(n)) return "—";
  return n.toFixed(digits);
}

function seededRandom(seed: number): () => number {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

function normalRandom(rng: () => number): number {
  const u1 = rng();
  const u2 = rng();
  return (
    Math.sqrt(-2 * Math.log(Math.max(u1, 1e-10))) * Math.cos(2 * Math.PI * u2)
  );
}

type HedgeFrequency = "daily" | "weekly";

// ─── Simulation types ────────────────────────────────────────────────────────

interface SimStep {
  day: number;
  price: number;
  delta: number;
  optionValue: number;
  hedgePnL: number;
  portfolioValue: number;
  cumulativeCost: number;
}

interface SimResult {
  steps: SimStep[];
  totalHedgingCost: number;
  trackingError: number;
  rebalanceCount: number;
  finalOptionPayoff: number;
}

// ─── Simulation engine ──────────────────────────────────────────────────────

function runSimulation(
  spot: number,
  strike: number,
  vol: number,
  rate: number,
  maturity: number,
  frequency: HedgeFrequency,
): SimResult {
  const rng = seededRandom(77);
  const totalDays = Math.round(maturity * 252);
  const dt = 1 / 252;
  const hedgeInterval = frequency === "daily" ? 1 : 5;

  const steps: SimStep[] = [];
  let currentSpot = spot;
  let prevDelta = 0;
  let cashAccount = 0;
  let rebalanceCount = 0;

  // Initial option value (we sold the option)
  const initialOptionValue = blackScholesPrice(
    spot,
    strike,
    maturity,
    rate,
    vol,
    "call",
  );
  cashAccount = initialOptionValue; // received premium

  for (let day = 0; day <= totalDays; day++) {
    const T = Math.max(maturity - day * dt, 0);

    // Price evolution (GBM)
    if (day > 0) {
      const drift = (rate - 0.5 * vol * vol) * dt;
      const diffusion = vol * Math.sqrt(dt) * normalRandom(rng);
      currentSpot = currentSpot * Math.exp(drift + diffusion);
    }

    const optionValue =
      T > 0
        ? blackScholesPrice(currentSpot, strike, T, rate, vol, "call")
        : Math.max(currentSpot - strike, 0);

    const greeks =
      T > 0
        ? blackScholesGreeks(currentSpot, strike, T, rate, vol, "call")
        : {
            delta: currentSpot > strike ? 1 : 0,
            gamma: 0,
            vega: 0,
            theta: 0,
            rho: 0,
          };

    const currentDelta = greeks.delta;

    // Rebalance hedge
    if (day === 0 || (day % hedgeInterval === 0 && day < totalDays)) {
      const deltaChange = currentDelta - prevDelta;
      // Buy deltaChange shares at currentSpot
      cashAccount -= deltaChange * currentSpot;
      prevDelta = currentDelta;
      if (day > 0) rebalanceCount++;
    }

    // Portfolio: short option + delta hedge + cash
    const hedgePosition = prevDelta * currentSpot;
    const cumulativeCost = -(cashAccount + hedgePosition - initialOptionValue);
    const portfolioValue = cashAccount + hedgePosition - optionValue;

    steps.push({
      day,
      price: currentSpot,
      delta: prevDelta,
      optionValue,
      hedgePnL: cumulativeCost,
      portfolioValue,
      cumulativeCost,
    });
  }

  // Final payoff
  const finalPayoff = Math.max(currentSpot - strike, 0);

  // Tracking error: std of daily portfolio value changes
  const portfolioChanges: number[] = [];
  for (let i = 1; i < steps.length; i++) {
    portfolioChanges.push(
      steps[i].portfolioValue - steps[i - 1].portfolioValue,
    );
  }
  const meanChange =
    portfolioChanges.reduce((a, b) => a + b, 0) / portfolioChanges.length;
  const trackingError = Math.sqrt(
    portfolioChanges.reduce((a, b) => a + (b - meanChange) ** 2, 0) /
      portfolioChanges.length,
  );

  const totalHedgingCost = steps[steps.length - 1].cumulativeCost;

  return {
    steps,
    totalHedgingCost,
    trackingError,
    rebalanceCount,
    finalOptionPayoff: finalPayoff,
  };
}

// ─── Stat Box ────────────────────────────────────────────────────────────────

function StatBox({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div
      style={{
        padding: "12px 16px",
        backgroundColor: C.elevated,
        borderRadius: 8,
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: 11,
          color: C.muted,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 18,
          fontWeight: 700,
          color: color || C.text,
          fontFamily: "JetBrains Mono, monospace",
        }}
      >
        {value}
      </div>
    </div>
  );
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function Hedging() {
  const [spot, setSpot] = useState(100);
  const [strike, setStrike] = useState(100);
  const [vol, setVol] = useState(0.2);
  const [rate, setRate] = useState(0.05);
  const [maturity, setMaturity] = useState(0.5);
  const [frequency, setFrequency] = useState<HedgeFrequency>("daily");
  const [result, setResult] = useState<SimResult | null>(null);

  const handleRun = useCallback(() => {
    setResult(runSimulation(spot, strike, vol, rate, maturity, frequency));
  }, [spot, strike, vol, rate, maturity, frequency]);

  // Subsample for charts (max ~100 points for smooth rendering)
  const chartData = useMemo(() => {
    if (!result) return [];
    const steps = result.steps;
    if (steps.length <= 100) return steps;
    const interval = Math.ceil(steps.length / 100);
    const sampled = steps.filter((_, i) => i % interval === 0);
    // Always include last point
    if (sampled[sampled.length - 1] !== steps[steps.length - 1]) {
      sampled.push(steps[steps.length - 1]);
    }
    return sampled;
  }, [result]);

  return (
    <div style={{ backgroundColor: C.bg, minHeight: "100vh", padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 24,
            color: C.text,
            margin: 0,
          }}
        >
          Delta Hedging Simulator
        </h1>
        <p style={{ color: C.muted, fontSize: 14, marginTop: 4 }}>
          Simulate dynamic delta hedging of a short call position
        </p>
      </div>

      {/* Inputs */}
      <Card className="mb-4">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
            gap: 16,
            alignItems: "end",
          }}
        >
          <div>
            <label style={labelStyle}>Spot Price</label>
            <input
              type="number"
              value={spot}
              onChange={(e) => setSpot(Number(e.target.value) || 100)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Strike Price</label>
            <input
              type="number"
              value={strike}
              onChange={(e) => setStrike(Number(e.target.value) || 100)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Volatility</label>
            <input
              type="number"
              step={0.01}
              value={vol}
              onChange={(e) => setVol(Number(e.target.value) || 0.2)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Risk-free Rate</label>
            <input
              type="number"
              step={0.01}
              value={rate}
              onChange={(e) => setRate(Number(e.target.value) || 0.05)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Maturity (years)</label>
            <input
              type="number"
              step={0.1}
              value={maturity}
              onChange={(e) => setMaturity(Number(e.target.value) || 0.5)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Hedge Frequency</label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value as HedgeFrequency)}
              style={selectStyle}
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </div>
          <div>
            <button onClick={handleRun} style={btnStyle}>
              Start Simulation
            </button>
          </div>
        </div>
      </Card>

      {result && (
        <>
          {/* Stats */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
              gap: 12,
              marginBottom: 16,
            }}
          >
            <StatBox
              label="Total Hedging Cost"
              value={`$${fmt(result.totalHedgingCost)}`}
              color={result.totalHedgingCost > 0 ? C.red : C.green}
            />
            <StatBox
              label="Tracking Error"
              value={`$${fmt(result.trackingError, 4)}`}
            />
            <StatBox
              label="Rebalance Count"
              value={`${result.rebalanceCount}`}
            />
            <StatBox
              label="Final Option Payoff"
              value={`$${fmt(result.finalOptionPayoff)}`}
              color={C.amber}
            />
          </div>

          {/* Charts Row 1: Price Path + Hedging P&L */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 16,
            }}
          >
            <Card
              title="Underlying Price Path"
              subtitle="Simulated GBM price evolution"
            >
              <ResponsiveContainer width="100%" height={300}>
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 30, bottom: 10, left: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="day"
                    stroke={C.muted}
                    tick={{ fill: C.muted, fontSize: 11 }}
                  />
                  <YAxis
                    stroke={C.muted}
                    tick={{ fill: C.muted, fontSize: 11 }}
                    tickFormatter={(v: any) => `$${Number(v).toFixed(0)}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: C.elevated,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                    }}
                    labelStyle={{ color: C.text }}
                    itemStyle={{ color: C.muted }}
                    formatter={(v: any) => `$${Number(v).toFixed(2)}`}
                    labelFormatter={(v: any) => `Day ${v}`}
                  />
                  <Legend wrapperStyle={{ color: C.muted, fontSize: 11 }} />
                  <Line
                    type="monotone"
                    dataKey="price"
                    stroke={C.blue}
                    strokeWidth={2}
                    dot={false}
                    name="Spot Price"
                  />
                  {/* Strike reference */}
                  <Line
                    type="monotone"
                    dataKey={() => strike}
                    stroke={C.muted}
                    strokeWidth={1}
                    strokeDasharray="5 5"
                    dot={false}
                    name="Strike"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>

            <Card
              title="Hedging P&L"
              subtitle="Accumulated hedging cost over time"
            >
              <ResponsiveContainer width="100%" height={300}>
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 30, bottom: 10, left: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="day"
                    stroke={C.muted}
                    tick={{ fill: C.muted, fontSize: 11 }}
                  />
                  <YAxis
                    stroke={C.muted}
                    tick={{ fill: C.muted, fontSize: 11 }}
                    tickFormatter={(v: any) => `$${Number(v).toFixed(1)}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: C.elevated,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                    }}
                    labelStyle={{ color: C.text }}
                    itemStyle={{ color: C.muted }}
                    formatter={(v: any) => `$${Number(v).toFixed(2)}`}
                    labelFormatter={(v: any) => `Day ${v}`}
                  />
                  <Legend wrapperStyle={{ color: C.muted, fontSize: 11 }} />
                  <Line
                    type="monotone"
                    dataKey="hedgePnL"
                    stroke={C.red}
                    strokeWidth={2}
                    dot={false}
                    name="Hedge P&L"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* Charts Row 2: Portfolio Value + Delta Evolution */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 16,
            }}
          >
            <Card
              title="Portfolio Value"
              subtitle="Option + hedge position over time"
            >
              <ResponsiveContainer width="100%" height={300}>
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 30, bottom: 10, left: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="day"
                    stroke={C.muted}
                    tick={{ fill: C.muted, fontSize: 11 }}
                  />
                  <YAxis
                    stroke={C.muted}
                    tick={{ fill: C.muted, fontSize: 11 }}
                    tickFormatter={(v: any) => `$${Number(v).toFixed(1)}`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: C.elevated,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                    }}
                    labelStyle={{ color: C.text }}
                    itemStyle={{ color: C.muted }}
                    formatter={(v: any) => `$${Number(v).toFixed(2)}`}
                    labelFormatter={(v: any) => `Day ${v}`}
                  />
                  <Legend wrapperStyle={{ color: C.muted, fontSize: 11 }} />
                  <Line
                    type="monotone"
                    dataKey="portfolioValue"
                    stroke={C.green}
                    strokeWidth={2}
                    dot={false}
                    name="Portfolio"
                  />
                  <Line
                    type="monotone"
                    dataKey="optionValue"
                    stroke={C.amber}
                    strokeWidth={1.5}
                    dot={false}
                    name="Option Value"
                    strokeDasharray="4 4"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>

            <Card
              title="Delta Evolution"
              subtitle="Hedge ratio changing over time"
            >
              <ResponsiveContainer width="100%" height={300}>
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 30, bottom: 10, left: 0 }}
                >
                  <CartesianGrid
                    strokeDasharray="3 3"
                    stroke="rgba(51,65,85,0.3)"
                  />
                  <XAxis
                    dataKey="day"
                    stroke={C.muted}
                    tick={{ fill: C.muted, fontSize: 11 }}
                  />
                  <YAxis
                    stroke={C.muted}
                    tick={{ fill: C.muted, fontSize: 11 }}
                    domain={[0, 1]}
                    tickFormatter={(v: any) => Number(v).toFixed(2)}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: C.elevated,
                      border: `1px solid ${C.border}`,
                      borderRadius: 6,
                    }}
                    labelStyle={{ color: C.text }}
                    itemStyle={{ color: C.muted }}
                    formatter={(v: any) => Number(v).toFixed(4)}
                    labelFormatter={(v: any) => `Day ${v}`}
                  />
                  <Legend wrapperStyle={{ color: C.muted, fontSize: 11 }} />
                  <Line
                    type="stepAfter"
                    dataKey="delta"
                    stroke={C.purple}
                    strokeWidth={2}
                    dot={false}
                    name="Delta"
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          </div>

          {/* Summary Table */}
          <Card
            title="Hedging P&L Breakdown"
            subtitle="Final simulation summary"
          >
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: 13,
                fontFamily: "JetBrains Mono, monospace",
              }}
            >
              <thead>
                <tr>
                  {["Metric", "Value", "Notes"].map((h) => (
                    <th
                      key={h}
                      style={{
                        textAlign: "left",
                        padding: "10px 16px",
                        color: C.muted,
                        fontSize: 11,
                        fontWeight: 600,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                        borderBottom: `1px solid ${C.border}`,
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    metric: "Option Premium Received",
                    value: `$${fmt(blackScholesPrice(spot, strike, maturity, rate, vol, "call"))}`,
                    notes: "BS price at inception",
                  },
                  {
                    metric: "Final Option Payoff",
                    value: `$${fmt(result.finalOptionPayoff)}`,
                    notes: `max(S_T - K, 0) where S_T = $${fmt(result.steps[result.steps.length - 1].price)}`,
                  },
                  {
                    metric: "Total Hedging Cost",
                    value: `$${fmt(result.totalHedgingCost)}`,
                    notes: "Cumulative cost of delta rebalancing",
                  },
                  {
                    metric: "Tracking Error",
                    value: `$${fmt(result.trackingError, 4)}`,
                    notes: "Std dev of daily portfolio value changes",
                  },
                  {
                    metric: "Rebalance Count",
                    value: `${result.rebalanceCount}`,
                    notes: `${frequency} rebalancing over ${Math.round(maturity * 252)} trading days`,
                  },
                  {
                    metric: "Net P&L",
                    value: `$${fmt(result.steps[result.steps.length - 1].portfolioValue)}`,
                    notes: "Premium + hedge - option payoff",
                  },
                ].map((row) => (
                  <tr key={row.metric}>
                    <td
                      style={{
                        padding: "10px 16px",
                        color: C.text,
                        fontWeight: 500,
                        borderBottom: `1px solid ${C.border}`,
                      }}
                    >
                      {row.metric}
                    </td>
                    <td
                      style={{
                        padding: "10px 16px",
                        fontWeight: 700,
                        borderBottom: `1px solid ${C.border}`,
                        color:
                          row.metric === "Net P&L"
                            ? result.steps[result.steps.length - 1]
                                .portfolioValue >= 0
                              ? C.green
                              : C.red
                            : C.text,
                      }}
                    >
                      {row.value}
                    </td>
                    <td
                      style={{
                        padding: "10px 16px",
                        color: C.muted,
                        fontSize: 12,
                        borderBottom: `1px solid ${C.border}`,
                      }}
                    >
                      {row.notes}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}
