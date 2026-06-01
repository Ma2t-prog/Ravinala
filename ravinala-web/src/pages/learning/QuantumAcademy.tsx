import { useState } from "react";
import { Badge, Card } from "../../components/ui";
import { Tabs } from "../../components/ui/Tabs";
import { useHealth } from "../../hooks/useMarketData";

// ── Shared formula renderer ────────────────────────────────────────────────────
const Formula = ({ src }: { src: string }) => (
  <pre
    style={{
      background: "rgba(99,102,241,0.07)",
      border: "1px solid rgba(99,102,241,0.2)",
      borderRadius: 6,
      padding: "10px 16px",
      fontFamily: "JetBrains Mono, monospace",
      fontSize: 12,
      color: "#A5B4FC",
      margin: "8px 0",
      whiteSpace: "pre-wrap",
      wordBreak: "break-word",
      lineHeight: 1.7,
    }}
  >
    {src}
  </pre>
);

const InfoBox = ({ children }: { children: React.ReactNode }) => (
  <div
    style={{
      background: "rgba(0,217,255,0.06)",
      border: "1px solid rgba(0,217,255,0.2)",
      borderRadius: 6,
      padding: "10px 14px",
      fontSize: 13,
      color: "#94A3B8",
      marginTop: 8,
      lineHeight: 1.6,
    }}
  >
    {children}
  </div>
);

const SectionTitle = ({ children }: { children: React.ReactNode }) => (
  <h3
    style={{
      fontFamily: "JetBrains Mono, monospace",
      fontSize: 15,
      color: "#6366F1",
      marginBottom: 8,
      marginTop: 16,
    }}
  >
    {children}
  </h3>
);

// ── Greeks dataset ─────────────────────────────────────────────────────────────
const GREEKS: Record<
  string,
  { formula: string; interpretation: string; insight: string }
> = {
  "Delta (Δ)": {
    formula: "Δ_call = e^{-qT} · N(d₁)\nΔ_put  = e^{-qT} · (N(d₁) - 1)",
    interpretation:
      "Price move per $1 spot change. A delta of 0.6 means the option gains ~$0.60 for every $1 rise in the underlying.",
    insight:
      "Hedging: hold -Δ shares per long call. Delta ranges (0,1) for calls and (-1,0) for puts. ATM options have Δ ≈ 0.5.",
  },
  "Gamma (Γ)": {
    formula: "Γ = e^{-qT} · N'(d₁) / (S · σ · √T)",
    interpretation:
      "Rate of Delta change per $1 spot move. Long options always have positive Gamma — large moves create profit regardless of direction.",
    insight:
      "Gamma peaks ATM near expiry (→ ∞ at expiry). Long Gamma = profits from realised vol > implied vol.",
  },
  "Vega (ν)": {
    formula: "ν = S · e^{-qT} · √T · N'(d₁) / 100",
    interpretation:
      "Price change per 1% increase in implied volatility. Always positive for long options (calls and puts).",
    insight:
      "Vega is highest ATM and for long-dated options. Vega fades as maturity → 0. Vega > 0 ⟹ long vol position.",
  },
  "Theta (Θ)": {
    formula:
      "Θ = [-S·e^{-qT}·N'(d₁)·σ / (2√T)] - r·K·e^{-rT}·N(d₂) + q·S·e^{-qT}·N(d₁)",
    interpretation:
      "Daily time decay in dollars. Theta is negative for long options — you lose value each day due to time value erosion.",
    insight:
      "BSM identity: Θ ≈ -½ Γ S² σ²  (Theta–Gamma relationship). Short Gamma positions earn Theta.",
  },
  Vanna: {
    formula: "Vanna = -e^{-qT} · N'(d₁) · d₂/σ\n      = ∂Δ/∂σ  =  ∂ν/∂S",
    interpretation:
      "How Delta changes with implied vol, and how Vega changes with spot. Critical for crash-hedging and skew risk.",
    insight:
      "Vanna is large for OTM options near expiry. A vol spike + spot drop = large Vanna P&L for barrier books.",
  },
  "Volga (Vomma)": {
    formula:
      "Volga = S · e^{-qT} · √T · N'(d₁) · d₁·d₂/σ\n      = ∂²V/∂σ²  =  ∂ν/∂σ",
    interpretation:
      "Convexity of option price vs volatility — acceleration of Vega. Highest for OTM options.",
    insight:
      "Vol-of-vol risk. Positive Volga means you benefit from vol moves in either direction (convexity in vol space).",
  },
  Charm: {
    formula:
      "Charm = -e^{-qT} · N'(d₁) · [2(r-q)T - d₂·σ√T] / (2T·σ√T)\n      = ∂Δ/∂t  (daily delta decay)",
    interpretation:
      "How Delta changes overnight — rate of Delta decay. Essential for managing delta positions over weekends.",
    insight:
      "Charm is zero for ATM options. For ITM calls, Charm > 0 (Delta approaches 1). For OTM calls, Charm < 0.",
  },
};

const GREEK_NAMES = Object.keys(GREEKS);

// ── Exotic payoffs ─────────────────────────────────────────────────────────────
const EXOTICS: Record<string, { payoff: string; description: string }> = {
  "Barrier (Down-In)": {
    payoff: "V_DI(T) = (S_T - K)⁺ · 𝟙{ min_{0≤t≤T} Sₜ > B }",
    description:
      "The option only activates if the spot ever breaches the barrier B from above. Gap Risk: spot can jump below B overnight — cannot hedge continuously. Must be priced via Monte Carlo with small Δt or via PDE with barrier boundary condition.",
  },
  "Asian (Average Price)": {
    payoff: "V_Asian(T) = ( (1/N) Σᵢ S_{tᵢ} - K )⁺",
    description:
      "Payoff based on the average spot over observation dates. Averaging reduces variance → cheaper than vanilla. Widely used in FX and Commodities to reduce fixing risk and smooth out manipulation at single fixing points.",
  },
  Autocall: {
    payoff: `Payoff at tᵢ:\n  100(1 + c·i)   if S_{tᵢ} ≥ K_call  [autocall]\n  Continue        if B < S_{tᵢ} < K_call\n  100 · S_T/S₀   if S_T ≤ B         [capital loss]`,
    description:
      "Delta profile: Negative delta near autocall trigger (digital risk). Large negative Gamma at the trigger level. Requires careful gamma hedging and digital hedging via spread approximation. Correlation risk when basket underlying.",
  },
  Himalaya: {
    payoff: "Payoff = (1/n) Σₖ max_{j ∉ removed} Sⱼ(tₖ)/Sⱼ(0)",
    description:
      "At each observation date, records the best-performing asset and removes it from the basket. Correlation risk dominates: as correlation rises, diversification benefit vanishes. Requires C-Delta hedging and Correlation Δ management.",
  },
};

const EXOTIC_NAMES = Object.keys(EXOTICS);

// ── Learning Hub Data ─────────────────────────────────────────────────────────

const RESOURCES = {
  Books: [
    { title: 'Options, Futures, and Other Derivatives', author: 'John Hull', difficulty: 'Intermediate', description: 'The definitive textbook on derivatives pricing and risk management.' },
    { title: 'Stochastic Calculus for Finance I & II', author: 'Steven Shreve', difficulty: 'Advanced', description: 'Rigorous mathematical treatment of continuous-time finance.' },
    { title: 'The Concepts and Practice of Mathematical Finance', author: 'Mark Joshi', difficulty: 'Advanced', description: 'Practical guide to pricing exotic options and structured products.' },
    { title: 'Quantitative Risk Management', author: 'McNeil, Frey & Embrechts', difficulty: 'Advanced', description: 'Comprehensive treatment of financial risk from a quantitative perspective.' },
    { title: 'Python for Finance', author: 'Yves Hilpisch', difficulty: 'Beginner', description: 'Hands-on guide to financial analysis and algorithmic trading with Python.' },
  ],
  Papers: [
    { title: 'The Pricing of Options and Corporate Liabilities', author: 'Black & Scholes (1973)', difficulty: 'Advanced', description: 'The foundational paper on option pricing theory.' },
    { title: 'Portfolio Selection', author: 'Markowitz (1952)', difficulty: 'Intermediate', description: 'Introduction of modern portfolio theory and mean-variance optimization.' },
    { title: 'Capital Asset Prices', author: 'Sharpe (1964)', difficulty: 'Intermediate', description: 'The Capital Asset Pricing Model (CAPM) for equilibrium asset pricing.' },
    { title: 'Attention Is All You Need', author: 'Vaswani et al. (2017)', difficulty: 'Advanced', description: 'Transformer architecture now applied to financial time series and NLP.' },
  ],
  'Online Courses': [
    { title: 'Financial Engineering & Risk Management', author: 'Columbia (Coursera)', difficulty: 'Intermediate', description: 'Comprehensive introduction to financial engineering concepts.' },
    { title: 'Machine Learning for Trading', author: 'Georgia Tech (Udacity)', difficulty: 'Intermediate', description: 'Applying ML algorithms to financial markets and trading strategies.' },
    { title: 'Quantitative Finance with Python', author: 'WorldQuant University', difficulty: 'Beginner', description: 'Free program covering quantitative finance fundamentals.' },
  ],
  Tools: [
    { title: 'QuantLib', author: 'Open Source', difficulty: 'Advanced', description: 'C++ library for quantitative finance: pricing, risk, and analytics.' },
    { title: 'Zipline / Backtrader', author: 'Open Source', difficulty: 'Intermediate', description: 'Python frameworks for algorithmic trading backtesting.' },
    { title: 'Bloomberg Terminal', author: 'Bloomberg LP', difficulty: 'Intermediate', description: 'Industry-standard platform for financial data and analytics.' },
    { title: 'Jupyter / Quarto', author: 'Open Source', difficulty: 'Beginner', description: 'Interactive notebook environments for financial research and analysis.' },
  ],
}

const diffVariant = (d: string): 'up' | 'warning' | 'down' => {
  if (d === 'Beginner') return 'up'
  if (d === 'Intermediate') return 'warning'
  return 'down'
}

const categoryColors: Record<string, string> = {
  Books: '#6366F1',
  Papers: '#00D9FF',
  'Online Courses': '#10B981',
  Tools: '#D4AF37',
}

// ── Page Tabs ─────────────────────────────────────────────────────────────────

const PAGE_TABS = ["Quantum Academy", "Learning Hub"];

// ── Sub-components ────────────────────────────────────────────────────────────

const QA_TABS = [
  "BSM Foundations",
  "Greeks Library",
  "Numerical Methods",
  "Exotic Mechanics",
];

function QuantumAcademyContent() {
  const [qaTab, setQaTab] = useState(0);
  const [selectedGreek, setSelectedGreek] = useState(GREEK_NAMES[0]);
  const [selectedExotic, setSelectedExotic] = useState(EXOTIC_NAMES[0]);

  return (
    <div>
      <p style={{ color: "#94A3B8", marginBottom: 20, fontSize: 14 }}>
        Mathematical foundations of pricing, risk and structuring models
      </p>

      {/* QA Tab bar */}
      <div
        style={{
          display: "flex",
          gap: 2,
          marginBottom: 16,
          borderBottom: "1px solid rgba(51,65,85,0.4)",
        }}
      >
        {QA_TABS.map((t, i) => (
          <button
            key={t}
            onClick={() => setQaTab(i)}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              padding: "8px 16px",
              fontSize: 13,
              color: qaTab === i ? "#6366F1" : "#94A3B8",
              borderBottom: `2px solid ${qaTab === i ? "#6366F1" : "transparent"}`,
              fontFamily: "Inter, sans-serif",
              fontWeight: qaTab === i ? 600 : 400,
              marginBottom: -1,
              transition: "color 0.15s",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* ── QA Tab 0: BSM Foundations ── */}
      {qaTab === 0 && (
        <Card title="Black-Scholes-Merton Framework">
          <SectionTitle>The BSM PDE</SectionTitle>
          <Formula src="∂V/∂t  +  (r - q)·S · ∂V/∂S  +  ½·σ²·S² · ∂²V/∂S²  -  r·V  =  0" />
          <p style={{ color: "#94A3B8", fontSize: 13, marginBottom: 4 }}>
            Under the risk-neutral measure Q, the underlying follows the SDE:
          </p>
          <Formula src="dSₜ  =  (r - q) · Sₜ dt  +  σ · Sₜ · dWₜᴾ" />

          <SectionTitle>Closed-Form Solution — European Call</SectionTitle>
          <Formula src="C  =  S · e^{-qT} · N(d₁)  -  K · e^{-rT} · N(d₂)" />
          <Formula
            src={`d₁ = [ ln(S/K) + (r - q + ½σ²)T ] / (σ√T)\nd₂ = d₁ - σ√T`}
          />

          <SectionTitle>Model Assumptions vs Reality</SectionTitle>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: 6,
              marginTop: 4,
            }}
          >
            {(
              [
                [
                  "Constant volatility",
                  "Reality: Implied vol varies with strike (smile/skew) → SABR, Heston, SVI",
                ],
                [
                  "No jumps",
                  "Reality: Overnight gaps & earnings → Merton Jump-Diffusion, Variance Gamma",
                ],
                [
                  "Continuous hedging",
                  "Reality: Discrete rebalancing → residual Gamma P&L accumulates",
                ],
                [
                  "Log-normal returns",
                  "Reality: Fat tails (excess kurtosis ≈ 4-6) → Lévy processes",
                ],
                [
                  "No transaction costs",
                  "Reality: Bid-ask spreads → Deep Hedging (Reinforcement Learning)",
                ],
              ] as [string, string][]
            ).map(([assumption, reality]) => (
              <details key={assumption} style={{ marginBottom: 2 }}>
                <summary
                  style={{
                    cursor: "pointer",
                    padding: "6px 10px",
                    background: "rgba(99,102,241,0.08)",
                    borderRadius: 5,
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 12,
                    color: "#A5B4FC",
                    listStyle: "none",
                    userSelect: "none",
                  }}
                >
                  ⚠ {assumption}
                </summary>
                <div
                  style={{
                    padding: "8px 10px",
                    fontSize: 13,
                    color: "#94A3B8",
                  }}
                >
                  {reality}
                </div>
              </details>
            ))}
          </div>
        </Card>
      )}

      {/* ── QA Tab 1: Greeks Library ── */}
      {qaTab === 1 && (
        <Card
          title="Greeks Reference Library"
          subtitle="Select a Greek to see its formula, interpretation and quant insight"
        >
          {/* Greek selector chips */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              marginBottom: 20,
            }}
          >
            {GREEK_NAMES.map((g) => (
              <button
                key={g}
                onClick={() => setSelectedGreek(g)}
                style={{
                  background:
                    selectedGreek === g
                      ? "rgba(99,102,241,0.2)"
                      : "rgba(51,65,85,0.2)",
                  border: `1px solid ${selectedGreek === g ? "rgba(99,102,241,0.6)" : "rgba(51,65,85,0.4)"}`,
                  borderRadius: 20,
                  padding: "5px 14px",
                  fontSize: 12,
                  color: selectedGreek === g ? "#A5B4FC" : "#94A3B8",
                  cursor: "pointer",
                  fontFamily: "JetBrains Mono, monospace",
                  transition: "all 0.15s",
                }}
              >
                {g}
              </button>
            ))}
          </div>

          {/* Greek detail */}
          {(() => {
            const g = GREEKS[selectedGreek];
            return (
              <div>
                <SectionTitle>Formula</SectionTitle>
                <Formula src={g.formula} />
                <SectionTitle>Interpretation</SectionTitle>
                <InfoBox>{g.interpretation}</InfoBox>
                <SectionTitle>Quant Insight</SectionTitle>
                <InfoBox>
                  <span style={{ color: "#6366F1", fontWeight: 600 }}>◆ </span>
                  {g.insight}
                </InfoBox>
              </div>
            );
          })()}
        </Card>
      )}

      {/* ── QA Tab 2: Numerical Methods ── */}
      {qaTab === 2 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Monte Carlo */}
          <Card title="Monte Carlo Simulation">
            <SectionTitle>Pricing Formula</SectionTitle>
            <Formula src="C₀  ≈  e^{-rT} · (1/N) · Σᵢ  max(Sₜ⁽ⁱ⁾ - K, 0)" />
            <SectionTitle>Standard Error</SectionTitle>
            <Formula src="SE = σ̂ / √N   ⟹   halving SE requires 4× more paths" />
            <SectionTitle>Antithetic Variates (used in Ravinala)</SectionTitle>
            <Formula src="Ĉ_AV = [f(Z) + f(-Z)] / 2   ⟹   Var[Ĉ_AV] ≤ Var[Ĉ]" />
            <InfoBox>
              Antithetic variates simulate both Z and −Z, exploiting negative
              correlation to reduce variance at no extra computational cost. For
              standard BSM, variance reduction ≈ 50%. Most effective when payoff
              is approximately linear in log-spot.
            </InfoBox>
          </Card>

          {/* Crank-Nicolson */}
          <Card title="Finite Differences — Crank-Nicolson">
            <SectionTitle>
              Scheme (2nd-order, unconditionally stable)
            </SectionTitle>
            <Formula src="(V^{n+1}_i - V^n_i) / Δt  =  ½ · (𝓛V^n_i + 𝓛V^{n+1}_i)" />
            <InfoBox>
              𝓛 is the Black-Scholes spatial operator acting at grid point i:
              𝓛Vᵢ = (r-q)·Sᵢ · ∂V/∂S + ½σ²·Sᵢ² · ∂²V/∂S² − r·V
              <br />
              <br />
              Crank-Nicolson is the average of explicit (n) and implicit (n+1)
              steps. This makes it 2nd-order in both Δt and ΔS, and
              unconditionally stable — no CFL condition required. Ideal for
              American option pricing with early exercise boundary.
            </InfoBox>
          </Card>

          {/* SABR */}
          <Card title="SABR Stochastic Volatility">
            <SectionTitle>Model SDEs</SectionTitle>
            <Formula src="dF  =  σ · Fᵝ · dW₁\ndσ  =  ν · σ · dW₂\n⟨dW₁, dW₂⟩  =  ρ · dt" />
            <div style={{ overflowX: "auto", marginTop: 12 }}>
              <table
                style={{
                  borderCollapse: "collapse",
                  width: "100%",
                  fontSize: 13,
                }}
              >
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(51,65,85,0.4)" }}>
                    {["Parameter", "Symbol", "Role"].map((h) => (
                      <th
                        key={h}
                        style={{
                          padding: "8px 12px",
                          textAlign: "left",
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
                  {(
                    [
                      [
                        "Vol level",
                        "α",
                        "Controls overall height of the vol smile",
                      ],
                      [
                        "Backbone",
                        "β",
                        "0 = normal model, 1 = log-normal model",
                      ],
                      [
                        "Skew",
                        "ρ",
                        "Negative for equity (puts more expensive than calls)",
                      ],
                      [
                        "Smile curvature",
                        "ν",
                        "Vol-of-vol — controls width of the smile",
                      ],
                    ] as [string, string, string][]
                  ).map(([param, sym, role]) => (
                    <tr
                      key={sym}
                      style={{ borderBottom: "1px solid rgba(51,65,85,0.2)" }}
                    >
                      <td style={{ padding: "8px 12px", color: "#F1F5F9" }}>
                        {param}
                      </td>
                      <td
                        style={{
                          padding: "8px 12px",
                          fontFamily: "JetBrains Mono, monospace",
                          color: "#A5B4FC",
                        }}
                      >
                        {sym}
                      </td>
                      <td style={{ padding: "8px 12px", color: "#94A3B8" }}>
                        {role}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* ── QA Tab 3: Exotic Mechanics ── */}
      {qaTab === 3 && (
        <Card
          title="Exotic Payoff Mechanics"
          subtitle="Select an exotic to see its payoff formula and risk properties"
        >
          {/* Exotic selector chips */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              marginBottom: 20,
            }}
          >
            {EXOTIC_NAMES.map((e) => (
              <button
                key={e}
                onClick={() => setSelectedExotic(e)}
                style={{
                  background:
                    selectedExotic === e
                      ? "rgba(168,85,247,0.2)"
                      : "rgba(51,65,85,0.2)",
                  border: `1px solid ${selectedExotic === e ? "rgba(168,85,247,0.5)" : "rgba(51,65,85,0.4)"}`,
                  borderRadius: 20,
                  padding: "5px 14px",
                  fontSize: 12,
                  color: selectedExotic === e ? "#D8B4FE" : "#94A3B8",
                  cursor: "pointer",
                  fontFamily: "JetBrains Mono, monospace",
                  transition: "all 0.15s",
                }}
              >
                {e}
              </button>
            ))}
          </div>

          {(() => {
            const ex = EXOTICS[selectedExotic];
            return (
              <div>
                <SectionTitle>Payoff</SectionTitle>
                <pre
                  style={{
                    background: "rgba(168,85,247,0.07)",
                    border: "1px solid rgba(168,85,247,0.2)",
                    borderRadius: 6,
                    padding: "10px 16px",
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 12,
                    color: "#D8B4FE",
                    margin: "8px 0",
                    whiteSpace: "pre-wrap",
                    lineHeight: 1.7,
                  }}
                >
                  {ex.payoff}
                </pre>
                <SectionTitle>Risk Properties</SectionTitle>
                <InfoBox>{ex.description}</InfoBox>
              </div>
            );
          })()}
        </Card>
      )}
    </div>
  );
}

function LearningHubContent() {
  const { data: healthData } = useHealth()

  return (
    <div>
      {!healthData && (
        <div style={{ background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 8, padding: '8px 16px', marginBottom: 16, fontSize: 13, color: '#F59E0B', fontFamily: 'Inter, sans-serif' }}>
          Backend unreachable — displaying demo data
        </div>
      )}
      <p style={{ color: '#94A3B8', marginBottom: 24, fontSize: 14 }}>
        Curated learning resources for quantitative finance
        {healthData && (
          <span style={{ marginLeft: 12, fontSize: 12, color: healthData.status === 'ok' ? '#10B981' : '#EF4444' }}>
            · Backend {healthData.status === 'ok' ? 'connected' : 'disconnected'}
          </span>
        )}
      </p>

      {Object.entries(RESOURCES).map(([category, items]) => (
        <div key={category} style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: categoryColors[category], marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            {category}
            <span style={{ fontSize: 12, color: '#64748B', fontWeight: 400 }}>({items.length})</span>
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
            {items.map(item => (
              <Card key={item.title}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                  <h3 style={{ fontSize: 14, fontWeight: 600, color: '#F1F5F9', flex: 1, marginRight: 8 }}>{item.title}</h3>
                  <Badge variant={diffVariant(item.difficulty)}>{item.difficulty}</Badge>
                </div>
                <div style={{ fontSize: 12, color: categoryColors[category], marginBottom: 6 }}>{item.author}</div>
                <p style={{ color: '#94A3B8', fontSize: 12, lineHeight: 1.5 }}>{item.description}</p>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function QuantumAcademy() {
  const [activeTab, setActiveTab] = useState(PAGE_TABS[0]);

  return (
    <div style={{ color: "#F1F5F9" }}>
      <h1
        style={{
          fontFamily: "JetBrains Mono, monospace",
          fontSize: 24,
          marginBottom: 16,
          color: "#6366F1",
        }}
      >
        Quantum Academy
      </h1>

      <Tabs tabs={PAGE_TABS} active={activeTab} onChange={setActiveTab} />

      <div style={{ marginTop: 20 }}>
        {activeTab === "Quantum Academy" && <QuantumAcademyContent />}
        {activeTab === "Learning Hub" && <LearningHubContent />}
      </div>
    </div>
  );
}
