"""
Ravinala — Position Book Manager Page
Multi-position Greeks aggregation, scenario matrix, hedging suggestions, position timeline.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timezone, timedelta
from position_book import (
    Position, new_position, position_greeks,
    book_greeks, book_summary_df, hedge_suggestions,
    scenario_book
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


# ── Session state helpers ─────────────────────────────────────────────────────
def _get_book() -> list:
    if "position_book" not in st.session_state:
        st.session_state["position_book"] = []
    return st.session_state["position_book"]


def _save_book(book: list) -> None:
    st.session_state["position_book"] = book


def _positions_from_state() -> list[Position]:
    return [Position.from_dict(d) for d in _get_book()]


def _positions_to_state(positions: list[Position]) -> None:
    _save_book([p.to_dict() for p in positions])


# ── Greek threshold colors ─────────────────────────────────────────────────────
def _greek_color(val: float, threshold: float) -> str:
    return _GREEN if abs(val) <= threshold else _RED


# ── Page ──────────────────────────────────────────────────────────────────────
st.title("Position Book Manager")
st.caption("Aggregate Greeks · Scenario P&L · Delta-Gamma-Vega hedging · Position timeline")

positions = _positions_from_state()

# ── Book-level Greeks strip ───────────────────────────────────────────────────
if positions:
    bg = book_greeks(positions)
    g_cols = st.columns(7)
    thresholds = {"delta": 50, "gamma": 0.5, "vega": 100, "theta": -50, "rho": 50, "vanna": 0.5, "volga": 10}
    labels = {"delta": "Δ Delta", "gamma": "Γ Gamma", "vega": "ν Vega",
               "theta": "Θ Theta", "rho": "ρ Rho", "vanna": "Vanna", "volga": "Volga"}
    for i, (gk, label) in enumerate(labels.items()):
        val = bg[gk]
        fmt = f"{val:.4f}"
        g_cols[i].metric(label, fmt)
    st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Book Manager",
    "Scenario Matrix",
    "Hedging",
    "Position Timeline",
    "Greeks Aggregation",
])

# ── TAB 1: Book Manager ───────────────────────────────────────────────────────
with tab1:
    st.markdown("### Add Position")
    with st.form("add_position_form", clear_on_submit=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        name      = fc1.text_input("Name", value="AAPL Dec Call")
        direction = fc2.selectbox("Direction", ["long", "short"])
        otype     = fc3.selectbox("Type", ["call", "put", "stock"])
        qty       = fc4.number_input("Quantity (contracts)", min_value=1, max_value=1000, value=1)

        fc5, fc6, fc7, fc8 = st.columns(4)
        strike       = fc5.number_input("Strike", min_value=0.01, value=100.0, step=1.0)
        expiry_days  = fc6.number_input("Expiry (days)", min_value=1, max_value=3650, value=30)
        spot         = fc7.number_input("Spot", min_value=0.01, value=100.0, step=1.0)
        vol_pct      = fc8.number_input("Vol %", min_value=0.1, max_value=500.0, value=25.0, step=0.5)

        fc9, fc10, fc11 = st.columns(3)
        rate_pct   = fc9.number_input("Rate %", min_value=0.0, max_value=30.0, value=5.0, step=0.1)
        div_pct    = fc10.number_input("Div Yield %", min_value=0.0, max_value=30.0, value=0.0, step=0.1)
        entry_price = fc11.number_input("Entry Price (0=BS)", min_value=0.0, value=0.0, step=0.01)

        submitted = st.form_submit_button("Add Position")

    if submitted:
        pos = new_position(
            name, direction, otype, int(qty), strike, int(expiry_days),
            spot, vol_pct / 100.0, rate_pct / 100.0, div_pct / 100.0,
            entry_price if entry_price > 0 else 0.0,
        )
        if pos.entry_price == 0.0:
            pos.entry_price = pos.current_price()
        positions.append(pos)
        _positions_to_state(positions)
        st.success(f"Added: {name}")
        st.rerun()

    # Positions table
    if positions:
        st.markdown("### Current Positions")
        df = book_summary_df(positions)
        if not df.empty:
            # Color P&L column
            def _color_pnl(val):
                try:
                    return f"color: {'#00FF9F' if float(val) >= 0 else '#FF4B4B'}"
                except Exception:
                    return ""
            styled = df.style.applymap(_color_pnl, subset=["P&L"])
            st.dataframe(styled, use_container_width=True, hide_index=True)

        # Remove / export
        col_rm, col_exp = st.columns([3, 1])
        with col_rm:
            if positions:
                pos_names = [f"{i+1}. {p.name} ({p.id})" for i, p in enumerate(positions)]
                to_remove = st.selectbox("Remove position", pos_names, key="pb_remove_sel")
                if st.button("Remove Selected"):
                    idx = int(to_remove.split(".")[0]) - 1
                    positions.pop(idx)
                    _positions_to_state(positions)
                    st.rerun()
        with col_exp:
            if not df.empty:
                csv = df.to_csv(index=False)
                st.download_button("Export CSV", csv, "position_book.csv", "text/csv")

        if st.button("Clear All Positions", type="secondary"):
            _positions_to_state([])
            st.rerun()
    else:
        st.info("No positions yet. Add your first position above.")

# ── TAB 2: Scenario Matrix ────────────────────────────────────────────────────
with tab2:
    if not positions:
        st.info("Add positions first.")
    else:
        sc1, sc2 = st.columns(2)
        spot_shock_pct = sc1.slider("Spot Shock Range ±%", 5, 50, 20)
        vol_shock_pct  = sc2.slider("Vol Shock Range ±%", 10, 80, 30)

        n_spot_pts = 9
        n_vol_pts  = 7
        spot_shocks = np.linspace(-spot_shock_pct/100, spot_shock_pct/100, n_spot_pts)
        vol_shocks  = np.linspace(-vol_shock_pct/100, vol_shock_pct/100, n_vol_pts)

        matrix_df = scenario_book(positions, spot_shocks.tolist(), vol_shocks.tolist())

        if not matrix_df.empty:
            z = matrix_df.values.astype(float)
            fig_sm = go.Figure(go.Heatmap(
                z=z,
                x=matrix_df.columns.tolist(),
                y=matrix_df.index.tolist(),
                colorscale="RdYlGn",
                zmid=0,
                text=[[f"${v:,.0f}" for v in row] for row in z],
                texttemplate="%{text}",
                textfont=dict(size=10),
                colorbar=dict(title="P&L ($)"),
            ))
            fig_sm.update_layout(
                **_LAYOUT,
                title="Book P&L — Spot × Vol Shock Scenario Matrix",
                xaxis_title="Spot Shock",
                yaxis_title="Vol Shock",
                height=420,
            )
            st.plotly_chart(fig_sm, use_container_width=True)

            with st.expander("Raw values"):
                st.dataframe(matrix_df, use_container_width=True)

# ── TAB 3: Hedging ────────────────────────────────────────────────────────────
with tab3:
    if not positions:
        st.info("Add positions first.")
    else:
        hc1, hc2, hc3 = st.columns(3)
        h_spot = hc1.number_input("Current Spot", value=positions[0].spot, step=1.0)
        h_vol  = hc2.number_input("Current Vol %", value=positions[0].vol * 100, step=0.5) / 100
        h_rate = hc3.number_input("Current Rate %", value=positions[0].rate * 100, step=0.1) / 100

        suggestions = hedge_suggestions(positions, h_spot, h_vol, h_rate)

        if suggestions:
            st.markdown("### Suggested Hedges")
            for sug in suggestions:
                col_s, col_btn = st.columns([4, 1])
                col_s.markdown(
                    f"**{sug['greek']} Hedge** — {sug['suggestion']}"
                )
                if col_btn.button(f"Add Hedge", key=f"add_hedge_{sug['greek']}"):
                    hedge_pos = new_position(
                        name=f"Hedge ({sug['greek']})",
                        direction=sug["direction"],
                        option_type=sug["option_type"],
                        quantity=int(sug["quantity"]),
                        strike=sug["strike"],
                        expiry_days=max(int(sug.get("expiry_days", 30)), 1),
                        spot=h_spot,
                        vol=h_vol,
                        rate=h_rate,
                    )
                    hedge_pos.entry_price = hedge_pos.current_price()
                    positions.append(hedge_pos)
                    _positions_to_state(positions)
                    st.success(f"Hedge added: {hedge_pos.name}")
                    st.rerun()

            # Show impact after hedges
            st.divider()
            st.markdown("### Book Greeks Before Hedging")
            bg_now = book_greeks(positions)
            g_cols_h = st.columns(5)
            for i, gk in enumerate(["delta", "gamma", "vega", "theta", "rho"]):
                g_cols_h[i].metric(gk.capitalize(), f"{bg_now[gk]:.4f}")
        else:
            st.success("Book is already well-hedged or no significant Greek exposure detected.")

# ── TAB 4: Position Timeline ──────────────────────────────────────────────────
with tab4:
    if not positions:
        st.info("Add positions first.")
    else:
        today = datetime.now(timezone.utc)
        fig_tl = go.Figure()

        for i, pos in enumerate(positions):
            expiry_date = today + timedelta(days=pos.expiry * 365)
            g = position_greeks(pos)
            pnl = pos.sign * pos.quantity * 100 * (pos.current_price() - pos.entry_price)
            color = _GREEN if pnl >= 0 else _RED

            fig_tl.add_trace(go.Bar(
                x=[pos.expiry * 365],
                y=[i],
                orientation="h",
                marker=dict(color=color, opacity=0.7),
                base=0,
                name=pos.name,
                text=f"{pos.name} | Δ={g['delta']:.3f} | P&L=${pnl:,.0f}",
                textposition="inside",
                hovertemplate=(
                    f"<b>{pos.name}</b><br>"
                    f"Type: {pos.direction} {pos.option_type}<br>"
                    f"Strike: {pos.strike:.2f}<br>"
                    f"Expiry: {int(pos.expiry*365)}d<br>"
                    f"Delta: {g['delta']:.4f}<br>"
                    f"P&L: ${pnl:,.2f}<extra></extra>"
                ),
                showlegend=False,
            ))

        fig_tl.update_layout(
            **_LAYOUT,
            title="Position Timeline — Days to Expiry",
            xaxis_title="Days to Expiry",
            yaxis=dict(
                tickvals=list(range(len(positions))),
                ticktext=[f"{p.name}" for p in positions],
                gridcolor=_GRID,
            ),
            xaxis=dict(gridcolor=_GRID),
            height=max(300, 80 + len(positions) * 50),
            barmode="overlay",
        )
        st.plotly_chart(fig_tl, use_container_width=True)

# ── TAB 5: Greeks Aggregation ─────────────────────────────────────────────────
with tab5:
    if not positions:
        st.info("Add positions first.")
    else:
        # Delta bar chart by position
        names_agg = [f"{p.name} ({p.direction[0].upper()})" for p in positions]
        deltas_agg = [position_greeks(p)["delta"] for p in positions]
        vegas_agg  = [abs(position_greeks(p)["vega"]) for p in positions]

        col_d, col_v = st.columns(2)

        with col_d:
            fig_delta = go.Figure(go.Bar(
                x=names_agg,
                y=deltas_agg,
                marker_color=[_GREEN if d >= 0 else _RED for d in deltas_agg],
                text=[f"{d:.3f}" for d in deltas_agg],
                textposition="outside",
            ))
            fig_delta.add_hline(y=0, line=dict(color="rgba(255,255,255,0.3)", width=1))
            fig_delta.update_layout(
                **_LAYOUT,
                title="Delta by Position",
                yaxis_title="Delta",
                yaxis=dict(gridcolor=_GRID),
                height=320,
            )
            st.plotly_chart(fig_delta, use_container_width=True)

        with col_v:
            fig_vega = go.Figure(go.Pie(
                labels=names_agg,
                values=vegas_agg,
                hole=0.4,
                marker=dict(colors=[_CYAN, _GOLD, _PURPLE, _GREEN, _ORANGE, _RED, "#FFFFFF"][:len(positions)]),
                textinfo="label+percent",
            ))
            fig_vega.update_layout(
                **_LAYOUT,
                title="|Vega| by Position",
                height=320,
            )
            st.plotly_chart(fig_vega, use_container_width=True)

        # Theta decay simulation
        st.markdown("### Theta Decay — Book P&L Over Time")
        days_sim = st.slider("Simulate (days)", 5, min(int(min(p.expiry * 365 for p in positions)), 120), 30)

        theta_rows = []
        for day in range(days_sim + 1):
            day_total = 0.0
            day_delta = day_delta_pnl = day_gamma_pnl = 0.0
            for pos in positions:
                T_rem = max(pos.expiry - day / 365.0, 1e-4)
                from engine import BlackScholesGreeks as BSG
                b = pos.rate - pos.div_yield
                ot = pos.option_type
                if ot == "stock":
                    continue
                scale = pos.sign * pos.quantity * 100
                if ot == "call":
                    curr_p = BSG.call_price(pos.spot, pos.strike, T_rem, pos.rate, b, pos.vol)
                else:
                    curr_p = BSG.put_price(pos.spot, pos.strike, T_rem, pos.rate, b, pos.vol)
                day_total += scale * (curr_p - pos.entry_price)
                day_delta += scale * BSG.theta(pos.spot, pos.strike, T_rem, pos.rate, b, pos.vol, ot)
            theta_rows.append({"Day": day, "Cumulative P&L (theta)": round(day_total, 2)})

        theta_df = pd.DataFrame(theta_rows)
        fig_theta = go.Figure(go.Scatter(
            x=theta_df["Day"],
            y=theta_df["Cumulative P&L (theta)"],
            mode="lines+markers",
            line=dict(color=_CYAN, width=2),
            marker=dict(size=4),
            name="Theta P&L",
            fill="tozeroy",
            fillcolor="rgba(0,217,255,0.08)",
        ))
        fig_theta.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"))
        fig_theta.update_layout(
            **_LAYOUT,
            title="Book P&L from Theta Decay (spot unchanged)",
            xaxis_title="Days Forward",
            yaxis_title="Cumulative P&L ($)",
            xaxis=dict(gridcolor=_GRID),
            yaxis=dict(gridcolor=_GRID),
            height=340,
        )
        st.plotly_chart(fig_theta, use_container_width=True)
