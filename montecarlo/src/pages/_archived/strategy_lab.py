"""
Ravinala — Option Strategy Lab Page
Multi-leg options strategy builder with payoff diagrams, Greeks dashboard, and comparison mode.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from strategy_lab import (
    Leg, fill_premiums, leg_greeks, net_greeks,
    payoff_at_expiry, payoff_today, breakevens,
    max_profit_loss, recognize_strategy
)

# ── Theme ────────────────────────────────────────────────────────────────────
_BG = "#0A0E1A"
_GRID = "rgba(255,255,255,0.05)"
_CYAN = "#00D9FF"
_GREEN = "#00FF9F"
_RED = "#FF4B4B"
_GOLD = "#FFD700"
_PURPLE = "#B44FFF"

_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=_BG,
    plot_bgcolor=_BG,
    font=dict(family="Inter, sans-serif", size=12, color="#E8ECF3"),
    margin=dict(l=60, r=20, t=40, b=50),
)


def _make_spots(legs: list, n: int = 300) -> np.ndarray:
    if not legs:
        return np.linspace(50, 200, n)
    ref = legs[0].spot
    lo = min(l.strike for l in legs) * 0.55
    hi = max(l.strike for l in legs) * 1.45
    lo = min(lo, ref * 0.60)
    hi = max(hi, ref * 1.40)
    return np.linspace(lo, hi, n)


def _render_leg_table(legs: list) -> None:
    if not legs:
        return
    fill_premiums(legs)
    rows = []
    for i, leg in enumerate(legs):
        g = leg_greeks(leg)
        rows.append({
            "#": i + 1,
            "Dir": leg.direction.upper(),
            "Type": leg.option_type.capitalize(),
            "Qty": leg.quantity,
            "Strike": f"{leg.strike:.2f}",
            "Expiry (d)": int(leg.expiry * 365),
            "Vol %": f"{leg.vol*100:.1f}%",
            "Premium": f"{leg.premium:.4f}",
            "Delta": f"{g['delta']:.3f}",
            "Gamma": f"{g['gamma']:.5f}",
            "Vega": f"{g['vega']:.3f}",
            "Theta": f"{g['theta']:.4f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _payoff_chart(legs: list, label: str = "") -> go.Figure:
    spots = _make_spots(legs)
    pnl_expiry = payoff_at_expiry(legs, spots)
    pnl_today = payoff_today(legs, spots, legs[0].expiry if legs else 0.25)
    be = breakevens(legs)
    mp, ml = max_profit_loss(legs, spots)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=spots, y=pnl_expiry,
        mode="lines", name="At Expiry",
        line=dict(color=_CYAN, width=2.5),
    ))
    fig.add_trace(go.Scatter(
        x=spots, y=pnl_today,
        mode="lines", name="Today",
        line=dict(color=_GOLD, width=1.8, dash="dash"),
    ))
    # Zero line
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.25)", width=1, dash="dot"))
    # Current spot
    if legs:
        fig.add_vline(
            x=legs[0].spot,
            line=dict(color=_PURPLE, width=1.2, dash="dot"),
            annotation_text="Spot",
            annotation_position="top",
        )
    # Breakevens
    for be_val in be:
        fig.add_vline(
            x=be_val,
            line=dict(color=_GREEN, width=1, dash="dashdot"),
            annotation_text=f"BE {be_val:.2f}",
            annotation_position="bottom right",
            annotation_font_size=10,
        )
    # Fill positive / negative
    fig.add_trace(go.Scatter(
        x=spots, y=np.maximum(pnl_expiry, 0),
        fill="tozeroy", fillcolor="rgba(0,255,159,0.07)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=spots, y=np.minimum(pnl_expiry, 0),
        fill="tozeroy", fillcolor="rgba(255,75,75,0.07)",
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))

    fig.update_layout(
        **_LAYOUT,
        title=f"Payoff Diagram{' — ' + label if label else ''}",
        xaxis_title="Spot Price",
        yaxis_title="P&L ($)",
        xaxis=dict(gridcolor=_GRID),
        yaxis=dict(gridcolor=_GRID),
        legend=dict(orientation="h", y=1.06),
        height=420,
    )

    # Annotations for max profit / max loss
    if mp != float("inf") and mp > 0:
        fig.add_annotation(
            text=f"Max Profit: ${mp:,.0f}",
            xref="paper", yref="paper", x=0.01, y=0.97,
            showarrow=False, font=dict(color=_GREEN, size=12),
        )
    if ml != float("-inf") and ml < 0:
        fig.add_annotation(
            text=f"Max Loss: ${ml:,.0f}",
            xref="paper", yref="paper", x=0.01, y=0.90,
            showarrow=False, font=dict(color=_RED, size=12),
        )

    return fig


def _greeks_chart(legs: list) -> go.Figure:
    """Delta contribution bar chart by leg."""
    if not legs:
        return go.Figure()
    fill_premiums(legs)
    names = [f"Leg {i+1} ({l.direction[0].upper()}{l.option_type[0].upper()} K={l.strike:.0f})" for i, l in enumerate(legs)]
    deltas = [leg_greeks(l)["delta"] for l in legs]
    colors = [_GREEN if d >= 0 else _RED for d in deltas]

    fig = go.Figure(go.Bar(
        x=names, y=deltas,
        marker_color=colors,
        text=[f"{d:.3f}" for d in deltas],
        textposition="outside",
    ))
    fig.update_layout(
        **_LAYOUT,
        title="Delta by Leg",
        xaxis_title="",
        yaxis_title="Delta",
        yaxis=dict(gridcolor=_GRID, zeroline=True, zerolinecolor="rgba(255,255,255,0.3)"),
        height=320,
    )
    return fig


def _scenario_chart(legs: list, days_forward: int) -> go.Figure:
    """Payoff at different time points."""
    spots = _make_spots(legs)
    if not legs:
        return go.Figure()
    T_max = legs[0].expiry
    times = [T_max, T_max * 0.75, T_max * 0.5, T_max * 0.25, 1.0 / 252.0]
    labels = ["At entry", "75% time", "50% time", "25% time", "At expiry"]
    palette = [_CYAN, _GOLD, _PURPLE, "#FF8C42", _GREEN]

    fig = go.Figure()
    for T_rem, label, color in zip(times, labels, palette):
        if T_rem == 1.0 / 252.0:
            pnl = payoff_at_expiry(legs, spots)
        else:
            pnl = payoff_today(legs, spots, T_rem)
        fig.add_trace(go.Scatter(x=spots, y=pnl, mode="lines", name=label,
                                  line=dict(color=color, width=1.8)))

    # Highlight selected scenario
    T_sel = max(T_max - days_forward / 365.0, 1e-4)
    pnl_sel = payoff_today(legs, spots, T_sel)
    fig.add_trace(go.Scatter(
        x=spots, y=pnl_sel, mode="lines", name=f"Day +{days_forward}",
        line=dict(color="#FFFFFF", width=2.5, dash="solid"),
    ))
    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"))
    if legs:
        fig.add_vline(x=legs[0].spot, line=dict(color=_PURPLE, width=1, dash="dot"))

    fig.update_layout(
        **_LAYOUT,
        title="Payoff Evolution Over Time",
        xaxis_title="Spot Price",
        yaxis_title="P&L ($)",
        xaxis=dict(gridcolor=_GRID),
        yaxis=dict(gridcolor=_GRID),
        legend=dict(orientation="h", y=1.06),
        height=420,
    )
    return fig


def _init_legs_state(key: str) -> None:
    if key not in st.session_state:
        st.session_state[key] = []


def _add_leg_form(key: str, spot_default: float, rate_default: float,
                   vol_default: float, div_default: float) -> None:
    """Form to add a new leg."""
    with st.expander("+ Add Leg", expanded=len(st.session_state[key]) == 0):
        c1, c2, c3, c4 = st.columns(4)
        direction = c1.selectbox("Direction", ["long", "short"], key=f"{key}_dir")
        otype = c2.selectbox("Type", ["call", "put", "stock"], key=f"{key}_type")
        qty = c3.number_input("Quantity (contracts)", min_value=1, max_value=100, value=1, key=f"{key}_qty")
        strike = c4.number_input("Strike", min_value=0.01, value=float(spot_default), step=1.0, key=f"{key}_K")

        c5, c6, c7, c8 = st.columns(4)
        expiry_days = c5.number_input("Expiry (days)", min_value=1, max_value=3650, value=30, key=f"{key}_exp")
        vol_override = c6.number_input("Vol % (override)", min_value=0.1, max_value=500.0,
                                        value=vol_default * 100, step=0.5, key=f"{key}_vol")
        premium_override = c7.number_input("Premium (0=BS)", min_value=0.0, value=0.0,
                                            step=0.01, key=f"{key}_prem")
        _ = c8  # spacer

        if st.button("Add Leg", key=f"{key}_add_btn"):
            leg = Leg(
                direction=direction,
                option_type=otype,
                quantity=qty,
                strike=strike,
                expiry=expiry_days / 365.0,
                spot=spot_default,
                vol=vol_override / 100.0,
                rate=rate_default,
                div_yield=div_default,
                premium=premium_override if premium_override > 0 else None,
            )
            st.session_state[key].append(leg)
            st.rerun()


def _render_strategy_block(key: str, spot: float, rate: float, vol: float, div: float) -> None:
    """Render full strategy builder for a given session key."""
    _init_legs_state(key)

    # Update spot/rate/div on existing legs when globals change
    for leg in st.session_state[key]:
        leg.spot = spot
        leg.rate = rate
        leg.div_yield = div

    legs = st.session_state[key]

    # Strategy name
    name = recognize_strategy(legs)
    if legs:
        fill_premiums(legs)
        st.info(f"**Strategy recognised:** {name} | {len(legs)} leg(s)")

    # Leg table
    _render_leg_table(legs)

    # Remove leg
    if legs:
        col_del, col_clr = st.columns([3, 1])
        idx_del = col_del.number_input("Remove leg #", min_value=1, max_value=len(legs),
                                        value=1, step=1, key=f"{key}_del_idx")
        if col_del.button("Remove", key=f"{key}_del_btn"):
            st.session_state[key].pop(idx_del - 1)
            st.rerun()
        if col_clr.button("Clear All", key=f"{key}_clr_btn"):
            st.session_state[key] = []
            st.rerun()

    _add_leg_form(key, spot, rate, vol, div)


# ── MAIN PAGE ─────────────────────────────────────────────────────────────────

st.title("Option Strategy Lab")
st.caption("Multi-leg options strategy builder — up to 8 legs per strategy")

# ── Global controls ────────────────────────────────────────────────────────────
st.markdown("### Global Parameters")
gc1, gc2, gc3, gc4 = st.columns(4)
spot_g = gc1.number_input("Spot Price", min_value=0.01, value=100.0, step=1.0, key="slab_spot")
rate_g = gc2.number_input("Risk-free Rate %", min_value=0.0, max_value=30.0, value=5.0, step=0.1, key="slab_rate") / 100.0
vol_g = gc3.number_input("Implied Vol %", min_value=0.1, max_value=500.0, value=25.0, step=0.5, key="slab_vol") / 100.0
div_g = gc4.number_input("Div Yield %", min_value=0.0, max_value=30.0, value=0.0, step=0.1, key="slab_div") / 100.0

st.divider()

# ── Mode selector ──────────────────────────────────────────────────────────────
mode = st.radio("Mode", ["Single Strategy", "Compare A vs B"], horizontal=True, key="slab_mode")

if mode == "Single Strategy":
    _render_strategy_block("slab_legs", spot_g, rate_g, vol_g, div_g)
    legs = st.session_state.get("slab_legs", [])

    if not legs:
        st.info("Add at least one leg to see the payoff diagram.")
    else:
        tab1, tab2, tab3 = st.tabs(["Payoff Diagram", "Greeks Dashboard", "Scenario"])

        with tab1:
            st.plotly_chart(_payoff_chart(legs), use_container_width=True)

            be = breakevens(legs)
            mp, ml = max_profit_loss(legs, _make_spots(legs))
            m1, m2, m3 = st.columns(3)
            m1.metric("Breakeven(s)", ", ".join(f"{b:.2f}" for b in be) if be else "None")
            m2.metric("Max Profit", f"${mp:,.2f}" if mp < 1e8 else "Unlimited")
            m3.metric("Max Loss", f"${ml:,.2f}" if ml > -1e8 else "Unlimited")

        with tab2:
            fill_premiums(legs)
            ng = net_greeks(legs)

            # Net Greeks metric strip
            cols_g = st.columns(6)
            cols_g[0].metric("Net Δ Delta", f"{ng['delta']:.4f}")
            cols_g[1].metric("Net Γ Gamma", f"{ng['gamma']:.6f}")
            cols_g[2].metric("Net ν Vega", f"{ng['vega']:.4f}")
            cols_g[3].metric("Net Θ Theta", f"{ng['theta']:.4f}")
            cols_g[4].metric("Net ρ Rho", f"{ng['rho']:.4f}")
            cols_g[5].metric("Vanna", f"{ng['vanna']:.5f}")

            st.plotly_chart(_greeks_chart(legs), use_container_width=True)

            # Full Greeks table
            rows = []
            for i, leg in enumerate(legs):
                g = leg_greeks(leg)
                rows.append({"Leg": f"#{i+1} {leg.direction.upper()} {leg.option_type.capitalize()} K={leg.strike:.2f}",
                              **{k: round(v, 6) for k, v in g.items() if k != "price"}})
            rows.append({"Leg": "NET", **{k: round(v, 6) for k, v in ng.items()}})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        with tab3:
            days_fwd = st.slider(
                "Days Forward", min_value=1,
                max_value=max(int(legs[0].expiry * 365), 2),
                value=max(int(legs[0].expiry * 365 // 2), 1),
                key="slab_days_fwd",
            )
            st.plotly_chart(_scenario_chart(legs, days_fwd), use_container_width=True)

else:
    # ── Compare A vs B ──────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Strategy A")
        _render_strategy_block("slab_legs_a", spot_g, rate_g, vol_g, div_g)
    with col_b:
        st.subheader("Strategy B")
        _render_strategy_block("slab_legs_b", spot_g, rate_g, vol_g, div_g)

    legs_a = st.session_state.get("slab_legs_a", [])
    legs_b = st.session_state.get("slab_legs_b", [])

    if legs_a or legs_b:
        all_legs = legs_a + legs_b
        spots = _make_spots(all_legs if all_legs else [])

        fig = go.Figure()
        if legs_a:
            fill_premiums(legs_a)
            pnl_a = payoff_at_expiry(legs_a, spots)
            fig.add_trace(go.Scatter(x=spots, y=pnl_a, mode="lines", name=f"A — {recognize_strategy(legs_a)}",
                                      line=dict(color=_CYAN, width=2.5)))
        if legs_b:
            fill_premiums(legs_b)
            pnl_b = payoff_at_expiry(legs_b, spots)
            fig.add_trace(go.Scatter(x=spots, y=pnl_b, mode="lines", name=f"B — {recognize_strategy(legs_b)}",
                                      line=dict(color=_GOLD, width=2.5, dash="dash")))
        fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"))
        fig.add_vline(x=spot_g, line=dict(color=_PURPLE, width=1, dash="dot"),
                      annotation_text="Spot", annotation_position="top")
        fig.update_layout(
            **_LAYOUT,
            title="Strategy Comparison — At Expiry",
            xaxis_title="Spot Price",
            yaxis_title="P&L ($)",
            xaxis=dict(gridcolor=_GRID),
            yaxis=dict(gridcolor=_GRID),
            legend=dict(orientation="h", y=1.06),
            height=460,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Side-by-side Greeks
        ca, cb = st.columns(2)
        if legs_a:
            ng_a = net_greeks(legs_a)
            ca.markdown("**Strategy A — Net Greeks**")
            ca.dataframe(pd.DataFrame([{"Greek": k, "Value": round(v, 6)} for k, v in ng_a.items()]),
                         use_container_width=True, hide_index=True)
        if legs_b:
            ng_b = net_greeks(legs_b)
            cb.markdown("**Strategy B — Net Greeks**")
            cb.dataframe(pd.DataFrame([{"Greek": k, "Value": round(v, 6)} for k, v in ng_b.items()]),
                         use_container_width=True, hide_index=True)
