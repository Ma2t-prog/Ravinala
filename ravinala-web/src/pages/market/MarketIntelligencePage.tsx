import { useState } from "react";
import { PageHeader, Tabs } from "../../components/ui";
import AltData from "./AltData";
import LiveMarket from "./LiveMarket";
import MacroAnalysis from "./MacroAnalysis";
import MarketNews from "./MarketNews";

const TAB_LIST = [
  "Live Market",
  "Market News",
  "Macro Analysis",
  "Alternative Data",
] as const;
type Tab = (typeof TAB_LIST)[number];

const TAB_COMPONENTS: Record<Tab, React.FC> = {
  "Live Market": LiveMarket,
  "Market News": MarketNews,
  "Macro Analysis": MacroAnalysis,
  "Alternative Data": AltData,
};

export default function MarketIntelligencePage() {
  const [activeTab, setActiveTab] = useState<Tab>("Live Market");
  const ActiveComponent = TAB_COMPONENTS[activeTab];

  return (
    <div>
      <PageHeader
        icon="📡"
        title="Market Intelligence"
        subtitle="Live data, macro analysis, news & alternative data — unified view"
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
