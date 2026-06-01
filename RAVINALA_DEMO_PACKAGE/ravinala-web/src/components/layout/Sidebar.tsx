import {
  Archive,
  Atom,
  BarChart,
  BarChart2,
  BookMarked,
  BookOpen,
  Bot,
  Boxes,
  Brain,
  Building2,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  FileText,
  Filter,
  FlaskConical,
  GraduationCap,
  History,
  Home,
  Layers,
  Leaf,
  LineChart,
  Microscope,
  Network,
  Receipt,
  Scale,
  ScanSearch,
  Settings,
  ShieldAlert,
  Signal,
  Sliders,
  Target,
  TrendingUp,
  User,
  Wrench,
} from "lucide-react";
import { useCallback, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface NavItem {
  label: string;
  path: string;
  icon: React.ReactNode;
}

interface Section {
  id: string;
  title: string;
  color: string; // accent colour for tick + active state
  activeColor: string; // text colour when active
  items: NavItem[];
}

/* ------------------------------------------------------------------ */
/*  Section colour map                                                 */
/* ------------------------------------------------------------------ */

const sections: Section[] = [
  {
    id: "market",
    title: "Market",
    color: "#00D4FF",
    activeColor: "#00D4FF",
    items: [
      {
        label: "Market Intelligence",
        path: "/market",
        icon: <BarChart2 size={14} />,
      },
      {
        label: "Instrument Navigator",
        path: "/market/instruments",
        icon: <ScanSearch size={14} />,
      },
      {
        label: "Instrument Detail",
        path: "/market/intelligence",
        icon: <Brain size={14} />,
      },
      {
        label: "Financial Analysis",
        path: "/market/financial-analysis",
        icon: <LineChart size={14} />,
      },
    ],
  },
  {
    id: "derivatives",
    title: "Derivatives & Structuring",
    color: "#8B5CF6",
    activeColor: "#A78BFA",
    items: [
      {
        label: "Options Analytics",
        path: "/derivatives/options",
        icon: <TrendingUp size={14} />,
      },
      {
        label: "Structuring Suite",
        path: "/derivatives/structuring",
        icon: <Layers size={14} />,
      },
      {
        label: "Custom Product",
        path: "/derivatives/custom",
        icon: <Wrench size={14} />,
      },
      {
        label: "Advanced Exotics",
        path: "/derivatives/exotics",
        icon: <FlaskConical size={14} />,
      },
      {
        label: "Vol Calibration",
        path: "/risk/vol-calibration",
        icon: <Sliders size={14} />,
      },
      {
        label: "Museum of Exotics",
        path: "/derivatives/museum",
        icon: <Archive size={14} />,
      },
      {
        label: "The Sandbox",
        path: "/derivatives/sandbox",
        icon: <Boxes size={14} />,
      },
    ],
  },
  {
    id: "risk",
    title: "Risk & Portfolio",
    color: "#F59E0B",
    activeColor: "#FCD34D",
    items: [
      {
        label: "Risk & Portfolio Suite",
        path: "/risk/suite",
        icon: <ShieldAlert size={14} />,
      },
      {
        label: "Portfolio Optimizer",
        path: "/portfolio/optimizer",
        icon: <Target size={14} />,
      },
      {
        label: "ML Pricing",
        path: "/risk/ml-pricing",
        icon: <Bot size={14} />,
      },
    ],
  },
  {
    id: "research",
    title: "Research & Education",
    color: "#3B82F6",
    activeColor: "#60A5FA",
    items: [
      {
        label: "Equity Research Workbench",
        path: "/research/workbench",
        icon: <Building2 size={14} />,
      },
      {
        label: "Equity Research",
        path: "/research/equity",
        icon: <BarChart size={14} />,
      },
      {
        label: "Fixed Income",
        path: "/research/fixed-income",
        icon: <BookOpen size={14} />,
      },
      {
        label: "Mathematical Foundations",
        path: "/learning/foundations",
        icon: <GraduationCap size={14} />,
      },
    ],
  },
  {
    id: "tax",
    title: "Tax Lab Ω",
    color: "#F59E0B",
    activeColor: "#FCD34D",
    items: [
      {
        label: "TAX LAB Ω — Full Suite",
        path: "/tax",
        icon: <Receipt size={14} />,
      },
    ],
  },
  {
    id: "genesix",
    title: "GENESIX Ω",
    color: "#D4AF37",
    activeColor: "#F5E6A3",
    items: [
      {
        label: "GenesiX Hub",
        path: "/genesix/hub",
        icon: <Network size={14} />,
      },
      {
        label: "Signal Intelligence",
        path: "/genesix/signals",
        icon: <Signal size={14} />,
      },
      {
        label: "Advanced Screener",
        path: "/genesix/screener",
        icon: <Filter size={14} />,
      },
      {
        label: "Instrument Analysis",
        path: "/genesix/instrument",
        icon: <Microscope size={14} />,
      },
      {
        label: "Backtesting",
        path: "/genesix/backtest",
        icon: <History size={14} />,
      },
      {
        label: "Physics Lab",
        path: "/genesix/physics",
        icon: <Atom size={14} />,
      },
    ],
  },
  {
    id: "compliance",
    title: "Compliance",
    color: "#6366F1",
    activeColor: "#818CF8",
    items: [
      {
        label: "ESG & Green Lab",
        path: "/compliance/esg",
        icon: <Leaf size={14} />,
      },
      {
        label: "Regulatory Capital",
        path: "/compliance/regulatory",
        icon: <Scale size={14} />,
      },
      {
        label: "Report Generator",
        path: "/compliance/reports",
        icon: <FileText size={14} />,
      },
      {
        label: "Legal & Compliance",
        path: "/compliance/legal",
        icon: <BookMarked size={14} />,
      },
    ],
  },
  {
    id: "trading",
    title: "Trading Desk",
    color: "#F43F5E",
    activeColor: "#FB7185",
    items: [
      {
        label: "Trade Book",
        path: "/trading/tradebook",
        icon: <ClipboardList size={14} />,
      },
      {
        label: "Admin Panel",
        path: "/trading/admin",
        icon: <Settings size={14} />,
      },
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Helper: which section does a path belong to?                       */
/* ------------------------------------------------------------------ */

/* sectionForPath removed — unused */

/* ------------------------------------------------------------------ */
/*  Sidebar component                                                  */
/* ------------------------------------------------------------------ */

export default function Sidebar() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [hoveredSection, setHoveredSection] = useState<string | null>(null);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const toggle = useCallback(
    (id: string) => setCollapsed((prev) => ({ ...prev, [id]: !prev[id] })),
    [],
  );

  const isActivePath = (path: string) => location.pathname === path;

  return (
    <>
      {/* Shimmer keyframes + scrollbar styles */}
      <style>{`
        @keyframes rvn-logo-shimmer {
          0%   { background-position: 100% center; }
          100% { background-position: -150% center; }
        }
        .rvn-sidebar::-webkit-scrollbar {
          width: 3px;
        }
        .rvn-sidebar::-webkit-scrollbar-track {
          background: transparent;
        }
        .rvn-sidebar::-webkit-scrollbar-thumb {
          background: rgba(192,192,192,0.12);
          border-radius: 3px;
        }
        .rvn-sidebar {
          scrollbar-width: thin;
          scrollbar-color: rgba(192,192,192,0.12) transparent;
        }
      `}</style>

      <aside
        className="rvn-sidebar"
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: 280,
          height: "100vh",
          background:
            "linear-gradient(180deg, #080C14 0%, #0A0E18 55%, #08090E 100%)",
          borderRight: "1px solid rgba(51,65,85,0.45)",
          boxShadow:
            "4px 0 32px rgba(0,0,0,0.55), 1px 0 0 rgba(212,175,55,0.04)",
          display: "flex",
          flexDirection: "column",
          zIndex: 100,
          overflowY: "auto",
          overflowX: "hidden",
        }}
      >
        {/* ── Logo brand strip ─────────────────────────────────── */}
        <NavLink to="/" style={{ textDecoration: "none", flexShrink: 0 }}>
          <div
            style={{
              padding: "24px 16px 6px 16px",
              borderBottom: "1px solid rgba(212,175,55,0.14)",
              backgroundColor: "rgba(212,175,55,0.04)",
            }}
          >
            <div
              style={{
                fontFamily: "Orbitron, sans-serif",
                fontSize: 16,
                fontWeight: 800,
                letterSpacing: "0.22em",
                textTransform: "uppercase",
                background: `linear-gradient(105deg,
                  #9CA3AF 0%, #C0C0C0 15%, #E8E8E8 28%,
                  #D4AF37 40%, #F5E6A3 50%, #D4AF37 60%,
                  #E8E8E8 72%, #C0C0C0 85%, #9CA3AF 100%)`,
                backgroundSize: "250% auto",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
                animation: "rvn-logo-shimmer 5s linear infinite",
                lineHeight: 1.2,
              }}
            >
              GENESIX{"  "}
              {"\u03A9"}
            </div>
          </div>
        </NavLink>

        {/* ── Tagline ──────────────────────────────────────────── */}
        <div
          style={{
            padding: "5px 16px 12px 16px",
            borderBottom: "1px solid rgba(212,175,55,0.10)",
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 8,
              fontWeight: 500,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "rgba(100,116,139,0.50)",
              lineHeight: 1.4,
            }}
          >
            Quantum Trading Intelligence
          </div>
        </div>

        {/* ── Home link ────────────────────────────────────────── */}
        <div style={{ padding: "8px 8px 2px 8px", flexShrink: 0 }}>
          <NavLink to="/" end style={{ textDecoration: "none" }}>
            {({ isActive: active }) => (
              <SidebarItem
                icon={<Home size={14} />}
                label="Home"
                active={active}
                hovered={hoveredItem === "/__home"}
                sectionColor="#00D4FF"
                activeColor="#00D4FF"
                isGenesix={false}
                onMouseEnter={() => setHoveredItem("/__home")}
                onMouseLeave={() => setHoveredItem(null)}
              />
            )}
          </NavLink>
        </div>

        {/* ── Nav sections ─────────────────────────────────────── */}
        <nav style={{ flex: 1, padding: "2px 8px 8px" }}>
          {sections.map((section) => {
            const isOpen = !collapsed[section.id];
            const hasActive = section.items.some((i) => isActivePath(i.path));
            const isGenesix = section.id === "genesix";
            const sectionHovered = hoveredSection === section.id;

            return (
              <div key={section.id}>
                {/* GENESIX separator */}
                {isGenesix && (
                  <div
                    style={{
                      borderTop: "1px solid rgba(212,175,55,0.16)",
                      marginTop: 4,
                    }}
                  />
                )}

                {/* Section header */}
                <button
                  onClick={() => toggle(section.id)}
                  onMouseEnter={() => setHoveredSection(section.id)}
                  onMouseLeave={() => setHoveredSection(null)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    width: "100%",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: "13px 10px 4px 12px",
                    color: sectionHovered
                      ? "rgba(192,192,192,0.90)"
                      : isGenesix
                        ? "rgba(212,175,55,0.70)"
                        : "rgba(71,85,105,0.85)",
                    fontSize: isGenesix ? 9 : 8.5,
                    fontWeight: 700,
                    letterSpacing: isGenesix ? "0.20em" : "0.18em",
                    textTransform: "uppercase",
                    fontFamily: "JetBrains Mono, monospace",
                    transition: "color 0.15s ease",
                    textShadow:
                      isGenesix && sectionHovered
                        ? "0 0 10px rgba(212,175,55,0.45)"
                        : "none",
                  }}
                >
                  <span
                    style={{ display: "flex", alignItems: "center", gap: 6 }}
                  >
                    {/* Decorative accent tick */}
                    <span
                      style={{
                        display: "inline-block",
                        width: sectionHovered ? 18 : 13,
                        height: 1,
                        backgroundColor: hasActive
                          ? section.color
                          : section.color,
                        opacity: hasActive ? 1 : 0.55,
                        transition: "width 0.2s ease, opacity 0.2s ease",
                        flexShrink: 0,
                      }}
                    />
                    {section.title}
                  </span>
                  {isOpen ? (
                    <ChevronDown size={10} style={{ opacity: 0.5 }} />
                  ) : (
                    <ChevronRight size={10} style={{ opacity: 0.5 }} />
                  )}
                </button>

                {/* Items */}
                {isOpen && (
                  <div style={{ paddingBottom: 2 }}>
                    {section.items.map((item) => {
                      const active = isActivePath(item.path);
                      return (
                        <NavLink
                          key={item.path}
                          to={item.path}
                          style={{ textDecoration: "none" }}
                        >
                          <SidebarItem
                            icon={item.icon}
                            label={item.label}
                            active={active}
                            hovered={hoveredItem === item.path}
                            sectionColor={section.color}
                            activeColor={section.activeColor}
                            isGenesix={isGenesix}
                            onMouseEnter={() => setHoveredItem(item.path)}
                            onMouseLeave={() => setHoveredItem(null)}
                          />
                        </NavLink>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* ── Bottom user area ─────────────────────────────────── */}
        <div
          style={{
            borderTop: "1px solid rgba(51,65,85,0.45)",
            padding: "10px 16px",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            gap: 10,
            backgroundColor: "rgba(0,0,0,0.15)",
          }}
        >
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              backgroundColor: "rgba(15,23,42,0.8)",
              border: "1px solid rgba(212,175,55,0.18)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <User size={14} color="rgba(212,175,55,0.55)" />
          </div>
          <div>
            <div
              style={{
                fontSize: 12,
                fontWeight: 500,
                color: "#E2E8F0",
                lineHeight: 1.2,
                fontFamily: "DM Sans, sans-serif",
              }}
            >
              Interview Demo
            </div>
            <div
              style={{
                fontSize: 10,
                color: "rgba(148,163,184,0.60)",
                lineHeight: 1.2,
                fontFamily: "JetBrains Mono, monospace",
                letterSpacing: "0.06em",
              }}
            >
              Trading Assistant
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Individual nav item                                                */
/* ------------------------------------------------------------------ */

interface SidebarItemProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  hovered: boolean;
  sectionColor: string;
  activeColor: string;
  isGenesix: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

function SidebarItem({
  icon,
  label,
  active,
  hovered,
  sectionColor,
  activeColor,
  isGenesix,
  onMouseEnter,
  onMouseLeave,
}: SidebarItemProps) {
  const showHover = hovered && !active;

  return (
    <div
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: active
          ? "4px 8px 4px 14px"
          : showHover
            ? "4px 8px 4px 17px"
            : "4px 8px 4px 14px",
        borderRadius: 4,
        fontSize: 13,
        fontFamily: "DM Sans, sans-serif",
        fontWeight: active ? (isGenesix ? 600 : 500) : 400,
        letterSpacing: "0.013em",
        lineHeight: "1.45",
        color: active
          ? activeColor
          : showHover
            ? "#E8E8E8"
            : "rgba(148,163,184,0.72)",
        background: active
          ? `linear-gradient(90deg, ${hexToRgba(sectionColor, 0.1)}, ${hexToRgba(sectionColor, 0.03)} 55%, transparent)`
          : showHover
            ? "rgba(255,255,255,0.022)"
            : "transparent",
        borderLeft: active
          ? `2px solid ${sectionColor}`
          : showHover
            ? "2px solid rgba(192,192,192,0.25)"
            : "2px solid transparent",
        cursor: "pointer",
        transition: "all 0.12s ease",
        textShadow:
          active && isGenesix ? "0 0 12px rgba(212,175,55,0.25)" : "none",
      }}
    >
      <span
        style={{
          flexShrink: 0,
          opacity: active ? 1 : 0.6,
          display: "flex",
          alignItems: "center",
        }}
      >
        {icon}
      </span>
      <span>{label}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Utility: hex colour to rgba string                                 */
/* ------------------------------------------------------------------ */

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
