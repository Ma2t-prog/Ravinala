"""
TAX LAB Ω — Global Multi-Jurisdictional Tax Optimization Engine
Tax-Loss Harvesting · Envelope Optimizer · Estate Planning · Multi-Jurisdiction · Compliance
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header, chart_h

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import date, timedelta, datetime
import warnings
warnings.filterwarnings('ignore')

#  PREMIUM CSS 
st.markdown("""
<style>
.tax-disclaimer {
    background: rgba(243,156,18,0.05);
    border: 1px solid rgba(243,156,18,0.25);
    border-left: 3px solid #F39C12;
    border-radius: 8px; padding: 10px 16px; margin-bottom: 16px;
}
.tax-disclaimer p { margin:0; font-size:11.5px; color:rgba(203,213,225,0.75); line-height:1.55; }
.tax-disclaimer strong { color:#F39C12; }
.tax-savings-block {
    background: linear-gradient(135deg, rgba(46,204,113,0.07), rgba(212,175,55,0.04));
    border: 1px solid rgba(46,204,113,0.22); border-radius: 12px;
    padding: 22px 28px; text-align: center; position: relative; overflow: hidden;
}
.tax-savings-number {
    font-family: 'JetBrains Mono', monospace; font-size: 40px;
    font-weight: 700; letter-spacing: -0.02em;
    background: linear-gradient(135deg, #2ECC71, #D4AF37);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; display: block; margin: 4px 0;
}
.tax-savings-label {
    font-size: 10px; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: rgba(46,204,113,0.75);
    font-family: 'JetBrains Mono', monospace;
}
.tax-savings-sub { font-size: 11px; color: rgba(148,163,184,0.55); margin-top: 6px; }
.tbadge {
    display: inline-flex; align-items: center; gap: 5px;
    font-family: 'JetBrains Mono', monospace; font-size: 10px;
    font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    padding: 3px 10px; border-radius: 999px;
}
.tbadge-safe  { background:rgba(46,204,113,0.1); border:1px solid rgba(46,204,113,0.35); color:#2ECC71; }
.tbadge-warn  { background:rgba(243,156,18,0.1); border:1px solid rgba(243,156,18,0.35); color:#F39C12; }
.tbadge-risk  { background:rgba(231,76,60,0.1);  border:1px solid rgba(231,76,60,0.35);  color:#E74C3C; }
.tbadge-gold  { background:rgba(212,175,55,0.1); border:1px solid rgba(212,175,55,0.35); color:#D4AF37; }
.tax-score-card {
    background: rgba(19,24,35,0.6); border: 1px solid rgba(46,204,113,0.18);
    border-radius: 10px; padding: 16px 18px; text-align: center;
}
.tax-score-num {
    font-family: 'JetBrains Mono', monospace; font-size: 36px; font-weight: 700;
    background: linear-gradient(135deg,#2ECC71,#D4AF37);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.tax-section-label {
    font-family: 'JetBrains Mono', monospace; font-size: 9px; font-weight: 700;
    letter-spacing: 0.18em; text-transform: uppercase;
    color: rgba(46,204,113,0.60); padding-bottom: 8px; margin-bottom: 12px;
    border-bottom: 1px solid rgba(46,204,113,0.10);
}
@keyframes tax-pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(46,204,113,0.4); }
    50%      { box-shadow: 0 0 0 6px rgba(46,204,113,0); }
}
.tax-live-dot {
    display: inline-block; width:8px; height:8px; border-radius:50%;
    background:#2ECC71; animation: tax-pulse 2s ease-in-out infinite;
    margin-right: 6px;
}
</style>
""", unsafe_allow_html=True)

_render_page_header("TL", "TAX LAB Ω",
    "Optimisation Fiscale Globale · 50+ Juridictions · Tax-Loss Harvesting · Succession", "Tax")

st.markdown("""
<div class="tax-disclaimer">
<p><strong> Disclaimer :</strong> TAX LAB Ω fournit des simulations à titre purement indicatif.
Cet outil ne constitue pas un conseil fiscal, juridique ou financier personnalisé.
Consultez toujours un conseiller fiscal qualifié avant toute décision.
GENESIX décline toute responsabilité quant aux conséquences fiscales résultant de l'utilisation de cet outil.</p>
</div>
""", unsafe_allow_html=True)

#  SESSION STATE — TAX PROFILE 
if "tax_profile" not in st.session_state:
    st.session_state.tax_profile = {
        "country": "France", "status": "Résident", "parts": 1.0,
        "income": 85000, "tmi": 0.30, "pfu_option": False,
        "envelopes": {
            "PEA":     {"opened": "2019-05-10", "amount": 112000, "limit": 150000},
            "PEA-PME": {"opened": None,          "amount": 0,      "limit": 225000},
            "AV":      {"opened": "2016-03-22", "amount": 85000,  "limit": None},
            "PER":     {"opened": "2021-01-15", "amount": 22000,  "limit": None},
            "CTO":     {"opened": "2018-09-01", "amount": 145000, "limit": None},
        },
    }

#  TAX RULES DATABASE 
TAX_RULES = {
    "France":      {"cgt_flat":0.30, "cgt_bareme":True, "social":0.172, "div_flat":0.30,
                    "div_abatt":0.40, "wash_sale":False, "wash_days":0,
                    "envelopes":["PEA","PEA-PME","AV","PER","CTO"],
                    "brackets":[0,11294,28797,82341,177106],
                    "rates":[0.0,0.11,0.30,0.41,0.45]},
    "USA":         {"cgt_flat":0.20, "cgt_lt":[0,0.15,0.20], "niit":0.038,
                    "wash_sale":True, "wash_days":30,
                    "envelopes":["401k","IRA","Roth IRA","HSA","529"],
                    "brackets":[0,44625,492300], "rates":[0.10,0.22,0.37]},
    "UK":          {"cgt_flat":0.20, "div_allowance":500, "wash_sale":True, "wash_days":30,
                    "envelopes":["ISA","SIPP","LISA"],
                    "brackets":[0,12570,50270,125140], "rates":[0,0.20,0.40,0.45]},
    "Germany":     {"cgt_flat":0.2638, "div_flat":0.2638, "sparerpauschbetrag":1000,
                    "wash_sale":False, "wash_days":0,
                    "envelopes":["Rürup","Riester","Depot"]},
    "Switzerland": {"cgt_flat":0.0, "div_income":True, "wealth_tax":True,
                    "wash_sale":False, "wash_days":0,
                    "envelopes":["Pilier 3a","Pilier 3b","Dépôt"]},
    "Singapore":   {"cgt_flat":0.0, "div_flat":0.0, "wash_sale":False, "wash_days":0,
                    "envelopes":["CPF","SRS"]},
    "UAE":         {"cgt_flat":0.0, "div_flat":0.0, "wash_sale":False, "wash_days":0,
                    "envelopes":[]},
    "Belgium":     {"cgt_flat":0.0, "div_flat":0.30, "speculation_tax":True,
                    "wash_sale":False, "wash_days":0, "envelopes":[]},
    "Netherlands": {"cgt_flat":0.017, "wealth_tax_box3":True, "wash_sale":False,
                    "wash_days":0, "envelopes":[]},
    "Portugal":    {"cgt_flat":0.28, "div_flat":0.28, "wash_sale":False,
                    "wash_days":0, "envelopes":[]},
    "Canada":      {"cgt_flat":0.50, "inclusion_rate":0.50, "wash_sale":True,
                    "wash_days":30, "envelopes":["TFSA","RRSP","RESP"]},
    "Australia":   {"cgt_flat":0.50, "cgt_discount_12m":0.50, "wash_sale":False,
                    "wash_days":0, "envelopes":["Super","Super Concess."]},
    "Japan":       {"cgt_flat":0.20315, "div_flat":0.20315, "wash_sale":False,
                    "wash_days":0, "envelopes":["NISA","iDeCo"]},
    "Italy":       {"cgt_flat":0.26, "div_flat":0.26, "wash_sale":False,
                    "wash_days":0, "envelopes":["PIR"]},
    "Spain":       {"cgt_flat":0.28, "div_flat":0.28, "wash_sale":False,
                    "wash_days":0, "envelopes":[]},
    "Ireland":     {"cgt_flat":0.33, "div_flat":0.25, "deemed_disposal":8,
                    "wash_sale":True, "wash_days":28, "envelopes":[]},
    "Luxembourg":  {"cgt_flat":0.15, "div_flat":0.15, "wash_sale":False,
                    "wash_days":0, "envelopes":["AV Luxembourg"]},
    "Hong Kong":   {"cgt_flat":0.0, "div_flat":0.0, "wash_sale":False,
                    "wash_days":0, "envelopes":["MPF"]},
}

#  DEMO PORTFOLIO 
@st.cache_data
def _demo_portfolio():
    rows = [
        # ticker, name,              envelope,  qty, buy,    now,   buy_date,     asset,   sector
        ("AAPL",   "Apple Inc.",      "PEA",     50,  150.00, 195.00,"2022-01-15","Stock", "Technology"),
        ("MSFT",   "Microsoft",       "PEA",    100,  280.00, 430.00,"2020-06-10","Stock", "Technology"),
        ("NVDA",   "NVIDIA Corp.",    "CTO",     80,  200.00, 880.00,"2021-01-15","Stock", "Technology"),
        ("VOO",    "Vanguard S&P500", "PEA",    200,  350.00, 450.00,"2020-01-20","ETF",   "Index"),
        ("VWRL",   "Vanguard AllWld", "AV",     300,   85.00, 115.00,"2021-09-15","ETF",   "Index"),
        ("META",   "Meta Platforms",  "CTO",    150,  180.00, 510.00,"2022-02-28","Stock", "Technology"),
        ("AIR.PA", "Airbus SE",       "PEA",    100,  120.00, 170.00,"2023-01-25","Stock", "Aerospace"),
        ("CW8.PA", "MSCI World AMDI", "PEA",    250,  340.00, 350.00,"2023-06-15","ETF",   "Index"),
        # --- LOSSES (TLH candidates) ---
        ("TSLA",   "Tesla Inc.",      "CTO",    200,  280.00, 185.00,"2022-08-15","Stock", "EV/Auto"),
        ("INTC",   "Intel Corp.",     "CTO",    300,   50.00,  22.00,"2022-03-10","Stock", "Semis"),
        ("MMM",    "3M Company",      "CTO",     80,  150.00, 105.00,"2022-05-20","Stock", "Industrials"),
        ("BNP.PA", "BNP Paribas",     "PEA",    400,   60.00,  55.00,"2021-12-10","Stock", "Financials"),
        ("ASML",   "ASML Holding",    "CTO",     30,  750.00, 720.00,"2024-01-10","Stock", "Semis"),
    ]
    cols = ["Ticker","Name","Envelope","Qty","CostBasis","Price","BuyDate","Type","Sector"]
    df = pd.DataFrame(rows, columns=cols)
    df["BuyDate"]   = pd.to_datetime(df["BuyDate"])
    df["Cost"]      = df["Qty"] * df["CostBasis"]
    df["Value"]     = df["Qty"] * df["Price"]
    df["PnL"]       = df["Value"] - df["Cost"]
    df["PnL_pct"]   = df["PnL"] / df["Cost"] * 100
    df["HoldDays"]  = (date.today() - df["BuyDate"].dt.date).apply(lambda x: x.days)
    return df

PORTFOLIO = _demo_portfolio()

#  HELPERS 
def tmi_france(income, parts=1.0):
    brackets = [0, 11294, 28797, 82341, 177106]
    rates    = [0.0, 0.11, 0.30, 0.41, 0.45]
    qi = income / parts
    tax = 0.0; tmi = 0.0
    for i in range(len(rates)):
        lo = brackets[i]
        hi = brackets[i+1] if i+1 < len(brackets) else 1e9
        if qi > lo:
            tax += (min(qi, hi) - lo) * rates[i]
            tmi = rates[i]
    return tax * parts, tmi

def cgt_france(gain, tmi=0.30, pfu=True):
    if pfu: return gain * 0.30
    return gain * (tmi + 0.172)

def cgt_usa_lt(gain, income):
    if income <= 44625:   return gain * 0.0
    elif income <= 492300: return gain * 0.15
    else:                  return gain * 0.20

def fmt(v, prefix="€", decimals=0):
    s = f"{abs(v):,.{decimals}f}"
    sign = "-" if v < 0 else ""
    return f"{sign}{prefix}{s}"

def score_color(s):
    if s >= 75: return "#2ECC71"
    elif s >= 50: return "#F39C12"
    else: return "#E74C3C"

def _plotly_dark():
    return dict(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#CBD5E1", family="DM Sans, sans-serif", size=11),
        xaxis=dict(gridcolor="rgba(51,65,85,0.3)", linecolor="rgba(51,65,85,0.4)"),
        yaxis=dict(gridcolor="rgba(51,65,85,0.3)", linecolor="rgba(51,65,85,0.4)"),
        margin=dict(l=40, r=20, t=30, b=40),
    )

#  8 TABS 
TABS = st.tabs([
    " Tax Profile",
    " Dashboard",
    " Loss Harvester",
    " Envelope Optimizer",
    " Scenario Lab",
    " Estate Planner",
    " Multi-Jurisdiction",
    " Compliance",
])

# 
# TAB 1 — TAX PROFILE ENGINE
# 
with TABS[0]:
    st.markdown('<p class="tax-section-label"> PROFIL FISCAL UTILISATEUR</p>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.4, 1.4, 1.2])

    with c1:
        st.markdown("**Identité fiscale**")
        country = st.selectbox("Pays de résidence fiscale", list(TAX_RULES.keys()),
            index=list(TAX_RULES.keys()).index(st.session_state.tax_profile["country"]),
            key="tp_country")
        status = st.selectbox("Statut", ["Résident", "Non-résident", "Quasi-résident", "Expatrié"],
            key="tp_status")
        parts = st.number_input("Nombre de parts fiscales", 1.0, 8.0,
            st.session_state.tax_profile["parts"], 0.5, key="tp_parts")
        income = st.number_input("Revenu net imposable (€)", 0, 5_000_000,
            int(st.session_state.tax_profile["income"]), 5000, key="tp_income",
            help="Revenus annuels hors investissements")

    with c2:
        st.markdown("**Enveloppes fiscales**")
        p = st.session_state.tax_profile
        env_data = []
        rules = TAX_RULES.get(country, TAX_RULES["France"])
        envelopes_for_country = rules.get("envelopes", [])
        for env in envelopes_for_country[:6]:
            ev = p["envelopes"].get(env, {"opened": None, "amount": 0, "limit": None})
            col_a, col_b = st.columns([1.2, 0.8])
            with col_a:
                amt = st.number_input(f"{env} — montant (€)", 0, 10_000_000,
                    int(ev.get("amount", 0)), 1000, key=f"env_{env}_amt")
            with col_b:
                opened = st.text_input(f"Ouvert le", ev.get("opened") or "", key=f"env_{env}_date",
                    placeholder="AAAA-MM-JJ")
            env_data.append((env, amt, opened, ev.get("limit")))

    with c3:
        # Compute TMI
        if country == "France":
            tax_due, tmi = tmi_france(income, parts)
            pfu_better = True
            pfu_label = "30% PFU (flat)"
        else:
            tax_due = 0.0
            tmi = rules.get("cgt_flat", 0.20)

        # Tax score (0-100)
        pea_used   = p["envelopes"].get("PEA", {}).get("amount", 0)
        pea_limit  = 150000
        pea_fill   = min(pea_used / pea_limit, 1.0) if pea_limit else 0
        av_opened  = p["envelopes"].get("AV", {}).get("opened")
        av_age     = 0
        if av_opened:
            try:
                av_age = (date.today() - datetime.strptime(av_opened, "%Y-%m-%d").date()).days / 365
            except: pass
        pea_opened = p["envelopes"].get("PEA", {}).get("opened")
        pea_age = 0
        if pea_opened:
            try:
                pea_age = (date.today() - datetime.strptime(pea_opened, "%Y-%m-%d").date()).days / 365
            except: pass

        score = int(
            (0.30 * min(pea_fill * 100, 100)) +
            (0.20 * min(av_age / 8 * 100, 100)) +
            (0.20 * min(pea_age / 5 * 100, 100)) +
            (0.15 * (80 if income > 50000 else 50)) +
            (0.15 * (70 if status == "Résident" else 50))
        )

        st.session_state.tax_profile.update({
            "country": country, "status": status, "parts": parts,
            "income": income, "tmi": tmi,
        })

        sc = score_color(score)
        st.markdown(f"""
        <div class="tax-score-card">
            <div style="font-size:10px;color:rgba(148,163,184,0.6);letter-spacing:0.12em;
                        text-transform:uppercase;font-family:'JetBrains Mono',monospace;
                        margin-bottom:4px;">Score d'optimisation</div>
            <div class="tax-score-num" style="background:linear-gradient(135deg,{sc},#D4AF37);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                background-clip:text;">{score}<span style="font-size:20px">/100</span></div>
            <div style="font-size:11px;color:rgba(148,163,184,0.55);margin-top:4px;">
                {"Très bien optimisé" if score >= 75 else ("Améliorable" if score >= 50 else "À optimiser")}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if country == "France":
            st.metric("TMI (Taux Marginal)", f"{tmi*100:.0f}%")
            st.metric("Impôt estimé (barème)", fmt(tax_due))
            st.metric("Taux optimal PV", "30% PFU" if tmi >= 0.30 else f"{(tmi+0.172)*100:.1f}% barème")
        else:
            st.metric("CGT rate", f"{tmi*100:.1f}%")

    st.divider()
    st.markdown("**Comparatif des régimes — clé par pays**")

    summary_data = {
        " France": ["30% PFU ou barème", "30% PFU", "IFI > 1.3M€ immo", "PEA · AV · PER"],
        " USA":    ["0/15/20% LT + 3.8% NIIT", "0/15/20% qualif.", "—", "401k · IRA · Roth · HSA"],
        " UK":     ["10/20% (18/24% immo)", "£500 allow. puis 8.75/39%", "—", "ISA · SIPP · LISA"],
        " Germany":["26.375% flat", "26.375% flat", "—", "Rürup · Riester"],
        " Suisse": ["0% (PV privées)", "Revenu ord.", "Wealth tax cantonal", "Pilier 3a/3b"],
        " Singapore":["0%", "0%", "—", "CPF · SRS"],
        " UAE":    ["0%", "0%", "—", "—"],
        " Belgique":["0% (PV privées)", "30%", "—", "—"],
        " Canada": ["50% inclusion", "Elig. div. gross-up", "—", "TFSA · RRSP"],
        " Australie":["50% discount >12m", "Franking credits", "—", "Super"],
    }
    df_cmp = pd.DataFrame(summary_data, index=["Plus-values","Dividendes","Wealth Tax","Enveloppes"]).T
    st.dataframe(df_cmp, use_container_width=True)


# 
# TAB 2 — TAX DASHBOARD
# 
with TABS[1]:
    st.markdown('<p class="tax-section-label"> COCKPIT FISCAL EN TEMPS RÉEL</p>', unsafe_allow_html=True)

    prof     = st.session_state.tax_profile
    tmi      = prof["tmi"]
    country  = prof["country"]
    pf       = PORTFOLIO

    total_value  = pf["Value"].sum()
    total_cost   = pf["Cost"].sum()
    total_pnl    = pf["PnL"].sum()
    gains        = pf[pf["PnL"] > 0]["PnL"].sum()
    losses       = pf[pf["PnL"] < 0]["PnL"].sum()
    tax_if_sold  = max(gains * 0.30, 0)  # PFU France
    tax_saved_tlh = abs(losses) * 0.30
    net_liability = max(tax_if_sold - tax_saved_tlh, 0)

    #  Hero metrics 
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Valeur Portefeuille",    fmt(total_value),  fmt(total_pnl, prefix="€"))
    m2.metric("Plus-values latentes",  fmt(gains),         f"+{gains/total_cost*100:.1f}%")
    m3.metric("Passif fiscal estimé",  fmt(tax_if_sold),   "si réalisé")
    m4.metric("Économies TLH possibles", fmt(tax_saved_tlh), "récolte pertes")

    st.markdown("<br>", unsafe_allow_html=True)

    ca, cb = st.columns([1.6, 1.4])

    with ca:
        # P&L Waterfall
        positions = pf.sort_values("PnL", ascending=False)
        colors = ["#2ECC71" if v > 0 else "#E74C3C" for v in positions["PnL"]]
        fig_wf = go.Figure(go.Bar(
            x=positions["Ticker"], y=positions["PnL"],
            marker_color=colors,
            text=[f"{v:+,.0f}€" for v in positions["PnL"]],
            textposition="outside", textfont=dict(size=9),
        ))
        fig_wf.update_layout(**_plotly_dark(), height=chart_h(2),
            title=dict(text="P&L Latent par Position (€)", font=dict(size=12, color="#CBD5E1")),
            yaxis_tickprefix="€", yaxis_tickformat=",.0f")
        st.plotly_chart(fig_wf, use_container_width=True)

    with cb:
        # Envelope allocation sunburst
        env_pf = pf.groupby("Envelope").agg(Value=("Value","sum"), Cost=("Cost","sum")).reset_index()
        env_pf["PnL"] = env_pf["Value"] - env_pf["Cost"]
        fig_sb = px.sunburst(
            pf, path=["Envelope","Ticker"], values="Value",
            color="PnL_pct",
            color_continuous_scale=[[0,"#E74C3C"],[0.5,"#F39C12"],[1,"#2ECC71"]],
            color_continuous_midpoint=0,
        )
        fig_sb.update_layout(**_plotly_dark(), height=chart_h(2),
            title=dict(text="Répartition par Enveloppe", font=dict(size=12, color="#CBD5E1")),
            coloraxis_showscale=False)
        st.plotly_chart(fig_sb, use_container_width=True)

    #  Tax Calendar 
    st.markdown("** Calendrier fiscal — Prochaines échéances**")
    today = date.today()
    cal_events = [
        (today + timedelta(days=12),  "", "Déclaration IR — Deadline zone 3", "warn"),
        (today + timedelta(days=22),  "", "PEA 5 ans atteints → Exonération IR activée", "safe"),
        (today + timedelta(days=45),  "", "AV 8 ans en septembre → Abattement 4,600€", "safe"),
        (today + timedelta(days=78),  "", "Fenêtre optimale rachat AV avant 31 déc.", "warn"),
        (today + timedelta(days=120), "", "Wash sale INTC expire → Harvesting possible", "risk"),
        (today + timedelta(days=185), "", "PER — Versement avant 31/12 déductible", "safe"),
        (today + timedelta(days=200), "", "Abattement donation 100k€/enfant disponible", "safe"),
    ]
    cal_df = pd.DataFrame(cal_events, columns=["Date","Icon","Événement","Type"])
    cal_df["Jours"] = (cal_df["Date"] - today).apply(lambda x: f"J+{x.days}")
    cal_df["Date"]  = cal_df["Date"].apply(lambda d: d.strftime("%d/%m/%Y"))
    st.dataframe(
        cal_df[["Date","Jours","Icon","Événement"]].rename(columns={"Icon":""}),
        use_container_width=True, hide_index=True
    )

    #  Tax savings counter 
    total_saved = tax_saved_tlh * 0.6 + 3200  # simulated YTD realized savings
    st.markdown(f"""
    <div class="tax-savings-block" style="margin-top:16px">
        <span class="tax-savings-label"><span class="tax-live-dot"></span>Économies fiscales générées YTD</span>
        <span class="tax-savings-number">{total_saved:,.0f} €</span>
        <div class="tax-savings-sub">TLH réalisé · Optimisation enveloppes · Abattements utilisés</div>
    </div>
    """, unsafe_allow_html=True)


# 
# TAB 3 — TAX-LOSS HARVESTING ENGINE
# 
with TABS[2]:
    st.markdown('<p class="tax-section-label"> MOTEUR ALGORITHMIQUE DE RÉCOLTE DE PERTES</p>', unsafe_allow_html=True)

    prof    = st.session_state.tax_profile
    country = prof["country"]
    tmi     = prof["tmi"]
    rules   = TAX_RULES.get(country, TAX_RULES["France"])
    wash    = rules.get("wash_sale", False)
    wash_d  = rules.get("wash_days", 0)
    social  = rules.get("social", 0.0)

    ca, cb = st.columns([1, 2])
    with ca:
        threshold_pct = st.slider("Seuil de déclenchement (%)", 5, 50, 10, 1,
            help="Récolter une position si perte latente > seuil")
        tx_cost_bps   = st.slider("Coûts de transaction (bps)", 0, 50, 10, 1,
            help="Spread + commission estimé en points de base")
        use_pfu       = st.checkbox("Utiliser PFU 30% (France)", value=True)
        effective_rate = 0.30 if use_pfu else (tmi + social)

    with cb:
        # TLH replacement database
        TLH_REPL = {
            "TSLA":   [("DRIV","Global X Autonomous & EV ETF", 0.78), ("KARS","KraneShares EV ETF", 0.74)],
            "INTC":   [("SOXX","iShares Semiconductor ETF",    0.82), ("SMH","VanEck Semi ETF",    0.84)],
            "MMM":    [("XLI", "Industrial Select SPDR",       0.76), ("VIS","Vanguard Industrials",0.73)],
            "BNP.PA": [("SX7E","EURO STOXX Banks ETF",         0.85), ("EXV1","DB European Banks", 0.83)],
            "ASML":   [("SOXX","iShares Semiconductor ETF",    0.78), ("SEMI","MSCI Global Semi",  0.80)],
            "CW8.PA": [("EWLD","iShares MSCI World",           0.99), ("WPEA","AMUNDI MSCI World", 0.98)],
        }

        # Scan losses
        losses_df = PORTFOLIO[PORTFOLIO["PnL_pct"] < -threshold_pct].copy()

        if len(losses_df) == 0:
            st.info(f"Aucune position en perte > {threshold_pct}% — portefeuille optimisé.")
        else:
            harvest_rows = []
            for _, row in losses_df.iterrows():
                loss_abs   = abs(row["PnL"])
                tx_cost    = row["Value"] * tx_cost_bps / 10000
                tax_saving = loss_abs * effective_rate
                net_saving = tax_saving - tx_cost
                repl       = TLH_REPL.get(row["Ticker"], [("—","Aucun substitut connu",0.0)])
                best_repl  = repl[0]

                # Wash sale check
                last_buy_days = row["HoldDays"]
                wash_issue = wash and last_buy_days < wash_d
                hold_years = row["HoldDays"] / 365

                harvest_rows.append({
                    "Ticker":       row["Ticker"],
                    "Nom":          row["Name"],
                    "Enveloppe":    row["Envelope"],
                    "Perte (€)":    f"-{loss_abs:,.0f}€",
                    "Perte (%)":    f"{row['PnL_pct']:.1f}%",
                    "Économie fisc.": f"{tax_saving:,.0f}€",
                    "Coûts trans.": f"{tx_cost:,.0f}€",
                    "Net saving":   f"{net_saving:,.0f}€",
                    "Substitut":    best_repl[0],
                    "Corrélation":  f"{best_repl[2]*100:.0f}%",
                    "Wash Sale":    " Risque" if wash_issue else " OK",
                    "Priorité":     " FORT" if row["PnL_pct"] < -25 else (" MOYEN" if row["PnL_pct"] < -15 else " FAIBLE"),
                    "_net":         net_saving,
                })

            harvest_df = pd.DataFrame(harvest_rows).sort_values("_net", ascending=False).drop(columns=["_net"])
            total_tlh_saving = sum(
                abs(r["PnL"]) * effective_rate - r["Value"] * tx_cost_bps / 10000
                for _, r in losses_df.iterrows()
            )

            cols_m = st.columns(3)
            cols_m[0].metric("Opportunités identifiées", len(harvest_df))
            cols_m[1].metric("Économie fiscale totale", f"{sum(abs(r['PnL'])*effective_rate for _,r in losses_df.iterrows()):,.0f}€")
            cols_m[2].metric("Net après coûts", f"{max(total_tlh_saving,0):,.0f}€")

            st.markdown("<br>", unsafe_allow_html=True)
            st.dataframe(harvest_df, use_container_width=True, hide_index=True)

    #  Wash Sale rules by country 
    with st.expander(" Règles Wash Sale / Superficial Loss par juridiction"):
        ws_data = {
            "Pays": [" France"," USA"," UK"," Canada"," Germany"," Australie"," Belgique"," Suisse"],
            "Règle": ["Aucune","Wash sale 30j","Bed & Breakfast 30j","Superficial Loss 30j","Aucune","Aucune","Aucune (≤6m = spéculation)","Aucune"],
            "Impact TLH": [" Harvesting agressif possible"," Restrictions strictes"," Limité aux actions"," Restrictions + affiliated persons"," Harvesting libre"," Libre (attention discount 12m)"," Surveiller délai spéculation"," PV privées exonérées"],
            "Conseil": ["Vendre et racheter immédiatement","Attendre 31j ou utiliser substitut","Utiliser ETF différent émetteur","Vérifier affiliated persons","Librement harvester","Vérifier statut 12m discount","Éviter speculation tax","Non applicable (PV exonérées)"],
        }
        st.dataframe(pd.DataFrame(ws_data), use_container_width=True, hide_index=True)

    #  TLH historical simulation 
    st.markdown("** Projection TLH — Impact sur 10 ans**")
    years = np.arange(1, 11)
    annual_portfolio = 250000
    annual_turnover  = 0.20
    avg_loss_rate    = 0.05
    tax_rate_sim     = effective_rate
    tlh_annual       = annual_portfolio * annual_turnover * avg_loss_rate * tax_rate_sim
    cumulative_tlh   = np.cumsum([tlh_annual * (1.07 ** y) for y in range(10)])
    no_tlh_portfolio = annual_portfolio * (1.07 ** years)
    tlh_portfolio    = annual_portfolio * (1.07 ** years) + cumulative_tlh

    fig_proj = go.Figure()
    fig_proj.add_trace(go.Scatter(x=years, y=no_tlh_portfolio, name="Sans TLH",
        line=dict(color="#94A3B8", dash="dash", width=2)))
    fig_proj.add_trace(go.Scatter(x=years, y=tlh_portfolio, name="Avec TLH",
        line=dict(color="#2ECC71", width=2.5),
        fill="tonexty", fillcolor="rgba(46,204,113,0.06)"))
    fig_proj.update_layout(**_plotly_dark(), height=280,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        xaxis_title="Années", yaxis_title="Valeur portefeuille (€)",
        yaxis_tickprefix="€", yaxis_tickformat=",.0f")
    st.plotly_chart(fig_proj, use_container_width=True)


# 
# TAB 4 — ENVELOPE OPTIMIZER
# 
with TABS[3]:
    st.markdown('<p class="tax-section-label"> OPTIMISATION DE L\'ALLOCATION PAR ENVELOPPE</p>', unsafe_allow_html=True)

    country = st.session_state.tax_profile["country"]
    p       = st.session_state.tax_profile

    # Asset-location rules
    ASSET_LOC_RULES = {
        "France": {
            "PEA": {
                "best_for": ["Actions EU/EEA", "ETF synthétiques MSCI World", "Growth stocks"],
                "avoid":    ["Actions US directes", "Obligations", "REITs hors EU"],
                "advantage": "Exonération totale IR après 5 ans (prélèvements sociaux 17.2% subsistent)",
                "limit_eur": 150000,
            },
            "AV": {
                "best_for": ["Obligations", "Fonds euros", "REITs", "Actifs à dividendes élevés"],
                "avoid":    ["Actions très volatiles", "Crypto"],
                "advantage": "Fiscalité dégressive : abattement 4,600€/an après 8 ans",
                "limit_eur": None,
            },
            "PER": {
                "best_for": ["Actifs à fort rendement long terme", "Actions de croissance"],
                "avoid":    ["Liquidités", "Fonds monétaires"],
                "advantage": "Déductible des revenus imposables (plafond 10% revenus professionnels)",
                "limit_eur": None,
            },
            "CTO": {
                "best_for": ["Actions US", "ETF hors PEA", "Actifs TLH candidates"],
                "avoid":    ["Obligations (mieux en AV)", "Actions EU (mieux en PEA)"],
                "advantage": "Aucun plafond — TLH optimal (pas de wash sale en France)",
                "limit_eur": None,
            },
        }
    }

    # Optimization audit of demo portfolio
    ISSUES = {
        "INTC":   ("CTO", "CTO", " OK — eligible TLH, action US non-éligible PEA", "safe"),
        "TSLA":   ("CTO", "CTO", " OK — eligible TLH, action US non-éligible PEA", "safe"),
        "NVDA":   ("CTO", "CTO", " Action US en CTO — seule option, mais TLH possible si perte", "warn"),
        "VWRL":   ("AV",  "PEA", " ETF World en AV — préférable en PEA pour exonération IR long terme", "risk"),
        "CW8.PA": ("PEA", "PEA", " Optimal — ETF MSCI World synthétique en PEA", "safe"),
        "BNP.PA": ("PEA", "PEA", " Action FR en perte dans PEA — pas de TLH possible en PEA (gains/pertes non comptabilisés hors PEA)", "warn"),
        "META":   ("CTO", "CTO", " OK — action US en CTO, TLH possible", "safe"),
        "MSFT":   ("PEA", "PEA", " MSFT en PEA via ETF synthétique uniquement — vérifier éligibilité", "warn"),
        "AIR.PA": ("PEA", "PEA", " Optimal — action EU en PEA", "safe"),
    }

    st.markdown("** Audit des placements actuels**")
    audit_rows = []
    for _, row in PORTFOLIO.iterrows():
        issue = ISSUES.get(row["Ticker"], (row["Envelope"], row["Envelope"], " OK", "safe"))
        audit_rows.append({
            "Ticker":        row["Ticker"],
            "Nom":           row["Name"],
            "Enveloppe act.": row["Envelope"],
            "Opt. suggérée": issue[1],
            "Analyse":       issue[2],
            "Valeur":        fmt(row["Value"]),
        })
    audit_df = pd.DataFrame(audit_rows)
    st.dataframe(audit_df, use_container_width=True, hide_index=True)

    st.divider()

    # Envelope capacity tracker
    st.markdown("** Capacité des enveloppes**")
    env_caps = [
        ("PEA",        p["envelopes"].get("PEA", {}).get("amount", 0),        150000),
        ("PEA-PME",    p["envelopes"].get("PEA-PME", {}).get("amount", 0),    225000),
        ("AV (Contrat 1)", p["envelopes"].get("AV", {}).get("amount", 0),     None),
        ("PER",        p["envelopes"].get("PER", {}).get("amount", 0),        None),
    ]
    for name, used, limit in env_caps:
        if limit:
            pct     = min(used / limit, 1.0)
            remaining = limit - used
            bar_color = "#E74C3C" if pct > 0.9 else ("#F39C12" if pct > 0.7 else "#2ECC71")
            ca, cb, cc = st.columns([2, 1, 1])
            ca.markdown(f"**{name}**")
            ca.progress(pct, text=f"{used:,.0f}€ / {limit:,.0f}€ ({pct*100:.0f}%)")
            cb.metric("Restant", fmt(remaining))
            cc.markdown(f"<span class='tbadge tbadge-{'risk' if pct>0.9 else ('warn' if pct>0.7 else 'safe')}'>"
                       f"{'Complet' if pct>0.95 else ('Presque plein' if pct>0.7 else 'Disponible')}</span>",
                       unsafe_allow_html=True)

    # Asset location matrix
    st.divider()
    if country == "France":
        st.markdown("** Matrice d'allocation optimale — France**")
        loc_rules = ASSET_LOC_RULES["France"]
        for env, rules_env in loc_rules.items():
            with st.expander(f"**{env}** — {rules_env['advantage']}"):
                c1, c2 = st.columns(2)
                c1.success(" Idéal pour : " + " · ".join(rules_env["best_for"]))
                c2.warning(" À éviter : " + " · ".join(rules_env["avoid"]))


# 
# TAB 5 — SCENARIO SIMULATOR
# 
with TABS[4]:
    st.markdown('<p class="tax-section-label"> SIMULATEUR WHAT-IF MULTI-SCÉNARIOS</p>', unsafe_allow_html=True)

    scenario = st.selectbox("Type de scénario", [
        "Vente maintenant vs plus tard (timing CGT)",
        "Roth IRA Conversion (USA)",
        "Rachat AV — Optimisation abattement (France)",
        "Déménagement fiscal — Comparaison pays",
        "Projection Monte Carlo sur 20 ans",
    ])

    st.divider()

    if scenario == "Vente maintenant vs plus tard (timing CGT)":
        c1, c2 = st.columns(2)
        with c1:
            s_gain      = st.number_input("Plus-value latente (€)", 1000, 5_000_000, 50000, 1000)
            s_country   = st.selectbox("Pays", list(TAX_RULES.keys()), key="sc_country")
            s_income    = st.number_input("Revenu annuel (€)", 0, 5_000_000, 85000, 5000, key="sc_inc")
            s_hold_days = st.slider("Durée de détention actuelle (jours)", 1, 1825, 300)
        with c2:
            months_wait = st.slider("Attendre encore (mois)", 0, 36, 6)

        # Compute taxes for each scenario
        def tax_for(gain, country_s, income_s, hold_days_s):
            r = TAX_RULES.get(country_s, TAX_RULES["France"])
            if country_s == "France":
                return gain * 0.30
            elif country_s == "USA":
                if hold_days_s >= 365: return cgt_usa_lt(gain, income_s)
                else: return gain * 0.37  # short-term = ordinary
            elif country_s == "UK":
                return gain * (0.10 if income_s <= 50270 else 0.20)
            elif country_s in ("Switzerland","Belgium","UAE","Singapore","Hong Kong"):
                return 0.0
            else:
                return gain * r.get("cgt_flat", 0.20)

        new_hold = s_hold_days + months_wait * 30
        tax_now   = tax_for(s_gain, s_country, s_income, s_hold_days)
        tax_later = tax_for(s_gain, s_country, s_income, new_hold)
        saving    = tax_now - tax_later

        c1, c2, c3 = st.columns(3)
        c1.metric("Impôt si vente maintenant",   fmt(tax_now))
        c2.metric(f"Impôt dans {months_wait} mois", fmt(tax_later))
        c3.metric("Économie potentielle",          fmt(saving),
                  delta=f"{saving/max(tax_now,1)*100:.1f}%" if tax_now else "N/A",
                  delta_color="normal")

        if s_country == "USA" and s_hold_days < 365 <= new_hold:
            st.success(" En attendant 1 an complet, vous basculez en taux long terme (0/15/20%) — économie significative possible.")
        elif s_country == "France":
            pea_months = st.checkbox("Position en PEA ?")
            if pea_months:
                st.info("En PEA, après 5 ans : exonération IR totale. Seuls 17.2% de prélèvements sociaux s'appliquent.")

        # Timeline chart
        hold_range  = np.arange(0, 37, 1)
        taxes_over_time = [tax_for(s_gain, s_country, s_income, s_hold_days + m*30) for m in hold_range]
        fig_t = go.Figure(go.Scatter(x=hold_range, y=taxes_over_time,
            line=dict(color="#2ECC71", width=2.5), fill="tozeroy",
            fillcolor="rgba(46,204,113,0.06)"))
        fig_t.add_vline(x=0, line=dict(color="#E74C3C", dash="dash", width=1.5), annotation_text="Maintenant")
        fig_t.add_vline(x=months_wait, line=dict(color="#D4AF37", dash="dash", width=1.5),
            annotation_text=f"Dans {months_wait}m")
        fig_t.update_layout(**_plotly_dark(), height=260,
            xaxis_title="Mois supplémentaires", yaxis_title="Impôt (€)",
            yaxis_tickprefix="€", yaxis_tickformat=",.0f")
        st.plotly_chart(fig_t, use_container_width=True)

    elif scenario == "Rachat AV — Optimisation abattement (France)":
        c1, c2 = st.columns(2)
        with c1:
            av_total    = st.number_input("Valeur totale AV (€)", 10000, 5_000_000, 120000, 5000)
            av_versed   = st.number_input("Primes versées (€)",   10000, 5_000_000,  80000, 5000)
            av_years    = st.slider("Ancienneté du contrat (années)", 1, 30, 10)
            av_part     = st.slider("Rachat (% du contrat)", 5, 100, 30)
        with c2:
            av_gain_total = av_total - av_versed
            av_rachat     = av_total * av_part / 100
            av_gain_rachat = av_gain_total * (av_part / 100)

            if av_years >= 8:
                abatt   = 4600  # célibataire
                taxable = max(av_gain_rachat - abatt, 0)
                tax_av  = taxable * 0.30
                st.success(f" Contrat > 8 ans — Abattement {abatt:,.0f}€ applicable")
            else:
                taxable = av_gain_rachat
                tax_av  = taxable * 0.30
                st.warning(f" Contrat < 8 ans — Pas d'abattement, PFU 30% sur {taxable:,.0f}€")

            st.metric("Rachat brut",        fmt(av_rachat))
            st.metric("Quote-part de gains", fmt(av_gain_rachat))
            st.metric("Taxable après abatt.", fmt(taxable))
            st.metric("Impôt estimé",        fmt(tax_av))
            st.metric("Perçu net",           fmt(av_rachat - tax_av))

        if av_years >= 8 and av_gain_rachat > 4600:
            st.info(f" Stratégie : Lisser les rachats sur plusieurs années. "
                   f"En rachetant {4600:.0f}€ de gains/an, vous utilisez l'abattement annuel complet sans payer d'impôt.")

    elif scenario == "Déménagement fiscal — Comparaison pays":
        income_mv = st.number_input("Revenu annuel brut (€)", 10000, 10_000_000, 200000, 10000)
        gains_mv  = st.number_input("Plus-values annuelles (€)", 0, 5_000_000, 80000, 5000)

        countries_compare = ["France","Germany","Switzerland","UAE","Portugal","Belgium","Singapore","UK"]
        results = []
        for c_name in countries_compare:
            r = TAX_RULES[c_name]
            cgt = gains_mv * r.get("cgt_flat", 0.0)
            if c_name == "France":
                _, tmi_c = tmi_france(income_mv)
                ir = income_mv * tmi_c * 0.5  # rough effective
            else:
                ir = 0
            total_tax = cgt + ir
            net        = income_mv + gains_mv - total_tax
            results.append({"Pays": c_name, "CGT": fmt(cgt), "IR estimé": fmt(ir),
                            "Charge totale": fmt(total_tax), "Net perçu": fmt(net),
                            "_net": net})

        res_df = pd.DataFrame(results).sort_values("_net", ascending=False).drop(columns=["_net"])
        st.dataframe(res_df, use_container_width=True, hide_index=True)

    elif scenario == "Projection Monte Carlo sur 20 ans":
        c1, c2 = st.columns(2)
        with c1:
            mc_wealth    = st.number_input("Patrimoine initial (€)", 50000, 50_000_000, 500000, 50000)
            mc_return    = st.slider("Rendement annuel moyen (%)", 1.0, 20.0, 7.0, 0.5) / 100
            mc_vol       = st.slider("Volatilité (%)", 1.0, 40.0, 15.0, 0.5) / 100
            mc_tax_rate  = st.slider("Taux d'imposition sur gains (%)", 0.0, 50.0, 30.0, 1.0) / 100

        with c2:
            np.random.seed(42)
            n_sims, n_years = 500, 20
            rets = np.random.normal(mc_return, mc_vol, (n_sims, n_years))
            pf_taxed    = np.zeros((n_sims, n_years + 1)); pf_taxed[:,0]    = mc_wealth
            pf_notaxed  = np.zeros((n_sims, n_years + 1)); pf_notaxed[:,0]  = mc_wealth
            for y in range(n_years):
                g_t = np.maximum(pf_taxed[:,y] * rets[:,y], 0)
                pf_taxed[:,y+1]   = pf_taxed[:,y]   * (1 + rets[:,y]) - g_t * mc_tax_rate
                pf_notaxed[:,y+1] = pf_notaxed[:,y] * (1 + rets[:,y])

            yrs = np.arange(n_years + 1)
            med_taxed   = np.median(pf_taxed, axis=0)
            med_notaxed = np.median(pf_notaxed, axis=0)
            p10_taxed   = np.percentile(pf_taxed, 10, axis=0)
            p90_taxed   = np.percentile(pf_taxed, 90, axis=0)

            fig_mc = go.Figure()
            fig_mc.add_trace(go.Scatter(x=np.concatenate([yrs, yrs[::-1]]),
                y=np.concatenate([p90_taxed, p10_taxed[::-1]]),
                fill="toself", fillcolor="rgba(46,204,113,0.07)",
                line=dict(color="transparent"), name="Intervalle 10-90%"))
            fig_mc.add_trace(go.Scatter(x=yrs, y=med_notaxed, name="Sans impôt",
                line=dict(color="#94A3B8", dash="dash", width=2)))
            fig_mc.add_trace(go.Scatter(x=yrs, y=med_taxed, name=f"Avec impôt ({mc_tax_rate*100:.0f}%)",
                line=dict(color="#2ECC71", width=2.5)))
            fig_mc.update_layout(**_plotly_dark(), height=chart_h(2),
                title=dict(text="Monte Carlo — 500 simulations", font=dict(size=12, color="#CBD5E1")),
                xaxis_title="Années", yaxis_title="Patrimoine (€)",
                yaxis_tickprefix="€", yaxis_tickformat=",.0f")
            st.plotly_chart(fig_mc, use_container_width=True)

            st.metric("Patrimoine médian après 20 ans (avec impôt)", fmt(med_taxed[-1]))
            st.metric("Manque à gagner vs sans impôt", fmt(med_notaxed[-1] - med_taxed[-1]),
                     delta_color="inverse")

    elif scenario == "Roth IRA Conversion (USA)":
        c1, c2 = st.columns(2)
        with c1:
            ira_bal       = st.number_input("Solde IRA traditionnel ($)", 10000, 5_000_000, 250000, 10000)
            conversion_amt = st.number_input("Montant à convertir ($)", 1000, 500000, 50000, 5000)
            current_income = st.number_input("Revenu ordinaire actuel ($)", 0, 5_000_000, 120000, 5000)
            ret_income     = st.number_input("Revenu estimé à la retraite ($)", 0, 500000, 60000, 5000)
            years_to_ret   = st.slider("Années avant retraite", 1, 40, 20)
        with c2:
            # Tax cost of conversion now
            total_now = current_income + conversion_amt
            def us_tax(inc):
                brackets = [(0,11925,0.10),(11925,48475,0.12),(48475,103350,0.22),
                            (103350,197300,0.24),(197300,250525,0.32),(250525,626350,0.35),(626350,1e9,0.37)]
                t = 0
                for lo, hi, r in brackets:
                    if inc > lo: t += (min(inc, hi) - lo) * r
                return t
            tax_now_conversion = us_tax(total_now) - us_tax(current_income)
            tax_roth_dist      = 0  # tax-free
            tax_trad_dist      = us_tax(ret_income + conversion_amt * 0.7) - us_tax(ret_income)
            roth_growth        = conversion_amt * (1.07 ** years_to_ret)
            trad_growth        = (conversion_amt - tax_now_conversion) * (1.07 ** years_to_ret)
            roth_net_dist      = roth_growth
            trad_net_dist      = trad_growth - us_tax(ret_income + trad_growth * 0.04) * 25

            st.metric("Impôt sur conversion maintenant", f"${tax_now_conversion:,.0f}")
            st.metric("Valeur Roth dans 20 ans (net)", f"${roth_net_dist:,.0f}")
            st.metric("Valeur IRA trad. dans 20 ans (net)", f"${trad_net_dist:,.0f}")
            delta = roth_net_dist - trad_net_dist
            if delta > 0:
                st.success(f" Roth conversion avantageuse : +${delta:,.0f} de richesse nette sur {years_to_ret} ans")
            else:
                st.warning(f" Garder l'IRA traditionnel : ${-delta:,.0f} d'avantage sur {years_to_ret} ans")


# 
# TAB 6 — ESTATE & SUCCESSION PLANNER
# 
with TABS[5]:
    st.markdown('<p class="tax-section-label"> PLANIFICATION SUCCESSORALE & TRANSMISSION</p>', unsafe_allow_html=True)

    country_estate = st.session_state.tax_profile["country"]

    c1, c2 = st.columns([1.2, 1.8])
    with c1:
        estate_val   = st.number_input("Patrimoine total (€)", 100000, 100_000_000, 1_500_000, 100000)
        n_children   = st.slider("Nombre d'enfants", 0, 8, 2)
        n_spouse     = st.selectbox("Conjoint survivant", ["Oui", "Non"])
        has_av       = st.checkbox("Assurance-vie souscrite", value=True)
        av_amount    = st.number_input("Montant AV (€)", 0, 10_000_000, 350000, 10000) if has_av else 0
        av_before_70 = st.checkbox("Versements avant 70 ans", value=True) if has_av else False

    with c2:
        if country_estate == "France":
            st.markdown("** Simulation droits de succession — France**")

            # AV exonération
            av_exempt_per_bene  = 152500 if av_before_70 else 30500
            av_taxable_per_bene = max((av_amount / max(n_children,1)) - av_exempt_per_bene, 0) if n_children > 0 else 0
            av_total_tax        = av_taxable_per_bene * n_children * 0.20  # 20% après abattement

            # Succession hors AV
            estate_hors_av = estate_val - av_amount
            abatt_spouse   = estate_hors_av if n_spouse == "Oui" else 0  # exonération totale conjoint
            abatt_child    = 100000 * n_children
            net_taxable    = max(estate_hors_av - abatt_spouse - abatt_child, 0)

            def droits_succession_fr(base, lien="enfant"):
                if lien == "conjoint": return 0
                brackets = [(8072,0.05),(12109,0.10),(15932,0.15),(552324,0.20),
                           (902838,0.30),(1805677,0.40),(1e9,0.45)]
                t = 0; prev = 0
                for hi, r in brackets:
                    chunk = min(base, hi) - prev
                    if chunk > 0: t += chunk * r
                    prev = hi
                    if base <= hi: break
                return t

            per_child_taxable = net_taxable / max(n_children, 1) if n_children > 0 else net_taxable
            ds_per_child      = droits_succession_fr(per_child_taxable)
            total_ds          = ds_per_child * n_children + av_total_tax

            cols_e = st.columns(3)
            cols_e[0].metric("Patrimoine total",          fmt(estate_val))
            cols_e[1].metric("Droits de succession est.", fmt(total_ds))
            cols_e[2].metric("Patrimoine transmis net",   fmt(estate_val - total_ds))

            st.progress(min(total_ds / estate_val, 1.0),
                text=f"Taux de friction successorale : {total_ds/estate_val*100:.1f}%")

            # Strategies
            st.markdown("** Stratégies de transmission optimales**")
            strategies = []
            if n_children > 0:
                donation_saving = 100000 * n_children * 0.20
                strategies.append((" Donation-partage", f"{100000*n_children:,.0f}€",
                    f"Abattement {100000:,.0f}€/enfant (renouvelable 15 ans) — économie estimée : {fmt(donation_saving)}",
                    "safe"))
            if estate_val > 300000:
                demo_saving = estate_val * 0.20 * 0.25  # rough démembrement saving
                strategies.append((" Démembrement de propriété",
                    f"{estate_val * 0.60:,.0f}€ NP",
                    f"Donner la nue-propriété maintenant (valeur réduite) — économie estimée : {fmt(demo_saving)}", "safe"))
            if has_av:
                strategies.append((" Assurance-vie", fmt(av_amount),
                    f"Abattement {av_exempt_per_bene:,.0f}€/bénéficiaire — hors succession", "safe"))
            if estate_val > 1_000_000:
                strategies.append((" SCI familiale", "Patrimoine immo",
                    "Décote sur parts (15-30%) + donations progressives réduisent l'assiette taxable", "warn"))

            for name, amount, desc, badge in strategies:
                st.markdown(f"""
                <div style="background:rgba(46,204,113,0.04);border:1px solid rgba(46,204,113,0.15);
                    border-left:3px solid #2ECC71;border-radius:8px;padding:12px 16px;margin-bottom:8px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                        <strong style="color:#E0E0E0;font-size:13px;">{name}</strong>
                        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#D4AF37;">{amount}</span>
                    </div>
                    <div style="font-size:12px;color:rgba(148,163,184,0.75);">{desc}</div>
                </div>
                """, unsafe_allow_html=True)

        else:
            estate_rules = {
                "USA":     "Lifetime gift exemption $13.99M (2025) — risque sunset TCJA 2026. Step-up in basis at death. Annual exclusion $19k/person.",
                "UK":      "IHT 40% au-dessus de £500k (allowance £325k + RNRB £175k). 7-year rule pour dons. BPR 100% pour entreprises.",
                "Germany": "Freibetrag enfants 400k€ renouvelable 10 ans. Taux 7-30% selon lien.",
                "Switzerland": "Impôt cantonal (0-7% enfants, 0-36% tiers). Conjoint et descendants directs souvent exonérés.",
            }
            msg = estate_rules.get(country_estate, "Consultez un notaire local pour les règles successorales de ce pays.")
            st.info(f"**{country_estate}** — {msg}")


# 
# TAB 7 — MULTI-JURISDICTION ENGINE
# 
with TABS[6]:
    st.markdown('<p class="tax-section-label"> OPTIMISATION MULTI-JURIDICTIONNELLE · HNWI & EXPATS</p>', unsafe_allow_html=True)

    sub = st.radio("Module", ["Day Counter · Résidence fiscale", "Treaty Navigator · Retenues à la source",
                               "Exit Tax Simulator", "Flag Theory Planner"], horizontal=True)
    st.divider()

    if sub == "Day Counter · Résidence fiscale":
        st.markdown("** Suivi des jours par pays — Règle des 183 jours**")
        c1, c2 = st.columns([1, 2])
        with c1:
            countries_days = {}
            n_countries = st.slider("Nombre de pays", 1, 6, 3)
            for i in range(n_countries):
                cn = st.selectbox(f"Pays {i+1}", list(TAX_RULES.keys()), key=f"dc_{i}")
                dd = st.number_input(f"Jours passés (2025)", 0, 365, [90, 60, 30, 20, 15, 10][i], 1, key=f"dd_{i}")
                countries_days[cn] = dd
        with c2:
            total_days = sum(countries_days.values())
            residency_risk = []
            for country_d, days_d in countries_days.items():
                pct = days_d / 365 * 100
                risk = " RÉSIDENT" if days_d >= 183 else (" Attention" if days_d >= 120 else " OK")
                residency_risk.append({"Pays": country_d, "Jours": days_d,
                    "Pourcentage": f"{pct:.0f}%", "Statut": risk,
                    "Seuil 183j": f"{183 - days_d}j restants" if days_d < 183 else " DÉPASSÉ"})
            rdf = pd.DataFrame(residency_risk)
            st.dataframe(rdf, use_container_width=True, hide_index=True)

            # Pie
            fig_days = go.Figure(go.Pie(
                labels=list(countries_days.keys()) + ["Reste (non renseigné)"],
                values=list(countries_days.values()) + [max(365 - total_days, 0)],
                hole=0.4,
                marker_colors=["#2ECC71","#3498DB","#D4AF37","#E74C3C","#9B59B6","#95A5A6","#BDC3C7"],
            ))
            fig_days.update_layout(**_plotly_dark(), height=300,
                title=dict(text="Répartition des jours (2025)", font=dict(size=12, color="#CBD5E1")))
            st.plotly_chart(fig_days, use_container_width=True)

    elif sub == "Treaty Navigator · Retenues à la source":
        st.markdown("** Conventions fiscales — Retenues à la source applicables**")
        treaty_db = {
            ("USA","France"):     {"div":15,"int":0,"roy":0,"convention":"FR-US 1994"},
            ("USA","UK"):         {"div":15,"int":0,"roy":0,"convention":"US-UK 2001"},
            ("USA","Germany"):    {"div":15,"int":0,"roy":0,"convention":"US-DE 1989"},
            ("USA","Switzerland"):{"div":15,"int":0,"roy":0,"convention":"US-CH 1996"},
            ("USA","Ireland"):    {"div":15,"int":0,"roy":0,"convention":"US-IE 1997"},
            ("USA","Luxembourg"): {"div":15,"int":0,"roy":0,"convention":"US-LU 1996"},
            ("UK","France"):      {"div":15,"int":0,"roy":0,"convention":"UK-FR 2008"},
            ("Germany","France"): {"div":15,"int":0,"roy":5,"convention":"DE-FR 1959"},
            ("Luxembourg","France"):{"div":15,"int":0,"roy":0,"convention":"LU-FR 1958"},
            ("Switzerland","France"):{"div":15,"int":0,"roy":5,"convention":"CH-FR 1966"},
        }
        c_src = st.selectbox("Pays source (émetteur du revenu)", list(TAX_RULES.keys()), key="tr_src")
        c_res = st.selectbox("Pays résidence (receveur)", list(TAX_RULES.keys()), key="tr_res")
        treaty_key  = (c_src, c_res) if (c_src, c_res) in treaty_db else (c_res, c_src) if (c_res, c_src) in treaty_db else None
        if treaty_key:
            t = treaty_db[treaty_key]
            st.success(f"**Convention {t['convention']}** — Dividendes : {t['div']}% · Intérêts : {t['int']}% · Redevances : {t['roy']}%")
            domestic = TAX_RULES.get(c_src, {}).get("div_flat", 0.30) * 100
            saving   = domestic - t["div"]
            if saving > 0:
                st.info(f" Taux domestique {c_src} : {domestic:.0f}% — Économie via convention : {saving:.0f} points")
        else:
            dom_src = TAX_RULES.get(c_src, {}).get("div_flat", 0.30) * 100
            st.warning(f"Pas de convention spécifique indexée — taux domestique {c_src} : {dom_src:.0f}%")

        # Treaty table
        st.markdown("**Extrait de la base conventions**")
        t_rows = [{"Source":" USA","Résidence":" France","Dividendes":"15%","Intérêts":"0%","Redevances":"0%","Convention":"FR-US 1994"},
                  {"Source":" USA","Résidence":" UK",    "Dividendes":"15%","Intérêts":"0%","Redevances":"0%","Convention":"US-UK 2001"},
                  {"Source":" USA","Résidence":" Germany","Dividendes":"15%","Intérêts":"0%","Redevances":"0%","Convention":"US-DE 1989"},
                  {"Source":" USA","Résidence":" Suisse", "Dividendes":"15%","Intérêts":"0%","Redevances":"0%","Convention":"US-CH 1996"},
                  {"Source":" USA","Résidence":" Lux.",   "Dividendes":"15%","Intérêts":"0%","Redevances":"0%","Convention":"US-LU 1996"},
                  {"Source":" UK", "Résidence":" France","Dividendes":"15%","Intérêts":"0%","Redevances":"0%","Convention":"UK-FR 2008"},
                  {"Source":" DE", "Résidence":" France","Dividendes":"15%","Intérêts":"0%","Redevances":"5%","Convention":"DE-FR 1959"},
                  {"Source":" CH", "Résidence":" France","Dividendes":"15%","Intérêts":"0%","Redevances":"5%","Convention":"CH-FR 1966"},
                  {"Source":" JP", "Résidence":" France","Dividendes":"10%","Intérêts":"10%","Redevances":"0%","Convention":"JP-FR 1995"},
                  {"Source":" AU", "Résidence":" France","Dividendes":"15%","Intérêts":"10%","Redevances":"5%","Convention":"AU-FR 2006"},
        ]
        st.dataframe(pd.DataFrame(t_rows), use_container_width=True, hide_index=True)

    elif sub == "Exit Tax Simulator":
        st.markdown("** Simulateur d'Exit Tax — Coût du départ fiscal**")
        c1, c2 = st.columns(2)
        with c1:
            exit_country   = st.selectbox("Pays de départ", ["France","Germany","Spain","Netherlands","Italy"], key="et_src")
            dest_country   = st.selectbox("Pays de destination", list(TAX_RULES.keys()), key="et_dst")
            pv_latentes    = st.number_input("Plus-values latentes totales (€)", 0, 50_000_000, 500000, 50000)
            parts_societe  = st.checkbox("Détention parts de société > 1%", value=False)
            nb_years_after = st.slider("Projection sur N années après départ", 1, 20, 5)
        with c2:
            exit_rules = {
                "France":      (800000,  0.30,  "Exit tax si PV > 800k€ — sursis si destination EEE. 150-0 B ter CGI."),
                "Germany":     (1,       0.25,  "Wegzugsbesteuerung sur parts > 1% — imposition immédiate latentes."),
                "Spain":       (4000000, 0.26,  "Exit tax si PV > 4M€ ou participation > 25% + 1M€."),
                "Netherlands": (1,       0.245, "Fictitious gain realization (box 2) — remboursable si retour 10 ans."),
                "Italy":       (0,       0.26,  "Capital gains crystallized at departure."),
            }
            threshold_exit, rate_exit, note_exit = exit_rules.get(exit_country, (0, 0.20, ""))
            exit_tax_now = max(pv_latentes - threshold_exit, 0) * rate_exit

            # Savings at destination after N years
            dest_cgt = TAX_RULES.get(dest_country, {}).get("cgt_flat", 0.20)
            hypothetical_gains  = pv_latentes * (1.07 ** nb_years_after) - pv_latentes
            tax_stay   = hypothetical_gains * rate_exit
            tax_dest   = hypothetical_gains * dest_cgt
            net_saving_move = tax_stay - tax_dest - exit_tax_now

            st.metric("Exit tax estimée (paiement immédiat)", fmt(exit_tax_now))
            st.metric(f"Imposition si on reste ({nb_years_after}a)", fmt(tax_stay))
            st.metric(f"Imposition à {dest_country} ({nb_years_after}a)", fmt(tax_dest))
            st.metric("Gain net de la mobilité", fmt(net_saving_move),
                     delta_color="normal")
            st.info(f"ℹ {note_exit}")

    elif sub == "Flag Theory Planner":
        st.markdown("** Flag Theory — Combinaisons pays optimales**")
        st.markdown("Concept : utiliser différents pays pour différents usages.")

        flag_options = {
            "Résidence personnelle (qualité de vie)": {
                "options": ["Portugal (IFICI)","Malte","Chypre","Andorre","Monaco","Dubai","Singapour"],
                "notes":   ["IFICI: flat tax 20% revenus étrangers","Citizenship-by-investment","Low tax, EU","0% CGT, ISF, 11k€/an","0% impôt","0% impôt, lifestyle premium","Territorial, 0% CGT"],
            },
            "Structure corporate (fiscalité business)": {
                "options": ["Ireland (12.5% IS)","Luxembourg","Netherlands","Cyprus","Bulgaria (10% IS)","UAE Freezone","Hong Kong"],
                "notes":   ["Double Irish structure","IP box, holding","Participation exemption","IP box 2.5%","IS le plus bas UE","0% tax Freezone","Territorial"],
            },
            "Banking (stabilité + confidentialité)": {
                "options": ["Switzerland","Luxembourg","Singapore","Liechtenstein","Cayman Islands"],
                "notes":   ["FINMA, triangle sécurité AV","CSSF, AV luxembourgeoise","MAS, private banking","LLB, LGT flagship","Offshore, confidentiel"],
            },
            "Investissements (pas de CGT)": {
                "options": ["UAE","Singapore","Hong Kong","Cayman Islands","Belgium (PV privées)","Switzerland (PV privées)"],
                "notes":   ["0% CGT, 0% income","0% CGT","0% CGT","0% tout","0% CGT (privé)","0% CGT (privé)"],
            },
        }
        for flag_type, data in flag_options.items():
            with st.expander(f"**{flag_type}**"):
                fd = pd.DataFrame({"Juridiction": data["options"], "Avantage": data["notes"]})
                st.dataframe(fd, use_container_width=True, hide_index=True)


# 
# TAB 8 — COMPLIANCE & REPORTING
# 
with TABS[7]:
    st.markdown('<p class="tax-section-label"> CONFORMITÉ · DÉCLARATIONS · AUDIT TRAIL</p>', unsafe_allow_html=True)

    comp_sub = st.radio("Section", [
        "Anti-Abuse Checker", "Déclaration Assistant", "CRS/FATCA Tracker", "Audit Trail"
    ], horizontal=True)
    st.divider()

    if comp_sub == "Anti-Abuse Checker":
        st.markdown("** Vérification anti-abus — Chaque stratégie est évaluée**")

        strategies_check = [
            ("PEA avec ETF MSCI World synthétique",
             "Légalement reconnu par les autorités fiscales françaises. ETF synthétique exposé US via swap éligible PEA.",
             " Haute confiance", "safe",
             "Aucun risque connu. Pratique courante validée."),
            ("Tax-Loss Harvesting (France)",
             "Vendre une position en perte et racheter immédiatement. Pas de wash sale rule en France.",
             " Haute confiance", "safe",
             "100% légal. Aucune règle anti-abus applicable en France pour cet usage."),
            ("Rachat partiel AV dans l'abattement annuel",
             "Rachat dans la limite de l'abattement de 4,600€/an (contrat > 8 ans).",
             " Haute confiance", "safe",
             "Avantage légalement prévu. À documenter dans la déclaration 2042."),
            ("Donation-partage avec abattement 100k€",
             "Transmission de 100k€ par enfant, renouvelable tous les 15 ans.",
             " Haute confiance", "safe",
             "Dispositif légal. Acte notarié recommandé."),
            ("Apport-cession (150-0 B ter CGI)",
             "Apport d'entreprise à une holding avant cession — report d'imposition des PV.",
             " Confiance moyenne", "warn",
             "Légal mais encadré. Exige remploi 60% dans 2 ans. Contrôlé par l'administration."),
            ("SCI familiale avec décote sur parts",
             "Créer une SCI, valoriser les parts avec décote (15-30%), puis donner des parts.",
             " Confiance moyenne", "warn",
             "Acceptable si la SCI a une substance réelle. Risque de requalification si abus de droit."),
            ("Assurance-vie luxembourgeoise multi-devises",
             "Souscrire une AV Lux pour diversification fiscale et protection via triangle de sécurité.",
             " Haute confiance", "safe",
             "Légal pour résident français. Déclaration 3916 obligatoire."),
            ("Déménagement fiscal immédiat avant réalisation de PV",
             "Quitter la France juste avant une cession pour éviter l'imposition française.",
             " Risque élevé", "risk",
             "Exit tax (Art. 167 bis CGI) si PV > 800k€ et destination hors EEE. Administration vigilante sur les schémas de délocalisation pré-cession. Consulter un avocat fiscaliste."),
            ("Structure offshore sans substance",
             "Société dans paradis fiscal sans employé, bureau, ni décisions prises localement.",
             " Risque élevé", "risk",
             "CFC rules, BEPS pilier 2, GAAR. Réqualification quasi-certaine en cas de contrôle. À proscrire."),
        ]

        for name, desc, verdict, badge, advice in strategies_check:
            badge_class = f"tbadge tbadge-{badge}"
            bg_color = {"safe":"rgba(46,204,113,0.04)","warn":"rgba(243,156,18,0.04)","risk":"rgba(231,76,60,0.04)"}[badge]
            border_color = {"safe":"rgba(46,204,113,0.25)","warn":"rgba(243,156,18,0.25)","risk":"rgba(231,76,60,0.25)"}[badge]
            left_color = {"safe":"#2ECC71","warn":"#F39C12","risk":"#E74C3C"}[badge]
            st.markdown(f"""
            <div style="background:{bg_color};border:1px solid {border_color};
                border-left:3px solid {left_color};border-radius:8px;
                padding:14px 18px;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <strong style="color:#E0E0E0;font-size:13px;">{name}</strong>
                    <span class="{badge_class}">{verdict}</span>
                </div>
                <div style="font-size:12px;color:rgba(148,163,184,0.8);margin-bottom:6px;">{desc}</div>
                <div style="font-size:11.5px;color:rgba(148,163,184,0.55);font-style:italic;"> {advice}</div>
            </div>
            """, unsafe_allow_html=True)

    elif comp_sub == "Déclaration Assistant":
        st.markdown("** Données pour votre déclaration fiscale (France)**")

        total_gains_real  = 12540.0
        total_losses_real = 4320.0
        total_div         = 3820.0
        total_int         = 540.0

        st.markdown("**Formulaire 2074 — Plus-values mobilières**")
        data_2074 = {
            "Ligne": ["1 — PV brutes réalisées", "2 — MV brutes réalisées", "3 — PV nette imposable"],
            "Montant": [fmt(total_gains_real), fmt(total_losses_real), fmt(total_gains_real - total_losses_real)],
            "Régime": ["PFU 12.8% + PS 17.2%", "Imputable sur PV", "Base imposable PFU"],
        }
        st.dataframe(pd.DataFrame(data_2074), use_container_width=True, hide_index=True)

        st.markdown("**Formulaire 2042 — Revenus de capitaux mobiliers**")
        data_2042 = {
            "Case": ["2DC — Dividendes bruts", "2BH — Intérêts et assimilés", "2CK — Prélèvement déjà effectué"],
            "Montant": [fmt(total_div), fmt(total_int), fmt((total_div + total_int) * 0.128)],
            "Notes": ["Avant abattement 40%", "Livrets, obligations, etc.", "Si PFU prélevé à la source"],
        }
        st.dataframe(pd.DataFrame(data_2042), use_container_width=True, hide_index=True)

        st.markdown("**Formulaire 3916 — Comptes bancaires étrangers**")
        foreign_accounts = [
            {"Institution": "Interactive Brokers LLC", "Pays": "USA", "Numéro": "U123XXXX", "Déclarable": " Oui"},
            {"Institution": "Degiro B.V.", "Pays": "Pays-Bas", "Numéro": "DE456XXXX", "Déclarable": " Oui"},
        ]
        st.dataframe(pd.DataFrame(foreign_accounts), use_container_width=True, hide_index=True)

        st.info(" Pensez à déclarer tout compte étranger via le formulaire 3916, même sans mouvement.")

    elif comp_sub == "CRS/FATCA Tracker":
        st.markdown("** CRS / FATCA — Échanges automatiques d'information**")
        crs_data = [
            {"Institution": "Interactive Brokers USA", "Pays": "USA", "Standard": "FATCA", "Déclaré à": "IRS → DGFiP France", "Statut": " Conforme"},
            {"Institution": "Degiro (NL)", "Pays": "Pays-Bas", "Standard": "CRS/OCDE", "Déclaré à": "Belastingdienst → DGFiP", "Statut": " Conforme"},
            {"Institution": "Saxo Bank (DK)", "Pays": "Danemark", "Standard": "CRS/OCDE", "Déclaré à": "SKAT → DGFiP", "Statut": " Conforme"},
            {"Institution": "Compte crypto (décentralisé)", "Pays": "—", "Standard": "CARF 2026", "Déclaré à": "À confirmer", "Statut": " Vérifier"},
        ]
        st.dataframe(pd.DataFrame(crs_data), use_container_width=True, hide_index=True)
        st.info(" Le nouveau standard CARF (Crypto-Asset Reporting Framework) de l'OCDE s'appliquera à partir de 2026 dans de nombreux pays.")

    elif comp_sub == "Audit Trail":
        st.markdown("** Historique des décisions fiscales**")
        audit_events = [
            (date.today() - timedelta(days=5),  "TLH",        "Vente 200 TSLA — perte récoltée 19,000€ — substitut DRIV acheté",       "safe"),
            (date.today() - timedelta(days=18), "Enveloppe",  "Versement 12,000€ sur PEA — positions AAPL transférées vers PEA",        "safe"),
            (date.today() - timedelta(days=35), "AV",         "Rachat partiel AV : 6,200€ — dont 2,100€ gains (< abattement 4,600€)",  "safe"),
            (date.today() - timedelta(days=62), "Déclaration","Formulaire 2074 soumis — PV nette 8,220€ — impôt PFU 2,466€",            "safe"),
            (date.today() - timedelta(days=90), "TLH",        "Vente 300 INTC — perte récoltée 8,400€ — substitut SOXX acheté",        "safe"),
            (date.today() - timedelta(days=120),"Enveloppe",  "Ouverture PER — premier versement 5,000€ — déductible 2025",             "safe"),
            (date.today() - timedelta(days=180),"Compliance", "3916 déposé : 2 comptes étrangers déclarés (IB + Degiro)",               "safe"),
        ]
        audit_df = pd.DataFrame(audit_events, columns=["Date","Type","Événement","Status"])
        audit_df["Date"] = audit_df["Date"].apply(lambda d: d.strftime("%d/%m/%Y"))
        audit_df[""] = ""
        st.dataframe(audit_df[["Date","Type","","Événement"]], use_container_width=True, hide_index=True)

        total_harvested  = 27400
        total_av_saved   = 630
        total_all        = total_harvested * 0.30 + total_av_saved
        st.markdown(f"""
        <div class="tax-savings-block" style="margin-top:16px">
            <span class="tax-savings-label"><span class="tax-live-dot"></span>Économies documentées YTD</span>
            <span class="tax-savings-number">{total_all:,.0f} €</span>
            <div class="tax-savings-sub">
                TLH : {total_harvested*0.30:,.0f}€ · Abattement AV : {total_av_saved:,.0f}€ · Tout justifié & documenté
            </div>
        </div>
        """, unsafe_allow_html=True)
