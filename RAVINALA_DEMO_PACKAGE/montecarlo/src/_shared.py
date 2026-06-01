"""
Shared utilities, CSS, market header and sidebar widgets for Ravinala multipage app.
Imported by app.py (entry point) and by all pages/ modules.
"""

import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# Ensure src/ is always on the path, regardless of whether this file
# is imported from src/ or from src/pages/
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from market_data import (
    fetch_spot_vol_div,
    fetch_atm_implied_vol,
    fetch_vol_surface,
    fetch_risk_free_rate,
    fetch_risk_free_rate_quote,
    fetch_market_overview,
    fetch_price_history,
)
from genesix.utils.quant_conventions import (
    RISK_FREE_RATE,
    RISK_FREE_RATE_LAST_UPDATED,
    RISK_FREE_RATE_SOURCE,
)
import utils

# ── CSS constant ─────────────────────────────────────────────────────────────
CSS = """
<style>
/* ── GOOGLE FONTS ──────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;800;900&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,450;9..40,500;9..40,600&family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ── DESIGN TOKENS (PREMIUM INSTITUTIONAL DARK MODE) ───────────────────── */
:root {
    /* BACKGROUNDS */
    --color-bg-base:      #0A0E1A;
    --color-bg-surface:   #131823;
    --color-bg-elevated:  #1A2332;
    --color-bg-hover:     #1F2A3A;
    --color-bg-active:    #2A3647;

    /* TEXT */
    --color-text-primary:   #F1F5F9;
    --color-text-secondary: #CBD5E1;
    --color-text-tertiary:  #94A3B8;
    --color-text-disabled:  #64748B;
    --color-text-muted:     #475569;

    /* ACCENTS */
    --color-accent-primary:   #00D9FF;
    --color-accent-secondary: #7C3AED;
    --color-accent-error:     #EF4444;
    --color-accent-success:   #10B981;
    --color-accent-warning:   #F59E0B;

    /* BORDERS */
    --color-border-default: rgba(51, 65, 85, 0.3);
    --color-border-hover:   rgba(0, 217, 255, 0.2);
    --color-border-focus:   rgba(0, 217, 255, 0.4);
    --color-divider-light:  rgba(51, 65, 85, 0.1);
    --color-divider:        rgba(51, 65, 85, 0.2);

    /* ASSET COLOURS */
    --color-equities:     #3B82F6;
    --color-fixed-income: #10B981;
    --color-derivatives:  #F59E0B;
    --color-commodities:  #EF4444;
    --color-etfs:         #8B5CF6;
    --color-crypto:       #F97316;

    /* TYPOGRAPHY */
    --font-family-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-family-mono: 'JetBrains Mono', 'Fira Code', monospace;

    --font-size-h1: 32px;
    --font-size-h2: 24px;
    --font-size-h3: 18px;
    --font-size-h4: 14px;
    --font-size-h5: 12px;
    --font-size-body-lg: 14px;
    --font-size-body: 13px;
    --font-size-body-sm: 12px;
    --font-size-xs: 11px;

    --font-weight-regular: 400;
    --font-weight-medium:  500;
    --font-weight-semibold: 600;
    --font-weight-bold:    700;

    /* SPACING (8px base) */
    --space-xs:  4px;
    --space-sm:  8px;
    --space-md:  12px;
    --space-lg:  16px;
    --space-xl:  24px;
    --space-2xl: 32px;
    --space-3xl: 48px;

    /* BORDER RADIUS */
    --radius-xs:   3px;
    --radius-sm:   6px;
    --radius-md:   8px;
    --radius-lg:   10px;
    --radius-full: 9999px;

    /* SHADOWS */
    --shadow-sm:    0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md:    0 4px 8px rgba(0, 0, 0, 0.1);
    --shadow-lg:    0 8px 16px rgba(0, 0, 0, 0.15);
    --shadow-xl:    0 12px 24px rgba(0, 0, 0, 0.2);
    --shadow-2xl:   0 20px 40px rgba(0, 0, 0, 0.25);
    --shadow-focus: 0 0 0 3px rgba(0, 217, 255, 0.15);

    /* TRANSITIONS */
    --transition-fast:   150ms ease;
    --transition-normal: 200ms ease;
    --transition-slow:   300ms ease-out;
    --transition-slower: 500ms ease;

    /* ── LEGACY ALIASES (backward compat) ─── */
    --bg-main:     #0A0E1A;
    --bg-secondary: #131823;
    --bg-tertiary: #0F1218;
    --bg-hover:    #1F2A3A;
    --accent-primary:   #00D9FF;
    --accent-secondary: #7C3AED;
    --accent-tertiary:  #06B6D4;
    --success:  #10B981;
    --alert:    #EF4444;
    --warning:  #F59E0B;
    --neutral:  #94A3B8;
    --text-primary:   #F1F5F9;
    --text-secondary: #CBD5E1;
    --text-tertiary:  #94A3B8;
    --text-disabled:  #64748B;
    --border-default: rgba(51, 65, 85, 0.3);
    --border-hover:   rgba(0, 217, 255, 0.2);
    --border-focus:   rgba(0, 217, 255, 0.4);
    --divider:        rgba(51, 65, 85, 0.2);
    --equities:     #3B82F6;
    --fixed-income: #10B981;
    --derivatives:  #F59E0B;
    --commodities:  #EF4444;
    --etfs:         #8B5CF6;
    --crypto:       #F97316;
    --font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-mono:    'JetBrains Mono', 'Fira Code', monospace;
    --r-sm:  6px;
    --r-md:  8px;
    --r-lg:  10px;
    --trans-fast:     all 150ms ease;
    --trans-standard: all 200ms ease;
    --trans-slow:     all 300ms ease-out;
    --glass: rgba(19, 24, 35, 0.6);
    --glass-h: rgba(26, 35, 50, 0.8);
    --border: rgba(51, 65, 85, 0.3);
    --border-h: rgba(0, 217, 255, 0.2);
    --trans: all 200ms ease;
    --ease: all 200ms ease;
    --glow: 0 0 20px rgba(0, 217, 255, 0.15);
    --glow-cyan: 0 0 20px rgba(0, 217, 255, 0.15);
    --glow-purple: 0 0 20px rgba(124, 58, 237, 0.12);
    --mono: 'JetBrains Mono', 'Fira Code', monospace;
    --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --bg: #0A0E1A;
    --bg-s: #131823;
    --t1: #F1F5F9;
    --t2: #CBD5E1;
    --t3: #94A3B8;
    --accent: #00D9FF;
    --accent2: #7C3AED;
    --green: #10B981;
    --blue: #3B82F6;
    --red: #EF4444;
    --amber: #F59E0B;
    --accent-dim: rgba(0, 217, 255, 0.08);
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 8px rgba(0,0,0,0.1);
    --shadow-lg: 0 8px 16px rgba(0,0,0,0.15);
}

/* ── RESET ─────────────────────────────────────────────────────────────── */
*,*::before,*::after{box-sizing:border-box}
[data-testid="stHeader"],[data-testid="stDecoration"]{display:none!important}
#MainMenu{visibility:hidden!important}
footer{display:none!important}

/* ── BASE ──────────────────────────────────────────────────────────────── */
html,body{
    background:var(--color-bg-base)!important;
    font-family:var(--font-family-body)!important;
    -webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;
    margin:0!important;padding:0!important;
    scrollbar-gutter:stable!important;
    overflow-x:hidden!important;
    overflow-y:auto!important;
    height:auto!important;
    color:var(--color-text-primary)!important;
    font-size:var(--font-size-body);
    line-height:1.5;
}
[data-testid="stApp"]{
    background:var(--color-bg-base)!important;
    background-image:
        radial-gradient(ellipse 1200px 800px at 20% 10%, rgba(0,217,255,0.04), transparent 55%),
        radial-gradient(ellipse 900px 650px at 85% 20%, rgba(124,58,237,0.03), transparent 55%);
    /* NE PAS mettre display:block — ça casse le flex layout de Streamlit */
}
[data-testid="stAppViewContainer"]{
    background:var(--color-bg-base)!important;
}
[data-testid="block-container"]{padding-top:0!important;padding-left:0!important;
  padding-right:0!important;max-width:100%}

/* ── RESET STREAMLIT DEFAULTS ──────────────────────────────────────────── */
[data-testid="stHeader"]{display:none!important}
[data-testid="stDecoration"]{display:none!important}
[data-testid="stMainBlockContainer"]{margin:0!important;padding:0!important}
[data-testid="stMain"]{padding:0!important;margin:0!important}
[data-testid="stAppViewContainer"] > section {margin:0!important;padding:0!important}
/* ── HIDE STREAMLIT 1.55 TOP NAV BAR (custom sidebar nav used instead) ── */
[data-testid="stToolbar"]{display:none!important}
[data-testid="stTopNavLink"]{display:none!important}
[data-testid="stTopNavSection"]{display:none!important}
[data-testid="stTopNavLinkContainer"]{display:none!important}
[data-testid="stTopNavPopover"]{display:none!important}

/* ── TOPBAR (56px, sticky) ──────────────────────────────────────────────── */
.rh{position:fixed;top:0;left:280px;right:0;height:56px;z-index:1000;
    background:rgba(10,14,26,0.82);backdrop-filter:blur(20px) saturate(180%);
    -webkit-backdrop-filter:blur(20px) saturate(180%);
    border-bottom:1px solid var(--color-border-default);
    display:flex;align-items:center;padding:0 var(--space-xl);gap:var(--space-md)}
.rh-logo-text{font-size:16px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
    color:var(--color-accent-primary);font-family:var(--font-family-body)}
.rh-sep{width:1px;height:16px;background:rgba(51,65,85,0.3);flex-shrink:0}
.rh-sub{font-size:var(--font-size-xs);color:var(--color-text-tertiary);font-weight:400;white-space:nowrap}
.rh-spacer{flex:1}
.rh-tag{font-size:10px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
    padding:4px 10px;border-radius:var(--radius-full);white-space:nowrap;flex-shrink:0}
.rh-tag-green{background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.20);color:var(--color-accent-success)}
.rh-tag-blue{background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.16);color:var(--color-equities)}

/* ── SIDEBAR: FIXED LAYOUT (NO TOGGLE) ───────────────────────────────── */
[data-testid="stSidebar"],
[data-testid="stSidebar"][aria-expanded="false"],
[data-testid="stSidebar"][aria-expanded="true"] {
    position: fixed !important;
    left: 0 !important;
    top: 0 !important;
    height: 100vh !important;
    width: 280px !important;
    min-width: 280px !important;
    max-width: 280px !important;
    z-index: 40 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    background: var(--color-bg-surface) !important;
    border: none !important;
    border-right: 1px solid var(--color-border-default) !important;
    box-shadow: none !important;
    margin: 0 !important;
    padding: 0 !important;
    pointer-events: auto !important;
    visibility: visible !important;
    display: block !important;
    transform: none !important;
    transition: none !important;
}

[data-testid="stSidebarContent"] {
    padding: 0 4px var(--space-xl) 4px !important;
}

/* ── SIDEBAR: HIDE ALL COLLAPSE/TOGGLE CONTROLS ─────────────────────── */
[data-testid="stSidebarCollapsedControl"]          { display:none!important }
[data-testid="stSidebarCollapseButton"]            { display:none!important }
button[aria-label="Close sidebar"]                 { display:none!important }
button[aria-label="Open sidebar"]                  { display:none!important }
button[aria-label="collapse sidebar"]              { display:none!important }
button[aria-label="expand sidebar"]                { display:none!important }
button[title*="sidebar"]                           { display:none!important }
button[data-testid="baseButton-headerNoBg"]        { display:none!important }
[data-testid="collapsedControl"]                   { display:none!important }
/* stSidebarNav — force all sections always visible */
[data-testid="stSidebarNav"] { display: block !important; }
[data-testid="stSidebarNav"] details { display: block !important; }
[data-testid="stSidebarNav"] details > ul { display: block !important; visibility: visible !important; }
[data-testid="stSidebarNav"] details summary svg { display: none !important; }
[data-testid="stSidebarNav"] details summary { pointer-events: none !important; cursor: default !important; }

/* Push main content to the right */
[data-testid="stAppViewContainer"] {
    margin-left: 280px !important;
    padding-left: var(--space-2xl) !important;
    padding-right: var(--space-xl) !important;
    padding-top: 116px !important;
    width: calc(100% - 280px) !important;
}

/* ── MARKET STRIP ──────────────────────────────────────────────────────── */
.rvn-global-market-strip{
    position:fixed;top:56px;left:280px;right:0;height:54px;z-index:900;
    background:rgba(13,18,30,0.92);
    border-bottom:1px solid var(--color-divider);
    backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
    display:flex;align-items:center;padding:0 var(--space-lg)}
.rvn-global-market-meta{font-size:10px;color:var(--color-text-disabled);letter-spacing:.08em;text-transform:uppercase;
    font-weight:600;white-space:nowrap;margin-right:var(--space-md)}
.rvn-global-market-track{display:flex;gap:var(--space-sm);overflow-x:auto;white-space:nowrap;
    width:100%;scrollbar-width:thin}
.rvn-mkt-card{flex:0 0 auto;min-width:196px;
    background:linear-gradient(135deg, rgba(19,24,35,0.6), rgba(15,18,24,0.6));
    border:1px solid var(--color-border-default);border-radius:var(--radius-lg);padding:6px 10px;
    transition:all var(--transition-normal)}
.rvn-mkt-card:hover{border-color:var(--color-border-hover);transform:translateY(-1px)}
.rvn-mkt-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:3px}
.rvn-mkt-venue{font-size:10px;color:var(--color-accent-primary);font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.rvn-mkt-time{font-size:10px;color:var(--color-text-tertiary);font-family:var(--font-family-mono)}
.rvn-mkt-index{font-size:10px;color:var(--color-text-tertiary);letter-spacing:.03em;text-transform:uppercase}
.rvn-mkt-level{font-size:16px;line-height:1.1;color:var(--color-text-primary);font-weight:700;font-family:var(--font-family-mono);margin-top:2px;font-variant-numeric:tabular-nums}
.rvn-mkt-status-wrap{display:flex;align-items:center;gap:6px;margin-top:3px}
.rvn-mkt-dot{width:7px;height:7px;border-radius:50%}
.rvn-mkt-status{font-size:10px;color:var(--color-text-secondary);text-transform:uppercase;letter-spacing:.05em}
.rvn-mkt-change{font-size:10px;font-weight:700;font-family:var(--font-family-mono);margin-left:auto;font-variant-numeric:tabular-nums}

/* Sidebar nav — replaced by custom rvn injector */
[data-testid="stSidebar"] [data-testid="stRadio"]{display:none!important}
.nav-divider{height:1px;background:rgba(255,255,255,0.05);margin:10px 14px}

/* ── SIDEBAR PARAMS ────────────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stExpander"]{
  margin:0 var(--space-sm) var(--space-xs) var(--space-sm)!important;
  border:1px solid var(--color-border-default)!important;
  border-radius:var(--radius-md)!important;background:rgba(19,24,35,0.4)!important}
[data-testid="stSidebar"] [data-testid="stExpander"] summary{
  font-size:var(--font-size-xs)!important;font-weight:600!important;
  color:var(--color-text-tertiary)!important;padding:10px var(--space-md)!important}
[data-testid="stSidebar"] .stMetric{padding:var(--space-sm) var(--space-md)!important;
  background:rgba(26,35,50,0.4)!important;border-radius:var(--radius-md)!important;margin:3px var(--space-sm)!important}
[data-testid="stSidebar"] [data-testid="stMetricValue"]{
  font-size:var(--font-size-body-lg)!important;font-weight:700!important;
  color:var(--color-text-primary)!important;font-family:var(--font-family-mono)!important;font-variant-numeric:tabular-nums}
[data-testid="stSidebar"] [data-testid="stMetricLabel"]{
  font-size:10px!important;text-transform:uppercase!important;
  letter-spacing:.08em!important;color:var(--color-text-tertiary)!important;font-weight:600!important}

/* ── TYPOGRAPHY (Strict Hierarchy) ─────────────────────────────────────── */
h1{font-size:var(--font-size-h1);font-weight:var(--font-weight-semibold);color:var(--color-text-primary);
    margin:0 0 var(--space-sm) 0;line-height:1.2;letter-spacing:-.02em;font-family:var(--font-family-body)}
h2{font-size:var(--font-size-h2);font-weight:var(--font-weight-semibold);color:var(--color-text-primary);
    margin:var(--space-xl) 0 var(--space-md) 0;line-height:1.3;letter-spacing:-.01em}
h3{font-size:var(--font-size-h3);font-weight:var(--font-weight-semibold);color:var(--color-text-primary);
    margin:var(--space-lg) 0 var(--space-sm) 0;line-height:1.4}
h4{font-size:var(--font-size-h4);font-weight:var(--font-weight-bold);color:var(--color-text-secondary);
    margin:var(--space-lg) 0 var(--space-sm) 0;line-height:1.5;letter-spacing:.5px;text-transform:uppercase}
h5{font-size:var(--font-size-h5);font-weight:var(--font-weight-bold);color:var(--color-text-tertiary);
    letter-spacing:.5px;text-transform:uppercase}
p{color:var(--color-text-secondary);font-size:var(--font-size-body-lg);line-height:1.6}

/* ── METRIC CARDS ──────────────────────────────────────────────────────── */
[data-testid="stMetric"]{
    background:linear-gradient(135deg, rgba(19,24,35,0.6), rgba(15,18,24,0.6));
    border:1px solid var(--color-border-default);border-radius:var(--radius-lg);
    padding:var(--space-lg) var(--space-xl);transition:all var(--transition-normal);
    position:relative;overflow:hidden}
[data-testid="stMetric"]:hover{
    border-color:var(--color-border-hover);
    box-shadow:var(--shadow-md), 0 0 0 1px var(--color-border-hover);
    transform:translateY(-2px)}
[data-testid="stMetricValue"]{
    font-size:22px!important;font-weight:700!important;color:var(--color-text-primary)!important;
    letter-spacing:-.02em!important;font-family:var(--font-family-mono)!important;
    font-variant-numeric:tabular-nums}
[data-testid="stMetricLabel"]{
    font-size:10px!important;color:var(--color-text-tertiary)!important;
    text-transform:uppercase!important;letter-spacing:.08em!important;font-weight:600!important}
[data-testid="stMetricDelta"]{font-size:var(--font-size-xs)!important;font-weight:600!important}

/* ── BUTTONS (Premium Silver/Gold Design System) ─────────────────────── */
.stButton > button {
    font-family: 'DM Sans', 'Geist', -apple-system, BlinkMacSystemFont, sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    
    /* Silver gradient background */
    background: linear-gradient(
        135deg,
        rgba(192, 192, 200, 0.12) 0%,
        rgba(212, 212, 220, 0.18) 50%,
        rgba(192, 192, 200, 0.12) 100%
    ) !important;
    
    border: 1px solid rgba(192, 192, 210, 0.25) !important;
    color: #F0F0F5 !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.02em !important;
    padding: 12px 24px !important;
    min-height: 44px !important;
    
    box-shadow: 
        0 1px 2px rgba(0, 0, 0, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
    
    transition: all 200ms cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
    cursor: pointer !important;
}

.stButton > button:hover {
    background: linear-gradient(
        135deg,
        rgba(192, 192, 200, 0.18) 0%,
        rgba(220, 220, 230, 0.25) 50%,
        rgba(192, 192, 200, 0.18) 100%
    ) !important;
    border-color: rgba(192, 192, 210, 0.40) !important;
    color: #FFFFFF !important;
    
    box-shadow: 
        0 2px 8px rgba(192, 192, 210, 0.15),
        0 1px 2px rgba(0, 0, 0, 0.3),
        inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    
    transform: translateY(-1px) !important;
}

.stButton > button:active {
    transform: translateY(0px) scale(0.98) !important;
    box-shadow: 
        0 1px 2px rgba(0, 0, 0, 0.4),
        inset 0 1px 3px rgba(0, 0, 0, 0.2) !important;
}

/* ── INPUTS (Clean, minimal) ────────────────────────────────────────────── */
.stTextInput>div>div>input,.stNumberInput>div>div>input{
    background:rgba(51,65,85,0.2)!important;border:1px solid var(--color-border-default)!important;
    border-radius:var(--radius-sm)!important;color:var(--color-text-primary)!important;
    font-size:var(--font-size-body)!important;font-family:var(--font-family-mono)!important;
    padding:8px 12px!important;transition:all var(--transition-normal)}
.stTextInput>div>div>input:focus,.stNumberInput>div>div>input:focus{
    border-color:var(--color-accent-primary)!important;outline:none!important;
    box-shadow:0 0 12px rgba(0,217,255,0.1)!important;
    background:rgba(51,65,85,0.3)!important}
[data-testid="stSelectbox"]>div>div{
    background:rgba(51,65,85,0.2)!important;border:1px solid var(--color-border-default)!important;
    border-radius:var(--radius-sm)!important;color:var(--color-text-primary)!important}
[data-testid="stMultiSelect"]>div>div{
    background:rgba(51,65,85,0.2)!important;border:1px solid var(--color-border-default)!important;
    border-radius:var(--radius-sm)!important;color:var(--color-text-primary)!important}
[data-testid="stSelectbox"]>div>div:focus-within,
[data-testid="stMultiSelect"]>div>div:focus-within{
    border-color:var(--color-accent-primary)!important;
    box-shadow:var(--shadow-focus)!important;
    background:rgba(51,65,85,0.3)!important}
.stTextArea textarea{
    background:rgba(51,65,85,0.2)!important;border:1px solid var(--color-border-default)!important;
    border-radius:var(--radius-md)!important;color:var(--color-text-primary)!important;
    font-family:var(--font-family-mono)!important;font-size:var(--font-size-body-sm)!important;line-height:1.5!important}
.stTextArea textarea:focus{
    border-color:var(--color-accent-primary)!important;
    box-shadow:var(--shadow-focus)!important;
    background:rgba(51,65,85,0.3)!important}
label[data-testid="stWidgetLabel"]>p{
    color:var(--color-text-tertiary)!important;font-size:var(--font-size-body-sm)!important;
    font-weight:500!important;text-transform:uppercase!important;letter-spacing:.06em!important}

/* ── RADIOS / CHIPS ────────────────────────────────────────────────────── */
[data-testid="stRadio"] [role="radiogroup"]{
    gap:var(--space-sm)!important;display:flex!important;flex-wrap:wrap!important}
[data-testid="stRadio"] [role="radio"]{
    border:1px solid var(--color-border-default)!important;border-radius:var(--radius-full)!important;
    background:rgba(19,24,35,0.5)!important;color:var(--color-text-tertiary)!important;
    padding:6px 14px!important;transition:all var(--transition-normal)!important;font-size:var(--font-size-body-sm)!important}
[data-testid="stRadio"] [role="radio"][aria-checked="true"]{
    border-color:rgba(0,217,255,.35)!important;
    background:rgba(0,217,255,.08)!important;
    color:var(--color-text-primary)!important}
[data-testid="stRadio"] [role="radio"]:hover{
    border-color:var(--color-border-hover)!important;color:var(--color-text-secondary)!important}

/* ── SLIDERS ───────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [role="progressbar"]{
    background:linear-gradient(90deg,#3B82F6,var(--color-accent-primary))!important}
[data-testid="stSlider"] [role="slider"]{
    background:var(--color-accent-primary)!important;border-color:var(--color-accent-primary)!important;
    box-shadow:0 4px 12px rgba(0,217,255,0.25)!important}

/* ── EXPANDERS ─────────────────────────────────────────────────────────── */
[data-testid="stExpander"]{
    border:1px solid var(--color-border-default)!important;border-radius:var(--radius-md)!important;
    background:linear-gradient(135deg, rgba(19,24,35,0.5), rgba(15,18,24,0.5))!important;overflow:hidden}
[data-testid="stExpander"] summary{
    font-size:var(--font-size-body)!important;font-weight:600!important;
    color:var(--color-text-secondary)!important;padding:var(--space-md) var(--space-lg)!important}
[data-testid="stExpander"] summary:hover{background:rgba(0,217,255,.03)!important}

/* ── DIVIDER ───────────────────────────────────────────────────────────── */
[data-testid="stDivider"]{border-color:var(--color-divider-light)!important;margin:var(--space-xl) 0!important}

/* ── STATUS BOXES (left-border style like toast) ───────────────────────── */
.stInfo>div{background:rgba(59,130,246,.04)!important;border:1px solid rgba(59,130,246,.12)!important;
    border-left:3px solid var(--color-accent-primary)!important;
    border-radius:var(--radius-md)!important;color:var(--color-text-secondary)!important}
.stSuccess>div{background:rgba(16,185,129,.04)!important;border:1px solid rgba(16,185,129,.12)!important;
    border-left:3px solid var(--color-accent-success)!important;
    border-radius:var(--radius-md)!important;color:var(--color-text-secondary)!important}
.stWarning>div{background:rgba(245,158,11,.04)!important;border:1px solid rgba(245,158,11,.12)!important;
    border-left:3px solid var(--color-accent-warning)!important;
    border-radius:var(--radius-md)!important;color:var(--color-text-secondary)!important}
.stError>div{background:rgba(239,68,68,.04)!important;border:1px solid rgba(239,68,68,.12)!important;
    border-left:3px solid var(--color-accent-error)!important;
    border-radius:var(--radius-md)!important;color:var(--color-text-secondary)!important}

/* ── DATAFRAME & TABLES (Professional, dense) ──────────────────────────── */
[data-testid="stDataFrame"]{border-radius:var(--radius-lg)!important;overflow:hidden;
    border:1px solid var(--color-border-default)!important;
    background:linear-gradient(135deg, rgba(19,24,35,0.5), rgba(15,18,24,0.5))!important;
    box-shadow:var(--shadow-md)}
.stTable table{
    border-collapse:separate!important;border-spacing:0!important;
    border:1px solid var(--color-border-default)!important;border-radius:var(--radius-lg)!important;overflow:hidden!important}
.stTable table thead tr th{
    background:rgba(19,24,35,0.4)!important;color:var(--color-text-tertiary)!important;
    font-size:var(--font-size-body-sm)!important;letter-spacing:.05em!important;text-transform:uppercase!important;
    font-weight:700!important;padding:var(--space-md)!important;
    border-bottom:1px solid var(--color-divider)!important}
.stTable table tbody tr td{
    background:transparent!important;color:var(--color-text-secondary)!important;
    font-size:var(--font-size-body-sm)!important;font-family:var(--font-family-mono)!important;
    padding:10px var(--space-md)!important;
    border-bottom:1px solid var(--color-divider-light)!important}
.stTable table tbody tr:hover td{background:rgba(0,217,255,0.03)!important}

/* ── DOWNLOAD BUTTONS (Secondary style) ────────────────────────────────── */
.stDownloadButton>button{
    background:rgba(0,217,255,.06)!important;border:1px solid rgba(0,217,255,.2)!important;
    color:var(--color-accent-primary)!important;border-radius:var(--radius-sm)!important;
    font-weight:600!important;font-size:var(--font-size-body)!important;
    letter-spacing:.02em!important;transition:all var(--transition-normal)!important}
.stDownloadButton>button:hover{
    background:rgba(0,217,255,.12)!important;border-color:var(--color-accent-primary)!important}

/* ── BORDERED CONTAINERS (Cards) ───────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"]{
    border:1px solid var(--color-border-default)!important;
    border-radius:var(--radius-lg)!important;
    background:linear-gradient(135deg, rgba(19,24,35,0.6), rgba(15,18,24,0.6))!important;
    box-shadow:var(--shadow-md)!important;
    transition:all var(--transition-normal)!important}
div[data-testid="stVerticalBlockBorderWrapper"]:hover{
    border-color:var(--color-border-hover)!important;
    box-shadow:0 8px 24px rgba(0,217,255,0.06)!important;
    transform:translateY(-1px)}
div[data-testid="stVerticalBlockBorderWrapper"] > div{
    background:transparent!important}

/* ── TABS (clean underline style) ──────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"]{
    border-bottom:1px solid var(--color-divider)!important;gap:0!important}
[data-testid="stTabs"] [role="tab"]{
    color:var(--color-text-tertiary)!important;font-size:var(--font-size-body)!important;
    font-weight:500!important;letter-spacing:.02em!important;
    padding:var(--space-md) var(--space-lg)!important;
    border-radius:0!important;transition:all var(--transition-normal)!important;
    border-bottom:2px solid transparent!important}
[data-testid="stTabs"] [role="tab"]:hover{
    color:var(--color-text-primary)!important;background:rgba(0,217,255,0.03)!important}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{
    color:var(--color-accent-primary)!important;border-bottom:2px solid var(--color-accent-primary)!important}

/* ── SCROLLBAR ─────────────────────────────────────────────────────────── */
/* Global: fine */
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(51,65,85,0.3);border-radius:var(--radius-full)}
::-webkit-scrollbar-thumb:hover{background:rgba(51,65,85,0.5)}

/* Main content scroll container: visible scrollbar on the right */
[data-testid="stAppViewContainer"]::-webkit-scrollbar {
    width: 6px !important;
}
[data-testid="stAppViewContainer"]::-webkit-scrollbar-track {
    background: rgba(15,18,24,0.5) !important;
}
[data-testid="stAppViewContainer"]::-webkit-scrollbar-thumb {
    background: rgba(212,175,55,0.35) !important;
    border-radius: 999px !important;
}
[data-testid="stAppViewContainer"]::-webkit-scrollbar-thumb:hover {
    background: rgba(212,175,55,0.65) !important;
}
/* Firefox */
[data-testid="stAppViewContainer"] {
    scrollbar-width: thin !important;
    scrollbar-color: rgba(212,175,55,0.35) rgba(15,18,24,0.5) !important;
}

/* ── WATERMARKS ────────────────────────────────────────────────────────── */
.watermark{position:fixed;top:50%;left:50%;
    transform:translate(-50%,-50%) rotate(-45deg);font-size:120px;opacity:.004;
    color:var(--color-text-disabled);font-weight:900;z-index:0;pointer-events:none;
    white-space:nowrap;user-select:none;font-family:var(--font-family-body)}
.footer-watermark{position:fixed;bottom:var(--space-md);right:var(--space-lg);font-size:10px;
    opacity:.15;color:var(--color-text-disabled);z-index:1;pointer-events:none;letter-spacing:.5px}

/* ── HAMBURGER (HIDDEN) ────────────────────────────────────────────────── */
.rh-hamburger{display:none!important}
#rh-hbg{display:none!important}
[data-testid="collapsedControl"]{position:fixed!important;top:-999px!important;left:-999px!important}

/* ── HERO (Clean, professional) ─────────────────────────────────────────── */
.rvn-hero{position:relative;min-height:72vh;display:flex;align-items:center;
    justify-content:center;overflow:hidden;
    background:linear-gradient(135deg,var(--color-bg-base) 0%,#111830 45%,var(--color-bg-base) 100%)}
.rvn-hero-grid{position:absolute;inset:0;
    background-image:radial-gradient(circle,rgba(51,65,85,0.08) 1px,transparent 1px);
    background-size:32px 32px;opacity:.4;pointer-events:none}
.rvn-hero-wm{position:absolute;right:-60px;top:50%;transform:translateY(-50%);
    opacity:.012;pointer-events:none}
.rvn-hero-inner{position:relative;z-index:2;text-align:center;padding:40px 20px;
    animation:rvn-fade-up .6s ease both}
.rvn-hero-logo{filter:drop-shadow(0 0 20px rgba(0,217,255,.2))}
@keyframes rvn-fade-up{
    from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes rvn-line-grow{from{width:0}to{width:160px}}
.rvn-hero-title{font-family:var(--font-family-body);font-size:clamp(36px,5vw,56px);font-weight:700;
    letter-spacing:-.03em;color:var(--color-text-primary);margin:20px 0 10px 0;line-height:1.1}
.rvn-hero-sub{font-size:var(--font-size-body-sm);color:var(--color-text-tertiary);font-weight:500;
    letter-spacing:.14em;text-transform:uppercase;margin:0 0 var(--space-2xl) 0}
.rvn-hero-sep{width:0;height:1px;
    background:linear-gradient(90deg,transparent,var(--color-accent-primary),transparent);
    margin:0 auto var(--space-2xl) auto;animation:rvn-line-grow .8s .2s ease forwards}
.rvn-hero-badges{display:flex;gap:var(--space-sm);justify-content:center;flex-wrap:wrap;margin-bottom:var(--space-3xl)}
.rvn-scroll{display:flex;flex-direction:column;align-items:center;gap:6px;margin-top:var(--space-sm)}
.rvn-scroll-line{width:1px;height:32px;
    background:linear-gradient(to bottom,rgba(148,163,184,.2),transparent);
    animation:rvn-scroll-anim 2s ease-in-out infinite}
@keyframes rvn-scroll-anim{0%,100%{opacity:.3;transform:scaleY(1)}50%{opacity:.7;transform:scaleY(1.1)}}

/* ── CARDS (Unified, consistent) ────────────────────────────────────────── */
.rvn-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:var(--space-xl);
    max-width:1400px;margin:0 auto var(--space-3xl) auto;padding:0 var(--space-xs)}
@media(max-width:900px){.rvn-grid{grid-template-columns:1fr}}
.rvn-card{background:linear-gradient(135deg, rgba(19,24,35,0.6), rgba(15,18,24,0.6));
    border:1px solid var(--color-border-default);border-radius:var(--radius-lg);
    padding:var(--space-xl);
    transition:all 250ms cubic-bezier(0.34, 1.56, 0.64, 1);
    animation:rvn-card-in .5s ease both}
.rvn-card:nth-child(1){animation-delay:.05s}
.rvn-card:nth-child(2){animation-delay:.1s}
.rvn-card:nth-child(3){animation-delay:.15s}
@keyframes rvn-card-in{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.rvn-card:hover{border-color:rgba(0,217,255,.25);
    box-shadow:0 8px 24px rgba(0,217,255,0.06);transform:translateY(-2px)}
.rvn-card-icon{width:36px;height:36px;border-radius:var(--radius-md);
    background:rgba(0,217,255,0.06);border:1px solid rgba(0,217,255,.12);
    display:flex;align-items:center;justify-content:center;margin-bottom:var(--space-xl)}
.rvn-card-label{font-size:10px;font-weight:700;letter-spacing:.1em;
    text-transform:uppercase;color:var(--color-text-tertiary);margin:0 0 var(--space-sm) 0}
.rvn-card-title{font-size:var(--font-size-h3);font-weight:600;color:var(--color-text-primary);
    letter-spacing:-.01em;margin:0 0 var(--space-lg) 0}
.rvn-card-body{font-size:var(--font-size-body);line-height:1.7;color:var(--color-text-secondary)}
.rvn-card-body strong{color:var(--color-text-primary);font-weight:600}
.rvn-feat-row{display:flex;align-items:center;gap:10px;padding:7px 0;
    border-bottom:1px solid var(--color-divider-light)}
.rvn-feat-row:last-child{border-bottom:none}
.rvn-feat-row:hover{color:var(--color-text-primary)}
.rvn-feat-check{flex-shrink:0;color:var(--color-accent-primary);font-size:var(--font-size-body-sm)}
.rvn-feat-text{font-size:var(--font-size-body);color:var(--color-text-secondary)}
.rvn-bullet{display:flex;align-items:flex-start;gap:10px;padding:5px 0}
.rvn-bullet-dot{width:4px;height:4px;border-radius:1px;background:var(--color-accent-primary);
    flex-shrink:0;margin-top:7px}
.rvn-bullet-text{font-size:var(--font-size-body);line-height:1.65;color:var(--color-text-secondary)}
.rvn-bullet-text strong{color:var(--color-text-primary);font-weight:500}

/* ── PAGE HEADERS ──────────────────────────────────────────────────────── */
.rvn-ph{display:flex;align-items:flex-start;gap:var(--space-lg);
    padding:var(--space-lg) 0 var(--space-xl) 0;border-bottom:1px solid var(--color-divider);margin-bottom:var(--space-xl)}
.rvn-ph-icon{width:40px;height:40px;border-radius:var(--radius-md);
    background:rgba(0,217,255,0.06);border:1px solid rgba(0,217,255,.12);
    display:flex;align-items:center;justify-content:center;flex-shrink:0;
    color:var(--color-accent-primary);font-size:var(--font-size-body-lg);font-weight:700}
.rvn-ph-title{font-size:var(--font-size-h2);font-weight:var(--font-weight-semibold);
    color:var(--color-text-primary);letter-spacing:-.02em;margin:0 0 3px 0;line-height:1.2}
.rvn-ph-sub{font-size:var(--font-size-body-sm);color:var(--color-text-tertiary);margin:0;font-weight:400}

/* ── BADGES ────────────────────────────────────────────────────────────── */
.rvn-badge{display:inline-flex;align-items:center;gap:5px;font-size:10px;
    font-weight:600;letter-spacing:.06em;text-transform:uppercase;
    padding:4px var(--space-md);border-radius:var(--radius-full)}
.rvn-badge-g{background:rgba(0,217,255,.06);border:1px solid rgba(0,217,255,.18);color:var(--color-accent-primary)}
.rvn-badge-b{background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.16);color:var(--color-equities)}
.rvn-badge-a{background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.16);color:var(--color-accent-warning)}

/* ── RESPONSIVE LAYOUT ─────────────────────────────────────────────────── */
/* Tablet: reduce sidebar width */
@media (max-width: 1024px) {
    [data-testid="stSidebar"] { width: 240px !important; min-width: 240px !important; max-width: 240px !important; }
    [data-testid="stAppViewContainer"] { margin-left: 240px !important; padding-top: 116px !important; }
    .rh { left: 240px !important; }
    .rvn-global-market-strip { left: 240px !important; }
}

/* Mobile: hide sidebar, full width */
@media (max-width: 768px) {
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stAppViewContainer"] { margin-left: 0 !important; padding-top: 64px !important; padding-left: var(--space-lg) !important; padding-right: var(--space-lg) !important; width: 100% !important; }
    .rh { left: 0 !important; }
    .rvn-global-market-strip { display: none !important; }
    [data-testid="stHeader"] { display: block !important; }
}

/* ═══════════════════════════════════════════════════════════════════════════
   SIDEBAR NAV — PREMIUM INSTITUTIONAL DARK
   Orbitron logo · DM Sans items · JetBrains Mono headers
   Gold/Silver metallics · Per-section accent colours
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── Sidebar shell ─────────────────────────────────────────────────────── */
[data-testid="stSidebar"],
[data-testid="stSidebar"][aria-expanded="true"],
[data-testid="stSidebar"][aria-expanded="false"] {
    background: linear-gradient(180deg, #080C14 0%, #0A0E18 55%, #08090E 100%) !important;
    border-right: 1px solid rgba(51,65,85,0.45) !important;
    box-shadow: 4px 0 32px rgba(0,0,0,0.55), 1px 0 0 rgba(212,175,55,0.04) !important;
}

/* ── Shimmer keyframe for the logo text ────────────────────────────────── */
@keyframes rvn-logo-shimmer {
    0%   { background-position: -300% center; }
    100% { background-position:  300% center; }
}
/* ── Gold omega glow pulse ─────────────────────────────────────────────── */
@keyframes rvn-omega-glow {
    0%, 100% { text-shadow: 0 0 20px rgba(212,175,55,0.35), 0 0 48px rgba(212,175,55,0.10); }
    50%       { text-shadow: 0 0 32px rgba(212,175,55,0.60), 0 0 64px rgba(212,175,55,0.20); }
}
/* ── Live dot pulse ────────────────────────────────────────────────────── */
@keyframes rvn-live-dot {
    0%, 100% { box-shadow: 0 0 6px 1px rgba(16,185,129,0.7); opacity:1; }
    50%       { box-shadow: 0 0 2px 0   rgba(16,185,129,0.2); opacity:0.5; }
}

/* ── Brand strip (pseudo-element header) ───────────────────────────────── */
[data-testid="stSidebarContent"] {
    padding-top: 0 !important;
}
[data-testid="stSidebarContent"]::before {
    content: "GENESIX  Ω";
    display:       block;
    font-family:   'Orbitron', monospace !important;
    font-size:     16px;
    font-weight:   800;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    /* Metallic shimmer gradient */
    background: linear-gradient(
        105deg,
        #9CA3AF 0%,
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
    animation: rvn-logo-shimmer 5s linear infinite;
    padding: 24px 16px 6px 16px;
    border-bottom: 1px solid rgba(212,175,55,0.14);
    background-color: rgba(212,175,55,0.04);
    margin-bottom: 0;
}
/* Tagline under the logo */
[data-testid="stSidebarContent"]::after {
    content: "Quantum Trading Intelligence";
    display:       block;
    font-family:   'JetBrains Mono', monospace !important;
    font-size:     8px;
    font-weight:   500;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color:         rgba(100,116,139,0.50);
    padding:       5px 16px 12px 16px;
    border-bottom: 1px solid rgba(212,175,55,0.10);
    margin-bottom: 4px;
}

/* ── Section group titles ──────────────────────────────────────────────── */
[data-testid="stSidebarNav"] details summary {
    font-family:    'JetBrains Mono', monospace !important;
    font-size:      8.5px !important;
    font-weight:    700 !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    color:          rgba(71,85,105,0.85) !important;
    padding:        13px 10px 4px 12px !important;
    margin:         0 !important;
    display:        flex !important;
    align-items:    center !important;
    gap:            8px !important;
    position:       relative !important;
    transition:     color 150ms ease !important;
    cursor:         pointer !important;
}
[data-testid="stSidebarNav"] details summary:hover {
    color: rgba(192,192,192,0.90) !important;
}
/* Decorative accent tick before each section */
[data-testid="stSidebarNav"] details summary::before {
    content:        "";
    display:        inline-block;
    width:          13px;
    min-width:      13px;
    height:         1px;
    background:     #00D4FF;
    border-radius:  1px;
    opacity:        0.45;
    vertical-align: middle;
    transition:     width 200ms ease, opacity 200ms ease;
    flex-shrink:    0;
}
[data-testid="stSidebarNav"] details summary:hover::before {
    width:   18px !important;
    opacity: 0.85 !important;
}

/* ── Per-section accent colours ────────────────────────────────────────── */
/* MARKET INTEL — cyan */
[data-testid="stSidebarNav"] details:has(a[href*="market_intelligence"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="instrument_navigator"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="instrument_detail"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="financial_analysis"]) summary::before {
    background: #00D4FF !important;
}
/* DERIVATIVES — purple */
[data-testid="stSidebarNav"] details:has(a[href*="options_analytics"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="structuring"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="custom_product"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="advanced_exotics"]) summary::before {
    background: #8B5CF6 !important;
}
/* RESEARCH — blue */
[data-testid="stSidebarNav"] details:has(a[href*="equity"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="fixed_income"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="mathematical_foundations"]) summary::before {
    background: #3B82F6 !important;
}
/* RISK & PORTFOLIO — amber */
[data-testid="stSidebarNav"] details:has(a[href*="risk_portfolio"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="vol_calibration"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="portfolio_optimizer"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="ml_pricing"]) summary::before {
    background: #F59E0B !important;
}
/* GENESIX Ω — gold (special treatment) */
[data-testid="stSidebarNav"] details:has(a[href*="genesix"]) summary {
    color:         rgba(212,175,55,0.65) !important;
    font-size:     9px !important;
    letter-spacing: 0.20em !important;
}
[data-testid="stSidebarNav"] details:has(a[href*="genesix"]) summary::before {
    background: #D4AF37 !important;
    opacity:    0.8 !important;
}
[data-testid="stSidebarNav"] details:has(a[href*="genesix"]) summary:hover {
    color: #F5E6A3 !important;
    text-shadow: 0 0 14px rgba(212,175,55,0.30) !important;
}
/* COMPLIANCE — indigo */
[data-testid="stSidebarNav"] details:has(a[href*="esg"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="regulatory"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="documentation"]) summary::before {
    background: #6366F1 !important;
}
/* LEARNING — teal */
[data-testid="stSidebarNav"] details:has(a[href*="mathematical_foundations"]) summary::before {
    background: #14B8A6 !important;
}
/* TRADING DESK — rose */
[data-testid="stSidebarNav"] details:has(a[href*="tradebook"]) summary::before,
[data-testid="stSidebarNav"] details:has(a[href*="admin"]) summary::before {
    background: #F43F5E !important;
}

/* ── Nav item container ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stPageLink"] {
    padding: 0 6px !important;
    margin:  0 !important;
}

/* ── Nav item link ──────────────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    display:         flex !important;
    align-items:     center !important;
    padding:         4px 8px 4px 14px !important;
    border-radius:   4px !important;
    font-family:     'DM Sans', 'Inter', sans-serif !important;
    font-size:       13px !important;
    font-weight:     400 !important;
    color:           rgba(148,163,184,0.72) !important;
    text-decoration: none !important;
    transition:      all 0.13s ease !important;
    border-left:     2px solid transparent !important;
    letter-spacing:  0.013em !important;
    white-space:     nowrap !important;
    overflow:        hidden !important;
    text-overflow:   ellipsis !important;
    margin:          0 !important;
    line-height:     1.45 !important;
}

/* ── Hover state ────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background:       rgba(255,255,255,0.022) !important;
    color:            #E8E8E8 !important;
    border-left-color: rgba(192,192,192,0.25) !important;
    padding-left:     17px !important;
}

/* ── Active / current page — cyan by default ────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] {
    background:  linear-gradient(90deg, rgba(0,212,255,0.10), rgba(0,212,255,0.03) 55%, transparent) !important;
    color:       #00D4FF !important;
    font-weight: 500 !important;
    border-left: 2px solid #00D4FF !important;
    padding-left: 15px !important;
    box-shadow:  inset 0 0 12px rgba(0,212,255,0.04) !important;
}

/* ── Active — section-specific overrides ────────────────────────────────── */
/* Derivatives (purple active) */
[data-testid="stSidebarNav"] details:has(a[href*="options_analytics"]) [data-testid="stPageLink"] a[aria-current="page"],
[data-testid="stSidebarNav"] details:has(a[href*="structuring"]) [data-testid="stPageLink"] a[aria-current="page"] {
    color:       #A78BFA !important;
    border-left-color: #8B5CF6 !important;
    background:  linear-gradient(90deg, rgba(139,92,246,0.10), transparent) !important;
}
/* Risk & Portfolio (amber active) */
[data-testid="stSidebarNav"] details:has(a[href*="risk_portfolio"]) [data-testid="stPageLink"] a[aria-current="page"],
[data-testid="stSidebarNav"] details:has(a[href*="vol_calibration"]) [data-testid="stPageLink"] a[aria-current="page"],
[data-testid="stSidebarNav"] details:has(a[href*="portfolio_optimizer"]) [data-testid="stPageLink"] a[aria-current="page"] {
    color:       #FCD34D !important;
    border-left-color: #F59E0B !important;
    background:  linear-gradient(90deg, rgba(245,158,11,0.09), transparent) !important;
}
/* GENESIX Ω — gold active (all genesix pages) */
[data-testid="stSidebarNav"] details:has(a[href*="genesix"]) [data-testid="stPageLink"] a[aria-current="page"] {
    color:       #F5E6A3 !important;
    font-weight: 600 !important;
    border-left: 2px solid #D4AF37 !important;
    background:  linear-gradient(90deg, rgba(212,175,55,0.12), rgba(212,175,55,0.04) 55%, transparent) !important;
    box-shadow:  inset 0 0 16px rgba(212,175,55,0.05) !important;
    text-shadow: 0 0 12px rgba(212,175,55,0.25) !important;
}

/* ── Gold gradient separator between PORTFOLIO DESK and GENESIX sections ─ */
[data-testid="stSidebarNav"] details:has(a[href*="genesix"]) {
    border-top: 1px solid rgba(212,175,55,0.16) !important;
    padding-top: 4px !important;
    margin-top:  4px !important;
}

/* ── Sidebar scrollbar ──────────────────────────────────────────────────── */
[data-testid="stSidebarContent"]::-webkit-scrollbar        { width: 3px; }
[data-testid="stSidebarContent"]::-webkit-scrollbar-track  { background: transparent; }
[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb  {
    background:    rgba(192,192,192,0.12);
    border-radius: 999px;
}
[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb:hover {
    background: rgba(212,175,55,0.30);
}

/* ── Nav divider (between market data widgets below) ───────────────────── */
.nav-divider {
    height:     1px;
    background: linear-gradient(90deg, transparent, rgba(100,116,139,0.18) 30%, rgba(100,116,139,0.18) 70%, transparent);
    margin:     7px 10px;
}

/* ── LOADING SKELETON ──────────────────────────────────────────────────── */
@keyframes rvn-shimmer{
    0%{background-position:-200% 0}
    100%{background-position:200% 0}}
.rvn-skeleton{
    background:linear-gradient(90deg, rgba(51,65,85,0.1), rgba(51,65,85,0.2), rgba(51,65,85,0.1));
    background-size:200% 100%;animation:rvn-shimmer 1.5s ease-in-out infinite;
    border-radius:var(--radius-xs)}

/* ── LOADING SPINNER ───────────────────────────────────────────────────── */
@keyframes rvn-spin{to{transform:rotate(360deg)}}
.rvn-spinner{width:32px;height:32px;border:2px solid var(--color-border-default);
    border-top-color:var(--color-accent-primary);border-radius:50%;
    animation:rvn-spin 1s linear infinite}

/* ── PROGRESS BAR ──────────────────────────────────────────────────────── */
.rvn-progress{background:rgba(51,65,85,0.2);height:4px;border-radius:2px;overflow:hidden}
.rvn-progress-fill{height:100%;background:linear-gradient(90deg,#7C3AED,#00D9FF);
    border-radius:2px;transition:width 300ms ease-out}

/* ── ACCESSIBILITY: Focus visible ──────────────────────────────────────── */
:focus-visible{outline:2px solid var(--color-accent-primary);outline-offset:2px;border-radius:var(--radius-xs)}

/* ── UTILITY: smooth transitions for statechanges ──────────────────────── */
.rvn-fade-enter{opacity:0;transform:translateY(8px);transition:all 250ms ease}
.rvn-fade-enter-active{opacity:1;transform:translateY(0)}

/* ══════════════════════════════════════════════════════════════════════════
   DENSITY LAYER — maximize usable space, eliminate dead whitespace
   ══════════════════════════════════════════════════════════════════════════ */

/* ── SCROLL FIX ──────────────────────────────────────────────────────────
   stAppViewContainer = scroll container (height fixe via flex, overflow auto).
   stMain = height auto (pas de jail concurrent).
   Le wheel event forwarder JS s'occupe du reste.
   ─────────────────────────────────────────────────────────────────────── */
[data-testid="stAppViewContainer"] {
    overflow-y: auto   !important;
    overflow-x: hidden !important;
}
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlock"] {
    height:     auto    !important;
    min-height: 0       !important;
    max-height: none    !important;
    overflow:   visible !important;
}

/* Main content lateral padding — tighter */
[data-testid="stAppViewContainer"] {
    padding-left:  18px !important;
    padding-right: 18px !important;
}

/* Kill ALL internal block-level vertical gaps — use 8px baseline */
[data-testid="stVerticalBlock"] {
    gap: 0.5rem !important;
}
[data-testid="stVerticalBlockBorderWrapper"] > div {
    gap: 0.5rem !important;
}

/* Column horizontal gap */
[data-testid="stHorizontalBlock"] {
    gap: 0.6rem !important;
}

/* Tab panel: zero padding top, let charts breathe naturally */
[data-testid="stTabsTabPanel"],
div[role="tabpanel"] {
    padding: 0.6rem 0 0 0 !important;
}

/* Tab bar: compact */
[data-testid="stTabs"] > div:first-child {
    gap: 0 !important;
    margin-bottom: 0.25rem !important;
}
button[role="tab"] {
    padding: 6px 14px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: .04em !important;
}

/* Headings: reduce overkill margins */
[data-testid="stMarkdownContainer"] h1 { margin: 0 0 6px 0 !important; }
[data-testid="stMarkdownContainer"] h2 { margin: 4px 0 4px 0 !important; }
[data-testid="stMarkdownContainer"] h3 { margin: 4px 0 4px 0 !important; }
[data-testid="stMarkdownContainer"] h4 { margin: 2px 0 2px 0 !important; }
[data-testid="stMarkdownContainer"] p  { margin: 2px 0 !important; }

/* st.header / st.subheader / st.title */
[data-testid="stHeading"] {
    padding: 0 !important;
    margin: 0 0 4px 0 !important;
    line-height: 1.25 !important;
}

/* Divider: thinner gap */
[data-testid="stDivider"] {
    margin: 6px 0 !important;
}

/* Metric cards: compact vertical padding */
[data-testid="stMetric"] {
    padding: 10px 14px !important;
}
[data-testid="stMetricValue"] {
    font-size: 20px !important;
    line-height: 1.2 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 10px !important;
    margin-bottom: 2px !important;
}
[data-testid="stMetricDelta"] {
    font-size: 11px !important;
    margin-top: 2px !important;
}

/* Expander: tighter */
[data-testid="stExpander"] {
    margin-bottom: 6px !important;
}
[data-testid="stExpanderDetails"] {
    padding: 8px 12px !important;
}

/* Dataframe / table: let it fill container without extra margin */
[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"] {
    width: 100% !important;
}
[data-testid="stDataFrame"] > div {
    width: 100% !important;
}

/* Plotly charts: no extra margins around the iframe */
[data-testid="stPlotlyChart"],
[data-testid="stPlotlyChart"] > div,
[data-testid="stPlotlyChart"] iframe {
    width: 100% !important;
    display: block !important;
}

/* Input widgets: compact */
[data-testid="stSlider"]        { padding: 2px 0 4px 0 !important; }
[data-testid="stSelectbox"]     { margin-bottom: 4px !important; }
[data-testid="stNumberInput"]   { margin-bottom: 4px !important; }
[data-testid="stRadio"]         { margin-bottom: 4px !important; }
[data-testid="stCheckbox"]      { margin-bottom: 2px !important; }
[data-testid="stTextInput"]     { margin-bottom: 4px !important; }

/* Info / warning / success / error alerts: compact */
[data-testid="stAlert"] {
    padding: 8px 12px !important;
    margin: 4px 0 !important;
}

/* st.container with border */
[data-testid="stVerticalBlockBorderWrapper"] {
    padding: 10px !important;
    margin-bottom: 6px !important;
}

/* Spinner text */
[data-testid="stSpinner"] { margin: 6px 0 !important; }

/* Caption text */
[data-testid="stCaptionContainer"] {
    margin: 2px 0 !important;
    font-size: 11px !important;
}

/* Hide empty markdown paragraphs (st.write("")) */
[data-testid="stMarkdownContainer"] p:empty {
    display: none !important;
}

/* Chart height CSS variables for consistent scaling */
:root {
    --ch-full: 520px;    /* full-width chart */
    --ch-half: 440px;    /* 2-col chart */
    --ch-third: 380px;   /* 3-col chart */
    --ch-quarter: 320px; /* 4-col chart */
    --ch-mini: 260px;    /* small/KPI chart */
}
</style>

<!-- FIXED TOPBAR -->
<div class="rh">
  <div class="rh-hamburger" id="rh-hbg" title="Toggle sidebar">
    <span id="hbg-1"></span><span id="hbg-2"></span><span id="hbg-3"></span>
  </div>
    <svg width="30" height="36" viewBox="0 0 40 48" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0">
    <!-- Trunk -->
    <path d="M19 48 Q18.5 42 19 36 Q19.5 42 20 48Z" fill="rgba(0,217,255,0.25)" stroke="#00D9FF" stroke-width="1.3" stroke-linecap="round"/>
    <!-- Leaf 1 — far left (-70°) -->
    <path d="M19 36 C12 37 4 33 3 30 C3.5 27 11 29 19 36Z" fill="rgba(0,217,255,0.10)" stroke="#00D9FF" stroke-width="0.9"/>
    <path d="M19 36 C12 34 7 32 3 30" fill="none" stroke="#00D9FF" stroke-width="1.2" stroke-linecap="round"/>
    <!-- Leaf 2 — mid-left (-45°) -->
    <path d="M19 36 C12 32 6 24 5 20 C8 18 17 23 19 36Z" fill="rgba(0,217,255,0.11)" stroke="#00D9FF" stroke-width="0.9"/>
    <path d="M19 36 C13 29 8 24 5 20" fill="none" stroke="#00D9FF" stroke-width="1.2" stroke-linecap="round"/>
    <!-- Leaf 3 — inner-left (-22°) -->
    <path d="M19 36 C12 29 9 18 12 10 C19 13 21 24 19 36Z" fill="rgba(0,217,255,0.13)" stroke="#00D9FF" stroke-width="0.9"/>
    <path d="M19 36 C15 27 13 18 12 10" fill="none" stroke="#00D9FF" stroke-width="1.3" stroke-linecap="round"/>
    <!-- Leaf 4 — center (0°) -->
    <path d="M19 36 C14 27 14 16 19 7 C24 16 24 27 19 36Z" fill="rgba(0,217,255,0.16)" stroke="#00D9FF" stroke-width="1.0"/>
    <path d="M19 36 C18 27 18 16 19 7" fill="none" stroke="#00D9FF" stroke-width="1.4" stroke-linecap="round"/>
    <!-- Leaf 5 — inner-right (+22°) -->
    <path d="M19 36 C26 29 29 18 26 10 C19 13 17 24 19 36Z" fill="rgba(0,217,255,0.13)" stroke="#00D9FF" stroke-width="0.9"/>
    <path d="M19 36 C23 27 25 18 26 10" fill="none" stroke="#00D9FF" stroke-width="1.3" stroke-linecap="round"/>
    <!-- Leaf 6 — mid-right (+45°) -->
    <path d="M19 36 C26 32 32 24 33 20 C30 18 21 23 19 36Z" fill="rgba(0,217,255,0.11)" stroke="#00D9FF" stroke-width="0.9"/>
    <path d="M19 36 C25 29 30 24 33 20" fill="none" stroke="#00D9FF" stroke-width="1.2" stroke-linecap="round"/>
    <!-- Leaf 7 — far right (+70°) -->
    <path d="M19 36 C26 37 34 33 35 30 C34.5 27 27 29 19 36Z" fill="rgba(0,217,255,0.10)" stroke="#00D9FF" stroke-width="0.9"/>
    <path d="M19 36 C26 34 31 32 35 30" fill="none" stroke="#00D9FF" stroke-width="1.2" stroke-linecap="round"/>
  </svg>
  <span class="rh-logo-text">RAVINALA</span>
  <div class="rh-sep"></div>
  <span class="rh-sub">by TSIVAHINY Matthias</span>
  <div class="rh-spacer"></div>
  <span class="rh-tag rh-tag-green">Quantum Lab</span>
  <span class="rh-tag rh-tag-blue">Cross-Asset v3.0</span>
</div>

<div class="watermark">RAVINALA</div>
<div class="footer-watermark">&#169; 2026 TSIVAHINY Matthias &#183; Ravinala</div>
"""

_HAMBURGER_JS = """
<script>
(function() {
    // Open all nav sections once on load — no polling
    function expandNavOnce(doc) {
        try {
            doc.querySelectorAll('[data-testid="stSidebarNav"] details')
               .forEach(function(d){ d.open = true; });
        } catch(e){}
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function(){
            expandNavOnce(document);
            try { expandNavOnce(window.parent.document); } catch(e){}
        });
    } else {
        expandNavOnce(document);
        try { expandNavOnce(window.parent.document); } catch(e){}
    }

    var _sidebarOpen = true;

    function getNativeToggle(doc) {
        return (
            doc.querySelector('[data-testid="stSidebarCollapseButton"] button') ||
            doc.querySelector('[data-testid="collapsedControl"] button')        ||
            doc.querySelector('button[aria-label="Close sidebar"]')            ||
            doc.querySelector('button[aria-label="Open sidebar"]')             ||
            doc.querySelector('section[data-testid="stSidebar"] button')
        );
    }

    function animateHamburger(doc, closing) {
        var l1 = doc.getElementById('hbg-1');
        var l2 = doc.getElementById('hbg-2');
        var l3 = doc.getElementById('hbg-3');
        if (!l1) return;
        if (closing) {
            l1.style.transform  = 'translateY(6px) rotate(45deg)';
            l1.style.background = '#a5b4fc';
            l2.style.opacity    = '0';
            l2.style.transform  = 'scaleX(0)';
            l3.style.transform  = 'translateY(-6px) rotate(-45deg)';
            l3.style.background = '#a5b4fc';
        } else {
            l1.style.transform  = 'none';
            l1.style.background = 'rgba(255,255,255,0.55)';
            l2.style.opacity    = '1';
            l2.style.transform  = 'none';
            l3.style.transform  = 'none';
            l3.style.background = 'rgba(255,255,255,0.55)';
        }
    }

    function attachHamburger() {
        var doc = window.parent.document;
        var hbg = doc.getElementById('rh-hbg');
        if (!hbg) { setTimeout(attachHamburger, 300); return; }

        // Replace node to wipe any old listeners
        var clone = hbg.cloneNode(true);
        hbg.parentNode.replaceChild(clone, hbg);

        clone.addEventListener('click', function() {
            var btn = getNativeToggle(doc);
            if (btn) {
                btn.click();
                _sidebarOpen = !_sidebarOpen;
                animateHamburger(doc, !_sidebarOpen);
            }
        });
    }

    attachHamburger();

    // ── SCROLL FIX ───────────────────────────────────────────────────────
    // setInterval polls until stAppViewContainer appears, then locks in.
    // setProperty('overflow-y','scroll','important') beats all Streamlit CSS.
    var _scrollMoAttached = false;
    var _scrollWheelAttached = false;

    function doScrollFix() {
        try {
            var doc = window.parent.document;
            var win = window.parent;
            var v = doc.querySelector('[data-testid="stAppViewContainer"]');
            if (!v) return false;

            v.style.setProperty('overflow-y', 'scroll', 'important');
            v.style.setProperty('overflow-x', 'hidden', 'important');
            win.__rvn_fix_count = (win.__rvn_fix_count || 0) + 1;

            // MutationObserver: re-apply after any React re-render (once)
            if (!_scrollMoAttached) {
                var app = doc.querySelector('[data-testid="stApp"]');
                if (app) {
                    _scrollMoAttached = true;
                    new MutationObserver(function() {
                        try {
                            var vc = doc.querySelector('[data-testid="stAppViewContainer"]');
                            if (vc) {
                                vc.style.setProperty('overflow-y', 'scroll', 'important');
                                vc.style.setProperty('overflow-x', 'hidden', 'important');
                            }
                        } catch(ex) {}
                    }).observe(app, { childList: true, subtree: true,
                                      attributes: true, attributeFilter: ['class'] });
                }
            }

            // Wheel forwarder: only if a nested element doesn't already scroll (once)
            if (!_scrollWheelAttached) {
                _scrollWheelAttached = true;
                doc.addEventListener('wheel', function(e) {
                    var vc = doc.querySelector('[data-testid="stAppViewContainer"]');
                    if (!vc) return;
                    var el = e.target;
                    while (el && el !== vc) {
                        try {
                            var oy = win.getComputedStyle(el).overflowY;
                            if ((oy === 'auto' || oy === 'scroll') &&
                                el.scrollHeight > el.clientHeight + 2) { return; }
                        } catch(ex) {}
                        el = el.parentElement;
                    }
                    e.preventDefault();
                    vc.scrollTop += e.deltaY;
                }, { passive: false, capture: true });
            }

            return true;
        } catch(e) { return false; }
    }

    // Poll every 300ms until the element is found, then stop
    var _scrollPollCount = 0;
    var _scrollInterval = setInterval(function() {
        _scrollPollCount++;
        if (doScrollFix() || _scrollPollCount > 40) {
            clearInterval(_scrollInterval);
        }
    }, 300);

})();
</script>
"""


def _market_state(local_dt, open_hm, close_hm, lunch_start=None, lunch_end=None):
    current = local_dt.hour * 60 + local_dt.minute
    open_min = open_hm[0] * 60 + open_hm[1]
    close_min = close_hm[0] * 60 + close_hm[1]

    if current < open_min or current >= close_min:
        return "closed", "Fermé"

    if lunch_start and lunch_end:
        lunch_s = lunch_start[0] * 60 + lunch_start[1]
        lunch_e = lunch_end[0] * 60 + lunch_end[1]
        if lunch_s <= current < lunch_e:
            return "mid", "Mi-séance"

    if current < open_min + 60 or current >= close_min - 60:
        return "mid", "Mi-séance"

    return "open", "Ouvert"


@st.cache_data(ttl=60)
def _get_header_market_overview():
    overview = {}
    try:
        overview = fetch_market_overview() or {}
    except Exception:
        overview = {}

    extra_tickers = {
        "^HSI": "Hang Seng",
        "^AXJO": "ASX 200",
        "^GSPTSE": "S&P/TSX Composite",
    }

    missing = [ticker for ticker in extra_tickers if ticker not in overview]
    if missing:
        try:
            import yfinance as yf

            raw = yf.download(missing, period="5d", progress=False, auto_adjust=True)
            close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw

            for ticker in missing:
                try:
                    series = close[ticker].dropna() if isinstance(close, pd.DataFrame) else close.dropna()
                    if len(series) >= 2:
                        price = float(series.iloc[-1])
                        prev = float(series.iloc[-2])
                        change_pct = (price - prev) / prev * 100
                        overview[ticker] = {
                            "name": extra_tickers[ticker],
                            "price": price,
                            "change_pct": change_pct,
                        }
                except Exception:
                    continue
        except Exception:
            pass

    return overview


@st.fragment(run_every="5m")
def _render_global_market_header():
    overview = _get_header_market_overview()
    now_utc = datetime.now(ZoneInfo("UTC"))

    market_specs = [
        {"venue": "NYSE", "city": "New York", "tz": "America/New_York", "open": (9, 30), "close": (16, 0), "ticker": "^GSPC", "fallback_name": "S&P 500"},
        {"venue": "NASDAQ", "city": "New York", "tz": "America/New_York", "open": (9, 30), "close": (16, 0), "ticker": "^NDX", "fallback_name": "Nasdaq 100"},
        {"venue": "LSE", "city": "London", "tz": "Europe/London", "open": (8, 0), "close": (16, 30), "ticker": "^FTSE", "fallback_name": "FTSE 100"},
        {"venue": "EUREX", "city": "Frankfurt", "tz": "Europe/Berlin", "open": (9, 0), "close": (17, 30), "ticker": "^STOXX50E", "fallback_name": "Euro Stoxx 50"},
        {"venue": "JPX", "city": "Tokyo", "tz": "Asia/Tokyo", "open": (9, 0), "close": (15, 0), "lunch_start": (11, 30), "lunch_end": (12, 30), "ticker": "^N225", "fallback_name": "Nikkei 225"},
        {"venue": "HKEX", "city": "Hong Kong", "tz": "Asia/Hong_Kong", "open": (9, 30), "close": (16, 0), "lunch_start": (12, 0), "lunch_end": (13, 0), "ticker": "^HSI", "fallback_name": "Hang Seng"},
        {"venue": "ASX", "city": "Sydney", "tz": "Australia/Sydney", "open": (10, 0), "close": (16, 0), "ticker": "^AXJO", "fallback_name": "ASX 200"},
        {"venue": "TSX", "city": "Toronto", "tz": "America/Toronto", "open": (9, 30), "close": (16, 0), "ticker": "^GSPTSE", "fallback_name": "S&P/TSX"},
    ]

    dot_colors = {"open": "#10B981", "mid": "#F59E0B", "closed": "#EF4444"}

    cards = []
    for spec in market_specs:
        local_now = now_utc.astimezone(ZoneInfo(spec["tz"]))
        state_key, state_label = _market_state(
            local_now,
            spec["open"],
            spec["close"],
            spec.get("lunch_start"),
            spec.get("lunch_end"),
        )

        market_data = overview.get(spec["ticker"], {})
        index_name = market_data.get("name", spec["fallback_name"])
        price = market_data.get("price")
        change_pct = market_data.get("change_pct")

        if isinstance(price, (int, float)):
            price_fmt = f"{price:,.2f}" if abs(price) >= 10 else f"{price:,.4f}"
        else:
            price_fmt = "N/A"

        if isinstance(change_pct, (int, float)):
            change_color = "#10B981" if change_pct >= 0 else "#EF4444"
            change_fmt = f"{change_pct:+.2f}%"
        else:
            change_color = "#94A3B8"
            change_fmt = "--"

        cards.append(
            (
                f'<div class="rvn-mkt-card">'
                f'<div class="rvn-mkt-top">'
                f'<span class="rvn-mkt-venue">{spec["venue"]}</span>'
                f'<span class="rvn-mkt-time">{local_now.strftime("%H:%M")}</span>'
                f'</div>'
                f'<div class="rvn-mkt-index">{index_name}</div>'
                f'<div class="rvn-mkt-level">{price_fmt}</div>'
                f'<div class="rvn-mkt-status-wrap">'
                f'<span class="rvn-mkt-dot" style="background:{dot_colors[state_key]}"></span>'
                f'<span class="rvn-mkt-status">{state_label}</span>'
                f'<span class="rvn-mkt-change" style="color:{change_color}">{change_fmt}</span>'
                f'</div>'
                f'</div>'
            )
        )

    strip_html = (
        '<div class="rvn-global-market-strip">'
        '<div class="rvn-global-market-meta">LIVE • 5min</div>'
        '<div class="rvn-global-market-track">'
        f'{"".join(cards)}'
        '</div>'
        '</div>'
    )

    st.markdown(strip_html, unsafe_allow_html=True)


def _render_page_header(icon: str, title: str, subtitle: str = "", badge: str = "Desk"):
    """Render a page header. `icon` can be a text label (e.g. 'PC') or SVG snippet."""
    subtitle_html = f'<p class="rvn-ph-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="rvn-ph">
            <div class="rvn-ph-icon">{icon}</div>
            <div style="flex:1">
                <h2 class="rvn-ph-title">{title}</h2>
                {subtitle_html}
            </div>
            <div class="rvn-badge rvn-badge-g">{badge}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_nav(brakata_available: bool = False) -> None:
    """Render categorized sidebar navigation using st.page_link."""

    def _section(label: str) -> None:
        st.sidebar.markdown(f'<div class="nav-section-title">{label}</div>', unsafe_allow_html=True)

    st.sidebar.page_link("pages/home.py", label="Home")

    _section("MARKET")
    st.sidebar.page_link("pages/market_intelligence.py",     label="Market Intelligence")
    st.sidebar.page_link("pages/instrument_navigator.py",    label="Instrument Navigator")
    st.sidebar.page_link("pages/instrument_detail.py",       label="Instrument Detail")
    st.sidebar.page_link("pages/financial_analysis.py",      label="Financial Analysis")

    _section("DERIVATIVES & STRUCTURING")
    st.sidebar.page_link("pages/options_analytics.py",       label="Options Analytics")
    st.sidebar.page_link("pages/structuring.py",             label="Structuring Suite")
    st.sidebar.page_link("pages/custom_product.py",          label="Custom Product")
    st.sidebar.page_link("pages/advanced_exotics.py",        label="Advanced Exotics")
    st.sidebar.page_link("pages/vol_calibration_page.py",    label="Vol Calibration")
    st.sidebar.page_link("pages/museum_exotics.py",          label="Museum of Exotics")
    st.sidebar.page_link("pages/sandbox.py",                 label="The Sandbox")

    _section("RISK & PORTFOLIO")
    st.sidebar.page_link("pages/risk_portfolio_suite.py",    label="Risk & Portfolio Suite")
    st.sidebar.page_link("pages/portfolio_optimizer.py",     label="Portfolio Optimizer")
    st.sidebar.page_link("pages/ml_pricing_page.py",         label="ML Pricing")

    _section("RESEARCH & EDUCATION")
    st.sidebar.page_link("pages/equity_research_workbench.py", label="Equity Research Workbench")
    st.sidebar.page_link("pages/equity_research.py",         label="Equity Research")
    st.sidebar.page_link("pages/fixed_income.py",            label="Fixed Income")
    st.sidebar.page_link("pages/mathematical_foundations.py", label="Mathematical Foundations")

    _section("TAX LAB Ω")
    st.sidebar.page_link("pages/tax_lab.py",                 label="TAX LAB Ω — Full Suite")

    _section("GENESIX Ω")
    st.sidebar.page_link("pages/genesix_hub.py",             label="GenesiX Hub")
    st.sidebar.page_link("pages/genesix_intelligence.py",    label="Signal Intelligence")
    st.sidebar.page_link("pages/performance_tracking.py",    label="Performance Tracking")
    st.sidebar.page_link("pages/risk_engine_dashboard.py",   label="Risk Engine Dashboard")
    st.sidebar.page_link("pages/backtest_results.py",        label="Backtest Results")
    st.sidebar.page_link("pages/physics_demo.py",            label="Physics Lab")

    _section("COMPLIANCE")
    st.sidebar.page_link("pages/esg.py",                     label="ESG & Green Lab")
    st.sidebar.page_link("pages/regulatory_capital.py",      label="Regulatory Capital")
    st.sidebar.page_link("pages/documentation.py",           label="Report Generator")
    st.sidebar.page_link("pages/legal.py",                   label="Legal & Compliance")

    if brakata_available:
        _section("TRADING DESK")
        st.sidebar.page_link("pages/tradebook.py",           label="Trade Book")
        st.sidebar.page_link("pages/admin.py",               label="Admin Panel")


_SCROLL_FIX_IFRAME = """
<iframe srcdoc='&lt;script&gt;
(function() {
  function fix() {
    try {
      var vc = window.parent.document.querySelector("[data-testid=\\"stAppViewContainer\\"]");
      if (!vc) { setTimeout(fix, 200); return; }
      vc.style.setProperty("overflow-y","scroll","important");
      vc.style.setProperty("overflow-x","hidden","important");
      window.parent.__rvn_fix_count = (window.parent.__rvn_fix_count||0)+1;
      var app = window.parent.document.querySelector("[data-testid=\\"stApp\\"]");
      if (app && !window.parent.__rvn_mo) {
        window.parent.__rvn_mo = new window.parent.MutationObserver(function(){
          var v=window.parent.document.querySelector("[data-testid=\\"stAppViewContainer\\"]");
          if(v){ v.style.setProperty("overflow-y","scroll","important"); }
        });
        window.parent.__rvn_mo.observe(app,{childList:true,subtree:true,attributes:true,attributeFilter:["class"]});
      }
    } catch(e) {}
  }
  fix(); setTimeout(fix,100); setTimeout(fix,400); setTimeout(fix,1000);
})();
&lt;/script&gt;'
style="display:none;width:0;height:0;border:none;position:absolute;"
></iframe>
"""

def inject_shared_css():
    """Inject CSS, topbar HTML, watermark, and hamburger JS into the page."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(_SCROLL_FIX_IFRAME, unsafe_allow_html=True)
    components.html(_HAMBURGER_JS, height=1, scrolling=False)


# ── Chart height helper ───────────────────────────────────────────────────
# Use this everywhere instead of hardcoded integers.
# cols = number of st.columns the chart sits in (1 = full width)
_CH = {1: 520, 2: 440, 3: 380, 4: 320, 0: 260}

def chart_h(cols: int = 1) -> int:
    """Return a consistent chart height for a given column count."""
    return _CH.get(cols, 440)


@dataclass(frozen=True)
class SidebarMarketContext:
    """Normalized market parameters shared across pricing and analytics pages."""

    spot: float
    volatility: float
    rate: float
    carry: float
    maturity: float
    credit_spread: float
    n_assets: int
    target_corr: float
    currency: str
    currency_symbol: str
    rate_source: str
    rate_mode: str
    rate_as_of_utc: str


def _ensure_market_sidebar_defaults() -> float:
    """Initialize shared sidebar defaults once so every page reads the same baseline."""

    default_rate_sidebar = float(st.session_state.setdefault("rate_sidebar", RISK_FREE_RATE))
    st.session_state.setdefault(
        "rate_sidebar_source",
        f"{RISK_FREE_RATE_SOURCE} (shared baseline)",
    )
    st.session_state.setdefault("rate_sidebar_mode", "baseline_default")
    st.session_state.setdefault("rate_sidebar_as_of_utc", RISK_FREE_RATE_LAST_UPDATED)
    st.session_state.setdefault("carry_sidebar", default_rate_sidebar)
    st.session_state.setdefault("curr_sidebar", "USD")
    st.session_state.setdefault("rate_sidebar_currency", st.session_state.get("curr_sidebar", "USD"))
    st.session_state.setdefault("rate_sidebar_quote_rate", default_rate_sidebar)
    st.session_state.setdefault("rate_sidebar_quote_initialized", False)
    st.session_state.setdefault("spot_sidebar", 100.0)
    st.session_state.setdefault("vol_sidebar", 0.20)
    st.session_state.setdefault("credit_sidebar", 0.01)
    st.session_state.setdefault("mat_sidebar", 2.0)
    st.session_state.setdefault("n_assets_sidebar", 3)
    st.session_state.setdefault("target_corr_sidebar", 0.5)
    return default_rate_sidebar


def get_sidebar_market_context() -> SidebarMarketContext:
    """Return a canonical snapshot of market sidebar parameters for downstream pages."""

    default_rate_sidebar = _ensure_market_sidebar_defaults()
    currency = str(st.session_state.get("curr_sidebar", "USD")).upper()
    return SidebarMarketContext(
        spot=float(st.session_state.get("spot_sidebar", 100.0)),
        volatility=float(st.session_state.get("vol_sidebar", 0.20)),
        rate=float(st.session_state.get("rate_sidebar", default_rate_sidebar)),
        carry=float(st.session_state.get("carry_sidebar", default_rate_sidebar)),
        maturity=float(st.session_state.get("mat_sidebar", 2.0)),
        credit_spread=float(st.session_state.get("credit_sidebar", 0.01)),
        n_assets=int(st.session_state.get("n_assets_sidebar", 3)),
        target_corr=float(st.session_state.get("target_corr_sidebar", 0.5)),
        currency=currency,
        currency_symbol={"EUR": "EUR", "USD": "$", "GBP": "GBP", "JPY": "JPY"}.get(currency, "$"),
        rate_source=str(
            st.session_state.get(
                "rate_sidebar_source",
                f"{RISK_FREE_RATE_SOURCE} (shared baseline)",
            )
        ),
        rate_mode=str(st.session_state.get("rate_sidebar_mode", "baseline_default")),
        rate_as_of_utc=str(st.session_state.get("rate_sidebar_as_of_utc", RISK_FREE_RATE_LAST_UPDATED)),
    )


def _sync_sidebar_rate_quote(
    currency: str,
    *,
    dividend_yield: float | None = None,
    force: bool = False,
):
    """Synchronize sidebar rate state from the structured market-data quote."""

    ccy = (currency or "USD").upper()
    if not force and st.session_state.get("rate_sidebar_currency") == ccy:
        return None

    quote = fetch_risk_free_rate_quote(ccy)
    st.session_state["rate_sidebar"] = float(quote.rate)
    st.session_state["rate_sidebar_source"] = quote.source_label
    st.session_state["rate_sidebar_mode"] = quote.mode
    st.session_state["rate_sidebar_as_of_utc"] = quote.as_of_utc
    st.session_state["rate_sidebar_currency"] = ccy
    st.session_state["rate_sidebar_quote_rate"] = float(quote.rate)
    st.session_state["rate_sidebar_quote_initialized"] = True

    div_yield = float(
        dividend_yield
        if dividend_yield is not None
        else st.session_state.get("mkt_loaded", {}).get("div_yield") or 0.0
    )
    st.session_state["carry_sidebar"] = round(max(0.0, float(quote.rate) - max(div_yield, 0.0)), 4)
    return quote


def render_sidebar_market_data():
    """Render all sidebar market data expanders (Load Ticker, Spot Prices, etc.)."""
    # Initialize shared-rate defaults once so all pages start from the same baseline.
    default_rate_sidebar = _ensure_market_sidebar_defaults()
    _sync_sidebar_rate_quote(
        st.session_state.get("curr_sidebar", "USD"),
        force=not bool(st.session_state.get("rate_sidebar_quote_initialized")),
    )

    st.sidebar.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="nav-section-title">LIVE DATA</div>', unsafe_allow_html=True)

    with st.sidebar.expander("Load Ticker", expanded=False):
        ticker_input = st.text_input(
            "Ticker Symbol",
            value=st.session_state.get("mkt_ticker_val", ""),
            placeholder="AAPL, SPY, ^STOXX50E",
            key="mkt_ticker_input",
        )
        use_iv = st.checkbox("Use Implied Vol (vs Hist)", value=True, key="use_iv_toggle")
        load_btn = st.button("Load Market Data", key="load_mkt_btn", use_container_width=True)

        if load_btn and ticker_input.strip():
            with st.spinner(f"Fetching {ticker_input.upper()}"):
                result = fetch_spot_vol_div(ticker_input)

            if result["error"]:
                st.error(result["error"])
            else:
                st.session_state["spot_sidebar"] = result["spot"]

                vol_to_use = result["hist_vol"]
                if use_iv:
                    iv = fetch_atm_implied_vol(ticker_input)
                    if iv:
                        vol_to_use = iv
                st.session_state["vol_sidebar"] = round(vol_to_use, 4)

                curr_now = st.session_state.get("curr_sidebar", "USD")
                rfr_quote = _sync_sidebar_rate_quote(
                    curr_now,
                    dividend_yield=result["div_yield"],
                    force=True,
                )
                if rfr_quote is None:
                    rfr_quote = fetch_risk_free_rate_quote(curr_now)
                rfr = float(rfr_quote.rate)
                rfr_src = rfr_quote.source_label
                st.session_state["rate_sidebar"] = rfr
                st.session_state["rate_sidebar_source"] = rfr_quote.source_label
                st.session_state["rate_sidebar_mode"] = rfr_quote.mode
                st.session_state["rate_sidebar_as_of_utc"] = rfr_quote.as_of_utc

                q = result["div_yield"]
                st.session_state["carry_sidebar"] = round(max(0.0, rfr - q), 4)

                st.session_state["mkt_loaded"] = result
                st.session_state["mkt_loaded"]["rfr_src"] = rfr_src
                st.session_state["mkt_loaded"]["rfr_mode"] = rfr_quote.mode
                st.session_state["mkt_loaded"]["rfr_as_of_utc"] = rfr_quote.as_of_utc
                st.session_state["mkt_ticker_val"] = ticker_input.upper()

                st.success(f"{result['name']} loaded")
                st.caption(
                    f"Spot **{result['spot']}** | Vol **{vol_to_use*100:.1f}%** "
                    f"| Rate **{rfr*100:.2f}%** ({rfr_src}, mode: {rfr_quote.mode})"
                )

        if "mkt_loaded" in st.session_state:
            loaded = st.session_state["mkt_loaded"]
            st.markdown(
                f"<div style='font-size:10px;color:var(--color-text-disabled);margin-top:6px'>"
                f"Last: <b style='color:var(--color-accent-primary)'>{st.session_state.get('mkt_ticker_val','')}</b> "
                f"&#8212; {loaded['name']}</div>",
                unsafe_allow_html=True,
            )

    st.sidebar.markdown('<div class="nav-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="nav-section-title">MARKET PARAMETERS</div>', unsafe_allow_html=True)

    with st.sidebar.expander("Spot Prices & Volatility", expanded=True):
        col1, col2 = st.sidebar.columns(2)
        with col1:
            spot_price = st.number_input("Spot (S)", value=100.0, step=0.1, min_value=0.1, key="spot_sidebar")
        with col2:
            volatility = st.number_input("Vol (sigma)", value=0.20, step=0.01, min_value=0.01, max_value=2.0, key="vol_sidebar")

        st.caption("Adjust underlying and implied volatility")

    with st.sidebar.expander("Interest Rates & Carry", expanded=False):
        top1, top2 = st.sidebar.columns([2, 1])
        with top1:
            currency = st.sidebar.selectbox("Currency", ["EUR", "USD", "GBP", "JPY"], key="curr_sidebar")
        with top2:
            refresh_rate = st.button("Sync Rate", key="sync_rate_sidebar_btn", use_container_width=True)

        current_div_yield = float(st.session_state.get("mkt_loaded", {}).get("div_yield") or 0.0)
        if refresh_rate or st.session_state.get("rate_sidebar_currency") != currency:
            _sync_sidebar_rate_quote(currency, dividend_yield=current_div_yield, force=True)

        col1, col2 = st.sidebar.columns(2)
        with col1:
            rate = st.number_input(
                "Risk-Free Rate",
                value=float(st.session_state.get("rate_sidebar", default_rate_sidebar)),
                step=0.001,
                min_value=-0.05,
                max_value=0.20,
                key="rate_sidebar",
            )
        with col2:
            carry = st.number_input(
                "Carry (b)",
                value=float(st.session_state.get("carry_sidebar", default_rate_sidebar)),
                step=0.001,
                min_value=-0.10,
                max_value=0.20,
                key="carry_sidebar",
            )

        quote_rate = float(st.session_state.get("rate_sidebar_quote_rate", default_rate_sidebar))
        quote_source = st.session_state.get("rate_sidebar_source", f"{RISK_FREE_RATE_SOURCE} (shared baseline)")
        quote_mode = st.session_state.get("rate_sidebar_mode", "baseline_default")
        quote_as_of = st.session_state.get("rate_sidebar_as_of_utc", RISK_FREE_RATE_LAST_UPDATED)
        if abs(float(rate) - quote_rate) > 1e-12:
            st.caption(
                f"Manual override active. Quote: {quote_rate*100:.2f}% "
                f"from {quote_source} ({quote_mode}, {quote_as_of})"
            )
        else:
            st.caption(f"Quote: {quote_source} ({quote_mode}, {quote_as_of})")

    with st.sidebar.expander("Funding & Credit", expanded=False):
        col1, col2 = st.sidebar.columns(2)
        with col1:
            credit_spread = st.number_input("Issuer Spread (bps)", value=100, step=10, min_value=0, max_value=1000, key="credit_sidebar") / 10000
        with col2:
            maturity = st.number_input("Maturity (Y)", value=2.0, step=0.5, min_value=0.25, max_value=10.0, key="mat_sidebar")

    with st.sidebar.expander("Multi-Asset Correlation", expanded=False):
        n_assets = st.sidebar.number_input("Assets", value=3, min_value=2, max_value=10, key="n_assets_sidebar")
        target_corr = st.sidebar.slider("Target Correlation", 0.0, 1.0, 0.5, key="target_corr_sidebar")
        corr_matrix = utils.create_correlation_matrix(n_assets, target_corr)
        st.sidebar.success(f"{n_assets}x{n_assets} correlation matrix created")

    CURRENCY_SYMBOL = {"EUR": "EUR", "USD": "$", "GBP": "GBP", "JPY": "JPY"}.get(
        st.session_state.get("curr_sidebar", "USD"), "$"
    )

    st.sidebar.divider()
    st.sidebar.markdown('<div class="nav-section-title">DASHBOARD</div>', unsafe_allow_html=True)
    st.sidebar.metric("Spot Price", f"{CURRENCY_SYMBOL} {st.session_state.get('spot_sidebar', 100.0):.2f}")
    st.sidebar.metric("Volatility", f"{st.session_state.get('vol_sidebar', 0.20)*100:.2f}%")
    st.sidebar.metric("Risk-Free Rate", f"{st.session_state.get('rate_sidebar', RISK_FREE_RATE)*100:.3f}%")
    st.sidebar.caption(
        "Rate source: "
        f"{st.session_state.get('rate_sidebar_source', f'{RISK_FREE_RATE_SOURCE} (shared baseline)')}"
    )
    st.sidebar.caption(
        "Rate mode/as-of: "
        f"{st.session_state.get('rate_sidebar_mode', 'baseline_default')} / "
        f"{st.session_state.get('rate_sidebar_as_of_utc', RISK_FREE_RATE_LAST_UPDATED)}"
    )
    st.sidebar.metric("Maturity", f"{st.session_state.get('mat_sidebar', 2.0):.2f} years")
