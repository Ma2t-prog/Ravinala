"""
Market Intelligence — Unified live market, macro, news & alternative data hub
Fusion of: live_market + macro_analysis + market_news + alt_data
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

_render_page_header("MI", "Market Intelligence",
                    "Live prices, macro dashboard, news flow & alternative data signals",
                    "Intelligence")

# ============================================================================
# TABS
# ============================================================================

tab_live, tab_macro, tab_news, tab_alt = st.tabs([
    "Live Market",
    "Macro Analysis",
    "Market News",
    "Alternative Data",
])

# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — LIVE MARKET (from live_market.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_live:
    import yfinance as yf
    from scipy.stats import norm

    def _flatten(df):
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df

    @st.cache_data(ttl=300)
    def _fetch_ticker_data(ticker):
        tk = yf.Ticker(ticker)
        data = _flatten(yf.download(ticker, period="1y", progress=False, interval="1d"))
        info = tk.fast_info
        return data, dict(info)

    @st.cache_data(ttl=300)
    def _fetch_chart(ticker, period):
        return _flatten(yf.download(ticker, period=period, progress=False))

    @st.cache_data(ttl=300)
    def _fetch_comparison(tickers):
        rows = []
        for t in tickers:
            try:
                d = _flatten(yf.download(t, period="1y", progress=False, interval="1d"))
                if d.empty:
                    continue
                fi = yf.Ticker(t).fast_info
                price_c = getattr(fi, 'last_price', None) or float(d['Close'].iloc[-1])
                ytd = (float(d['Close'].iloc[-1]) - float(d['Close'].iloc[0])) / float(d['Close'].iloc[0]) * 100
                iv = float(d['Close'].pct_change().std()) * np.sqrt(252) * 100
                rows.append({'Ticker': t, 'Price': f"${price_c:.2f}", 'YTD%': f"{ytd:.2f}%", 'IV%': f"{iv:.2f}%"})
            except Exception:
                pass
        return rows

    ticker = st.text_input("Ticker (e.g. AAPL, MSFT, EURUSD=X)", "AAPL", key="live_ticker")

    if ticker:
        try:
            data, fi = _fetch_ticker_data(ticker)
            if data.empty:
                st.error("No data returned. Check the ticker symbol.")
                st.stop()

            _close = data['Close']
            price_val = getattr(yf.Ticker(ticker).fast_info, 'last_price', None) or float(_close.iloc[-1])
            price_val = float(price_val)
            price_prev = float(_close.iloc[-2]) if len(data) > 1 else price_val
            change_1d = (price_val - price_prev) / price_prev * 100 if price_prev else 0

            # Key Metrics
            st.markdown("### Key Metrics")
            c1, c2, c3, c4, c5 = st.columns(5)
            mktcap = getattr(yf.Ticker(ticker).fast_info, 'market_cap', 0) or 0
            c1.metric("Price", f"${price_val:.2f}", f"{change_1d:+.2f}%")
            c2.metric("Market Cap", f"${mktcap/1e9:.1f}B" if mktcap else "N/A")
            c3.metric("52W High", f"${getattr(yf.Ticker(ticker).fast_info,'year_high',0) or 0:.2f}")
            c4.metric("52W Low", f"${getattr(yf.Ticker(ticker).fast_info,'year_low',0) or 0:.2f}")
            c5.metric("Vol Rank", "–")

            # Volatility
            st.markdown("### Volatility Analysis")
            returns = _close.pct_change().dropna()
            hv_30 = float(returns.tail(30).std()) * np.sqrt(252) * 100
            hv_90 = float(returns.tail(90).std()) * np.sqrt(252) * 100
            hv_1y = float(returns.std()) * np.sqrt(252) * 100

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("HV 30D", f"{hv_30:.2f}%")
            c2.metric("HV 90D", f"{hv_90:.2f}%")
            c3.metric("HV 1Y", f"{hv_1y:.2f}%")
            c4.metric("Vol Percentile", f"{hv_30/hv_1y*100:.0f}th %ile" if hv_1y else "N/A")

            # Options Greeks Calculator
            st.markdown("### Options Greeks (Black-Scholes)")
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                strike_lm = st.slider("Strike K", float(price_val*0.8), float(price_val*1.2), float(price_val),
                                       step=float(max(0.5, price_val*0.005)), key="lm_strike")
            with c2:
                dte = st.slider("Days to Expiry", 1, 365, 30, key="lm_dte")
            with c3:
                vol_pct = st.slider("Vol (%)", 5, 200, max(5, min(200, int(hv_30 or 25))), key="lm_vol") / 100
            with c4:
                rfr = st.slider("Risk-Free (%)", 0, 10, 5, key="lm_rfr") / 100
            with c5:
                opt = st.radio("Type", ["Call", "Put"], horizontal=True, key="lm_opt")

            T_lm = dte / 365
            if vol_pct > 0 and T_lm > 0:
                d1 = (np.log(price_val/strike_lm) + (rfr + 0.5*vol_pct**2)*T_lm) / (vol_pct*np.sqrt(T_lm))
                d2 = d1 - vol_pct*np.sqrt(T_lm)
                if opt == "Call":
                    delta_lm = norm.cdf(d1)
                    prem = price_val*norm.cdf(d1) - strike_lm*np.exp(-rfr*T_lm)*norm.cdf(d2)
                    theta_lm = (-price_val*norm.pdf(d1)*vol_pct/(2*np.sqrt(T_lm)) -
                                rfr*strike_lm*np.exp(-rfr*T_lm)*norm.cdf(d2)) / 365
                else:
                    delta_lm = norm.cdf(d1) - 1
                    prem = strike_lm*np.exp(-rfr*T_lm)*norm.cdf(-d2) - price_val*norm.cdf(-d1)
                    theta_lm = (-price_val*norm.pdf(d1)*vol_pct/(2*np.sqrt(T_lm)) +
                                rfr*strike_lm*np.exp(-rfr*T_lm)*norm.cdf(-d2)) / 365
                gamma_lm = norm.pdf(d1) / (price_val*vol_pct*np.sqrt(T_lm))
                vega_lm = price_val*norm.pdf(d1)*np.sqrt(T_lm) / 100
                rho_lm = (strike_lm*T_lm*np.exp(-rfr*T_lm)*norm.cdf(d2) if opt == "Call"
                           else -strike_lm*T_lm*np.exp(-rfr*T_lm)*norm.cdf(-d2)) / 100
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                c1.metric("Premium", f"${prem:.2f}")
                c2.metric("Delta", f"{delta_lm:.3f}")
                c3.metric("Gamma", f"{gamma_lm:.4f}")
                c4.metric("Vega", f"{vega_lm:.3f}")
                c5.metric("Theta", f"{theta_lm:.4f}")
                c6.metric("Rho", f"{rho_lm:.3f}")

            # Price Chart
            st.markdown("### Price Chart")
            period_map = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y"}
            chart_period = st.selectbox("Period", list(period_map.keys()), index=3, key="lm_period")
            cd = _fetch_chart(ticker, period_map[chart_period])
            if not cd.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=cd.index, y=cd['Close'], mode='lines',
                                         name='Price', line=dict(color='#00D9FF', width=2)))
                fig.add_trace(go.Scatter(x=cd.index, y=cd['Close'].rolling(20).mean(),
                                         mode='lines', name='MA20', line=dict(color='orange', dash='dash')))
                fig.add_trace(go.Scatter(x=cd.index, y=cd['Close'].rolling(50).mean(),
                                         mode='lines', name='MA50', line=dict(color='#ef4444', dash='dash')))
                fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=20,b=0))
                st.plotly_chart(fig, use_container_width=True)

            # Technicals
            st.markdown("### Technical Indicators")
            diff = _close.diff()
            gain = diff.where(diff > 0, 0).rolling(14).mean()
            loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
            rsi = 100 - (100 / (1 + gain / loss))
            exp1 = _close.ewm(span=12, adjust=False).mean()
            exp2 = _close.ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            sig_macd = macd.ewm(span=9, adjust=False).mean()
            hist = macd - sig_macd

            c1, c2 = st.columns(2)
            with c1:
                fr = go.Figure()
                fr.add_trace(go.Scatter(x=rsi.index, y=rsi, fill='tozeroy', name='RSI(14)',
                                         line=dict(color='#00D9FF')))
                fr.add_hline(y=70, line_dash="dash", line_color="red")
                fr.add_hline(y=30, line_dash="dash", line_color="green")
                fr.update_layout(template="plotly_dark", height=280, yaxis_range=[0, 100],
                                 margin=dict(l=0,r=0,t=20,b=0), title="RSI (14)")
                st.plotly_chart(fr, use_container_width=True)
            with c2:
                fm = go.Figure()
                fm.add_trace(go.Scatter(x=macd.index, y=macd, name='MACD', line=dict(color='#7C3AED')))
                fm.add_trace(go.Scatter(x=sig_macd.index, y=sig_macd, name='Signal', line=dict(color='#f59e0b')))
                fm.add_trace(go.Bar(x=hist.index, y=hist, name='Hist', marker_color='#475569'))
                fm.update_layout(template="plotly_dark", height=280,
                                 margin=dict(l=0,r=0,t=20,b=0), title="MACD")
                st.plotly_chart(fm, use_container_width=True)

            # Comparison
            st.markdown("### Multi-Ticker Comparison")
            peers = st.multiselect("Add tickers (max 5)", ["AAPL","MSFT","GOOGL","TSLA","AMZN","SPY","QQQ","NVDA"],
                                   default=[], max_selections=5, key="lm_peers")
            if peers:
                rows_c = _fetch_comparison(tuple([ticker] + peers))
                if rows_c:
                    st.dataframe(pd.DataFrame(rows_c), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error loading data: {e}")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — MACRO ANALYSIS (from macro_analysis.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_macro:
    try:
        from macro_dashboard import render_macro_dashboard
        MACRO_DASHBOARD_AVAILABLE = True
    except ImportError:
        MACRO_DASHBOARD_AVAILABLE = False

    if MACRO_DASHBOARD_AVAILABLE:
        render_macro_dashboard()
    else:
        st.error("Macro Dashboard is not available. Please ensure macro_dashboard module is installed.")
        st.info("Falling back to basic macro data view...")
        try:
            from macro_data import render_macro_tab
            render_macro_tab()
        except ImportError:
            st.warning("Basic macro view also unavailable.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — MARKET NEWS (from market_news.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_news:
    try:
        from news_module import render_news_module
        render_news_module()
    except ImportError:
        st.warning("News module not available. Please ensure news_module is installed.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — ALTERNATIVE DATA (from alt_data.py)
# ════════════════════════════════════════════════════════════════════════════════
with tab_alt:
    import yfinance as yf

    col_at1, col_at2 = st.columns([2, 1])
    with col_at1:
        sent_ticker = st.text_input("Ticker", value="AAPL", key="sent_ticker")
    with col_at2:
        sent_btn = st.button("Fetch News", key="sent_btn")

    if sent_btn and sent_ticker.strip():
        with st.spinner("Fetching news..."):
            try:
                t_s = yf.Ticker(sent_ticker.upper().strip())
                st.session_state["alt_news"] = (t_s.news or [])[:15]
                st.session_state["alt_ticker"] = sent_ticker.upper().strip()
            except Exception as e:
                st.error(f"Could not fetch news: {e}")

    if "alt_news" in st.session_state and st.session_state["alt_news"]:
        st.info("Connect your Anthropic API key to enable automatic Bullish/Bearish/Neutral classification.")
        st.markdown(f"### Latest News — {st.session_state.get('alt_ticker','')}")
        for item in st.session_state["alt_news"]:
            title = item.get("title", "No title")
            source = item.get("publisher", "Unknown")
            url = item.get("link", "#")
            try:
                dt_str = datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime("%Y-%m-%d %H:%M")
            except Exception:
                dt_str = "N/A"
            with st.expander(f"{title[:90]}..."):
                st.caption(f"Source: **{source}** | {dt_str}")
                st.markdown(f"[Read full article]({url})")

    st.divider()
    st.markdown("### Earnings Calendar")
    earn_ticker = st.text_input("Ticker", value="AAPL", key="earn_ticker")
    if st.button("Load Earnings", key="earn_btn"):
        try:
            t_e = yf.Ticker(earn_ticker.upper().strip())
            cal = t_e.calendar
            if cal is not None and not (isinstance(cal, dict) and not cal):
                if isinstance(cal, pd.DataFrame):
                    st.dataframe(cal, use_container_width=True)
                else:
                    st.json(cal)
            else:
                info_e = t_e.info
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Trailing EPS", f"${info_e.get('trailingEps','N/A')}")
                with m2:
                    st.metric("Forward EPS", f"${info_e.get('forwardEps','N/A')}")
                with m3:
                    ts_e = info_e.get("earningsTimestamp")
                    if ts_e:
                        st.metric("Next Earnings", datetime.fromtimestamp(ts_e).strftime("%Y-%m-%d"))
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()
    st.markdown("### Volatility Predictor — Earnings Impact")
    pred_ticker = st.text_input("Ticker", value="AAPL", key="pred_ticker")
    if st.button("Estimate Earnings Vol", key="pred_btn"):
        try:
            t_p = yf.Ticker(pred_ticker.upper().strip())
            hist_p = t_p.history(period="2y")
            if not hist_p.empty:
                rets_p = hist_p["Close"].pct_change().dropna()
                rv = float(rets_p.std() * np.sqrt(252))
                em = float(rets_p.abs().nlargest(8).mean())
                iv_p = t_p.info.get("impliedVolatility") or rv

                c1, c2, c3 = st.columns(3)
                c1.metric("Realized Vol (2Y)", f"{rv*100:.1f}%")
                c2.metric("Avg Top-8 Move", f"{em*100:.2f}%")
                c3.metric("Implied Vol", f"{iv_p*100:.1f}%" if isinstance(iv_p, float) else str(iv_p))
        except Exception as e:
            st.error(f"Error: {e}")
