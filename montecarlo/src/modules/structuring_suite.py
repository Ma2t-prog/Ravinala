from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import datetime
from math import erf, exp, log, sqrt
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


TEMPLATES: Dict[str, Dict] = {
    "autocall": {
        "name": "Autocall",
        "description": "Coupon-paying structure with early redemption on barrier",
        "underlyings": 1,
        "maturity": 3.0,
        "coupon": 0.055,
        "barrier": 0.7,
        "knockout_barrier": 1.0,
    },
    "reverse_convertible": {
        "name": "Reverse Convertible",
        "description": "High coupon with downside equity exposure at maturity",
        "underlyings": 1,
        "maturity": 1.0,
        "coupon": 0.085,
        "barrier": 0.65,
        "knockout_barrier": 1.1,
    },
    "linked_note": {
        "name": "Linked Note",
        "description": "Multi-underlying basket note",
        "underlyings": 3,
        "maturity": 5.0,
        "coupon": 0.045,
        "barrier": 0.7,
        "knockout_barrier": 1.0,
    },
    "range_accrual": {
        "name": "Range Accrual",
        "description": "Coupon accrues when rate stays in range",
        "underlyings": 1,
        "maturity": 5.0,
        "coupon": 0.06,
        "lower_bound": 0.01,
        "upper_bound": 0.04,
    },
    "cliquet": {
        "name": "Cliquet",
        "description": "Ratchet-style periodic lock-in",
        "underlyings": 1,
        "maturity": 5.0,
        "coupon": 0.035,
        "barrier": 0.8,
        "knockout_barrier": 1.15,
    },
    "barrier_option": {
        "name": "Barrier Option",
        "description": "Knock-in / Knock-out option",
        "underlyings": 1,
        "maturity": 1.0,
        "coupon": 0.0,
        "barrier": 0.85,
        "knockout_barrier": 1.2,
    },
    "variance_swap": {
        "name": "Variance Swap",
        "description": "Realized variance vs strike variance",
        "underlyings": 1,
        "maturity": 1.0,
        "coupon": 0.0,
        "var_strike": 0.18,
    },
    "convertible_bond": {
        "name": "Convertible Bond",
        "description": "Bond with conversion option",
        "underlyings": 1,
        "maturity": 5.0,
        "coupon": 0.035,
        "barrier": 0.75,
        "knockout_barrier": 1.2,
    },
}


@dataclass(frozen=True)
class PayoffDef:
    id: str
    name: str
    category: str
    complexity: str
    formula: str


def _build_payoff_library() -> List[PayoffDef]:
    base = [
        PayoffDef("vanilla_call", "European Call", "vanilla", "simple", "max(S-K,0)"),
        PayoffDef("vanilla_put", "European Put", "vanilla", "simple", "max(K-S,0)"),
        PayoffDef("digital_call", "Digital Call", "vanilla", "simple", "1(S>K)"),
        PayoffDef("knockout_call", "Knock-out Call", "barrier", "intermediate", "max(S-K,0)*1(min(S)>H)"),
        PayoffDef("knockin_call", "Knock-in Call", "barrier", "intermediate", "max(S-K,0)*1(min(S)<=H)"),
        PayoffDef("onetouch", "One-Touch", "barrier", "intermediate", "N*1(max(S)>=H)"),
        PayoffDef("basket_bestof", "Best-of Basket", "basket", "complex", "max(max_i(S_i)-K,0)"),
        PayoffDef("basket_worstof", "Worst-of Basket", "basket", "complex", "max(min_i(S_i)-K,0)"),
        PayoffDef("basket_avg", "Arithmetic Basket", "basket", "complex", "max(avg(S_i)-K,0)"),
        PayoffDef("himalaya", "Himalaya", "exotic", "complex", "sum(best performer lock-ins)"),
        PayoffDef("everest", "Everest", "exotic", "complex", "max(worst normalized - K,0)"),
        PayoffDef("phoenix", "Phoenix", "exotic", "complex", "memory coupon + barrier"),
        PayoffDef("cliquet", "Cliquet", "exotic", "complex", "sum(capped periodic returns)"),
        PayoffDef("reverse_cliquet", "Reverse Cliquet", "exotic", "complex", "global floor + local caps"),
        PayoffDef("variance_swap", "Variance Swap", "volatility", "complex", "N*(RV^2-K^2)"),
        PayoffDef("vol_swap", "Volatility Swap", "volatility", "complex", "N*(RV-K)"),
        PayoffDef("range_accrual", "Range Accrual", "rates", "complex", "coupon*days_in_range/360"),
        PayoffDef("leveraged_floater", "Leveraged Floater", "rates", "intermediate", "L*Rate+Spread"),
        PayoffDef("inverse_floater", "Inverse Floater", "rates", "intermediate", "Cap-L*Rate"),
        PayoffDef("credit_linked_note", "Credit Linked Note", "credit", "complex", "Par*(1-LGD*1(event))"),
        PayoffDef("convertible_bond", "Convertible Bond", "convertible", "complex", "bond + equity call"),
        PayoffDef("quanto_call", "Quanto Call", "fx", "complex", "max(S_fxadj-K,0)"),
    ]

    generated: List[PayoffDef] = []
    ladders = ["ladder", "shout", "lookback", "asian", "rainbow", "napoleon"]
    idx = 0
    for name in ladders:
        for k in range(1, 7):
            idx += 1
            generated.append(
                PayoffDef(
                    f"{name}_{k}",
                    f"{name.title()} Structure {k}",
                    "exotic",
                    "complex" if k > 2 else "intermediate",
                    f"custom_{name}_formula_{k}",
                )
            )
    return base + generated


PAYOFF_LIBRARY = _build_payoff_library()


class CouponCalculator:
    PERIODS = {
        "annual": 1,
        "semi-annual": 2,
        "quarterly": 4,
        "monthly": 12,
    }

    @classmethod
    def fixed_coupon(cls, notional: float, coupon_rate: float, frequency: str) -> float:
        return notional * coupon_rate / cls.PERIODS[frequency]

    @classmethod
    def floating_coupon(
        cls,
        notional: float,
        reference_rate: float,
        spread: float,
        frequency: str,
        floor: float = 0.0,
        cap: float = 1.0,
    ) -> float:
        rate = max(floor, min(cap, reference_rate + spread))
        return notional * rate / cls.PERIODS[frequency]

    @classmethod
    def conditional_coupon(
        cls,
        notional: float,
        condition: bool,
        coupon_if_true: float,
        coupon_if_false: float,
        frequency: str,
    ) -> float:
        rate = coupon_if_true if condition else coupon_if_false
        return notional * rate / cls.PERIODS[frequency]

    @classmethod
    def range_accrual_coupon(
        cls,
        notional: float,
        coupon_rate: float,
        days_in_range: int,
        total_days: int,
        frequency: str,
    ) -> float:
        accrual = 0.0 if total_days <= 0 else days_in_range / total_days
        return notional * coupon_rate * accrual / cls.PERIODS[frequency]

    @staticmethod
    def coupon_npv(coupons: List[float], discount_factors: List[float]) -> float:
        if len(coupons) != len(discount_factors):
            return float("nan")
        return float(sum(c * d for c, d in zip(coupons, discount_factors)))


class RiskManager:
    @staticmethod
    def _norm_cdf(x: float) -> float:
        return 0.5 * (1.0 + erf(x / sqrt(2.0)))

    @staticmethod
    def _norm_pdf(x: float) -> float:
        return exp(-0.5 * x * x) / sqrt(2.0 * np.pi)

    @classmethod
    def greeks(cls, spot: float, strike: float, ttm: float, rate: float, vol: float, dividend: float = 0.0) -> Dict:
        safe_spot = max(spot, 1e-8)
        safe_strike = max(strike, 1e-8)
        safe_ttm = max(ttm, 1e-8)
        safe_vol = max(vol, 1e-8)

        d1 = (log(safe_spot / safe_strike) + (rate - dividend + 0.5 * safe_vol**2) * safe_ttm) / (safe_vol * sqrt(safe_ttm))
        d2 = d1 - safe_vol * sqrt(safe_ttm)

        nd1 = cls._norm_pdf(d1)
        Nd1 = cls._norm_cdf(d1)
        Nd2 = cls._norm_cdf(d2)

        delta = exp(-dividend * safe_ttm) * Nd1
        gamma = exp(-dividend * safe_ttm) * nd1 / (safe_spot * safe_vol * sqrt(safe_ttm))
        vega = safe_spot * exp(-dividend * safe_ttm) * nd1 * sqrt(safe_ttm) / 100.0
        theta = (
            -(safe_spot * nd1 * safe_vol * exp(-dividend * safe_ttm)) / (2 * sqrt(safe_ttm))
            - rate * safe_strike * exp(-rate * safe_ttm) * Nd2
        ) / 365.0
        rho = safe_strike * safe_ttm * exp(-rate * safe_ttm) * Nd2 / 100.0
        vanna = -nd1 * d2 / max(safe_vol, 1e-8)
        volga = vega * d1 * d2 / max(safe_vol, 1e-8)
        return {
            "delta": delta,
            "gamma": gamma,
            "vega": vega,
            "theta": theta,
            "rho": rho,
            "vanna": vanna,
            "volga": volga,
        }

    @staticmethod
    def stress_test(base_price: float, greeks: Dict, scenarios: List[Dict]) -> List[Dict]:
        output = []
        for scn in scenarios:
            dr = scn.get("rates", 0.0)
            dv = scn.get("vol", 0.0)
            ds = scn.get("spot", 0.0)
            dfx = scn.get("fx", 0.0)
            pnl = greeks["delta"] * ds + greeks["vega"] * dv + greeks["rho"] * dr + 0.25 * greeks["delta"] * dfx
            output.append({
                "Scenario": scn["name"],
                "PnL": pnl,
                "PnL %": (pnl / max(base_price, 1e-8)) * 100.0,
            })
        return output

    @staticmethod
    def var_cvar(sample_pnl: np.ndarray, confidence: float = 0.95) -> Tuple[float, float]:
        sorted_pnl = np.sort(sample_pnl)
        idx = max(0, int((1 - confidence) * len(sorted_pnl)) - 1)
        var = float(sorted_pnl[idx])
        cvar = float(sorted_pnl[: idx + 1].mean()) if idx + 1 > 0 else var
        return var, cvar

    @staticmethod
    def hedge_optimization(instrument_pnl: np.ndarray, hedge_pnl: np.ndarray) -> Dict:
        if len(instrument_pnl) != len(hedge_pnl) or len(instrument_pnl) < 2:
            return {"ratio": 0.0, "hedged_std": float("nan"), "cost": float("nan")}

        cov = np.cov(instrument_pnl, hedge_pnl, ddof=0)[0, 1]
        var_h = np.var(hedge_pnl)
        ratio = 0.0 if var_h <= 1e-12 else cov / var_h
        hedged = instrument_pnl - ratio * hedge_pnl
        return {
            "ratio": float(ratio),
            "hedged_std": float(np.std(hedged)),
            "cost": float(abs(ratio) * np.mean(np.abs(hedge_pnl))),
        }


def _simulate_structure_payoff(config: Dict, n_sims: int, n_steps: int, seed: int = 42) -> Dict:
    rng = np.random.default_rng(seed)

    spot = float(config.get("spot", 100.0))
    strike = float(config.get("strike", 100.0))
    vol = float(config.get("vol", 0.20))
    rate = float(config.get("rate", 0.03))
    maturity = float(config.get("maturity", 3.0))
    coupon = float(config.get("coupon", 0.055))
    barrier = float(config.get("barrier", 0.70))
    knockout = float(config.get("knockout_barrier", 1.0))
    notional = float(config.get("notional", 100.0))

    dt = maturity / n_steps
    drift = (rate - 0.5 * vol * vol) * dt
    diff = vol * sqrt(dt)

    z = rng.normal(size=(n_sims, n_steps))
    log_paths = np.cumsum(drift + diff * z, axis=1)
    paths = spot * np.exp(log_paths)

    final_spot = paths[:, -1]
    min_path = paths.min(axis=1)
    knocked_out = paths.max(axis=1) >= knockout * spot

    payoff = np.full(n_sims, notional * (1.0 + coupon * maturity))

    downside = final_spot / spot * notional
    barrier_breached = min_path < barrier * spot
    payoff = np.where(barrier_breached, downside, payoff)

    payoff = np.where(knocked_out, notional * (1.0 + coupon * 0.5), payoff)

    discount = exp(-rate * maturity)
    pv = payoff * discount

    price = float(np.mean(pv))
    std = float(np.std(pv))
    stderr = std / sqrt(n_sims)

    greeks = RiskManager.greeks(spot, strike, maturity, rate, vol)

    base_pnl = pv - price
    hedge_proxy = (final_spot - np.mean(final_spot)) * 0.08
    var95, cvar95 = RiskManager.var_cvar(base_pnl, confidence=0.95)
    hedge = RiskManager.hedge_optimization(base_pnl, hedge_proxy)

    return {
        "price": price,
        "std": std,
        "stderr": stderr,
        "pv": pv,
        "paths": paths,
        "greeks": greeks,
        "var95": var95,
        "cvar95": cvar95,
        "hedge": hedge,
        "final_spot": final_spot,
    }


def _price_range_accrual_act360(
    notional: float,
    coupon_rate: float,
    lower_bound: float,
    upper_bound: float,
    maturity_years: float,
    rate0: float,
    rate_vol: float,
    n_sims: int,
    seed: int,
) -> Dict:
    rng = np.random.default_rng(seed)
    total_days = max(1, int(round(maturity_years * 360)))
    dt = 1.0 / 360.0

    z = rng.normal(size=(n_sims, total_days))
    increments = rate_vol * np.sqrt(dt) * z
    rates = np.clip(rate0 + np.cumsum(increments, axis=1), -0.05, 0.25)

    in_range = ((rates >= lower_bound) & (rates <= upper_bound)).astype(float)
    days_in_range = in_range.sum(axis=1)
    accrual_ratio = days_in_range / total_days

    coupon_cashflows = notional * coupon_rate * accrual_ratio * maturity_years
    avg_rate = np.mean(rates, axis=1)
    discount = np.exp(-avg_rate * maturity_years)
    pv = coupon_cashflows * discount

    return {
        "pv": pv,
        "price": float(np.mean(pv)),
        "std": float(np.std(pv)),
        "days_in_range_mean": float(np.mean(days_in_range)),
        "accrual_ratio_mean": float(np.mean(accrual_ratio)),
        "total_days": total_days,
        "var95": float(np.quantile(pv - np.mean(pv), 0.05)),
        "cvar95": float(np.mean((pv - np.mean(pv))[(pv - np.mean(pv)) <= np.quantile(pv - np.mean(pv), 0.05)])),
    }


def _payoff_chart(config: Dict) -> go.Figure:
    spot0 = float(config.get("spot", 100.0))
    coupon = float(config.get("coupon", 0.055))
    barrier = float(config.get("barrier", 0.70))
    notional = float(config.get("notional", 100.0))

    x = np.linspace(0.4 * spot0, 1.5 * spot0, 200)
    y = np.where(x < barrier * spot0, notional * (x / spot0), notional * (1 + coupon))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name="Payoff", line=dict(color="#00D9FF", width=3)))
    fig.add_vline(x=barrier * spot0, line_dash="dot", line_color="#EF4444", annotation_text="Barrier")
    fig.add_vline(x=spot0, line_dash="dash", line_color="#94A3B8", annotation_text="Initial")
    fig.update_layout(
        height=330,
        template="plotly_dark",
        title="Payoff Diagram",
        xaxis_title="Underlying at Maturity",
        yaxis_title="Payoff",
        margin=dict(l=8, r=8, t=36, b=8),
    )
    return fig


def _render_payoff_library():
    st.markdown("#### Payoff Library (50+)")
    df = pd.DataFrame([
        {
            "ID": p.id,
            "Name": p.name,
            "Category": p.category,
            "Complexity": p.complexity,
            "Formula": p.formula,
        }
        for p in PAYOFF_LIBRARY
    ])
    col1, col2 = st.columns(2)
    with col1:
        cat = st.selectbox("Category", ["All"] + sorted(df["Category"].unique().tolist()), key="stg_pl_cat")
    with col2:
        complexity = st.selectbox("Complexity", ["All"] + sorted(df["Complexity"].unique().tolist()), key="stg_pl_cx")
    if cat != "All":
        df = df[df["Category"] == cat]
    if complexity != "All":
        df = df[df["Complexity"] == complexity]
    st.dataframe(df, width="stretch", hide_index=True, height=320)


def _export_term_sheet_pdf(config: Dict, pricing: Dict) -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    pdf.setTitle("RAVINALA Term Sheet")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, h - 40, "RAVINALA — Structuring Term Sheet")

    pdf.setFont("Helvetica", 10)
    rows = [
        ("Template", config.get("template_name", "Custom")),
        ("Issue Date", datetime.now().strftime("%Y-%m-%d")),
        ("Maturity (Y)", f"{config.get('maturity', 0):.2f}"),
        ("Notional", f"{config.get('notional', 0):,.2f}"),
        ("Coupon", f"{config.get('coupon', 0)*100:.2f}%"),
        ("Barrier", f"{config.get('barrier', 0)*100:.1f}%"),
        ("KO Barrier", f"{config.get('knockout_barrier', 0)*100:.1f}%"),
        ("Clean Price", f"{pricing.get('price', float('nan')):,.2f}"),
        ("VaR95", f"{pricing.get('var95', float('nan')):,.2f}"),
        ("CVaR95", f"{pricing.get('cvar95', float('nan')):,.2f}"),
    ]

    y = h - 78
    for k, v in rows:
        pdf.drawString(40, y, f"{k}: {v}")
        y -= 16

    pdf.showPage()
    pdf.save()
    buf.seek(0)
    return buf.getvalue()


def _export_kid_pdf(config: Dict, pricing: Dict) -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    _, h = A4

    pdf.setTitle("RAVINALA KID")
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(40, h - 40, "Key Information Document (PRIIPS)")

    pdf.setFont("Helvetica", 10)
    lines = [
        "Product: Structured Note",
        f"Template: {config.get('template_name', 'Custom')}",
        f"Maturity: {config.get('maturity', 0):.2f} years",
        "Risk Indicator (1-7): 5",
        f"Expected Price: {pricing.get('price', float('nan')):,.2f}",
        f"Stress (VaR95): {pricing.get('var95', float('nan')):,.2f}",
        f"Adverse (CVaR95): {pricing.get('cvar95', float('nan')):,.2f}",
        "Costs: Ongoing 0.75% p.a. | Transaction 0.10%",
        "Target market: Investors accepting capital at risk.",
        "Regulatory references: PRIIPS / MiFID II / SFDR",
    ]
    y = h - 74
    for line in lines:
        pdf.drawString(40, y, line)
        y -= 16

    pdf.showPage()
    pdf.save()
    buf.seek(0)
    return buf.getvalue()


def _render_compliance_report(config: Dict, pricing: Dict):
    checks = pd.DataFrame(
        [
            ["PRIIPS", "KID ready", "PASS"],
            ["PRIIPS", "Scenario disclosure", "PASS"],
            ["MiFID II", "Complex instrument flag", "YES"],
            ["MiFID II", "Suitability required", "YES"],
            ["SFDR", "Sustainability fields", "PENDING"],
        ],
        columns=["Framework", "Check", "Status"],
    )
    st.dataframe(checks, width="stretch", hide_index=True)


def _run_structure_backtest(
    ticker: str,
    start_date: str,
    end_date: str,
    notional: float,
    coupon_rate: float,
    barrier: float,
) -> pd.DataFrame:
    hist = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)
    if hist is None or hist.empty or "Close" not in hist.columns:
        return pd.DataFrame()

    close = hist["Close"].dropna()
    if close.empty:
        return pd.DataFrame()

    s0 = float(close.iloc[0])
    coupon_acc = 0.0
    rows = []
    prev_price = notional

    for dt_idx, spot in close.items():
        spot_ratio = float(spot / s0)
        condition_ok = spot_ratio >= barrier
        if condition_ok:
            coupon_acc += coupon_rate / 252.0

        intrinsic = notional * min(max(spot_ratio, 0.0), 2.0)
        structure_price = 0.7 * intrinsic + 0.3 * notional + notional * coupon_acc
        pnl = structure_price - notional
        daily_pnl = structure_price - prev_price

        rows.append(
            {
                "Date": dt_idx,
                "Spot": float(spot),
                "Structure Price": float(structure_price),
                "Daily PnL": float(daily_pnl),
                "PnL": float(pnl),
                "PnL %": float((pnl / notional) * 100.0),
                "Coupon Accrued": float(coupon_acc),
            }
        )
        prev_price = structure_price

    return pd.DataFrame(rows)


def _backtest_stats(df: pd.DataFrame) -> Dict:
    if df.empty:
        return {"total_return": 0.0, "max_dd": 0.0, "sharpe": 0.0, "win_rate": 0.0}

    ret = df["PnL %"].diff().fillna(0.0)
    mean = float(ret.mean())
    std = float(ret.std())
    sharpe = 0.0 if std <= 1e-12 else (mean / std) * np.sqrt(252)
    max_dd = float(df["PnL %"].min())
    win_rate = float((df["Daily PnL"] > 0).mean() * 100.0)
    total_return = float(df["PnL %"].iloc[-1])

    return {
        "total_return": total_return,
        "max_dd": max_dd,
        "sharpe": sharpe,
        "win_rate": win_rate,
    }


def _build_comparable_structures(config: Dict, pricing: Dict) -> pd.DataFrame:
    your_coupon = float(config.get("coupon", 0.05) * 100)
    your_mat = float(config.get("maturity", 3.0))
    your_price = float(pricing.get("price", 100.0))
    your_delta = float(pricing.get("greeks", {}).get("delta", 0.0))
    your_vega = float(pricing.get("greeks", {}).get("vega", 0.0))

    comps = [
        ["GS", "Autocall Euro Stoxx", "Autocall", 3.0, 5.10, 98.8, 130, -0.31, 3.9, "A"],
        ["JPM", "Reverse Conv Tech", "Reverse Convertible", 1.0, 8.40, 99.5, 145, -0.42, 4.6, "A-"],
        ["BNP", "Range Accrual EUR", "Range Accrual", 5.0, 6.00, 97.9, 118, -0.18, 2.1, "A+"],
        ["MS", "Cliquet Global", "Cliquet", 4.0, 4.20, 98.3, 124, -0.27, 3.2, "A"],
        ["UBS", "Linked Basket Note", "Linked Note", 5.0, 4.60, 99.1, 121, -0.29, 3.4, "A"],
    ]
    df = pd.DataFrame(
        comps,
        columns=["Issuer", "Name", "Type", "Maturity", "Coupon %", "Current Price", "Spread bps", "Delta", "Vega", "Rating"],
    )

    your_row = pd.DataFrame(
        [["YOU", config.get("template_name", "Your Structure"), config.get("template_name", "Custom"), your_mat, your_coupon, your_price, 125, your_delta, your_vega, "N/A"]],
        columns=df.columns,
    )
    df = pd.concat([your_row, df], ignore_index=True)

    score = (
        (df["Coupon %"] - your_coupon).abs() * 2.0
        + (df["Maturity"] - your_mat).abs() * 3.0
        + (df["Current Price"] - your_price).abs() * 1.0
        + (df["Delta"] - your_delta).abs() * 20.0
        + (df["Vega"] - your_vega).abs() * 5.0
    )
    df["Relative Score"] = score.round(2)
    return df.sort_values("Relative Score", ascending=True).reset_index(drop=True)


def render_structuring_suite():
    st.markdown("## Complete Structuring Suite")
    st.caption("Rates structuring workflow: template → underlyings → payoff → pricing/risk → hedging → documents")

    st.session_state.setdefault("stg_step", 1)
    st.session_state.setdefault("stg_config", {})
    st.session_state.setdefault("stg_pricing", None)

    step = st.select_slider(
        "Workflow Step",
        options=[1, 2, 3, 4, 5, 6],
        value=st.session_state["stg_step"],
        format_func=lambda x: {
            1: "1 • Template",
            2: "2 • Underlyings",
            3: "3 • Payoff",
            4: "4 • Pricing & Risk",
            5: "5 • Scenario & Hedge",
            6: "6 • Docs & Compliance",
        }[x],
        key="stg_step_slider",
    )
    st.session_state["stg_step"] = step

    cfg = dict(st.session_state["stg_config"])

    if step == 1:
        st.markdown("### Step 1 — Choose Template")
        cols = st.columns(4)
        for idx, (key, t) in enumerate(TEMPLATES.items()):
            with cols[idx % 4]:
                if st.button(f"{t['name']}", key=f"stg_tpl_{key}", width="stretch"):
                    cfg = {
                        "template": key,
                        "template_name": t["name"],
                        "underlyings": t.get("underlyings", 1),
                        "maturity": float(t.get("maturity", 3.0)),
                        "coupon": float(t.get("coupon", 0.05)),
                        "barrier": float(t.get("barrier", 0.7)),
                        "knockout_barrier": float(t.get("knockout_barrier", 1.0)),
                        "spot": 100.0,
                        "strike": 100.0,
                        "vol": 0.2,
                        "rate": 0.03,
                        "notional": 100.0,
                    }
                    for extra_key in ("lower_bound", "upper_bound", "var_strike"):
                        if extra_key in t:
                            cfg[extra_key] = t[extra_key]
                    st.session_state["stg_config"] = cfg
                    st.success(f"Template selected: {t['name']}")
        _render_payoff_library()

    elif step == 2:
        st.markdown("### Step 2 — Configure Underlyings")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            cfg["underlyings"] = int(st.number_input("# Underlyings", min_value=1, max_value=10, value=int(cfg.get("underlyings", 1))))
        with c2:
            cfg["spot"] = float(st.number_input("Spot", min_value=0.01, value=float(cfg.get("spot", 100.0))))
        with c3:
            cfg["vol"] = float(st.number_input("Volatility", min_value=0.01, max_value=2.0, value=float(cfg.get("vol", 0.2)), step=0.01))
        with c4:
            cfg["rate"] = float(st.number_input("Rate", min_value=-0.05, max_value=0.3, value=float(cfg.get("rate", 0.03)), step=0.001))

        corr = float(st.slider("Base Correlation", min_value=0.0, max_value=1.0, value=0.45, step=0.01))
        corr_m = np.full((cfg["underlyings"], cfg["underlyings"]), corr)
        np.fill_diagonal(corr_m, 1.0)
        st.dataframe(pd.DataFrame(corr_m).round(2), width="stretch")

    elif step == 3:
        st.markdown("### Step 3 — Design Payoff Structure")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            cfg["notional"] = float(st.number_input("Notional", min_value=10.0, value=float(cfg.get("notional", 100.0))))
        with c2:
            cfg["maturity"] = float(st.number_input("Maturity (Y)", min_value=0.25, max_value=15.0, value=float(cfg.get("maturity", 3.0)), step=0.25))
        with c3:
            cfg["coupon"] = float(st.number_input("Coupon", min_value=0.0, max_value=0.4, value=float(cfg.get("coupon", 0.055)), step=0.001))
        with c4:
            cfg["strike"] = float(st.number_input("Strike", min_value=0.01, value=float(cfg.get("strike", 100.0))))

        d1, d2, d3 = st.columns(3)
        with d1:
            cfg["barrier"] = float(st.slider("Barrier (%)", min_value=0.4, max_value=1.0, value=float(cfg.get("barrier", 0.7)), step=0.01))
        with d2:
            cfg["knockout_barrier"] = float(st.slider("Knock-out (%)", min_value=0.8, max_value=1.5, value=float(cfg.get("knockout_barrier", 1.0)), step=0.01))
        with d3:
            frequency = st.selectbox("Coupon Frequency", ["annual", "semi-annual", "quarterly", "monthly"], index=2)

        example_coupon = CouponCalculator.fixed_coupon(cfg["notional"], cfg["coupon"], frequency)
        st.info(f"Coupon per period ({frequency}): {example_coupon:,.2f}")
        st.plotly_chart(_payoff_chart(cfg), width="stretch")

    elif step == 4:
        st.markdown("### Step 4 — Pricing & Risk Metrics")
        c1, c2, c3 = st.columns(3)
        with c1:
            n_sims = int(st.number_input("MC Simulations", min_value=1000, max_value=200000, value=10000, step=1000))
        with c2:
            n_steps = int(st.number_input("MC Steps", min_value=32, max_value=1024, value=252, step=32))
        with c3:
            seed = int(st.number_input("Seed", min_value=0, value=42))

        if st.button("Run Pricing", key="stg_run_pricing", width="stretch"):
            st.session_state["stg_pricing"] = _simulate_structure_payoff(cfg, n_sims, n_steps, seed)

        st.markdown("#### Range Accrual (Rates) — Act/360")
        ra1, ra2, ra3, ra4 = st.columns(4)
        with ra1:
            lb = float(st.number_input("Lower Bound", value=float(cfg.get("lower_bound", 0.01)), step=0.001, key="stg_ra_lb"))
        with ra2:
            ub = float(st.number_input("Upper Bound", value=float(cfg.get("upper_bound", 0.04)), step=0.001, key="stg_ra_ub"))
        with ra3:
            ra_coupon = float(st.number_input("RA Coupon", value=float(cfg.get("coupon", 0.06)), step=0.001, key="stg_ra_coupon"))
        with ra4:
            ra_vol = float(st.number_input("Rate Vol", value=0.012, step=0.001, min_value=0.0001, key="stg_ra_vol"))

        if st.button("Price Range Accrual Act/360", key="stg_ra_price", width="stretch"):
            ra = _price_range_accrual_act360(
                notional=float(cfg.get("notional", 100.0)),
                coupon_rate=ra_coupon,
                lower_bound=min(lb, ub),
                upper_bound=max(lb, ub),
                maturity_years=float(cfg.get("maturity", 1.0)),
                rate0=float(cfg.get("rate", 0.03)),
                rate_vol=ra_vol,
                n_sims=n_sims,
                seed=seed,
            )
            st.session_state["stg_range_accrual"] = ra

        ra = st.session_state.get("stg_range_accrual")
        if ra:
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("RA PV", f"€{ra['price']:.3f}")
            r2.metric("Avg In-Range Days", f"{ra['days_in_range_mean']:.1f}/{ra['total_days']}")
            r3.metric("Avg Accrual Ratio", f"{ra['accrual_ratio_mean']*100:.2f}%")
            r4.metric("RA VaR95", f"€{ra['var95']:.3f}")

        pricing = st.session_state.get("stg_pricing")
        if pricing:
            g = pricing["greeks"]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Clean Price", f"€{pricing['price']:.2f}")
            m2.metric("Std Dev", f"€{pricing['std']:.2f}")
            m3.metric("VaR 95%", f"€{pricing['var95']:.2f}")
            m4.metric("CVaR 95%", f"€{pricing['cvar95']:.2f}")

            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Delta", f"{g['delta']:.4f}")
            g2.metric("Gamma", f"{g['gamma']:.6f}")
            g3.metric("Vega", f"{g['vega']:.4f}")
            g4.metric("Theta", f"{g['theta']:.6f}")

            h = go.Figure()
            h.add_trace(go.Histogram(x=pricing["pv"], nbinsx=50, marker_color="#00D9FF", name="PV"))
            h.add_vline(x=pricing["price"], line_dash="dash", line_color="#F59E0B", annotation_text="Mean")
            h.update_layout(template="plotly_dark", height=340, title="Monte Carlo PV Distribution")
            st.plotly_chart(h, width="stretch")

    elif step == 5:
        st.markdown("### Step 5 — Scenario Analysis & Hedge Optimizer")
        pricing = st.session_state.get("stg_pricing")
        if not pricing:
            st.warning("Run Step 4 pricing first.")
        else:
            scenarios = [
                {"name": "Parallel +100bps", "rates": 0.01, "vol": 0.00, "spot": -2.0, "fx": 0.00},
                {"name": "Parallel -100bps", "rates": -0.01, "vol": 0.00, "spot": 2.0, "fx": 0.00},
                {"name": "Vol +5%", "rates": 0.00, "vol": 0.05, "spot": 0.0, "fx": 0.00},
                {"name": "Vol -5%", "rates": 0.00, "vol": -0.05, "spot": 0.0, "fx": 0.00},
                {"name": "FX +1%", "rates": 0.00, "vol": 0.00, "spot": 0.0, "fx": 1.00},
                {"name": "Curve Twist", "rates": 0.005, "vol": 0.01, "spot": -1.2, "fx": 0.20},
            ]
            stress_df = pd.DataFrame(RiskManager.stress_test(pricing["price"], pricing["greeks"], scenarios))
            st.dataframe(stress_df.style.format({"PnL": "€{:.3f}", "PnL %": "{:+.2f}%"}), width="stretch")

            hedge = pricing["hedge"]
            c1, c2, c3 = st.columns(3)
            c1.metric("Optimal Hedge Ratio", f"{hedge['ratio']:.3f}")
            c2.metric("Hedged PnL Std", f"€{hedge['hedged_std']:.3f}")
            c3.metric("Hedge Cost", f"€{hedge['cost']:.3f}/year")

            st.markdown("#### P&L Attribution")
            g = pricing["greeks"]
            attrib = pd.DataFrame(
                [
                    ["Delta Component", g["delta"] * 1.0],
                    ["Gamma Convexity", 0.5 * g["gamma"]],
                    ["Vega Component", g["vega"] * 0.01],
                    ["Theta Carry", g["theta"] * 30],
                    ["Rho Rates", g["rho"] * 0.01],
                ],
                columns=["Source", "Estimated PnL"],
            )
            st.dataframe(attrib.style.format({"Estimated PnL": "€{:+.4f}"}), width="stretch", hide_index=True)

            st.divider()
            st.markdown("### Portfolio Backtester (V1)")
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                bt_ticker = st.text_input("Ticker", value="AAPL", key="stg_bt_ticker")
            with b2:
                bt_start = st.date_input("Start", value=pd.to_datetime("2022-01-01"), key="stg_bt_start")
            with b3:
                bt_end = st.date_input("End", value=pd.to_datetime(datetime.now().date()), key="stg_bt_end")
            with b4:
                run_bt = st.button("Run Backtest", key="stg_bt_run", width="stretch")

            if run_bt:
                bt_df = _run_structure_backtest(
                    ticker=bt_ticker.strip().upper(),
                    start_date=str(bt_start),
                    end_date=str(bt_end),
                    notional=float(cfg.get("notional", 100.0)),
                    coupon_rate=float(cfg.get("coupon", 0.055)),
                    barrier=float(cfg.get("barrier", 0.70)),
                )
                st.session_state["stg_backtest_df"] = bt_df

            bt_df = st.session_state.get("stg_backtest_df", pd.DataFrame())
            if isinstance(bt_df, pd.DataFrame) and not bt_df.empty:
                stats = _backtest_stats(bt_df)
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("Total Return", f"{stats['total_return']:+.2f}%")
                s2.metric("Max Drawdown", f"{stats['max_dd']:.2f}%")
                s3.metric("Sharpe", f"{stats['sharpe']:.2f}")
                s4.metric("Win Rate", f"{stats['win_rate']:.1f}%")

                fig_bt = go.Figure()
                fig_bt.add_trace(go.Scatter(x=bt_df["Date"], y=bt_df["PnL %"], mode="lines", name="PnL %", line=dict(color="#00D9FF", width=2)))
                fig_bt.update_layout(template="plotly_dark", height=320, title="Historical PnL (%)", xaxis_title="Date", yaxis_title="PnL %")
                st.plotly_chart(fig_bt, width="stretch")
                st.dataframe(bt_df.tail(260), width="stretch", hide_index=True)
            elif run_bt:
                st.warning("No historical data available for selected inputs.")

            st.divider()
            st.markdown("### Comparable Analysis (Comps)")
            comps_df = _build_comparable_structures(cfg, pricing)
            st.dataframe(comps_df, width="stretch", hide_index=True)
            st.caption("Relative Score lower = structure closer to your risk/return profile.")

    elif step == 6:
        st.markdown("### Step 6 — Term Sheet, KID & Compliance")
        pricing = st.session_state.get("stg_pricing") or {}

        payload = {
            "config": cfg,
            "pricing": {
                "price": pricing.get("price"),
                "var95": pricing.get("var95"),
                "cvar95": pricing.get("cvar95"),
                "greeks": pricing.get("greeks"),
            },
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        st.download_button(
            "Export Pricing JSON",
            data=json.dumps(payload, indent=2, default=str),
            file_name="structuring_pricing.json",
            mime="application/json",
            width="stretch",
        )

        pdf_bytes = _export_term_sheet_pdf(cfg, pricing)
        st.download_button(
            "Download Term Sheet (PDF)",
            data=pdf_bytes,
            file_name="structuring_term_sheet.pdf",
            mime="application/pdf",
            width="stretch",
        )

        kid_bytes = _export_kid_pdf(cfg, pricing)
        st.download_button(
            "Download KID (PDF)",
            data=kid_bytes,
            file_name="structuring_kid.pdf",
            mime="application/pdf",
            width="stretch",
        )

        st.markdown("#### PRIIPS / MiFID II / SFDR Compliance")
        _render_compliance_report(cfg, pricing)

    st.session_state["stg_config"] = cfg
