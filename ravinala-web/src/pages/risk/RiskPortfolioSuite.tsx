import { useState } from "react";
import { PageHeader, Tabs } from "../../components/ui";
import PnLAttribution from "../portfolio/PnLAttribution";
import PositionBook from "../portfolio/PositionBook";
import Backtesting from "./Backtesting";
import Hedging from "./Hedging";
import RiskManagement from "./RiskManagement";

const TAB_LIST = [
  "Risk Analytics",
  "Position Book",
  "Hedging",
  "Backtesting",
  "P&L Attribution",
] as const;
type Tab = (typeof TAB_LIST)[number];

const TAB_COMPONENTS: Record<Tab, React.FC> = {
  "Risk Analytics": RiskManagement,
  "Position Book": PositionBook,
  Hedging: Hedging,
  Backtesting: Backtesting,
  "P&L Attribution": PnLAttribution,
};

export default function RiskPortfolioSuite() {
  const [activeTab, setActiveTab] = useState<Tab>("Risk Analytics");
  const ActiveComponent = TAB_COMPONENTS[activeTab];

  return (
    <div>
      <PageHeader
        icon="🛡️"
        title="Risk & Portfolio Suite"
        subtitle="Risk analytics, positions, hedging, backtesting & P&L attribution"
        badge="RISK"
        badgeColor="#F59E0B"
      />
      <Tabs
        tabs={[...TAB_LIST]}
        active={activeTab}
        onChange={(t) => setActiveTab(t as Tab)}
      />
      <div style={{ marginTop: 24 }}>
        <ActiveComponent />
      </div>
    </div>
  );
}
