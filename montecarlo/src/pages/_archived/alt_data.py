import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from _shared import _render_page_header

import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
import yfinance as yf

_render_page_header("AD", "Alternative Data & Sentiment", "News flow, earnings calendar and volatility signal monitor", "Alt Data")

col_at1, col_at2 = st.columns([2, 1])
with col_at1:
    sent_ticker = st.text_input("Ticker", value="AAPL", key="sent_ticker")
with col_at2:
    sent_btn = st.button("Fetch News", key="sent_btn", width="stretch")

if sent_btn and sent_ticker.strip():
    with st.spinner("Fetching news…"):
        try:
            t_s = yf.Ticker(sent_ticker.upper().strip())
            st.session_state["alt_news"] = (t_s.news or [])[:15]
            st.session_state["alt_ticker"] = sent_ticker.upper().strip()
        except Exception as e:
            st.error(f"Could not fetch news: {e}")

if "alt_news" in st.session_state and st.session_state["alt_news"]:
    st.info("Connect your Anthropic API key to enable automatic Bullish/Bearish/Neutral classification and vol impact prediction.")
    st.markdown(f"### Latest News — {st.session_state.get('alt_ticker','')}")
    for item in st.session_state["alt_news"]:
        title  = item.get("title", "No title")
        source = item.get("publisher", "Unknown")
        url    = item.get("link", "#")
        try:
            dt_str = datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime("%Y-%m-%d %H:%M")
        except Exception:
            dt_str = "N/A"
        with st.expander(f"{title[:90]}…"):
            st.caption(f"Source: **{source}** | {dt_str}")
            st.markdown(f"[Read full article →]({url})")

st.divider()
st.markdown("### Earnings Calendar")
earn_ticker = st.text_input("Ticker", value="AAPL", key="earn_ticker")
if st.button("Load Earnings", key="earn_btn"):
    try:
        t_e = yf.Ticker(earn_ticker.upper().strip())
        cal = t_e.calendar
        if cal is not None and not (isinstance(cal, dict) and not cal):
            if isinstance(cal, pd.DataFrame):
                st.dataframe(cal, width="stretch")
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
        t_p  = yf.Ticker(pred_ticker.upper().strip())
        hist_p = t_p.history(period="2y")
        if not hist_p.empty:
            rets_p = hist_p["Close"].pct_change().dropna()
            rv = float(rets_p.std() * np.sqrt(252))
            em = float(rets_p.abs().nlargest(8).mean())
            iv_p = t_p.info.get("impliedVolatility") or rv
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.metric("Realized Vol (1Y)", f"{rv*100:.1f}%")
            with m2: st.metric("Current IV (approx)", f"{float(iv_p)*100:.1f}%")
            with m3: st.metric("Avg Top-8 Daily Move", f"{em*100:.2f}%")
            with m4: st.metric("Expected Earnings Move", f"±{em*np.sqrt(252/8)*100:.1f}%")
    except Exception as e:
        st.error(f"Error: {e}")
