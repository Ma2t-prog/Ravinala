"""
Ravinala — Scenario Matrix & Greeks Surface Page
2D heatmaps, 3D Greek surfaces, and term structure analysis.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scenario_matrix import (
    build_scenario_matrix, greeks_vs_spot,
    greeks_surface_3d, vol_surface_3d, term_structure
)

# ── Theme ─────────────────────────────────────────────────────────────────────
_BG = "#0A0E1A"
_GRID = "rgba(255,255,255,0.05)"
_CYAN = "#00D9FF"
_PURPLE = "#B44FFF"

_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    font=dict(family="Inter, sans-serif", size=12, color="#E8ECF3"),
    margin=dict(l=60, r=20, t=50, b=50),
)

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("Scenario Matrix & Greeks Surface")
st.caption("2D P&L heatmaps · 3D Greek surfaces · Vol×Spot grids · Term structure")

# ── Controls ──────────────────────────────────────────────────────────────────
with st.expander("Position Parameters", expanded=True):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    S      = c1.number_input("Spot (S)", min_value=0.01, value=100.0, step=1.0)
    K      = c2.number_input("Strike (K)", min_value=0.01, value=100.0, step=1.0)
    T_days = c3.number_input("Expiry (days)", min_value=1, max_value=3650, value=30)
    r_pct  = c4.number_input("Rate %", min_value=0.0, max_value=30.0, value=5.0, step=0.1)
    sig_pct= c5.number_input("Vol %", min_value=0.1, max_value=500.0, value=25.0, step=0.5)
    div_pct= c6.number_input("Div Yield %", min_value=0.0, max_value=30.0, value=0.0, step=0.1)
    otype  = st.radio("Option Type", ["call", "put"], horizontal=True)

T      = T_days / 365.0
r      = r_pct / 100.0
sigma  = sig_pct / 100.0
div    = div_pct / 100.0

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "2D Heatmap",
    "3D Greeks Surface",
    "Vol × Spot Surface",
    "Greeks vs Spot",
    "Term Structure",
])

# ── TAB 1: 2D Heatmap ────────────────────────────────────────────────────────
with tab1:
    col_m, col_sr, col_vr, col_ns, col_nv = st.columns(5)
    metric   = col_m.selectbox("Metric", ["price","delta","gamma","vega","theta","rho","vanna","volga"])
    sp_range = col_sr.slider("Spot Range ±%", 5, 50, 30)
    vl_range = col_vr.slider("Vol Range ±%", 10, 80, 40)
    n_sp     = col_ns.slider("# Spot pts", 8, 25, 12)
    n_vl     = col_nv.slider("# Vol pts", 8, 25, 12)

    matrix_df, spots_arr, vols_arr = build_scenario_matrix(
        S, K, T, r, sigma, otype, div,
        spot_range_pct=sp_range/100, vol_range_pct=vl_range/100,
        n_spots=n_sp, n_vols=n_vl, metric=metric
    )

    z = matrix_df.values.astype(float)
    fig_hm = go.Figure(go.Heatmap(
        z=z,
        x=matrix_df.columns.tolist(),
        y=matrix_df.index.tolist(),
        colorscale="RdYlGn",
        zmid=0 if metric not in ["price","gamma","vega"] else None,
        text=[[f"{v:.4f}" for v in row] for row in z],
        texttemplate="%{text}",
        textfont=dict(size=9),
        colorbar=dict(title=metric.capitalize()),
    ))
    # Mark current spot/vol
    spot_label = f"{S:.2f}"
    vol_label  = f"{sigma*100:.1f}%"
    if spot_label in matrix_df.columns:
        fig_hm.add_vline(x=matrix_df.columns.tolist().index(spot_label),
                          line=dict(color=_CYAN, width=2, dash="dash"))
    if vol_label in matrix_df.index:
        fig_hm.add_hline(y=matrix_df.index.tolist().index(vol_label),
                          line=dict(color=_PURPLE, width=2, dash="dash"))

    fig_hm.update_layout(
        **_LAYOUT,
        title=f"{metric.capitalize()} — Spot × Vol Scenario Matrix",
        xaxis_title="Spot Price",
        yaxis_title="Implied Vol",
        height=500,
    )
    st.plotly_chart(fig_hm, use_container_width=True)

    with st.expander("Raw matrix table"):
        st.dataframe(matrix_df.style.background_gradient(cmap="RdYlGn", axis=None), use_container_width=True)

# ── TAB 2: 3D Greeks Surface ─────────────────────────────────────────────────
with tab2:
    c_g, c_sr2, c_t = st.columns(3)
    greek3d = c_g.selectbox("Greek", ["delta","gamma","vega","theta","rho","price","vanna","volga"], key="g3d")
    sp_r2   = c_sr2.slider("Spot Range ±%", 5, 50, 25, key="sr3d")
    t_max   = c_t.slider("Max Expiry (years)", 0.1, 3.0, 1.0, step=0.1)

    spots3d, times3d, surf3d = greeks_surface_3d(
        S, K, r, sigma, otype, div, greek3d,
        spot_range_pct=sp_r2/100, n_spots=35, n_times=25, T_max=t_max
    )

    # Camera control
    cx, cy = st.columns(2)
    el = cx.slider("Elevation", 5, 60, 25)
    az = cy.slider("Azimuth", 0, 360, 220)

    fig_3d = go.Figure(go.Surface(
        x=spots3d,
        y=times3d,
        z=surf3d.T,
        colorscale="Plasma",
        colorbar=dict(title=greek3d.capitalize()),
        contours=dict(
            z=dict(show=True, usecolormap=True, highlightcolor="#00D9FF", project_z=True)
        ),
    ))
    eye_r = 2.0
    eye_az = np.radians(az)
    eye_el = np.radians(el)
    fig_3d.update_layout(
        **_LAYOUT,
        title=f"{greek3d.capitalize()} Surface — Spot × Time to Expiry",
        scene=dict(
            xaxis=dict(title="Spot", backgroundcolor=_BG, gridcolor=_GRID),
            yaxis=dict(title="Time (yrs)", backgroundcolor=_BG, gridcolor=_GRID),
            zaxis=dict(title=greek3d.capitalize(), backgroundcolor=_BG, gridcolor=_GRID),
            bgcolor=_BG,
            camera=dict(eye=dict(
                x=eye_r * np.cos(eye_el) * np.cos(eye_az),
                y=eye_r * np.cos(eye_el) * np.sin(eye_az),
                z=eye_r * np.sin(eye_el),
            )),
        ),
        height=560,
    )
    st.plotly_chart(fig_3d, use_container_width=True)

# ── TAB 3: Vol × Spot Surface ─────────────────────────────────────────────────
with tab3:
    c_gv, c_srv, c_vrv = st.columns(3)
    greek_vs = c_gv.selectbox("Metric", ["price","delta","gamma","vega","theta","rho"], key="gvs")
    sp_rv    = c_srv.slider("Spot Range ±%", 5, 50, 25, key="sprvs")
    vl_rv    = c_vrv.slider("Vol Range ±%", 10, 80, 40, key="vlrvs")

    spots_vs, vols_vs, surf_vs = vol_surface_3d(
        S, K, r, otype, div, greek_vs,
        spot_range_pct=sp_rv/100, vol_range_pct=vl_rv/100,
        sigma_center=sigma, n_spots=30, n_vols=25, T=T
    )

    fig_vs = go.Figure(go.Surface(
        x=spots_vs, y=vols_vs, z=surf_vs.T,
        colorscale="Viridis",
        colorbar=dict(title=greek_vs.capitalize()),
    ))
    fig_vs.update_layout(
        **_LAYOUT,
        title=f"{greek_vs.capitalize()} — Spot × Vol",
        scene=dict(
            xaxis=dict(title="Spot", backgroundcolor=_BG, gridcolor=_GRID),
            yaxis=dict(title="Vol", backgroundcolor=_BG, gridcolor=_GRID),
            zaxis=dict(title=greek_vs.capitalize(), backgroundcolor=_BG, gridcolor=_GRID),
            bgcolor=_BG,
        ),
        height=520,
    )
    st.plotly_chart(fig_vs, use_container_width=True)

# ── TAB 4: Greeks vs Spot ──────────────────────────────────────────────────────
with tab4:
    gvs_df = greeks_vs_spot(S, K, T, r, sigma, otype, div, n_spots=150)

    fig_gvs = make_subplots(specs=[[{"secondary_y": True}]])
    colors_map = {"delta": _CYAN, "gamma": "#FFD700", "vega": "#FF8C42",
                  "theta": _PURPLE, "rho": "#00FF9F"}

    for greek_name, color in colors_map.items():
        fig_gvs.add_trace(
            go.Scatter(x=gvs_df["spot"], y=gvs_df[greek_name],
                       name=greek_name.capitalize(), line=dict(color=color, width=1.8)),
            secondary_y=False,
        )

    fig_gvs.add_trace(
        go.Scatter(x=gvs_df["spot"], y=gvs_df["price"],
                   name="Price", line=dict(color="#FFFFFF", width=2, dash="dash")),
        secondary_y=True,
    )
    fig_gvs.add_vline(x=S, line=dict(color=_PURPLE, width=1.5, dash="dot"),
                      annotation_text="Spot", annotation_position="top")
    fig_gvs.add_vline(x=K, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"),
                      annotation_text="K", annotation_position="bottom")

    fig_gvs.update_layout(
        **_LAYOUT,
        title="All Greeks vs Spot Price",
        xaxis_title="Spot",
        height=460,
        legend=dict(orientation="h", y=1.08),
    )
    fig_gvs.update_yaxes(title_text="Greek Value", secondary_y=False, gridcolor=_GRID)
    fig_gvs.update_yaxes(title_text="Option Price", secondary_y=True, gridcolor=_GRID)
    st.plotly_chart(fig_gvs, use_container_width=True)

# ── TAB 5: Term Structure ─────────────────────────────────────────────────────
with tab5:
    c_gt, = st.columns(1)
    greek_ts = st.selectbox("Greek", ["delta","gamma","vega","theta","rho","price"], key="gts")

    ts_df = term_structure(S, K, r, sigma, otype, div, greek_ts)
    expiry_cols = [c for c in ts_df.columns if c != "spot"]

    palette_ts = ["#00D9FF","#FFD700","#FF8C42","#B44FFF","#00FF9F","#FF4B4B","#FFFFFF"]
    fig_ts = go.Figure()
    for i, col in enumerate(expiry_cols):
        fig_ts.add_trace(go.Scatter(
            x=ts_df["spot"], y=ts_df[col],
            mode="lines", name=col,
            line=dict(color=palette_ts[i % len(palette_ts)], width=1.8),
        ))
    fig_ts.add_vline(x=S, line=dict(color=_PURPLE, width=1.5, dash="dot"),
                     annotation_text="Spot", annotation_position="top")
    fig_ts.add_vline(x=K, line=dict(color="rgba(255,255,255,0.3)", width=1, dash="dot"),
                     annotation_text="K", annotation_position="bottom")
    fig_ts.update_layout(
        **_LAYOUT,
        title=f"{greek_ts.capitalize()} Term Structure vs Spot",
        xaxis_title="Spot",
        yaxis_title=greek_ts.capitalize(),
        xaxis=dict(gridcolor=_GRID),
        yaxis=dict(gridcolor=_GRID),
        legend=dict(orientation="h", y=1.08),
        height=460,
    )
    st.plotly_chart(fig_ts, use_container_width=True)
