import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import api from "../../api/client";
import { Card } from "../../components/ui/Card";
import { useSnapshot } from "../../hooks/useMarketData";

// ─── Theme constants ─────────────────────────────────────────────────────────
const AMBER = "#F59E0B";
const BG = "#0A0E1A";
const ELEVATED = "#1A2332";
const TEXT = "#F1F5F9";
const MUTED = "#94A3B8";
const MONO = "JetBrains Mono, monospace";
const SANS = "Inter, system-ui, sans-serif";

// ─── Product types & defaults ────────────────────────────────────────────────
type ProductType =
  | "Autocall"
  | "Reverse Convertible"
  | "Capital Protected Note"
  | "Phoenix"
  | "Worst-Of";

const PRODUCT_TYPES: ProductType[] = [
  "Autocall",
  "Reverse Convertible",
  "Capital Protected Note",
  "Phoenix",
  "Worst-Of",
];

interface ProductParams {
  underlying: string;
  strike: number;
  barrier: number;
  coupon: number;
  maturity: number;
  obsFrequency: "Monthly" | "Quarterly" | "Semi-Annual" | "Annual";
  notional: number;
}

const DEFAULT_PARAMS: ProductParams = {
  underlying: "EUROSTOXX 50",
  strike: 100,
  barrier: 60,
  coupon: 8,
  maturity: 3,
  obsFrequency: "Quarterly",
  notional: 100000,
};

const OBS_FREQUENCIES = [
  "Monthly",
  "Quarterly",
  "Semi-Annual",
  "Annual",
] as const;

// ─── Payoff generators ───────────────────────────────────────────────────────
function generatePayoff(type: ProductType, params: ProductParams) {
  const points: { spot: number; payoff: number }[] = [];
  const { strike, barrier, coupon, maturity, notional } = params;
  const barrierLevel = strike * (barrier / 100);

  for (let s = 0; s <= 200; s += 1) {
    let payoff = 0;
    const spotPct = s; // as % of initial
    const totalCoupon = (coupon / 100) * maturity * notional;

    switch (type) {
      case "Autocall":
        if (spotPct >= strike) {
          payoff = notional + totalCoupon;
        } else if (spotPct >= barrierLevel) {
          payoff = notional;
        } else {
          payoff = notional * (spotPct / strike);
        }
        break;
      case "Reverse Convertible":
        if (spotPct >= barrierLevel) {
          payoff = notional + totalCoupon;
        } else {
          payoff = notional * (spotPct / strike) + totalCoupon;
        }
        break;
      case "Capital Protected Note":
        payoff =
          notional +
          Math.max(0, ((notional * (spotPct - strike)) / strike) * 0.8);
        break;
      case "Phoenix":
        if (spotPct >= strike) {
          payoff = notional + totalCoupon;
        } else if (spotPct >= barrierLevel) {
          payoff = notional + totalCoupon * 0.5;
        } else {
          payoff = notional * (spotPct / strike);
        }
        break;
      case "Worst-Of":
        if (spotPct >= strike) {
          payoff = notional + totalCoupon;
        } else if (spotPct >= barrierLevel) {
          payoff = notional;
        } else {
          payoff = notional * (spotPct / strike) * 0.9;
        }
        break;
    }
    points.push({ spot: s, payoff });
  }
  return points;
}

function getScenarios(type: ProductType, params: ProductParams) {
  const { strike, barrier, coupon, maturity, notional } = params;

  const bull = { spotReturn: 20, label: "Bull (+20%)" };
  const base = { spotReturn: 0, label: "Base (0%)" };
  const bear = { spotReturn: -50, label: "Bear (-50%)" };

  return [bull, base, bear].map((sc) => {
    const finalSpot = strike * (1 + sc.spotReturn / 100);
    const totalCoupon = (coupon / 100) * maturity * notional;
    let payoff = 0;
    const barrierLevel = strike * (barrier / 100);

    switch (type) {
      case "Autocall":
        if (finalSpot >= strike) payoff = notional + totalCoupon;
        else if (finalSpot >= barrierLevel) payoff = notional;
        else payoff = notional * (finalSpot / strike);
        break;
      case "Reverse Convertible":
        if (finalSpot >= barrierLevel) payoff = notional + totalCoupon;
        else payoff = notional * (finalSpot / strike) + totalCoupon;
        break;
      case "Capital Protected Note":
        payoff =
          notional +
          Math.max(0, ((notional * (finalSpot - strike)) / strike) * 0.8);
        break;
      case "Phoenix":
        if (finalSpot >= strike) payoff = notional + totalCoupon;
        else if (finalSpot >= barrierLevel)
          payoff = notional + totalCoupon * 0.5;
        else payoff = notional * (finalSpot / strike);
        break;
      case "Worst-Of":
        if (finalSpot >= strike) payoff = notional + totalCoupon;
        else if (finalSpot >= barrierLevel) payoff = notional;
        else payoff = notional * (finalSpot / strike) * 0.9;
        break;
    }

    const returnPct = ((payoff - notional) / notional) * 100;
    return {
      ...sc,
      finalSpot: finalSpot.toFixed(1),
      payoff: payoff.toFixed(0),
      returnPct: returnPct.toFixed(2),
    };
  });
}

function getKeyFeatures(type: ProductType): string[] {
  switch (type) {
    case "Autocall":
      return [
        "Early redemption if underlying above autocall level on observation dates",
        "Capital at risk below barrier level",
        "Enhanced coupon for accepting downside risk",
        "Periodic observation with memory coupon feature",
      ];
    case "Reverse Convertible":
      return [
        "High fixed coupon paid regardless of performance",
        "Capital protected above barrier level",
        "Below barrier: physical or cash settlement at worst performance",
        "Short maturity typical (6-18 months)",
      ];
    case "Capital Protected Note":
      return [
        "100% capital protection at maturity",
        "Participation in upside (typically 60-100%)",
        "No downside risk beyond opportunity cost",
        "Lower coupon than barrier products",
      ];
    case "Phoenix":
      return [
        "Conditional coupon paid if above coupon barrier",
        "Memory feature: missed coupons paid later if conditions met",
        "Autocall feature on observation dates",
        "Capital at risk below put barrier",
      ];
    case "Worst-Of":
      return [
        "Payoff linked to worst performing underlying in a basket",
        "Higher coupon due to correlation risk",
        "Barrier observed on worst performer only",
        "Diversification does not reduce risk",
      ];
  }
}

// ─── Styled helpers ──────────────────────────────────────────────────────────
const inputStyle: React.CSSProperties = {
  backgroundColor: ELEVATED,
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 6,
  padding: "6px 10px",
  color: TEXT,
  fontFamily: MONO,
  fontSize: 13,
  width: "100%",
  outline: "none",
};

const selectStyle: React.CSSProperties = {
  ...inputStyle,
  cursor: "pointer",
};

const labelStyle: React.CSSProperties = {
  color: MUTED,
  fontSize: 11,
  fontFamily: SANS,
  marginBottom: 4,
  display: "block",
};

// ─── Product type → backend product_type map ─────────────────────────────────
const PRODUCT_TYPE_MAP: Record<ProductType, string> = {
  Autocall: "autocall",
  "Reverse Convertible": "barrier",
  "Capital Protected Note": "cliquet",
  Phoenix: "phoenix",
  "Worst-Of": "himalaya",
};

export default function StructuringSuite() {
  // ── Live market data ────────────────────────────────────────────────────────
  const { data: snapshot, isLoading: snapshotLoading } = useSnapshot();
  const usingFallback = !snapshot;

  const [productType, setProductType] = useState<ProductType>("Autocall");
  const [params, setParams] = useState<ProductParams>(DEFAULT_PARAMS);
  const [generatingBook, setGeneratingBook] = useState(false);
  const [bookError, setBookError] = useState<string | null>(null);

  const payoffData = useMemo(
    () => generatePayoff(productType, params),
    [productType, params],
  );
  const scenarios = useMemo(
    () => getScenarios(productType, params),
    [productType, params],
  );
  const features = useMemo(() => getKeyFeatures(productType), [productType]);

  const updateParam = <K extends keyof ProductParams>(
    key: K,
    value: ProductParams[K],
  ) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  const handleGenerateBook = async () => {
    setGeneratingBook(true);
    setBookError(null);
    try {
      const liveSpot = snapshot
        ? (Object.values(snapshot.indices)
            .flat()
            .find((idx) =>
              idx.name.toLowerCase().includes(params.underlying.toLowerCase()),
            )?.price ?? 100)
        : 100;
      const payload = {
        product_type: PRODUCT_TYPE_MAP[productType],
        product_name: `${params.underlying} ${productType}`,
        underlying: params.underlying,
        spot: liveSpot,
        strike: (params.strike / 100) * liveSpot,
        barrier_level: (params.barrier / 100) * liveSpot,
        barrier_type: "down-and-in",
        coupon_rate: params.coupon / 100,
        maturity_years: params.maturity,
        risk_free_rate: 0.04,
        volatility: 0.2,
        notional: params.notional,
        issuer: "Ravinala Capital",
        backtest_period_years: 5.0,
        var_confidence: 0.95,
        include_backtesting: true,
      };
      const response = await api.post("/v1/generate/scenariobook", payload, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(
        new Blob([response.data], { type: "application/pdf" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = `scenariobook_${params.underlying.replace(/\s+/g, "_")}_${productType.replace(/\s+/g, "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setBookError("PDF generation failed — check backend is running");
    } finally {
      setGeneratingBook(false);
    }
  };

  return (
    <div
      style={{
        background: BG,
        minHeight: "100vh",
        padding: 24,
        fontFamily: SANS,
      }}
    >
      {/* Fallback Banner */}
      {usingFallback && !snapshotLoading && (
        <div
          style={{
            backgroundColor: "rgba(245,158,11,0.1)",
            border: "1px solid rgba(245,158,11,0.3)",
            borderRadius: 6,
            padding: "8px 16px",
            marginBottom: 16,
            color: AMBER,
            fontSize: 13,
            fontFamily: MONO,
          }}
        >
          Backend unreachable — showing demo data
        </div>
      )}

      {/* Header */}
      <div
        style={{
          marginBottom: 24,
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <h1
            style={{ fontFamily: MONO, fontSize: 26, color: TEXT, margin: 0 }}
          >
            <span style={{ color: AMBER }}>&#9670;</span> Structuring Suite
          </h1>
          <p style={{ color: MUTED, fontSize: 14, marginTop: 4 }}>
            Build and analyze structured products with interactive payoff
            diagrams
          </p>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-end",
            gap: 6,
          }}
        >
          <button
            onClick={handleGenerateBook}
            disabled={generatingBook}
            style={{
              backgroundColor: generatingBook
                ? "rgba(245,158,11,0.1)"
                : "rgba(245,158,11,0.15)",
              border: "1px solid rgba(245,158,11,0.4)",
              borderRadius: 8,
              color: AMBER,
              padding: "9px 18px",
              fontSize: 13,
              fontWeight: 600,
              cursor: generatingBook ? "wait" : "pointer",
              opacity: generatingBook ? 0.7 : 1,
              fontFamily: SANS,
              whiteSpace: "nowrap",
            }}
          >
            {generatingBook ? "Generating PDF…" : "⬇ Scenario Book PDF"}
          </button>
          {bookError && (
            <span style={{ color: "#EF4444", fontSize: 12 }}>{bookError}</span>
          )}
        </div>
      </div>

      {/* Product Type Selector */}
      <div
        style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}
      >
        {PRODUCT_TYPES.map((pt) => (
          <button
            key={pt}
            onClick={() => setProductType(pt)}
            style={{
              padding: "8px 16px",
              borderRadius: 6,
              border:
                pt === productType
                  ? `1px solid ${AMBER}`
                  : "1px solid rgba(51,65,85,0.5)",
              background:
                pt === productType ? "rgba(245,158,11,0.15)" : ELEVATED,
              color: pt === productType ? AMBER : MUTED,
              fontFamily: SANS,
              fontSize: 13,
              fontWeight: pt === productType ? 600 : 400,
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            {pt}
          </button>
        ))}
      </div>

      <div
        style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 20 }}
      >
        {/* Left: Input Panel */}
        <Card title="Parameters" subtitle={productType}>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <label style={labelStyle}>Underlying</label>
              <input
                style={inputStyle}
                value={params.underlying}
                onChange={(e) => updateParam("underlying", e.target.value)}
              />
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 10,
              }}
            >
              <div>
                <label style={labelStyle}>Strike (%)</label>
                <input
                  style={inputStyle}
                  type="number"
                  value={params.strike}
                  onChange={(e) => updateParam("strike", +e.target.value)}
                />
              </div>
              <div>
                <label style={labelStyle}>Barrier (%)</label>
                <input
                  style={inputStyle}
                  type="number"
                  value={params.barrier}
                  onChange={(e) => updateParam("barrier", +e.target.value)}
                />
              </div>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 10,
              }}
            >
              <div>
                <label style={labelStyle}>Coupon (% p.a.)</label>
                <input
                  style={inputStyle}
                  type="number"
                  step="0.5"
                  value={params.coupon}
                  onChange={(e) => updateParam("coupon", +e.target.value)}
                />
              </div>
              <div>
                <label style={labelStyle}>Maturity (yrs)</label>
                <input
                  style={inputStyle}
                  type="number"
                  step="0.5"
                  value={params.maturity}
                  onChange={(e) => updateParam("maturity", +e.target.value)}
                />
              </div>
            </div>
            <div>
              <label style={labelStyle}>Observation Frequency</label>
              <select
                style={selectStyle}
                value={params.obsFrequency}
                onChange={(e) =>
                  updateParam(
                    "obsFrequency",
                    e.target.value as ProductParams["obsFrequency"],
                  )
                }
              >
                {OBS_FREQUENCIES.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Notional</label>
              <input
                style={inputStyle}
                type="number"
                step="10000"
                value={params.notional}
                onChange={(e) => updateParam("notional", +e.target.value)}
              />
            </div>
          </div>
        </Card>

        {/* Right: Results */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Payoff Diagram */}
          <Card
            title="Payoff at Maturity"
            subtitle={`${productType} — ${params.underlying}`}
          >
            <div style={{ height: 320 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={payoffData}
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
                      value: "Spot (% of Initial)",
                      position: "insideBottom",
                      offset: -10,
                      fill: MUTED,
                      fontSize: 11,
                    }}
                  />
                  <YAxis
                    stroke={MUTED}
                    tick={{ fill: MUTED, fontSize: 11, fontFamily: MONO }}
                    tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
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
                    formatter={(v: any) => [
                      `${Number(v).toLocaleString()}`,
                      "Payoff",
                    ]}
                    labelFormatter={(v: any) => `Spot: ${v}%`}
                  />
                  <ReferenceLine
                    x={params.strike}
                    stroke={MUTED}
                    strokeDasharray="5 5"
                    label={{ value: "Strike", fill: MUTED, fontSize: 10 }}
                  />
                  <ReferenceLine
                    x={(params.strike * params.barrier) / 100}
                    stroke="#EF4444"
                    strokeDasharray="5 5"
                    label={{ value: "Barrier", fill: "#EF4444", fontSize: 10 }}
                  />
                  <ReferenceLine
                    y={params.notional}
                    stroke="rgba(245,158,11,0.3)"
                    strokeDasharray="3 3"
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
          </Card>

          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}
          >
            {/* Scenario Analysis */}
            <Card title="Scenario Analysis" subtitle="Bull / Base / Bear">
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontFamily: MONO,
                  fontSize: 12,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.5)" }}>
                    {["Scenario", "Final", "Payoff", "Return"].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "6px 8px",
                          textAlign: "left",
                          color: MUTED,
                          fontWeight: 500,
                          fontSize: 11,
                        }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {scenarios.map((sc) => {
                    const ret = parseFloat(sc.returnPct);
                    return (
                      <tr
                        key={sc.label}
                        style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                      >
                        <td
                          style={{ padding: "8px", color: TEXT, fontSize: 12 }}
                        >
                          {sc.label}
                        </td>
                        <td style={{ padding: "8px", color: MUTED }}>
                          {sc.finalSpot}
                        </td>
                        <td style={{ padding: "8px", color: TEXT }}>
                          {parseInt(sc.payoff).toLocaleString()}
                        </td>
                        <td
                          style={{
                            padding: "8px",
                            color: ret >= 0 ? "#10B981" : "#EF4444",
                            fontWeight: 600,
                          }}
                        >
                          {ret >= 0 ? "+" : ""}
                          {sc.returnPct}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Card>

            {/* Key Features */}
            <Card title="Key Features" subtitle={productType}>
              <ul
                style={{
                  margin: 0,
                  padding: 0,
                  listStyle: "none",
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                }}
              >
                {features.map((f, i) => (
                  <li
                    key={i}
                    style={{
                      display: "flex",
                      gap: 8,
                      fontSize: 13,
                      color: TEXT,
                      fontFamily: SANS,
                    }}
                  >
                    <span style={{ color: AMBER, flexShrink: 0 }}>&#9656;</span>
                    {f}
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
