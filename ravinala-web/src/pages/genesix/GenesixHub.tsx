import { useState } from "react";
import { Card, PageHeader } from "../../components/ui";
import AdvancedAnalysis from "./AdvancedAnalysis";
import DataLayer from "./DataLayer";
import IntelligenceHub from "./IntelligenceHub";
import MLEngine from "./MLEngine";
import PortfolioMonitor from "./PortfolioMonitor";
import PortfolioOmega from "./PortfolioOmega";
import RiskEngine from "./RiskEngine";

const SECTIONS = [
  "Portfolio Allocator",
  "Portfolio Monitor",
  "Risk Engine",
  "ML Engine",
  "Market Intelligence",
  "Advanced Analysis",
  "Data Layer",
  "Intelligence Center",
] as const;

type Section = (typeof SECTIONS)[number];

const SECTION_COMPONENTS: Record<Section, React.FC> = {
  "Portfolio Allocator": PortfolioOmega,
  "Portfolio Monitor": PortfolioMonitor,
  "Risk Engine": RiskEngine,
  "ML Engine": MLEngine,
  "Market Intelligence": IntelligenceHub,
  "Advanced Analysis": AdvancedAnalysis,
  "Data Layer": DataLayer,
  "Intelligence Center": IntelligenceHub,
};

const SECTION_ICONS: Record<Section, string> = {
  "Portfolio Allocator": "📊",
  "Portfolio Monitor": "👁️",
  "Risk Engine": "🛡️",
  "ML Engine": "🤖",
  "Market Intelligence": "📡",
  "Advanced Analysis": "🔬",
  "Data Layer": "💾",
  "Intelligence Center": "🧠",
};

export default function GenesixHub() {
  const [activeSection, setActiveSection] = useState<Section>(
    "Portfolio Allocator",
  );
  const ActiveComponent = SECTION_COMPONENTS[activeSection];

  return (
    <div>
      <PageHeader
        icon="Ω"
        title="GenesiX Hub"
        subtitle="Unified command center — portfolio, risk, ML, intelligence & data"
        badge="GENESIX Ω"
        badgeColor="#D4AF37"
      />

      {/* Section selector */}
      <Card>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <label
            style={{
              fontSize: 12,
              fontWeight: 700,
              color: "#D4AF37",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              fontFamily: "JetBrains Mono, monospace",
              whiteSpace: "nowrap",
            }}
          >
            Module
          </label>
          <select
            value={activeSection}
            onChange={(e) => setActiveSection(e.target.value as Section)}
            style={{
              flex: 1,
              background: "rgba(51,65,85,0.2)",
              border: "1px solid rgba(51,65,85,0.3)",
              borderRadius: 6,
              color: "#F1F5F9",
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 13,
              padding: "8px 12px",
              cursor: "pointer",
              outline: "none",
            }}
          >
            {SECTIONS.map((s) => (
              <option key={s} value={s}>
                {SECTION_ICONS[s]} {s}
              </option>
            ))}
          </select>
        </div>
      </Card>

      {/* Active section content */}
      <div style={{ marginTop: 24 }}>
        <ActiveComponent />
      </div>
    </div>
  );
}
