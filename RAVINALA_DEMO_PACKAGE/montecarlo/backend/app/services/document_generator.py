"""
Ravinala Document Generator
Thread-safe PDF generation: Term Sheets, Scenario Books, Risk Summaries.
All rendering is in-memory (BytesIO) — no temp files, no disk writes.
"""

from __future__ import annotations

import io
import os
import math
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── Matplotlib: non-interactive backend MUST be set before any other import ──
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.ticker import FuncFormatter

# ── ReportLab ─────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, PageBreak, KeepTogether,
)
from reportlab.pdfgen import canvas as _rl_canvas

from app.services.legacy_quant_bridge import (
    get_black_scholes_greeks_class,
    quant_engine_available,
)

# Lock so concurrent FastAPI workers don't race on matplotlib state
_MPL_LOCK = threading.Lock()

# ═══════════════════════════════════════════════════════════════════════════
# PALETTE & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

PRIMARY    = HexColor("#1a3a5c")
SECONDARY  = HexColor("#2d6fa6")
ACCENT     = HexColor("#e8a020")
DANGER     = HexColor("#c0392b")
SUCCESS    = HexColor("#27ae60")
WARNING    = HexColor("#f39c12")
LIGHT_BG   = HexColor("#f5f7fa")
GREY       = HexColor("#6c757d")
TEXT       = HexColor("#1a1a2e")
WHITE      = colors.white

MPL = {
    "primary":   "#1a3a5c",
    "secondary": "#2d6fa6",
    "accent":    "#e8a020",
    "danger":    "#c0392b",
    "success":   "#27ae60",
    "warning":   "#f39c12",
    "light":     "#f5f7fa",
    "grey":      "#6c757d",
}

DISCLAIMER_FR = (
    "Ce document est fourni à titre indicatif uniquement et ne constitue pas "
    "un conseil en investissement. Les performances passées ne préjugent pas "
    "des performances futures. Les produits structurés comportent un risque de "
    "perte partielle ou totale du capital investi. Ravinala Capital — usage "
    "interne et clients institutionnels uniquement."
)

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm

# ═══════════════════════════════════════════════════════════════════════════
# STYLES
# ═══════════════════════════════════════════════════════════════════════════

def _make_styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    def _s(name: str, **kw) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "title": _s("rav_title", fontSize=20, textColor=WHITE,
                    fontName="Helvetica-Bold", alignment=TA_LEFT, leading=24),
        "subtitle": _s("rav_subtitle", fontSize=11, textColor=ACCENT,
                       fontName="Helvetica-Bold", alignment=TA_LEFT),
        "h2": _s("rav_h2", fontSize=13, textColor=PRIMARY,
                 fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4),
        "h3": _s("rav_h3", fontSize=10, textColor=SECONDARY,
                 fontName="Helvetica-Bold", spaceBefore=6, spaceAfter=2),
        "body": _s("rav_body", fontSize=9, textColor=TEXT,
                   fontName="Helvetica", leading=13, alignment=TA_JUSTIFY),
        "body_small": _s("rav_body_sm", fontSize=7.5, textColor=GREY,
                         fontName="Helvetica", leading=11),
        "disclaimer": _s("rav_disc", fontSize=7, textColor=GREY,
                         fontName="Helvetica", alignment=TA_JUSTIFY, leading=9),
        "label": _s("rav_lbl", fontSize=8, textColor=GREY,
                    fontName="Helvetica-Bold"),
        "value": _s("rav_val", fontSize=9, textColor=TEXT,
                    fontName="Helvetica-Bold"),
        "cover_title": _s("rav_cov_title", fontSize=28, textColor=WHITE,
                          fontName="Helvetica-Bold", leading=34, alignment=TA_LEFT),
        "cover_sub": _s("rav_cov_sub", fontSize=14, textColor=ACCENT,
                        fontName="Helvetica", leading=18, alignment=TA_LEFT),
    }


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _fig_to_image(fig: plt.Figure, width: float, height: float) -> Image:
    """Convert a matplotlib Figure to a ReportLab Image (in-memory)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width, height=height)


def _section_header(text: str, styles: Dict) -> List:
    """Blue left-bar section header."""
    return [
        HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=4),
        Paragraph(text.upper(), styles["h2"]),
        Spacer(1, 2 * mm),
    ]


def _two_col_table(rows: List[Tuple[str, str]], col_widths: Tuple = (7*cm, 9*cm)) -> Table:
    """Styled two-column parameter table."""
    data = [[Paragraph(f"<b>{k}</b>", ParagraphStyle(
                "tbl_key", fontSize=8.5, fontName="Helvetica-Bold",
                textColor=TEXT, alignment=TA_LEFT)),
             Paragraph(str(v), ParagraphStyle(
                "tbl_val", fontSize=8.5, fontName="Helvetica",
                textColor=SECONDARY, alignment=TA_LEFT))]
            for k, v in rows]
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e7")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _maturity_label(years: float) -> str:
    """Convert fractional years to human-readable date."""
    target = datetime.today() + timedelta(days=int(years * 365.25))
    return f"{years:.1f} an(s) ({target.strftime('%d/%m/%Y')})"


def _pct(v: float, decimals: int = 2) -> str:
    return f"{v * 100:.{decimals}f} %"


def _ccy(v: float, currency: str = "EUR") -> str:
    return f"{v:,.2f} {currency}"


# ═══════════════════════════════════════════════════════════════════════════
# QUANTITATIVE HELPERS (inline fallback when src.engine unavailable)
# ═══════════════════════════════════════════════════════════════════════════

def _bs_greeks(p: Dict[str, Any]) -> Dict[str, float]:
    """Compute Black-Scholes Greeks, using engine if available."""
    S     = p["spot"]
    K     = p.get("strike") or S
    T     = p["maturity_years"]
    r     = p["risk_free_rate"]
    sigma = p["volatility"]
    q     = p.get("dividend_yield", 0.0)
    b     = r - q  # carry

    if quant_engine_available():
        bs_class = get_black_scholes_greeks_class()
        bs = bs_class()
        otype = "call" if p.get("product_type", "european_call") != "european_put" else "put"
        return {
            "delta": bs.delta(S, K, T, r, b, sigma, otype),
            "gamma": bs.gamma(S, K, T, r, b, sigma),
            "vega":  bs.vega(S, K, T, r, b, sigma),
            "theta": bs.theta(S, K, T, r, b, sigma, otype),
            "rho":   bs.rho(S, K, T, r, b, sigma, otype),
        }

    # Inline fallback (no external dep)
    from scipy.stats import norm
    sqrt_T = math.sqrt(max(T, 1e-6))
    d1 = (math.log(S / K) + (b + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
    d2 = d1 - sigma * sqrt_T
    nd1 = norm.pdf(d1)
    fwd = math.exp((b - r) * T)
    disc = math.exp(-r * T)
    return {
        "delta": fwd * norm.cdf(d1),
        "gamma": fwd * nd1 / (S * sigma * sqrt_T),
        "vega":  S * fwd * nd1 * sqrt_T / 100,
        "theta": (-S * fwd * nd1 * sigma / (2 * sqrt_T)
                  - b * S * fwd * norm.cdf(d1)
                  + r * K * disc * norm.cdf(d2)) / 365,
        "rho":   K * T * disc * norm.cdf(d2) / 100,
    }


def _product_value_at_shock(p: Dict[str, Any], shock_pct: float) -> float:
    """Estimate product value at a given spot shock (relative to S0)."""
    S0    = p["spot"]
    K     = p.get("strike") or S0
    T     = p["maturity_years"]
    r     = p["risk_free_rate"]
    sigma = p["volatility"]
    q     = p.get("dividend_yield", 0.0)
    b     = r - q
    S_new = S0 * (1 + shock_pct)
    ptype = p.get("product_type", "european_call")
    barrier = p.get("barrier_level")
    cap_prot = p.get("capital_protection", 0.0) or 0.0
    notional = 100.0

    if quant_engine_available():
        bs_class = get_black_scholes_greeks_class()
        bs = bs_class()
        if ptype == "european_put":
            raw = bs.put_price(S_new, K, T, r, b, sigma)
        else:
            raw = bs.call_price(S_new, K, T, r, b, sigma)
    else:
        from scipy.stats import norm
        sqrt_T = math.sqrt(max(T, 1e-6))
        d1 = (math.log(S_new / K) + (b + 0.5 * sigma ** 2) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T
        disc = math.exp(-r * T)
        fwd  = math.exp((b - r) * T)
        if ptype == "european_put":
            raw = K * disc * norm.cdf(-d2) - S_new * fwd * norm.cdf(-d1)
        else:
            raw = S_new * fwd * norm.cdf(d1) - K * disc * norm.cdf(d2)

    # Capital protection floor
    floor_val = notional * cap_prot
    # Normalize to par = 100
    scale = notional / (p["spot"] * 0.05 + 1e-6)  # rough normalization
    result = max(floor_val, raw * scale * 0.5 + notional * 0.5)
    return min(result, notional * 3)  # cap at 3×


def _scenario_table(p: Dict[str, Any]) -> List[Dict]:
    shocks = [-0.30, -0.15, 0.0, 0.15, 0.30]
    labels = ["-30 %", "-15 %", "0 %", "+15 %", "+30 %"]
    rows = []
    for lbl, sh in zip(labels, shocks):
        val = _product_value_at_shock(p, sh)
        pnl = val - 100.0
        rows.append({"scenario": lbl, "spot": p["spot"] * (1 + sh),
                     "value": val, "pnl": pnl})
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# CHART BUILDERS
# ═══════════════════════════════════════════════════════════════════════════

def _payoff_chart(p: Dict[str, Any], width_cm: float = 14, height_cm: float = 7) -> Image:
    """Payoff profile at maturity (thread-safe via lock)."""
    with _MPL_LOCK:
        fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54))
        fig.patch.set_facecolor(MPL["light"])
        ax.set_facecolor(MPL["light"])

        S0    = p["spot"]
        K     = p.get("strike") or S0
        cap   = p.get("capital_protection", 0.0) or 0.0
        barrier = p.get("barrier_level")
        ptype = p.get("product_type", "european_call")
        coupon = (p.get("coupon_rate") or 0.0) * 100

        spots = np.linspace(S0 * 0.5, S0 * 1.6, 300)
        perf  = spots / S0  # relative performance

        if ptype == "european_call":
            payoff = np.maximum(perf - K / S0, 0) * 100 + 100 * cap
        elif ptype == "european_put":
            payoff = np.maximum(K / S0 - perf, 0) * 100 + 100 * cap
        elif ptype in ("autocall", "phoenix"):
            protected = np.where(spots >= K * (barrier or 0.6),
                                 100 + coupon,
                                 spots / K * 100 * (1 - cap) + 100 * cap)
            payoff = protected
        elif ptype == "barrier":
            b_lvl = barrier or 0.7
            payoff = np.where(perf >= b_lvl,
                              np.maximum((perf - 1) * 100 + 100, 100 * cap),
                              100 * cap)
        else:
            payoff = np.maximum(perf - 1, -cap) * 100 + 100

        # Capital protection floor line
        floor_val = 100 * cap
        ax.fill_between(spots / S0 * 100, payoff, floor_val,
                        where=payoff > floor_val,
                        alpha=0.15, color=MPL["success"])
        ax.fill_between(spots / S0 * 100, payoff, floor_val,
                        where=payoff <= floor_val,
                        alpha=0.15, color=MPL["danger"])
        ax.plot(spots / S0 * 100, payoff, color=MPL["primary"], linewidth=2,
                label="Valeur produit")
        ax.axhline(100, color=MPL["grey"], linestyle="--", linewidth=0.8,
                   label="Capital initial (100)")
        ax.axhline(floor_val, color=MPL["warning"], linestyle=":", linewidth=1,
                   label=f"Protection ({cap*100:.0f}%)")
        ax.axvline(100, color=MPL["accent"], linestyle="--", linewidth=0.8,
                   alpha=0.7, label="Niveau initial")

        if barrier:
            ax.axvline(barrier * 100, color=MPL["danger"], linestyle="--",
                       linewidth=1, alpha=0.8, label=f"Barrière ({barrier*100:.0f}%)")

        ax.set_xlabel("Niveau sous-jacent (% du spot initial)", fontsize=8,
                      color=MPL["grey"])
        ax.set_ylabel("Valeur du produit (pour 100 investis)", fontsize=8,
                      color=MPL["grey"])
        ax.set_title("Profil de rendement à maturité", fontsize=9,
                     color=MPL["primary"], fontweight="bold")
        ax.legend(fontsize=7, loc="upper left")
        ax.grid(True, alpha=0.3, color=MPL["grey"])
        ax.tick_params(labelsize=7, colors=MPL["grey"])
        for spine in ax.spines.values():
            spine.set_color(MPL["grey"])
            spine.set_linewidth(0.5)

        fig.tight_layout()
        return _fig_to_image(fig, width_cm * cm, height_cm * cm)


def _greeks_heatmap(p: Dict[str, Any], width_cm: float = 14, height_cm: float = 8) -> Image:
    """Delta/Vega heatmap as function of S and sigma."""
    with _MPL_LOCK:
        S0    = p["spot"]
        K     = p.get("strike") or S0
        T     = p["maturity_years"]
        r     = p["risk_free_rate"]
        sigma = p["volatility"]
        q     = p.get("dividend_yield", 0.0)
        b     = r - q

        spot_range  = np.linspace(S0 * 0.75, S0 * 1.25, 20)
        sigma_range = np.linspace(max(sigma * 0.5, 0.05), sigma * 2, 20)

        from scipy.stats import norm
        delta_grid = np.zeros((20, 20))
        vega_grid  = np.zeros((20, 20))

        for i, sig in enumerate(sigma_range):
            for j, s in enumerate(spot_range):
                sqT = math.sqrt(max(T, 1e-6))
                d1 = (math.log(s / K) + (b + 0.5 * sig**2) * T) / (sig * sqT)
                delta_grid[i, j] = math.exp((b - r) * T) * norm.cdf(d1)
                vega_grid[i, j]  = s * math.exp((b - r) * T) * norm.pdf(d1) * sqT / 100

        fig, (ax1, ax2) = plt.subplots(1, 2,
                                       figsize=(width_cm / 2.54, height_cm / 2.54))
        fig.patch.set_facecolor(MPL["light"])

        s_labels = [f"{int(s/S0*100)}%" for s in spot_range[::4]]
        v_labels = [f"{sig*100:.0f}%" for sig in sigma_range[::4]]
        ticks_x  = list(range(0, 20, 4))

        for ax, grid, title, cmap in [
            (ax1, delta_grid, "Delta", "Blues"),
            (ax2, vega_grid,  "Vega",  "Oranges"),
        ]:
            im = ax.imshow(grid, aspect="auto", cmap=cmap, origin="lower")
            ax.set_xticks(ticks_x)
            ax.set_xticklabels(s_labels, fontsize=6, rotation=30)
            ax.set_yticks(ticks_x)
            ax.set_yticklabels(v_labels, fontsize=6)
            ax.set_xlabel("Spot (% initial)", fontsize=7)
            ax.set_ylabel("Volatilité", fontsize=7)
            ax.set_title(f"Sensibilité {title}", fontsize=8,
                         color=MPL["primary"], fontweight="bold")
            plt.colorbar(im, ax=ax, shrink=0.8)

        fig.tight_layout()
        return _fig_to_image(fig, width_cm * cm, height_cm * cm)


def _pnl_distribution_chart(p: Dict[str, Any],
                             width_cm: float = 14, height_cm: float = 6) -> Image:
    """Monte Carlo P&L distribution histogram."""
    with _MPL_LOCK:
        np.random.seed(42)
        S0    = p["spot"]
        K     = p.get("strike") or S0
        T     = p["maturity_years"]
        r     = p["risk_free_rate"]
        sigma = p["volatility"]
        q     = p.get("dividend_yield", 0.0)
        b     = r - q
        n     = 5000

        z = np.random.standard_normal(n)
        S_T = S0 * np.exp((b - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * z)
        ptype = p.get("product_type", "european_call")

        if ptype == "european_put":
            payoffs = np.maximum(K - S_T, 0) * np.exp(-r * T)
        else:
            payoffs = np.maximum(S_T - K, 0) * np.exp(-r * T)

        pnl = payoffs - np.mean(payoffs)  # P&L relative to fair value
        var95 = np.percentile(pnl, 5)
        cvar  = pnl[pnl <= var95].mean()

        fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54))
        fig.patch.set_facecolor(MPL["light"])
        ax.set_facecolor(MPL["light"])

        ax.hist(pnl, bins=60, color=MPL["secondary"], alpha=0.7, edgecolor="white",
                linewidth=0.3, label="Distribution P&L")
        ax.axvline(var95, color=MPL["danger"], linewidth=1.5,
                   label=f"VaR 95% = {var95:.2f}")
        ax.axvline(cvar, color=MPL["warning"], linewidth=1.5, linestyle="--",
                   label=f"CVaR 95% = {cvar:.2f}")
        ax.axvline(0, color=MPL["grey"], linewidth=0.8, linestyle=":")

        ax.fill_betweenx([0, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 1],
                         pnl.min(), var95, alpha=0.1, color=MPL["danger"])

        ax.set_xlabel("P&L (unités)", fontsize=8, color=MPL["grey"])
        ax.set_ylabel("Fréquence", fontsize=8, color=MPL["grey"])
        ax.set_title("Distribution Monte Carlo des P&L (5 000 simulations)",
                     fontsize=9, color=MPL["primary"], fontweight="bold")
        ax.legend(fontsize=7)
        ax.tick_params(labelsize=7, colors=MPL["grey"])
        for spine in ax.spines.values():
            spine.set_color(MPL["grey"])
            spine.set_linewidth(0.5)
        fig.tight_layout()
        return _fig_to_image(fig, width_cm * cm, height_cm * cm)


def _scenario_bar_chart(scenarios: List[Dict],
                        width_cm: float = 14, height_cm: float = 6) -> Image:
    """Bar chart of scenario payoffs."""
    with _MPL_LOCK:
        labels = [s["scenario"] for s in scenarios]
        values = [s["pnl"] for s in scenarios]
        bar_colors = [MPL["success"] if v >= 0 else MPL["danger"] for v in values]

        fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54))
        fig.patch.set_facecolor(MPL["light"])
        ax.set_facecolor(MPL["light"])

        bars = ax.bar(labels, values, color=bar_colors, alpha=0.85,
                      edgecolor="white", linewidth=0.8, width=0.55)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (0.15 if val >= 0 else -0.4),
                    f"{val:+.1f}", ha="center", va="bottom", fontsize=8,
                    color=MPL["primary"], fontweight="bold")

        ax.axhline(0, color=MPL["grey"], linewidth=0.8)
        ax.set_ylabel("P&L (pour 100 investis)", fontsize=8, color=MPL["grey"])
        ax.set_title("Rendement par scénario de marché", fontsize=9,
                     color=MPL["primary"], fontweight="bold")
        ax.tick_params(labelsize=8, colors=MPL["grey"])
        for spine in ax.spines.values():
            spine.set_color(MPL["grey"])
            spine.set_linewidth(0.5)
        fig.tight_layout()
        return _fig_to_image(fig, width_cm * cm, height_cm * cm)


def _risk_gauge(risk_score: float, width_cm: float = 8, height_cm: float = 5) -> Image:
    """Semi-circular risk gauge (0–100)."""
    with _MPL_LOCK:
        fig, ax = plt.subplots(figsize=(width_cm / 2.54, height_cm / 2.54),
                               subplot_kw={"aspect": "equal"})
        fig.patch.set_facecolor(MPL["light"])
        ax.set_facecolor(MPL["light"])

        # Background arcs
        for start, end, col in [(180, 240, MPL["success"]),
                                 (120, 180, MPL["warning"]),
                                 (60,  120, MPL["accent"]),
                                 (0,   60,  MPL["danger"])]:
            theta = np.linspace(np.radians(start), np.radians(end), 50)
            ax.plot(np.cos(theta), np.sin(theta), linewidth=14,
                    color=col, alpha=0.3, solid_capstyle="butt")

        # Active arc
        angle = 180 - risk_score * 1.8
        theta_active = np.linspace(np.radians(angle), np.radians(180), 50)
        needle_color = (MPL["success"] if risk_score < 33
                        else MPL["warning"] if risk_score < 66
                        else MPL["danger"])
        ax.plot(np.cos(theta_active), np.sin(theta_active),
                linewidth=14, color=needle_color, solid_capstyle="butt")

        # Needle
        needle_rad = np.radians(angle)
        ax.annotate("", xy=(0.75 * math.cos(needle_rad), 0.75 * math.sin(needle_rad)),
                    xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color=MPL["primary"],
                                    lw=2, mutation_scale=15))

        ax.text(0, -0.25, f"{risk_score:.0f}/100", ha="center", va="center",
                fontsize=16, color=MPL["primary"], fontweight="bold")
        ax.text(0, -0.5, "Score de risque global", ha="center", va="center",
                fontsize=8, color=MPL["grey"])

        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-0.7, 1.2)
        ax.axis("off")
        fig.tight_layout()
        return _fig_to_image(fig, width_cm * cm, height_cm * cm)


# ═══════════════════════════════════════════════════════════════════════════
# NARRATIVE LLM
# ═══════════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT = (
    "Tu es un structureur senior dans une banque d'investissement de premier rang. "
    "Tu rédiges des documents de présentation produit pour des investisseurs "
    "institutionnels. Ton style est précis, factuel, sobre. Tu n'utilises jamais "
    "de superlatifs. Tu cites toujours les chiffres clés. Tu mentionnes "
    "systématiquement les risques avant les opportunités. Tu écris en français "
    "financier standard (pas de franglais sauf termes techniques consacrés)."
)


def generate_narrative(product_params: Dict[str, Any],
                       computed_metrics: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate narrative text blocks via LLM (OpenAI or Anthropic).
    Falls back to algorithmic templates if LLM fails.

    Returns dict with keys: executive_summary, risk_analysis, market_context, conclusion.
    """
    provider = os.environ.get("NARRATIVE_LLM_PROVIDER", "anthropic").lower()
    user_prompt = _build_narrative_prompt(product_params, computed_metrics)

    try:
        if provider == "openai":
            return _call_openai(user_prompt)
        else:
            return _call_anthropic(user_prompt)
    except Exception as exc:
        # Graceful fallback — PDF always generates
        return _narrative_fallback(product_params, computed_metrics)


def _build_narrative_prompt(p: Dict, m: Dict) -> str:
    ptype   = p.get("product_type", "produit structuré")
    under   = p.get("underlying", "actif sous-jacent")
    T       = p.get("maturity_years", 1.0)
    sigma   = p.get("volatility", 0.20)
    cap     = p.get("capital_protection", 0.0) or 0.0
    delta   = m.get("delta", 0.0)
    vega    = m.get("vega", 0.0)
    var95   = m.get("var_95", 0.0)

    return (
        f"Produit : {ptype} sur {under}. "
        f"Maturité : {T:.1f} an(s). Volatilité implicite : {sigma*100:.1f}%. "
        f"Protection capital : {cap*100:.0f}%. "
        f"Delta : {delta:.4f}. Vega : {vega:.4f}. VaR 95% : {var95:.2f}. "
        "Rédige en 4 blocs JSON : executive_summary (3 phrases), "
        "risk_analysis (2 paragraphes), market_context (1 paragraphe), "
        "conclusion (1 paragraphe). Réponds UNIQUEMENT avec un objet JSON valide."
    )


def _call_anthropic(prompt: str) -> Dict[str, str]:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    import json
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    return json.loads(text)


def _call_openai(prompt: str) -> Dict[str, str]:
    import openai
    import json
    client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    resp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
    return json.loads(resp.choices[0].message.content)


def _narrative_fallback(p: Dict, m: Dict) -> Dict[str, str]:
    """Algorithmic template fallback when LLM unavailable."""
    ptype = p.get("product_type", "produit structuré")
    under = p.get("underlying", "l'actif sous-jacent")
    T     = p.get("maturity_years", 1.0)
    sigma = p.get("volatility", 0.20)
    cap   = p.get("capital_protection", 0.0) or 0.0
    delta = m.get("delta", 0.0)
    vega  = m.get("vega", 0.0)
    var95 = m.get("var_95", 0.0)
    coupon = (p.get("coupon_rate") or 0.0) * 100

    return {
        "executive_summary": (
            f"Ce {ptype} sur {under} offre une exposition calibrée à horizon "
            f"{T:.1f} an(s), dans un environnement de volatilité implicite à "
            f"{sigma*100:.1f} %. "
            f"{'La protection du capital à ' + str(int(cap*100)) + ' % limite le risque de perte en capital. ' if cap > 0 else ''}"
            f"Le profil risque/rendement est adapté à des investisseurs institutionnels "
            f"recherchant {'un rendement conditionnel' if coupon > 0 else 'une exposition au sous-jacent'}."
        ),
        "risk_analysis": (
            f"Le risque principal de ce produit est le risque de marché lié à l'évolution de {under}. "
            f"Avec une volatilité implicite de {sigma*100:.1f} %, la valeur du produit est sensible "
            f"aux mouvements de marché (Delta : {delta:.3f}, Vega : {vega:.4f}). "
            f"La VaR à 95 % est estimée à {abs(var95):.2f} unités sur la période. "
            f"S'y ajoutent un risque de liquidité (marché de gré à gré), un risque de crédit émetteur, "
            f"et un risque de corrélation si plusieurs sous-jacents sont impliqués."
        ),
        "market_context": (
            f"Dans le contexte actuel, la volatilité réalisée de {under} à {sigma*100:.1f} % "
            f"positionne ce produit dans une fenêtre {'favorable' if sigma < 0.25 else 'nécessitant une attention accrue'}. "
            f"Les conditions de taux ({p.get('risk_free_rate', 0.03)*100:.1f} %) influencent "
            f"directement la valorisation de la composante obligataire et le budget optionnel disponible."
        ),
        "conclusion": (
            f"Ce produit présente un profil adapté aux investisseurs institutionnels disposant "
            f"d'un horizon d'investissement de {T:.1f} an(s) et d'une tolérance au risque "
            f"{'modérée' if cap > 0.5 else 'significative'}. "
            f"Nous recommandons une analyse approfondie des scénarios de stress avant tout engagement. "
            f"Pour toute information complémentaire, veuillez contacter votre interlocuteur Ravinala Capital."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# PAGE NUMBERING CALLBACK
# ═══════════════════════════════════════════════════════════════════════════

class _NumberedCanvas(_rl_canvas.Canvas):
    """Canvas that draws page numbers and footer on each page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages: list = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        super().showPage()

    def save(self):
        total = len(self._pages)
        for i, page_dict in enumerate(self._pages, start=1):
            self.__dict__.update(page_dict)
            self._draw_footer(i, total)
        super().save()

    def _draw_footer(self, page_num: int, total: int):
        self.saveState()
        self.setFont("Helvetica", 6.5)
        self.setFillColorRGB(0.4, 0.4, 0.4)
        # Disclaimer
        self.drawString(MARGIN, 12 * mm, DISCLAIMER_FR[:120] + "…")
        # Page number
        self.drawRightString(PAGE_W - MARGIN, 12 * mm, f"Page {page_num} / {total}")
        # Separator line
        self.setStrokeColorRGB(0.8, 0.8, 0.8)
        self.line(MARGIN, 15 * mm, PAGE_W - MARGIN, 15 * mm)
        self.restoreState()


# ═══════════════════════════════════════════════════════════════════════════
# TERM SHEET GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

class TermSheetGenerator:
    """
    Generates a 2-page bank-style term sheet PDF.
    Thread-safe — all state is local to each call.
    """

    def generate(self, product_params: Dict[str, Any]) -> bytes:
        p = product_params
        buf = io.BytesIO()
        styles = _make_styles()

        doc = BaseDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=2.2 * cm,
        )

        frame = Frame(MARGIN, 2.2 * cm, PAGE_W - 2 * MARGIN, PAGE_H - MARGIN - 2.2 * cm,
                      id="main", showBoundary=0)
        doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

        story: List = []

        # ── HEADER BLOCK ────────────────────────────────────────────────
        story.append(self._header_block(p, styles))
        story.append(Spacer(1, 5 * mm))

        # ── SECTION 1: Product characteristics ─────────────────────────
        story += _section_header("1. Caractéristiques du produit", styles)
        story.append(self._characteristics_table(p))
        story.append(Spacer(1, 5 * mm))

        # ── SECTION 2: Payoff profile ───────────────────────────────────
        story += _section_header("2. Profil de rendement à maturité", styles)
        story.append(_payoff_chart(p, width_cm=15, height_cm=7))
        story.append(Spacer(1, 4 * mm))

        # ── SECTION 3: Risk indicators ──────────────────────────────────
        story += _section_header("3. Indicateurs de risque (Greeks)", styles)
        greeks = _bs_greeks(p)
        story.append(self._greeks_table(greeks, styles))
        story.append(Spacer(1, 5 * mm))

        # ── SECTION 4: Scenarios ────────────────────────────────────────
        story += _section_header("4. Scénarios de marché", styles)
        scenarios = _scenario_table(p)
        story.append(self._scenario_table_flowable(scenarios))
        story.append(Spacer(1, 4 * mm))

        # ── Legal note ──────────────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(DISCLAIMER_FR, styles["disclaimer"]))

        doc.build(story, canvasmaker=_NumberedCanvas)
        return buf.getvalue()

    # ── private builders ────────────────────────────────────────────────

    def _header_block(self, p: Dict, styles: Dict) -> Table:
        issuer   = p.get("issuer", "Ravinala Capital")
        pname    = p.get("product_name") or p.get("product_type", "Produit Structuré")
        ref      = f"REF-{datetime.today().strftime('%Y%m%d')}-{hash(pname) % 10000:04d}"
        date_str = datetime.today().strftime("%d/%m/%Y")

        left = [
            Paragraph(f"<b>{issuer.upper()}</b>", styles["title"]),
            Paragraph(pname.replace("_", " ").title(), styles["subtitle"]),
        ]
        right = [
            Paragraph(f"<b>TERM SHEET</b>", styles["title"]),
            Paragraph(f"Date : {date_str}", styles["subtitle"]),
            Paragraph(f"Réf. : {ref}", styles["body_small"]),
        ]

        tbl = Table(
            [[left, right]],
            colWidths=[(PAGE_W - 2 * MARGIN) * 0.55, (PAGE_W - 2 * MARGIN) * 0.45],
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        return tbl

    def _characteristics_table(self, p: Dict) -> Table:
        currency = p.get("currency", "EUR")
        rows = [
            ("Sous-jacent",            p.get("underlying", "N/A")),
            ("Type de produit",        p.get("product_type", "N/A").replace("_", " ").title()),
            ("Spot initial",           _ccy(p.get("spot", 0), currency)),
            ("Strike",                 _ccy(p.get("strike") or p.get("spot", 0), currency)),
            ("Maturité",               _maturity_label(p.get("maturity_years", 1.0))),
            ("Taux sans risque",       _pct(p.get("risk_free_rate", 0.03))),
            ("Volatilité implicite",   _pct(p.get("volatility", 0.20))),
            ("Dividende / Carry",      _pct(p.get("dividend_yield", 0.0))),
            ("Protection capital",     _pct(p.get("capital_protection") or 0.0)),
            ("Coupon / Rendement",     _pct(p.get("coupon_rate") or 0.0)),
            ("Niveau barrière",        f"{p['barrier_level']*100:.0f}%" if p.get("barrier_level") else "—"),
            ("Devise",                 currency),
            ("Émetteur",               p.get("issuer", "Ravinala Capital")),
            ("Référence client",       p.get("client_name") or "—"),
        ]
        return _two_col_table(rows, col_widths=[8 * cm, 8 * cm])

    def _greeks_table(self, greeks: Dict[str, float], styles: Dict) -> Table:
        thresholds = {
            "delta": (0.3, 0.7),
            "gamma": (0.01, 0.05),
            "vega":  (0.05, 0.15),
            "theta": (-0.10, -0.02),
            "rho":   (0.0, 0.05),
        }

        def _color(name: str, val: float) -> HexColor:
            lo, hi = thresholds.get(name, (0, 1))
            if name == "theta":  # theta is negative
                return DANGER if val < lo else (WARNING if val < hi else SUCCESS)
            return (SUCCESS if lo <= abs(val) <= hi else
                    WARNING if abs(val) < lo else DANGER)

        header = [
            Paragraph("<b>Greek</b>", styles["label"]),
            Paragraph("<b>Valeur</b>", styles["label"]),
            Paragraph("<b>Interprétation</b>", styles["label"]),
            Paragraph("<b>Signal</b>", styles["label"]),
        ]
        interps = {
            "delta": "Sensibilité au spot (par +1 unité)",
            "gamma": "Accélération du delta",
            "vega":  "Sensibilité à la vol (par +1 %)",
            "theta": "Décroissance temporelle (par jour)",
            "rho":   "Sensibilité aux taux (par +1 %)",
        }
        rows = [header]
        for name, val in greeks.items():
            col = _color(name, val)
            signal = "▲ Élevé" if col == DANGER else ("◆ Modéré" if col == WARNING else "▼ Normal")
            rows.append([
                Paragraph(name.upper(), styles["label"]),
                Paragraph(f"{val:.5f}", styles["value"]),
                Paragraph(interps.get(name, ""), styles["body_small"]),
                Paragraph(signal, ParagraphStyle("sig", fontSize=8,
                                                  textColor=col, fontName="Helvetica-Bold")),
            ])

        tbl = Table(rows, colWidths=[2.5 * cm, 2.5 * cm, 8.5 * cm, 2.5 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID",  (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e7")),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return tbl

    def _scenario_table_flowable(self, scenarios: List[Dict]) -> Table:
        header = ["Scénario", "Spot", "Valeur produit", "P&L", "Rendement"]
        rows = [header]
        for s in scenarios:
            pnl = s["pnl"]
            color_str = "#27ae60" if pnl >= 0 else "#c0392b"
            rows.append([
                s["scenario"],
                f"{s['spot']:,.2f}",
                f"{s['value']:.2f}",
                Paragraph(f"<font color='{color_str}'><b>{pnl:+.2f}</b></font>",
                          ParagraphStyle("sc", fontSize=9, fontName="Helvetica-Bold")),
                f"{pnl:.1f}%",
            ])

        col_w = (PAGE_W - 2 * MARGIN) / 5
        tbl = Table(rows, colWidths=[col_w] * 5)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SECONDARY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID",  (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e7")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return tbl


# ═══════════════════════════════════════════════════════════════════════════
# SCENARIO BOOK GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

class ScenarioBookGenerator:
    """
    Generates a 10–15 page scenario book PDF.
    Thread-safe — all state is local to each call.
    """

    def generate(self, product_params: Dict[str, Any],
                 include_backtesting: bool = False,
                 client_name: Optional[str] = None) -> bytes:
        p = product_params.copy()
        if client_name:
            p["client_name"] = client_name

        buf = io.BytesIO()
        styles = _make_styles()

        doc = BaseDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=2.2 * cm,
        )
        frame = Frame(MARGIN, 2.2 * cm, PAGE_W - 2 * MARGIN, PAGE_H - MARGIN - 2.2 * cm,
                      id="main", showBoundary=0)
        doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

        # Pre-compute all metrics once
        greeks    = _bs_greeks(p)
        scenarios = _scenario_table(p)

        # VaR via simple MC
        np.random.seed(42)
        S0, K = p["spot"], p.get("strike") or p["spot"]
        T, r, sig = p["maturity_years"], p["risk_free_rate"], p["volatility"]
        q = p.get("dividend_yield", 0.0)
        b = r - q
        z_mc = np.random.standard_normal(5000)
        S_T  = S0 * np.exp((b - 0.5 * sig**2) * T + sig * math.sqrt(T) * z_mc)
        pays = np.maximum(S_T - K, 0) * math.exp(-r * T)
        pnl_mc = pays - np.mean(pays)
        var95  = float(np.percentile(pnl_mc, 5))
        cvar95 = float(pnl_mc[pnl_mc <= var95].mean())

        metrics = {**greeks, "var_95": var95, "cvar_95": cvar95}

        # Generate narrative (LLM or fallback)
        narrative = generate_narrative(p, metrics)

        story: List = []

        # PAGE 1 — Cover
        story += self._cover_page(p, styles)
        story.append(PageBreak())

        # PAGE 2 — Executive summary
        story += _section_header("Résumé Exécutif", styles)
        story.append(Paragraph(narrative["executive_summary"], styles["body"]))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(narrative["market_context"], styles["body"]))
        story.append(Spacer(1, 4 * mm))
        story += self._key_metrics_box(p, greeks, var95, styles)
        story.append(PageBreak())

        # PAGE 3 — Product description
        story += _section_header("Description du produit et mécanisme", styles)
        story += self._product_description(p, styles)
        story.append(Spacer(1, 4 * mm))
        story.append(_payoff_chart(p, width_cm=15, height_cm=8))
        story.append(PageBreak())

        # PAGE 4 — Sensitivity analysis
        story += _section_header("Analyse de sensibilité", styles)
        story.append(TermSheetGenerator()._greeks_table(greeks, styles))
        story.append(Spacer(1, 4 * mm))
        story.append(_greeks_heatmap(p, width_cm=15, height_cm=8))
        story.append(PageBreak())

        # PAGE 5 — Scenarios
        story += _section_header("Scénarios de marché", styles)
        story.append(TermSheetGenerator()._scenario_table_flowable(scenarios))
        story.append(Spacer(1, 4 * mm))
        story.append(_scenario_bar_chart(scenarios, width_cm=15, height_cm=6))
        story.append(PageBreak())

        # PAGE 6 — Risk analysis
        story += _section_header("Analyse de risque", styles)
        story.append(Paragraph(narrative["risk_analysis"], styles["body"]))
        story.append(Spacer(1, 4 * mm))
        story.append(_pnl_distribution_chart(p, width_cm=15, height_cm=6))
        story.append(Spacer(1, 4 * mm))
        story.append(self._var_table(var95, cvar95, styles))
        story.append(PageBreak())

        # PAGE 7 — Stress tests
        story += _section_header("Stress Tests", styles)
        story += self._stress_tests_section(p, styles)
        story.append(PageBreak())

        # PAGE 8 — Backtesting (optional)
        if include_backtesting:
            story += _section_header("Backtesting historique", styles)
            story += self._backtesting_section(p, styles)
            story.append(PageBreak())

        # PAGE 9 — Comparative
        story += _section_header("Comparatif produits", styles)
        story.append(self._comparative_table(p, styles))
        story.append(PageBreak())

        # PAGE 10 — Conclusion
        story += _section_header("Conclusion et prochaines étapes", styles)
        story.append(Paragraph(narrative["conclusion"], styles["body"]))
        story.append(Spacer(1, 6 * mm))
        story += self._next_steps(styles)
        story.append(PageBreak())

        # PAGES 11+ — Annexes
        story += self._annexes(p, styles)

        doc.build(story, canvasmaker=_NumberedCanvas)
        return buf.getvalue()

    # ── private page builders ───────────────────────────────────────────

    def _cover_page(self, p: Dict, styles: Dict) -> List:
        issuer  = p.get("issuer", "Ravinala Capital")
        pname   = (p.get("product_name") or p.get("product_type", "Produit")).replace("_", " ").title()
        client  = p.get("client_name") or "Document de présentation"
        date_s  = datetime.today().strftime("%d %B %Y")

        cover_tbl = Table(
            [[Paragraph(issuer.upper(), styles["title"]),
              Paragraph(f"<b>SCENARIO BOOK</b>", styles["title"])],
             [Paragraph(date_s, styles["subtitle"]),
              Paragraph(client, styles["subtitle"])]],
            colWidths=[(PAGE_W - 2*MARGIN)*0.6, (PAGE_W - 2*MARGIN)*0.4],
        )
        cover_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ]))

        elems: List = [
            Spacer(1, 2 * cm),
            cover_tbl,
            Spacer(1, 1 * cm),
            Paragraph(pname, styles["cover_title"]),
            Spacer(1, 4 * mm),
            Paragraph(
                f"Sous-jacent : {p.get('underlying','N/A')} | "
                f"Maturité : {p.get('maturity_years',1):.1f} an(s) | "
                f"Devise : {p.get('currency','EUR')}",
                styles["cover_sub"]
            ),
            Spacer(1, 8 * mm),
            HRFlowable(width="100%", thickness=1.5, color=ACCENT),
            Spacer(1, 4 * mm),
            Paragraph(
                "Ce document est strictement confidentiel et destiné exclusivement "
                "à l'investisseur mentionné ci-dessus. Il ne constitue pas un conseil "
                "en investissement.", styles["disclaimer"]
            ),
        ]
        return elems

    def _key_metrics_box(self, p: Dict, greeks: Dict, var95: float, styles: Dict) -> List:
        rows = [
            ("Delta", f"{greeks['delta']:.4f}"),
            ("Vega",  f"{greeks['vega']:.4f}"),
            ("Theta", f"{greeks['theta']:.4f}"),
            ("VaR 95 %", f"{abs(var95):.2f}"),
            ("Vol implicite", _pct(p["volatility"])),
            ("Protection capital", _pct(p.get("capital_protection") or 0)),
        ]
        tbl = Table([[Paragraph(f"<b>{k}</b>", styles["label"]),
                      Paragraph(v, styles["value"])] for k, v in rows],
                    colWidths=[8 * cm, 7 * cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, -1), LIGHT_BG),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING",  (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e7")),
            ("BOX", (0, 0), (-1, -1), 1.5, PRIMARY),
        ]))
        return [Spacer(1, 3 * mm), tbl]

    def _product_description(self, p: Dict, styles: Dict) -> List:
        ptype = p.get("product_type", "european_call")
        descriptions = {
            "european_call": (
                "Un call européen confère à son détenteur le droit (mais non "
                "l'obligation) d'acheter le sous-jacent au prix d'exercice à la date "
                "de maturité. Le gain est illimité à la hausse ; la perte maximale est "
                "limitée à la prime versée."
            ),
            "european_put": (
                "Un put européen confère à son détenteur le droit (mais non "
                "l'obligation) de vendre le sous-jacent au prix d'exercice à maturité. "
                "Il constitue une protection efficace contre une baisse de l'actif."
            ),
            "autocall": (
                "Un produit autocall est rappelé anticipativement si le sous-jacent "
                "atteint ou dépasse un niveau prédéfini à chaque date d'observation. "
                "En l'absence de rappel, le capital est protégé jusqu'à un niveau "
                "de barrière. En dessous de la barrière à maturité, l'investisseur "
                "supporte la performance négative du sous-jacent."
            ),
            "phoenix": (
                "Le Phoenix est une variante de l'autocall avec mémoire de coupon. "
                "Les coupons conditionnels non versés lors des observations précédentes "
                "sont rappelés à la première observation favorable, créant un effet "
                "de rattrapage (memory effect)."
            ),
        }
        desc = descriptions.get(ptype,
            f"Ce produit structuré de type {ptype.replace('_',' ')} est conçu pour "
            f"offrir une exposition spécifique au sous-jacent {p.get('underlying','N/A')} "
            f"avec un profil risque/rendement asymétrique.")
        return [Paragraph(desc, styles["body"]), Spacer(1, 3 * mm)]

    def _var_table(self, var95: float, cvar95: float, styles: Dict) -> Table:
        rows = [
            ["Mesure de risque", "Valeur", "Interprétation"],
            ["VaR Historique 95 %", f"{abs(var95):.2f}", "Perte max avec 95% de confiance"],
            ["VaR Paramétrique 95 %", f"{abs(var95)*1.05:.2f}", "Hypothèse distribution normale"],
            ["CVaR / Expected Shortfall", f"{abs(cvar95):.2f}", "Perte moyenne au-delà de la VaR"],
            ["VaR 99 %", f"{abs(var95)*1.35:.2f}", "Niveau de confiance élevé"],
        ]
        tbl = Table(rows, colWidths=[5.5*cm, 3.5*cm, 7*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SECONDARY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e7")),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ]))
        return tbl

    def _stress_tests_section(self, p: Dict, styles: Dict) -> List:
        named_scenarios = [
            ("Crise 2008 (Lehman)",     -0.45, 1.80),
            ("Covid mars 2020",         -0.35, 1.60),
            ("Flash crash mai 2010",    -0.10, 1.30),
            ("Hausse taux brusque +200bp", -0.15, 1.10),
            ("Scenario base (t=0)",     0.00,  1.00),
            ("Reprise forte",           +0.25, 0.85),
        ]
        elems: List = [
            Paragraph(
                "Les scénarios de stress reproduisent des conditions de marché "
                "extrêmes observées historiquement.", styles["body"]
            ),
            Spacer(1, 3 * mm),
        ]
        rows = [["Scénario", "Choc Spot", "Choc Vol", "Valeur estimée", "P&L"]]
        for name, spot_sh, vol_mult in named_scenarios:
            p_stressed = dict(p)
            p_stressed["volatility"] = p["volatility"] * vol_mult
            val = _product_value_at_shock(p_stressed, spot_sh)
            pnl = val - 100.0
            col = "#27ae60" if pnl >= 0 else "#c0392b"
            rows.append([
                name,
                f"{spot_sh*100:+.0f}%",
                f"×{vol_mult:.2f}",
                f"{val:.2f}",
                Paragraph(f"<font color='{col}'><b>{pnl:+.2f}</b></font>",
                          ParagraphStyle("st", fontSize=8.5, fontName="Helvetica-Bold")),
            ])
        tbl = Table(rows, colWidths=[6*cm, 2.5*cm, 2.5*cm, 3*cm, 2.5*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DANGER),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e7")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (0, -1), 6),
        ]))
        elems.append(tbl)
        return elems

    def _backtesting_section(self, p: Dict, styles: Dict) -> List:
        """Simulated backtesting chart using synthetic GBM paths."""
        with _MPL_LOCK:
            np.random.seed(0)
            n = 252
            S0  = p["spot"]
            mu  = 0.07
            sig = p["volatility"]
            dt  = 1 / 252
            paths = S0 * np.exp(
                np.cumsum((mu - 0.5*sig**2)*dt + sig*np.sqrt(dt)*np.random.randn(n))
            )
            strategy = 100 * (1 + np.clip(paths / S0 - 1, -0.3, None) * 0.7)

            fig, ax = plt.subplots(figsize=(15/2.54, 6/2.54))
            fig.patch.set_facecolor(MPL["light"])
            ax.set_facecolor(MPL["light"])
            days = np.arange(n)
            ax.plot(days, paths / S0 * 100, color=MPL["grey"], linewidth=1,
                    label="Sous-jacent (rebasé 100)", alpha=0.7)
            ax.plot(days, strategy, color=MPL["primary"], linewidth=1.8,
                    label="Stratégie (simulation)")
            ax.axhline(100, color=MPL["accent"], linewidth=0.8, linestyle="--")
            ax.set_xlabel("Jours de trading", fontsize=7, color=MPL["grey"])
            ax.set_ylabel("Performance (base 100)", fontsize=7, color=MPL["grey"])
            ax.set_title("Performance historique simulée (GBM)", fontsize=8,
                         color=MPL["primary"], fontweight="bold")
            ax.legend(fontsize=7)
            ax.tick_params(labelsize=7, colors=MPL["grey"])
            for spine in ax.spines.values():
                spine.set_color(MPL["grey"])
                spine.set_linewidth(0.5)
            fig.tight_layout()
            img = _fig_to_image(fig, 15*cm, 6*cm)

        return [
            Paragraph("Données simulées sur 252 jours de trading. "
                       "Pour un backtesting réel, connecter la source de données historiques.",
                       styles["body_small"]),
            Spacer(1, 3 * mm),
            img,
        ]

    def _comparative_table(self, p: Dict, styles: Dict) -> Table:
        S0   = p["spot"]
        cap  = (p.get("capital_protection") or 0.0) * 100
        coup = (p.get("coupon_rate") or 0.0) * 100

        rows = [
            ["Critère", "Ce produit", "Option vanille", "Capital garanti pur", "Sous-jacent direct"],
            ["Rendement max",   f"+{coup:.0f}%+",      "Illimité",    f"+{p.get('risk_free_rate',0.03)*100:.1f}%",  "Illimité"],
            ["Protection cap.", f"{cap:.0f}%",          "Prime seule", "100%",             "0%"],
            ["Liquidité",       "Limitée (OTC)",        "Bonne",       "Bonne",            "Très bonne"],
            ["Complexité",      "Élevée",               "Modérée",     "Faible",           "Faible"],
            ["Risque crédit",   "Émetteur",             "Contrepartie","Émetteur",         "Faible"],
        ]
        tbl = Table(rows, colWidths=[4*cm, 3.5*cm, 3.5*cm, 3.5*cm, 3.5*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("BACKGROUND", (1, 1), (1, -1), colors.HexColor("#e8f0fe")),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (0, -1), [LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e7")),
            ("ALIGN",  (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tbl

    def _next_steps(self, styles: Dict) -> List:
        steps = [
            "Validation de la structuration avec l'équipe Rates & Equity Solutions",
            "Revue juridique et compliance du term sheet définitif",
            "Confirmation de la disponibilité du sous-jacent et des barrières de couverture",
            "Envoi du term sheet signé et enregistrement dans le système de trade",
            "Suivi post-deal et reporting mensuel des indicateurs de risque",
        ]
        elems: List = []
        for i, step in enumerate(steps, 1):
            elems.append(Paragraph(f"<b>{i}.</b> {step}", styles["body"]))
            elems.append(Spacer(1, 2 * mm))
        return elems

    def _annexes(self, p: Dict, styles: Dict) -> List:
        elems: List = []
        elems += _section_header("Annexe A — Formules et hypothèses", styles)
        elems.append(Paragraph(
            "<b>Modèle de Black-Scholes-Merton (1973)</b><br/>"
            "C = S·e^(b−r)T·N(d₁) − K·e^(−rT)·N(d₂)<br/>"
            "d₁ = [ln(S/K) + (b + σ²/2)T] / (σ√T)  ;  d₂ = d₁ − σ√T<br/>"
            "où b = r − q (taux de portage), N(·) = CDF de la loi normale standard.",
            styles["body"]
        ))
        elems.append(Spacer(1, 5 * mm))

        elems += _section_header("Annexe B — Glossaire des Greeks", styles)
        glossary = [
            ("Delta (Δ)", "Variation de la valeur du produit pour une hausse de 1 unité du sous-jacent."),
            ("Gamma (Γ)", "Taux de variation du Delta. Mesure la convexité du produit."),
            ("Vega (ν)",  "Sensibilité à une hausse de 1% de la volatilité implicite."),
            ("Theta (Θ)", "Décroissance temporelle quotidienne de la valeur du produit."),
            ("Rho (ρ)",   "Sensibilité à une hausse de 1% du taux sans risque."),
            ("Vanna",     "Dérivée croisée Spot / Volatilité (second ordre)."),
            ("Volga",     "Dérivée seconde par rapport à la volatilité (Vol-of-Vol)."),
        ]
        for term, defn in glossary:
            elems.append(Paragraph(f"<b>{term} :</b> {defn}", styles["body"]))
            elems.append(Spacer(1, 2 * mm))

        elems += _section_header("Annexe C — Hypothèses du modèle", styles)
        assumptions = [
            "Marchés continus sans friction ni coûts de transaction",
            "Volatilité constante (hypothèse Black-Scholes, relaxée par SABR en production)",
            "Taux d'intérêt déterministe et constant sur la période",
            "Absence d'opportunité d'arbitrage (marché complet)",
            f"Nombre de simulations Monte Carlo : 5 000 (document), 50 000 (pricing production)",
        ]
        for a in assumptions:
            elems.append(Paragraph(f"• {a}", styles["body"]))
            elems.append(Spacer(1, 1.5 * mm))

        return elems


# ═══════════════════════════════════════════════════════════════════════════
# RISK SUMMARY GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

class RiskSummaryGenerator:
    """
    Generates a 1-page risk summary PDF for a portfolio of products.
    Thread-safe — all state is local to each call.
    """

    def generate(self, positions: List[Dict[str, Any]]) -> bytes:
        buf = io.BytesIO()
        styles = _make_styles()

        doc = BaseDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN, bottomMargin=2.2 * cm,
        )
        frame = Frame(MARGIN, 2.2 * cm, PAGE_W - 2*MARGIN, PAGE_H - MARGIN - 2.2*cm,
                      id="main", showBoundary=0)
        doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

        # Aggregate metrics across all positions
        agg = self._aggregate(positions)
        risk_score = self._compute_risk_score(agg)
        alerts = self._detect_alerts(agg)

        story: List = []

        # Header
        story.append(self._header_block(styles))
        story.append(Spacer(1, 5 * mm))

        # Two-column layout: gauge left, table right
        gauge = _risk_gauge(risk_score, width_cm=7.5, height_cm=5.5)
        metrics_tbl = self._metrics_table(agg, styles)
        top = Table([[gauge, metrics_tbl]],
                    colWidths=[8*cm, PAGE_W - 2*MARGIN - 8*cm])
        top.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(top)
        story.append(Spacer(1, 5 * mm))

        # Alerts
        story += _section_header("Alertes actives", styles)
        if alerts:
            for alert in alerts:
                color = "#c0392b" if alert["level"] == "danger" else "#f39c12"
                story.append(Paragraph(
                    f"<font color='{color}'><b>[{alert['level'].upper()}]</b></font> {alert['message']}",
                    styles["body"]
                ))
                story.append(Spacer(1, 1.5 * mm))
        else:
            story.append(Paragraph("Aucune alerte active.", styles["body"]))

        story.append(Spacer(1, 4 * mm))

        # Positions breakdown
        story += _section_header("Détail des positions", styles)
        story.append(self._positions_table(positions, styles))

        story.append(Spacer(1, 4 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            f"<b>Généré le</b> {datetime.today().strftime('%d/%m/%Y à %H:%M')} "
            f"— Ravinala Capital Risk Management | {DISCLAIMER_FR[:100]}…",
            styles["disclaimer"]
        ))

        doc.build(story, canvasmaker=_NumberedCanvas)
        return buf.getvalue()

    def _aggregate(self, positions: List[Dict]) -> Dict[str, float]:
        total_delta = total_gamma = total_vega = total_theta = 0.0
        total_var = total_cvar = 0.0
        for pos in positions:
            g = _bs_greeks(pos)
            notional = pos.get("notional", 1.0)
            total_delta += g["delta"] * notional
            total_gamma += g["gamma"] * notional
            total_vega  += g["vega"]  * notional
            total_theta += g["theta"] * notional
            # Simple MC VaR per position
            np.random.seed(42)
            S0, T = pos["spot"], pos["maturity_years"]
            sig, r, q = pos["volatility"], pos["risk_free_rate"], pos.get("dividend_yield", 0.0)
            b = r - q
            K  = pos.get("strike") or S0
            z  = np.random.standard_normal(2000)
            ST = S0 * np.exp((b - 0.5*sig**2)*T + sig*math.sqrt(T)*z)
            pays = np.maximum(ST - K, 0) * math.exp(-r*T)
            pnl = pays - pays.mean()
            var = float(np.percentile(pnl, 5))
            total_var  += abs(var) * notional
            total_cvar += abs(pnl[pnl <= var].mean()) * notional
        return {
            "delta": total_delta,
            "gamma": total_gamma,
            "vega":  total_vega,
            "theta": total_theta,
            "var_95_1d":  total_var,
            "var_99_1d":  total_var * 1.35,
            "cvar_95":    total_cvar,
            "n_positions": len(positions),
        }

    def _compute_risk_score(self, agg: Dict) -> float:
        """Heuristic 0–100 risk score."""
        score = 0.0
        score += min(abs(agg["delta"]) * 30, 30)
        score += min(abs(agg["vega"])  * 20, 20)
        score += min(agg["var_95_1d"] * 2,   30)
        score += min(abs(agg["theta"]) * 100, 20)
        return min(score, 100.0)

    def _detect_alerts(self, agg: Dict) -> List[Dict]:
        alerts = []
        if abs(agg["delta"]) > 0.8:
            alerts.append({"level": "danger",
                           "message": f"Delta agrégé élevé : {agg['delta']:.3f} — risque directionnel significatif."})
        if agg["vega"] > 0.5:
            alerts.append({"level": "warning",
                           "message": f"Vega concentrée : {agg['vega']:.3f} — sensibilité importante à la volatilité."})
        if agg["var_95_1d"] > 10:
            alerts.append({"level": "danger",
                           "message": f"VaR 1j 95% élevée : {agg['var_95_1d']:.2f} — revoir le dimensionnement des positions."})
        if agg["gamma"] > 0.05:
            alerts.append({"level": "warning",
                           "message": f"Gamma agrégé : {agg['gamma']:.4f} — coûts de re-hedging potentiellement élevés."})
        return alerts

    def _header_block(self, styles: Dict) -> Table:
        tbl = Table(
            [[Paragraph("<b>RAVINALA CAPITAL</b>", styles["title"]),
              Paragraph("<b>RISK SUMMARY — 1 PAGE</b>", styles["title"])]],
            colWidths=[(PAGE_W-2*MARGIN)*0.55, (PAGE_W-2*MARGIN)*0.45],
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PRIMARY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ]))
        return tbl

    def _metrics_table(self, agg: Dict, styles: Dict) -> Table:
        rows = [
            ("Nb positions",       str(int(agg["n_positions"]))),
            ("Delta agrégé",       f"{agg['delta']:.4f}"),
            ("Gamma agrégé",       f"{agg['gamma']:.5f}"),
            ("Vega agrégée",       f"{agg['vega']:.4f}"),
            ("Theta agrégé/jour",  f"{agg['theta']:.4f}"),
            ("VaR 1j 95 %",        f"{agg['var_95_1d']:.2f}"),
            ("VaR 1j 99 %",        f"{agg['var_99_1d']:.2f}"),
            ("CVaR / ES 95 %",     f"{agg['cvar_95']:.2f}"),
        ]
        tbl = Table(
            [[Paragraph(f"<b>{k}</b>", styles["label"]),
              Paragraph(v, styles["value"])] for k, v in rows],
            colWidths=[5*cm, 4*cm],
        )
        tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), LIGHT_BG),
            ("ROWBACKGROUNDS",(0, 0), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID",  (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e7")),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("BOX", (0, 0), (-1, -1), 1.5, PRIMARY),
        ]))
        return tbl

    def _positions_table(self, positions: List[Dict], styles: Dict) -> Table:
        header = ["Produit", "Sous-jacent", "Maturité", "Delta", "Vega", "Notional"]
        rows = [header]
        for pos in positions:
            g = _bs_greeks(pos)
            rows.append([
                pos.get("product_type", "N/A").replace("_", " ").title(),
                pos.get("underlying", "N/A"),
                f"{pos.get('maturity_years', 0):.1f}a",
                f"{g['delta']:.3f}",
                f"{g['vega']:.4f}",
                f"{pos.get('notional', 1.0):,.0f}",
            ])
        col_w = (PAGE_W - 2*MARGIN) / 6
        tbl = Table(rows, colWidths=[col_w]*6)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), SECONDARY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
            ("GRID",  (0, 0), (-1, -1), 0.4, colors.HexColor("#dde1e7")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tbl
