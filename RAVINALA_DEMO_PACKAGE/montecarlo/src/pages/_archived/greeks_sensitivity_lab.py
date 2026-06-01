"""
Ravinala — Greeks & Sensitivity Lab
Full analytical Greeks (engine.py), sensitivity heatmaps, profiles, P&L attribution.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from engine import BlackScholesGreeks

BSG = BlackScholesGreeks

# ── Theme ─────────────────────────────────────────────────────────────────────
_BG    = "#0A0E1A"
_SURF  = "#131823"
_GRID  = "rgba(255,255,255,0.05)"
_CYAN  = "#00D9FF"
_GREEN = "#10B981"
_RED   = "#EF4444"
_GOLD  = "#F59E0B"
_PURPLE= "#A78BFA"
_ORANGE= "#F97316"

_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    font=dict(family="Inter, sans-serif", size=12, color="#E8ECF3"),
    margin=dict(l=60, r=20, t=50, b=50),
)

# ── Page header ───────────────────────────────────────────────────────────────
st.title("Greeks & Sensitivity Lab")
st.caption("Analytical Greeks · Sensitivity profiles · Heatmaps · P&L attribution")

# ── Parameter panel ───────────────────────────────────────────────────────────
with st.expander("Position Parameters", expanded=True):
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    S       = c1.number_input("Spot (S)",      min_value=0.01, value=100.0,  step=1.0,  key="gl_S")
    K       = c2.number_input("Strike (K)",    min_value=0.01, value=100.0,  step=1.0,  key="gl_K")
    T_days  = c3.number_input("Expiry (days)", min_value=1,    value=90,     step=1,    key="gl_Td")
    r_pct   = c4.number_input("Rate %",        min_value=0.0,  value=5.0,    step=0.1,  key="gl_r")
    sig_pct = c5.number_input("Vol %",         min_value=0.1,  value=25.0,   step=0.5,  key="gl_sig")
    div_pct = c6.number_input("Div Yield %",   min_value=0.0,  value=0.0,    step=0.1,  key="gl_div")
    otype   = c7.radio("Type", ["call", "put"], key="gl_otype")

T     = max(T_days / 365.0, 1e-6)
r     = r_pct   / 100.0
sigma = sig_pct / 100.0
div   = div_pct / 100.0
b     = r - div   # carry: b = r - q

# ── Compute all Greeks ────────────────────────────────────────────────────────
price  = BSG.call_price(S, K, T, r, b, sigma) if otype == "call" else BSG.put_price(S, K, T, r, b, sigma)
delta  = BSG.delta(S, K, T, r, b, sigma, option_type=otype)
gamma  = BSG.gamma(S, K, T, r, b, sigma)
vega   = BSG.vega(S, K, T, r, b, sigma)          # per 1% vol
theta  = BSG.theta(S, K, T, r, b, sigma, option_type=otype)   # per day
rho    = BSG.rho(S, K, T, r, b, sigma, option_type=otype)     # per 1% rate
vanna  = BSG.vanna(S, K, T, r, b, sigma)
volga  = BSG.volga(S, K, T, r, b, sigma)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "Greeks Dashboard",
    "Sensitivity Profiles",
    "Heatmaps",
    "P&L Attribution",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — GREEKS DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    # ── 7 metric cards ──
    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    m1.metric("Price",  f"{price:.4f}")
    m2.metric("Delta",  f"{delta:.4f}", help="∂P/∂S — hedge ratio")
    m3.metric("Gamma",  f"{gamma:.6f}", help="∂²P/∂S² — convexity")
    m4.metric("Vega",   f"{vega:.4f}",  help="∂P/∂σ per 1% vol")
    m5.metric("Theta",  f"{theta:.4f}", help="∂P/∂t per day (decay)")
    m6.metric("Rho",    f"{rho:.4f}",   help="∂P/∂r per 1% rate")
    m7.metric("Vanna",  f"{vanna:.5f}", help="∂²P/∂S∂σ cross-greek")

    st.divider()

    # ── Greeks vs Spot — all in one multi-panel ──
    spot_range = np.linspace(S * 0.5, S * 1.5, 200)

    d_arr  = np.array([BSG.delta(float(s), K, T, r, b, sigma, option_type=otype) for s in spot_range])
    g_arr  = np.array([BSG.gamma(float(s), K, T, r, b, sigma) for s in spot_range])
    v_arr  = np.array([BSG.vega(float(s),  K, T, r, b, sigma) for s in spot_range])
    th_arr = np.array([BSG.theta(float(s), K, T, r, b, sigma, option_type=otype) for s in spot_range])
    p_arr  = np.array([
        BSG.call_price(float(s), K, T, r, b, sigma) if otype == "call"
        else BSG.put_price(float(s), K, T, r, b, sigma)
        for s in spot_range
    ])

    fig = make_subplots(
        rows=2, cols=3,
        shared_xaxes=False,
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
        subplot_titles=["Price", "Delta", "Gamma", "Vega", "Theta", "Vanna"],
    )

    SERIES = [
        (p_arr,  _CYAN,   1, 1),
        (d_arr,  _GREEN,  1, 2),
        (g_arr,  _GOLD,   1, 3),
        (v_arr,  _PURPLE, 2, 1),
        (th_arr, _RED,    2, 2),
        (np.array([BSG.vanna(float(s), K, T, r, b, sigma) for s in spot_range]), _ORANGE, 2, 3),
    ]
    for arr, color, row, col in SERIES:
        fig.add_trace(
            go.Scatter(x=spot_range, y=arr, mode="lines",
                       line=dict(color=color, width=2), showlegend=False),
            row=row, col=col,
        )
        fig.add_vline(x=S, line=dict(color="#475569", width=1, dash="dot"), row=row, col=col)
        fig.add_vline(x=K, line=dict(color="#334155", width=1, dash="dash"), row=row, col=col)

    fig.update_layout(**_LAYOUT, height=520,
                      title=dict(text=f"All Greeks vs Spot — {otype.upper()} K={K} T={T_days}d", font=dict(color="#F1F5F9", size=13)))
    for r_i in range(1, 3):
        for c_i in range(1, 4):
            fig.update_xaxes(gridcolor=_GRID, tickfont=dict(color="#94A3B8"), row=r_i, col=c_i)
            fig.update_yaxes(gridcolor=_GRID, tickfont=dict(color="#94A3B8"), row=r_i, col=c_i)

    st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Cyan line = current spot S={S:.2f} · Dashed line = strike K={K:.2f}")

    # ── Greeks summary table ──
    tbl = pd.DataFrame({
        "Greek":          ["Price", "Delta (Δ)", "Gamma (Γ)", "Vega (ν)", "Theta (Θ)", "Rho (ρ)", "Vanna", "Volga"],
        "Value":          [f"{price:.6f}", f"{delta:.6f}", f"{gamma:.8f}", f"{vega:.6f}", f"{theta:.6f}", f"{rho:.6f}", f"{vanna:.6f}", f"{volga:.6f}"],
        "Interpretation": [
            f"Current {'call' if otype=='call' else 'put'} price",
            f"{delta*100:.2f}% of a unit spot move | hedge {delta:.4f} shares per option",
            f"Delta changes by {gamma:.4f} per $1 spot move",
            f"${vega:.4f} P&L per 1% vol move",
            f"${theta:.4f} lost per calendar day",
            f"${rho:.4f} P&L per 1% rate move",
            f"Delta changes by {vanna:.4f} per 1% vol move",
            f"Vega changes by {volga:.4f} per 1% vol move (vol convexity)",
        ]
    })
    st.dataframe(tbl, use_container_width=True, hide_index=True)

    csv = tbl.to_csv(index=False)
    st.download_button("Download Greeks (CSV)", csv,
                       file_name=f"greeks_{otype}_K{K}_T{T_days}.csv", mime="text/csv")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — SENSITIVITY PROFILES
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    profile_axis = st.radio("Vary", ["Spot", "Volatility", "Time to Expiry", "Rate"],
                            horizontal=True, key="gl_profile_axis")
    greek_sel = st.selectbox("Greek to display",
                             ["Price", "Delta", "Gamma", "Vega", "Theta", "Rho", "Vanna", "Volga"],
                             key="gl_greek_sel")

    def _compute_greek(greek, S_, K_, T_, r_, b_, sig_):
        sig_ = max(sig_, 1e-6)
        T_   = max(T_,   1e-6)
        if greek == "Price":  return BSG.call_price(S_, K_, T_, r_, b_, sig_) if otype == "call" else BSG.put_price(S_, K_, T_, r_, b_, sig_)
        if greek == "Delta":  return BSG.delta(S_, K_, T_, r_, b_, sig_, option_type=otype)
        if greek == "Gamma":  return BSG.gamma(S_, K_, T_, r_, b_, sig_)
        if greek == "Vega":   return BSG.vega(S_, K_, T_, r_, b_, sig_)
        if greek == "Theta":  return BSG.theta(S_, K_, T_, r_, b_, sig_, option_type=otype)
        if greek == "Rho":    return BSG.rho(S_, K_, T_, r_, b_, sig_, option_type=otype)
        if greek == "Vanna":  return BSG.vanna(S_, K_, T_, r_, b_, sig_)
        if greek == "Volga":  return BSG.volga(S_, K_, T_, r_, b_, sig_)
        return 0.0

    # Build series for selected axis
    if profile_axis == "Spot":
        x_range = np.linspace(S * 0.4, S * 1.6, 200)
        y_vals  = np.array([_compute_greek(greek_sel, float(x), K, T, r, b, sigma) for x in x_range])
        x_label = "Spot Price"
        ref_val = S
    elif profile_axis == "Volatility":
        x_range = np.linspace(0.01, 1.5, 200)
        y_vals  = np.array([_compute_greek(greek_sel, S, K, T, r, r - div, float(x)) for x in x_range])
        x_label = "Volatility"
        ref_val = sigma
    elif profile_axis == "Time to Expiry":
        x_range = np.linspace(0.01, max(T * 3, 2.0), 200)
        y_vals  = np.array([_compute_greek(greek_sel, S, K, float(x), r, b, sigma) for x in x_range])
        x_label = "Time to Expiry (years)"
        ref_val = T
    else:  # Rate
        x_range = np.linspace(0.0, 0.15, 200)
        y_vals  = np.array([_compute_greek(greek_sel, S, K, T, float(x), float(x) - div, sigma) for x in x_range])
        x_label = "Risk-free Rate"
        ref_val = r

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=x_range, y=y_vals,
        mode="lines",
        line=dict(color=_CYAN, width=2.5),
        name=greek_sel,
        fill="tozeroy", fillcolor="rgba(0,217,255,0.06)",
    ))
    fig2.add_vline(x=ref_val,
                   line=dict(color="#94A3B8", width=1, dash="dot"),
                   annotation_text=f"Current ({ref_val:.3g})",
                   annotation_font_color="#94A3B8",
                   annotation_position="top right")

    fig2.update_layout(
        **_LAYOUT, height=440,
        xaxis=dict(title=x_label, gridcolor=_GRID, tickfont=dict(color="#94A3B8")),
        yaxis=dict(title=greek_sel, gridcolor=_GRID, tickfont=dict(color="#94A3B8")),
        title=dict(text=f"{greek_sel} vs {profile_axis} — {otype.upper()} K={K}", font=dict(color="#F1F5F9", size=13)),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Second: show all Greeks on same axis at once
    st.markdown("<p style='color:#94A3B8;font-size:12px;margin-top:8px'>All Greeks normalised to [−1, 1] for comparison:</p>", unsafe_allow_html=True)

    GREEK_LIST = ["Delta", "Gamma", "Vega", "Theta", "Rho"]
    COLORS_LIST = [_GREEN, _GOLD, _PURPLE, _RED, _ORANGE]

    fig3 = go.Figure()
    for gname, gcolor in zip(GREEK_LIST, COLORS_LIST):
        if profile_axis == "Spot":
            arr = np.array([_compute_greek(gname, float(x), K, T, r, b, sigma) for x in x_range])
        elif profile_axis == "Volatility":
            arr = np.array([_compute_greek(gname, S, K, T, r, r - div, float(x)) for x in x_range])
        elif profile_axis == "Time to Expiry":
            arr = np.array([_compute_greek(gname, S, K, float(x), r, b, sigma) for x in x_range])
        else:
            arr = np.array([_compute_greek(gname, S, K, T, float(x), float(x) - div, sigma) for x in x_range])

        # Normalise
        a_max = np.nanmax(np.abs(arr))
        if a_max > 1e-12:
            arr = arr / a_max

        fig3.add_trace(go.Scatter(
            x=x_range, y=arr, mode="lines",
            name=gname, line=dict(color=gcolor, width=1.8),
        ))

    fig3.add_vline(x=ref_val, line=dict(color="#475569", width=1, dash="dot"))
    fig3.add_hline(y=0, line=dict(color="#334155", width=1))

    fig3.update_layout(
        **_LAYOUT, height=340,
        xaxis=dict(title=x_label, gridcolor=_GRID, tickfont=dict(color="#94A3B8")),
        yaxis=dict(title="Normalised value", gridcolor=_GRID, tickfont=dict(color="#94A3B8")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    font=dict(color="#CBD5E1", size=11)),
    )
    st.plotly_chart(fig3, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — HEATMAPS
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    metric_h = st.selectbox("Metric", ["Price", "Delta", "Gamma", "Vega", "Theta", "Rho"],
                             key="gl_hm_metric")
    hc1, hc2, hc3, hc4 = st.columns(4)
    n_sp     = hc1.slider("Spot points",   7, 21, 13, step=2, key="gl_nsp")
    sp_rng   = hc2.slider("Spot range ±%", 10, 50, 30, step=5, key="gl_sprng")
    n_vl     = hc3.slider("Vol points",    5, 15, 11, step=2, key="gl_nvl")
    vl_rng   = hc4.slider("Vol range ±%",  20, 100, 50, step=10, key="gl_vlrng")

    spot_moves = np.linspace(-sp_rng / 100, sp_rng / 100, n_sp)
    vol_moves  = np.linspace(-vl_rng / 100, vl_rng / 100, n_vl)

    matrix = np.empty((len(spot_moves), len(vol_moves)), dtype=float)
    for i, ds in enumerate(spot_moves):
        S_new = S * (1.0 + ds)
        for j, dv in enumerate(vol_moves):
            sig_new = max(sigma * (1.0 + dv), 1e-6)
            matrix[i, j] = _compute_greek(metric_h, S_new, K, T, r, b, sig_new)

    x_lbl = [f"{v*100:+.0f}%" for v in vol_moves]
    y_lbl = [f"{v*100:+.0f}%" for v in spot_moves]

    use_div = metric_h in ("Price",)
    cscale  = [[0, _RED], [0.5, "#1F2937"], [1, _GREEN]] if metric_h == "Price" else "Viridis"

    fig4 = go.Figure(go.Heatmap(
        z=matrix, x=x_lbl, y=y_lbl,
        colorscale=cscale,
        text=[[f"{matrix[i,j]:+.4f}" if abs(matrix[i,j]) < 100 else f"{matrix[i,j]:+.2f}"
               for j in range(len(vol_moves))] for i in range(len(spot_moves))],
        texttemplate="%{text}",
        colorbar=dict(thickness=12, tickfont=dict(color="#94A3B8", size=10)),
    ))

    # highlight current cell
    zi = int(np.argmin(np.abs(spot_moves)))
    zj = int(np.argmin(np.abs(vol_moves)))
    fig4.add_shape(type="rect",
                   x0=zj - 0.5, x1=zj + 0.5, y0=zi - 0.5, y1=zi + 0.5,
                   line=dict(color=_CYAN, width=2), fillcolor="rgba(0,0,0,0)")

    fig4.update_layout(
        **_LAYOUT, height=500,
        xaxis=dict(title="Vol change", tickfont=dict(color="#94A3B8")),
        yaxis=dict(title="Spot change", tickfont=dict(color="#94A3B8")),
        title=dict(text=f"{metric_h} — Spot × Vol scenario matrix | {otype.upper()} K={K} T={T_days}d",
                   font=dict(color="#F1F5F9", size=13)),
    )
    st.plotly_chart(fig4, use_container_width=True)

    # Current stats strip
    sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
    sc1.metric("Price",  f"{price:.4f}")
    sc2.metric("Delta",  f"{delta:.4f}")
    sc3.metric("Gamma",  f"{gamma:.6f}")
    sc4.metric("Vega",   f"{vega:.4f}")
    sc5.metric("Theta",  f"{theta:.4f}")
    sc6.metric("Rho",    f"{rho:.4f}")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — P&L ATTRIBUTION
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown(
        "<p style='color:#94A3B8;font-size:13px'>"
        "Taylor decomposition: ΔP = Δ·ΔS + ½Γ·ΔS² + ν·Δσ + Θ·Δt + Vanna·ΔS·Δσ + ½Volga·Δσ² + residual"
        "</p>", unsafe_allow_html=True
    )

    ac1, ac2, ac3 = st.columns(3)
    S_prev    = ac1.number_input("Previous Spot",    value=S * 0.98, step=0.5, key="gl_Sprev")
    sig_prev  = ac2.number_input("Previous Vol %",   value=sig_pct - 1.0, step=0.5, key="gl_sigprev") / 100.0
    dt_days_a = ac3.number_input("Days elapsed",     value=1, min_value=1, step=1, key="gl_dt")

    sig_prev = max(sig_prev, 1e-6)
    T_prev   = T + dt_days_a / 365.0   # T at start was longer

    # Prices
    p0 = BSG.call_price(S_prev, K, T_prev, r, b, sig_prev) if otype == "call" else BSG.put_price(S_prev, K, T_prev, r, b, sig_prev)
    p1 = price

    dS      = S       - S_prev
    dsigma  = sigma   - sig_prev
    dt_yr   = dt_days_a / 365.0

    # Greeks at entry
    d0 = BSG.delta(S_prev, K, T_prev, r, b, sig_prev, option_type=otype)
    g0 = BSG.gamma(S_prev, K, T_prev, r, b, sig_prev)
    v0 = BSG.vega( S_prev, K, T_prev, r, b, sig_prev)
    t0 = BSG.theta(S_prev, K, T_prev, r, b, sig_prev, option_type=otype)
    va0= BSG.vanna(S_prev, K, T_prev, r, b, sig_prev)
    vg0= BSG.volga(S_prev, K, T_prev, r, b, sig_prev)

    delta_pnl = d0  * dS
    gamma_pnl = 0.5 * g0 * dS ** 2
    vega_pnl  = v0  * dsigma * 100.0
    theta_pnl = t0  * dt_days_a
    vanna_pnl = va0 * dS * dsigma * 100.0
    volga_pnl = 0.5 * vg0 * (dsigma * 100.0) ** 2
    total_taylor = delta_pnl + gamma_pnl + vega_pnl + theta_pnl + vanna_pnl + volga_pnl
    actual_pnl   = p1 - p0
    residual     = actual_pnl - total_taylor

    # ── Waterfall chart ──
    labels = ["Start", "Delta", "Gamma", "Vega", "Theta", "Vanna", "Volga", "Residual", "End"]
    values = [p0, delta_pnl, gamma_pnl, vega_pnl, theta_pnl, vanna_pnl, volga_pnl, residual, p1]
    measures = ["absolute"] + ["relative"] * 6 + ["relative", "total"]

    fig5 = go.Figure(go.Waterfall(
        name="P&L attribution",
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        connector=dict(line=dict(color="#334155", width=1)),
        increasing=dict(marker_color=_GREEN),
        decreasing=dict(marker_color=_RED),
        totals=dict(marker_color=_CYAN),
        text=[f"{v:+.4f}" for v in values],
        textposition="outside",
        textfont=dict(color="#94A3B8", size=10),
    ))
    fig5.update_layout(
        **_LAYOUT, height=440,
        yaxis=dict(title="Option price", gridcolor=_GRID, tickfont=dict(color="#94A3B8")),
        title=dict(text=f"P&L Attribution — ΔS={dS:+.2f} | Δσ={dsigma*100:+.2f}% | Δt={dt_days_a}d",
                   font=dict(color="#F1F5F9", size=13)),
    )
    st.plotly_chart(fig5, use_container_width=True)

    # ── Attribution table ──
    attr_df = pd.DataFrame({
        "Component":   ["Delta", "Gamma", "Vega", "Theta", "Vanna", "Volga", "Residual", "Total (Taylor)", "Actual P&L"],
        "P&L":         [delta_pnl, gamma_pnl, vega_pnl, theta_pnl, vanna_pnl, volga_pnl, residual, total_taylor, actual_pnl],
        "% of Actual": [
            f"{delta_pnl/actual_pnl*100:.1f}%" if actual_pnl else "—",
            f"{gamma_pnl/actual_pnl*100:.1f}%" if actual_pnl else "—",
            f"{vega_pnl/actual_pnl*100:.1f}%"  if actual_pnl else "—",
            f"{theta_pnl/actual_pnl*100:.1f}%" if actual_pnl else "—",
            f"{vanna_pnl/actual_pnl*100:.1f}%" if actual_pnl else "—",
            f"{volga_pnl/actual_pnl*100:.1f}%" if actual_pnl else "—",
            f"{residual/actual_pnl*100:.1f}%"  if actual_pnl else "—",
            f"{total_taylor/actual_pnl*100:.1f}%" if actual_pnl else "—",
            "100%",
        ],
        "Formula": [
            f"Δ·ΔS = {d0:.4f} × {dS:+.4f}",
            f"½Γ·ΔS² = 0.5 × {g0:.6f} × {dS**2:.4f}",
            f"ν·Δσ×100 = {v0:.4f} × {dsigma*100:+.4f}",
            f"Θ·Δt = {t0:.4f} × {dt_days_a}",
            f"Vanna·ΔS·Δσ×100 = {va0:.4f} × {dS:+.4f} × {dsigma*100:+.4f}",
            f"½Volga·(Δσ×100)² = 0.5 × {vg0:.4f} × {(dsigma*100)**2:.4f}",
            "Actual − Taylor",
            "Sum of components",
            f"P₁ − P₀ = {p1:.6f} − {p0:.6f}",
        ]
    })
    attr_df["P&L"] = attr_df["P&L"].apply(lambda x: f"{x:+.6f}")
    st.dataframe(attr_df, use_container_width=True, hide_index=True)

    # ── Input move summary ──
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Spot move ΔS",   f"{dS:+.4f}",         f"{dS/S_prev*100:+.2f}%")
    mc2.metric("Vol move Δσ",    f"{dsigma*100:+.2f}%")
    mc3.metric("Time elapsed",   f"{dt_days_a}d",       f"{dt_yr:.4f}y")
    mc4.metric("Actual P&L",     f"{actual_pnl:+.6f}",  f"{actual_pnl/p0*100:+.2f}%" if p0 > 0 else "—")
