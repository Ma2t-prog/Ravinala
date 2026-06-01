"""
Ravinala — Report Generator
Generates professional Term Sheets, Scenario Books and Risk Summaries
directly in-process using ReportLab. No backend required.
"""

from __future__ import annotations

import io
from datetime import datetime

import streamlit as st

# ── ReportLab imports ─────────────────────────────────────────────────────
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    _RL_OK = True
except ImportError:
    _RL_OK = False

DEFAULT_ISSUER = "Ravinala Capital"
_ACCENT = colors.HexColor("#00d9ff")
_DARK   = colors.HexColor("#0d121e")
_MID    = colors.HexColor("#1a2235")
_BORDER = colors.HexColor("#1e293b")
_TEXT   = colors.HexColor("#f1f5f9")
_MUTED  = colors.HexColor("#64748b")
_GREEN  = colors.HexColor("#10b981")
_RED    = colors.HexColor("#ef4444")
_GOLD   = colors.HexColor("#f59e0b")
_PAGE_W, _PAGE_H = A4


# ═══════════════════════════════════════════════════════════════════════════
# PDF BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def _base_doc(buf: io.BytesIO, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=title,
        author=DEFAULT_ISSUER,
    )


def _styles():
    base = getSampleStyleSheet()
    s = {}
    s["h1"] = ParagraphStyle("h1", parent=base["Normal"],
        fontSize=20, leading=24, textColor=_TEXT, fontName="Helvetica-Bold",
        spaceAfter=4)
    s["h2"] = ParagraphStyle("h2", parent=base["Normal"],
        fontSize=13, leading=16, textColor=_ACCENT, fontName="Helvetica-Bold",
        spaceBefore=14, spaceAfter=4)
    s["h3"] = ParagraphStyle("h3", parent=base["Normal"],
        fontSize=10, leading=13, textColor=_TEXT, fontName="Helvetica-Bold",
        spaceBefore=8, spaceAfter=2)
    s["body"] = ParagraphStyle("body", parent=base["Normal"],
        fontSize=9, leading=13, textColor=colors.HexColor("#94a3b8"),
        fontName="Helvetica")
    s["mono"] = ParagraphStyle("mono", parent=base["Normal"],
        fontSize=8.5, leading=12, textColor=_TEXT, fontName="Courier")
    s["label"] = ParagraphStyle("label", parent=base["Normal"],
        fontSize=7.5, leading=10, textColor=_MUTED, fontName="Helvetica-Bold",
        spaceAfter=1)
    s["center"] = ParagraphStyle("center", parent=base["Normal"],
        fontSize=9, leading=13, textColor=_MUTED, alignment=TA_CENTER)
    s["disclaimer"] = ParagraphStyle("disclaimer", parent=base["Normal"],
        fontSize=7, leading=10, textColor=_MUTED, fontName="Helvetica",
        alignment=TA_CENTER)
    return s


def _kv_table(rows: list[tuple[str, str]], col_widths=None) -> Table:
    """Two-column key/value table with dark styling."""
    col_widths = col_widths or [7 * cm, 10.6 * cm]
    data = [[Paragraph(f"<font color='#64748b'><b>{k}</b></font>", ParagraphStyle(
                "kl", fontSize=8, leading=11, fontName="Helvetica-Bold")),
             Paragraph(f"<font color='#f1f5f9'>{v}</font>", ParagraphStyle(
                "kv", fontSize=8.5, leading=12, fontName="Courier"))]
            for k, v in rows]
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), _MID),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_MID, colors.HexColor("#111827")]),
        ("GRID",        (0, 0), (-1, -1), 0.3, _BORDER),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _header_block(story: list, s: dict, title: str, subtitle: str, p: dict) -> None:
    """Dark header band with issuer + product name."""
    now = datetime.utcnow().strftime("%d %b %Y — %H:%M UTC")
    story.append(Paragraph(p.get("issuer", DEFAULT_ISSUER).upper(), ParagraphStyle(
        "iss", fontSize=8, leading=10, textColor=_ACCENT, fontName="Helvetica-Bold",
        letterSpacing=2)))
    story.append(Spacer(1, 4))
    story.append(Paragraph(title, s["h1"]))
    story.append(Paragraph(subtitle, s["body"]))
    story.append(HRFlowable(width="100%", thickness=1, color=_ACCENT, spaceAfter=8))
    story.append(Paragraph(f"Generated {now}  ·  CONFIDENTIAL  ·  FOR INSTITUTIONAL USE ONLY", s["disclaimer"]))
    story.append(Spacer(1, 12))


def _footer_disclaimer() -> list:
    s = _styles()
    return [
        Spacer(1, 16),
        HRFlowable(width="100%", thickness=0.5, color=_BORDER, spaceAfter=6),
        Paragraph(
            "This document is produced by Ravinala Capital for informational purposes only and does not constitute "
            "investment advice, an offer, or a solicitation. Past performance is not indicative of future results. "
            "Financial instruments described herein carry risk of loss. © Ravinala Capital 2026 — All rights reserved.",
            s["disclaimer"],
        ),
    ]


# ── TERM SHEET ─────────────────────────────────────────────────────────────

def build_termsheet(p: dict) -> bytes:
    buf = io.BytesIO()
    doc = _base_doc(buf, "Term Sheet")
    s = _styles()
    story = []

    ptype  = p.get("product_type", "").replace("_", " ").title()
    und    = p.get("underlying", "N/A")
    pname  = p.get("product_name") or f"{ptype} on {und}"
    ccy    = p.get("currency", "USD")
    spot   = p.get("spot", 0.0)
    strike = p.get("strike", 0.0)
    mat    = p.get("maturity_years", 1.0)
    vol    = p.get("volatility", 0.20)
    rfr    = p.get("risk_free_rate", 0.03)
    div    = p.get("dividend_yield", 0.0)
    cprot  = p.get("capital_protection", 0.90)
    coupon = p.get("coupon_rate", 0.08)
    blevel = p.get("barrier_level")
    btype  = p.get("barrier_type") or "N/A"
    client = p.get("client_name") or "Institutional Investor"

    # Greeks (Black-Scholes approximation)
    import math
    try:
        from scipy.stats import norm
        d1 = (math.log(spot / strike) + (rfr - div + 0.5 * vol**2) * mat) / (vol * math.sqrt(mat))
        d2 = d1 - vol * math.sqrt(mat)
        delta = round(norm.cdf(d1), 4) if "call" in ptype.lower() else round(norm.cdf(d1) - 1, 4)
        gamma = round(norm.pdf(d1) / (spot * vol * math.sqrt(mat)), 6)
        theta = round(-(spot * norm.pdf(d1) * vol) / (2 * math.sqrt(mat)) / 365, 4)
        vega  = round(spot * norm.pdf(d1) * math.sqrt(mat) / 100, 4)
        rho   = round(strike * mat * math.exp(-rfr * mat) * norm.cdf(d2) / 100, 4)
    except Exception:
        delta = gamma = theta = vega = rho = "N/A"

    _header_block(story, s, pname, f"{ptype}  ·  {und}  ·  {ccy}", p)

    story.append(Paragraph("PRODUCT CHARACTERISTICS", s["h2"]))
    story.append(_kv_table([
        ("Product Type",       ptype),
        ("Underlying",         und),
        ("Currency",           ccy),
        ("Client / Investor",  client),
        ("Issuer",             p.get("issuer", DEFAULT_ISSUER)),
        ("Initial Spot (S₀)",  f"{spot:,.2f}"),
        ("Strike (K)",         f"{strike:,.2f}  ({strike/spot*100:.1f}% moneyness)"),
        ("Maturity",           f"{mat:.2f} year(s)"),
        ("Implicit Vol (σ)",   f"{vol*100:.2f}%"),
        ("Risk-Free Rate (r)", f"{rfr*100:.3f}%"),
        ("Dividend Yield (q)", f"{div*100:.3f}%"),
        ("Capital Protection", f"{cprot*100:.0f}%"),
        ("Coupon / Yield",     f"{coupon*100:.2f}% p.a."),
    ]))

    if blevel:
        story.append(Spacer(1, 8))
        story.append(Paragraph("BARRIER", s["h2"]))
        story.append(_kv_table([
            ("Barrier Level", f"{blevel*100:.0f}%  ({spot*blevel:,.2f} {ccy})"),
            ("Barrier Type",  btype),
        ]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("GREEKS  (Black-Scholes)", s["h2"]))
    story.append(_kv_table([
        ("Delta (Δ)",  str(delta)),
        ("Gamma (Γ)",  str(gamma)),
        ("Theta (Θ)",  f"{theta} per day"),
        ("Vega  (ν)",  f"{vega} per 1% vol"),
        ("Rho   (ρ)",  f"{rho} per 1% rate"),
    ]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("MARKET SCENARIOS", s["h2"]))
    scenarios = [
        ("Stress Bear",  spot * 0.70,  -30.0),
        ("Bear",         spot * 0.85,  -15.0),
        ("Base",         spot * 1.00,    0.0),
        ("Bull",         spot * 1.15,  +15.0),
        ("Strong Bull",  spot * 1.30,  +30.0),
    ]
    scen_data = [["Scenario", "Underlying Level", "Perf vs Spot", "Est. P&L (%)"],
                 *[[sc, f"{lv:,.2f}", f"{pf:+.1f}%",
                    f"{max(-1.0, pf/100 * (1 - cprot) + coupon * mat):.2%}"]
                   for sc, lv, pf in scenarios]]
    scen_table = Table(scen_data, colWidths=[4.5*cm, 4.2*cm, 4.2*cm, 4.8*cm], hAlign="LEFT")
    scen_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), _ACCENT),
        ("TEXTCOLOR",    (0, 0), (-1, 0), _DARK),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_MID, colors.HexColor("#111827")]),
        ("FONTSIZE",     (0, 1), (-1, -1), 8),
        ("TEXTCOLOR",    (0, 1), (-1, -1), _TEXT),
        ("FONTNAME",     (0, 1), (-1, -1), "Courier"),
        ("GRID",         (0, 0), (-1, -1), 0.3, _BORDER),
        ("ALIGN",        (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(scen_table)

    story.extend(_footer_disclaimer())
    doc.build(story)
    return buf.getvalue()


# ── SCENARIO BOOK ──────────────────────────────────────────────────────────

def build_scenariobook(p: dict, language: str = "fr") -> bytes:
    buf = io.BytesIO()
    doc = _base_doc(buf, "Scenario Book")
    s = _styles()
    story = []

    ptype  = p.get("product_type", "").replace("_", " ").title()
    und    = p.get("underlying", "N/A")
    pname  = p.get("product_name") or f"{ptype} on {und}"
    ccy    = p.get("currency", "USD")
    spot   = p.get("spot", 0.0)
    vol    = p.get("volatility", 0.20)
    mat    = p.get("maturity_years", 1.0)
    coupon = p.get("coupon_rate", 0.08)
    cprot  = p.get("capital_protection", 0.90)

    _header_block(story, s, f"SCENARIO BOOK — {pname}",
                  f"Full scenario analysis  ·  {und}  ·  {ccy}", p)

    # Executive summary
    story.append(Paragraph("EXECUTIVE SUMMARY", s["h2"]))
    lang_summary = {
        "fr": (
            f"Ce Scenario Book analyse le produit <b>{pname}</b> sur le sous-jacent <b>{und}</b>. "
            f"L'instrument offre une protection du capital à <b>{cprot*100:.0f}%</b> à maturité "
            f"({mat:.1f} an(s)), avec un rendement cible de <b>{coupon*100:.1f}% p.a.</b> "
            f"La volatilité implicite retenue est de <b>{vol*100:.1f}%</b>. "
            "Les scénarios présentés couvrent des chocs de -40% à +40% sur le sous-jacent, "
            "avec analyse de sensibilité aux paramètres clés (vol, taux, dividendes)."
        ),
        "en": (
            f"This Scenario Book analyses the product <b>{pname}</b> on underlying <b>{und}</b>. "
            f"The instrument offers <b>{cprot*100:.0f}%</b> capital protection at maturity "
            f"({mat:.1f} year(s)) with a target yield of <b>{coupon*100:.1f}% p.a.</b> "
            f"Implied volatility used: <b>{vol*100:.1f}%</b>. "
            "Scenarios cover shocks from -40% to +40% on the underlying, "
            "with full sensitivity analysis across vol, rates and dividends."
        ),
    }
    story.append(Paragraph(lang_summary.get(language, lang_summary["en"]), s["body"]))
    story.append(Spacer(1, 8))

    # Sensitivity table
    story.append(Paragraph("SENSITIVITY ANALYSIS — UNDERLYING SHOCKS", s["h2"]))
    shocks = [-40, -30, -20, -10, 0, +10, +20, +30, +40]
    headers = ["Shock (%)", "Underlying", "Capital at Risk", "Coupon Effect", "Net P&L Est."]
    rows = [headers]
    for sh in shocks:
        lv  = spot * (1 + sh / 100)
        cap = max(cprot - 1.0, sh / 100 * (1 - cprot))
        net = cap + coupon * mat
        rows.append([
            f"{sh:+d}%",
            f"{lv:,.2f}",
            f"{cap*100:+.1f}%",
            f"+{coupon*mat*100:.2f}%",
            f"{net*100:+.2f}%",
        ])
    sens_t = Table(rows, colWidths=[2.8*cm, 4*cm, 4*cm, 4*cm, 3.6*cm], hAlign="LEFT")
    sens_t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), _ACCENT),
        ("TEXTCOLOR",    (0, 0), (-1, 0), _DARK),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_MID, colors.HexColor("#111827")]),
        ("TEXTCOLOR",    (0, 1), (-1, -1), _TEXT),
        ("FONTNAME",     (0, 1), (-1, -1), "Courier"),
        ("GRID",         (0, 0), (-1, -1), 0.3, _BORDER),
        ("ALIGN",        (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        # Color negative net P&L rows red
        *[("TEXTCOLOR", (4, i+1), (4, i+1), _RED if float(rows[i+1][4].replace("%","")) < 0 else _GREEN)
          for i in range(len(shocks))],
    ]))
    story.append(sens_t)

    # Vol sensitivity
    story.append(Paragraph("VOLATILITY SENSITIVITY", s["h2"]))
    vols = [vol * m for m in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]]
    vol_rows = [["Vol Scenario", "Implied Vol", "Estimated Vega Impact", "Adjusted Yield"]]
    for i, v in enumerate(vols):
        labels = ["Vol Crush -50%", "Vol -25%", "Base Case", "Vol +25%", "Vol Spike +50%", "Vol Dbl +100%"]
        vega_impact = (v - vol) * spot * 0.01
        adj_yield = coupon + (v - vol) * 0.5
        vol_rows.append([labels[i], f"{v*100:.1f}%", f"{vega_impact:+.2f} {ccy}", f"{adj_yield*100:.2f}%"])
    vol_t = Table(vol_rows, colWidths=[5*cm, 4*cm, 5*cm, 4.6*cm], hAlign="LEFT")
    vol_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _GOLD),
        ("TEXTCOLOR",     (0, 0), (-1, 0), _DARK),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_MID, colors.HexColor("#111827")]),
        ("TEXTCOLOR",     (0, 1), (-1, -1), _TEXT),
        ("FONTNAME",      (0, 1), (-1, -1), "Courier"),
        ("GRID",          (0, 0), (-1, -1), 0.3, _BORDER),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(vol_t)

    # Risk metrics
    story.append(Paragraph("KEY RISK METRICS", s["h2"]))
    import math
    try:
        from scipy.stats import norm
        d1 = (math.log(spot / p.get("strike", spot)) + (p.get("risk_free_rate", 0.03) + 0.5 * vol**2) * mat) / (vol * math.sqrt(mat))
        var_95 = spot * vol * math.sqrt(mat / 252) * norm.ppf(0.05)
        cvar_95 = spot * vol * math.sqrt(mat / 252) * norm.pdf(norm.ppf(0.05)) / 0.05
        sharpe = (coupon - p.get("risk_free_rate", 0.03)) / vol if vol > 0 else 0
    except Exception:
        var_95 = cvar_95 = sharpe = 0
    story.append(_kv_table([
        ("VaR 95% (1-day)",    f"{abs(var_95):,.2f} {ccy}  ({abs(var_95)/spot*100:.2f}%)"),
        ("CVaR 95% (1-day)",   f"{abs(cvar_95):,.2f} {ccy}  ({abs(cvar_95)/spot*100:.2f}%)"),
        ("Sharpe Ratio (est)", f"{sharpe:.3f}"),
        ("Max Drawdown (est)", f"{(1-cprot)*100:.1f}%  (capital protection floor)"),
        ("Break-even Level",   f"{p.get('strike', spot) * (1 - coupon*mat):,.2f} {ccy}"),
    ]))

    story.extend(_footer_disclaimer())
    doc.build(story)
    return buf.getvalue()


# ── RISK SUMMARY ───────────────────────────────────────────────────────────

def build_risksummary(portfolio: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = _base_doc(buf, "Risk Summary")
    s = _styles()
    story = []

    import math
    now = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
    story.append(Paragraph("RAVINALA CAPITAL", ParagraphStyle(
        "iss2", fontSize=8, leading=10, textColor=_ACCENT, fontName="Helvetica-Bold", letterSpacing=2)))
    story.append(Spacer(1, 4))
    story.append(Paragraph("PORTFOLIO RISK SUMMARY", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=_ACCENT, spaceAfter=8))
    story.append(Paragraph(f"Generated {now}  ·  {len(portfolio)} position(s)  ·  CONFIDENTIAL", s["disclaimer"]))
    story.append(Spacer(1, 12))

    # Per-position table
    story.append(Paragraph("POSITION DETAILS", s["h2"]))
    pos_rows = [["#", "Product", "Underlying", "Spot", "Strike", "Vol", "Mat", "Coupon"]]
    total_notional = 0
    agg_var = 0
    for i, p in enumerate(portfolio, 1):
        ptype = p.get("product_type", "N/A").replace("_", " ").title()
        spot  = p.get("spot", 0.0)
        vol   = p.get("volatility", 0.20)
        mat   = p.get("maturity_years", 1.0)
        total_notional += spot
        try:
            from scipy.stats import norm
            agg_var += spot * vol * math.sqrt(mat / 252) * norm.ppf(0.05)
        except Exception:
            pass
        pos_rows.append([
            str(i), ptype[:18],
            p.get("underlying", "N/A")[:10],
            f"{spot:,.0f}",
            f"{p.get('strike', 0):,.0f}",
            f"{vol*100:.1f}%",
            f"{mat:.1f}y",
            f"{p.get('coupon_rate', 0)*100:.1f}%",
        ])

    pos_t = Table(pos_rows, colWidths=[0.9*cm, 4.2*cm, 2.6*cm, 2.4*cm, 2.4*cm, 1.8*cm, 1.6*cm, 2*cm], hAlign="LEFT")
    pos_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), _ACCENT),
        ("TEXTCOLOR",     (0, 0), (-1, 0), _DARK),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [_MID, colors.HexColor("#111827")]),
        ("TEXTCOLOR",     (0, 1), (-1, -1), _TEXT),
        ("FONTNAME",      (0, 1), (-1, -1), "Courier"),
        ("GRID",          (0, 0), (-1, -1), 0.3, _BORDER),
        ("ALIGN",         (3, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    story.append(pos_t)

    # Aggregate metrics
    story.append(Paragraph("AGGREGATE RISK METRICS", s["h2"]))
    avg_vol   = sum(p.get("volatility", 0.2) for p in portfolio) / len(portfolio)
    avg_cprot = sum(p.get("capital_protection", 0.9) for p in portfolio) / len(portfolio)
    risk_score = min(100, int(avg_vol * 300 + (1 - avg_cprot) * 100))
    try:
        from scipy.stats import norm
        agg_cvar = abs(agg_var) * norm.pdf(norm.ppf(0.05)) / 0.05
    except Exception:
        agg_cvar = 0

    story.append(_kv_table([
        ("Positions",              str(len(portfolio))),
        ("Aggregate Notional",     f"{total_notional:,.2f}"),
        ("Portfolio VaR 95% 1d",   f"{abs(agg_var):,.2f}  ({abs(agg_var)/max(total_notional,1)*100:.2f}%)"),
        ("Portfolio CVaR 95% 1d",  f"{agg_cvar:,.2f}  ({agg_cvar/max(total_notional,1)*100:.2f}%)"),
        ("Avg Implied Vol",        f"{avg_vol*100:.2f}%"),
        ("Avg Capital Protection", f"{avg_cprot*100:.1f}%"),
        ("Composite Risk Score",   f"{risk_score} / 100"),
    ]))

    # Risk score band
    story.append(Spacer(1, 8))
    if risk_score < 30:
        band, col = "LOW RISK", _GREEN
    elif risk_score < 60:
        band, col = "MODERATE RISK", _GOLD
    else:
        band, col = "HIGH RISK", _RED
    band_t = Table([[Paragraph(f"<b>{band}</b>  ·  Score {risk_score}/100", ParagraphStyle(
        "band", fontSize=11, leading=14, textColor=col, fontName="Helvetica-Bold", alignment=TA_CENTER))]],
        colWidths=[17.8*cm])
    band_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#111827")),
        ("BOX",        (0, 0), (0, 0), 1.5, col),
        ("TOPPADDING",    (0, 0), (0, 0), 10),
        ("BOTTOMPADDING", (0, 0), (0, 0), 10),
    ]))
    story.append(band_t)

    story.extend(_footer_disclaimer())
    doc.build(story)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════════════

st.title("Report Generator")
st.caption("Term Sheets, Scenario Books and Risk Summaries — generated in-process, no backend required.")
st.divider()

if not _RL_OK:
    st.error("ReportLab is not installed. Run: `uv pip install reportlab`")
    st.stop()

# ── Product parameters ─────────────────────────────────────────────────────
st.subheader("Product Parameters")

col1, col2, col3 = st.columns(3)
with col1:
    product_type = st.selectbox("Product Type", options=[
        "european_call", "european_put", "barrier", "autocall", "phoenix",
        "himalaya", "cliquet", "variance_swap", "convertible_bond", "cln",
    ], format_func=lambda x: x.replace("_", " ").title(), key="doc_product_type")
    underlying = st.text_input("Underlying", value="CAC 40", key="doc_underlying")
    currency   = st.selectbox("Currency", ["EUR", "USD", "GBP", "CHF", "JPY"], key="doc_currency")

with col2:
    spot    = st.number_input("Spot (S₀)",        value=7500.0, step=50.0,  key="doc_spot")
    strike  = st.number_input("Strike (K)",        value=7500.0, step=50.0,  key="doc_strike")
    maturity= st.number_input("Maturity (years)", value=1.0, min_value=0.1, max_value=10.0, step=0.25, key="doc_maturity")

with col3:
    risk_free  = st.number_input("Risk-Free Rate (%)",    value=3.0,  step=0.1, key="doc_rfr")  / 100
    volatility = st.number_input("Implied Vol (%)",       value=20.0, step=0.5, key="doc_vol")  / 100
    dividend   = st.number_input("Dividend / Carry (%)", value=0.0,  step=0.1, key="doc_div")  / 100

col4, col5, col6 = st.columns(3)
with col4:
    capital_prot = st.number_input("Capital Protection (%)", value=90.0, step=5.0, key="doc_cap")    / 100
    coupon_rate  = st.number_input("Coupon / Yield (%)",     value=8.0,  step=0.5, key="doc_coupon") / 100
with col5:
    barrier_level = st.number_input("Barrier Level (%)", value=60.0, step=5.0, key="doc_barrier") / 100
    barrier_type  = st.selectbox("Barrier Type",
                                  ["—", "down-and-in", "down-and-out", "up-and-in", "up-and-out"],
                                  key="doc_barrier_type")
with col6:
    product_name = st.text_input("Product Name", value="", key="doc_pname",
                                  placeholder="e.g. Phoenix Europe Q1 2026")

with st.expander("Customisation", expanded=False):
    cust1, cust2 = st.columns(2)
    with cust1:
        issuer = st.text_input("Issuer", value=DEFAULT_ISSUER, key="doc_issuer")
    with cust2:
        client_name = st.text_input("Client Name", value="", key="doc_client",
                                     placeholder="e.g. Crédit Agricole AM")

base_params: dict = {
    "product_type":      product_type,
    "underlying":        underlying,
    "currency":          currency,
    "spot":              spot,
    "strike":            strike,
    "maturity_years":    maturity,
    "risk_free_rate":    risk_free,
    "volatility":        volatility,
    "dividend_yield":    dividend,
    "capital_protection": capital_prot,
    "coupon_rate":       coupon_rate,
    "barrier_level":     barrier_level if barrier_level < 1.0 else None,
    "barrier_type":      None if barrier_type == "—" else barrier_type,
    "product_name":      product_name.strip() or None,
    "issuer":            issuer,
    "client_name":       client_name.strip() or None,
    "notional":          1.0,
}

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────
tabs = st.tabs(["Term Sheet", "Scenario Book", "Risk Summary"])

# Tab 1: Term Sheet
with tabs[0]:
    st.markdown("**Term Sheet** — 1-page institutional document: characteristics, Greeks, market scenarios.")
    if st.button("Generate Term Sheet", type="primary", key="btn_termsheet"):
        with st.spinner("Building PDF…"):
            try:
                pdf_bytes = build_termsheet(base_params)
                pname = (product_name or product_type).replace(" ", "_")
                st.success("Term Sheet generated.")
                st.download_button(
                    label="Download Term Sheet (PDF)",
                    data=pdf_bytes,
                    file_name=f"termsheet_{pname}.pdf",
                    mime="application/pdf",
                )
            except Exception as exc:
                st.error(f"Generation failed: {exc}")

# Tab 2: Scenario Book
with tabs[1]:
    st.markdown("**Scenario Book** — Multi-page: executive summary, sensitivity analysis, vol surface, risk metrics.")
    sb_col1, sb_col2 = st.columns(2)
    with sb_col1:
        language = st.selectbox("Document Language", ["fr", "en"],
                                 format_func=lambda x: "Francais" if x == "fr" else "English",
                                 key="doc_language")
    if st.button("Generate Scenario Book", type="primary", key="btn_scenariobook"):
        with st.spinner("Building PDF…"):
            try:
                pdf_bytes = build_scenariobook(base_params, language)
                pname = (product_name or product_type).replace(" ", "_")
                st.success("Scenario Book generated.")
                st.download_button(
                    label="Download Scenario Book (PDF)",
                    data=pdf_bytes,
                    file_name=f"scenariobook_{pname}.pdf",
                    mime="application/pdf",
                )
            except Exception as exc:
                st.error(f"Generation failed: {exc}")

# Tab 3: Risk Summary
with tabs[2]:
    st.markdown("**Risk Summary** — Aggregate portfolio risk: VaR, CVaR, composite risk score.")

    if "doc_portfolio" not in st.session_state:
        st.session_state["doc_portfolio"] = []

    rs_col1, rs_col2 = st.columns([3, 1])
    with rs_col1:
        if st.button("+ Add current position to portfolio", key="btn_add_pos"):
            pos = dict(base_params)
            pos["product_name"] = product_name or product_type
            if len(st.session_state["doc_portfolio"]) < 10:
                st.session_state["doc_portfolio"].append(pos)
                st.success("Position added.")
            else:
                st.warning("Maximum 10 positions.")
    with rs_col2:
        if st.button("Clear portfolio", key="btn_clear_pos"):
            st.session_state["doc_portfolio"] = []
            st.info("Portfolio cleared.")

    portfolio = st.session_state.get("doc_portfolio", [])
    if portfolio:
        st.markdown(f"**{len(portfolio)} position(s) in portfolio:**")
        for i, pos in enumerate(portfolio, 1):
            st.markdown(
                f"{i}. **{pos.get('product_type','').replace('_',' ').title()}** "
                f"on {pos.get('underlying','N/A')} — "
                f"Spot {pos.get('spot',0):,.0f} | "
                f"Vol {pos.get('volatility',0)*100:.0f}% | "
                f"Mat {pos.get('maturity_years',0):.1f}y"
            )

    gen_disabled = len(portfolio) == 0
    if st.button("Generate Risk Summary", type="primary", key="btn_risksummary", disabled=gen_disabled):
        with st.spinner(f"Aggregating {len(portfolio)} position(s)…"):
            try:
                pdf_bytes = build_risksummary(portfolio)
                st.success("Risk Summary generated.")
                st.download_button(
                    label="Download Risk Summary (PDF)",
                    data=pdf_bytes,
                    file_name="risksummary_portfolio.pdf",
                    mime="application/pdf",
                )
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
    elif gen_disabled:
        st.caption("Add at least one position to enable generation.")

st.divider()
st.caption(
    "Documents are for institutional use only and do not constitute investment advice. "
    "— Ravinala Capital © 2026"
)
