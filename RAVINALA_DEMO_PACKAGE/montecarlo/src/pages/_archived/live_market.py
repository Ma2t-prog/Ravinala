import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

_render_page_header("LM", "Live Market Dashboard", "Real-time prices, volatility and technical surveillance", "Live")

import yfinance as yf
from scipy.stats import norm

def _flatten(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# ── CACHED FETCHERS ────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def _fetch_ticker_data(ticker: str):
    """Fetch 1Y daily + info in one shot. Cached 5 min."""
    tk = yf.Ticker(ticker)
    data = _flatten(yf.download(ticker, period="1y", progress=False, interval="1d"))
    info = tk.fast_info  # fast_info is much faster than .info
    return data, dict(info)

@st.cache_data(ttl=300)
def _fetch_chart(ticker: str, period: str):
    return _flatten(yf.download(ticker, period=period, progress=False))

@st.cache_data(ttl=300)
def _fetch_comparison(tickers: tuple):
    rows = []
    for t in tickers:
        try:
            d = _flatten(yf.download(t, period="1y", progress=False, interval="1d"))
            if d.empty:
                continue
            fi = yf.Ticker(t).fast_info
            price = getattr(fi, 'last_price', None) or float(d['Close'].iloc[-1])
            ytd = (float(d['Close'].iloc[-1]) - float(d['Close'].iloc[0])) / float(d['Close'].iloc[0]) * 100
            iv  = float(d['Close'].pct_change().std()) * np.sqrt(252) * 100
            rows.append({'Ticker': t, 'Price': f"${price:.2f}", 'YTD%': f"{ytd:.2f}%", 'IV%': f"{iv:.2f}%"})
        except:
            pass
    return rows

@st.cache_data(ttl=300)
def _fetch_benchmark(ticker: str, bench: str):
    t1 = _flatten(yf.download(ticker, period="1y", progress=False))
    b1 = _flatten(yf.download(bench,  period="1y", progress=False))
    return t1, b1

# ── CONTROLS ───────────────────────────────────────────────────────────────

ticker = st.text_input("Ticker (e.g. AAPL, MSFT, EURUSD=X)", "AAPL", key="live_ticker")

if ticker:
    try:
        data, fi = _fetch_ticker_data(ticker)

        if data.empty:
            st.error("No data returned. Check the ticker symbol.")
            st.stop()

        _close = data['Close']
        price  = getattr(yf.Ticker(ticker).fast_info, 'last_price', None) or float(_close.iloc[-1])
        price  = float(price)
        price_prev = float(_close.iloc[-2]) if len(data) > 1 else price
        change_1d  = (price - price_prev) / price_prev * 100 if price_prev else 0
        currency   = getattr(yf.Ticker(ticker).fast_info, 'currency', 'USD') or 'USD'

        # ── SECTION 1: KEY METRICS ─────────────────────────────────────────
        st.markdown("### Key Metrics")
        c1, c2, c3, c4, c5 = st.columns(5)
        mktcap = getattr(yf.Ticker(ticker).fast_info, 'market_cap', 0) or 0
        c1.metric("Price",      f"${price:.2f} {currency}", f"{change_1d:+.2f}%")
        c2.metric("Market Cap", f"${mktcap/1e9:.1f}B" if mktcap else "N/A")
        c3.metric("52W High",   f"${getattr(yf.Ticker(ticker).fast_info,'year_high',0) or 0:.2f}")
        c4.metric("52W Low",    f"${getattr(yf.Ticker(ticker).fast_info,'year_low',0) or 0:.2f}")
        c5.metric("Vol Rank",   "–")  # lightweight placeholder

        # ── SECTION 2: VOLATILITY ──────────────────────────────────────────
        st.markdown("### Volatility Analysis")
        returns = _close.pct_change().dropna()
        hv_30  = float(returns.tail(30).std()) * np.sqrt(252) * 100
        hv_90  = float(returns.tail(90).std()) * np.sqrt(252) * 100
        hv_1y  = float(returns.std())          * np.sqrt(252) * 100

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("HV 30D", f"{hv_30:.2f}%")
        c2.metric("HV 90D", f"{hv_90:.2f}%")
        c3.metric("HV 1Y",  f"{hv_1y:.2f}%")
        c4.metric("Vol Percentile", f"{hv_30/hv_1y*100:.0f}th %ile" if hv_1y else "N/A")

        # ── SECTION 3: GREEKS CALCULATOR ──────────────────────────────────
        st.markdown("### Options Greeks (Black-Scholes)")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            strike = st.slider("Strike K", float(price*0.8), float(price*1.2), float(price),
                                step=float(max(0.5, price*0.005)))
        with c2:
            dte = st.slider("Days to Expiry", 1, 365, 30)
        with c3:
            vol_pct = st.slider("Vol (%)", 5, 200, max(5, min(200, int(hv_30 or 25)))) / 100
        with c4:
            rfr = st.slider("Risk-Free (%)", 0, 10, 5) / 100
        with c5:
            opt = st.radio("Type", ["Call", "Put"], horizontal=True)

        T = dte / 365
        if vol_pct > 0 and T > 0:
            d1 = (np.log(price/strike) + (rfr + 0.5*vol_pct**2)*T) / (vol_pct*np.sqrt(T))
            d2 = d1 - vol_pct*np.sqrt(T)
            if opt == "Call":
                delta_v = norm.cdf(d1)
                prem    = price*norm.cdf(d1) - strike*np.exp(-rfr*T)*norm.cdf(d2)
                theta_v = (-price*norm.pdf(d1)*vol_pct/(2*np.sqrt(T)) -
                           rfr*strike*np.exp(-rfr*T)*norm.cdf(d2)) / 365
            else:
                delta_v = norm.cdf(d1) - 1
                prem    = strike*np.exp(-rfr*T)*norm.cdf(-d2) - price*norm.cdf(-d1)
                theta_v = (-price*norm.pdf(d1)*vol_pct/(2*np.sqrt(T)) +
                           rfr*strike*np.exp(-rfr*T)*norm.cdf(-d2)) / 365
            gamma_v = norm.pdf(d1) / (price*vol_pct*np.sqrt(T))
            vega_v  = price*norm.pdf(d1)*np.sqrt(T) / 100
            rho_v   = (strike*T*np.exp(-rfr*T)*norm.cdf(d2) if opt == "Call"
                       else -strike*T*np.exp(-rfr*T)*norm.cdf(-d2)) / 100
            c1,c2,c3,c4,c5,c6 = st.columns(6)
            c1.metric("Premium", f"${prem:.2f}")
            c2.metric("Delta Δ", f"{delta_v:.3f}")
            c3.metric("Gamma Γ", f"{gamma_v:.4f}")
            c4.metric("Vega ν",  f"{vega_v:.3f}")
            c5.metric("Theta Θ", f"{theta_v:.4f}")
            c6.metric("Rho ρ",   f"{rho_v:.3f}")

        # ── SECTION 4: PRICE CHART ─────────────────────────────────────────
        st.markdown("### Price Chart")
        period_map = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y"}
        chart_period = st.selectbox("Period", list(period_map.keys()), index=3)
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

        # ── SECTION 5: TECHNICALS ─────────────────────────────────────────
        st.markdown("### Technical Indicators")
        diff  = _close.diff()
        gain  = diff.where(diff>0, 0).rolling(14).mean()
        loss  = (-diff.where(diff<0, 0)).rolling(14).mean()
        rsi   = 100 - (100/(1 + gain/loss))
        exp1  = _close.ewm(span=12, adjust=False).mean()
        exp2  = _close.ewm(span=26, adjust=False).mean()
        macd  = exp1 - exp2
        sig   = macd.ewm(span=9, adjust=False).mean()
        hist  = macd - sig

        c1, c2 = st.columns(2)
        with c1:
            fr = go.Figure()
            fr.add_trace(go.Scatter(x=rsi.index, y=rsi, fill='tozeroy', name='RSI(14)', line=dict(color='#00D9FF')))
            fr.add_hline(y=70, line_dash="dash", line_color="red")
            fr.add_hline(y=30, line_dash="dash", line_color="green")
            fr.update_layout(template="plotly_dark", height=280, yaxis_range=[0,100],
                             margin=dict(l=0,r=0,t=20,b=0), title="RSI (14)")
            st.plotly_chart(fr, use_container_width=True)
        with c2:
            fm = go.Figure()
            fm.add_trace(go.Scatter(x=macd.index, y=macd, name='MACD', line=dict(color='#7C3AED')))
            fm.add_trace(go.Scatter(x=sig.index, y=sig, name='Signal', line=dict(color='#f59e0b')))
            fm.add_trace(go.Bar(x=hist.index, y=hist, name='Hist', marker_color='#475569'))
            fm.update_layout(template="plotly_dark", height=280,
                             margin=dict(l=0,r=0,t=20,b=0), title="MACD")
            st.plotly_chart(fm, use_container_width=True)

        # ── SECTION 6: COMPARISON ─────────────────────────────────────────
        st.markdown("### Multi-Ticker Comparison")
        peers = st.multiselect("Add tickers (max 5)", ["AAPL","MSFT","GOOGL","TSLA","AMZN","SPY","QQQ","NVDA"],
                               default=[], max_selections=5)
        if peers:
            rows = _fetch_comparison(tuple([ticker] + peers))
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # ── SECTION 7: BENCHMARK ──────────────────────────────────────────
        st.markdown("### Relative Performance vs Benchmark")
        bench_map = {"S&P 500 (SPY)": "SPY", "Nasdaq 100 (QQQ)": "QQQ", "Russell 2000 (IWM)": "IWM"}
        bench_name = st.selectbox("Benchmark", list(bench_map.keys()))
        bench_tk = bench_map[bench_name]
        try:
            t1y, b1y = _fetch_benchmark(ticker, bench_tk)
            if not t1y.empty and not b1y.empty:
                tp = (float(t1y['Close'].iloc[-1]) - float(t1y['Close'].iloc[0])) / float(t1y['Close'].iloc[0]) * 100
                bp = (float(b1y['Close'].iloc[-1]) - float(b1y['Close'].iloc[0])) / float(b1y['Close'].iloc[0]) * 100
                c1, c2, c3 = st.columns(3)
                c1.metric(f"{ticker} 1Y", f"{tp:.2f}%")
                c2.metric(bench_tk+" 1Y", f"{bp:.2f}%")
                c3.metric("Alpha", f"{tp-bp:+.2f}%")
                fp = go.Figure()
                fp.add_trace(go.Scatter(x=t1y.index, y=(1+t1y['Close'].pct_change()).cumprod(), name=ticker, line=dict(color='#00D9FF')))
                fp.add_trace(go.Scatter(x=b1y.index, y=(1+b1y['Close'].pct_change()).cumprod(), name=bench_tk, line=dict(color='#f59e0b')))
                fp.update_layout(template="plotly_dark", height=320,
                                 margin=dict(l=0,r=0,t=20,b=0), title="1Y Cumulative Return")
                st.plotly_chart(fp, use_container_width=True)
        except:
            st.warning("Could not fetch benchmark data.")

        # ── SECTION 8: EXPORT ─────────────────────────────────────────────
        with st.expander("Data Export"):
            ep = st.selectbox("Period", ["1Y","3Y","5Y"], key="export_period")
            export_data = _fetch_chart(ticker, {"1Y":"1y","3Y":"3y","5Y":"5y"}[ep])
            st.download_button(f"Download {ep} CSV", export_data.to_csv(),
                               f"{ticker}_{ep}.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}")
