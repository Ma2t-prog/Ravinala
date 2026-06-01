"""
GenesiX Intelligence — Real implementation using signals, regime, contagion, and smart alert backends.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(page_title="Intelligence — GenesiX", page_icon=None, layout="wide")


# ============================================================================
# CACHED BACKEND CALLS
# ============================================================================

@st.cache_data(ttl=1800)
def get_signals(tickers: tuple) -> dict:
    """Generate signals for a list of tickers."""
    try:
        from genesix.intelligence.signals import SignalGenerator
        gen = SignalGenerator()
        return gen.signal_dashboard_data(list(tickers))
    except Exception as e:
        return {'error': str(e)}


@st.cache_data(ttl=1800)
def get_regime(ticker: str, days: int) -> dict:
    """Get regime detection results for a ticker."""
    try:
        from genesix.data.market_fetcher import MarketDataFetcher
        from genesix.intelligence.regime_ml import RegimeDetector

        fetcher = MarketDataFetcher()
        end = datetime.now()
        start = end - timedelta(days=days)
        df = fetcher.get_historical_ohlcv(ticker, start, end)
        if df.empty or 'close' not in df.columns:
            return {'error': 'No data'}

        returns = df['close'].pct_change().dropna().values
        detector = RegimeDetector()
        current = detector.detect_regime(returns=returns)
        hist = detector.historical_regimes(returns)
        trans = detector.regime_transition_matrix(hist)
        return {
            'current': current,
            'hist': hist,
            'trans': trans,
            'returns': df['close'].pct_change().dropna(),
        }
    except Exception as e:
        return {'error': str(e)}


@st.cache_data(ttl=1800)
def get_contagion(tickers: tuple) -> dict:
    """Build and return contagion network + real correlation matrix."""
    try:
        import yfinance as yf
        from genesix.intelligence.contagion import ContagionNetwork

        # Real correlation from yfinance
        data = yf.download(list(tickers), period='1y', progress=False)['Close']
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.dropna(axis=1, thresh=int(len(data) * 0.8))
        data = data.dropna()
        avail_tickers = data.columns.tolist()
        returns = data.pct_change().dropna()
        corr_matrix = returns.corr()

        # Build contagion network
        net = ContagionNetwork()
        network = net.build_network(avail_tickers)
        risks = net.identify_systemic_risks(network)

        return {
            'corr_matrix': corr_matrix,
            'avail_tickers': avail_tickers,
            'network': network,
            'risks': risks,
        }
    except Exception as e:
        return {'error': str(e)}


@st.cache_data(ttl=900)
def get_smart_alerts(portfolio: tuple) -> list:
    """Generate smart alerts for a given portfolio."""
    try:
        from genesix.intelligence.smart_alerts import SmartAlertSystem
        system = SmartAlertSystem()
        portfolio_dict = dict(zip(portfolio[::2], portfolio[1::2]))
        alerts = system.generate_smart_alerts(portfolio=portfolio_dict)
        return alerts
    except Exception as e:
        return []


@st.cache_data(ttl=1800)
def get_rolling_correlation(tickers: tuple, window: int, days: int):
    """Compute rolling correlation for the Correlation Dynamics tab."""
    try:
        import yfinance as yf
        data = yf.download(list(tickers), period=f"{days}d", progress=False)['Close']
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data = data.dropna(axis=1, thresh=int(len(data) * 0.7))
        returns = data.pct_change().dropna()
        return returns
    except Exception as e:
        return pd.DataFrame()


# ============================================================================
# PAGE HEADER
# ============================================================================

st.title("Intelligence")
st.markdown(
    "⚠️ **Research / Demo mode** — signals and regime detection use synthetic (np.random) data. "
    "Not calibrated real-time feeds. Do not use for live trading decisions."
)

# ============================================================================
# TABS
# ============================================================================

tab_signals, tab_regime, tab_contagion, tab_alerts, tab_corrdy = st.tabs([
    "Signals",
    "Regime Detection",
    "Contagion",
    "Smart Alerts",
    "Correlation Dynamics",
])


# ============================================================================
# TAB 1: SIGNALS
# ============================================================================

with tab_signals:
    st.subheader("Asset Signal Generator")

    sig_tickers_raw = st.text_input(
        "Tickers (comma-separated)",
        value="SPY, QQQ, AAPL, MSFT, GLD, TLT",
        key="sig_tickers"
    )
    sig_tickers = tuple(t.strip().upper() for t in sig_tickers_raw.split(',') if t.strip())

    with st.spinner("Generating signals..."):
        signals_data = get_signals(sig_tickers)

    if 'error' in signals_data:
        st.error(f"Signal generation error: {signals_data['error']}")
    else:
        # Market signal
        mkt = signals_data.get('market_signal', {})
        if mkt:
            mkt_c1, mkt_c2, mkt_c3 = st.columns(3)
            mkt_c1.metric("Market Regime", mkt.get('regime', 'N/A').upper(),
                          f"Score: {mkt.get('score', 0):.2f}")
            mkt_c2.metric("Confidence", f"{mkt.get('confidence', 0)*100:.0f}%")
            mkt_c3.metric("Regime Outlook", mkt.get('outlook', 'N/A')[:60])

            favored = mkt.get('favored_assets', [])
            avoid = mkt.get('avoid_assets', [])
            if favored or avoid:
                st.markdown(
                    f"**Favored:** {', '.join(favored)} | "
                    f"**Avoid:** {', '.join(avoid)}"
                )

        st.divider()

        # Asset signals table
        asset_sigs = signals_data.get('asset_signals', {})
        if asset_sigs:
            st.subheader("Individual Asset Signals")

            signal_map = {
                'strong_buy': 'STRONG BUY',
                'buy': 'BUY',
                'hold': 'HOLD',
                'sell': 'SELL',
                'strong_sell': 'STRONG SELL',
            }
            color_map = {
                'strong_buy': 'green', 'buy': 'green',
                'hold': 'blue', 'sell': 'red', 'strong_sell': 'red',
            }

            rows = []
            for asset, sig in asset_sigs.items():
                rows.append({
                    'Ticker': asset,
                    'Signal': signal_map.get(sig['signal'], sig['signal']),
                    'Composite Score': f"{sig['composite_score']:.3f}",
                    'Confidence': f"{sig['confidence']*100:.0f}%",
                    'ML Score': f"{sig['sub_signals']['ml_prediction']['score']:.3f}",
                    'Technical Score': f"{sig['sub_signals']['technical']['score']:.3f}",
                    'Key Reason': sig['key_reasons'][0] if sig['key_reasons'] else 'N/A',
                })
            sig_df = pd.DataFrame(rows)
            st.dataframe(sig_df, use_container_width=True, hide_index=True)

            # Score bar chart
            scores = [float(asset_sigs[a]['composite_score']) for a in asset_sigs]
            bar_colors = ['green' if s > 0.2 else ('red' if s < -0.2 else 'steelblue') for s in scores]

            fig_sig = go.Figure(go.Bar(
                x=list(asset_sigs.keys()),
                y=scores,
                marker_color=bar_colors,
                hovertemplate='%{x}: %{y:.3f}<extra></extra>',
            ))
            fig_sig.add_hline(y=0, line_color='black', line_width=0.8)
            fig_sig.update_layout(
                title="Composite Signal Score by Asset",
                yaxis_title="Composite Score",
                height=520,
            )
            st.plotly_chart(fig_sig, use_container_width=True)

        # Event signals
        event_sigs = signals_data.get('event_signals', [])
        if event_sigs:
            st.subheader("Upcoming Event Signals")
            for ev in event_sigs:
                with st.container(border=True):
                    st.markdown(f"**{ev['event']}** — {ev.get('date', 'N/A')} "
                                f"({ev.get('days_until', 'N/A')} days)")
                    st.caption(f"Expected move: {ev.get('expected_move', 'N/A')} | "
                               f"Historical avg: {ev.get('historical_avg_move', 'N/A')}")


# ============================================================================
# TAB 2: REGIME DETECTION
# ============================================================================

with tab_regime:
    st.subheader("Market Regime Detection")

    reg_ticker = st.text_input("Ticker for regime analysis", value="SPY", key="reg_ticker").upper().strip()
    reg_days = st.selectbox("Lookback", [504, 756, 1260], index=0,
                            format_func=lambda d: {504: '2 Years', 756: '3 Years', 1260: '5 Years'}[d],
                            key="reg_days")

    with st.spinner("Detecting regime..."):
        reg_data = get_regime(reg_ticker, reg_days)

    if 'error' in reg_data:
        st.error(f"Regime detection error: {reg_data['error']}")
    else:
        current = reg_data['current']
        hist = reg_data['hist']
        trans = reg_data['trans']

        regime_label_map = {
            'low_vol': 'LOW VOLATILITY (Bull)',
            'normal': 'NORMAL',
            'high_vol': 'HIGH VOLATILITY',
            'crisis': 'CRISIS',
        }

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Current Regime",
                   regime_label_map.get(current['regime'], current['regime'].upper()))
        rc2.metric("Detection Confidence", f"{current['confidence']*100:.0f}%")
        rc3.metric("Days in Current Regime", str(current.get('days_in_regime', 'N/A')))
        rc4.metric("Transition Probability (tomorrow)", f"{current['transition_probability']*100:.0f}%")

        st.divider()

        # Historical regimes
        regime_num = hist.map({'low_vol': 0, 'normal': 1, 'high_vol': 2, 'crisis': 3}).fillna(1)
        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(
            x=hist.index, y=regime_num.values,
            mode='lines', fill='tozeroy',
            fillcolor='rgba(31,119,180,0.2)',
            line=dict(color='steelblue', width=1.5),
            text=hist.values,
            hovertemplate='%{x|%Y-%m-%d}<br>Regime: %{text}<extra></extra>',
            name='Regime',
        ))
        fig_h.update_layout(
            title=f"{reg_ticker} Historical Regimes (GMM-based)",
            xaxis_title="Date",
            yaxis=dict(tickvals=[0, 1, 2, 3],
                       ticktext=['Low Vol', 'Normal', 'High Vol', 'Crisis']),
            height=520,
        )
        st.plotly_chart(fig_h, use_container_width=True)

        # Transition matrix
        st.subheader("Transition Probability Matrix")
        fig_tm = go.Figure(go.Heatmap(
            z=trans.values,
            x=trans.columns.tolist(),
            y=trans.index.tolist(),
            colorscale='Blues',
            zmin=0, zmax=1,
            text=[[f"{v:.2f}" for v in row] for row in trans.values],
            texttemplate="%{text}",
            hovertemplate='From %{y} → To %{x}: %{z:.3f}<extra></extra>',
        ))
        fig_tm.update_layout(
            title="Regime Transition Probabilities",
            height=520,
            xaxis_title="To",
            yaxis_title="From",
        )
        st.plotly_chart(fig_tm, use_container_width=True)

        # Regime distribution pie
        regime_counts = hist.value_counts()
        fig_reg_pie = go.Figure(go.Pie(
            labels=[regime_label_map.get(r, r) for r in regime_counts.index],
            values=regime_counts.values,
            textinfo='label+percent',
            marker=dict(colors=['#2ca02c', '#1f77b4', '#ff7f0e', '#d62728']),
        ))
        fig_reg_pie.update_layout(title="Historical Time in Each Regime", height=520)
        st.plotly_chart(fig_reg_pie, use_container_width=True)


# ============================================================================
# TAB 3: CONTAGION
# ============================================================================

with tab_contagion:
    st.subheader("Cross-Asset Contagion & Correlation Network")

    contagion_tickers_raw = st.text_input(
        "Assets for contagion analysis (comma-separated)",
        value="SPY, QQQ, IWM, EEM, GLD, TLT",
        key="contagion_tickers"
    )
    contagion_tickers = tuple(t.strip().upper() for t in contagion_tickers_raw.split(',') if t.strip())

    with st.spinner("Building contagion network..."):
        contagion_data = get_contagion(contagion_tickers)

    if 'error' in contagion_data:
        st.error(f"Contagion analysis error: {contagion_data['error']}")
    else:
        corr = contagion_data['corr_matrix']
        avail = contagion_data['avail_tickers']
        risks = contagion_data['risks']
        network = contagion_data['network']

        # Real correlation heatmap
        fig_corr = go.Figure(go.Heatmap(
            z=corr.values,
            x=corr.columns.tolist(),
            y=corr.index.tolist(),
            colorscale='RdYlGn',
            zmin=-1, zmax=1,
            text=[[f"{v:.2f}" for v in row] for row in corr.values],
            texttemplate="%{text}",
            colorbar=dict(title="Correlation"),
            hovertemplate='%{y} vs %{x}: %{z:.3f}<extra></extra>',
        ))
        fig_corr.update_layout(
            title=f"Real Correlation Matrix (1Y daily returns) — {', '.join(avail)}",
            height=520,
        )
        st.plotly_chart(fig_corr, use_container_width=True)

        st.caption("Green = low/negative correlation (diversification). "
                   "Red = high positive correlation (contagion risk).")

        st.divider()

        # Network metrics
        metrics = network.get('metrics', {})
        nm1, nm2, nm3 = st.columns(3)
        nm1.metric("Network Density", f"{metrics.get('network_density', 0):.3f}")
        nm2.metric("Most Central Asset", metrics.get('most_central_asset', 'N/A'))
        nm3.metric("Contagion Risk Score", f"{metrics.get('contagion_risk_score', 0):.1f}/100")

        # Systemic risks
        st.subheader("Systemic Risk Assessment")
        if risks:
            risk_rows = []
            for r in risks[:8]:
                risk_rows.append({
                    'Asset': r['asset'],
                    'Systemic Score': f"{r['systemic_score']:.3f}",
                    'Stress Level': r['current_stress_level'].upper(),
                    'Risk Level': r['risk_level'].upper(),
                    'Assets Affected': r['n_assets_affected'],
                })
            st.dataframe(pd.DataFrame(risk_rows), use_container_width=True, hide_index=True)


# ============================================================================
# TAB 4: SMART ALERTS
# ============================================================================

with tab_alerts:
    st.subheader("Smart Alert System")
    st.markdown("Predictive, reactive, and opportunity alerts based on real market signals.")

    alert_portfolio_raw = st.text_input(
        "Portfolio (TICKER:WEIGHT, comma-separated)",
        value="SPY:0.35, QQQ:0.20, TLT:0.20, GLD:0.10, AAPL:0.15",
        key="alert_portfolio"
    )

    # Parse portfolio
    try:
        portfolio_dict = {}
        for item in alert_portfolio_raw.split(','):
            item = item.strip()
            if ':' in item:
                t, w = item.split(':')
                portfolio_dict[t.strip().upper()] = float(w.strip())
    except Exception:
        portfolio_dict = {'SPY': 0.5, 'TLT': 0.3, 'GLD': 0.2}

    # Flatten to tuple for cache key
    portfolio_tuple = tuple(x for pair in portfolio_dict.items() for x in pair)

    with st.spinner("Generating smart alerts..."):
        alerts = get_smart_alerts(portfolio_tuple)

    if not alerts:
        st.info("No active alerts generated. Market conditions appear calm, or the alert system backend is initializing.")
    else:
        severity_colors = {
            'critical': '#d62728',
            'warning': '#ff7f0e',
            'info': '#1f77b4',
        }
        category_icons = {
            'predictive': 'PREDICTIVE',
            'reactive': 'REACTIVE',
            'opportunity': 'OPPORTUNITY',
            'portfolio': 'PORTFOLIO',
        }

        # Summary counts
        by_sev = {}
        for a in alerts:
            s = a.get('severity', 'info')
            by_sev[s] = by_sev.get(s, 0) + 1

        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Critical / Warning", str(by_sev.get('critical', 0) + by_sev.get('warning', 0)))
        sc2.metric("Informational", str(by_sev.get('info', 0)))
        sc3.metric("Total Alerts", str(len(alerts)))

        st.divider()

        for alert in alerts:
            sev = alert.get('severity', 'info')
            cat = alert.get('category', 'info')
            color = severity_colors.get(sev, '#1f77b4')

            with st.container(border=True):
                col_head, col_prob = st.columns([4, 1])
                with col_head:
                    st.markdown(f"**[{category_icons.get(cat, cat.upper())}] {alert.get('title', 'Alert')}**")
                    st.caption(f"Severity: **{sev.upper()}** | Horizon: {alert.get('time_horizon', 'N/A')} | "
                               f"Assets: {', '.join(alert.get('affected_assets', []))[:60]}")
                with col_prob:
                    prob = alert.get('probability')
                    if prob is not None:
                        st.metric("Probability", f"{prob*100:.0f}%")

                st.write(alert.get('description', ''))

                actions = alert.get('suggested_actions', [])
                if actions:
                    st.markdown("**Suggested Actions:**")
                    for action in actions:
                        st.markdown(f"- {action}")

                dismiss = alert.get('dismiss_condition', '')
                if dismiss:
                    st.caption(f"Dismiss when: {dismiss}")


# ============================================================================
# TAB 5: CORRELATION DYNAMICS
# ============================================================================

with tab_corrdy:
    st.subheader("Rolling Correlation Dynamics")
    st.markdown("Monitor how correlations between assets evolve over time.")

    corr_col1, corr_col2, corr_col3 = st.columns(3)
    with corr_col1:
        corr_assets_raw = st.text_input(
            "Assets",
            value="SPY, QQQ, TLT, GLD, BTC-USD, EEM, DX-Y.NYB",
            key="corr_assets"
        )
        corr_assets = tuple(t.strip().upper() for t in corr_assets_raw.split(',') if t.strip())
    with corr_col2:
        corr_window = st.select_slider(
            "Rolling Window (days)",
            options=[20, 60, 120, 252],
            value=60,
        )
    with corr_col3:
        corr_lookback = st.selectbox(
            "Data Lookback",
            [504, 756, 1260],
            index=0,
            format_func=lambda d: {504: '2 Years', 756: '3 Years', 1260: '5 Years'}[d],
            key="corr_lookback"
        )

    with st.spinner("Loading data and computing rolling correlations..."):
        returns_all = get_rolling_correlation(corr_assets, corr_window, corr_lookback)

    if returns_all.empty:
        st.error("Could not load data for correlation analysis. Check tickers.")
    else:
        avail_corr = returns_all.columns.tolist()
        st.caption(f"Available tickers: {', '.join(avail_corr)}")

        if len(avail_corr) < 2:
            st.warning("Need at least 2 valid tickers for correlation analysis.")
        else:
            # Compute rolling correlation between first two tickers as primary series
            # Also compute full rolling correlation at the last date for snapshot heatmap
            pair_corrs = {}
            for i in range(len(avail_corr)):
                for j in range(i + 1, len(avail_corr)):
                    a1, a2 = avail_corr[i], avail_corr[j]
                    rolling_c = returns_all[a1].rolling(corr_window).corr(returns_all[a2]).dropna()
                    pair_corrs[f"{a1}/{a2}"] = rolling_c

            # Plot top-5 most volatile pairs (highest std of rolling correlation)
            pair_stds = {k: v.std() for k, v in pair_corrs.items()}
            top5_pairs = sorted(pair_stds.items(), key=lambda x: -x[1])[:5]
            top5_names = [p[0] for p in top5_pairs]

            fig_rc = go.Figure()
            colors_rc = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            for idx, pname in enumerate(top5_names):
                rc_series = pair_corrs[pname]
                # Color by value: green<0.5, orange 0.5-0.8, red>0.8
                fig_rc.add_trace(go.Scatter(
                    x=rc_series.index,
                    y=rc_series.values,
                    mode='lines',
                    name=pname,
                    line=dict(color=colors_rc[idx % len(colors_rc)], width=1.5),
                    hovertemplate=f'{pname}<br>%{{x|%Y-%m-%d}}: %{{y:.3f}}<extra></extra>',
                ))

            fig_rc.add_hline(y=0.8, line_color='red', line_dash='dash', opacity=0.5,
                             annotation_text="Crisis threshold (0.8)")
            fig_rc.add_hline(y=0, line_color='black', line_width=0.5)

            fig_rc.update_layout(
                title=f"Rolling {corr_window}-Day Correlation — Top 5 Most Dynamic Pairs",
                xaxis_title="Date",
                yaxis_title="Correlation",
                height=520,
                hovermode='x unified',
                yaxis=dict(range=[-1, 1]),
            )
            st.plotly_chart(fig_rc, use_container_width=True)

            # Current snapshot heatmap
            st.subheader("Current Correlation Snapshot")
            n_tickers = len(avail_corr)
            snapshot_matrix = np.ones((n_tickers, n_tickers))
            for i in range(n_tickers):
                for j in range(i + 1, n_tickers):
                    a1, a2 = avail_corr[i], avail_corr[j]
                    key = f"{a1}/{a2}"
                    if key in pair_corrs and len(pair_corrs[key]) > 0:
                        val = pair_corrs[key].iloc[-1]
                        snapshot_matrix[i, j] = val
                        snapshot_matrix[j, i] = val

            fig_snap = go.Figure(go.Heatmap(
                z=snapshot_matrix,
                x=avail_corr,
                y=avail_corr,
                colorscale='RdYlGn_r',
                zmin=-1, zmax=1,
                text=[[f"{v:.2f}" for v in row] for row in snapshot_matrix],
                texttemplate="%{text}",
                colorbar=dict(title="Corr"),
                hovertemplate='%{y} vs %{x}: %{z:.3f}<extra></extra>',
            ))
            fig_snap.update_layout(
                title=f"Current {corr_window}-Day Rolling Correlation — Snapshot",
                height=520,
            )
            st.plotly_chart(fig_snap, use_container_width=True)

            # Correlation instability metric
            st.subheader("Correlation Instability (Std of Rolling Correlation)")
            instab = {k: v.std() for k, v in pair_corrs.items()}
            instab_sorted = dict(sorted(instab.items(), key=lambda x: -x[1]))

            fig_instab = go.Figure(go.Bar(
                x=list(instab_sorted.keys()),
                y=list(instab_sorted.values()),
                marker_color=['#d62728' if v > 0.2 else '#2ca02c' for v in instab_sorted.values()],
                hovertemplate='%{x}: %{y:.4f}<extra></extra>',
            ))
            fig_instab.update_layout(
                title=f"Correlation Instability (std of {corr_window}-day rolling corr)",
                yaxis_title="Std of Rolling Correlation",
                height=520,
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig_instab, use_container_width=True)
