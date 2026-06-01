"""
Ravinala — P&L Attribution Engine Page
Taylor decomposition waterfall, multi-day path attribution, sensitivity analysis.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pnl_attribution import (
    attribute_pnl, simulate_price_path,
    multi_day_attribution, sensitivity_attribution, AttributionResult
)

# ── Theme ─────────────────────────────────────────────────────────────────────
_BG = "#0A0E1A"
_GRID = "rgba(255,255,255,0.05)"
_CYAN = "#00D9FF"
_GREEN = "#00FF9F"
_RED = "#FF4B4B"
_GOLD = "#FFD700"
_PURPLE = "#B44FFF"
_ORANGE = "#FF8C42"

_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    font=dict(family="Inter, sans-serif", size=12, color="#E8ECF3"),
    margin=dict(l=60, r=20, t=50, b=50),
)

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("P&L Attribution Engine")
st.caption("Taylor decomposition: ΔP = Δ·ΔS + ½Γ·ΔS² + ν·Δσ + Θ·Δt + Vanna·ΔS·Δσ + ½Volga·Δσ² + ρ·Δr + ε")

# ── Controls ──────────────────────────────────────────────────────────────────
with st.expander("Position Parameters", expanded=True):
    st.markdown("**Initial State**")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    S0      = c1.number_input("Spot S₀", min_value=0.01, value=100.0, step=1.0)
    K       = c2.number_input("Strike K", min_value=0.01, value=100.0, step=1.0)
    T_days  = c3.number_input("Expiry T (days)", min_value=2, max_value=3650, value=30)
    sig0_pct= c4.number_input("Vol σ₀ %", min_value=0.1, max_value=500.0, value=25.0, step=0.5)
    r_pct   = c5.number_input("Rate r %", min_value=0.0, max_value=30.0, value=5.0, step=0.1)
    div_pct = c6.number_input("Div Yield %", min_value=0.0, max_value=30.0, value=0.0, step=0.1)

    otype   = st.radio("Option Type", ["call", "put"], horizontal=True)
    qty     = st.number_input("Quantity (contracts)", min_value=1, max_value=1000, value=1)

    st.markdown("**Scenario (next day)**")
    d1, d2, d3, d4 = st.columns(4)
    S1      = d1.number_input("New Spot S₁", min_value=0.01, value=103.0, step=1.0)
    sig1_pct= d2.number_input("New Vol σ₁ %", min_value=0.1, max_value=500.0, value=26.0, step=0.5)
    dr_pct  = d3.number_input("Rate Shock Δr %", min_value=-5.0, max_value=5.0, value=0.0, step=0.1)
    dt_days = d4.number_input("Time Elapsed (days)", min_value=1, max_value=365, value=1)

T0     = T_days / 365.0
T1     = max(T0 - dt_days / 365.0, 1e-4)
sigma0 = sig0_pct / 100.0
sigma1 = sig1_pct / 100.0
r      = r_pct / 100.0
div    = div_pct / 100.0
dr     = dr_pct / 100.0

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "Single-Day Waterfall",
    "Multi-Day Path",
    "Formula Detail",
    "Sensitivity",
])

# ── TAB 1: Single-Day Waterfall ───────────────────────────────────────────────
with tab1:
    result = attribute_pnl(S0, S1, sigma0, sigma1, T0, T1, r, K, otype, qty, div, dr)
    bd = result.breakdown

    # Metric cards
    ma, mb, mc = st.columns(3)
    actual_color = _GREEN if result.total_actual >= 0 else _RED
    ma.metric("Actual P&L", f"${result.total_actual:,.2f}",
               delta=f"{result.total_actual:.2f}")
    mb.metric("Theoretical P&L", f"${result.total_theoretical:,.2f}")
    mc.metric("Residual (unexplained)", f"${result.residual:,.2f}")

    # Waterfall
    terms = list(bd.keys())
    values = list(bd.values())
    measure = ["relative"] * (len(terms) - 1) + ["relative"]

    # Colors: green if positive, red if negative
    colors_wf = [_GREEN if v >= 0 else _RED for v in values]

    fig_wf = go.Figure(go.Waterfall(
        name="P&L Attribution",
        orientation="v",
        measure=["relative"] * len(terms),
        x=terms,
        y=values,
        text=[f"${v:,.2f}" for v in values],
        textposition="outside",
        connector=dict(line=dict(color=_GRID, width=1)),
        increasing=dict(marker=dict(color=_GREEN)),
        decreasing=dict(marker=dict(color=_RED)),
        totals=dict(marker=dict(color=_CYAN)),
    ))
    fig_wf.update_layout(
        **_LAYOUT,
        title="Single-Day P&L Attribution Waterfall",
        xaxis_title="Component",
        yaxis_title="P&L ($)",
        yaxis=dict(gridcolor=_GRID, zeroline=True, zerolinecolor="rgba(255,255,255,0.3)"),
        height=440,
    )
    st.plotly_chart(fig_wf, use_container_width=True)

    # Detail table
    total = sum(abs(v) for v in values if v != result.residual) or 1.0
    rows_wf = []
    for term, val in bd.items():
        rows_wf.append({
            "Term": term,
            "P&L ($)": f"${val:,.4f}",
            "% of |Total|": f"{abs(val)/max(abs(result.total_actual), 1e-8)*100:.1f}%",
        })
    st.dataframe(pd.DataFrame(rows_wf), use_container_width=True, hide_index=True)

    # Explain residual
    if abs(result.residual) > 0.001 * abs(result.total_actual):
        st.info(
            f"**Residual ${result.residual:,.4f}** — The Taylor expansion truncates at 2nd order. "
            "Higher-order terms (particularly cross-gamma and higher vol terms) contribute to this residual. "
            "Large residuals indicate significant nonlinearity or large moves."
        )

# ── TAB 2: Multi-Day Path ──────────────────────────────────────────────────────
with tab2:
    pc1, pc2, pc3, pc4 = st.columns(4)
    n_days  = pc1.slider("Days", 5, 120, 30)
    n_paths = pc2.slider("Paths", 1, 10, 3)
    vol_drift = pc3.slider("Vol Drift/Day (bps)", -50, 50, 0) / 10000.0
    seed    = pc4.number_input("Seed", min_value=0, max_value=9999, value=42)

    paths = simulate_price_path(S0, sigma0, r, div, n_days, n_paths, int(seed))
    attr_df = multi_day_attribution(paths, K, T0, r, sigma0, otype, qty, div, vol_drift)

    # Price paths
    fig_paths = go.Figure()
    colors_path = [_CYAN, _GOLD, _GREEN, _ORANGE, _PURPLE, "#FF4B4B", "#FFFFFF", "#FF69B4", "#00FF9F", "#98FB98"]
    for p in range(1, n_paths + 1):
        pdata = paths[p - 1]
        fig_paths.add_trace(go.Scatter(
            x=list(range(len(pdata))),
            y=pdata,
            mode="lines",
            name=f"Path {p}",
            line=dict(color=colors_path[(p - 1) % len(colors_path)], width=1.5),
        ))
    fig_paths.add_hline(y=K, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"),
                        annotation_text=f"K={K:.2f}")
    fig_paths.update_layout(
        **_LAYOUT,
        title="Simulated Price Paths (GBM)",
        xaxis_title="Day",
        yaxis_title="Spot Price",
        xaxis=dict(gridcolor=_GRID),
        yaxis=dict(gridcolor=_GRID),
        height=320,
        legend=dict(orientation="h", y=1.06),
    )
    st.plotly_chart(fig_paths, use_container_width=True)

    if not attr_df.empty:
        # Cumulative P&L per path
        fig_cum = go.Figure()
        for p in range(1, n_paths + 1):
            pdata = attr_df[attr_df["path"] == p]
            fig_cum.add_trace(go.Scatter(
                x=pdata["day"],
                y=pdata["cumulative_pnl"],
                mode="lines",
                name=f"Path {p}",
                line=dict(color=colors_path[(p - 1) % len(colors_path)], width=1.8),
            ))
        fig_cum.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"))
        fig_cum.update_layout(
            **_LAYOUT,
            title="Cumulative P&L by Path",
            xaxis_title="Day",
            yaxis_title="Cumulative P&L ($)",
            xaxis=dict(gridcolor=_GRID),
            yaxis=dict(gridcolor=_GRID, zeroline=True, zerolinecolor="rgba(255,255,255,0.25)"),
            height=320,
            legend=dict(orientation="h", y=1.06),
        )
        st.plotly_chart(fig_cum, use_container_width=True)

        # Stacked attribution for path 1
        p1 = attr_df[attr_df["path"] == 1].copy()
        components = ["delta_pnl", "gamma_pnl", "vega_pnl", "theta_pnl", "vanna_pnl", "volga_pnl", "residual"]
        comp_labels = ["Delta", "Gamma", "Vega", "Theta", "Vanna", "Volga", "Residual"]
        comp_colors = [_CYAN, _GOLD, _ORANGE, _RED, _PURPLE, "#FF69B4", "#888888"]

        fig_stack = go.Figure()
        for comp, label, color in zip(components, comp_labels, comp_colors):
            fig_stack.add_trace(go.Bar(
                x=p1["day"], y=p1[comp],
                name=label, marker_color=color, opacity=0.8,
            ))
        fig_stack.update_layout(
            **_LAYOUT,
            barmode="relative",
            title="Daily Attribution Components — Path 1",
            xaxis_title="Day",
            yaxis_title="Daily P&L ($)",
            xaxis=dict(gridcolor=_GRID),
            yaxis=dict(gridcolor=_GRID, zeroline=True, zerolinecolor="rgba(255,255,255,0.3)"),
            legend=dict(orientation="h", y=1.06),
            height=360,
        )
        st.plotly_chart(fig_stack, use_container_width=True)

# ── TAB 3: Formula Detail ──────────────────────────────────────────────────────
with tab3:
    st.markdown("### Taylor Expansion P&L Attribution")
    st.latex(r"""
    \Delta P \approx \underbrace{\Delta \cdot \Delta S}_{\text{Delta}}
    + \underbrace{\frac{1}{2}\Gamma \cdot (\Delta S)^2}_{\text{Gamma}}
    + \underbrace{\nu \cdot \Delta\sigma}_{\text{Vega}}
    + \underbrace{\Theta \cdot \Delta t}_{\text{Theta}}
    + \underbrace{\text{Vanna} \cdot \Delta S \cdot \Delta\sigma}_{\text{Vanna}}
    + \underbrace{\frac{1}{2}\text{Volga} \cdot (\Delta\sigma)^2}_{\text{Volga}}
    + \underbrace{\rho \cdot \Delta r}_{\text{Rho}}
    + \varepsilon
    """)

    result2 = attribute_pnl(S0, S1, sigma0, sigma1, T0, T1, r, K, otype, qty, div, dr)
    dS = S1 - S0
    dsigma = sigma1 - sigma0
    dt = T1 - T0

    st.markdown("### Current Scenario Breakdown")
    rows_fm = [
        {"Term", "Formula", "Inputs", "Value ($)"},
    ]
    from engine import BlackScholesGreeks as BSG
    b0 = r - div
    delta_v  = BSG.delta(S0, K, T0, r, b0, sigma0, otype)
    gamma_v  = BSG.gamma(S0, K, T0, r, b0, sigma0)
    vega_v   = BSG.vega(S0, K, T0, r, b0, sigma0) * 100.0
    theta_v  = BSG.theta(S0, K, T0, r, b0, sigma0, otype)
    rho_v    = BSG.rho(S0, K, T0, r, b0, sigma0, otype) * 100.0
    vanna_v  = BSG.vanna(S0, K, T0, r, b0, sigma0)
    volga_v  = BSG.volga(S0, K, T0, r, b0, sigma0)
    scale    = qty * 100

    rows_fm = [
        {"Term": "Delta", "Formula": "Δ · ΔS", "Greek": f"Δ={delta_v:.5f}",
         "ΔInput": f"ΔS={dS:+.3f}", "Value ($)": f"${result2.delta_pnl:,.4f}"},
        {"Term": "Gamma", "Formula": "½Γ · (ΔS)²", "Greek": f"Γ={gamma_v:.6f}",
         "ΔInput": f"(ΔS)²={dS**2:.4f}", "Value ($)": f"${result2.gamma_pnl:,.4f}"},
        {"Term": "Vega", "Formula": "ν · Δσ", "Greek": f"ν={vega_v:.5f}",
         "ΔInput": f"Δσ={dsigma:+.4f}", "Value ($)": f"${result2.vega_pnl:,.4f}"},
        {"Term": "Theta", "Formula": "Θ · Δt", "Greek": f"Θ={theta_v:.6f}/day",
         "ΔInput": f"Δt={abs(dt)*365:.2f}d", "Value ($)": f"${result2.theta_pnl:,.4f}"},
        {"Term": "Vanna", "Formula": "Vanna · ΔS · Δσ", "Greek": f"Vanna={vanna_v:.6f}",
         "ΔInput": f"ΔS·Δσ={dS*dsigma:.6f}", "Value ($)": f"${result2.vanna_pnl:,.4f}"},
        {"Term": "Volga", "Formula": "½Volga · (Δσ)²", "Greek": f"Volga={volga_v:.4f}",
         "ΔInput": f"(Δσ)²={dsigma**2:.6f}", "Value ($)": f"${result2.volga_pnl:,.4f}"},
        {"Term": "Rho", "Formula": "ρ · Δr", "Greek": f"ρ={rho_v:.5f}",
         "ΔInput": f"Δr={dr:+.4f}", "Value ($)": f"${result2.rho_pnl:,.4f}"},
        {"Term": "Residual", "Formula": "Actual − Theoretical", "Greek": "—",
         "ΔInput": "—", "Value ($)": f"${result2.residual:,.4f}"},
        {"Term": "TOTAL (Actual)", "Formula": "BS(S₁,σ₁,T₁) − BS(S₀,σ₀,T₀)", "Greek": "—",
         "ΔInput": "—", "Value ($)": f"${result2.total_actual:,.4f}"},
    ]
    st.dataframe(pd.DataFrame(rows_fm), use_container_width=True, hide_index=True)

    st.markdown("### Greek Definitions")
    st.markdown("""
| Greek | Symbol | Definition |
|-------|--------|-----------|
| Delta | Δ | ∂V/∂S — sensitivity to spot |
| Gamma | Γ | ∂²V/∂S² — convexity to spot |
| Vega | ν | ∂V/∂σ — sensitivity to vol (per unit) |
| Theta | Θ | ∂V/∂t — time decay (per calendar day) |
| Vanna | — | ∂²V/∂S∂σ — cross sensitivity spot/vol |
| Volga | — | ∂²V/∂σ² — convexity to vol |
| Rho | ρ | ∂V/∂r — rate sensitivity (per unit) |
""")

# ── TAB 4: Sensitivity ──────────────────────────────────────────────────────────
with tab4:
    shock_range = st.slider("Spot Shock Range ±%", 5, 50, 25)
    sens_df = sensitivity_attribution(S0, sigma0, T0, r, K, otype, qty, div, shock_range/100)

    components_s = ["Delta", "Gamma", "Vega", "Theta", "Vanna", "Volga", "Total"]
    colors_s = [_CYAN, _GOLD, _ORANGE, _RED, _PURPLE, "#FF69B4", "#FFFFFF"]

    fig_sens = go.Figure()
    for comp, color in zip(components_s, colors_s):
        lw = 2.5 if comp == "Total" else 1.5
        dash = "solid" if comp == "Total" else "solid"
        fig_sens.add_trace(go.Scatter(
            x=sens_df["shock_pct"],
            y=sens_df[comp],
            mode="lines",
            name=comp,
            line=dict(color=color, width=lw, dash=dash),
        ))
    fig_sens.add_vline(x=0, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"))
    fig_sens.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"))
    fig_sens.update_layout(
        **_LAYOUT,
        title="P&L Attribution vs Spot Shock",
        xaxis_title="Spot Shock %",
        yaxis_title="P&L ($)",
        xaxis=dict(gridcolor=_GRID, zeroline=True, zerolinecolor="rgba(255,255,255,0.25)"),
        yaxis=dict(gridcolor=_GRID, zeroline=True, zerolinecolor="rgba(255,255,255,0.25)"),
        legend=dict(orientation="h", y=1.06),
        height=460,
    )
    st.plotly_chart(fig_sens, use_container_width=True)
