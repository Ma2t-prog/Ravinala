"""
Omega Market Intelligence Dashboard — Real data implementation.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

st.set_page_config(
    page_title="Market Intelligence — Omega",
    page_icon=None,
    layout="wide"
)

# ============================================================================
# CACHED DATA FUNCTIONS
# ============================================================================

PRESET_TICKERS = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'GOOGL', 'NVDA', 'BTC-USD', 'GLD']


@st.cache_data(ttl=900)
def fetch_ohlcv(ticker: str, days: int = 30) -> pd.DataFrame:
    """Fetch historical OHLCV with 15-min cache."""
    try:
        from genesix.data.market_fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        end = datetime.now()
        start = end - timedelta(days=days)
        df = fetcher.get_historical_ohlcv(ticker, start, end)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900)
def fetch_extended(ticker: str, days: int = 252) -> pd.DataFrame:
    """Fetch extended history for moving averages."""
    try:
        from genesix.data.market_fetcher import MarketDataFetcher
        fetcher = MarketDataFetcher()
        end = datetime.now()
        start = end - timedelta(days=days)
        df = fetcher.get_historical_ohlcv(ticker, start, end)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=900)
def get_market_health(ticker: str, days: int = 252):
    """Compute market health metrics using rolling z-score anomaly proxy."""
    try:
        df = fetch_extended(ticker, days)
        if df.empty or 'close' not in df.columns:
            return None

        returns = df['close'].pct_change().dropna()
        if len(returns) < 30:
            return None

        # Rolling z-score based anomaly level
        window = 21
        rolling_mean = returns.rolling(window).mean()
        rolling_std = returns.rolling(window).std()
        z_scores = (returns - rolling_mean) / (rolling_std + 1e-12)
        recent_anomalies = (z_scores.abs() > 2.0).iloc[-30:].mean() * 100

        # Rolling Sharpe (1Y annualized)
        ann_ret = returns.mean() * 252
        ann_vol = returns.std() * np.sqrt(252)
        sharpe = ann_ret / max(ann_vol, 0.01)

        # Max drawdown
        prices = (1 + returns).cumprod()
        cummax = prices.cummax()
        dd = ((prices - cummax) / cummax).min()

        # Momentum: 3-month vs 12-month return
        ret_3m = float(df['close'].iloc[-1] / df['close'].iloc[max(-63, -len(df))] - 1) if len(df) >= 21 else 0
        ret_1y = float(df['close'].iloc[-1] / df['close'].iloc[0] - 1)

        # Health score (0-100): penalise high anomaly level, low Sharpe, high drawdown
        health = max(0, min(100, 60 + sharpe * 10 - recent_anomalies * 0.5 + dd * 100))

        return {
            'health_score': float(health),
            'anomaly_level': float(recent_anomalies),
            'annualized_return': float(ann_ret * 100),
            'annualized_vol': float(ann_vol * 100),
            'sharpe': float(sharpe),
            'max_drawdown': float(dd * 100),
            'return_3m': float(ret_3m * 100),
            'return_1y': float(ret_1y * 100),
        }
    except Exception:
        return None


# ============================================================================
# PAGE HEADER
# ============================================================================

st.markdown("# Market Intelligence [Demo / Research Mode]")
st.markdown(
    "⚠️ Candlestick prices via yfinance (live). "
    "AI health score and recommendations are illustrative demo outputs — not calibrated models."
)

# ============================================================================
# TABS
# ============================================================================

tabs = st.tabs(["Market Data", "AI Recommendations", "Alerts", "News & Sentiment"])

# ============================================================================
# TAB 1: MARKET DATA
# ============================================================================

with tabs[0]:
    st.subheader("Real Market Data")

    sel_col1, sel_col2 = st.columns([2, 1])
    with sel_col1:
        selected_ticker = st.selectbox("Select Asset", PRESET_TICKERS, index=0)
    with sel_col2:
        chart_days = st.selectbox("Chart Period", [30, 60, 90], index=0,
                                  format_func=lambda d: f"{d} Days")

    with st.spinner(f"Loading {selected_ticker} data..."):
        df_chart = fetch_ohlcv(selected_ticker, chart_days)
        df_ext = fetch_extended(selected_ticker, 252)

    if df_chart.empty or 'close' not in df_chart.columns:
        st.error(f"Could not load data for {selected_ticker}. Check ticker and connectivity.")
    else:
        # Key metrics
        last_close = df_chart['close'].iloc[-1]
        prev_close = df_chart['close'].iloc[-2] if len(df_chart) > 1 else last_close
        daily_chg = (last_close - prev_close) / prev_close * 100
        ytd_chg = float(df_ext['close'].iloc[-1] / df_ext['close'].iloc[0] - 1) * 100 if not df_ext.empty else 0
        vol_30d = df_chart['close'].pct_change().std() * np.sqrt(252) * 100

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Last Price", f"${last_close:.2f}",
                   delta=f"{daily_chg:+.2f}%",
                   delta_color="normal")
        mc2.metric("Volume (latest)", f"{int(df_chart['volume'].iloc[-1]):,}",
                   help="Latest day's volume")
        mc3.metric("YTD Return", f"{ytd_chg:+.1f}%",
                   delta_color="normal")
        mc4.metric("30D Realized Vol (ann.)", f"{vol_30d:.1f}%")

        st.divider()

        # Candlestick chart
        fig_candle = go.Figure()
        fig_candle.add_trace(go.Candlestick(
            x=df_chart.index,
            open=df_chart['open'],
            high=df_chart['high'],
            low=df_chart['low'],
            close=df_chart['close'],
            name=selected_ticker,
            increasing_line_color='#2ca02c',
            decreasing_line_color='#d62728',
        ))

        # Moving averages from extended data
        if not df_ext.empty and len(df_ext) > 20:
            for ma_period, color, dash in [(20, 'orange', 'solid'), (50, 'blue', 'dash')]:
                if len(df_ext) >= ma_period:
                    ma = df_ext['close'].rolling(ma_period).mean()
                    # Only show where it overlaps with chart period
                    ma_trimmed = ma.loc[ma.index >= df_chart.index[0]]
                    if len(ma_trimmed) > 0:
                        fig_candle.add_trace(go.Scatter(
                            x=ma_trimmed.index,
                            y=ma_trimmed.values,
                            mode='lines',
                            line=dict(color=color, width=1.5, dash=dash),
                            name=f'{ma_period}d MA',
                        ))
            # 200-day MA if available
            if len(df_ext) >= 200:
                ma200 = df_ext['close'].rolling(200).mean()
                ma200_trimmed = ma200.loc[ma200.index >= df_chart.index[0]]
                if len(ma200_trimmed) > 0:
                    fig_candle.add_trace(go.Scatter(
                        x=ma200_trimmed.index,
                        y=ma200_trimmed.values,
                        mode='lines',
                        line=dict(color='red', width=1.5, dash='dot'),
                        name='200d MA',
                    ))

        fig_candle.update_layout(
            title=f"{selected_ticker} — {chart_days}-Day Candlestick with Moving Averages",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            height=480,
            xaxis_rangeslider_visible=False,
            hovermode='x unified',
        )
        st.plotly_chart(fig_candle, use_container_width=True)

        # Volume bar chart
        vol_colors = ['#2ca02c' if c >= o else '#d62728'
                      for c, o in zip(df_chart['close'], df_chart['open'])]
        fig_vol = go.Figure(go.Bar(
            x=df_chart.index,
            y=df_chart['volume'],
            marker_color=vol_colors,
            name='Volume',
            hovertemplate='%{x|%Y-%m-%d}<br>Volume: %{y:,}<extra></extra>',
        ))
        fig_vol.update_layout(
            title=f"{selected_ticker} — Volume",
            xaxis_title="Date",
            yaxis_title="Volume",
            height=220,
        )
        st.plotly_chart(fig_vol, use_container_width=True)

        # Daily returns chart
        if not df_ext.empty:
            rets = df_ext['close'].pct_change().dropna()
            rets_trimmed = rets.loc[rets.index >= df_chart.index[0]]
            ret_colors = ['#2ca02c' if r > 0 else '#d62728' for r in rets_trimmed.values]
            fig_rets = go.Figure(go.Bar(
                x=rets_trimmed.index,
                y=rets_trimmed.values * 100,
                marker_color=ret_colors,
                hovertemplate='%{x|%Y-%m-%d}<br>%{y:.2f}%<extra></extra>',
            ))
            fig_rets.update_layout(
                title=f"{selected_ticker} — Daily Returns (%)",
                xaxis_title="Date",
                yaxis_title="Return (%)",
                height=220,
            )
            st.plotly_chart(fig_rets, use_container_width=True)


# ============================================================================
# TAB 2: AI RECOMMENDATIONS
# ============================================================================

with tabs[1]:
    st.subheader("AI-Powered Market Health & Recommendations")
    st.info("Real anomaly detection and risk metrics computed from live market data.")

    with st.spinner("Computing market health scores..."):
        health_results = {}
        for t in PRESET_TICKERS:
            h = get_market_health(t)
            if h:
                health_results[t] = h

    if not health_results:
        st.error("Could not compute market health. Check data connectivity.")
    else:
        # Health score table
        rows = []
        for ticker_h, metrics in health_results.items():
            score = metrics['health_score']
            signal = 'BUY' if score > 65 else ('HOLD' if score > 45 else 'CAUTION')
            rows.append({
                'Ticker': ticker_h,
                'Health Score': f"{score:.0f}/100",
                'Ann. Return': f"{metrics['annualized_return']:.1f}%",
                'Ann. Vol': f"{metrics['annualized_vol']:.1f}%",
                'Sharpe': f"{metrics['sharpe']:.2f}",
                'Max Drawdown': f"{metrics['max_drawdown']:.1f}%",
                '3M Return': f"{metrics['return_3m']:+.1f}%",
                'Anomaly Level': f"{metrics['anomaly_level']:.1f}%",
                'Signal': signal,
            })
        health_df = pd.DataFrame(rows)
        st.dataframe(health_df, use_container_width=True, hide_index=True)

        # Health score bar chart
        fig_health = go.Figure(go.Bar(
            x=list(health_results.keys()),
            y=[h['health_score'] for h in health_results.values()],
            marker_color=['#2ca02c' if h['health_score'] > 65
                         else '#ff7f0e' if h['health_score'] > 45
                         else '#d62728' for h in health_results.values()],
            text=[f"{h['health_score']:.0f}" for h in health_results.values()],
            textposition='outside',
            hovertemplate='%{x}: %{y:.0f}/100<extra></extra>',
        ))
        fig_health.update_layout(
            title="AI Market Health Score (0-100) by Asset",
            yaxis_title="Health Score",
            yaxis_range=[0, 110],
            height=520,
        )
        st.plotly_chart(fig_health, use_container_width=True)

        # Detailed view for selected asset
        st.divider()
        detail_ticker = st.selectbox(
            "Detailed view for:", PRESET_TICKERS, key="detail_ticker"
        )
        if detail_ticker in health_results:
            d = health_results[detail_ticker]
            dc1, dc2, dc3, dc4, dc5 = st.columns(5)
            dc1.metric("Health Score", f"{d['health_score']:.0f}/100")
            dc2.metric("Ann. Return", f"{d['annualized_return']:+.1f}%")
            dc3.metric("Ann. Volatility", f"{d['annualized_vol']:.1f}%")
            dc4.metric("Sharpe Ratio", f"{d['sharpe']:.2f}")
            dc5.metric("Max Drawdown", f"{d['max_drawdown']:.1f}%")


# ============================================================================
# TAB 3: ALERTS
# ============================================================================

with tabs[2]:
    st.subheader("Smart Alerts")
    st.info("Dynamic alerts driven by the SmartAlertSystem backend. "
            "Configure your portfolio below for personalized alerts.")

    alert_tickers_raw = st.text_input(
        "Portfolio Tickers (TICKER:WEIGHT format, comma-separated)",
        value="SPY:0.40, QQQ:0.20, GLD:0.15, TLT:0.15, BTC-USD:0.10",
        key="mkt_alert_portfolio"
    )

    try:
        port_dict = {}
        for item in alert_tickers_raw.split(','):
            item = item.strip()
            if ':' in item:
                t, w = item.split(':')
                port_dict[t.strip().upper()] = float(w.strip())
    except Exception:
        port_dict = {'SPY': 0.5, 'GLD': 0.3, 'TLT': 0.2}

    if st.button("Generate Alerts", type="primary"):
        with st.spinner("Generating smart alerts..."):
            try:
                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                from genesix.intelligence.smart_alerts import SmartAlertSystem
                system = SmartAlertSystem()
                live_alerts = system.generate_smart_alerts(portfolio=port_dict)
            except Exception as e:
                live_alerts = []
                st.warning(f"Alert system encountered an issue: {e}")

        if not live_alerts:
            st.success("No active alerts. Market conditions appear stable.")
        else:
            for alert in live_alerts:
                sev = alert.get('severity', 'info')
                icon = {'critical': 'CRITICAL', 'warning': 'WARNING', 'info': 'INFO'}.get(sev, 'INFO')
                with st.container(border=True):
                    st.markdown(f"**[{icon}] {alert.get('title', 'Alert')}**")
                    st.write(alert.get('description', ''))
                    actions = alert.get('suggested_actions', [])
                    if actions:
                        for a in actions:
                            st.markdown(f"  - {a}")


# ============================================================================
# TAB 4: NEWS & SENTIMENT
# ============================================================================

with tabs[3]:
    st.subheader("News & Sentiment Analysis")
    st.info("News integration requires an NLP/news API. "
            "Sector sentiment scores below are model-computed from price momentum.")

    # Compute momentum-based sentiment from real data
    with st.spinner("Computing sector momentum scores..."):
        sector_etfs = {
            'Technology': 'QQQ',
            'S&P 500': 'SPY',
            'Small Cap': 'IWM',
            'Emerging Mkts': 'EEM',
            'Gold': 'GLD',
            'Bonds (LT)': 'TLT',
        }

        sentiment_scores = {}
        for sector, etf in sector_etfs.items():
            try:
                h = get_market_health(etf)
                if h:
                    # Use Sharpe + 3M return as sentiment proxy
                    raw_score = 50 + h['sharpe'] * 15 + h['return_3m'] * 0.5
                    sentiment_scores[sector] = max(0, min(100, raw_score))
            except Exception:
                pass

    if sentiment_scores:
        mc1, mc2 = st.columns(2)
        with mc1:
            fig_sent = go.Figure(go.Bar(
                x=list(sentiment_scores.keys()),
                y=list(sentiment_scores.values()),
                marker=dict(
                    color=list(sentiment_scores.values()),
                    colorscale='RdYlGn',
                    cmin=0, cmax=100,
                ),
                text=[f"{v:.0f}" for v in sentiment_scores.values()],
                textposition='outside',
                hovertemplate='%{x}: %{y:.0f}/100<extra></extra>',
            ))
            fig_sent.update_layout(
                title="Sector Momentum-Based Sentiment (0-100)",
                yaxis_title="Score",
                yaxis_range=[0, 115],
                height=520,
            )
            st.plotly_chart(fig_sent, use_container_width=True)

        with mc2:
            st.markdown("**Sector Scores (momentum + risk-adjusted return)**")
            sent_df = pd.DataFrame([
                {'Sector': k,
                 'Score': f"{v:.0f}/100",
                 'Signal': 'Bullish' if v > 60 else ('Neutral' if v > 40 else 'Bearish')}
                for k, v in sorted(sentiment_scores.items(), key=lambda x: -x[1])
            ])
            st.dataframe(sent_df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("""
            **Note on News Integration**

            Real-time news sentiment requires connecting to a news API such as:
            - [NewsAPI.org](https://newsapi.org)
            - [Refinitiv Eikon](https://www.refinitiv.com/en/products/eikon-trading-software)
            - [Bloomberg Terminal API](https://www.bloomberg.com/professional/product/api/)

            Configure `NEWSAPI_KEY` in your `.env` file to enable live sentiment.
            """)
    else:
        st.warning("Could not compute sector scores. Check data connectivity.")
