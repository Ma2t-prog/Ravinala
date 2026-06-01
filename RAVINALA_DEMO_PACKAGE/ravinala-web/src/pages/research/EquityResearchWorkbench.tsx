import { useState } from "react";
import { PageHeader, Tabs } from "../../components/ui";
import CompanyAnalyzer from "./CompanyAnalyzer";
import EnterpriseValuations from "./EnterpriseValuations";

/**
 * Equity Research Workbench — Fusion of EnterpriseValuations + CompanyAnalyzer
 * EnterpriseValuations already contains 8 internal tabs (Overview, DCF, Monte Carlo DCF,
 * Multiples, Financials, Health & Risk, Ownership, Sensitivity).
 * CompanyAnalyzer is a stub — its intended content is absorbed into the valuations tabs.
 *
 * We expose 2 top-level tabs to keep the fusion pattern consistent while
 * preserving all the rich sub-tab content from EnterpriseValuations.
 */

const TAB_LIST = ["Valuations & DCF", "Company Analyzer"] as const;
type Tab = (typeof TAB_LIST)[number];

const TAB_COMPONENTS: Record<Tab, React.FC> = {
  "Valuations & DCF": EnterpriseValuations,
  "Company Analyzer": CompanyAnalyzer,
};

export default function EquityResearchWorkbench() {
  const [activeTab, setActiveTab] = useState<Tab>("Valuations & DCF");
  const ActiveComponent = TAB_COMPONENTS[activeTab];

  return (
    <div>
      <PageHeader
        icon="🔬"
        title="Equity Research Workbench"
        subtitle="DCF valuation, Monte Carlo, multiples, financials, health & ownership"
        badge="RESEARCH"
        badgeColor="#3B82F6"
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
