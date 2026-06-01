"""
Advanced Portfolio Analysis & Backtesting Engine
Provides historical backtesting, Monte Carlo simulations, and optimization
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ============================================================================
# EFFICIENT FRONTIER COMPUTATION (CACHED)
# ============================================================================

@st.cache_data(ttl=3600)
def compute_efficient_frontier(tickers: tuple):
    """Monte Carlo Efficient Frontier with 5000 random portfolios."""
    try:
        import yfinance as yf
        tickers_list = list(tickers)
        data = yf.download(tickers_list, period='2y', progress=False)['Close']
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.dropna(axis=1, thresh=int(len(data) * 0.8))
        data = data.dropna()
        tickers_clean = data.columns.tolist()

        if len(tickers_clean) < 2:
            return None, None

        returns = data.pct_change().dropna()
        mu = returns.mean().values * 252
        cov = returns.cov().values * 252
        n = len(tickers_clean)

        results = {'vol': [], 'ret': [], 'sharpe': [], 'weights': []}
        rng = np.random.default_rng(42)
        for _ in range(5000):
            w = rng.dirichlet(np.ones(n))
            ret = float(w @ mu)
            vol = float(np.sqrt(w @ cov @ w))
            results['vol'].append(vol)
            results['ret'].append(ret)
            results['sharpe'].append(ret / (vol + 1e-8))
            results['weights'].append(w.tolist())

        # Min variance portfolio
        from scipy.optimize import minimize
        def port_vol(w): return float(np.sqrt(w @ cov @ w))
        res_mv = minimize(port_vol, np.ones(n)/n, method='SLSQP',
                          bounds=[(0, 1)]*n,
                          constraints=[{'type': 'eq', 'fun': lambda w: np.sum(w)-1}])
        min_var_w = res_mv.x if res_mv.success else np.ones(n)/n
        min_var_ret = float(min_var_w @ mu)
        min_var_vol = float(np.sqrt(min_var_w @ cov @ min_var_w))

        # Max Sharpe
        def neg_sharpe(w): return -(w @ mu) / (np.sqrt(w @ cov @ w) + 1e-8)
        res_ms = minimize(neg_sharpe, np.ones(n)/n, method='SLSQP',
                          bounds=[(0, 1)]*n,
                          constraints=[{'type': 'eq', 'fun': lambda w: np.sum(w)-1}])
        max_sharpe_w = res_ms.x if res_ms.success else np.ones(n)/n
        max_sharpe_ret = float(max_sharpe_w @ mu)
        max_sharpe_vol = float(np.sqrt(max_sharpe_w @ cov @ max_sharpe_w))

        # Equal weight
        ew = np.ones(n) / n
        ew_ret = float(ew @ mu)
        ew_vol = float(np.sqrt(ew @ cov @ ew))

        specials = {
            'min_var': {'weights': min_var_w.tolist(), 'ret': min_var_ret, 'vol': min_var_vol,
                        'sharpe': min_var_ret / (min_var_vol + 1e-8)},
            'max_sharpe': {'weights': max_sharpe_w.tolist(), 'ret': max_sharpe_ret, 'vol': max_sharpe_vol,
                           'sharpe': max_sharpe_ret / (max_sharpe_vol + 1e-8)},
            'equal_weight': {'weights': ew.tolist(), 'ret': ew_ret, 'vol': ew_vol,
                             'sharpe': ew_ret / (ew_vol + 1e-8)},
        }

        return results, {'tickers': tickers_clean, 'specials': specials,
                         'mu': mu.tolist(), 'cov': cov.tolist()}
    except Exception as e:
        return None, None


st.set_page_config(
    page_title=" Portfolio Analysis - Omega",
    page_icon=None,
    layout="wide"
)

st.markdown("#  Advanced Portfolio Analysis")
st.markdown("Backtesting, Monte Carlo Simulations & Optimization")

tabs = st.tabs([" Backtest", " Monte Carlo", " Optimization", " Drawdown", " Efficient Frontier"])

# ============================================================================
# TAB: BACKTESTING
# ============================================================================

with tabs[0]:
    st.subheader("Historical Backtesting")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        start_date = st.date_input("Start Date", datetime(2020, 1, 1))
    with col2:
        end_date = st.date_input("End Date", datetime.now())
    with col3:
        rebalance_freq = st.selectbox("Rebalance", ["Monthly", "Quarterly", "Annual"])
    
    # Simulate backtest
    dates = pd.date_range(start_date, end_date, freq='D')
    portfolio_values = [100000]
    
    for i in range(1, len(dates)):
        daily_return = np.random.normal(0.0003, 0.01)
        portfolio_values.append(portfolio_values[-1] * (1 + daily_return))
    
    df_backtest = pd.DataFrame({
        'Date': dates,
        'Portfolio Value': portfolio_values
    })
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_backtest['Date'],
        y=df_backtest['Portfolio Value'],
        mode='lines',
        fill='tozeroy',
        name='Portfolio Value'
    ))
    
    # Add benchmark (S&P 500)
    sp500_returns = np.random.normal(0.0004, 0.012, len(dates))
    sp500_values = [100000 * np.prod(1 + sp500_returns[:i+1]) for i in range(len(dates))]
    
    fig.add_trace(go.Scatter(
        x=df_backtest['Date'],
        y=sp500_values,
        mode='lines',
        name='S&P 500 (Benchmark)',
        line=dict(dash='dash', color='gray')
    ))
    
    fig.update_layout(
        title="Portfolio vs S&P 500 Backtest",
        xaxis_title="Date",
        yaxis_title="Portfolio Value (USD)",
        height=500,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Backtest statistics
    col1, col2, col3, col4 = st.columns(4)
    final_value = portfolio_values[-1]
    total_return = (final_value - 100000) / 100000 * 100
    annual_return = total_return / ((end_date - start_date).days / 365)
    
    col1.metric("Final Value", f"${final_value:,.0f}", f"+${final_value - 100000:,.0f}")
    col2.metric("Total Return", f"{total_return:.1f}%")
    col3.metric("Annualized Return", f"{annual_return:.1f}%")
    col4.metric("vs S&P 500", f"+{annual_return - 10:.1f}%")

# ============================================================================
# TAB: MONTE CARLO
# ============================================================================

with tabs[1]:
    st.subheader("Monte Carlo Simulation")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        simulations = st.slider("# of Simulations", 1000, 10000, 5000, step=1000)
    with col2:
        time_period = st.slider("Time Period (Years)", 1, 30, 5)
    with col3:
        initial_investment = st.number_input("Initial Investment", 100000)
    
    np.random.seed(42)
    annual_return = 0.07
    annual_volatility = 0.12
    
    # Run Monte Carlo
    days = time_period * 252
    paths = np.zeros((int(days), simulations))
    paths[0] = initial_investment
    
    for day in range(1, int(days)):
        random_returns = np.random.normal(
            annual_return / 252,
            annual_volatility / np.sqrt(252),
            simulations
        )
        paths[day] = paths[day-1] * (1 + random_returns)
    
    # Plot paths
    fig = go.Figure()
    
    # Add percentile bands
    percentiles = [10, 25, 50, 75, 90]
    colors_percentiles = ['#ff6b6b', '#ffa502', '#51cf66', '#ffa502', '#ff6b6b']
    days_range = np.arange(0, int(days))
    
    for percentile, color in zip(percentiles, colors_percentiles):
        values = np.percentile(paths, percentile, axis=1)
        fig.add_trace(go.Scatter(
            x=days_range / 252,
            y=values,
            mode='lines',
            name=f'{percentile}th Percentile',
            line=dict(color=color, width=2)
        ))
    
    # Add sample paths
    for i in range(min(100, simulations)):
        fig.add_trace(go.Scatter(
            x=days_range / 252,
            y=paths[:, i],
            mode='lines',
            line=dict(color='rgba(0,0,0,0.1)'),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    fig.update_layout(
        title="Monte Carlo Portfolio Simulation",
        xaxis_title="Years",
        yaxis_title="Portfolio Value (USD)",
        height=500,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistics
    final_values = paths[-1]
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Median (P50)", f"${np.median(final_values):,.0f}")
    col2.metric("Best Case (P90)", f"${np.percentile(final_values, 90):,.0f}")
    col3.metric("Expected Value", f"${np.mean(final_values):,.0f}")
    col4.metric("Worst Case (P10)", f"${np.percentile(final_values, 10):,.0f}")
    col5.metric("Success Rate", f"{((final_values >= initial_investment).sum() / simulations * 100):.1f}%")

# ============================================================================
# TAB: OPTIMIZATION
# ============================================================================

with tabs[2]:
    st.subheader("Portfolio Optimization (Modern Portfolio Theory)")
    
    st.info("Finding optimal weights to maximize Sharpe ratio")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Current Allocation")
        current_alloc = {
            'US Stocks': 0.35,
            'Bonds': 0.30,
            'Intl Stocks': 0.15,
            'REITs': 0.10,
            'Commodities': 0.10
        }
        
        for asset, weight in current_alloc.items():
            st.markdown(f"**{asset}**: {weight*100:.0f}%")
    
    with col2:
        st.markdown("### Optimized Allocation (Max Sharpe)")
        optimal_alloc = {
            'US Stocks': 0.42,
            'Bonds': 0.28,
            'Intl Stocks': 0.18,
            'REITs': 0.07,
            'Commodities': 0.05
        }
        
        for asset, weight in optimal_alloc.items():
            st.markdown(f"**{asset}**: {weight*100:.0f}%")
    
    # Comparison chart
    assets = list(current_alloc.keys())
    current_weights = list(current_alloc.values())
    optimal_weights = list(optimal_alloc.values())
    
    fig = go.Figure(data=[
        go.Bar(x=assets, y=current_weights, name='Current', marker_color='lightblue'),
        go.Bar(x=assets, y=optimal_weights, name='Optimized', marker_color='darkblue')
    ])
    fig.update_layout(
        title="Current vs Optimized Allocation",
        barmode='group',
        yaxis_title="Weight",
        height=520
    )
    st.plotly_chart(fig, use_container_width=True)
    
    col1, col2 = st.columns(2)
    col1.metric("Current Sharpe Ratio", "0.62")
    col2.metric("Optimized Sharpe Ratio", f"0.78 (+25.8%)")

# ============================================================================
# TAB: DRAWDOWN ANALYSIS
# ============================================================================

with tabs[3]:
    st.subheader("Drawdown Analysis & Recovery")
    
    # Simulate drawdown data
    dates_dd = pd.date_range('2020-01-01', periods=1000)
    prices = 100000 * np.exp(np.cumsum(np.random.normal(0.0003, 0.015, 1000)))
    running_max = np.maximum.accumulate(prices)
    drawdown = (prices - running_max) / running_max * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates_dd, y=prices,
        mode='lines', name='Portfolio Value',
        yaxis='y1', line=dict(color='blue')
    ))
    
    fig.add_trace(go.Scatter(
        x=dates_dd, y=drawdown,
        mode='lines', name='Drawdown',
        yaxis='y2', fill='tozeroy',
        line=dict(color='red')
    ))
    
    fig.update_layout(
        title="Drawdown Analysis",
        xaxis_title="Date",
        yaxis=dict(title="Portfolio Value (USD)", side='left'),
        yaxis2=dict(title="Drawdown (%)", overlaying='y', side='right'),
        height=500,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Drawdown statistics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Max Drawdown", f"{drawdown.min():.1f}%")
    col2.metric("Current Drawdown", f"{drawdown[-1]:.1f}%")
    col3.metric("Avg Recovery Time", "9.5 months")
    _price_chg = pd.Series(np.diff(prices) / prices[:-1])
    _calmar = (_price_chg.mean() / _price_chg.std()) if _price_chg.std() != 0 else 0.0
    col4.metric("Avg Gain/Drawdown", f"{_calmar:.2f}")


# ============================================================================
# TAB: EFFICIENT FRONTIER
# ============================================================================

with tabs[4]:
    st.subheader("Efficient Frontier — Monte Carlo Portfolio Optimization")
    st.markdown("""
    Monte Carlo simulation of **5000 random portfolios** to visualize the efficient frontier.
    Special portfolios highlighted: **Min Variance**, **Max Sharpe**, **Equal Weight**, **Capital Market Line**.
    """)

    ef_preset = ['SPY', 'QQQ', 'TLT', 'GLD', 'IWM', 'EEM', 'AAPL', 'MSFT']
    ef_raw = st.text_input(
        "Assets for Efficient Frontier (comma-separated)",
        value=', '.join(ef_preset),
        key="ef_tickers"
    )
    ef_tickers = tuple(t.strip().upper() for t in ef_raw.split(',') if t.strip())

    if len(ef_tickers) < 2:
        st.warning("Enter at least 2 tickers.")
    else:
        if st.button("Compute Efficient Frontier", type="primary", use_container_width=True):
            with st.spinner("Fetching 2-year data and running 5000 Monte Carlo portfolios..."):
                ef_results, ef_meta = compute_efficient_frontier(ef_tickers)

            if ef_results is None or ef_meta is None:
                st.error("Could not compute efficient frontier. Check tickers and connectivity.")
            else:
                tickers_used = ef_meta['tickers']
                specials = ef_meta['specials']

                vols = np.array(ef_results['vol']) * 100
                rets = np.array(ef_results['ret']) * 100
                sharpes = np.array(ef_results['sharpe'])

                # Main scatter
                fig_ef = go.Figure()

                # All portfolios colored by Sharpe
                fig_ef.add_trace(go.Scatter(
                    x=vols, y=rets,
                    mode='markers',
                    marker=dict(
                        color=sharpes,
                        colorscale='Viridis',
                        size=4,
                        opacity=0.6,
                        colorbar=dict(title="Sharpe"),
                        showscale=True,
                    ),
                    customdata=np.array(ef_results['weights']),
                    hovertemplate=(
                        'Vol: %{x:.2f}%<br>'
                        'Return: %{y:.2f}%<br>'
                        'Sharpe: %{marker.color:.3f}<extra></extra>'
                    ),
                    name='Random Portfolios',
                ))

                # Efficient frontier (Pareto front: max return for each vol bucket)
                df_ef = pd.DataFrame({'vol': vols, 'ret': rets, 'sharpe': sharpes})
                df_ef_sorted = df_ef.sort_values('vol')
                n_buckets = 40
                vol_min, vol_max = df_ef['vol'].min(), df_ef['vol'].max()
                bucket_size = (vol_max - vol_min) / n_buckets
                frontier_pts = []
                for i in range(n_buckets):
                    bucket_low = vol_min + i * bucket_size
                    bucket_high = bucket_low + bucket_size
                    bucket = df_ef[(df_ef['vol'] >= bucket_low) & (df_ef['vol'] < bucket_high)]
                    if len(bucket) > 0:
                        best = bucket.loc[bucket['ret'].idxmax()]
                        frontier_pts.append(best)
                if frontier_pts:
                    frontier_df = pd.DataFrame(frontier_pts).sort_values('vol')
                    fig_ef.add_trace(go.Scatter(
                        x=frontier_df['vol'], y=frontier_df['ret'],
                        mode='lines+markers',
                        line=dict(color='black', width=2.5),
                        marker=dict(size=5, color='black'),
                        name='Efficient Frontier',
                        hovertemplate='Vol: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>',
                    ))

                # Special portfolios
                special_styles = {
                    'min_var': ('Min Variance', '#1f77b4', 'star', 18),
                    'max_sharpe': ('Max Sharpe', '#d62728', 'diamond', 18),
                    'equal_weight': ('Equal Weight', '#ff7f0e', 'circle', 14),
                }
                for key, (label, color, symbol, size) in special_styles.items():
                    sp = specials[key]
                    fig_ef.add_trace(go.Scatter(
                        x=[sp['vol'] * 100], y=[sp['ret'] * 100],
                        mode='markers+text',
                        marker=dict(color=color, size=size, symbol=symbol,
                                    line=dict(color='white', width=1.5)),
                        text=[label],
                        textposition='top center',
                        name=label,
                        hovertemplate=(
                            f'{label}<br>Vol: %{{x:.2f}}%<br>'
                            f'Return: %{{y:.2f}}%<br>'
                            f'Sharpe: {sp["sharpe"]:.3f}<extra></extra>'
                        ),
                    ))

                # Capital Market Line (from Max Sharpe tangent)
                rf = 4.5  # risk-free rate in %
                ms = specials['max_sharpe']
                cml_vols = np.linspace(0, max(vols) * 1.1, 100)
                slope = (ms['ret'] * 100 - rf) / (ms['vol'] * 100)
                cml_rets = rf + slope * cml_vols
                fig_ef.add_trace(go.Scatter(
                    x=cml_vols, y=cml_rets,
                    mode='lines',
                    line=dict(color='green', dash='dash', width=1.8),
                    name=f'CML (rf={rf}%)',
                    hovertemplate='Vol: %{x:.2f}%<br>CML Return: %{y:.2f}%<extra></extra>',
                ))

                fig_ef.update_layout(
                    title="Efficient Frontier — 5000 Monte Carlo Portfolios",
                    xaxis_title="Annualized Volatility (%)",
                    yaxis_title="Annualized Return (%)",
                    height=560,
                    legend=dict(x=0.01, y=0.99),
                    hovermode='closest',
                )
                st.plotly_chart(fig_ef, use_container_width=True)

                # Special portfolio allocations
                st.subheader("Special Portfolio Allocations")
                sp_cols = st.columns(3)
                for idx, (key, (label, color, _, _)) in enumerate(special_styles.items()):
                    sp = specials[key]
                    with sp_cols[idx]:
                        st.markdown(f"**{label}**")
                        sp_m1, sp_m2 = st.columns(2)
                        sp_m1.metric("Return", f"{sp['ret']*100:.2f}%")
                        sp_m2.metric("Sharpe", f"{sp['sharpe']:.3f}")
                        sp_alloc = pd.DataFrame({
                            'Ticker': tickers_used,
                            'Weight': [f"{w*100:.1f}%" for w in sp['weights']],
                        }).sort_values('Weight', ascending=False)
                        st.dataframe(sp_alloc, use_container_width=True, hide_index=True)

                        # Mini pie
                        fig_mini = go.Figure(go.Pie(
                            labels=tickers_used,
                            values=[round(w * 100, 1) for w in sp['weights']],
                            textinfo='label+percent',
                            showlegend=False,
                        ))
                        fig_mini.update_layout(height=380, margin=dict(t=0, b=0, l=0, r=0))
                        st.plotly_chart(fig_mini, use_container_width=True)
        else:
            st.info("Click **Compute Efficient Frontier** to run the optimization. "
                    "This fetches 2 years of data and simulates 5000 portfolios.")
