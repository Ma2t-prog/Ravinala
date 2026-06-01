"""
GenesiX Backtest Results — v2.1
Equity curve, performance metrics, rolling returns, attribution
"""

import sys
import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.genesix.backtesting_engine import BacktestingEngine, BacktestConfig, create_backtest_config
from src.genesix.design_system import QUANTUM_DARK

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Backtest Results | GENESIX Ω",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom theme
st.markdown(f"""
<style>
:root {{
    --primary-bg: {QUANTUM_DARK['bg_1']};
    --primary-text: {QUANTUM_DARK['text_0']};
    --accent-1: {QUANTUM_DARK['accent_primary']};
}}
body {{
    background-color: {QUANTUM_DARK['bg_1']};
    color: {QUANTUM_DARK['text_0']};
}}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# PAGE STATE & CONFIG
# ============================================================================

st.title("Backtest Results")
st.markdown("Simulate portfolio performance over historical period with detailed attribution analysis.")

# Sidebar configuration
with st.sidebar:
    st.header("Backtest Configuration")
    
    # Portfolio universe
    portfolio_universe = st.multiselect(
        "Portfolio Tickers",
        ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "JPM", "JNJ", "XOM", "PG"],
        default=["AAPL", "MSFT", "GOOGL"]
    )
    
    if not portfolio_universe:
        st.warning("Select at least one ticker")
        st.stop()
    
    # Equal weight for simplicity
    weights = {ticker: 1.0 / len(portfolio_universe) for ticker in portfolio_universe}
    
    # Date range
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=datetime.now() - timedelta(days=365)
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=datetime.now()
        )
    
    # Initial capital
    initial_capital = st.number_input(
        "Initial Capital ($)",
        value=100_000,
        min_value=10_000,
        step=10_000
    )
    
    # Benchmark
    benchmark_ticker = st.selectbox(
        "Benchmark",
        ["SPY", "QQQ", "IWM", "EEM", "AGG"]
    )
    
    # Rebalance frequency
    rebalance_freq = st.selectbox(
        "Rebalance Frequency",
        ["daily", "weekly", "monthly", "quarterly"]
    )
    
    # Run backtest
    run_bt = st.button("▶️ Run Backtest", use_container_width=True)

# ============================================================================
# BACKTEST EXECUTION
# ============================================================================

if run_bt:
    with st.spinner("Running backtest simulation..."):
        config = BacktestConfig(
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.min.time()),
            initial_capital=initial_capital,
            rebalance_frequency=rebalance_freq,
            benchmark_ticker=benchmark_ticker
        )
        
        engine = BacktestingEngine(
            tickers=portfolio_universe,
            weights=weights,
            config=config
        )
        
        result = engine.run()
    
    if result is None:
        st.error("Backtest failed. Check data availability.")
        st.stop()
    
    # Store in session state
    st.session_state['backtest_result'] = result
    st.session_state['backtest_config'] = config
    st.session_state['ticker_weights'] = weights
    st.success("✅ Backtest complete!")

# ============================================================================
# RESULTS DISPLAY
# ============================================================================

if 'backtest_result' in st.session_state:
    result = st.session_state['backtest_result']
    config = st.session_state['backtest_config']
    weights = st.session_state['ticker_weights']
    
    # Create tabs
    tabs = st.tabs([
        "Equity Curve",
        "Performance Metrics",
        "Rolling Returns",
        "Attribution",
        "Risk Analysis",
        "Returns Heatmap"
    ])
    
    # ========== TAB 1: EQUITY CURVE ==========
    with tabs[0]:
        st.subheader("Portfolio vs Benchmark")
        
        # Prepare data
        equity_data = pd.DataFrame({
            'Date': result.portfolio_value.index,
            'Portfolio': result.portfolio_value.values,
            'Benchmark': result.benchmark_value.reindex_like(result.portfolio_value).ffill().values
        }).set_index('Date')
        
        # Normalize to 100 at start
        equity_data_norm = (equity_data / equity_data.iloc[0]) * 100
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=equity_data_norm.index,
            y=equity_data_norm['Portfolio'],
            name='Portfolio',
            line=dict(color=QUANTUM_DARK['accent_primary'], width=2),
            hovertemplate='<b>Portfolio</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:.2f}k<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=equity_data_norm.index,
            y=equity_data_norm['Benchmark'],
            name='Benchmark',
            line=dict(color=QUANTUM_DARK['accent_info'], width=2, dash='dash'),
            hovertemplate='<b>Benchmark</b><br>Date: %{x|%Y-%m-%d}<br>Value: $%{y:.2f}k<extra></extra>'
        ))
        
        fig.update_layout(
            title="Portfolio Equity Curve (Indexed to 100)",
            xaxis_title="Date",
            yaxis_title="Value (Indexed)",
            hovermode='x unified',
            template='plotly_dark',
            plot_bgcolor=QUANTUM_DARK['bg_1'],
            paper_bgcolor=QUANTUM_DARK['bg_1'],
            font=dict(color=QUANTUM_DARK['text_0']),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Key stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Return", f"{result.total_return:.2f}%")
        with col2:
            outperformance = result.total_return - ((result.benchmark_value.iloc[-1] / config.initial_capital - 1) * 100)
            st.metric("Outperformance", f"{outperformance:+.2f}%")
        with col3:
            st.metric("Max Drawdown", f"{result.max_drawdown:.2f}%", delta_color="inverse")
        with col4:
            st.metric("Sharpe Ratio", f"{result.sharpe_ratio:.2f}")
    
    # ========== TAB 2: PERFORMANCE METRICS ==========
    with tabs[1]:
        st.subheader("Performance Metrics Summary")
        
        # Create metrics table
        metrics_data = {
            'Metric': [
                'Annual Return',
                'Annual Volatility',
                'Sharpe Ratio',
                'Sortino Ratio',
                'Max Drawdown',
                'Calmar Ratio',
                'Beta',
                'Alpha (Annual)',
                'Information Ratio',
                'Tracking Error',
                'Win/Loss Ratio',
                'Days Negative'
            ],
            'Portfolio': [
                f"{result.annual_return:.2f}%",
                f"{result.annual_volatility:.2f}%",
                f"{result.sharpe_ratio:.2f}",
                f"{result.sortino_ratio:.2f}",
                f"{result.max_drawdown:.2f}%",
                f"{result.calmar_ratio:.2f}",
                f"{result.beta:.2f}",
                f"{result.alpha:.2f}%",
                f"{result.information_ratio:.2f}",
                f"{result.tracking_error:.2f}%",
                f"{result.win_loss_ratio:.2f}",
                f"{result.days_negative}"
            ]
        }
        
        metrics_df = pd.DataFrame(metrics_data)
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
        
        # Benchmark comparison
        st.subheader("vs Benchmark")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Portfolio Return", f"{result.annual_return:.2f}%")
        with col2:
            st.metric("Benchmark Return", f"{(result.benchmark_returns.mean() * 252 * 100):.2f}%")
        with col3:
            st.metric("Excess Return (Alpha)", f"{result.alpha:.2f}%")
    
    # ========== TAB 3: ROLLING RETURNS ==========
    with tabs[2]:
        st.subheader("Rolling Performance")
        
        # Calculate rolling returns
        rolling_1m = result.daily_returns.rolling(21).mean() * 252  # 21 trading days
        rolling_3m = result.daily_returns.rolling(63).mean() * 252
        rolling_6m = result.daily_returns.rolling(126).mean() * 252
        rolling_1y = result.daily_returns.rolling(252).mean() * 252
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=rolling_1m.index,
            y=rolling_1m.values,
            name='1M Rolling Return',
            line=dict(color=QUANTUM_DARK['accent_primary'])
        ))
        
        fig.add_trace(go.Scatter(
            x=rolling_3m.index,
            y=rolling_3m.values,
            name='3M Rolling Return',
            line=dict(color=QUANTUM_DARK['accent_info'])
        ))
        
        fig.add_trace(go.Scatter(
            x=rolling_6m.index,
            y=rolling_6m.values,
            name='6M Rolling Return',
            line=dict(color=QUANTUM_DARK['accent_premium'])
        ))
        
        fig.add_trace(go.Scatter(
            x=rolling_1y.index,
            y=rolling_1y.values,
            name='1Y Rolling Return',
            line=dict(color=QUANTUM_DARK['text_0'], width=2)
        ))
        
        fig.update_layout(
            title="Rolling Annualized Returns",
            xaxis_title="Date",
            yaxis_title="Return (%)",
            hovermode='x unified',
            template='plotly_dark',
            plot_bgcolor=QUANTUM_DARK['bg_1'],
            paper_bgcolor=QUANTUM_DARK['bg_1'],
            font=dict(color=QUANTUM_DARK['text_0']),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Rolling volatility
        fig2 = go.Figure()
        rolling_vol = result.daily_returns.rolling(63).std() * np.sqrt(252) * 100
        
        fig2.add_trace(go.Scatter(
            x=rolling_vol.index,
            y=rolling_vol.values,
            name='Rolling Volatility (63-day)',
            fill='tozeroy',
            line=dict(color=QUANTUM_DARK['accent_primary'])
        ))
        
        fig2.update_layout(
            title="Rolling Volatility",
            xaxis_title="Date",
            yaxis_title="Volatility (%)",
            hovermode='x',
            template='plotly_dark',
            plot_bgcolor=QUANTUM_DARK['bg_1'],
            paper_bgcolor=QUANTUM_DARK['bg_1'],
            font=dict(color=QUANTUM_DARK['text_0']),
            height=400
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    # ========== TAB 4: ATTRIBUTION ==========
    with tabs[3]:
        st.subheader("Position Attribution")
        
        # Attribution table
        attribution_data = []
        for ticker, weight in weights.items():
            ticker_return = result.instrument_returns.get(ticker, 0)
            pnl = result.instrument_pnl.get(ticker, 0)
            
            attribution_data.append({
                'Ticker': ticker,
                'Weight': f"{weight*100:.1f}%",
                'Return': f"{ticker_return:.2f}%",
                'Contribution': f"{pnl:.2f}%"
            })
        
        attr_df = pd.DataFrame(attribution_data)
        st.dataframe(attr_df, use_container_width=True, hide_index=True)
        
        # Attribution chart
        fig = go.Figure(data=[
            go.Bar(
                x=[a['Ticker'] for a in attribution_data],
                y=[float(a['Contribution'].rstrip('%')) for a in attribution_data],
                marker_color=QUANTUM_DARK['accent_primary'],
                name='Return Contribution'
            )
        ])
        
        fig.update_layout(
            title="Return Contribution by Position",
            xaxis_title="Ticker",
            yaxis_title="Contribution (%)",
            template='plotly_dark',
            plot_bgcolor=QUANTUM_DARK['bg_1'],
            paper_bgcolor=QUANTUM_DARK['bg_1'],
            font=dict(color=QUANTUM_DARK['text_0']),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # ========== TAB 5: RISK ANALYSIS ==========
    with tabs[4]:
        st.subheader("Risk Analysis")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("VaR (95%)", f"{result.var_95:.2f}%", delta_color="inverse")
        with col2:
            st.metric("CVaR (95%)", f"{result.cvar_95:.2f}%", delta_color="inverse")
        with col3:
            st.metric("Max Daily Loss", f"{result.max_daily_loss:.2f}%", delta_color="inverse")
        with col4:
            st.metric("Max Drawdown", f"{result.max_drawdown:.2f}%", delta_color="inverse")
        
        # Return distribution
        fig = go.Figure(data=[
            go.Histogram(
                x=result.daily_returns.values,
                nbinsx=50,
                name='Daily Returns',
                marker_color=QUANTUM_DARK['accent_primary'],
                opacity=0.7
            )
        ])
        
        fig.add_vline(x=result.var_95, line_dash="dash", line_color=QUANTUM_DARK['accent_info'], 
                      annotation_text=f"VaR (95%): {result.var_95:.2f}%")
        
        fig.update_layout(
            title="Daily Returns Distribution (with VaR)",
            xaxis_title="Daily Return (%)",
            yaxis_title="Frequency",
            template='plotly_dark',
            plot_bgcolor=QUANTUM_DARK['bg_1'],
            paper_bgcolor=QUANTUM_DARK['bg_1'],
            font=dict(color=QUANTUM_DARK['text_0']),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # ========== TAB 6: RETURNS HEATMAP ==========
    with tabs[5]:
        st.subheader("Monthly Returns Heatmap")
        
        # Create monthly returns
        monthly_returns = result.daily_returns.resample('M').sum()
        
        # Create pivot table (year x month)
        monthly_returns_df = pd.DataFrame({
            'Date': monthly_returns.index,
            'Return': monthly_returns.values
        })
        
        monthly_returns_df['Year'] = monthly_returns_df['Date'].dt.year
        monthly_returns_df['Month'] = monthly_returns_df['Date'].dt.month
        monthly_returns_df['Month_Name'] = monthly_returns_df['Date'].dt.strftime('%b')
        
        heatmap_data = monthly_returns_df.pivot_table(
            values='Return',
            index='Year',
            columns='Month',
            aggfunc='sum'
        )
        
        # Rename columns to month names
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        heatmap_data.columns = [month_names[i-1] if i in heatmap_data.columns else f"M{i}" for i in range(1, 13)]
        
        # Reorder columns
        heatmap_data = heatmap_data[[col for col in month_names if col in heatmap_data.columns]]
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns,
            y=heatmap_data.index,
            colorscale='RdYlGn',
            zmid=0,
            text=[[f"{v:.1f}%" if not pd.isna(v) else "" for v in row] for row in heatmap_data.values],
            texttemplate='%{text}',
            textfont={"size": 10},
            colorbar=dict(title="Return (%)")
        ))
        
        fig.update_layout(
            title="Monthly Returns by Year (%)",
            xaxis_title="Month",
            yaxis_title="Year",
            template='plotly_dark',
            plot_bgcolor=QUANTUM_DARK['bg_1'],
            paper_bgcolor=QUANTUM_DARK['bg_1'],
            font=dict(color=QUANTUM_DARK['text_0']),
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
else:
    # Initial state
    st.info("""
    Configure backtest settings in the sidebar, then click **Run Backtest** to simulate portfolio performance.
    
    The backtest will:
    - Simulate daily portfolio performance from start to end date
    - Rebalance according to selected frequency
    - Calculate professional metrics (Sharpe, Sortino, Alpha, Beta)
    - Compare vs benchmark (SPY, QQQ, etc.)
    - Generate attribution analysis
    - Compute Value at Risk and stress scenarios
    """)
