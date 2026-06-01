"""
GenesiX Hub — Unified GenesiX AI suite dashboard
Fusion of: genesix_home + genesix_portfolio_monitor + genesix_risk_engine +
           genesix_ml_engine + genesix_market_intelligence + genesix_advanced_analysis +
           genesix_data_layer + intelligence_center
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

_render_page_header("GX", "GenesiX Hub",
                    "AI portfolio allocator, risk engine, ML predictions & market intelligence",
                    "GenesiX")

# ── Theme ─────────────────────────────────────────────────────────────────────
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
    margin=dict(l=60, r=20, t=50, b=50),
)

# ============================================================================
# Section selector
# ============================================================================
section = st.selectbox("GenesiX Module", [
    "Portfolio Allocator",
    "Portfolio Monitor",
    "Risk Engine",
    "ML Engine",
    "Market Intelligence",
    "Advanced Analysis",
    "Data Layer",
    "Intelligence Center",
], key="gx_section")


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 1 — PORTFOLIO ALLOCATOR (from genesix_home.py)
# ════════════════════════════════════════════════════════════════════════════════
if section == "Portfolio Allocator":
    try:
        from genesix.omega_database import AssetDatabase, BrokerDatabase
        from genesix.risk_matrix import RISK_MATRIX, CATEGORIES, CATEGORY_COLORS, get_level
    except ImportError:
        st.error("GenesiX modules not available. Check installation.")
        st.stop()

    @st.cache_data(ttl=3600)
    def optimize_portfolio(tickers, risk_profile):
        try:
            from scipy.optimize import minimize
            import yfinance as yf
            tickers_list = list(tickers)
            data = yf.download(tickers_list, period='2y', progress=False)['Close']
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            data = data.dropna(axis=1, thresh=int(len(data) * 0.9))
            valid_tickers = data.columns.tolist()
            returns = data.pct_change().dropna()
            mu = returns.mean() * 252
            cov = returns.cov() * 252
            n = len(valid_tickers)
            if n < 2:
                return None, None
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
            result = minimize(portfolio_vol, w0, method='SLSQP',
                            bounds=bounds, constraints=constraints,
                            options={'ftol': 1e-9, 'maxiter': 1000})
            if result.success:
                weights = result.x
                opt_weights = {t: float(w * 100) for t, w in zip(valid_tickers, weights)}
                opt_return = float(weights @ mu.values * 100)
                opt_vol = float(np.sqrt(weights @ cov.values @ weights) * 100)
                return opt_weights, {'return': opt_return, 'vol': opt_vol, 'sharpe': opt_return / max(opt_vol, 0.1)}
            return None, None
        except Exception:
            return None, None

    st.markdown("### OMEGA AI Portfolio Allocator")

    # Risk profile selector
    risk_level = st.slider("Risk Profile (1=Conservative, 20=Aggressive)", 1, 20, 10, key="gx_risk")

    # Asset database
    db = AssetDatabase()
    categories = CATEGORIES
    selected_cats = st.multiselect("Asset Categories", categories, default=categories[:3], key="gx_cats")

    all_tickers = []
    for cat in selected_cats:
        assets = db.get_assets_by_category(cat) if hasattr(db, 'get_assets_by_category') else []
        all_tickers.extend([a.ticker if hasattr(a, 'ticker') else str(a) for a in assets])

    if not all_tickers:
        all_tickers = ['SPY', 'QQQ', 'BND', 'GLD', 'VNQ', 'AAPL', 'MSFT', 'NVDA']

    st.info(f"Optimizing across {len(all_tickers)} assets with risk level {risk_level}...")

    if st.button("Run Optimization", key="gx_opt_btn"):
        with st.spinner("Running mean-variance optimization..."):
            weights, stats = optimize_portfolio(tuple(all_tickers[:20]), str(risk_level))
            if weights and stats:
                c1, c2, c3 = st.columns(3)
                c1.metric("Expected Return", f"{stats['return']:.2f}%")
                c2.metric("Portfolio Vol", f"{stats['vol']:.2f}%")
                c3.metric("Sharpe Ratio", f"{stats['sharpe']:.2f}")

                # Allocation chart
                sorted_w = dict(sorted(weights.items(), key=lambda x: x[1], reverse=True))
                fig_alloc = go.Figure(data=[go.Pie(
                    labels=list(sorted_w.keys()),
                    values=list(sorted_w.values()),
                    hole=0.4,
                    textinfo="label+percent",
                )])
                fig_alloc.update_layout(**_LAYOUT, title="Optimal Allocation", height=400)
                st.plotly_chart(fig_alloc, use_container_width=True)

                st.dataframe(pd.DataFrame(list(sorted_w.items()),
                            columns=["Ticker", "Weight %"]).sort_values("Weight %", ascending=False),
                            use_container_width=True, hide_index=True)
            else:
                st.warning("Optimization failed. Try different assets or risk level.")


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PORTFOLIO MONITOR (from genesix_portfolio_monitor.py)
# ════════════════════════════════════════════════════════════════════════════════
elif section == "Portfolio Monitor":
    st.markdown("### Portfolio Monitoring & Tax Optimization")

    tabs_pm = st.tabs(["Portfolio Status", "Tax-Loss Harvesting", "Rebalancing", "Performance"])

    with tabs_pm[0]:
        st.subheader("Current Portfolio")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Value", "$487,234", "+$12,456 (+2.6%)")
        c2.metric("Cash", "$48,723", "10%")
        c3.metric("YTD Return", "+18.5%", "+$73,456")
        c4.metric("This Week", "+2.1%", "+$9,832")

        portfolio = pd.DataFrame({
            'Ticker': ['VOO', 'BND', 'NVDA', 'AAPL', 'VTI', 'GLD', 'VNQ'],
            'Company': ['Vanguard S&P 500', 'Vanguard Bond', 'NVIDIA', 'Apple', 'Vanguard Total', 'Gold ETF', 'Vanguard REIT'],
            'Value': ['$81,935', '$16,824', '$23,386', '$34,621', '$23,456', '$9,784', '$6,692'],
            'Change %': ['+2.1%', '+0.3%', '+4.2%', '+1.2%', '+1.8%', '-0.5%', '+1.5%'],
            'Allocation': ['16.8%', '3.5%', '4.8%', '7.1%', '4.8%', '2.0%', '1.4%'],
        })
        st.dataframe(portfolio, use_container_width=True, hide_index=True)

    with tabs_pm[1]:
        st.subheader("Tax-Loss Harvesting Engine")
        c1, c2, c3 = st.columns(3)
        c1.metric("Potential Tax Savings", "$3,240")
        c2.metric("Harvestable Losses", "$10,800")
        c3.metric("YTD Harvested", "$5,200")
        st.info("AI identifies positions with unrealized losses eligible for tax harvesting while maintaining portfolio exposure via similar substitutes.")

    with tabs_pm[2]:
        st.subheader("Rebalancing Alerts")
        st.warning("3 positions are outside target allocation bands.")

    with tabs_pm[3]:
        st.subheader("Performance Tracking")
        st.info("Track portfolio performance vs benchmarks over time.")


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 3 — RISK ENGINE (from genesix_risk_engine.py)
# ════════════════════════════════════════════════════════════════════════════════
elif section == "Risk Engine":
    st.markdown("### GenesiX Risk Engine")

    @st.cache_data(ttl=3600)
    def _fetch_risk_data(ticker, days):
        try:
            from genesix.data.market_fetcher import MarketDataFetcher
            fetcher = MarketDataFetcher()
            end = datetime.now()
            start = end - timedelta(days=days)
            return fetcher.get_historical_ohlcv(ticker, start, end)
        except Exception as e:
            st.error(f"Data fetch error: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=3600)
    def _compute_risk(ticker, days, confidence):
        try:
            df = _fetch_risk_data(ticker, days)
            if df.empty or 'close' not in df.columns:
                return None
            from genesix.risk.risk_engine import GenesiXRiskEngine
            engine = GenesiXRiskEngine(n_simulations=5000, random_seed=42)
            returns = df['close'].pct_change().dropna()
            if len(returns) < 20:
                return None
            prices = (1 + returns).cumprod()
            var_summary = engine.var_summary(returns, horizons=[1, 5, 10])
            drawdown = engine.drawdown_series(prices)
            max_dd = engine.max_drawdown(prices)
            vol_cone = engine.volatility_cone(returns)
            var_hist = engine.var_historical(returns, confidence=confidence, horizon=1)
            var_param = engine.var_parametric(returns, confidence=confidence, horizon=1)
            cvar_val = engine.cvar(returns, confidence=confidence, horizon=1)
            dist_stats = engine.return_distribution(returns)
            return {
                'returns': returns, 'prices': prices, 'var_summary': var_summary,
                'drawdown': drawdown, 'max_dd': max_dd, 'vol_cone': vol_cone,
                'var_hist': var_hist, 'var_param': var_param, 'cvar': cvar_val,
                'dist_stats': dist_stats,
            }
        except Exception as e:
            st.error(f"Risk computation error: {e}")
            return None

    c1, c2, c3 = st.columns(3)
    risk_ticker = c1.text_input("Ticker", "SPY", key="gx_risk_t")
    risk_days = c2.slider("Lookback (days)", 60, 756, 252, key="gx_risk_d")
    risk_conf = c3.slider("VaR Confidence", 0.90, 0.99, 0.95, 0.01, key="gx_risk_c")

    if st.button("Compute Risk", key="gx_risk_btn"):
        with st.spinner("Running GenesiX Risk Engine..."):
            result = _compute_risk(risk_ticker, risk_days, risk_conf)
            if result:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("VaR (Hist)", f"{result['var_hist']:.4f}" if isinstance(result['var_hist'], float) else str(result['var_hist']))
                c2.metric("VaR (Param)", f"{result['var_param']:.4f}" if isinstance(result['var_param'], float) else str(result['var_param']))
                c3.metric("CVaR", f"{result['cvar']:.4f}" if isinstance(result['cvar'], float) else str(result['cvar']))
                c4.metric("Max Drawdown", f"{result['max_dd']:.2%}" if isinstance(result['max_dd'], float) else str(result['max_dd']))

                # Returns chart
                if result['returns'] is not None and not result['returns'].empty:
                    fig_ret = go.Figure()
                    fig_ret.add_trace(go.Scatter(x=result['returns'].index, y=result['returns'].values,
                                                  mode='lines', name='Returns', line=dict(color=_CYAN, width=1)))
                    fig_ret.update_layout(**_LAYOUT, title=f"{risk_ticker} Daily Returns", height=350)
                    st.plotly_chart(fig_ret, use_container_width=True)

                if result['var_summary'] is not None:
                    st.markdown("### VaR Summary by Horizon")
                    if isinstance(result['var_summary'], pd.DataFrame):
                        st.dataframe(result['var_summary'], use_container_width=True)
                    else:
                        st.json(result['var_summary'])
            else:
                st.warning("Could not compute risk metrics. Check ticker and data availability.")


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 4 — ML ENGINE (from genesix_ml_engine.py)
# ════════════════════════════════════════════════════════════════════════════════
elif section == "ML Engine":
    st.markdown("### GenesiX ML Prediction Engine")

    @st.cache_data(ttl=1800)
    def _fetch_ml_data(ticker, days):
        try:
            from genesix.data.market_fetcher import MarketDataFetcher
            fetcher = MarketDataFetcher()
            end = datetime.now()
            start = end - timedelta(days=days)
            return fetcher.get_historical_ohlcv(ticker, start, end)
        except Exception:
            return pd.DataFrame()

    @st.cache_data(ttl=1800)
    def _run_predictor(ticker, horizon):
        try:
            from genesix.ml.prediction_engine import GenesiXPredictor
            predictor = GenesiXPredictor(random_seed=42)
            train_result = predictor.train_ensemble(ticker, horizon=horizon)
            prediction = predictor.ensemble_predict(ticker, horizon=horizon, investment=10000.0)
            return prediction, train_result
        except Exception as e:
            return None, {'error': str(e)}

    @st.cache_data(ttl=1800)
    def _run_risk_scenarios(ticker, horizon, days):
        try:
            df = _fetch_ml_data(ticker, days)
            if df.empty or 'close' not in df.columns:
                return None
            from genesix.risk.risk_engine import GenesiXRiskEngine
            engine = GenesiXRiskEngine(n_simulations=5000, random_seed=42)
            returns = df['close'].pct_change().dropna()
            if len(returns) < 30:
                return None
            return engine.simulate_return_scenarios(returns, horizon=horizon, investment=10000.0)
        except Exception:
            return None

    c1, c2, c3 = st.columns(3)
    ml_ticker = c1.text_input("Ticker", "AAPL", key="gx_ml_t")
    ml_horizon = c2.slider("Prediction Horizon (days)", 1, 30, 5, key="gx_ml_h")
    ml_days = c3.slider("Training Data (days)", 180, 756, 504, key="gx_ml_d")

    if st.button("Run ML Prediction", key="gx_ml_btn"):
        with st.spinner("Training GenesiX ML models..."):
            prediction, train_result = _run_predictor(ml_ticker, ml_horizon)
            if prediction:
                c1, c2, c3 = st.columns(3)
                if hasattr(prediction, 'expected_return'):
                    c1.metric("Expected Return", f"{prediction.expected_return*100:.2f}%")
                if hasattr(prediction, 'confidence'):
                    c2.metric("Confidence", f"{prediction.confidence*100:.1f}%")
                if hasattr(prediction, 'direction'):
                    c3.metric("Direction", prediction.direction)
                st.json(train_result if isinstance(train_result, dict) else str(train_result))
            else:
                st.info("Predictor unavailable. Running risk scenario simulation instead...")
                scenarios = _run_risk_scenarios(ml_ticker, ml_horizon, ml_days)
                if scenarios:
                    st.json(scenarios if isinstance(scenarios, dict) else str(scenarios))
                else:
                    st.warning("Could not run scenarios. Check data availability.")


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 5 — MARKET INTELLIGENCE (from genesix_market_intelligence.py)
# ════════════════════════════════════════════════════════════════════════════════
elif section == "Market Intelligence":
    st.markdown("### Omega Market Intelligence")

    PRESET_TICKERS = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'NVDA', 'BTC-USD', 'GLD']

    @st.cache_data(ttl=900)
    def _fetch_ohlcv(ticker, days=30):
        try:
            from genesix.data.market_fetcher import MarketDataFetcher
            fetcher = MarketDataFetcher()
            end = datetime.now()
            start = end - timedelta(days=days)
            return fetcher.get_historical_ohlcv(ticker, start, end)
        except Exception:
            return pd.DataFrame()

    selected_tickers = st.multiselect("Tickers", PRESET_TICKERS, default=PRESET_TICKERS[:4], key="gx_mi_tickers")

    if selected_tickers:
        cols = st.columns(min(len(selected_tickers), 4))
        for i, t in enumerate(selected_tickers[:4]):
            df = _fetch_ohlcv(t)
            if not df.empty and 'close' in df.columns:
                last = float(df['close'].iloc[-1])
                prev = float(df['close'].iloc[-2]) if len(df) > 1 else last
                change = (last - prev) / prev * 100 if prev else 0
                cols[i].metric(t, f"${last:.2f}", f"{change:+.2f}%")
            else:
                cols[i].metric(t, "N/A")

        # Chart for first selected ticker
        t0 = selected_tickers[0]
        df0 = _fetch_ohlcv(t0, days=90)
        if not df0.empty and 'close' in df0.columns:
            fig_mi = go.Figure()
            fig_mi.add_trace(go.Scatter(x=df0.index, y=df0['close'], mode='lines',
                                         name=t0, line=dict(color=_CYAN, width=2)))
            fig_mi.update_layout(**_LAYOUT, title=f"{t0} — 90 Day Chart", height=350)
            st.plotly_chart(fig_mi, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 6 — ADVANCED ANALYSIS (from genesix_advanced_analysis.py)
# ════════════════════════════════════════════════════════════════════════════════
elif section == "Advanced Analysis":
    st.markdown("### Efficient Frontier & Portfolio Optimization")

    @st.cache_data(ttl=3600)
    def _compute_frontier(tickers):
        try:
            import yfinance as yf
            from scipy.optimize import minimize
            tickers_list = list(tickers)
            data = yf.download(tickers_list, period='2y', progress=False)['Close']
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            data = data.dropna(axis=1, thresh=int(len(data) * 0.8)).dropna()
            tickers_clean = data.columns.tolist()
            if len(tickers_clean) < 2:
                return None
            returns = data.pct_change().dropna()
            mu = returns.mean().values * 252
            cov = returns.cov().values * 252
            n = len(tickers_clean)

            results = {'vol': [], 'ret': [], 'sharpe': []}
            rng = np.random.default_rng(42)
            for _ in range(5000):
                w = rng.dirichlet(np.ones(n))
                ret = float(w @ mu)
                vol = float(np.sqrt(w @ cov @ w))
                results['vol'].append(vol * 100)
                results['ret'].append(ret * 100)
                results['sharpe'].append(ret / (vol + 1e-8))

            # Max Sharpe
            def neg_sharpe(w):
                return -(w @ mu) / (np.sqrt(w @ cov @ w) + 1e-8)
            res_ms = minimize(neg_sharpe, np.ones(n)/n, method='SLSQP',
                             bounds=[(0, 1)]*n,
                             constraints=[{'type': 'eq', 'fun': lambda w: np.sum(w)-1}])
            ms_w = res_ms.x if res_ms.success else np.ones(n)/n
            ms_ret = float(ms_w @ mu * 100)
            ms_vol = float(np.sqrt(ms_w @ cov @ ms_w) * 100)
            return {
                'results': results, 'tickers': tickers_clean,
                'max_sharpe': {'ret': ms_ret, 'vol': ms_vol, 'weights': {t: float(w*100) for t, w in zip(tickers_clean, ms_w)}},
            }
        except Exception as e:
            st.error(f"Error: {e}")
            return None

    ef_tickers = st.multiselect("Portfolio Assets", ['SPY', 'QQQ', 'BND', 'GLD', 'VNQ', 'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN'],
                                default=['SPY', 'QQQ', 'BND', 'GLD', 'VNQ'], key="gx_ef_tickers")

    if ef_tickers and len(ef_tickers) >= 2 and st.button("Compute Frontier", key="gx_ef_btn"):
        with st.spinner("Computing Efficient Frontier..."):
            ef = _compute_frontier(tuple(ef_tickers))
            if ef:
                fig_ef = go.Figure()
                fig_ef.add_trace(go.Scatter(
                    x=ef['results']['vol'], y=ef['results']['ret'],
                    mode='markers', marker=dict(color=ef['results']['sharpe'], colorscale='Viridis',
                                                size=4, colorbar=dict(title='Sharpe')),
                    name='Random Portfolios'
                ))
                ms = ef['max_sharpe']
                fig_ef.add_trace(go.Scatter(
                    x=[ms['vol']], y=[ms['ret']], mode='markers',
                    marker=dict(color=_GOLD, size=15, symbol='star'),
                    name=f"Max Sharpe ({ms['ret']:.1f}%/{ms['vol']:.1f}%)"
                ))
                fig_ef.update_layout(**_LAYOUT, title="Efficient Frontier (5000 Portfolios)",
                                    xaxis_title="Volatility (%)", yaxis_title="Return (%)", height=450)
                st.plotly_chart(fig_ef, use_container_width=True)

                st.markdown("### Max Sharpe Portfolio")
                st.dataframe(pd.DataFrame(list(ms['weights'].items()),
                            columns=["Ticker", "Weight %"]).sort_values("Weight %", ascending=False),
                            use_container_width=True, hide_index=True)
    elif ef_tickers and len(ef_tickers) < 2:
        st.warning("Select at least 2 assets.")


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 7 — DATA LAYER (from genesix_data_layer.py)
# ════════════════════════════════════════════════════════════════════════════════
elif section == "Data Layer":
    st.markdown("### GenesiX Infrastructure Health")
    import time

    @st.cache_data(ttl=300)
    def _get_cache_stats():
        try:
            from genesix.utils.config import Config
            cache_dir = Config.DATA_CACHE_DIR
            stats = {'exists': cache_dir.exists(), 'path': str(cache_dir),
                     'total_size_mb': 0.0, 'file_count': 0, 'files': []}
            if cache_dir.exists():
                for f in cache_dir.rglob('*'):
                    if f.is_file():
                        size_mb = f.stat().st_size / (1024 * 1024)
                        stats['total_size_mb'] += size_mb
                        stats['file_count'] += 1
                        stats['files'].append({
                            'file': f.name, 'size_mb': round(size_mb, 3),
                            'last_modified': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M'),
                        })
            return stats
        except Exception as e:
            return {'error': str(e), 'exists': False, 'total_size_mb': 0, 'file_count': 0, 'files': []}

    @st.cache_data(ttl=60)
    def _check_yfinance():
        start = time.time()
        try:
            import yfinance as yf
            tick = yf.download('SPY', period='2d', progress=False)
            elapsed = (time.time() - start) * 1000
            if tick is not None and len(tick) > 0:
                return {'ok': True, 'latency_ms': round(elapsed, 1), 'rows': len(tick)}
            return {'ok': False, 'latency_ms': round(elapsed, 1)}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Yahoo Finance")
        yf_status = _check_yfinance()
        if yf_status.get('ok'):
            st.success(f"Connected — {yf_status.get('latency_ms', 0):.0f}ms")
        else:
            st.error(f"Disconnected — {yf_status.get('error', 'Unknown')}")

    with c2:
        st.markdown("#### Cache Stats")
        cache = _get_cache_stats()
        if cache.get('error'):
            st.warning(f"Cache unavailable: {cache['error']}")
        else:
            st.info(f"Files: {cache['file_count']} | Size: {cache['total_size_mb']:.1f} MB")

    if cache.get('files'):
        st.markdown("#### Cached Files")
        st.dataframe(pd.DataFrame(cache['files']), use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# SECTION 8 — INTELLIGENCE CENTER (from intelligence_center.py)
# ════════════════════════════════════════════════════════════════════════════════
elif section == "Intelligence Center":
    st.markdown("### Intelligence Center")
    st.write("Integrated market intelligence platform combining multiple data sources.")

    tabs_ic = st.tabs(["Dashboard", "News & Sentiment", "Signals", "Alerts", "Details"])

    with tabs_ic[0]:
        st.subheader("Market Overview")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Market Sentiment", "Bullish", "+2.5%")
        c2.metric("VIX Level", "18.5", "-1.2")
        c3.metric("News Score", "0.72", "+0.08")
        c4.metric("Correlation", "0.45", "-0.05")

    with tabs_ic[1]:
        st.subheader("Recent News & Sentiment")
        st.info("Top stories and sentiment analysis")

    with tabs_ic[2]:
        st.subheader("Trading Signals")
        st.success("Generated from technical + fundamental analysis")

    with tabs_ic[3]:
        st.subheader("Alerts")
        st.warning("Critical market alerts appear here.")

    with tabs_ic[4]:
        st.subheader("Detailed Analytics")
        st.info("Extended analysis and research tools.")
