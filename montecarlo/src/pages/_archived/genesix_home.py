"""
Ω OMEGA - Advanced AI Portfolio Allocator
World-Class Investment Dashboard
Better than Wealthfront, Betterment, and Personal Capital combined.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from genesix.omega_database import AssetDatabase, BrokerDatabase
from genesix.risk_matrix import RISK_MATRIX, CATEGORIES, CATEGORY_COLORS, get_level


# ============================================================================
# PORTFOLIO OPTIMIZATION (SCIPY)
# ============================================================================

@st.cache_data(ttl=3600)
def optimize_portfolio(tickers: tuple, risk_profile: str):
    """Scipy-based mean-variance optimization for a given risk profile."""
    try:
        from scipy.optimize import minimize
        import yfinance as yf

        tickers_list = list(tickers)
        data = yf.download(tickers_list, period='2y', progress=False)['Close']
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        # Drop any tickers with insufficient data
        data = data.dropna(axis=1, thresh=int(len(data) * 0.9))
        valid_tickers = data.columns.tolist()
        returns = data.pct_change().dropna()

        mu = returns.mean() * 252
        cov = returns.cov() * 252
        n = len(valid_tickers)

        if n < 2:
            return None, None

        # risk_profile is now an int 1-20
        rl = get_level(int(risk_profile))
        target = rl.target_return_pa / 100.0

        def portfolio_vol(w):
            return float(np.sqrt(w @ cov.values @ w))

        constraints = [
            {'type': 'eq', 'fun': lambda w: float(np.sum(w)) - 1.0},
            {'type': 'ineq', 'fun': lambda w: float(w @ mu.values) - target},
        ]
        bounds = [(0.02, 0.40)] * n
        w0 = np.ones(n) / n
        result = minimize(
            portfolio_vol, w0, method='SLSQP',
            bounds=bounds, constraints=constraints,
            options={'ftol': 1e-9, 'maxiter': 1000}
        )
        if result.success:
            weights = result.x
            opt_weights = {t: float(w * 100) for t, w in zip(valid_tickers, weights)}
            opt_return = float(weights @ mu.values * 100)
            opt_vol = float(np.sqrt(weights @ cov.values @ weights) * 100)
            return opt_weights, {'return': opt_return, 'vol': opt_vol, 'sharpe': opt_return / max(opt_vol, 0.1)}
        return None, None
    except Exception as e:
        return None, None


st.set_page_config(
    page_title="Omega - GenesiX AI Allocator",
    page_icon="Ω",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .allocation-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# HEADER
# ============================================================================

col1, col2 = st.columns([3, 1])
with col1:
    st.title("Ω Omega")
    st.write("_GenesiX Intelligent Asset Allocator_")
with col2:
    st.image("https://via.placeholder.com/100", width=100)

st.divider()

# ============================================================================
# PORTFOLIO MODE SELECTOR
# ============================================================================

st.markdown("### Portfolio Builder Mode")

portfolio_mode = st.radio(
    "Choose your portfolio construction approach",
    options=["Classic Risk Matrix Mode", "Advanced Dynamic Universe Mode"],
    horizontal=True,
    help="Risk Matrix: Automatic allocations per risk level | Dynamic Universe: Select specific instruments"
)

st.divider()

# ============================================================================
# ADVANCED MODE: DYNAMIC UNIVERSE BUILDER
# ============================================================================

if portfolio_mode == "Advanced Dynamic Universe Mode":
    st.markdown("### 🚀 Advanced Portfolio Builder — Dynamic Universe")
    
    from genesix.portfolio_allocation_ui import run_portfolio_builder_workflow
    run_portfolio_builder_workflow()
    
    st.stop()

# ============================================================================
# CLASSIC MODE: RISK MATRIX
# ============================================================================

# (Rest of existing code below)

st.header(" Build Your Optimal Portfolio")

with st.container(border=True):
    form_col1, form_col2 = st.columns(2)
    
    # LEFT: Input Parameters
    with form_col1:
        st.subheader("Your Investment Profile")
        
        # Investment amount
        col_amt1, col_amt2 = st.columns(2)
        with col_amt1:
            amount = st.number_input(
                " Investment Amount",
                min_value=1000,
                max_value=10000000,
                value=100000,
                step=10000,
                help="Enter amount to invest"
            )
        
        with col_amt2:
            currency = st.selectbox(
                " Currency",
                ["USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD"],
                index=0
            )
        
        st.write(f"**Total Investment: {amount:,.0f} {currency}**")
        
        st.divider()
        
        # ── INSTITUTIONAL RISK SCALE ──────────────────────────────────────────
        st.subheader("Risk Level  (1 — 20)")

        risk_level = st.slider(
            "Select your institutional risk score",
            min_value=1, max_value=20, value=7, step=1,
            help=(
                "1–3 Capital Preservation  |  4–6 Conservative  |  7–9 Balanced  "
                "|  10–12 Growth  |  13–15 Aggressive Growth  |  16–17 High Risk  "
                "|  18 Speculative  |  19–20 Maximum Risk"
            )
        )
        risk_profile = risk_level   # int 1-20 from here on
        rl = get_level(risk_level)

        # colour band pill
        cat_color = CATEGORY_COLORS.get(rl.category, "#888")
        st.markdown(
            f'<span style="background:{cat_color};color:white;padding:3px 12px;'
            f'border-radius:12px;font-weight:600;font-size:0.85rem">'
            f'Level {rl.level} — {rl.label} &nbsp;|&nbsp; {rl.category}</span>',
            unsafe_allow_html=True,
        )
        st.write("")

        # Parameter grid
        p1, p2, p3 = st.columns(3)
        p1.metric("Vol Budget (σ p.a.)",   f"{rl.vol_budget_pa:.1f}%")
        p2.metric("Max Drawdown",           f"{rl.max_drawdown_pct:.0f}%")
        p3.metric("VaR 95% (1-day)",        f"{rl.var_95_1d:.2f}% NAV")

        p4, p5, p6 = st.columns(3)
        p4.metric("VaR 99% (1-day)",        f"{rl.var_99_1d:.2f}% NAV")
        p5.metric("Beta Cap (vs S&P 500)",  f"{rl.beta_cap:.2f}x" if rl.beta_cap != float('inf') else "Uncapped")
        p6.metric("Max Leverage",           f"{rl.max_leverage:.1f}x")

        with st.expander("Allocation constraints & instrument universe", expanded=False):
            st.markdown(f"**Typical mandate:** _{rl.typical_mandate}_")
            st.markdown("**Allowed instrument universe:**")
            st.markdown("  " + "  ·  ".join(rl.universe))
            st.markdown("**Asset class constraints:**")
            cdf = pd.DataFrame(
                [{"Asset Class": k, "Min %": f"{v[0]:.0f}%", "Max %": f"{v[1]:.0f}%"}
                 for k, v in rl.constraints.items()]
            )
            st.dataframe(cdf, hide_index=True, use_container_width=True)

        risk_aversion = 21 - risk_level  # keep downstream compat (high level = low aversion)
        
        st.divider()
        
        # Time Horizon
        st.subheader("Time Horizon")
        hz_col1, hz_col2 = st.columns([2, 1])
        with hz_col2:
            hz_unit = st.selectbox("Unit", ["Days", "Weeks", "Months", "Years"], index=3)
        with hz_col1:
            _unit_limits = {
                "Days":   (1,   3650, 30),
                "Weeks":  (1,   520,  4),
                "Months": (1,   120,  6),
                "Years":  (1,   50,   5),
            }
            _lo, _hi, _def = _unit_limits[hz_unit]
            hz_val = st.number_input(
                f"Duration ({hz_unit.lower()})",
                min_value=_lo, max_value=_hi, value=_def, step=1,
            )
        # Convert to years (float) for all downstream calcs
        _to_years = {"Days": 1/365, "Weeks": 1/52, "Months": 1/12, "Years": 1}
        years = hz_val * _to_years[hz_unit]

        # Human-readable label
        if hz_unit == "Days" and hz_val < 7:
            _hz_label = f"{hz_val}d"
        elif hz_unit == "Days":
            _hz_label = f"{hz_val}d ({hz_val/7:.1f}w)"
        elif hz_unit == "Weeks" and hz_val < 4:
            _hz_label = f"{hz_val}w"
        elif hz_unit == "Weeks":
            _hz_label = f"{hz_val}w ({hz_val/4.33:.1f}mo)"
        elif hz_unit == "Months" and hz_val < 12:
            _hz_label = f"{hz_val}mo"
        else:
            _hz_label = f"{years:.2f}y" if years < 2 else f"{years:.1f}y"

        st.caption(f"Horizon: **{_hz_label}**  ·  {years*365:.0f} calendar days  ·  {years*252:.0f} trading days")
        
        st.divider()
        
        # ESG & Additional Preferences
        st.subheader("Preferences")
        col_esg1, col_esg2 = st.columns(2)
        with col_esg1:
            esg_focus = st.checkbox(" ESG Focus", value=False)
        with col_esg2:
            income_focus = st.checkbox(" Income Focus", value=False)
        
        st.write("")
        
        # SUBMIT BUTTON
        submit = st.button(
            " Generate Optimal Portfolio",
            use_container_width=True,
            type="primary"
        )
    
    # RIGHT: Risk-Return Profile
    with form_col2:
        st.subheader("Risk/Return Profile")

        # Pull from risk matrix
        expected_return = rl.target_return_pa
        volatility      = rl.vol_budget_pa
        sharpe_ratio    = rl.sharpe_target

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Target Return (p.a.)", f"{expected_return:.1f}%")
            st.metric("Sharpe Target",        f"{sharpe_ratio:.2f}")
        with col2:
            st.metric("Vol Budget (σ p.a.)",  f"{volatility:.1f}%")
            st.metric("Time Horizon",         _hz_label)

        # 20-level risk tower gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk_level,
            number={'font': {'size': 40, 'color': CATEGORY_COLORS.get(rl.category, '#888')}},
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"<b>{rl.label}</b><br><sub>{rl.category}</sub>",
                   'font': {'size': 13}},
            gauge={
                'axis': {'range': [1, 20], 'tickwidth': 1,
                         'tickvals': [1, 4, 7, 10, 13, 16, 18, 20],
                         'ticktext': ['CP', 'Cons.', 'Bal.', 'Gr.',
                                      'Agg.', 'Hi', 'Spec', 'MAX']},
                'bar': {'color': CATEGORY_COLORS.get(rl.category, '#888'), 'thickness': 0.25},
                'bgcolor': "#1a1a2e",
                'bordercolor': "#333",
                'steps': [
                    {'range': [1,  4],  'color': '#1a9850'},
                    {'range': [4,  7],  'color': '#d9ef8b'},
                    {'range': [7,  10], 'color': '#fee08b'},
                    {'range': [10, 13], 'color': '#fdae61'},
                    {'range': [13, 16], 'color': '#f46d43'},
                    {'range': [16, 18], 'color': '#d73027'},
                    {'range': [18, 20], 'color': '#67000d'},
                ],
                'threshold': {
                    'line': {'color': 'white', 'width': 3},
                    'thickness': 0.85,
                    'value': risk_level,
                },
            }
        ))
        fig.update_layout(
            height=380,
            paper_bgcolor='rgba(0,0,0,0)',
            font={'color': 'white'},
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# PORTFOLIO GENERATION & DISPLAY
# ============================================================================

if submit:
    st.divider()
    
    # Build allocation from risk matrix constraints (midpoint of min/max)
    rl_alloc = get_level(risk_level)
    raw = {k: (v[0] + v[1]) / 2.0 for k, v in rl_alloc.constraints.items()
           if k != "Unconstrained"}
    total = sum(raw.values()) or 1.0
    allocation = {k: v / total for k, v in raw.items()}
    
    # Calculate amounts
    allocation_amounts = {asset: amount * pct for asset, pct in allocation.items()}
    allocation_pct = {asset: pct * 100 for asset, pct in allocation.items()}
    
    # RESULTS SECTION
    st.header("Your Optimal Portfolio Recommendation")
    
    # Allocation breakdown
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(" Asset Allocation")
        
        # Pie chart
        fig = go.Figure(data=[go.Pie(
            labels=list(allocation_pct.keys()),
            values=list(allocation_pct.values()),
            textposition='auto',
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>'
        )])
        fig.update_layout(height=520)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader(" Investment Breakdown")
        alloc_df = pd.DataFrame({
            'Asset Class': list(allocation_amounts.keys()),
            'Allocation %': [f"{v:.1f}%" for v in allocation_pct.values()],
            f'Amount ({currency})': [f"{v:,.0f}" for v in allocation_amounts.values()]
        })
        st.dataframe(alloc_df, use_container_width=True, hide_index=True)
    
    # ========================================================================
    # KEY METRICS & PROJECTIONS
    # ========================================================================
    
    st.divider()
    st.subheader(" Projected Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    final_value = amount * (1 + expected_return/100) ** years
    total_gain = final_value - amount
    annualized_return = (expected_return * years)
    max_loss = amount * (volatility / 100) * 2  # 2-sigma approximation
    
    with col1:
        st.metric(
            "Projected Final Value",
            f"{final_value:,.0f} {currency}",
            f"+{total_gain:,.0f}",
            help=f"After {years:.1f} years at {expected_return:.1f}% p.a."
        )
    
    with col2:
        st.metric(
            "Total Gain",
            f"{(total_gain/amount)*100:.1f}%",
            f"{total_gain:,.0f} {currency}",
            help="Cumulative return over period"
        )
    
    with col3:
        st.metric(
            "Annual Return",
            f"{expected_return:.1f}%",
            help="Expected annual return"
        )
    
    with col4:
        st.metric(
            "Max Expected Loss (2σ)",
            f"{max_loss:,.0f} {currency}",
            f"{(max_loss/amount)*100:.1f}%",
            help="Potential loss in adverse scenarios"
        )
    
    # Growth projection chart
    st.subheader(" Growth Projection")
    
    years_range = np.linspace(0, years, int(years * 12))  # Monthly projections
    values = amount * (1 + expected_return/100) ** years_range
    
    # Add confidence interval
    upper_bound = amount * (1 + (expected_return + volatility)/100) ** years_range
    lower_bound = amount * (1 + max(0, expected_return - volatility)/100) ** years_range
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=years_range,
        y=values,
        name='Expected Growth',
        mode='lines',
        line=dict(color='green', width=3)
    ))
    
    fig.add_trace(go.Scatter(
        x=years_range,
        y=upper_bound,
        name='Upper Bound (+1σ)',
        mode='lines',
        line=dict(color='lightgreen', width=1, dash='dash'),
        opacity=0.5
    ))
    
    fig.add_trace(go.Scatter(
        x=years_range,
        y=lower_bound,
        name='Lower Bound (-1σ)',
        mode='lines',
        line=dict(color='salmon', width=1, dash='dash'),
        opacity=0.5,
        fill='tonexty'
    ))
    
    fig.update_layout(
        title='Portfolio Value Projection Over Time',
        xaxis_title='Years',
        yaxis_title=f'Portfolio Value ({currency})',
        hovermode='x unified',
        height=520
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ========================================================================
    # WHY THIS ALLOCATION?
    # ========================================================================
    
    st.divider()
    st.subheader(" Why This Allocation?")
    
    explanation_text = (
        f"**Level {rl.level} — {rl.label}** ({rl.category})\n\n"
        f"- **Mandate:** {rl.typical_mandate}\n"
        f"- **Vol budget:** {rl.vol_budget_pa:.1f}% p.a. — portfolio must stay within this annualized sigma\n"
        f"- **VaR limit:** 1-day 95% VaR ≤ {rl.var_95_1d:.2f}% of NAV "
        f"/ 99% VaR ≤ {rl.var_99_1d:.2f}%\n"
        f"- **Max drawdown tolerance:** {rl.max_drawdown_pct:.0f}%\n"
        f"- **Beta cap:** net exposure ≤ {rl.beta_cap:.2f}x S&P 500\n"
        f"- **Max leverage:** {rl.max_leverage:.1f}x NAV\n"
        f"- **Sharpe target:** ≥ {rl.sharpe_target:.2f}"
    )
    
    with st.container(border=True):
        st.markdown(explanation_text)
    
    # ========================================================================
    # RISK WARNINGS
    # ========================================================================
    
    st.divider()
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("[WARN] Risk Factors")
        risks = [
            "**Market Risk**: Overall market downturns may impact all assets",
            "**Interest Rate Risk**: Bond prices decline if rates rise",
            "**Currency Risk**: Non-domestic allocations exposed to FX movements",
            "**Liquidity Risk**: Some assets may be difficult to sell quickly",
            "**Concentration Risk**: Overweight in any single sector"
        ]
        for risk in risks:
            st.write(risk)
    
    with col2:
        st.subheader("Mitigations")
        mitigations = [
            "v **Diversification**: Spread across multiple asset classes and geographies",
            "v **Rebalancing**: Quarterly adjustments to maintain target allocation",
            "v **Dollar-Cost Averaging**: Gradual investment over time reduces timing risk",
            "v **Stop-Loss Orders**: Automatic selling at predetermined loss levels (optional)",
            "v **ESG Screening**: Focus on quality, sustainable companies" if esg_focus else "v **Professional Management**: Expert oversight of positions"
        ]
        for mitigation in mitigations:
            st.write(mitigation)
    
    # ========================================================================
    # ACTION ITEMS
    # ========================================================================
    
    st.divider()
    st.subheader(" Next Steps")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button(" Export Portfolio", use_container_width=True):
            # Export to CSV
            csv = alloc_df.to_csv(index=False)
            st.download_button(
                label="Download as CSV",
                data=csv,
                file_name=f"portfolio_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with action_col2:
        if st.button(" View Detailed Analysis", use_container_width=True):
            st.info("Detailed analysis with physics-based risk metrics coming from GenesisX Physics module")
    
    with action_col3:
        if st.button(" Discuss with Advisor", use_container_width=True):
            st.info("Schedule a consultation to refine your portfolio")

# ============================================================================
# REAL PORTFOLIO OPTIMIZATION SECTION
# ============================================================================

st.divider()
st.header("Quantitative Portfolio Optimization")
st.markdown("Mean-variance optimization using real 2-year historical data via scipy SLSQP solver.")

with st.expander("Run Optimizer", expanded=False):
    opt_col1, opt_col2 = st.columns(2)
    with opt_col1:
        default_tickers = ['SPY', 'QQQ', 'TLT', 'GLD', 'IWM', 'EEM']
        opt_tickers_raw = st.text_input(
            "Tickers (comma-separated)",
            value=', '.join(default_tickers),
            help="Enter tickers to optimize across"
        )
        opt_tickers = [t.strip().upper() for t in opt_tickers_raw.split(',') if t.strip()]
    with opt_col2:
        opt_level = st.slider(
            "Risk level (1–20)",
            min_value=1, max_value=20, value=7, step=1,
            help="Sets the target return constraint for optimization",
            key="opt_risk_slider"
        )
        opt_profile = opt_level

    if st.button("Run Optimization", type="primary", use_container_width=True):
        if len(opt_tickers) < 2:
            st.warning("Please enter at least 2 tickers.")
        else:
            with st.spinner("Fetching data and running optimization..."):
                opt_weights, opt_metrics = optimize_portfolio(tuple(opt_tickers), opt_profile)

            if opt_weights and opt_metrics:
                st.success("Optimization converged successfully.")
                m1, m2, m3 = st.columns(3)
                m1.metric("Expected Return (p.a.)", f"{opt_metrics['return']:.1f}%")
                m2.metric("Portfolio Volatility (p.a.)", f"{opt_metrics['vol']:.1f}%")
                m3.metric("Sharpe Ratio", f"{opt_metrics['sharpe']:.2f}")

                opt_df = pd.DataFrame([
                    {'Ticker': t, 'Optimal Weight (%)': f"{w:.1f}%"}
                    for t, w in sorted(opt_weights.items(), key=lambda x: -x[1])
                ])
                oc1, oc2 = st.columns(2)
                with oc1:
                    st.dataframe(opt_df, use_container_width=True, hide_index=True)
                with oc2:
                    fig_opt = go.Figure(data=[go.Pie(
                        labels=list(opt_weights.keys()),
                        values=[round(w, 2) for w in opt_weights.values()],
                        textinfo='label+percent',
                        hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>'
                    )])
                    fig_opt.update_layout(title="Optimized Allocation", height=520)
                    st.plotly_chart(fig_opt, use_container_width=True)
            else:
                st.error("Optimization failed. This can happen if target return is unachievable with the given tickers or data is unavailable. Try different tickers or a lower target.")


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
---
**GenesiX Intelligent Portfolio Allocator** | Powered by Advanced Physics-Based Risk Analytics

*Disclaimer: This tool is for educational purposes. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making investment decisions.*
""")
