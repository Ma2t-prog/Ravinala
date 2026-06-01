import React, { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Badge, Card } from "../../components/ui";
import { Tabs } from "../../components/ui/Tabs";
import { useBonds, useHealth } from "../../hooks/useMarketData";

// ── Static dashboard data ──────────────────────────────────────────────────────
const CAPITAL_RATIOS = [
  {
    name: "CET1 Ratio",
    value: 13.8,
    minimum: 4.5,
    target: 11.5,
    color: "#10B981",
  },
  {
    name: "Tier 1 Ratio",
    value: 15.2,
    minimum: 6.0,
    target: 13.0,
    color: "#00D9FF",
  },
  {
    name: "Total Capital Ratio",
    value: 18.4,
    minimum: 8.0,
    target: 15.0,
    color: "#D4AF37",
  },
  {
    name: "Leverage Ratio",
    value: 5.8,
    minimum: 3.0,
    target: 5.0,
    color: "#A855F7",
  },
];

const RWA_DATA = [
  { name: "Credit Risk", value: 62, amount: 310, color: "#00D9FF" },
  { name: "Market Risk", value: 18, amount: 90, color: "#D4AF37" },
  { name: "Operational Risk", value: 12, amount: 60, color: "#EF4444" },
  { name: "CVA Risk", value: 5, amount: 25, color: "#A855F7" },
  { name: "Other", value: 3, amount: 15, color: "#94A3B8" },
];

const BUFFERS = [
  { name: "Capital Conservation Buffer", required: "2.50%", actual: "5.30%" },
  { name: "Countercyclical Buffer", required: "1.00%", actual: "1.80%" },
  { name: "G-SIB Buffer", required: "1.50%", actual: "2.30%" },
  { name: "Pillar 2 Guidance (P2G)", required: "1.25%", actual: "1.80%" },
  { name: "Combined Buffer Requirement", required: "6.25%", actual: "11.30%" },
];

const ttStyle = {
  backgroundColor: "#131823",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 8,
  color: "#F1F5F9",
};

// ── FRTB calculation logic ─────────────────────────────────────────────────────
interface SBMAsset {
  ticker: string;
  delta: number;
  spot: number;
  notional: number;
  vega: number;
  gamma: number;
}
interface SACCRTrade {
  notional: number;
  mtm: number;
  delta: number;
  collateral: number;
}

function calcSBM(assets: SBMAsset[]) {
  const RHO = 0.75; // intra-bucket delta correlation
  const VRHO = 0.65; // intra-bucket vega correlation
  const STRESS = 0.01; // 1% spot stress
  const Si = assets.map((a) => a.delta * a.spot * a.notional * STRESS);
  const sumSq = Si.reduce((s, v) => s + v * v, 0);
  let cross = 0;
  for (let i = 0; i < Si.length; i++)
    for (let j = 0; j < Si.length; j++)
      if (i !== j) cross += RHO * Si[i] * Si[j];
  const deltaCharge = Math.sqrt(Math.max(0, sumSq + cross));

  const Vi = assets.map((a) => a.vega * a.notional * STRESS);
  const vSumSq = Vi.reduce((s, v) => s + v * v, 0);
  let vCross = 0;
  for (let i = 0; i < Vi.length; i++)
    for (let j = 0; j < Vi.length; j++)
      if (i !== j) vCross += VRHO * Vi[i] * Vi[j];
  const vegaCharge = Math.sqrt(Math.max(0, vSumSq + vCross));

  const curvatureCharge = assets.reduce(
    (s, a) =>
      s + Math.abs(0.5 * a.gamma * a.spot * a.spot * a.notional * 0.0001),
    0,
  );
  return {
    deltaCharge,
    vegaCharge,
    curvatureCharge,
    total: deltaCharge + vegaCharge + curvatureCharge,
  };
}

function calcSACCR(trades: SACCRTrade[]) {
  const SF = 0.32; // supervisory factor — equity spot
  const V = trades.reduce((s, t) => s + t.mtm, 0);
  const C = trades.reduce((s, t) => s + t.collateral, 0);
  const RC = Math.max(V - C, 0);
  const rawAddOn = trades.reduce(
    (s, t) => s + Math.abs(t.delta) * t.notional * SF,
    0,
  );
  const floor = 0.05;
  const multiplier =
    rawAddOn > 0
      ? Math.min(
          1,
          floor +
            (1 - floor) * Math.exp((V - C) / (2 * (1 - floor) * rawAddOn)),
        )
      : 1;
  const addon = multiplier * rawAddOn;
  const ead = 1.4 * (RC + addon);
  return { ead, rc: RC, addon, capitalCharge: 0.08 * ead };
}

function calcKVA(trades: SACCRTrade[], coc: number) {
  const { ead, capitalCharge } = calcSACCR(trades);
  const kva = coc * ead * 2 * 0.08; // integrate over 2y horizon
  const regulatoryROE =
    capitalCharge > 0
      ? trades.reduce((s, t) => s + Math.max(t.mtm, 0) * 0.05, 0) /
        capitalCharge
      : 0;
  return { kva, coc, regulatoryROE };
}

function calcROESolver(
  notional: number,
  maturity: number,
  deltaCap: number,
  vegaCap: number,
  kva: number,
  targetROE: number,
) {
  const totalCapital = deltaCap + vegaCap + kva;
  const annualCost = totalCapital * targetROE;
  const minSpreadBps =
    notional > 0 && maturity > 0
      ? (annualCost / (notional * maturity)) * 10000
      : 0;
  return { minSpreadBps, totalCapital, annualCost, viable: minSpreadBps < 50 };
}

// ── Shared mini-components ─────────────────────────────────────────────────────
const FormulaBlock = ({ tex }: { tex: string }) => (
  <pre
    style={{
      background: "rgba(0,217,255,0.05)",
      border: "1px solid rgba(0,217,255,0.15)",
      borderRadius: 6,
      padding: "10px 14px",
      fontFamily: "JetBrains Mono, monospace",
      fontSize: 12,
      color: "#00D9FF",
      margin: "10px 0",
      whiteSpace: "pre-wrap",
      wordBreak: "break-word",
    }}
  >
    {tex}
  </pre>
);

const Metric = ({
  label,
  value,
  color = "#10B981",
}: {
  label: string;
  value: string;
  color?: string;
}) => (
  <div
    style={{
      background: "#131823",
      borderRadius: 8,
      padding: "12px 16px",
      border: "1px solid rgba(51,65,85,0.3)",
    }}
  >
    <div style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}>
      {label}
    </div>
    <div
      style={{
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 18,
        fontWeight: 700,
        color,
      }}
    >
      {value}
    </div>
  </div>
);

const inputStyle: React.CSSProperties = {
  background: "#1E293B",
  border: "1px solid rgba(51,65,85,0.5)",
  borderRadius: 6,
  color: "#F1F5F9",
  padding: "6px 10px",
  fontSize: 13,
  fontFamily: "JetBrains Mono, monospace",
  width: "100%",
  boxSizing: "border-box",
};

const btnStyle: React.CSSProperties = {
  background: "rgba(0,217,255,0.12)",
  border: "1px solid rgba(0,217,255,0.35)",
  borderRadius: 8,
  color: "#00D9FF",
  padding: "8px 20px",
  fontFamily: "JetBrains Mono, monospace",
  fontSize: 13,
  cursor: "pointer",
};

const addBtnStyle: React.CSSProperties = {
  ...btnStyle,
  background: "rgba(212,175,55,0.1)",
  border: "1px solid rgba(212,175,55,0.3)",
  color: "#D4AF37",
};

const removeBtnStyle: React.CSSProperties = {
  ...btnStyle,
  background: "rgba(239,68,68,0.1)",
  border: "1px solid rgba(239,68,68,0.3)",
  color: "#EF4444",
};

const FRTB_TABS = ["SBM Capital", "SA-CCR", "KVA", "ROE Solver"];

// ── Legal & Compliance Data ────────────────────────────────────────────────────

const REGULATIONS = [
  {
    name: 'MiFID II',
    fullName: 'Markets in Financial Instruments Directive II',
    jurisdiction: 'EU',
    status: 'Compliant',
    lastAudit: '2026-01-20',
    nextReview: '2026-07-20',
    score: 96,
    items: [
      { name: 'Best execution reporting', status: 'Compliant' },
      { name: 'Transaction reporting (RTS 25)', status: 'Compliant' },
      { name: 'Product governance', status: 'Compliant' },
      { name: 'Research unbundling', status: 'Under Review' },
    ],
  },
  {
    name: 'EMIR',
    fullName: 'European Market Infrastructure Regulation',
    jurisdiction: 'EU',
    status: 'Compliant',
    lastAudit: '2026-02-10',
    nextReview: '2026-08-10',
    score: 92,
    items: [
      { name: 'Trade reporting to TRs', status: 'Compliant' },
      { name: 'Clearing obligation', status: 'Compliant' },
      { name: 'Risk mitigation for non-cleared', status: 'Action Required' },
      { name: 'Margin requirements', status: 'Compliant' },
    ],
  },
  {
    name: 'Basel III/IV',
    fullName: 'Basel Committee on Banking Supervision',
    jurisdiction: 'Global',
    status: 'Compliant',
    lastAudit: '2026-01-30',
    nextReview: '2026-07-30',
    score: 98,
    items: [
      { name: 'Capital adequacy (CET1)', status: 'Compliant' },
      { name: 'Liquidity coverage ratio', status: 'Compliant' },
      { name: 'Net stable funding ratio', status: 'Compliant' },
      { name: 'Leverage ratio', status: 'Compliant' },
    ],
  },
  {
    name: 'Dodd-Frank',
    fullName: 'Dodd-Frank Wall Street Reform Act',
    jurisdiction: 'US',
    status: 'Partial',
    lastAudit: '2026-02-28',
    nextReview: '2026-08-28',
    score: 88,
    items: [
      { name: 'Volcker Rule compliance', status: 'Compliant' },
      { name: 'Swap dealer registration', status: 'Compliant' },
      { name: 'Position limits', status: 'Under Review' },
      { name: 'Whistleblower program', status: 'Compliant' },
    ],
  },
]

const ACTION_ITEMS = [
  { id: 1, regulation: 'EMIR', item: 'Update bilateral margin agreements for non-cleared derivatives', priority: 'High', due: '2026-04-15', owner: 'Legal Team' },
  { id: 2, regulation: 'MiFID II', item: 'Review research payment arrangements under new guidance', priority: 'Medium', due: '2026-05-01', owner: 'Compliance' },
  { id: 3, regulation: 'Dodd-Frank', item: 'Re-assess position limit calculations for commodity swaps', priority: 'Medium', due: '2026-04-30', owner: 'Risk Ops' },
  { id: 4, regulation: 'SFDR', item: 'Prepare PAI statement for next reporting period', priority: 'Low', due: '2026-06-30', owner: 'ESG Team' },
  { id: 5, regulation: 'Basel III', item: 'FRTB implementation readiness assessment', priority: 'High', due: '2026-04-01', owner: 'Market Risk' },
]

const legalStatusBadge = (s: string) => {
  if (s === 'Compliant') return <Badge variant="up">{s}</Badge>
  if (s === 'Action Required') return <Badge variant="down">{s}</Badge>
  if (s === 'Under Review') return <Badge variant="warning">{s}</Badge>
  return <Badge variant="warning">{s}</Badge>
}

// ── Page Tabs ─────────────────────────────────────────────────────────────────

const PAGE_TABS = ["Regulatory Capital", "Legal & Compliance"];

// ── Sub-components ────────────────────────────────────────────────────────────

function RegulatoryCapitalContent() {
  const { data: bondsData } = useBonds();
  const usingFallback = !bondsData;

  // FRTB tab
  const [frtbTab, setFrtbTab] = useState(0);

  // SBM
  const [sbmAssets, setSbmAssets] = useState<SBMAsset[]>([
    {
      ticker: "AAPL",
      delta: 0.5,
      spot: 150,
      notional: 100000,
      vega: 0.02,
      gamma: 0.01,
    },
    {
      ticker: "MSFT",
      delta: 0.6,
      spot: 300,
      notional: 100000,
      vega: 0.018,
      gamma: 0.008,
    },
    {
      ticker: "JPM",
      delta: 0.45,
      spot: 140,
      notional: 100000,
      vega: 0.015,
      gamma: 0.012,
    },
  ]);
  const [sbmResult, setSbmResult] = useState<ReturnType<typeof calcSBM> | null>(
    null,
  );

  // SA-CCR
  const [saccrTrades, setSaccrTrades] = useState<SACCRTrade[]>([
    { notional: 1_000_000, mtm: 50_000, delta: 0.5, collateral: 0 },
    { notional: 500_000, mtm: -20_000, delta: -0.4, collateral: 0 },
  ]);
  const [saccrResult, setSaccrResult] = useState<ReturnType<
    typeof calcSACCR
  > | null>(null);

  // KVA
  const [kvaCoc, setKvaCoc] = useState(10);
  const [kvaResult, setKvaResult] = useState<ReturnType<typeof calcKVA> | null>(
    null,
  );

  // ROE Solver
  const [roeNotional, setRoeNotional] = useState(10_000_000);
  const [roeMaturity, setRoeMaturity] = useState(2);
  const [roeDeltaCap, setRoeDeltaCap] = useState(50_000);
  const [roeVegaCap, setRoeVegaCap] = useState(20_000);
  const [roeKvaVal, setRoeKvaVal] = useState(30_000);
  const [roeTarget, setRoeTarget] = useState(12);
  const [roeResult, setRoeResult] = useState<ReturnType<
    typeof calcROESolver
  > | null>(null);

  const updateSbm = (i: number, field: keyof SBMAsset, raw: string) => {
    const val: string | number =
      field === "ticker" ? raw : parseFloat(raw) || 0;
    setSbmAssets((prev) =>
      prev.map((a, idx) => (idx === i ? { ...a, [field]: val } : a)),
    );
    setSbmResult(null);
  };
  const updateSaccr = (i: number, field: keyof SACCRTrade, raw: string) => {
    const val = parseFloat(raw) || 0;
    setSaccrTrades((prev) =>
      prev.map((t, idx) => (idx === i ? { ...t, [field]: val } : t)),
    );
    setSaccrResult(null);
  };

  return (
    <div>
      <p style={{ color: "#94A3B8", marginBottom: 20, fontSize: 14 }}>
        Basel IV stack: capital ratios, RWA, SBM, SA-CCR, KVA and ROE solver
      </p>

      {usingFallback && (
        <div
          style={{
            background: "rgba(245,158,11,0.08)",
            border: "1px solid rgba(245,158,11,0.2)",
            borderRadius: 8,
            padding: "8px 14px",
            marginBottom: 16,
            fontSize: 12,
            color: "#F59E0B",
          }}
        >
          Backend unreachable — showing demo data
        </div>
      )}

      {/* ── Capital Ratios ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: 12,
          marginBottom: 16,
        }}
      >
        {CAPITAL_RATIOS.map((r) => (
          <Card key={r.name}>
            <div style={{ fontSize: 12, color: "#94A3B8", marginBottom: 4 }}>
              {r.name}
            </div>
            <div
              style={{
                fontSize: 28,
                fontWeight: 700,
                fontFamily: "JetBrains Mono, monospace",
                color: r.color,
              }}
            >
              {r.value}%
            </div>
            <div style={{ marginTop: 8 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 11,
                  color: "#64748B",
                  marginBottom: 2,
                }}
              >
                <span>Min: {r.minimum}%</span>
                <span>Target: {r.target}%</span>
              </div>
              <div
                style={{
                  width: "100%",
                  height: 6,
                  backgroundColor: "rgba(51,65,85,0.3)",
                  borderRadius: 3,
                  position: "relative",
                }}
              >
                <div
                  style={{
                    width: `${Math.min((r.value / 20) * 100, 100)}%`,
                    height: 6,
                    borderRadius: 3,
                    backgroundColor: r.color,
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: -2,
                    left: `${(r.minimum / 20) * 100}%`,
                    width: 2,
                    height: 10,
                    backgroundColor: "#EF4444",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: -2,
                    left: `${(r.target / 20) * 100}%`,
                    width: 2,
                    height: 10,
                    backgroundColor: "#F59E0B",
                  }}
                />
              </div>
            </div>
            <div style={{ marginTop: 4 }}>
              <Badge variant="up">
                Surplus: +{(r.value - r.target).toFixed(1)}%
              </Badge>
            </div>
          </Card>
        ))}
      </div>

      {/* ── RWA + Buffers ── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))",
          gap: 16,
          marginBottom: 28,
        }}
      >
        <Card title="Risk-Weighted Assets" subtitle="Total RWA: $500B">
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={RWA_DATA}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={95}
                  innerRadius={50}
                  label={({ name, value }: any) => `${name}: ${value}%`}
                  labelLine={false}
                  style={{ fontSize: 10 }}
                >
                  {RWA_DATA.map((_r, i) => (
                    <Cell key={i} fill={RWA_DATA[i].color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={ttStyle}
                  formatter={(v: any, name: any) => {
                    const item = RWA_DATA.find((r) => r.name === name);
                    return [`${v}% ($${item?.amount}B)`, name];
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            {RWA_DATA.map((r) => (
              <div
                key={r.name}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                  fontSize: 11,
                }}
              >
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: 2,
                    backgroundColor: r.color,
                  }}
                />
                <span style={{ color: "#94A3B8" }}>
                  {r.name}: ${r.amount}B
                </span>
              </div>
            ))}
          </div>
        </Card>

        <Card
          title="Buffer Requirements"
          subtitle="Regulatory capital buffer compliance"
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
                  {["Buffer", "Required", "Actual", "Status"].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: "8px 10px",
                        textAlign: h === "Buffer" ? "left" : "center",
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
                {BUFFERS.map((b) => (
                  <tr
                    key={b.name}
                    style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                  >
                    <td
                      style={{
                        padding: "8px 10px",
                        color: "#F1F5F9",
                        fontSize: 12,
                      }}
                    >
                      {b.name}
                    </td>
                    <td
                      style={{
                        padding: "8px 10px",
                        textAlign: "center",
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#94A3B8",
                      }}
                    >
                      {b.required}
                    </td>
                    <td
                      style={{
                        padding: "8px 10px",
                        textAlign: "center",
                        fontFamily: "JetBrains Mono, monospace",
                        color: "#10B981",
                      }}
                    >
                      {b.actual}
                    </td>
                    <td style={{ padding: "8px 10px", textAlign: "center" }}>
                      <Badge variant="up">Met</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* ── FRTB Interactive Calculator ── */}
      <div style={{ marginBottom: 12 }}>
        <h2
          style={{
            fontFamily: "JetBrains Mono, monospace",
            fontSize: 18,
            color: "#D4AF37",
            marginBottom: 2,
          }}
        >
          FRTB Interactive Calculator
        </h2>
        <p style={{ color: "#94A3B8", fontSize: 13 }}>
          Simplified Basel IV stack — SBM, SA-CCR, KVA and ROE solver
        </p>
      </div>

      {/* FRTB Tab bar */}
      <div
        style={{
          display: "flex",
          gap: 2,
          marginBottom: 16,
          borderBottom: "1px solid rgba(51,65,85,0.4)",
        }}
      >
        {FRTB_TABS.map((t, i) => (
          <button
            key={t}
            onClick={() => setFrtbTab(i)}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              padding: "8px 18px",
              fontSize: 13,
              color: frtbTab === i ? "#00D9FF" : "#94A3B8",
              borderBottom: `2px solid ${frtbTab === i ? "#00D9FF" : "transparent"}`,
              fontFamily: "Inter, sans-serif",
              fontWeight: frtbTab === i ? 600 : 400,
              marginBottom: -1,
              transition: "color 0.15s",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ── FRTB Tab 0: SBM Capital ── */}
      {frtbTab === 0 && (
        <Card
          title="Sensitivities-Based Method (SBM)"
          subtitle="Per-asset Greeks → Delta / Vega / Curvature charges"
        >
          {sbmAssets.map((a, i) => (
            <details key={i} open={i === 0} style={{ marginBottom: 8 }}>
              <summary
                style={{
                  cursor: "pointer",
                  padding: "8px 12px",
                  background: "rgba(51,65,85,0.2)",
                  borderRadius: 6,
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 13,
                  color: "#F1F5F9",
                  listStyle: "none",
                  display: "flex",
                  justifyContent: "space-between",
                  userSelect: "none",
                }}
              >
                <span>
                  Asset {i + 1}: {a.ticker}
                </span>
                <span style={{ color: "#64748B", fontSize: 11 }}>▾ expand</span>
              </summary>
              <div
                style={{
                  padding: "12px 0",
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
                  gap: 10,
                }}
              >
                {(
                  [
                    "ticker",
                    "delta",
                    "spot",
                    "notional",
                    "vega",
                    "gamma",
                  ] as (keyof SBMAsset)[]
                ).map((field) => (
                  <div key={field}>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#64748B",
                        marginBottom: 4,
                        textTransform: "capitalize",
                      }}
                    >
                      {field}
                    </div>
                    <input
                      type={field === "ticker" ? "text" : "number"}
                      value={a[field]}
                      step={
                        field === "delta" ||
                        field === "vega" ||
                        field === "gamma"
                          ? "0.001"
                          : field === "spot"
                            ? "1"
                            : "10000"
                      }
                      onChange={(e) => updateSbm(i, field, e.target.value)}
                      style={inputStyle}
                    />
                  </div>
                ))}
              </div>
            </details>
          ))}
          <div
            style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}
          >
            <button
              onClick={() => {
                setSbmAssets((p) => [
                  ...p,
                  {
                    ticker: `A${p.length + 1}`,
                    delta: 0.5,
                    spot: 100,
                    notional: 100000,
                    vega: 0.02,
                    gamma: 0.01,
                  },
                ]);
                setSbmResult(null);
              }}
              style={addBtnStyle}
            >
              + Add Asset
            </button>
            {sbmAssets.length > 1 && (
              <button
                onClick={() => {
                  setSbmAssets((p) => p.slice(0, -1));
                  setSbmResult(null);
                }}
                style={removeBtnStyle}
              >
                − Remove Last
              </button>
            )}
            <button
              onClick={() => setSbmResult(calcSBM(sbmAssets))}
              style={btnStyle}
            >
              Calculate FRTB Capital
            </button>
          </div>
          {sbmResult && (
            <div style={{ marginTop: 16 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                  gap: 10,
                  marginBottom: 10,
                }}
              >
                <Metric
                  label="Delta Charge"
                  value={`$${sbmResult.deltaCharge.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                />
                <Metric
                  label="Vega Charge"
                  value={`$${sbmResult.vegaCharge.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                  color="#00D9FF"
                />
                <Metric
                  label="Curvature Charge"
                  value={`$${sbmResult.curvatureCharge.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                  color="#D4AF37"
                />
                <Metric
                  label="Total FRTB Capital"
                  value={`$${sbmResult.total.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                  color="#A855F7"
                />
              </div>
              <FormulaBlock
                tex={`K = √( ΣSᵢ² + Σ ρᵢⱼ·Sᵢ·Sⱼ )   [ρ_delta = 0.75, ρ_vega = 0.65]\nSᵢ = δᵢ × Spotᵢ × Notionalᵢ × σ_stress`}
              />
            </div>
          )}
        </Card>
      )}

      {/* ── FRTB Tab 1: SA-CCR ── */}
      {frtbTab === 1 && (
        <Card
          title="SA-CCR — Standardised Approach for Counterparty Credit Risk"
          subtitle="EAD = 1.4 × (RC + Multiplier × AddOn)"
        >
          {saccrTrades.map((t, i) => (
            <details key={i} open={i === 0} style={{ marginBottom: 8 }}>
              <summary
                style={{
                  cursor: "pointer",
                  padding: "8px 12px",
                  background: "rgba(51,65,85,0.2)",
                  borderRadius: 6,
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 13,
                  color: "#F1F5F9",
                  listStyle: "none",
                  display: "flex",
                  justifyContent: "space-between",
                  userSelect: "none",
                }}
              >
                <span>Trade {i + 1}</span>
                <span
                  style={{
                    color: t.mtm >= 0 ? "#10B981" : "#EF4444",
                    fontSize: 11,
                  }}
                >
                  MtM: {t.mtm >= 0 ? "+" : ""}
                  {t.mtm.toLocaleString()}
                </span>
              </summary>
              <div
                style={{
                  padding: "12px 0",
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
                  gap: 10,
                }}
              >
                {(
                  [
                    "notional",
                    "mtm",
                    "delta",
                    "collateral",
                  ] as (keyof SACCRTrade)[]
                ).map((field) => (
                  <div key={field}>
                    <div
                      style={{
                        fontSize: 11,
                        color: "#64748B",
                        marginBottom: 4,
                        textTransform: "capitalize",
                      }}
                    >
                      {field}
                    </div>
                    <input
                      type="number"
                      value={t[field]}
                      step={field === "delta" ? "0.01" : "10000"}
                      onChange={(e) => updateSaccr(i, field, e.target.value)}
                      style={inputStyle}
                    />
                  </div>
                ))}
              </div>
            </details>
          ))}
          <div
            style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}
          >
            <button
              onClick={() => {
                setSaccrTrades((p) => [
                  ...p,
                  { notional: 1_000_000, mtm: 0, delta: 0.5, collateral: 0 },
                ]);
                setSaccrResult(null);
              }}
              style={addBtnStyle}
            >
              + Add Trade
            </button>
            {saccrTrades.length > 1 && (
              <button
                onClick={() => {
                  setSaccrTrades((p) => p.slice(0, -1));
                  setSaccrResult(null);
                }}
                style={removeBtnStyle}
              >
                − Remove Last
              </button>
            )}
            <button
              onClick={() => setSaccrResult(calcSACCR(saccrTrades))}
              style={btnStyle}
            >
              Calculate SA-CCR EAD
            </button>
          </div>
          {saccrResult && (
            <div style={{ marginTop: 16 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                  gap: 10,
                  marginBottom: 10,
                }}
              >
                <Metric
                  label="EAD"
                  value={`$${saccrResult.ead.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                />
                <Metric
                  label="Replacement Cost"
                  value={`$${saccrResult.rc.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                  color="#00D9FF"
                />
                <Metric
                  label="PFE Add-On"
                  value={`$${saccrResult.addon.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                  color="#D4AF37"
                />
                <Metric
                  label="Capital Charge (8%)"
                  value={`$${saccrResult.capitalCharge.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                  color="#A855F7"
                />
              </div>
              <FormulaBlock
                tex={`EAD = 1.4 × (RC + Multiplier × AddOn)\nMultiplier = min(1, 0.05 + 0.95 × exp(V-C / (1.9 × AddOn)))\nAddOn = Σ |δᵢ| × Notionalᵢ × SF_equity   [SF = 32%]`}
              />
            </div>
          )}
        </Card>
      )}

      {/* ── FRTB Tab 2: KVA ── */}
      {frtbTab === 2 && (
        <Card
          title="KVA — Capital Valuation Adjustment"
          subtitle="Cost of capital charge across the trade lifetime"
        >
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: "#64748B", marginBottom: 6 }}>
              Cost of Capital:{" "}
              <span
                style={{
                  color: "#00D9FF",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 14,
                }}
              >
                {kvaCoc}%
              </span>
            </div>
            <input
              type="range"
              min={6}
              max={20}
              step={0.5}
              value={kvaCoc}
              onChange={(e) => {
                setKvaCoc(parseFloat(e.target.value));
                setKvaResult(null);
              }}
              style={{ width: 260, accentColor: "#00D9FF", display: "block" }}
            />
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 10,
                color: "#475569",
                width: 260,
                marginTop: 2,
              }}
            >
              <span>6%</span>
              <span>20%</span>
            </div>
          </div>
          <p style={{ fontSize: 12, color: "#64748B", marginBottom: 10 }}>
            Uses {saccrTrades.length} trade{saccrTrades.length !== 1 ? "s" : ""}{" "}
            from SA-CCR tab.
          </p>
          <button
            onClick={() => setKvaResult(calcKVA(saccrTrades, kvaCoc / 100))}
            style={btnStyle}
          >
            Calculate KVA
          </button>
          {kvaResult && (
            <div style={{ marginTop: 16 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                  gap: 10,
                  marginBottom: 10,
                }}
              >
                <Metric
                  label="KVA"
                  value={`$${kvaResult.kva.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                />
                <Metric
                  label="Cost of Capital"
                  value={`${(kvaResult.coc * 100).toFixed(1)}%`}
                  color="#00D9FF"
                />
                <Metric
                  label="Regulatory ROE"
                  value={`${(kvaResult.regulatoryROE * 100).toFixed(1)}%`}
                  color="#D4AF37"
                />
              </div>
              <FormulaBlock tex="KVA = CoC × ∫₀ᵀ E[EAD(t)] · e^{-rt} dt" />
            </div>
          )}
        </Card>
      )}

      {/* ── FRTB Tab 3: ROE Solver ── */}
      {frtbTab === 3 && (
        <Card
          title="ROE Solver — Minimum Spread"
          subtitle="Solve for the spread required to meet a target ROE"
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
              gap: 12,
              marginBottom: 14,
            }}
          >
            {(
              [
                {
                  label: "Notional ($)",
                  value: roeNotional,
                  setter: setRoeNotional,
                  step: 1_000_000,
                },
                {
                  label: "Maturity (Y)",
                  value: roeMaturity,
                  setter: setRoeMaturity,
                  step: 0.5,
                },
                {
                  label: "Delta Capital ($)",
                  value: roeDeltaCap,
                  setter: setRoeDeltaCap,
                  step: 5_000,
                },
                {
                  label: "Vega Capital ($)",
                  value: roeVegaCap,
                  setter: setRoeVegaCap,
                  step: 5_000,
                },
                {
                  label: "KVA ($)",
                  value: roeKvaVal,
                  setter: setRoeKvaVal,
                  step: 5_000,
                },
              ] as {
                label: string;
                value: number;
                setter: (v: number) => void;
                step: number;
              }[]
            ).map(({ label, value, setter, step }) => (
              <div key={label}>
                <div
                  style={{ fontSize: 11, color: "#64748B", marginBottom: 4 }}
                >
                  {label}
                </div>
                <input
                  type="number"
                  value={value}
                  step={step}
                  onChange={(e) => {
                    setter(parseFloat(e.target.value) || 0);
                    setRoeResult(null);
                  }}
                  style={inputStyle}
                />
              </div>
            ))}
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: "#64748B", marginBottom: 6 }}>
              Target ROE:{" "}
              <span
                style={{
                  color: "#00D9FF",
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 14,
                }}
              >
                {roeTarget}%
              </span>
            </div>
            <input
              type="range"
              min={5}
              max={25}
              step={1}
              value={roeTarget}
              onChange={(e) => {
                setRoeTarget(parseFloat(e.target.value));
                setRoeResult(null);
              }}
              style={{ width: 260, accentColor: "#00D9FF", display: "block" }}
            />
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 10,
                color: "#475569",
                width: 260,
                marginTop: 2,
              }}
            >
              <span>5%</span>
              <span>25%</span>
            </div>
          </div>
          <button
            onClick={() =>
              setRoeResult(
                calcROESolver(
                  roeNotional,
                  roeMaturity,
                  roeDeltaCap,
                  roeVegaCap,
                  roeKvaVal,
                  roeTarget / 100,
                ),
              )
            }
            style={btnStyle}
          >
            Solve
          </button>
          {roeResult && (
            <div style={{ marginTop: 16 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                  gap: 10,
                  marginBottom: 10,
                }}
              >
                <Metric
                  label="Min Spread Required"
                  value={`${roeResult.minSpreadBps.toFixed(1)} bps`}
                />
                <Metric
                  label="Total Capital"
                  value={`$${roeResult.totalCapital.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                  color="#00D9FF"
                />
                <Metric
                  label="Annual Cost"
                  value={`$${roeResult.annualCost.toLocaleString("en", { maximumFractionDigits: 0 })}`}
                  color="#D4AF37"
                />
                <div
                  style={{
                    background: "#131823",
                    borderRadius: 8,
                    padding: "12px 16px",
                    border: `1px solid ${roeResult.viable ? "rgba(16,185,129,0.35)" : "rgba(239,68,68,0.35)"}`,
                  }}
                >
                  <div
                    style={{ fontSize: 11, color: "#64748B", marginBottom: 2 }}
                  >
                    Viability
                  </div>
                  <div
                    style={{
                      fontFamily: "JetBrains Mono, monospace",
                      fontSize: 15,
                      fontWeight: 700,
                      color: roeResult.viable ? "#10B981" : "#EF4444",
                    }}
                  >
                    {roeResult.viable ? "Viable Trade" : "Uneconomical"}
                  </div>
                </div>
              </div>
              <FormulaBlock tex="Min Spread (bps) = (Total Capital × Target ROE) / (Notional × Maturity) × 10 000" />
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function LegalComplianceContent() {
  const { data: healthData } = useHealth()

  return (
    <div>
      {!healthData && (
        <div style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, padding: '8px 16px', marginBottom: 16, fontSize: 13, color: '#F59E0B', fontFamily: 'Inter, sans-serif' }}>
          Backend unreachable — displaying demo data
        </div>
      )}
      <p style={{ color: '#94A3B8', marginBottom: 20, fontSize: 14 }}>
        Regulatory compliance tracker &amp; action items
        {healthData && (
          <span style={{ marginLeft: 12, fontSize: 12, color: healthData.status === 'ok' ? '#10B981' : '#EF4444' }}>
            · Backend {healthData.status === 'ok' ? 'connected' : 'disconnected'}
          </span>
        )}
      </p>

      {/* Regulation cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16, marginBottom: 16 }}>
        {REGULATIONS.map(reg => (
          <Card key={reg.name}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontWeight: 700, fontSize: 18, color: '#00D9FF' }}>{reg.name}</span>
                  <Badge variant="info">{reg.jurisdiction}</Badge>
                </div>
                <div style={{ fontSize: 12, color: '#64748B', marginTop: 2 }}>{reg.fullName}</div>
              </div>
              {legalStatusBadge(reg.status)}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <div style={{ flex: 1, height: 6, backgroundColor: 'rgba(51,65,85,0.3)', borderRadius: 3 }}>
                <div style={{
                  width: `${reg.score}%`, height: 6, borderRadius: 3,
                  backgroundColor: reg.score >= 95 ? '#10B981' : reg.score >= 90 ? '#F59E0B' : '#EF4444',
                }} />
              </div>
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color: '#F1F5F9', fontWeight: 600 }}>{reg.score}%</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {reg.items.map((item, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, padding: '4px 0' }}>
                  <span style={{ color: '#94A3B8' }}>{item.name}</span>
                  {legalStatusBadge(item.status)}
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 16, marginTop: 10, fontSize: 11, color: '#64748B' }}>
              <span>Last audit: {reg.lastAudit}</span>
              <span>Next review: {reg.nextReview}</span>
            </div>
          </Card>
        ))}
      </div>

      {/* Action Items */}
      <Card title="Action Items" subtitle="Outstanding compliance tasks">
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(51,65,85,0.4)' }}>
                {['Regulation', 'Action Item', 'Priority', 'Due Date', 'Owner'].map(h => (
                  <th key={h} style={{ padding: '8px 10px', textAlign: 'left', color: '#94A3B8', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ACTION_ITEMS.map(a => (
                <tr key={a.id} style={{ borderBottom: '1px solid rgba(51,65,85,0.2)' }}>
                  <td style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace', color: '#00D9FF', fontWeight: 600 }}>{a.regulation}</td>
                  <td style={{ padding: '8px 10px', color: '#F1F5F9', fontSize: 12 }}>{a.item}</td>
                  <td style={{ padding: '8px 10px' }}>
                    <Badge variant={a.priority === 'High' ? 'down' : a.priority === 'Medium' ? 'warning' : 'neutral'}>{a.priority}</Badge>
                  </td>
                  <td style={{ padding: '8px 10px', fontFamily: 'JetBrains Mono, monospace', color: '#94A3B8', fontSize: 12 }}>{a.due}</td>
                  <td style={{ padding: '8px 10px', color: '#94A3B8' }}>{a.owner}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
export default function RegulatoryCapital() {
  const [activeTab, setActiveTab] = useState(PAGE_TABS[0]);

  return (
    <div style={{ color: "#F1F5F9" }}>
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 16,
        }}
      >
        Regulatory Capital
      </h1>

      <Tabs tabs={PAGE_TABS} active={activeTab} onChange={setActiveTab} />

      <div style={{ marginTop: 20 }}>
        {activeTab === "Regulatory Capital" && <RegulatoryCapitalContent />}
        {activeTab === "Legal & Compliance" && <LegalComplianceContent />}
      </div>
    </div>
  );
}
