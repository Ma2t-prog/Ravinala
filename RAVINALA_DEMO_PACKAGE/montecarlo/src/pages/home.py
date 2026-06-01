"""
Home — GENESIX Ω Landing Page
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_global_market_header

import streamlit as st
from datetime import datetime

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.home-hero {
    text-align: center;
    padding: 48px 24px 32px;
}
.home-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: clamp(28px, 4vw, 48px);
    font-weight: 700;
    letter-spacing: 0.08em;
    background: linear-gradient(135deg, #E8E8E8 0%, #D4AF37 50%, #C0C0C0 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 10px 0;
}
.home-omega {
    color: #D4AF37 !important;
    -webkit-text-fill-color: #D4AF37 !important;
}
.home-tagline {
    font-size: 13px;
    font-weight: 400;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: rgba(148, 163, 184, 0.60);
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 32px;
}
.home-divider {
    width: 160px; height: 1px; margin: 0 auto 36px;
    background: linear-gradient(90deg, transparent, #D4AF37, transparent);
}
.module-card {
    background: linear-gradient(135deg, rgba(19,24,35,0.7), rgba(15,18,24,0.8));
    border: 1px solid rgba(51,65,85,0.35);
    border-top: 1px solid rgba(192,192,192,0.10);
    border-radius: 10px;
    padding: 18px 20px;
    height: 100%;
    transition: all 160ms ease;
    cursor: default;
}
.module-card:hover {
    border-color: rgba(212,175,55,0.25);
    background: linear-gradient(135deg, rgba(22,28,42,0.85), rgba(18,22,32,0.9));
    transform: translateY(-1px);
    box-shadow: 0 4px 20px rgba(212,175,55,0.06);
}
.module-card-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px; font-weight: 700;
    letter-spacing: 0.16em; text-transform: uppercase;
    margin-bottom: 6px;
}
.module-card-title {
    font-size: 14px; font-weight: 600;
    color: #E0E0E0; margin-bottom: 6px;
    letter-spacing: 0.01em;
}
.module-card-desc {
    font-size: 11.5px;
    color: rgba(148,163,184,0.60);
    line-height: 1.5;
}
.stat-block {
    background: rgba(15,18,24,0.6);
    border: 1px solid rgba(51,65,85,0.25);
    border-radius: 8px;
    padding: 14px 18px;
    text-align: center;
}
.stat-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 22px; font-weight: 700;
    background: linear-gradient(135deg, #C0C0C0, #D4AF37);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}
.stat-label {
    font-size: 10px; letter-spacing: 0.12em;
    text-transform: uppercase; color: rgba(148,163,184,0.45);
    font-family: 'JetBrains Mono', monospace;
    margin-top: 3px;
}
.section-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px; font-weight: 700;
    letter-spacing: 0.18em; text-transform: uppercase;
    color: rgba(192,192,192,0.40);
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(51,65,85,0.20);
    margin-bottom: 14px;
}
</style>
""", unsafe_allow_html=True)

# ── HERO ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="home-hero">
    <div class="home-title">GENESIX <span class="home-omega">Ω</span></div>
    <div class="home-tagline">Quantum Trading Intelligence Platform</div>
    <div class="home-divider"></div>
</div>
""", unsafe_allow_html=True)

# ── STATS BAR ────────────────────────────────────────────────────────────────
s1, s2, s3, s4, s5, s6 = st.columns(6)
stats = [
    ("32", "Modules"),
    ("15+", "Pays fiscaux"),
    ("500+", "Instruments"),
    ("12", "Modèles quant"),
    ("3", "Moteurs ML"),
    ("Real-time", "Market data"),
]
for col, (num, label) in zip([s1,s2,s3,s4,s5,s6], stats):
    col.markdown(f"""
    <div class="stat-block">
        <div class="stat-num">{num}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── MODULE GRID ───────────────────────────────────────────────────────────────
MODULES = [
    {
        "section": "MARKET INTELLIGENCE",
        "color": "#00D4FF",
        "items": [
            ("Market Intelligence",  "Live market, macro, news & alternative data hub"),
            ("Instrument Navigator", "Search, screening, asset classes & ETF explorer"),
            ("Instrument Detail",    "Deep-dive sur un instrument spécifique"),
            ("Financial Analysis",   "Analyse financière avancée"),
        ]
    },
    {
        "section": "DERIVATIVES & STRUCTURING",
        "color": "#A855F7",
        "items": [
            ("Options Analytics",    "Pricing, strategy lab, Greeks & scenario matrix"),
            ("Structuring Suite",    "Produits structurés sur mesure"),
            ("Advanced Exotics",     "Barrier, Asian, Lookback, Rainbow, Cliquets"),
            ("Vol Calibration",      "SABR, SVI, Heston, Dupire, GARCH, HAR-RV"),
        ]
    },
    {
        "section": "RISK & PORTFOLIO",
        "color": "#F59E0B",
        "items": [
            ("Risk & Portfolio Suite","VaR, positions, hedging, backtesting, P&L attribution"),
            ("Portfolio Optimizer",   "Mean-variance, Black-Litterman, HRP"),
            ("TAX LAB Ω",            "Optimisation fiscale multi-juridictionnelle"),
            ("Tradebook",            "Carnet d'ordres et historique de trading"),
        ]
    },
    {
        "section": "RESEARCH & EDUCATION",
        "color": "#3B82F6",
        "items": [
            ("Equity Research Workbench", "DCF, Monte Carlo, multiples, santé financière"),
            ("Equity Research",           "Fondamentaux, scoring, momentum"),
            ("Fixed Income",              "Duration, convexité, courbes, spreads"),
            ("Mathematical Foundations",  "Educational hub, théorie quantitative, probabilités"),
        ]
    },
    {
        "section": "GENESIX Ω SUITE",
        "color": "#D4AF37",
        "items": [
            ("GenesiX Hub",           "Portfolio, risk, ML, market intel — suite unifiée"),
            ("GenesiX Intelligence",  "Détection de signaux, régimes et alertes"),
            ("Performance Tracking",  "Suivi de performance du portefeuille"),
            ("Risk Engine Dashboard", "Monitoring du moteur de risque"),
        ]
    },
    {
        "section": "QUANTITATIVE TOOLS",
        "color": "#10B981",
        "items": [
            ("ML Pricing",        "Neural nets, XGBoost, random forests sur options"),
            ("Museum Exotics",    "Collection de payoffs exotiques historiques"),
            ("Sandbox",           "Environnement de test libre"),
            ("Physics Demo",      "Modèles physiques appliqués à la finance"),
        ]
    },
    {
        "section": "COMPLIANCE & OPERATIONS",
        "color": "#94A3B8",
        "items": [
            ("Backtest Results",    "Historique des backtests et résultats"),
            ("ESG",                 "Environmental, Social & Governance metrics"),
            ("Regulatory Capital",  "Calcul de capital réglementaire"),
            ("Custom Product",      "Création de produits personnalisés"),
        ]
    },
    {
        "section": "DOCUMENTATION & ADMIN",
        "color": "#64748B",
        "items": [
            ("Documentation",    "Guides, API reference et tutoriels"),
            ("Legal",            "Mentions légales et disclaimers"),
            ("Admin",            "Administration et configuration"),
        ]
    },
]

for mod in MODULES:
    st.markdown(f'<p class="section-title">{mod["section"]}</p>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, (title, desc) in enumerate(mod["items"]):
        with cols[i]:
            st.markdown(f"""
            <div class="module-card">
                <div class="module-card-label" style="color:{mod['color']}80;">{mod['section']}</div>
                <div class="module-card-title">{title}</div>
                <div class="module-card-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;padding:24px 0 8px;border-top:1px solid rgba(51,65,85,0.15);margin-top:8px;">
    <span style="font-family:'JetBrains Mono',monospace;font-size:10px;
                 color:rgba(148,163,184,0.30);letter-spacing:0.12em;">
        GENESIX Ω · TSIVAHINY Matthias · {datetime.now().year} · Quantum Trading Intelligence
    </span>
</div>
""", unsafe_allow_html=True)
