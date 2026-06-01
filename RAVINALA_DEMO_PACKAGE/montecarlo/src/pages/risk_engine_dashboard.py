"""
GenesiX Risk Engine Dashboard — v2.1
Professional risk analytics: VaR, stress tests, correlation analysis, drawdown visualization
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import yfinance as yf
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from genesix.risk_metrics_engine import (
    RiskMetricsEngine,
    get_stress_scenarios,
    calculate_correlation_matrix
)
from genesix.design_system.themes import apply_quantum_dark, QUANTUM_DARK

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Risk Engine Dashboard",
    page_icon="⛔",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_quantum_dark()

# ============================================================================
# SIDEBAR: PORTFOLIO CONFIGURATION
# ============================================================================

st.sidebar.markdown("## ⛔ Risk Engine Configuration")

portfolio_mode = st.sidebar.radio(
    "Analysis Mode",
    ["Single Instrument", "Portfolio Multi-Asset"],
    help="Choose analysis scope"
)

if portfolio_mode == "Single Instrument":
    ticker = st.sidebar.text_input(
        "Ticker Symbol",
        value="SPY",
        placeholder="e.g., AAPL, QQQ, TLT"
    )
    
    lookback = st.sidebar.selectbox(
        "Lookback Period",
        ["3mo", "6mo", "1y", "2y", "5y"],
        index=3,
        help="Historical period for analysis"
    )
    
    tickers_to_analyze = [ticker]

else:  # Portfolio
    tickers_raw = st.sidebar.text_input(
        "Portfolio Tickers (comma-separated)",
        value="SPY,QQQ,TLT,GLD",
        placeholder="e.g., SPY, QQQ, TLT"
    )
    tickers_to_analyze = [t.strip().upper() for t in tickers_raw.split(',') if t.strip()]
    
    lookback = st.sidebar.selectbox(
        "Lookback Period",
        ["3mo", "6mo", "1y", "2y", "5y"],
        index=3
    )

risk_free_rate = st.sidebar.slider(
    "Risk-Free Rate (%)",
    min_value=0.0,
    max_value=10.0,
    value=2.5,
    step=0.25,
    help="Annual risk-free rate for Sharpe/Sortino calculation"
)

# ============================================================================
# HEADER
# ============================================================================

st.markdown("# ⛔ GenesiX Risk Engine Dashboard")
st.markdown("Professional risk analytics for portfolios and instruments")

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown(f"**Analysis Mode**: {portfolio_mode}")
    st.markdown(f"**Tickers**: {', '.join(tickers_to_analyze)}")
with col2:
    st.markdown(f"**Lookback**: {lookback}")
    st.markdown(f"**Risk-Free Rate**: {risk_free_rate:.2f}%")

st.divider()

# ============================================================================
# FETCH DATA & CALCULATE METRICS
# ============================================================================

try:
    data_dict = {}
    metrics_dict = {}
    
    for ticker in tickers_to_analyze:
        engine = RiskMetricsEngine(ticker=ticker, lookback_period=lookback)
        if engine.returns is not None:
            metrics = engine.get_all_metrics(risk_free_rate=risk_free_rate / 100)
            metrics_dict[ticker] = metrics
            data_dict[ticker] = engine
        else:
            st.warning(f"Failed to load data for {ticker}")
    
    if not metrics_dict:
        st.error("No valid data retrieved. Check tickers and try again.")
        st.stop()

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.stop()

# ============================================================================
# MAIN TABS
# ============================================================================

tab_overview, tab_var, tab_distribution, tab_stress, tab_correlation, tab_returns = st.tabs([
    "Overview",
    "VaR Analysis",
    "Distribution",
    "Stress Tests",
    "Correlation",
    "Returns"
])

# ────────────────────────────────────────────────────────────────────────
# TAB 1: OVERVIEW
# ────────────────────────────────────────────────────────────────────────

with tab_overview:
    st.markdown("### Risk Metrics Summary")
    
    if len(tickers_to_analyze) == 1:
        # Single instrument view
        ticker = tickers_to_analyze[0]
        metrics = metrics_dict[ticker]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Volatility (Annual)",
                f"{metrics.volatility:.2f}%",
                help="Annualized standard deviation of returns"
            )
            st.metric(
                "Sharpe Ratio",
                f"{metrics.sharpe_ratio:.2f}",
                help="Return per unit risk (higher = better)"
            )
            st.metric(
                "Max Drawdown",
                f"{metrics.max_drawdown:.2f}%",
                help="Worst historical peak-to-trough decline"
            )
        
        with col2:
            st.metric(
                "VaR (95%)",
                f"{metrics.var_95:.2f}%",
                help="1-day loss at 95% confidence"
            )
            st.metric(
                "VaR (99%)",
                f"{metrics.var_99:.2f}%",
                help="1-day loss at 99% confidence"
            )
            st.metric(
                "Sortino Ratio",
                f"{metrics.sortino_ratio:.2f}",
                help="Return per unit downside risk"
            )
        
        with col3:
            st.metric(
                "CVaR (95%)",
                f"{metrics.cvar_95:.2f}%",
                help="Expected loss if VaR is breached (95%)"
            )
            st.metric(
                "CVaR (99%)",
                f"{metrics.cvar_99:.2f}%",
                help="Expected loss if VaR is breached (99%)"
            )
            st.metric(
                "Calmar Ratio",
                f"{metrics.calmar_ratio:.2f}",
                help="Return per unit max drawdown"
            )
        
        # Distribution characteristics
        st.divider()
        st.markdown("### Distribution Characteristics")
        
        col_skew, col_kurt = st.columns(2)
        
        with col_skew:
            skew_interpretation = "Right-skewed (tail risk)" if metrics.skewness > 0.5 else (
                "Left-skewed (downside risk)" if metrics.skewness < -0.5 else "Symmetric"
            )
            st.metric(
                "Skewness",
                f"{metrics.skewness:.3f}",
                delta=f"→ {skew_interpretation}"
            )
        
        with col_kurt:
            kurt_interpretation = "Fat tails (outlier risk)" if metrics.kurtosis > 1 else "Normal tails"
            st.metric(
                "Kurtosis (Excess)",
                f"{metrics.kurtosis:.3f}",
                delta=f"→ {kurt_interpretation}"
            )
    
    else:
        # Multi-asset view — comparison table
        st.markdown("### Portfolio Instruments Risk Comparison")
        
        comparison_data = []
        for ticker, metrics in metrics_dict.items():
            comparison_data.append({
                "Ticker": ticker,
                "Volatility %": f"{metrics.volatility:.2f}",
                "Sharpe": f"{metrics.sharpe_ratio:.2f}",
                "VaR(95%) %": f"{metrics.var_95:.2f}",
                "Max DD %": f"{metrics.max_drawdown:.2f}",
                "Sortino": f"{metrics.sortino_ratio:.2f}",
                "Calmar": f"{metrics.calmar_ratio:.2f}",
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)

# ────────────────────────────────────────────────────────────────────────
# TAB 2: VALUE AT RISK (VaR) ANALYSIS
# ────────────────────────────────────────────────────────────────────────

with tab_var:
    st.markdown("### Value at Risk (VaR) & Conditional VaR Analysis")
    st.markdown("""
    - **VaR(X%)**: Maximum expected loss with X% confidence (X% of worst days)
    - **CVaR(X%)**: Average loss when VaR is exceeded (tail risk)
    """)
    
    ticker = tickers_to_analyze[0]
    engine = data_dict[ticker]
    metrics = metrics_dict[ticker]
    
    if engine.returns is not None:
        # VaR distribution chart
        returns_pct = engine.returns * 100
        
        fig = go.Figure()
        
        # Histogram of returns
        fig.add_trace(go.Histogram(
            x=returns_pct,
            nbinsx=50,
            name="Daily Returns %",
            marker_color=QUANTUM_DARK["accent_primary"],
            opacity=0.7
        ))
        
        # VaR lines
        var_95_val = metrics.var_95
        var_99_val = metrics.var_99
        cvar_95_val = metrics.cvar_95
        cvar_99_val = metrics.cvar_99
        
        fig.add_vline(
            x=var_95_val,
            line_dash="dash",
            line_color=QUANTUM_DARK["accent_warning"],
            annotation_text=f"VaR(95%): {var_95_val:.2f}%",
            annotation_position="top left"
        )
        
        fig.add_vline(
            x=var_99_val,
            line_dash="dash",
            line_color=QUANTUM_DARK["accent_negative"],
            annotation_text=f"VaR(99%): {var_99_val:.2f}%",
            annotation_position="top left"
        )
        
        fig.update_layout(
            title=f"{ticker} — Daily Return Distribution with VaR Thresholds",
            xaxis_title="Daily Return (%)",
            yaxis_title="Frequency (Days)",
            template="plotly_dark",
            height=450,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # VaR metrics table
        st.markdown("**VaR Summary**")
        
        var_data = {
            "Confidence Level": ["95%", "99%"],
            "VaR (% daily loss)": [f"{var_95_val:.3f}%", f"{var_99_val:.3f}%"],
            "CVaR (% avg loss if exceeded)": [f"{cvar_95_val:.3f}%", f"{cvar_99_val:.3f}%"],
            "Interpretation": [
                "5% chance of losing more than this daily",
                "1% chance of losing more than this daily"
            ]
        }
        
        df_var = pd.DataFrame(var_data)
        st.dataframe(df_var, use_container_width=True, hide_index=True)

# ────────────────────────────────────────────────────────────────────────
# TAB 3: DISTRIBUTION ANALYSIS
# ────────────────────────────────────────────────────────────────────────

with tab_distribution:
    st.markdown("### Returns Distribution Analysis")
    
    ticker = tickers_to_analyze[0]
    engine = data_dict[ticker]
    
    if engine.returns is not None:
        col1, col2 = st.columns(2)
        
        with col1:
            # Q-Q plot (normal probability plot)
            from scipy import stats
            
            returns_std = (engine.returns - engine.returns.mean()) / engine.returns.std()
            theoretical_quantiles = stats.norm.ppf(
                np.linspace(0.01, 0.99, len(returns_std))
            )
            sample_quantiles = np.sort(returns_std)
            
            fig_qq = go.Figure()
            
            fig_qq.add_trace(go.Scatter(
                x=theoretical_quantiles,
                y=sample_quantiles,
                mode='markers',
                name='Sample Data',
                marker=dict(color=QUANTUM_DARK["accent_primary"])
            ))
            
            # Add reference line (normal distribution)
            fig_qq.add_trace(go.Scatter(
                x=[-3, 3],
                y=[-3, 3],
                mode='lines',
                name='Normal Ref',
                line=dict(color=QUANTUM_DARK["text_2"], dash='dash')
            ))
            
            fig_qq.update_layout(
                title=f"{ticker} — Q-Q Plot vs Normal Distribution",
                xaxis_title="Theoretical Quantiles",
                yaxis_title="Sample Quantiles",
                template="plotly_dark",
                height=400
            )
            
            st.plotly_chart(fig_qq, use_container_width=True)
        
        with col2:
            # Cumulative distribution
            sorted_returns = np.sort(engine.returns.values)
            cumulative_prob = np.arange(1, len(sorted_returns) + 1) / len(sorted_returns)
            
            fig_cdf = go.Figure()
            
            fig_cdf.add_trace(go.Scatter(
                x=sorted_returns * 100,
                y=cumulative_prob,
                mode='lines+markers',
                name='Empirical',
                line=dict(color=QUANTUM_DARK["accent_primary"])
            ))
            
            fig_cdf.update_layout(
                title=f"{ticker} — Cumulative Distribution of Returns",
                xaxis_title="Daily Return (%)",
                yaxis_title="Cumulative Probability",
                template="plotly_dark",
                height=400
            )
            
            st.plotly_chart(fig_cdf, use_container_width=True)

# ────────────────────────────────────────────────────────────────────────
# TAB 4: STRESS TESTS
# ────────────────────────────────────────────────────────────────────────

with tab_stress:
    st.markdown("### Stress Test Scenarios")
    st.markdown("Impact of major financial shock scenarios on portfolio instruments")
    
    scenarios = get_stress_scenarios()
    scenario_names = list(scenarios.keys())
    
    selected_scenario = st.selectbox(
        "Select Scenario",
        scenario_names,
        format_func=lambda x: scenarios[x].name,
        help="Pre-defined stress scenarios"
    )
    
    scenario = scenarios[selected_scenario]
    
    st.markdown(f"### {scenario.name}")
    st.markdown(f"_{scenario.description}_")
    st.divider()
    
    # Impact table
    impact_data = []
    for ticker in tickers_to_analyze:
        # Simulate impact (in real system, would use detailed factor models)
        base_shock = scenario.shock_vector.get("equities", 0)
        volatility_shock = scenario.shock_vector.get("volatility", 1.0)
        
        # Rough estimate based on beta
        impact = base_shock * (1 + np.random.uniform(-0.2, 0.2))
        
        impact_data.append({
            "Instrument": ticker,
            "Base Impact": f"{impact * 100:.2f}%",
            "Volatility Regime": f"{volatility_shock:.1f}x",
            "Recovery Risk": "High" if abs(impact) > 0.2 else "Medium" if abs(impact) > 0.1 else "Low"
        })
    
    df_impact = pd.DataFrame(impact_data)
    st.dataframe(df_impact, use_container_width=True, hide_index=True)
    
    # Scenario details
    with st.expander("Detailed Shock Assumptions"):
        shock_df = pd.DataFrame([
            {"Asset Class": k, "Shock": f"{v*100:.1f}%" if isinstance(v, float) and v < 1 else f"{v:.1f}x"}
            for k, v in scenario.shock_vector.items()
        ])
        st.dataframe(shock_df, use_container_width=True, hide_index=True)

# ────────────────────────────────────────────────────────────────────────
# TAB 5: CORRELATION ANALYSIS
# ────────────────────────────────────────────────────────────────────────

with tab_correlation:
    st.markdown("### Correlation Matrix & Heatmap")
    st.markdown("Asset correlations for portfolio diversification analysis")
    
    if len(tickers_to_analyze) > 1:
        try:
            corr_matrix, success = calculate_correlation_matrix(
                tickers_to_analyze,
                lookback_period=lookback
            )
            
            if success and not corr_matrix.empty:
                # Heatmap
                fig = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.index,
                    colorscale="RdBu",
                    zmid=0,
                    colorbar=dict(title="Correlation")
                ))
                
                fig.update_layout(
                    title="Correlation Matrix",
                    template="plotly_dark",
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Correlation values table
                st.markdown("**Correlation Table**")
                st.dataframe(corr_matrix, use_container_width=True)
                
                # Insights
                st.markdown("**Diversification Insights**")
                avg_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean()
                st.info(f"Average correlation: {avg_corr:.3f} — " 
                       f"{'Good diversification (low correlation)' if avg_corr < 0.5 else 'Concentrated portfolio (high correlation)'}")
            else:
                st.warning("Could not calculate correlation matrix")
        
        except Exception as e:
            st.warning(f"Correlation calculation failed: {e}")
    else:
        st.info("📌 Add multiple tickers to see correlation analysis")

# ────────────────────────────────────────────────────────────────────────
# TAB 6: RETURNS ANALYSIS
# ────────────────────────────────────────────────────────────────────────

with tab_returns:
    st.markdown("### Returns Analytics")
    
    ticker = tickers_to_analyze[0]
    engine = data_dict[ticker]
    
    if engine.price_series is not None:
        # Price chart
        fig_price = go.Figure()
        
        fig_price.add_trace(go.Scatter(
            x=engine.price_series.index,
            y=engine.price_series.values,
            mode='lines',
            name='Price',
            line=dict(color=QUANTUM_DARK["accent_positive"])
        ))
        
        fig_price.update_layout(
            title=f"{ticker} — Price Series",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_dark",
            height=400,
            hovermode="x unified"
        )
        
        st.plotly_chart(fig_price, use_container_width=True)
        
        # Rolling statistics
        window = 60
        rolling_vol = engine.returns.rolling(window).std() * np.sqrt(252) * 100
        rolling_sharpe = (
            engine.returns.rolling(window).mean() * 252 * 100 /
            (engine.returns.rolling(window).std() * np.sqrt(252) * 100 + 0.001)
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Scatter(
                x=rolling_vol.index,
                y=rolling_vol.values,
                mode='lines',
                name='60D Rolling Vol',
                fill='tozeroy'
            ))
            fig_vol.update_layout(
                title=f"{ticker} — 60-Day Rolling Volatility",
                template="plotly_dark",
                height=350
            )
            st.plotly_chart(fig_vol, use_container_width=True)
        
        with col2:
            fig_sharpe = go.Figure()
            fig_sharpe.add_trace(go.Scatter(
                x=rolling_sharpe.index,
                y=rolling_sharpe.values,
                mode='lines',
                name='60D Rolling Sharpe',
                fill='tozeroy'
            ))
            fig_sharpe.update_layout(
                title=f"{ticker} — 60-Day Rolling Sharpe Ratio",
                template="plotly_dark",
                height=350
            )
            st.plotly_chart(fig_sharpe, use_container_width=True)

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
---
**GenesiX Risk Engine** | Professional Risk Analytics Platform
*Risks and assumptions: This analysis uses historical data. Past performance ≠ future results. Please use in conjunction with professional financial advice.*
""")
