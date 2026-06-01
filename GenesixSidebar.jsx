/**
 * GenesixSidebar.jsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Premium institutional trading platform sidebar navigation
 * GENESIX Ω · Cross-Asset Quantum Structuring Lab
 *
 * Stack : React · Framer Motion · Lucide React
 * Fonts : Orbitron (logo) · DM Sans (items) · JetBrains Mono (headers)
 *
 * Usage:
 *   import GenesixSidebar from './GenesixSidebar';
 *   <GenesixSidebar activeItem="Live Market" onNavigate={(label) => …} />
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity, Newspaper, Globe, Database, Brain, BarChart3,
  DollarSign, Layers, Wrench, Sparkles, Landmark, Box,
  Building2, TrendingUp, Lock, Compass, Search, PieChart,
  Shield, Sigma, SlidersHorizontal, History, Cpu, Umbrella,
  Target, FlaskConical, Grid3x3, GitBranch, BookOpen,
  Orbit, Flame, BrainCircuit, Microscope, Eye, Monitor,
  Radio, HardDrive, Atom,
  Leaf, Scale, FileText, Gavel,
  GraduationCap, Lightbulb,
  Receipt, Settings,
  ChevronDown, Menu, X, Home,
} from 'lucide-react';

// ─── DESIGN TOKENS ────────────────────────────────────────────────────────────
const C = {
  bg:        '#080C14',
  bgDeep:    '#050810',
  bgSurface: '#0D1120',
  border:    'rgba(51,65,85,0.45)',
  borderH:   'rgba(212,175,55,0.25)',
  t1:        '#E8E8E8',
  t2:        '#94A3B8',
  t3:        '#3D4F66',
  t4:        '#1E293B',
  cyan:      '#00D4FF',
  cyanDim:   'rgba(0,212,255,0.07)',
  cyanGlow:  'rgba(0,212,255,0.20)',
  gold:      '#D4AF37',
  goldL:     '#F5E6A3',
  goldDim:   'rgba(212,175,55,0.09)',
  goldGlow:  'rgba(212,175,55,0.22)',
  silver:    '#C0C0C0',
  silverL:   '#E8E8E8',
};

// ─── PER-SECTION ACCENT PALETTE ───────────────────────────────────────────────
const SECTION_THEME = {
  'MARKET INTEL':   { color: '#00D4FF', dim: 'rgba(0,212,255,0.07)',   glow: 'rgba(0,212,255,0.18)'   },
  'DERIVATIVES':    { color: '#8B5CF6', dim: 'rgba(139,92,246,0.07)',  glow: 'rgba(139,92,246,0.18)'  },
  'RESEARCH':       { color: '#3B82F6', dim: 'rgba(59,130,246,0.07)',  glow: 'rgba(59,130,246,0.18)'  },
  'RISK & QUANT':   { color: '#F59E0B', dim: 'rgba(245,158,11,0.07)',  glow: 'rgba(245,158,11,0.18)'  },
  'PORTFOLIO DESK': { color: '#10B981', dim: 'rgba(16,185,129,0.07)',  glow: 'rgba(16,185,129,0.18)'  },
  'GENESIX Ω':      { color: '#D4AF37', dim: 'rgba(212,175,55,0.09)',  glow: 'rgba(212,175,55,0.28)'  },
  'COMPLIANCE':     { color: '#6366F1', dim: 'rgba(99,102,241,0.07)',  glow: 'rgba(99,102,241,0.18)'  },
  'LEARNING':       { color: '#14B8A6', dim: 'rgba(20,184,166,0.07)',  glow: 'rgba(20,184,166,0.18)'  },
  'TRADING DESK':   { color: '#F43F5E', dim: 'rgba(244,63,94,0.07)',   glow: 'rgba(244,63,94,0.18)'   },
};

// ─── MENU STRUCTURE ───────────────────────────────────────────────────────────
const MENU = [
  {
    section: 'MARKET INTEL',
    items: [
      { label: 'Live Market',        icon: Activity           },
      { label: 'Market News',        icon: Newspaper          },
      { label: 'Macro Analysis',     icon: Globe              },
      { label: 'Alt Data',           icon: Database           },
      { label: 'Intelligence',       icon: Brain              },
      { label: 'Financial Analysis', icon: BarChart3          },
    ],
  },
  {
    section: 'DERIVATIVES',
    items: [
      { label: 'Pricing Center',     icon: DollarSign         },
      { label: 'Structuring Suite',  icon: Layers             },
      { label: 'Custom Product',     icon: Wrench             },
      { label: 'Advanced Exotics',   icon: Sparkles           },
      { label: 'Museum of Exotics',  icon: Landmark           },
      { label: 'The Sandbox',        icon: Box                },
    ],
  },
  {
    section: 'RESEARCH',
    items: [
      { label: 'Enterprise Val.',    icon: Building2          },
      { label: 'Equity Research',    icon: TrendingUp         },
      { label: 'Fixed Income',       icon: Lock               },
      { label: 'Asset Explorer',     icon: Compass            },
      { label: 'Company Analyzer',   icon: Search             },
      { label: 'ETF Explorer',       icon: PieChart           },
    ],
  },
  {
    section: 'RISK & QUANT',
    items: [
      { label: 'Risk Management',      icon: Shield             },
      { label: 'Greeks & Sensitivity', icon: Sigma              },
      { label: 'Vol Calibration',      icon: SlidersHorizontal  },
      { label: 'Backtesting',          icon: History            },
      { label: 'ML Pricing',           icon: Cpu                },
      { label: 'Hedging',              icon: Umbrella           },
    ],
  },
  {
    section: 'PORTFOLIO DESK',
    items: [
      { label: 'Portfolio Optimizer', icon: Target             },
      { label: 'Strategy Lab',        icon: FlaskConical       },
      { label: 'Scenario Matrix',     icon: Grid3x3            },
      { label: 'P&L Attribution',     icon: GitBranch          },
      { label: 'Position Book',       icon: BookOpen           },
    ],
  },
  {
    section: 'GENESIX Ω',
    items: [
      { label: 'Portfolio Omega',     icon: Orbit              },
      { label: 'Risk Engine',         icon: Flame              },
      { label: 'ML Engine',           icon: BrainCircuit       },
      { label: 'Advanced Analysis',   icon: Microscope         },
      { label: 'Market Intelligence', icon: Eye                },
      { label: 'Portfolio Monitor',   icon: Monitor            },
      { label: 'Signal Intelligence', icon: Radio              },
      { label: 'Data Layer',          icon: HardDrive          },
      { label: 'Physics Lab',         icon: Atom               },
    ],
  },
  {
    section: 'COMPLIANCE',
    items: [
      { label: 'ESG & Green Lab',     icon: Leaf               },
      { label: 'Regulatory Capital',  icon: Scale              },
      { label: 'Report Generator',    icon: FileText           },
      { label: 'Legal & Compliance',  icon: Gavel              },
    ],
  },
  {
    section: 'LEARNING',
    items: [
      { label: 'Quantum Academy',     icon: GraduationCap      },
      { label: 'Probability Bible',   icon: BookOpen           },
      { label: 'Learning Hub',        icon: Lightbulb          },
    ],
  },
  {
    section: 'TRADING DESK',
    items: [
      { label: 'Trade Book',          icon: Receipt            },
      { label: 'Admin Panel',         icon: Settings           },
    ],
  },
];

// ─── GLOBAL CSS (injected once via <style>) ───────────────────────────────────
const GLOBAL_CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,450;9..40,500;9..40,600&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

  /* ── Custom Scrollbar ── */
  .gnx-scroll {
    scrollbar-width: thin;
    scrollbar-color: rgba(192,192,192,0.12) transparent;
  }
  .gnx-scroll::-webkit-scrollbar { width: 3px; }
  .gnx-scroll::-webkit-scrollbar-track { background: transparent; }
  .gnx-scroll::-webkit-scrollbar-thumb {
    background: rgba(192,192,192,0.12);
    border-radius: 999px;
    transition: background 200ms;
  }
  .gnx-scroll::-webkit-scrollbar-thumb:hover {
    background: rgba(212,175,55,0.30);
  }

  /* ── Logo shimmer sweep ── */
  @keyframes gnx-shimmer {
    0%   { background-position: -300% center; }
    100% { background-position:  300% center; }
  }
  .gnx-logo-text {
    background: linear-gradient(
      105deg,
      #9CA3AF  0%,
      #C0C0C0 15%,
      #E8E8E8 28%,
      #D4AF37 40%,
      #F5E6A3 50%,
      #D4AF37 60%,
      #E8E8E8 72%,
      #C0C0C0 85%,
      #9CA3AF 100%
    );
    background-size: 250% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gnx-shimmer 5s linear infinite;
    font-family: 'Orbitron', monospace;
    font-weight: 800;
    letter-spacing: 0.20em;
  }

  /* ── Live dot pulse ── */
  @keyframes gnx-pulse {
    0%, 100% { opacity: 1;   box-shadow: 0 0 6px 1px rgba(16,185,129,0.7); }
    50%       { opacity: 0.5; box-shadow: 0 0 2px 0   rgba(16,185,129,0.2); }
  }
  .gnx-live-dot {
    animation: gnx-pulse 2.2s ease-in-out infinite;
  }

  /* ── Omega glow pulse (subtle) ── */
  @keyframes gnx-omega-glow {
    0%, 100% { text-shadow: 0 0 20px rgba(212,175,55,0.35), 0 0 48px rgba(212,175,55,0.10); }
    50%       { text-shadow: 0 0 32px rgba(212,175,55,0.55), 0 0 64px rgba(212,175,55,0.18); }
  }
  .gnx-omega {
    animation: gnx-omega-glow 4s ease-in-out infinite;
  }

  /* ── Tooltip ── */
  .gnx-tooltip {
    position: absolute;
    left: calc(100% + 10px);
    top: 50%;
    transform: translateY(-50%);
    background: linear-gradient(135deg, #1A2035, #111827);
    border: 1px solid rgba(212,175,55,0.30);
    color: #E8E8E8;
    font-family: 'DM Sans', sans-serif;
    font-size: 12px;
    font-weight: 500;
    padding: 5px 11px;
    border-radius: 6px;
    white-space: nowrap;
    z-index: 99999;
    pointer-events: none;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.04);
    opacity: 0;
    animation: gnx-tooltip-in 0.15s 0.05s ease forwards;
  }
  @keyframes gnx-tooltip-in {
    from { opacity: 0; transform: translateY(-50%) translateX(-4px); }
    to   { opacity: 1; transform: translateY(-50%) translateX(0); }
  }
  .gnx-tooltip::before {
    content: '';
    position: absolute;
    right: 100%;
    top: 50%;
    transform: translateY(-50%);
    border: 5px solid transparent;
    border-right-color: rgba(212,175,55,0.30);
  }

  /* ── Icon slide on hover ── */
  .gnx-item-row:hover .gnx-icon-wrap {
    transform: translateX(2px);
  }
  .gnx-icon-wrap {
    transition: transform 180ms ease-out;
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  /* ── Toggle button ── */
  .gnx-toggle-btn {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(51,65,85,0.45);
    color: #3D4F66;
    border-radius: 6px;
    cursor: pointer;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: border-color 150ms ease, color 150ms ease, background 150ms ease;
    flex-shrink: 0;
  }
  .gnx-toggle-btn:hover {
    border-color: rgba(212,175,55,0.40);
    color: #D4AF37;
    background: rgba(212,175,55,0.06);
  }

  /* ── Section header ── */
  .gnx-section-hdr {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 10px 5px 12px;
    cursor: pointer;
    user-select: none;
    border-radius: 4px;
    transition: background 120ms ease;
  }
  .gnx-section-hdr:hover { background: rgba(255,255,255,0.018); }
`;

// ─── ANIMATION VARIANTS ───────────────────────────────────────────────────────
const staggerList = {
  show: { transition: { staggerChildren: 0.028, delayChildren: 0.06 } },
  hidden: {},
};
const itemIn = {
  hidden: { opacity: 0, x: -10 },
  show:   { opacity: 1, x: 0, transition: { duration: 0.22, ease: 'easeOut' } },
};
const sectionContent = {
  open:   { height: 'auto', opacity: 1,   transition: { duration: 0.22, ease: 'easeOut'  } },
  closed: { height: 0,      opacity: 0.4, transition: { duration: 0.18, ease: 'easeIn'   } },
};

// ─── HELPERS ──────────────────────────────────────────────────────────────────
/** Gradient separator div */
function Divider({ gold = false }) {
  return (
    <div style={{
      height: '1px',
      margin: '7px 10px',
      background: gold
        ? 'linear-gradient(90deg, transparent, rgba(212,175,55,0.28) 35%, rgba(212,175,55,0.28) 65%, transparent)'
        : 'linear-gradient(90deg, transparent, rgba(100,116,139,0.18) 35%, rgba(100,116,139,0.18) 65%, transparent)',
    }} />
  );
}

// ─── NAV ITEM ─────────────────────────────────────────────────────────────────
function NavItem({ item, sectionTheme, isActive, isCollapsed, onActivate }) {
  const [hovered, setHovered] = useState(false);
  const [showTip, setShowTip] = useState(false);
  const tipTimer = useRef(null);
  const Icon = item.icon;

  const isGenesix  = sectionTheme.color === C.gold;
  const accent     = sectionTheme.color;
  const activeBg   = isGenesix
    ? `linear-gradient(90deg, rgba(212,175,55,0.12), rgba(212,175,55,0.04) 55%, transparent)`
    : `linear-gradient(90deg, ${sectionTheme.dim}, rgba(0,0,0,0) 65%)`;

  const enter = useCallback(() => {
    setHovered(true);
    if (isCollapsed) tipTimer.current = setTimeout(() => setShowTip(true), 280);
  }, [isCollapsed]);
  const leave = useCallback(() => {
    setHovered(false);
    clearTimeout(tipTimer.current);
    setShowTip(false);
  }, []);

  return (
    <motion.div variants={itemIn} style={{ position: 'relative' }}>
      <div
        className="gnx-item-row"
        onMouseEnter={enter}
        onMouseLeave={leave}
        onClick={() => onActivate(item.label)}
        style={{
          display:        'flex',
          alignItems:     'center',
          gap:            '10px',
          padding:        isCollapsed ? '8px 0' : '5px 10px 5px 14px',
          justifyContent: isCollapsed ? 'center' : 'flex-start',
          borderRadius:   '4px',
          cursor:         'pointer',
          position:       'relative',
          overflow:       'hidden',
          transition:     'background 140ms ease, padding-left 140ms ease',
          background: isActive
            ? activeBg
            : hovered
            ? 'rgba(255,255,255,0.022)'
            : 'transparent',
          paddingLeft: !isCollapsed && hovered && !isActive ? '17px' : undefined,
        }}
      >
        {/* Left accent bar */}
        {!isCollapsed && (
          <div style={{
            position:  'absolute',
            left:      0,
            top:       '18%',
            bottom:    '18%',
            width:     '2px',
            borderRadius: '0 2px 2px 0',
            background: accent,
            opacity:   isActive ? 1 : hovered ? 0.40 : 0,
            transition: 'opacity 140ms ease',
            boxShadow: isActive ? `0 0 8px ${accent}70` : 'none',
          }} />
        )}

        {/* Icon */}
        <div className="gnx-icon-wrap">
          <Icon
            size={isCollapsed ? 18 : 16}
            style={{
              color: isActive
                ? accent
                : hovered
                ? C.silverL
                : C.t3,
              transition: 'color 140ms ease',
              filter: isActive ? `drop-shadow(0 0 5px ${accent}90)` : 'none',
            }}
          />
        </div>

        {/* Label */}
        {!isCollapsed && (
          <span style={{
            fontFamily:   "'DM Sans', sans-serif",
            fontSize:     '13px',
            fontWeight:   isActive ? 500 : 400,
            color: isActive
              ? (isGenesix ? C.goldL : '#D8E4F0')
              : hovered
              ? C.t1
              : C.t2,
            letterSpacing: '0.013em',
            transition:   'color 140ms ease',
            whiteSpace:   'nowrap',
            overflow:     'hidden',
            textOverflow: 'ellipsis',
            lineHeight:   1.45,
          }}>
            {item.label}
          </span>
        )}

        {/* Subtle highlight sweep on hover */}
        {hovered && !isActive && (
          <div style={{
            position:   'absolute',
            inset:      0,
            background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.012) 50%, transparent 100%)',
            pointerEvents: 'none',
          }} />
        )}
      </div>

      {/* Collapsed tooltip */}
      {isCollapsed && showTip && (
        <div className="gnx-tooltip">{item.label}</div>
      )}
    </motion.div>
  );
}

// ─── SECTION HEADER ───────────────────────────────────────────────────────────
function SectionHeader({ section, isOpen, onToggle, theme, isCollapsed }) {
  const [hovered, setHovered] = useState(false);
  const isGenesix = section === 'GENESIX Ω';

  if (isCollapsed) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 3px' }}>
        <div style={{
          width: '18px', height: '1px',
          background: theme.color, opacity: 0.38, borderRadius: '1px',
        }} />
      </div>
    );
  }

  return (
    <div
      className="gnx-section-hdr"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onToggle}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* Decorative accent tick */}
        <div style={{
          width:      hovered ? '18px' : '13px',
          height:     '1px',
          background: theme.color,
          opacity:    hovered ? 0.85 : 0.45,
          transition: 'width 200ms ease, opacity 200ms ease',
          flexShrink: 0,
          borderRadius: '1px',
        }} />

        {/* Section label */}
        <span style={{
          fontFamily:    "'JetBrains Mono', monospace",
          fontSize:      isGenesix ? '9.5px' : '8.5px',
          fontWeight:    700,
          letterSpacing: isGenesix ? '0.22em' : '0.17em',
          textTransform: 'uppercase',
          color: hovered
            ? theme.color
            : isGenesix
            ? 'rgba(212,175,55,0.65)'
            : 'rgba(71,85,105,0.85)',
          transition: 'color 150ms ease',
          textShadow: (hovered && isGenesix)
            ? `0 0 14px ${C.goldGlow}`
            : 'none',
        }}>
          {isGenesix ? (
            <>
              GENESIX{' '}
              <span style={{
                fontFamily: 'Georgia, serif',
                fontSize:   '11px',
                color:      hovered ? C.goldL : C.gold,
                textShadow: hovered
                  ? `0 0 16px ${C.goldGlow}`
                  : `0 0 8px rgba(212,175,55,0.25)`,
                transition: 'color 150ms ease, text-shadow 150ms ease',
              }}>Ω</span>
            </>
          ) : section}
        </span>
      </div>

      {/* Chevron — rotates when open */}
      <motion.div
        animate={{ rotate: isOpen ? 0 : -90 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
      >
        <ChevronDown
          size={11}
          style={{
            color: hovered ? theme.color : C.t3,
            transition: 'color 150ms ease',
          }}
        />
      </motion.div>
    </div>
  );
}

// ─── LOGO BLOCK ───────────────────────────────────────────────────────────────
function LogoBlock({ isCollapsed }) {
  if (isCollapsed) {
    return (
      <div style={{
        padding: '18px 0',
        display: 'flex',
        justifyContent: 'center',
        borderBottom: '1px solid rgba(212,175,55,0.14)',
        background:   'linear-gradient(180deg, rgba(212,175,55,0.05), transparent)',
        flexShrink: 0,
      }}>
        <div style={{
          width: 36, height: 36,
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'center',
          borderRadius:   '9px',
          background:     'rgba(212,175,55,0.07)',
          border:         '1px solid rgba(212,175,55,0.30)',
          boxShadow:      '0 0 20px rgba(212,175,55,0.10)',
        }}>
          <span className="gnx-omega" style={{
            fontFamily: 'Georgia, serif',
            fontSize:   '22px',
            color:      C.gold,
            lineHeight: 1,
          }}>Ω</span>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      padding:      '26px 18px 18px 18px',
      borderBottom: '1px solid rgba(212,175,55,0.12)',
      background:   'linear-gradient(180deg, rgba(212,175,55,0.045) 0%, rgba(0,0,0,0) 100%)',
      flexShrink:   0,
    }}>
      {/* Brand wordmark */}
      <div style={{ marginBottom: '2px' }}>
        <span className="gnx-logo-text" style={{ fontSize: '21px', display: 'block', lineHeight: 1.1 }}>
          GENESIX
        </span>
      </div>

      {/* Omega glyph */}
      <div style={{ marginTop: '-2px', marginBottom: '8px' }}>
        <span className="gnx-omega" style={{
          fontFamily:    'Georgia, serif',
          fontSize:      '30px',
          fontWeight:    900,
          color:         C.gold,
          lineHeight:    1,
          display:       'inline-block',
          letterSpacing: '0.04em',
        }}>
          Ω
        </span>
      </div>

      {/* Tagline */}
      <span style={{
        fontFamily:    "'JetBrains Mono', monospace",
        fontSize:      '8.5px',
        fontWeight:    500,
        letterSpacing: '0.16em',
        textTransform: 'uppercase',
        color:         'rgba(100,116,139,0.55)',
        display:       'block',
        marginBottom:  '16px',
      }}>
        Quantum Trading Intelligence
      </span>

      {/* Separator — silver→gold gradient that fades at edges */}
      <div style={{
        width:      '100%',
        height:     '1px',
        background: 'linear-gradient(90deg, transparent 0%, rgba(192,192,192,0.20) 25%, rgba(212,175,55,0.45) 50%, rgba(192,192,192,0.20) 75%, transparent 100%)',
      }} />
    </div>
  );
}

// ─── FOOTER BLOCK ─────────────────────────────────────────────────────────────
function FooterBlock({ isCollapsed, onToggleCollapse }) {
  return (
    <div style={{
      flexShrink: 0,
      borderTop:  `1px solid ${C.border}`,
      padding:    isCollapsed ? '10px 0' : '10px 14px',
      display:    'flex',
      alignItems: 'center',
      justifyContent: isCollapsed ? 'center' : 'space-between',
      background: 'rgba(0,0,0,0.18)',
      gap:        '8px',
    }}>
      {/* Left: live + version */}
      {!isCollapsed && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div className="gnx-live-dot" style={{
              width: '6px', height: '6px',
              borderRadius: '50%',
              background: '#10B981',
              flexShrink: 0,
            }} />
            <span style={{
              fontFamily:    "'JetBrains Mono', monospace",
              fontSize:      '9px',
              fontWeight:    600,
              letterSpacing: '0.13em',
              textTransform: 'uppercase',
              color:         '#10B981',
            }}>
              Live
            </span>
          </div>
          <span style={{
            fontFamily:    "'JetBrains Mono', monospace",
            fontSize:      '9px',
            color:         C.t3,
            letterSpacing: '0.06em',
          }}>
            v2.4.1 · RAVINALA
          </span>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        className="gnx-toggle-btn"
        onClick={onToggleCollapse}
        aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {isCollapsed ? <Menu size={14} /> : <X size={14} />}
      </button>
    </div>
  );
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────
/**
 * @param {string}   activeItem    — Currently active page label (default: 'Live Market')
 * @param {Function} onNavigate    — Callback(label: string) when user clicks a nav item
 */
export default function GenesixSidebar({ activeItem = 'Live Market', onNavigate }) {
  const [collapsed,    setCollapsed]    = useState(false);
  const [active,       setActive]       = useState(activeItem);
  const [openSections, setOpenSections] = useState(() =>
    Object.fromEntries(MENU.map(g => [g.section, true]))
  );

  const handleNavigate = useCallback((label) => {
    setActive(label);
    if (onNavigate) onNavigate(label);
  }, [onNavigate]);

  const toggleSection = useCallback((section) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  }, []);

  const SIDEBAR_W = collapsed ? 60 : 270;

  return (
    <>
      {/* Inject global CSS once */}
      <style>{GLOBAL_CSS}</style>

      <motion.aside
        animate={{ width: SIDEBAR_W }}
        transition={{ duration: 0.28, ease: [0.4, 0, 0.2, 1] }}
        style={{
          position:        'fixed',
          top:             0,
          left:            0,
          height:          '100vh',
          zIndex:          100,
          display:         'flex',
          flexDirection:   'column',
          /* Deep noise-ish dark background via gradient layering */
          background: [
            'linear-gradient(180deg,',
            '  #080C14 0%,',
            '  #0A0E18 40%,',
            '  #080B12 100%)',
          ].join(' '),
          borderRight:     `1px solid ${C.border}`,
          /* Subtle gold rim on the right edge */
          boxShadow: [
            '4px 0 32px rgba(0,0,0,0.55)',
            '1px 0 0  rgba(212,175,55,0.04)',
          ].join(', '),
          overflow:        'hidden',
          fontFamily:      "'DM Sans', sans-serif",
        }}
      >
        {/* ── Brand header ───────────────────────────────────────────────── */}
        <LogoBlock isCollapsed={collapsed} />

        {/* ── Home shortcut ──────────────────────────────────────────────── */}
        {!collapsed && (
          <div style={{ padding: '8px 6px 0 6px', flexShrink: 0 }}>
            <NavItem
              item={{ label: 'Home', icon: Home }}
              sectionTheme={{ color: C.cyan, dim: C.cyanDim, glow: C.cyanGlow }}
              isActive={active === 'Home'}
              isCollapsed={false}
              onActivate={handleNavigate}
            />
          </div>
        )}

        {/* ── Scrollable nav ─────────────────────────────────────────────── */}
        <div
          className="gnx-scroll"
          style={{
            flex:        1,
            overflowY:   'auto',
            overflowX:   'hidden',
            padding:     collapsed ? '4px 4px' : '2px 6px 12px 6px',
          }}
        >
          <motion.nav
            variants={staggerList}
            initial="hidden"
            animate="show"
          >
            {MENU.map((group, idx) => {
              const theme    = SECTION_THEME[group.section] || { color: C.silver, dim: 'rgba(192,192,192,0.06)', glow: 'rgba(192,192,192,0.10)' };
              const isOpen   = openSections[group.section];
              const isLast   = idx === MENU.length - 1;
              const isGenesix = group.section === 'GENESIX Ω';

              return (
                <div key={group.section}>
                  {/* Genesix: gold divider above the section */}
                  {isGenesix && <Divider gold />}

                  {/* Section header */}
                  <SectionHeader
                    section={group.section}
                    isOpen={isOpen}
                    onToggle={() => toggleSection(group.section)}
                    theme={theme}
                    isCollapsed={collapsed}
                  />

                  {/* Collapsible items */}
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        key="items"
                        variants={sectionContent}
                        initial="closed"
                        animate="open"
                        exit="closed"
                        style={{ overflow: 'hidden' }}
                      >
                        <motion.div
                          variants={staggerList}
                          initial="hidden"
                          animate="show"
                          style={{ padding: '1px 0 2px 0' }}
                        >
                          {group.items.map(item => (
                            <NavItem
                              key={item.label}
                              item={item}
                              sectionTheme={theme}
                              isActive={active === item.label}
                              isCollapsed={collapsed}
                              onActivate={handleNavigate}
                            />
                          ))}
                        </motion.div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Section divider — gold for Genesix section, normal otherwise */}
                  {!isLast && <Divider gold={isGenesix} />}
                </div>
              );
            })}
          </motion.nav>
        </div>

        {/* ── Footer ─────────────────────────────────────────────────────── */}
        <FooterBlock
          isCollapsed={collapsed}
          onToggleCollapse={() => setCollapsed(v => !v)}
        />
      </motion.aside>
    </>
  );
}
