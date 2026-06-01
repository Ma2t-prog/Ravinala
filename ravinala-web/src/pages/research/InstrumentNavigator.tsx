import { useState } from "react";
import { PageHeader, Tabs } from "../../components/ui";
import UniverseScreener from "../genesix/UniverseScreener";
import UniverseSearch from "../genesix/UniverseSearch";
import AssetExplorer from "./AssetExplorer";
import ETFExplorer from "./ETFExplorer";

const TAB_LIST = ["Search", "Screener", "Asset Classes", "ETF Focus"] as const;
type Tab = (typeof TAB_LIST)[number];

const TAB_COMPONENTS: Record<Tab, React.FC> = {
  Search: UniverseSearch,
  Screener: UniverseScreener,
  "Asset Classes": AssetExplorer,
  "ETF Focus": ETFExplorer,
};

export default function InstrumentNavigator() {
  const [activeTab, setActiveTab] = useState<Tab>("Search");
  const ActiveComponent = TAB_COMPONENTS[activeTab];

  return (
    <div>
      <PageHeader
        icon="🔎"
        title="Instrument Navigator"
        subtitle="Search, screen, explore asset classes & ETFs"
        badge="MARKET"
        badgeColor="#00D4FF"
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
