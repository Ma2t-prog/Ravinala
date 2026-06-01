"""
GenesiX Risk Engine — Real implementation connected to GenesiXRiskEngine backend.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(page_title="Risk Engine — GenesiX", page_icon=None, layout="wide")

# ============================================================================
# CACHED DATA FUNCTIONS
# ============================================================================

@st.cache_data(ttl=3600)
def fetch_data(ticker: str, days: int) -> pd.DataFrame:
    """Fetch historical OHLCV with caching."""
    try:
        from genesix.data.market_fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        end = datetime.now()
        start = end - timedelta(days=days)
        df = fetcher.get_historical_ohlcv(ticker, start, end)
        return df
    except Exception as e:
        st.error(f"Data fetch error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def compute_risk(ticker: str, days: int, confidence: float):
    """Run full risk analysis with caching."""
    try:
        df = fetch_data(ticker, days)
        if df.empty or 'close' not in df.columns:
            return None

        from genesix.risk.risk_engine import GenesiXRiskEngine
        engine = GenesiXRiskEngine(n_simulations=5000, random_seed=42)

        returns = df['close'].pct_change().dropna()
        if len(returns) < 20:
            return None

        # Cumulative price series for drawdown
        prices = (1 + returns).cumprod()

        var_summary = engine.var_summary(returns, horizons=[1, 5, 10])
        drawdown = engine.drawdown_series(prices)
        max_dd = engine.max_drawdown(prices)
        vol_cone = engine.volatility_cone(returns)
        vol_regime = engine.volatility_regime(returns)

        # Stress test: treat the ticker as the portfolio asset.
        # Falls back to SPY shocks if ticker not in the scenario data.
        stress_weights = {ticker: 0.5, 'SPY': 0.3, 'QQQ': 0.2}
        stress = engine.stress_test_all_scenarios(stress_weights, portfolio_value=100.0)

        # VaR / CVaR at chosen confidence
        var_hist = engine.var_historical(returns, confidence=confidence, horizon=1)
        var_param = engine.var_parametric(returns, confidence=confidence, horizon=1)
        var_mc = engine.var_monte_carlo(returns, confidence=confidence, horizon=1, model='normal')
        cvar_val = engine.cvar(returns, confidence=confidence, horizon=1)

        dist_stats = engine.return_distribution(returns)

        return {
            'returns': returns,
            'prices': prices,
            'var_summary': var_summary,
            'drawdown': drawdown,
            'max_dd': max_dd,
            'vol_cone': vol_cone,
            'vol_regime': vol_regime,
            'stress': stress,
            'var_hist': var_hist,
            'var_param': var_param,
            'var_mc': var_mc,
            'cvar': cvar_val,
            'dist_stats': dist_stats,
        }
    except Exception as e:
        st.error(f"Risk computation error: {e}")
        return None


@st.cache_data(ttl=3600)
def compute_factor_analysis(ticker: str, days: int):
    """Download factor proxies and run OLS regression."""
    try:
        import yfinance as yf
        from scipy import stats as sp_stats

        end = datetime.now()
        start = end - timedelta(days=days)

        factor_tickers = {
            'Market (SPY)': 'SPY',
            'Size (IWM-SPY)': ['IWM', 'SPY'],
            'Value (IVE-IVW)': ['IVE', 'IVW'],
            'Momentum (MTUM)': 'MTUM',
            'Quality (QUAL)': 'QUAL',
        }

        # Fetch asset
        asset_data = yf.download(ticker, start=start, end=end, progress=False)['Close']
        if isinstance(asset_data, pd.DataFrame):
            asset_data = asset_data.iloc[:, 0]
        asset_returns = asset_data.pct_change().dropna()

        # Fetch factor data
        all_tickers = ['SPY', 'IWM', 'IVE', 'IVW', 'MTUM', 'QUAL']
        raw = yf.download(all_tickers, start=start, end=end, progress=False)['Close']
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw_returns = raw.pct_change().dropna()

        # Build factor matrix
        factors = pd.DataFrame(index=raw_returns.index)
        factors['Market'] = raw_returns['SPY'] if 'SPY' in raw_returns else np.nan
        if 'IWM' in raw_returns and 'SPY' in raw_returns:
            factors['Size'] = raw_returns['IWM'] - raw_returns['SPY']
        if 'IVE' in raw_returns and 'IVW' in raw_returns:
            factors['Value'] = raw_returns['IVE'] - raw_returns['IVW']
        if 'MTUM' in raw_returns:
            factors['Momentum'] = raw_returns['MTUM']
        if 'QUAL' in raw_returns:
            factors['Quality'] = raw_returns['QUAL']

        factors = factors.dropna()

        # Align with asset returns
        common_idx = asset_returns.index.intersection(factors.index)
        y = asset_returns.loc[common_idx].values
        X = factors.loc[common_idx].values
        factor_names = factors.columns.tolist()

        if len(y) < 30:
            return None

        # Add intercept
        X_with_const = np.column_stack([np.ones(len(X)), X])

        # OLS via lstsq
        coeffs, residuals, rank, sv = np.linalg.lstsq(X_with_const, y, rcond=None)
        y_hat = X_with_const @ coeffs
        ss_res = np.sum((y - y_hat) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # t-stats
        n_obs = len(y)
        n_params = X_with_const.shape[1]
        sigma2 = ss_res / max(n_obs - n_params, 1)
        cov_matrix = sigma2 * np.linalg.pinv(X_with_const.T @ X_with_const)
        se = np.sqrt(np.diag(cov_matrix))
        t_stats = coeffs / (se + 1e-12)

        alpha = coeffs[0]
        factor_betas = coeffs[1:]
        factor_t = t_stats[1:]

        # Variance explained by each factor
        factor_var_contrib = {}
        for i, fname in enumerate(factor_names):
            var_contrib = (factor_betas[i] ** 2 * np.var(factors[fname].loc[common_idx])) / max(np.var(y), 1e-12)
            factor_var_contrib[fname] = float(var_contrib * 100)

        return {
            'alpha': float(alpha * 252),  # annualized
            'alpha_tstat': float(t_stats[0]),
            'betas': {fname: float(b) for fname, b in zip(factor_names, factor_betas)},
            'tstats': {fname: float(t) for fname, t in zip(factor_names, factor_t)},
            'r2': float(r2),
            'var_contrib': factor_var_contrib,
            'n_obs': n_obs,
        }
    except Exception as e:
        return None


# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("Risk Engine")
st.markdown("Advanced portfolio risk analytics powered by **GenesiXRiskEngine**.")

# ============================================================================
# SIDEBAR INPUTS
# ============================================================================

with st.sidebar:
    st.header("Parameters")
    ticker = st.text_input("Ticker", value="SPY", help="Any equity, ETF, or index ticker").upper().strip()
    days = st.selectbox("Lookback Period", [252, 504, 756, 1260], index=1,
                        format_func=lambda d: {252: '1 Year', 504: '2 Years', 756: '3 Years', 1260: '5 Years'}[d])
    confidence = st.slider("VaR Confidence Level", 0.90, 0.99, 0.95, 0.01,
                           format="%.2f")
    run_btn = st.button("Run Analysis", type="primary", use_container_width=True)

st.info(f"Showing risk analysis for **{ticker}** | Lookback: **{days} days** | Confidence: **{confidence:.0%}**")

# ============================================================================
# TABS
# ============================================================================

tab_var, tab_dd, tab_vol, tab_stress, tab_factor = st.tabs([
    "VaR / CVaR",
    "Drawdown",
    "Volatility Cone",
    "Stress Tests",
    "Factor Analysis",
])

# ============================================================================
# LOAD DATA
# ============================================================================

with st.spinner(f"Loading data for {ticker}..."):
    risk_data = compute_risk(ticker, days, confidence)

if risk_data is None:
    st.error(f"Could not load or compute risk data for **{ticker}**. Check the ticker and try again.")
    st.stop()

returns = risk_data['returns']
prices = risk_data['prices']
dist_stats = risk_data['dist_stats']
var_summary = risk_data['var_summary']

# ============================================================================
# HEADER METRICS
# ============================================================================

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric(f"VaR {confidence:.0%} (Hist.)", f"{risk_data['var_hist']*100:.2f}%")
m2.metric(f"VaR {confidence:.0%} (Param.)", f"{risk_data['var_param']*100:.2f}%")
m3.metric(f"VaR {confidence:.0%} (MC)", f"{risk_data['var_mc']*100:.2f}%")
m4.metric(f"CVaR {confidence:.0%}", f"{risk_data['cvar']*100:.2f}%")
m5.metric("Max Drawdown", f"{risk_data['max_dd']*100:.1f}%")
vr = risk_data['vol_regime']
m6.metric("Vol Regime", vr['regime'].upper(),
          f"{vr['current_vol_annualized']*100:.1f}% p.a.")

st.divider()

# ============================================================================
# TAB 1: VaR / CVaR
# ============================================================================

with tab_var:
    st.subheader("Return Distribution with VaR / CVaR Markers")

    col_chart, col_table = st.columns([3, 1])

    with col_chart:
        var_val = risk_data['var_hist']
        cvar_val = risk_data['cvar']

        hist_vals, bin_edges = np.histogram(returns.values, bins=80)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        fig_dist = go.Figure()
        colors = ['#d62728' if bc < -var_val else '#2ca02c' for bc in bin_centers]
        fig_dist.add_trace(go.Bar(
            x=bin_centers * 100,
            y=hist_vals,
            marker_color=colors,
            name='Return Distribution',
            hovertemplate='Return: %{x:.2f}%<br>Count: %{y}<extra></extra>',
        ))

        # Normal overlay
        mu = dist_stats['mean']
        sigma = dist_stats['std']
        x_line = np.linspace(returns.min(), returns.max(), 300)
        from scipy.stats import norm
        y_line = norm.pdf(x_line, mu, sigma) * len(returns) * (bin_edges[1] - bin_edges[0])
        fig_dist.add_trace(go.Scatter(
            x=x_line * 100, y=y_line,
            mode='lines', line=dict(color='black', width=2, dash='dash'),
            name='Normal Fit',
        ))

        fig_dist.add_vline(x=-var_val * 100, line_color='orange', line_dash='dash', line_width=2,
                           annotation_text=f"VaR {confidence:.0%}: {var_val*100:.2f}%",
                           annotation_position="top right")
        fig_dist.add_vline(x=-cvar_val * 100, line_color='red', line_dash='dot', line_width=2,
                           annotation_text=f"CVaR {confidence:.0%}: {cvar_val*100:.2f}%",
                           annotation_position="top left")

        fig_dist.update_layout(
            title=f"{ticker} Daily Return Distribution",
            xaxis_title="Daily Return (%)",
            yaxis_title="Frequency",
            height=520,
            showlegend=True,
        )
        st.plotly_chart(fig_dist, use_container_width=True)

        # Distribution stats
        st.caption(f"Annualized Return: **{dist_stats['annualized_return']*100:.1f}%** | "
                   f"Ann. Volatility: **{dist_stats['annualized_volatility']*100:.1f}%** | "
                   f"Skewness: **{dist_stats['skewness']:.3f}** | "
                   f"Kurtosis (excess): **{dist_stats['kurtosis']:.3f}** | "
                   f"Normal? **{'Yes' if dist_stats['normality_test']['is_normal'] else 'No'}** "
                   f"(JB p={dist_stats['normality_test']['jarque_bera_pval']:.4f})")

    with col_table:
        st.subheader("VaR Summary Table")
        if not var_summary.empty:
            styled = var_summary.style.format("{:.4f}")
            st.dataframe(var_summary.applymap(lambda x: f"{x*100:.3f}%"),
                         use_container_width=True)
        else:
            st.info("No VaR summary available.")

        st.markdown("---")
        st.markdown("**Percentiles**")
        p_data = dist_stats['percentiles']
        p_df = pd.DataFrame({
            'Percentile': ['1%', '5%', '10%', '25%', '50%', '75%', '90%', '95%', '99%'],
            'Value': [f"{v*100:.2f}%" for v in p_data.values()],
        })
        st.dataframe(p_df, use_container_width=True, hide_index=True)


# ============================================================================
# TAB 2: DRAWDOWN
# ============================================================================

with tab_dd:
    st.subheader("Drawdown Analysis")

    dd_series = risk_data['drawdown']

    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=dd_series.index,
        y=dd_series.values * 100,
        fill='tozeroy',
        fillcolor='rgba(214,39,40,0.25)',
        line=dict(color='#d62728', width=1.2),
        name='Drawdown (%)',
        hovertemplate='%{x|%Y-%m-%d}<br>Drawdown: %{y:.2f}%<extra></extra>',
    ))

    max_dd_idx = dd_series.idxmin()
    fig_dd.add_annotation(
        x=max_dd_idx,
        y=dd_series.min() * 100,
        text=f"Max DD: {dd_series.min()*100:.1f}%",
        showarrow=True, arrowhead=2, arrowcolor='red',
        font=dict(color='red', size=12),
    )

    fig_dd.update_layout(
        title=f"{ticker} Drawdown Series",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        height=520,
        hovermode='x unified',
    )
    st.plotly_chart(fig_dd, use_container_width=True)

    # Price chart alongside
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(
        x=prices.index,
        y=prices.values,
        mode='lines',
        line=dict(color='#1f77b4', width=2),
        name='Cumulative Return (rebased to 1)',
        hovertemplate='%{x|%Y-%m-%d}<br>Value: %{y:.4f}<extra></extra>',
    ))
    fig_price.update_layout(
        title=f"{ticker} Cumulative Return",
        xaxis_title="Date",
        yaxis_title="Portfolio Value (rebased)",
        height=380,
        hovermode='x unified',
    )
    st.plotly_chart(fig_price, use_container_width=True)

    dd_m1, dd_m2, dd_m3 = st.columns(3)
    dd_m1.metric("Max Drawdown", f"{risk_data['max_dd']*100:.2f}%")
    dd_m2.metric("Current Drawdown", f"{dd_series.iloc[-1]*100:.2f}%")
    dd_m3.metric("Avg Daily Return", f"{returns.mean()*100:.4f}%")


# ============================================================================
# TAB 3: VOLATILITY CONE
# ============================================================================

with tab_vol:
    st.subheader("Volatility Cone")
    st.markdown("Rolling realized volatility across different window lengths. "
                "The **current** level is plotted against historical min/max/percentiles.")

    vol_cone = risk_data['vol_cone']

    if vol_cone is not None and not vol_cone.empty:
        horizons_plot = vol_cone.index.tolist()
        labels = [f"{int(h)}d" for h in horizons_plot]

        fig_cone = go.Figure()

        # Shaded band: min to max
        fig_cone.add_trace(go.Scatter(
            x=labels + labels[::-1],
            y=list(vol_cone['max'].values * 100) + list(vol_cone['min'].values[::-1] * 100),
            fill='toself',
            fillcolor='rgba(31,119,180,0.1)',
            line=dict(color='rgba(255,255,255,0)'),
            name='Min-Max Band',
            showlegend=True,
        ))

        # IQR band
        fig_cone.add_trace(go.Scatter(
            x=labels + labels[::-1],
            y=list(vol_cone['p75'].values * 100) + list(vol_cone['p25'].values[::-1] * 100),
            fill='toself',
            fillcolor='rgba(31,119,180,0.25)',
            line=dict(color='rgba(255,255,255,0)'),
            name='IQR (25th-75th pct.)',
        ))

        # Median
        fig_cone.add_trace(go.Scatter(
            x=labels, y=vol_cone['median'].values * 100,
            mode='lines+markers', line=dict(color='steelblue', width=2),
            name='Median',
        ))

        # Current
        fig_cone.add_trace(go.Scatter(
            x=labels, y=vol_cone['current'].values * 100,
            mode='lines+markers',
            line=dict(color='orange', width=2.5, dash='dash'),
            marker=dict(size=8),
            name='Current',
        ))

        fig_cone.update_layout(
            title=f"{ticker} Volatility Cone (Annualized)",
            xaxis_title="Rolling Window",
            yaxis_title="Annualized Volatility (%)",
            height=520,
            hovermode='x unified',
        )
        st.plotly_chart(fig_cone, use_container_width=True)

        # Table
        cone_display = vol_cone.copy()
        cone_display.index = labels
        cone_display = (cone_display * 100).round(2)
        cone_display.columns = [c.capitalize() for c in cone_display.columns]
        st.dataframe(cone_display.style.format("{:.2f}%"), use_container_width=True)

        # Regime info
        vr = risk_data['vol_regime']
        regime_colors = {
            'low': 'green', 'normal': 'blue', 'elevated': 'orange',
            'high': 'red', 'extreme': 'darkred',
        }
        color = regime_colors.get(vr['regime'], 'blue')
        st.markdown(
            f"**Volatility Regime:** :{color}[{vr['regime'].upper()}] | "
            f"Current Ann. Vol: **{vr['current_vol_annualized']*100:.1f}%** | "
            f"Percentile (1Y): **{vr['percentile_1y']:.0f}th** | "
            f"Trend: **{vr['vol_trend'].upper()}**"
        )
    else:
        st.warning("Insufficient data for volatility cone computation.")


# ============================================================================
# TAB 4: STRESS TESTS
# ============================================================================

with tab_stress:
    st.subheader("Historical Stress Test Scenarios")
    st.markdown("Impact of major historical crises on a **100% equity** single-asset portfolio.")

    stress_df = risk_data['stress']

    if stress_df is not None and not stress_df.empty:
        # Bar chart
        stress_sorted = stress_df.sort_values('Impact %')
        colors_bar = ['#d62728' if v < 0 else '#2ca02c' for v in stress_sorted['Impact %']]

        fig_stress = go.Figure(go.Bar(
            x=stress_sorted['Impact %'],
            y=stress_sorted['Scenario'],
            orientation='h',
            marker_color=colors_bar,
            hovertemplate='<b>%{y}</b><br>Impact: %{x:.1f}%<extra></extra>',
        ))
        fig_stress.update_layout(
            title="Stress Test: Portfolio Impact (%)",
            xaxis_title="Portfolio Impact (%)",
            height=max(400, len(stress_sorted) * 28),
            xaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black'),
        )
        st.plotly_chart(fig_stress, use_container_width=True)

        # Worst 5
        st.markdown("**Top 5 Worst Scenarios**")
        worst5 = stress_df.sort_values('Impact %').head(5)[['Scenario', 'Impact %', 'Impact Value', 'Worst Asset']]
        worst5['Impact %'] = worst5['Impact %'].map(lambda x: f"{x:.1f}%")
        worst5['Impact Value'] = worst5['Impact Value'].map(lambda x: f"{x:.1f}")
        st.dataframe(worst5, use_container_width=True, hide_index=True)
    else:
        st.info("Stress test data unavailable. This requires the HISTORICAL_STRESS_EVENTS constant to be populated.")


# ============================================================================
# TAB 5: FACTOR ANALYSIS
# ============================================================================

with tab_factor:
    st.subheader("Factor Risk Decomposition (Fama-French Style)")
    st.markdown("""
    OLS regression of asset returns on factor proxies:
    - **Market**: SPY returns
    - **Size**: IWM − SPY (small-cap minus large-cap)
    - **Value**: IVE − IVW (value minus growth)
    - **Momentum**: MTUM
    - **Quality**: QUAL
    """)

    with st.spinner("Running factor regression..."):
        factor_result = compute_factor_analysis(ticker, days)

    if factor_result:
        fa1, fa2, fa3, fa4 = st.columns(4)
        fa1.metric("Alpha (ann.)", f"{factor_result['alpha']*100:.2f}%",
                   help="Annualized alpha (intercept)")
        fa2.metric("Alpha t-stat", f"{factor_result['alpha_tstat']:.2f}",
                   help="|t| > 2 suggests statistical significance")
        fa3.metric("R²", f"{factor_result['r2']*100:.1f}%",
                   help="% of variance explained by factors")
        fa4.metric("Observations", str(factor_result['n_obs']))

        st.divider()

        fc1, fc2 = st.columns(2)

        with fc1:
            st.markdown("**Factor Betas (Exposures)**")
            betas = factor_result['betas']
            tstats = factor_result['tstats']
            beta_df = pd.DataFrame({
                'Factor': list(betas.keys()),
                'Beta': [f"{v:.4f}" for v in betas.values()],
                't-stat': [f"{tstats[k]:.2f}" for k in betas.keys()],
                'Significant': ['Yes' if abs(tstats[k]) > 2 else 'No' for k in betas.keys()],
            })
            st.dataframe(beta_df, use_container_width=True, hide_index=True)

            # Beta bar chart
            fig_beta = go.Figure(go.Bar(
                x=list(betas.keys()),
                y=list(betas.values()),
                marker_color=['#2ca02c' if v > 0 else '#d62728' for v in betas.values()],
                hovertemplate='%{x}: %{y:.4f}<extra></extra>',
            ))
            fig_beta.update_layout(
                title="Factor Betas",
                yaxis_title="Beta",
                height=520,
                xaxis_title="Factor",
            )
            st.plotly_chart(fig_beta, use_container_width=True)

        with fc2:
            st.markdown("**Variance Explained by Factor (%)**")
            var_contrib = factor_result['var_contrib']
            unexplained = max(0, 100 - sum(var_contrib.values()))
            pie_labels = list(var_contrib.keys()) + ['Idiosyncratic']
            pie_values = list(var_contrib.values()) + [unexplained]

            fig_pie = go.Figure(go.Pie(
                labels=pie_labels,
                values=[round(v, 2) for v in pie_values],
                textinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>%{value:.1f}%<extra></extra>',
            ))
            fig_pie.update_layout(
                title=f"R² = {factor_result['r2']*100:.1f}% — Variance Attribution",
                height=520,
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning(
            "Factor analysis unavailable. This may be due to missing factor ETF data "
            "(IVE, IVW, MTUM, QUAL) or insufficient internet connectivity. "
            "Ensure yfinance can access these tickers."
        )
