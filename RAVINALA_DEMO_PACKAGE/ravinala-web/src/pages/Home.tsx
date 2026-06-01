import {
  Atom,
  BarChart3,
  BookOpen,
  FlaskConical,
  GraduationCap,
  Layers,
  Scale,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useHealth, useIndices, useSnapshot } from "../hooks/useMarketData";

// ─── Types ────────────────────────────────────────────────────────────────────

interface KpiItem {
  value: string;
  label: string;
}

interface ModuleCard {
  section: string;
  sectionColor: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  href: string;
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const KPI_ITEMS: KpiItem[] = [
  { value: "50+", label: "Modules" },
  { value: "15+", label: "Pays fiscaux" },
  { value: "500+", label: "Instruments" },
  { value: "12", label: "Modèles quant" },
  { value: "3", label: "Moteurs ML" },
  { value: "Real-time", label: "Market data" },
];

interface DetailedCard {
  section: string;
  sectionColor: string;
  title: string;
  description: string;
  href: string;
}

const ICON_SIZE = 18;

// ──────────────────────────────────────────────────────────────────────────────
// DETAILED PAGE CARDS — organized by section (matches Streamlit)
// ──────────────────────────────────────────────────────────────────────────────

const DETAILED_CARDS: DetailedCard[] = [
  // ── MARKET INTELLIGENCE
  {
    section: "MARKET INTELLIGENCE",
    sectionColor: "#00D4FF",
    title: "Live Market",
    description: "Prix, vol, Greeks, technicals en temps réel",
    href: "/market/live",
  },
  {
    section: "MARKET INTELLIGENCE",
    sectionColor: "#00D4FF",
    title: "Market News",
    description: "Flux d'actualité avec accès aux articles",
    href: "/market/news",
  },
  {
    section: "MARKET INTELLIGENCE",
    sectionColor: "#00D4FF",
    title: "Macro Analysis",
    description: "Indicateurs macro, taux, devises, commodities",
    href: "/market/macro",
  },
  {
    section: "MARKET INTELLIGENCE",
    sectionColor: "#00D4FF",
    title: "Alt Data",
    description: "Sentiment, options flow, dark pools",
    href: "/market/alt-data",
  },

  // ── DERIVATIVES & STRUCTURING
  {
    section: "DERIVATIVES & STRUCTURING",
    sectionColor: "#A855F7",
    title: "Pricing Center",
    description: "Black-Scholes, Binomial, Monte Carlo, FDM",
    href: "/derivatives/pricing",
  },
  {
    section: "DERIVATIVES & STRUCTURING",
    sectionColor: "#A855F7",
    title: "Structuring Suite",
    description: "Produits structurés sur mesure",
    href: "/derivatives/structuring",
  },
  {
    section: "DERIVATIVES & STRUCTURING",
    sectionColor: "#A855F7",
    title: "Advanced Exotics",
    description: "Barrier, Asian, Lookback, Rainbow, Cliquets",
    href: "/derivatives/exotics",
  },
  {
    section: "DERIVATIVES & STRUCTURING",
    sectionColor: "#A855F7",
    title: "Vol Calibration",
    description: "SABR, SVI, Heston, Dupire, GARCH, HAR-RV",
    href: "/derivatives/vol",
  },

  // ── RISK & QUANT
  {
    section: "RISK & QUANT",
    sectionColor: "#F59E0B",
    title: "Risk Management",
    description: "VaR, CVaR, stress tests, drawdown analysis",
    href: "/risk/management",
  },
  {
    section: "RISK & QUANT",
    sectionColor: "#F59E0B",
    title: "Greeks & Sensitivity",
    description: "Delta, Gamma, Vega, surface de sensibilité",
    href: "/risk/greeks",
  },
  {
    section: "RISK & QUANT",
    sectionColor: "#F59E0B",
    title: "Backtesting",
    description: "Stratégies historiques avec transaction costs",
    href: "/risk/backtesting",
  },
  {
    section: "RISK & QUANT",
    sectionColor: "#F59E0B",
    title: "ML Pricing",
    description: "Neural nets, XGBoost, random forests",
    href: "/risk/ml-pricing",
  },

  // ── PORTFOLIO DESK
  {
    section: "PORTFOLIO DESK",
    sectionColor: "#10B981",
    title: "Portfolio Optimizer",
    description: "Mean-variance, Black-Litterman, HRP",
    href: "/portfolio/optimizer",
  },
  {
    section: "PORTFOLIO DESK",
    sectionColor: "#10B981",
    title: "Strategy Lab",
    description: "Backtesting de stratégies multi-assets",
    href: "/portfolio/strategy",
  },
  {
    section: "PORTFOLIO DESK",
    sectionColor: "#10B981",
    title: "Scenario Matrix",
    description: "Stress tests, what-if, Monte Carlo paths",
    href: "/portfolio/scenarios",
  },
  {
    section: "PORTFOLIO DESK",
    sectionColor: "#10B981",
    title: "TAX LAB Ω",
    description: "Optimisation fiscale multi-juridictionnelle",
    href: "/tax",
  },

  // ── RESEARCH
  {
    section: "RESEARCH",
    sectionColor: "#3B82F6",
    title: "Enterprise Val.",
    description: "DCF, comparables, LBO, SOTP",
    href: "/research/valuations",
  },
  {
    section: "RESEARCH",
    sectionColor: "#3B82F6",
    title: "Equity Research",
    description: "Fondamentaux, scoring, momentum",
    href: "/research/equity",
  },
  {
    section: "RESEARCH",
    sectionColor: "#3B82F6",
    title: "Fixed Income",
    description: "Duration, convexité, courbes, spreads",
    href: "/research/fixed-income",
  },
  {
    section: "RESEARCH",
    sectionColor: "#3B82F6",
    title: "ETF Explorer",
    description: "Screening, analyse, comparaison",
    href: "/research/etf",
  },

  // ── GENESIX Ω SUITE
  {
    section: "GENESIX Ω SUITE",
    sectionColor: "#D4AF37",
    title: "Portfolio Omega",
    description: "Vue d'ensemble du portefeuille institutionnel",
    href: "/genesix/portfolio",
  },
  {
    section: "GENESIX Ω SUITE",
    sectionColor: "#D4AF37",
    title: "Risk Engine",
    description: "Moteur de risque temps réel",
    href: "/genesix/risk",
  },
  {
    section: "GENESIX Ω SUITE",
    sectionColor: "#D4AF37",
    title: "ML Engine",
    description: "Prédictions et signaux machine learning",
    href: "/genesix/ml",
  },
  {
    section: "GENESIX Ω SUITE",
    sectionColor: "#D4AF37",
    title: "Signal Intelligence",
    description: "Détection de signaux et alertes",
    href: "/genesix/signals",
  },
];

// Legacy summary cards (for now, kept as fallback)
const _MODULE_CARDS: ModuleCard[] = [
  {
    section: "MARKET INTEL",
    sectionColor: "#3B82F6",
    icon: <TrendingUp size={ICON_SIZE} />,
    title: "Live Market & Intelligence",
    description:
      "Real-time market data, macro analysis, news sentiment across 30+ global indices",
    href: "/market/live",
  },
  {
    section: "DERIVATIVES",
    sectionColor: "#F59E0B",
    icon: <Layers size={ICON_SIZE} />,
    title: "Pricing & Structuring",
    description:
      "Black-Scholes, Monte Carlo, exotic products, Greeks, vol calibration",
    href: "/derivatives/pricing",
  },
  {
    section: "RESEARCH",
    sectionColor: "#10B981",
    icon: <FlaskConical size={ICON_SIZE} />,
    title: "Deep Research",
    description:
      "Equity research, fixed income, company analysis, ETF explorer",
    href: "/research/equity",
  },
  {
    section: "RISK & QUANT",
    sectionColor: "#EF4444",
    icon: <ShieldAlert size={ICON_SIZE} />,
    title: "Risk Analytics",
    description: "VaR, CVaR, stress testing, backtesting, ML pricing models",
    href: "/risk/management",
  },
  {
    section: "PORTFOLIO DESK",
    sectionColor: "#8B5CF6",
    icon: <BarChart3 size={ICON_SIZE} />,
    title: "Portfolio Management",
    description: "Optimizer, strategy lab, scenario matrix, P&L attribution",
    href: "/portfolio/optimizer",
  },
  {
    section: "GENESIX Ω",
    sectionColor: "#D4AF37",
    icon: <Atom size={ICON_SIZE} />,
    title: "Institutional Risk Suite",
    description:
      "Universe explorer, advanced screener, ML engine, signal intelligence",
    href: "/genesix/universe",
  },
  {
    section: "COMPLIANCE",
    sectionColor: "#00D9FF",
    icon: <Scale size={ICON_SIZE} />,
    title: "ESG & Regulatory",
    description: "ESG scoring, regulatory capital, compliance reporting",
    href: "/compliance/esg",
  },
  {
    section: "LEARNING",
    sectionColor: "#6366F1",
    icon: <GraduationCap size={ICON_SIZE} />,
    title: "Quantum Academy",
    description: "Options theory, probability, quantitative finance education",
    href: "/learning/academy",
  },
  {
    section: "TRADING DESK",
    sectionColor: "#F97316",
    icon: <BookOpen size={ICON_SIZE} />,
    title: "Trade Management",
    description: "Trade book, position tracking, P&L, admin panel",
    href: "/trading/tradebook",
  },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function KpiCard({ value, label }: KpiItem) {
  return (
    <div
      style={{
        backgroundColor: "#131823",
        border: "1px solid rgba(51,65,85,0.3)",
        borderRadius: 8,
        padding: "12px 16px",
        textAlign: "center",
        flex: "0 1 120px",
        transition: "border-color 0.2s",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor =
          "rgba(212,175,55,0.3)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLDivElement).style.borderColor =
          "rgba(51,65,85,0.3)";
      }}
    >
      <div
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 18,
          fontWeight: 700,
          color: "#D4AF37",
          lineHeight: 1.2,
          marginBottom: 2,
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          color: "#94A3B8",
        }}
      >
        {label}
      </div>
    </div>
  );
}

function DetailedCardItem({
  section,
  sectionColor,
  title,
  description,
  href,
}: DetailedCard) {
  const [hovered, setHovered] = useState(false);

  return (
    <Link
      to={href}
      style={{ textDecoration: "none" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div
        style={{
          backgroundColor:
            "linear-gradient(135deg, rgba(19,24,35,0.7), rgba(15,18,24,0.8))",
          background:
            "linear-gradient(135deg, rgba(19,24,35,0.7), rgba(15,18,24,0.8))",
          border: `1px solid ${hovered ? sectionColor + "40" : "rgba(51,65,85,0.35)"}`,
          borderTop: `1px solid rgba(192,192,192,${hovered ? "0.15" : "0.10"})`,
          borderRadius: 10,
          padding: "18px 20px",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          gap: 6,
          transform: hovered ? "translateY(-1px)" : "translateY(0)",
          transition: "all 160ms ease, border-color 160ms ease",
          cursor: "pointer",
          boxShadow: hovered ? `0 4px 20px ${sectionColor}0f` : "none",
          boxSizing: "border-box",
        }}
      >
        {/* Section label */}
        <div
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
            color: sectionColor + "80",
            marginBottom: 2,
          }}
        >
          {section}
        </div>

        {/* Title */}
        <div
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 14,
            fontWeight: 600,
            color: "#E0E0E0",
            lineHeight: 1.35,
            letterSpacing: "0.01em",
          }}
        >
          {title}
        </div>

        {/* Description */}
        <div
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 11.5,
            color: "rgba(148,163,184,0.60)",
            lineHeight: 1.5,
            flexGrow: 1,
          }}
        >
          {description}
        </div>
      </div>
    </Link>
  );
}

function _ModuleCardItem({
  section,
  sectionColor,
  icon,
  title,
  description,
  href,
}: ModuleCard) {
  const [hovered, setHovered] = useState(false);

  return (
    <Link
      to={href}
      style={{ textDecoration: "none" }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div
        style={{
          backgroundColor: "#131823",
          border: `1px solid ${hovered ? sectionColor + "33" : "rgba(51,65,85,0.3)"}`,
          borderRadius: 8,
          padding: "20px 20px 18px",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          gap: 10,
          transform: hovered ? "translateY(-2px)" : "translateY(0)",
          transition: "transform 0.18s ease, border-color 0.18s ease",
          cursor: "pointer",
          boxSizing: "border-box",
        }}
      >
        {/* Section label + icon */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              color: sectionColor,
              display: "flex",
              alignItems: "center",
            }}
          >
            {icon}
          </span>
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              fontWeight: 600,
              color: sectionColor,
            }}
          >
            {section}
          </span>
        </div>

        {/* Title */}
        <div
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 13,
            fontWeight: 600,
            color: "#F1F5F9",
            lineHeight: 1.35,
          }}
        >
          {title}
        </div>

        {/* Description */}
        <div
          style={{
            fontFamily: "'Inter', sans-serif",
            fontSize: 11.5,
            color: "#94A3B8",
            lineHeight: 1.55,
            flexGrow: 1,
          }}
        >
          {description}
        </div>

        {/* Arrow indicator */}
        <div
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            color: hovered ? sectionColor : "rgba(148,163,184,0.4)",
            transition: "color 0.18s ease",
            letterSpacing: "0.08em",
          }}
        >
          OPEN →
        </div>
      </div>
    </Link>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function Home() {
  const { data: snapshotData } = useSnapshot();
  const { data: indicesData } = useIndices();
  const { data: healthData } = useHealth();
  const [now, setNow] = useState<Date>(new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const formattedDate = now.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const formattedTime = now.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return (
    <div
      style={{
        minHeight: "100%",
        backgroundColor: "#0A0E1A",
        padding: "40px 32px 60px",
        boxSizing: "border-box",
      }}
    >
      {!snapshotData && !indicesData && (
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

      {/* ── Live Market Summary ── */}
      {(snapshotData || indicesData || healthData) && (
        <section style={{ marginBottom: 24 }}>
          {/* Backend status */}
          {healthData && (
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 12,
                padding: "4px 12px",
                borderRadius: 6,
                backgroundColor:
                  (healthData.status === "ok" || healthData.status === "healthy")
                    ? "rgba(16,185,129,0.1)"
                    : "rgba(239,68,68,0.1)",
                border: `1px solid ${(healthData.status === "ok" || healthData.status === "healthy") ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
              }}
            >
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  display: "inline-block",
                  backgroundColor:
                    (healthData.status === "ok" || healthData.status === "healthy") ? "#10B981" : "#EF4444",
                }}
              />
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 11,
                  color: (healthData.status === "ok" || healthData.status === "healthy") ? "#10B981" : "#EF4444",
                }}
              >
                Backend {(healthData.status === "ok" || healthData.status === "healthy") ? "connected" : "degraded"}
                {healthData.redis_connected ? " · Redis OK" : ""}
              </span>
            </div>
          )}

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {/* Indices summary */}
            {indicesData &&
              Object.values(indicesData)
                .flat()
                .slice(0, 4)
                .map((idx) => (
                  <div
                    key={idx.symbol}
                    style={{
                      backgroundColor: "#131823",
                      border: "1px solid rgba(51,65,85,0.3)",
                      borderRadius: 8,
                      padding: "10px 16px",
                      flex: "1 1 160px",
                      maxWidth: 220,
                    }}
                  >
                    <div
                      style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10,
                        color: "#94A3B8",
                        letterSpacing: "0.08em",
                        marginBottom: 2,
                      }}
                    >
                      {idx.symbol}
                    </div>
                    <div
                      style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 16,
                        fontWeight: 700,
                        color: "#F1F5F9",
                      }}
                    >
                      {idx.price?.toLocaleString(undefined, {
                        maximumFractionDigits: 0,
                      }) ?? "—"}
                    </div>
                    <div
                      style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 11,
                        color:
                          (idx.change?.percent ?? 0) >= 0
                            ? "#10B981"
                            : "#EF4444",
                      }}
                    >
                      {(idx.change?.percent ?? 0) >= 0 ? "+" : ""}
                      {(idx.change?.percent ?? 0).toFixed(2)}%
                    </div>
                  </div>
                ))}

            {/* FX rates */}
            {snapshotData?.fx?.pairs?.slice(0, 3).map((pair) => (
              <div
                key={pair.symbol}
                style={{
                  backgroundColor: "#131823",
                  border: "1px solid rgba(51,65,85,0.3)",
                  borderRadius: 8,
                  padding: "10px 16px",
                  flex: "1 1 140px",
                  maxWidth: 180,
                }}
              >
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10,
                    color: "#94A3B8",
                    letterSpacing: "0.08em",
                    marginBottom: 2,
                  }}
                >
                  {pair.symbol}
                </div>
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 16,
                    fontWeight: 700,
                    color: "#F1F5F9",
                  }}
                >
                  {pair.rate.toFixed(4)}
                </div>
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11,
                    color:
                      (pair.change?.percent ?? 0) >= 0 ? "#10B981" : "#EF4444",
                  }}
                >
                  {(pair.change?.percent ?? 0) >= 0 ? "+" : ""}
                  {(pair.change?.percent ?? 0).toFixed(2)}%
                </div>
              </div>
            ))}

            {/* Bond yields */}
            {snapshotData?.bonds?.bonds?.slice(0, 2).map((bond) => (
              <div
                key={bond.country_code}
                style={{
                  backgroundColor: "#131823",
                  border: "1px solid rgba(51,65,85,0.3)",
                  borderRadius: 8,
                  padding: "10px 16px",
                  flex: "1 1 140px",
                  maxWidth: 180,
                }}
              >
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10,
                    color: "#94A3B8",
                    letterSpacing: "0.08em",
                    marginBottom: 2,
                  }}
                >
                  {bond.country} 10Y
                </div>
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 16,
                    fontWeight: 700,
                    color: "#D4AF37",
                  }}
                >
                  {bond.yield_10y?.toFixed(3) ?? "—"}%
                </div>
                {bond.spread_vs_bund_bp != null && (
                  <div
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11,
                      color: "#94A3B8",
                    }}
                  >
                    +{bond.spread_vs_bund_bp}bp vs Bund
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Hero ── */}
      <section
        style={{
          textAlign: "center",
          marginBottom: 48,
          paddingBottom: 40,
          borderBottom: "1px solid rgba(51,65,85,0.25)",
        }}
      >
        {/* Title */}
        <h1
          style={{
            fontFamily: "'Orbitron', sans-serif",
            fontSize: "clamp(28px, 5vw, 48px)",
            fontWeight: 900,
            letterSpacing: "0.12em",
            margin: "0 0 4px",
            background:
              "linear-gradient(135deg, #E8E8E8 0%, #D4AF37 50%, #C0C0C0 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            lineHeight: 1.1,
          }}
        >
          RAVINALA
        </h1>

        {/* Omega */}
        <div
          style={{
            fontFamily: "'Orbitron', sans-serif",
            fontSize: "clamp(18px, 2.5vw, 28px)",
            color: "#D4AF37",
            margin: "0 0 18px",
            fontWeight: 700,
            letterSpacing: "0.2em",
          }}
        >
          Ω
        </div>

        {/* Tagline */}
        <p
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 12,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: "rgba(148,163,184,0.6)",
            margin: "0 0 24px",
          }}
        >
          Cross-Asset Quantum Structuring Lab
        </p>

        {/* Gold divider */}
        <div
          style={{
            width: 160,
            height: 1,
            margin: "0 auto 20px",
            background:
              "linear-gradient(90deg, transparent 0%, #D4AF37 50%, transparent 100%)",
          }}
        />

        {/* Timestamp */}
        <div
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: "rgba(148,163,184,0.45)",
            letterSpacing: "0.1em",
          }}
        >
          {formattedDate}&nbsp;&nbsp;·&nbsp;&nbsp;{formattedTime} UTC
        </div>
      </section>

      {/* ── KPI row ── */}
      <section style={{ marginBottom: 48 }}>
        <div
          style={{
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          {KPI_ITEMS.map((item) => (
            <KpiCard key={item.label} {...item} />
          ))}
        </div>
      </section>

      {/* ── Detailed module grid (organized by section) ── */}
      <section style={{ marginBottom: 56 }}>
        {/* Group cards by section */}
        {Array.from(
          new Map(DETAILED_CARDS.map((c) => [c.section, c])).keys(),
        ).map((section) => {
          const sectionCards = DETAILED_CARDS.filter(
            (c) => c.section === section,
          );
          const _sectionColor = sectionCards[0]?.sectionColor || "#D4AF37";

          return (
            <div key={section} style={{ marginBottom: 28 }}>
              <div
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 9,
                  fontWeight: 700,
                  letterSpacing: "0.18em",
                  textTransform: "uppercase",
                  color: "rgba(192,192,192,0.40)",
                  paddingBottom: 10,
                  borderBottom: "1px solid rgba(51,65,85,0.20)",
                  marginBottom: 14,
                }}
              >
                {section}
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(4, 1fr)",
                  gap: 14,
                }}
              >
                {sectionCards.map((card) => (
                  <DetailedCardItem
                    key={`${card.section}-${card.title}`}
                    {...card}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </section>

      {/* ── Footer ── */}
      <footer
        style={{
          textAlign: "center",
          paddingTop: 24,
          borderTop: "1px solid rgba(51,65,85,0.2)",
        }}
      >
        <p
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            letterSpacing: "0.1em",
            color: "rgba(148,163,184,0.35)",
            margin: 0,
          }}
        >
          RAVINALA by TSIVAHINY Matthias &nbsp;·&nbsp; Quantum Structuring Lab
          &nbsp;·&nbsp; v2.1
        </p>
      </footer>

      {/* Responsive grid style */}
      <style>{`
        @media (max-width: 900px) {
          .module-grid {
            grid-template-columns: repeat(2, 1fr) !important;
          }
        }
        @media (max-width: 560px) {
          .module-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}
