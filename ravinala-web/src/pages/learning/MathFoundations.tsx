import { useState } from "react";
import { PageHeader, Tabs } from "../../components/ui";
import LearningHub from "./LearningHub";
import ProbabilityBible from "./ProbabilityBible";
import QuantumAcademy from "./QuantumAcademy";

const TAB_LIST = [
  "📚 Educational Hub",
  "⚛️ Quantum Academy",
  "🎲 Probability Bible",
] as const;
type Tab = (typeof TAB_LIST)[number];

const TAB_COMPONENTS: Record<Tab, React.FC> = {
  "📚 Educational Hub": LearningHub,
  "⚛️ Quantum Academy": QuantumAcademy,
  "🎲 Probability Bible": ProbabilityBible,
};

export default function MathFoundations() {
  const [activeTab, setActiveTab] = useState<Tab>("📚 Educational Hub");
  const ActiveComponent = TAB_COMPONENTS[activeTab];

  return (
    <div>
      <PageHeader
        icon="📐"
        title="Mathematical Foundations"
        subtitle="Educational hub, quantum academy & probability bible"
        badge="LEARNING"
        badgeColor="#14B8A6"
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
