import { useState } from "react";
import { PageHeader, Tabs } from "../../components/ui";
import ScenarioMatrix from "../portfolio/ScenarioMatrix";
import StrategyLab from "../portfolio/StrategyLab";
import GreeksVolLab from "../risk/GreeksVolLab";
import PricingCenter from "./PricingCenter";

const TAB_LIST = [
  "Pricing Center",
  "Strategy Lab",
  "Greeks & Sensitivity",
  "Scenario Matrix",
] as const;
type Tab = (typeof TAB_LIST)[number];

const TAB_COMPONENTS: Record<Tab, React.FC> = {
  "Pricing Center": PricingCenter,
  "Strategy Lab": StrategyLab,
  "Greeks & Sensitivity": GreeksVolLab,
  "Scenario Matrix": ScenarioMatrix,
};

export default function OptionsAnalytics() {
  const [activeTab, setActiveTab] = useState<Tab>("Pricing Center");
  const ActiveComponent = TAB_COMPONENTS[activeTab];

  return (
    <div>
      <PageHeader
        icon="📊"
        title="Options Analytics"
        subtitle="Pricing, strategies, Greeks sensitivity & scenario analysis"
        badge="DERIVATIVES"
        badgeColor="#8B5CF6"
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
