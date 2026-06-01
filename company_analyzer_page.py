if selected == "🏢  Company Analyzer":

    import yfinance as yf
    from datetime import datetime, timedelta

    # ── helpers ────────────────────────────────────────────────────────────────
    CHART_LAYOUT = dict(
        paper_bgcolor="#07080d",
        plot_bgcolor="#07080d",
        font=dict(color="#9ca3af"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", showgrid=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", showgrid=True),
        margin=dict(l=40, r=20, t=40, b=40),
    )
    GREEN  = "#10b981"
    RED    = "#ef4444"
    ACCENT = "#6366f1"
    YELLOW = "#f59e0b"

    def _safe_val(info, *keys, default=None):
        for k in keys:
            v = info.get(k)
            if v is not None and v != "N/A":
                return v
        return default

    def _fmt_large(val, symbol=CURRENCY_SYMBOL):
        if val is None:
            return "N/A"
        abs_v = abs(val)
        if abs_v >= 1e12:
            return f"{symbol}{val/1e12:.2f}T"
        if abs_v >= 1e9:
            return f"{symbol}{val/1e9:.2f}B"
        if abs_v >= 1e6:
            return f"{symbol}{val/1e6:.2f}M"
        return f"{symbol}{val:,.0f}"

    def _get_fx_rate(from_currency: str, to_currency: str) -> float:
        if from_currency == to_currency:
            return 1.0
        try:
            pair = f"{from_currency}{to_currency}=X"
            t = yf.Ticker(pair)
            hist = t.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
            info = t.info
            rate = info.get("regularMarketPrice") or info.get("previousClose")
            if rate:
                return float(rate)
        except Exception:
            pass
        return 1.0

    def _dcf_single(fcf_base, g1, g2, g_t, wacc, shares, net_debt):
        fcfs = []
        cf = fcf_base
        for yr in range(1, 11):
            g = g1 if yr <= 5 else g2
            cf = cf * (1 + g)
            fcfs.append(cf)
        tv = fcfs[-1] * (1 + g_t) / max(wacc - g_t, 0.001)
        pv_fcfs = sum(f / (1 + wacc) ** (i + 1) for i, f in enumerate(fcfs))
        pv_tv   = tv / (1 + wacc) ** 10
        ev      = pv_fcfs + pv_tv
        eq_val  = ev - net_debt
        ivps    = eq_val / shares if shares and shares > 0 else 0
        return fcfs, pv_fcfs, pv_tv, ev, eq_val, ivps

    # ── top controls ───────────────────────────────────────────────────────────
    st.markdown("## 🏢 Company Analyzer")

    col_ticker, col_curr, col_btn = st.columns([3, 2, 1])
    with col_ticker:
        ticker_input = st.text_input("Ticker Symbol", value=st.session_state.get("ca_ticker", "AAPL"),
                                     placeholder="e.g. AAPL, MSFT, TSLA", label_visibility="collapsed",
                                     key="ca_ticker_input")
    with col_curr:
        currency_choice = st.selectbox("Currency", ["USD 🇺🇸", "EUR 🇪🇺", "GBP 🇬🇧", "JPY 🇯🇵"],
                                       index=0, label_visibility="collapsed", key="ca_currency_input")
    with col_btn:
        analyze_clicked = st.button("🔍 Analyze", use_container_width=True)

    selected_currency = currency_choice.split()[0]   # "USD", "EUR", etc.

    if analyze_clicked and ticker_input.strip():
        ticker_sym = ticker_input.strip().upper()
        with st.spinner(f"Fetching data for {ticker_sym} …"):
            try:
                t = yf.Ticker(ticker_sym)
                info = t.info

                # currency of the ticker itself
                ticker_currency = info.get("currency", "USD") or "USD"
                fx_rate = _get_fx_rate(ticker_currency, selected_currency)

                # financials
                try:
                    income_stmt = t.income_stmt
                except Exception:
                    income_stmt = pd.DataFrame()
                try:
                    balance_sheet = t.balance_sheet
                except Exception:
                    balance_sheet = pd.DataFrame()
                try:
                    cashflow = t.cashflow
                except Exception:
                    cashflow = pd.DataFrame()
                try:
                    hist_1y = t.history(period="1y")
                except Exception:
                    hist_1y = pd.DataFrame()
                try:
                    inst_holders = t.institutional_holders
                except Exception:
                    inst_holders = pd.DataFrame()
                try:
                    insider_tx = t.insider_transactions
                except Exception:
                    insider_tx = pd.DataFrame()
                try:
                    rec_summary = t.recommendations_summary
                except Exception:
                    rec_summary = pd.DataFrame()

                st.session_state["company_data"] = {
                    "ticker":          ticker_sym,
                    "info":            info,
                    "fx_rate":         fx_rate,
                    "selected_currency": selected_currency,
                    "ticker_currency": ticker_currency,
                    "income_stmt":     income_stmt,
                    "balance_sheet":   balance_sheet,
                    "cashflow":        cashflow,
                    "hist_1y":         hist_1y,
                    "inst_holders":    inst_holders,
                    "insider_tx":      insider_tx,
                    "rec_summary":     rec_summary,
                    "updated_at":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            except Exception as e:
                st.error(f"Failed to fetch data for '{ticker_input}': {e}")

    # ── guard: no data yet ─────────────────────────────────────────────────────
    if "company_data" not in st.session_state:
        st.info("Enter a ticker symbol and click **🔍 Analyze** to begin.")
        st.stop()

    cd          = st.session_state["company_data"]
    info        = cd["info"]
    fx          = cd["fx_rate"]
    sel_cur     = cd["selected_currency"]
    cur_sym     = CURRENCY_SYMBOL
    income_stmt = cd["income_stmt"]
    balance_sheet = cd["balance_sheet"]
    cashflow    = cd["cashflow"]
    hist_1y     = cd["hist_1y"]
    inst_holders = cd["inst_holders"]
    insider_tx  = cd["insider_tx"]
    rec_summary = cd["rec_summary"]

    # ── company header ─────────────────────────────────────────────────────────
    company_name = info.get("longName") or info.get("shortName") or cd["ticker"]
    sector       = info.get("sector", "N/A")
    exchange     = info.get("exchange", "N/A")
    st.markdown(f"### {company_name}")
    st.caption(f"**Sector:** {sector}  |  **Exchange:** {exchange}  |  **Currency displayed:** {sel_cur}  |  *Last updated: {cd['updated_at']}*")
    st.divider()

    # ── 5 tabs ─────────────────────────────────────────────────────────────────
    tab_ov, tab_fin, tab_dcf, tab_hr, tab_own = st.tabs(
        ["📊 Overview", "📋 Financials", "💰 DCF Valuation", "🏦 Health & Risk", "👥 Ownership"]
    )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 – OVERVIEW
    # ══════════════════════════════════════════════════════════════════════════
    with tab_ov:
        st.subheader("Key Metrics")

        market_cap_raw = _safe_val(info, "marketCap")
        market_cap     = (market_cap_raw * fx) if market_cap_raw else None
        pe             = _safe_val(info, "trailingPE", "forwardPE")
        ev_ebitda      = _safe_val(info, "enterpriseToEbitda")
        pb             = _safe_val(info, "priceToBook")
        div_yield      = _safe_val(info, "dividendYield")
        low_52         = _safe_val(info, "fiftyTwoWeekLow")
        high_52        = _safe_val(info, "fiftyTwoWeekHigh")
        curr_price_raw = _safe_val(info, "currentPrice", "regularMarketPrice", "previousClose")
        curr_price     = (curr_price_raw * fx) if curr_price_raw else None

        c1, c2, c3 = st.columns(3)
        c4, c5, c6 = st.columns(3)
        c1.metric("Market Cap", _fmt_large(market_cap, cur_sym) if market_cap else "N/A")
        c2.metric("P/E Ratio (Trailing)", f"{pe:.2f}" if pe else "N/A")
        c3.metric("EV / EBITDA", f"{ev_ebitda:.2f}x" if ev_ebitda else "N/A")
        c4.metric("Price / Book", f"{pb:.2f}x" if pb else "N/A")
        c5.metric("Dividend Yield", f"{div_yield*100:.2f}%" if div_yield else "N/A")
        if low_52 and high_52:
            low_disp  = f"{cur_sym}{low_52*fx:,.2f}"
            high_disp = f"{cur_sym}{high_52*fx:,.2f}"
            c6.metric("52-Week Range", f"{low_disp} – {high_disp}")
        else:
            c6.metric("52-Week Range", "N/A")

        # ── candlestick chart ──────────────────────────────────────────────────
        st.subheader("Price Chart (1 Year)")
        if not hist_1y.empty:
            try:
                fig_price = go.Figure(data=[go.Candlestick(
                    x=hist_1y.index,
                    open=hist_1y["Open"]  * fx,
                    high=hist_1y["High"]  * fx,
                    low=hist_1y["Low"]   * fx,
                    close=hist_1y["Close"] * fx,
                    increasing_line_color=GREEN,
                    decreasing_line_color=RED,
                    name="Price",
                )])
                fig_price.update_layout(
                    **CHART_LAYOUT,
                    title=f"{cd['ticker']} – 1Y Candlestick ({sel_cur})",
                    xaxis_rangeslider_visible=False,
                    height=380,
                )
                st.plotly_chart(fig_price, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not render price chart: {e}")
        else:
            st.info("No price history available.")

        # ── analyst consensus ──────────────────────────────────────────────────
        st.subheader("Analyst Consensus")
        target_mean = _safe_val(info, "targetMeanPrice")
        n_analysts  = _safe_val(info, "numberOfAnalystOpinions")
        rec_key     = _safe_val(info, "recommendationKey", default="")

        ca1, ca2, ca3 = st.columns(3)
        if target_mean and curr_price_raw:
            tgt_disp  = f"{cur_sym}{target_mean*fx:,.2f}"
            upside    = (target_mean - curr_price_raw) / curr_price_raw * 100
            upside_str = f"{upside:+.1f}%"
            delta_col = GREEN if upside >= 0 else RED
        else:
            tgt_disp   = "N/A"
            upside_str = "N/A"
            delta_col  = "#9ca3af"

        ca1.metric("Avg Target Price", tgt_disp)
        ca2.metric("Upside / Downside vs Current", upside_str)
        ca3.metric("Analyst Count", str(n_analysts) if n_analysts else "N/A")

        # recommendation breakdown bar
        buy_count  = _safe_val(info, "recommendationMean")  # fallback
        strong_buy = _safe_val(info, "numberOfStrongBuyAnalystOpinions", default=0) or 0
        buy_r      = _safe_val(info, "numberOfBuyAnalystOpinions",       default=0) or 0
        hold_r     = _safe_val(info, "numberOfHoldAnalystOpinions",      default=0) or 0
        sell_r     = _safe_val(info, "numberOfSellAnalystOpinions",      default=0) or 0
        strong_sell= _safe_val(info, "numberOfStrongSellAnalystOpinions",default=0) or 0

        total_recs = strong_buy + buy_r + hold_r + sell_r + strong_sell
        if total_recs == 0 and not rec_summary.empty:
            try:
                latest = rec_summary.iloc[0]
                strong_buy  = int(latest.get("strongBuy",  0) or 0)
                buy_r       = int(latest.get("buy",        0) or 0)
                hold_r      = int(latest.get("hold",       0) or 0)
                sell_r      = int(latest.get("sell",       0) or 0)
                strong_sell = int(latest.get("strongSell", 0) or 0)
                total_recs  = strong_buy + buy_r + hold_r + sell_r + strong_sell
            except Exception:
                pass

        if total_recs > 0:
            fig_rec = go.Figure()
            fig_rec.add_trace(go.Bar(
                y=["Analyst Ratings"],
                x=[strong_buy + buy_r],
                name="Buy",
                orientation="h",
                marker_color=GREEN,
            ))
            fig_rec.add_trace(go.Bar(
                y=["Analyst Ratings"],
                x=[hold_r],
                name="Hold",
                orientation="h",
                marker_color=YELLOW,
            ))
            fig_rec.add_trace(go.Bar(
                y=["Analyst Ratings"],
                x=[sell_r + strong_sell],
                name="Sell",
                orientation="h",
                marker_color=RED,
            ))
            fig_rec.update_layout(
                **CHART_LAYOUT,
                barmode="stack",
                height=130,
                showlegend=True,
                legend=dict(orientation="h", y=1.5),
                title="Buy / Hold / Sell Breakdown",
                margin=dict(l=20, r=20, t=50, b=10),
            )
            st.plotly_chart(fig_rec, use_container_width=True)
        else:
            st.info("No analyst rating breakdown available.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 – FINANCIALS
    # ══════════════════════════════════════════════════════════════════════════
    with tab_fin:
        fs1, fs2, fs3 = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow"])

        def _prepare_stmt(df: pd.DataFrame) -> pd.DataFrame:
            """Transpose, keep last 4 cols, convert to M with FX."""
            if df is None or df.empty:
                return pd.DataFrame()
            df = df.T
            df = df.iloc[:4] if len(df) >= 4 else df
            df = df.apply(pd.to_numeric, errors="coerce") * fx / 1e6
            df.index = [str(i)[:10] for i in df.index]
            return df.sort_index()

        def _yoy(series: pd.Series) -> str:
            vals = series.dropna()
            if len(vals) < 2:
                return "N/A"
            g = (vals.iloc[-1] - vals.iloc[0]) / abs(vals.iloc[0]) * 100
            sign = "+" if g >= 0 else ""
            return f"{sign}{g:.1f}%"

        def _bar_chart(df, rows, title, colors=None):
            if df.empty:
                return None
            fig = go.Figure()
            if colors is None:
                colors = [ACCENT, GREEN, RED]
            for i, row in enumerate(rows):
                if row in df.columns:
                    clr = colors[i % len(colors)]
                    fig.add_trace(go.Bar(
                        name=row,
                        x=df.index.tolist(),
                        y=df[row].tolist(),
                        marker_color=clr,
                    ))
            fig.update_layout(**CHART_LAYOUT, barmode="group", title=title, height=350)
            return fig

        # ── Income Statement ──────────────────────────────────────────────────
        with fs1:
            is_df = _prepare_stmt(income_stmt)
            if not is_df.empty:
                rev_key  = next((c for c in is_df.columns if "Total Revenue" in c or "Revenue" in c), None)
                gp_key   = next((c for c in is_df.columns if "Gross Profit" in c), None)
                ni_key   = next((c for c in is_df.columns if "Net Income" in c), None)

                if rev_key:
                    st.metric("Revenue YoY (oldest→latest)", _yoy(is_df[rev_key]))
                if ni_key:
                    st.metric("Net Income YoY (oldest→latest)", _yoy(is_df[ni_key]))

                st.dataframe(
                    is_df.style.format("{:,.1f}", na_rep="N/A"),
                    use_container_width=True,
                )

                chart_rows = [r for r in [rev_key, gp_key, ni_key] if r]
                if chart_rows:
                    fig_is = _bar_chart(is_df, chart_rows, f"IS Key Metrics ({sel_cur} M)")
                    if fig_is:
                        st.plotly_chart(fig_is, use_container_width=True)
            else:
                st.info("Income statement data not available.")

        # ── Balance Sheet ─────────────────────────────────────────────────────
        with fs2:
            bs_df = _prepare_stmt(balance_sheet)
            if not bs_df.empty:
                ta_key  = next((c for c in bs_df.columns if "Total Assets" in c), None)
                tl_key  = next((c for c in bs_df.columns if "Total Liab" in c or "Total Liabilities" in c), None)
                eq_key  = next((c for c in bs_df.columns if "Stockholders" in c or "Total Equity" in c or "Common Stock Equity" in c), None)

                st.dataframe(
                    bs_df.style.format("{:,.1f}", na_rep="N/A"),
                    use_container_width=True,
                )
                chart_rows = [r for r in [ta_key, tl_key, eq_key] if r]
                if chart_rows:
                    fig_bs = _bar_chart(bs_df, chart_rows,
                                        f"BS Key Metrics ({sel_cur} M)",
                                        [ACCENT, RED, GREEN])
                    if fig_bs:
                        st.plotly_chart(fig_bs, use_container_width=True)
            else:
                st.info("Balance sheet data not available.")

        # ── Cash Flow ─────────────────────────────────────────────────────────
        with fs3:
            cf_df = _prepare_stmt(cashflow)
            if not cf_df.empty:
                ocf_key = next((c for c in cf_df.columns if "Operating" in c and "Cash" in c), None)
                icf_key = next((c for c in cf_df.columns if "Investing" in c), None)
                fcf_key = next((c for c in cf_df.columns if "Financing" in c), None)

                st.dataframe(
                    cf_df.style.format("{:,.1f}", na_rep="N/A"),
                    use_container_width=True,
                )
                # waterfall-style: pos=green, neg=red per bar
                if ocf_key or icf_key or fcf_key:
                    fig_cf = go.Figure()
                    for key, label in [(ocf_key, "Operating CF"), (icf_key, "Investing CF"), (fcf_key, "Financing CF")]:
                        if key and key in cf_df.columns:
                            vals = cf_df[key].tolist()
                            fig_cf.add_trace(go.Bar(
                                name=label,
                                x=cf_df.index.tolist(),
                                y=vals,
                                marker_color=[GREEN if v >= 0 else RED for v in vals],
                            ))
                    fig_cf.update_layout(**CHART_LAYOUT, barmode="group",
                                         title=f"Cash Flow Key Metrics ({sel_cur} M)", height=350)
                    st.plotly_chart(fig_cf, use_container_width=True)
            else:
                st.info("Cash flow data not available.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 – DCF VALUATION
    # ══════════════════════════════════════════════════════════════════════════
    with tab_dcf:
        st.subheader("2-Stage DCF Valuation")

        d1, d2, d3, d4, d5 = st.columns(5)
        g1        = d1.number_input("Stage 1 Growth (Yr 1-5)", value=10.0, min_value=-50.0, max_value=100.0, step=0.5, format="%.1f") / 100
        g2        = d2.number_input("Stage 2 Growth (Yr 6-10)", value=6.0,  min_value=-50.0, max_value=100.0, step=0.5, format="%.1f") / 100
        g_terminal= d3.number_input("Terminal Growth Rate",      value=2.5,  min_value=0.0,   max_value=10.0,  step=0.1, format="%.1f") / 100
        wacc      = d4.number_input("WACC",                      value=10.0, min_value=1.0,   max_value=50.0,  step=0.1, format="%.1f") / 100
        n_mc      = d5.number_input("MC Simulations",            value=3000, min_value=500,   max_value=20000, step=500)

        # ── derive FCF base ────────────────────────────────────────────────────
        fcf_base = None
        try:
            if not cashflow.empty:
                ocf_row  = next((r for r in cashflow.index if "Operating" in r and "Cash" in r), None)
                capex_row= next((r for r in cashflow.index if "Capital Expenditure" in r or "Capex" in r), None)
                if ocf_row:
                    ocf_val = cashflow.loc[ocf_row].iloc[0]
                    capex_val = cashflow.loc[capex_row].iloc[0] if capex_row else 0
                    fcf_base = float(ocf_val - abs(capex_val)) * fx
        except Exception:
            fcf_base = None

        if not fcf_base or fcf_base <= 0:
            try:
                if not income_stmt.empty:
                    ebitda_row = next((r for r in income_stmt.index if "EBITDA" in r), None)
                    if ebitda_row:
                        fcf_base = float(income_stmt.loc[ebitda_row].iloc[0]) * 0.75 * fx
            except Exception:
                fcf_base = None

        shares_out = _safe_val(info, "sharesOutstanding")
        total_debt = _safe_val(info, "totalDebt", default=0) or 0
        cash_val   = _safe_val(info, "totalCash", "cash", default=0) or 0
        net_debt   = (total_debt - cash_val) * fx

        if fcf_base and shares_out and shares_out > 0:
            fcfs, pv_fcfs, pv_tv, ev_dcf, eq_val, ivps = _dcf_single(
                fcf_base, g1, g2, g_terminal, wacc, shares_out, net_debt
            )

            # ── summary metrics ────────────────────────────────────────────────
            curr_p = (_safe_val(info, "currentPrice", "regularMarketPrice") or 0) * fx
            upside_pct = ((ivps - curr_p) / curr_p * 100) if curr_p else 0

            if abs(upside_pct) <= 15:
                valuation_label = "🟡 FAIRLY VALUED"
                val_color = YELLOW
            elif ivps > curr_p:
                valuation_label = "🟢 UNDERVALUED"
                val_color = GREEN
            else:
                valuation_label = "🔴 OVERVALUED"
                val_color = RED

            st.markdown(f"<h2 style='color:{val_color};text-align:center'>{valuation_label}</h2>",
                        unsafe_allow_html=True)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("FCF Base (Current Year)", _fmt_large(fcf_base, cur_sym))
            m2.metric("Enterprise Value (DCF)", _fmt_large(ev_dcf, cur_sym))
            m3.metric("Equity Value (DCF)", _fmt_large(eq_val, cur_sym))
            m4.metric("Intrinsic Value / Share", f"{cur_sym}{ivps:,.2f}",
                      delta=f"{upside_pct:+.1f}% vs current {cur_sym}{curr_p:,.2f}")

            # ── FCF projections bar chart ──────────────────────────────────────
            years = [f"Yr {i+1}" for i in range(10)]
            fig_fcf = go.Figure(go.Bar(
                x=years, y=[v / 1e9 for v in fcfs],
                marker_color=[ACCENT if i < 5 else GREEN for i in range(10)],
                text=[f"{cur_sym}{v/1e9:.2f}B" for v in fcfs],
                textposition="outside",
            ))
            fig_fcf.update_layout(**CHART_LAYOUT, title=f"Projected FCF ({sel_cur} B)",
                                   height=340)
            st.plotly_chart(fig_fcf, use_container_width=True)

            # ── waterfall chart ────────────────────────────────────────────────
            wf_labels  = ["PV of FCFs", "PV of Terminal Value", "Enterprise Value",
                          "Net Debt", "Equity Value", "Intrinsic Value/Share"]
            wf_values  = [pv_fcfs / 1e9, pv_tv / 1e9, 0,
                          -net_debt / 1e9, 0, ivps]
            wf_measures= ["relative", "relative", "total",
                          "relative", "total", "absolute"]
            fig_wf = go.Figure(go.Waterfall(
                name="DCF Bridge",
                orientation="v",
                measure=wf_measures,
                x=wf_labels,
                y=wf_values,
                connector={"line": {"color": "rgba(255,255,255,0.2)"}},
                increasing_marker_color=GREEN,
                decreasing_marker_color=RED,
                totals_marker_color=ACCENT,
            ))
            fig_wf.update_layout(**CHART_LAYOUT, title="DCF Value Bridge",
                                  height=380, showlegend=False)
            st.plotly_chart(fig_wf, use_container_width=True)

            # ── Monte Carlo DCF ────────────────────────────────────────────────
            st.subheader("Monte Carlo DCF Simulation")
            np.random.seed(42)
            n_sims    = int(n_mc)
            g1_sims   = np.random.normal(g1,        0.03,  n_sims)
            g2_sims   = np.random.normal(g2,        0.02,  n_sims)
            wacc_sims = np.random.normal(wacc,      0.015, n_sims).clip(0.03, 0.30)
            g_t_sims  = np.random.normal(g_terminal,0.005, n_sims).clip(0.005, 0.04)

            # vectorised DCF
            ivps_sims = np.zeros(n_sims)
            for idx in range(n_sims):
                try:
                    _, _, _, _, _, v = _dcf_single(
                        fcf_base, g1_sims[idx], g2_sims[idx],
                        g_t_sims[idx], wacc_sims[idx], shares_out, net_debt
                    )
                    ivps_sims[idx] = v
                except Exception:
                    ivps_sims[idx] = np.nan

            ivps_clean = ivps_sims[np.isfinite(ivps_sims)]

            pct_underval = (np.sum(ivps_clean > curr_p) / len(ivps_clean) * 100) if len(ivps_clean) > 0 else 0

            pc1, pc2, pc3, pc4, pc5 = st.columns(5)
            pc1.metric("P10",  f"{cur_sym}{np.percentile(ivps_clean,10):,.2f}")
            pc2.metric("P25",  f"{cur_sym}{np.percentile(ivps_clean,25):,.2f}")
            pc3.metric("P50 (Median)", f"{cur_sym}{np.percentile(ivps_clean,50):,.2f}")
            pc4.metric("P75",  f"{cur_sym}{np.percentile(ivps_clean,75):,.2f}")
            pc5.metric("P90",  f"{cur_sym}{np.percentile(ivps_clean,90):,.2f}")

            st.metric("Probability of Undervaluation",
                      f"{pct_underval:.1f}%",
                      help="% of MC simulations where intrinsic value > current price")

            fig_mc = go.Figure()
            fig_mc.add_trace(go.Histogram(
                x=ivps_clean,
                nbinsx=80,
                name="Simulated IV/Share",
                marker_color=ACCENT,
                opacity=0.75,
            ))
            if curr_p:
                fig_mc.add_vline(x=curr_p, line_color=RED, line_width=2,
                                 annotation_text=f"Current {cur_sym}{curr_p:,.2f}",
                                 annotation_font_color=RED)
            fig_mc.add_vline(x=float(np.percentile(ivps_clean, 50)),
                             line_color=YELLOW, line_dash="dot", line_width=1.5,
                             annotation_text="Median IV",
                             annotation_font_color=YELLOW)
            fig_mc.update_layout(**CHART_LAYOUT,
                                  title=f"Monte Carlo Distribution of Intrinsic Value/Share ({n_sims:,} sims)",
                                  xaxis_title=f"Intrinsic Value ({sel_cur})",
                                  yaxis_title="Frequency",
                                  height=380)
            st.plotly_chart(fig_mc, use_container_width=True)

        else:
            st.warning("Insufficient financial data to run DCF. Free Cash Flow and/or Shares Outstanding could not be determined.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 – HEALTH & RISK
    # ══════════════════════════════════════════════════════════════════════════
    with tab_hr:

        # ── Altman Z-Score ─────────────────────────────────────────────────────
        st.subheader("Altman Z-Score")
        z_score = None
        try:
            bs_raw = balance_sheet
            is_raw = income_stmt
            cf_raw = cashflow

            def _get_bs(keys):
                for k in keys:
                    row = next((r for r in bs_raw.index if k.lower() in r.lower()), None)
                    if row is not None:
                        v = bs_raw.loc[row].iloc[0]
                        if pd.notna(v):
                            return float(v)
                return None

            def _get_is(keys):
                for k in keys:
                    row = next((r for r in is_raw.index if k.lower() in r.lower()), None)
                    if row is not None:
                        v = is_raw.loc[row].iloc[0]
                        if pd.notna(v):
                            return float(v)
                return None

            total_assets   = _get_bs(["Total Assets"])
            curr_assets    = _get_bs(["Current Assets"])
            curr_liab      = _get_bs(["Current Liabilities"])
            total_liab     = _get_bs(["Total Liab", "Total Liabilities"])
            retained_earn  = _get_bs(["Retained Earnings"])
            rev_z          = _get_is(["Total Revenue", "Revenue"])
            ebit_z         = _get_is(["EBIT", "Operating Income"])
            mc_z           = (info.get("marketCap") or 0) * fx

            if all(v is not None for v in [total_assets, curr_assets, curr_liab, total_liab, retained_earn, rev_z, ebit_z]) and total_assets > 0:
                wc     = curr_assets - curr_liab
                x1 = wc              / total_assets
                x2 = retained_earn   / total_assets
                x3 = ebit_z          / total_assets
                x4 = mc_z            / total_liab if total_liab else 0
                x5 = rev_z           / total_assets
                z_score = 1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5
        except Exception as e:
            st.caption(f"Z-Score calc note: {e}")

        if z_score is not None:
            if z_score > 2.99:
                z_color = GREEN;  z_zone = "Safe Zone"
            elif z_score >= 1.81:
                z_color = YELLOW; z_zone = "Grey Zone"
            else:
                z_color = RED;    z_zone = "Distress Zone"

            fig_z = go.Figure(go.Indicator(
                mode="gauge+number",
                value=z_score,
                number={"font": {"color": z_color, "size": 36}, "suffix": ""},
                title={"text": f"Altman Z-Score – {z_zone}", "font": {"color": z_color}},
                gauge={
                    "axis": {"range": [0, 5], "tickcolor": "#9ca3af"},
                    "bar":  {"color": z_color},
                    "bgcolor": "#07080d",
                    "bordercolor": "#9ca3af",
                    "steps": [
                        {"range": [0, 1.81],    "color": "rgba(239,68,68,0.15)"},
                        {"range": [1.81, 2.99], "color": "rgba(245,158,11,0.15)"},
                        {"range": [2.99, 5],    "color": "rgba(16,185,129,0.15)"},
                    ],
                    "threshold": {"line": {"color": "white", "width": 2}, "value": z_score},
                },
            ))
            fig_z.update_layout(paper_bgcolor="#07080d", font=dict(color="#9ca3af"),
                                 height=280, margin=dict(l=30, r=30, t=60, b=10))
            st.plotly_chart(fig_z, use_container_width=True)

            interp = {
                "Safe Zone":     "The company appears financially healthy. Low bankruptcy risk.",
                "Grey Zone":     "The company is in a borderline financial position. Monitor closely.",
                "Distress Zone": "The company shows signs of financial distress. Elevated bankruptcy risk.",
            }
            st.info(f"**{z_zone}** (Z = {z_score:.2f}): {interp[z_zone]}")
        else:
            st.info("Altman Z-Score could not be computed (insufficient balance sheet data).")

        st.divider()

        # ── Piotroski F-Score ──────────────────────────────────────────────────
        st.subheader("Piotroski F-Score")
        f_score = 0
        f_details = {}
        try:
            bs_cols = list(balance_sheet.columns) if not balance_sheet.empty else []
            is_cols = list(income_stmt.columns)   if not income_stmt.empty   else []
            cf_cols = list(cashflow.columns)       if not cashflow.empty      else []

            def _col_val(df, key_parts, col_idx=0):
                row = next((r for r in df.index if any(k.lower() in r.lower() for k in key_parts)), None)
                if row is not None and len(df.columns) > col_idx:
                    v = df.loc[row].iloc[col_idx]
                    return float(v) if pd.notna(v) else None
                return None

            ta_now  = _col_val(balance_sheet, ["Total Assets"], 0)
            ta_prev = _col_val(balance_sheet, ["Total Assets"], 1) if len(balance_sheet.columns) > 1 else None
            ni_now  = _col_val(income_stmt,   ["Net Income"],   0)
            ni_prev = _col_val(income_stmt,   ["Net Income"],   1) if len(income_stmt.columns) > 1 else None
            ocf_now = _col_val(cashflow,      ["Operating"],    0)
            gp_now  = _col_val(income_stmt,   ["Gross Profit"], 0)
            gp_prev = _col_val(income_stmt,   ["Gross Profit"], 1) if len(income_stmt.columns) > 1 else None
            rev_now = _col_val(income_stmt,   ["Total Revenue", "Revenue"], 0)
            rev_prev= _col_val(income_stmt,   ["Total Revenue", "Revenue"], 1) if len(income_stmt.columns) > 1 else None
            td_now  = _col_val(balance_sheet, ["Total Debt", "Long Term Debt"], 0)
            td_prev = _col_val(balance_sheet, ["Total Debt", "Long Term Debt"], 1) if len(balance_sheet.columns) > 1 else None
            ca_now  = _col_val(balance_sheet, ["Current Assets"], 0)
            ca_prev = _col_val(balance_sheet, ["Current Assets"], 1) if len(balance_sheet.columns) > 1 else None
            cl_now  = _col_val(balance_sheet, ["Current Liabilities"], 0)
            cl_prev = _col_val(balance_sheet, ["Current Liabilities"], 1) if len(balance_sheet.columns) > 1 else None
            shares_now  = _col_val(balance_sheet, ["Common Stock", "Ordinary Shares"], 0)
            shares_prev = _col_val(balance_sheet, ["Common Stock", "Ordinary Shares"], 1) if len(balance_sheet.columns) > 1 else None

            roa_now  = (ni_now  / ta_now)  if (ni_now  and ta_now)  else None
            roa_prev = (ni_prev / ta_prev) if (ni_prev and ta_prev) else None

            p1 = int(roa_now > 0)             if roa_now  is not None               else 0
            p2 = int(ocf_now > 0)             if ocf_now  is not None               else 0
            p3 = int(roa_now > roa_prev)      if (roa_now and roa_prev)             else 0
            p4_val = int((td_now / ta_now if ta_now else 0) < (td_prev / ta_prev if ta_prev else 1)) if (td_now is not None and td_prev is not None) else 0
            p5 = int((ca_now/cl_now if cl_now else 0) > (ca_prev/cl_prev if cl_prev else 0)) if (ca_now and ca_prev and cl_now and cl_prev) else 0
            p6 = int(shares_now <= shares_prev) if (shares_now is not None and shares_prev is not None) else 0
            gm_now  = (gp_now  / rev_now)  if (gp_now  and rev_now)  else None
            gm_prev = (gp_prev / rev_prev) if (gp_prev and rev_prev) else None
            p7 = int(gm_now > gm_prev)       if (gm_now  and gm_prev) else 0
            at_now  = (rev_now  / ta_now)  if (rev_now  and ta_now)  else None
            at_prev = (rev_prev / ta_prev) if (rev_prev and ta_prev) else None
            p8 = int(at_now > at_prev)       if (at_now and at_prev)  else 0
            p9 = int(ocf_now > ni_now)       if (ocf_now and ni_now)  else 0

            f_score = p1+p2+p3+p4_val+p5+p6+p7+p8+p9
            f_details = {
                "ROA > 0 (Profitability)":          ("✅" if p1 else "❌"),
                "Operating CF > 0":                 ("✅" if p2 else "❌"),
                "ROA Improving YoY":                ("✅" if p3 else "❌"),
                "Leverage Ratio Decreasing":        ("✅" if p4_val else "❌"),
                "Current Ratio Improving":          ("✅" if p5 else "❌"),
                "No New Shares Issued":             ("✅" if p6 else "❌"),
                "Gross Margin Improving":           ("✅" if p7 else "❌"),
                "Asset Turnover Improving":         ("✅" if p8 else "❌"),
                "CF > Net Income (Low Accruals)":   ("✅" if p9 else "❌"),
            }
        except Exception as e:
            st.caption(f"F-Score calc note: {e}")

        if f_details:
            if f_score >= 7:
                f_label = "Strong"; f_color = GREEN
            elif f_score >= 4:
                f_label = "Neutral"; f_color = YELLOW
            else:
                f_label = "Weak"; f_color = RED

            st.markdown(f"<h3 style='color:{f_color}'>F-Score: {f_score}/9 – {f_label}</h3>",
                        unsafe_allow_html=True)
            f_df = pd.DataFrame(list(f_details.items()), columns=["Signal", "Result"])
            st.dataframe(f_df, use_container_width=True, hide_index=True)
        else:
            st.info("Piotroski F-Score could not be computed.")

        st.divider()

        # ── Key Ratios ─────────────────────────────────────────────────────────
        st.subheader("Key Financial Ratios")
        ratio_data = {
            "ROE (%)":                (info.get("returnOnEquity") or 0) * 100,
            "ROA (%)":                (info.get("returnOnAssets") or 0) * 100,
            "Net Margin (%)":         (info.get("profitMargins") or 0) * 100,
            "Gross Margin (%)":       (info.get("grossMargins") or 0) * 100,
            "Operating Margin (%)":   (info.get("operatingMargins") or 0) * 100,
            "Debt / Equity":          info.get("debtToEquity"),
            "Interest Coverage":      info.get("interestCoverage") or info.get("ebitdaMargins"),
            "Current Ratio":          info.get("currentRatio"),
            "Quick Ratio":            info.get("quickRatio"),
            "Asset Turnover":         info.get("assetTurnover"),
            "Inventory Turnover":     info.get("inventoryTurnover"),
        }
        ratio_rows = []
        for label, val in ratio_data.items():
            if val is not None and val != 0:
                ratio_rows.append({"Ratio": label, "Value": f"{val:.2f}"})
        if ratio_rows:
            st.dataframe(pd.DataFrame(ratio_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Ratio data not available from ticker info.")

        st.divider()

        # ── Rolling Beta Chart ─────────────────────────────────────────────────
        st.subheader("Rolling 252-Day Beta vs SPY")
        try:
            end_dt   = datetime.today()
            start_dt = end_dt - timedelta(days=365 * 2 + 30)
            spy_hist = yf.Ticker("SPY").history(start=start_dt, end=end_dt)["Close"]
            stk_hist = hist_1y["Close"] if not hist_1y.empty else pd.Series(dtype=float)

            if not spy_hist.empty and not stk_hist.empty:
                # align on date index (strip timezone)
                spy_hist.index = spy_hist.index.tz_localize(None) if spy_hist.index.tzinfo else spy_hist.index
                stk_hist.index = stk_hist.index.tz_localize(None) if stk_hist.index.tzinfo else stk_hist.index

                combined = pd.concat([stk_hist.rename("stock"), spy_hist.rename("spy")], axis=1).dropna()
                ret      = combined.pct_change().dropna()
                if len(ret) >= 60:
                    window = min(252, len(ret) // 2)
                    roll_cov = ret["stock"].rolling(window).cov(ret["spy"])
                    roll_var = ret["spy"].rolling(window).var()
                    roll_beta = roll_cov / roll_var

                    fig_beta = go.Figure()
                    fig_beta.add_trace(go.Scatter(
                        x=roll_beta.index, y=roll_beta.values,
                        mode="lines", name=f"{window}-day Rolling Beta",
                        line=dict(color=ACCENT, width=1.5),
                    ))
                    fig_beta.add_hline(y=1.0, line_dash="dot", line_color="#9ca3af",
                                       annotation_text="β=1 (Market)")
                    fig_beta.update_layout(**CHART_LAYOUT,
                                           title=f"Rolling {window}-Day Beta vs SPY",
                                           yaxis_title="Beta", height=320)
                    st.plotly_chart(fig_beta, use_container_width=True)
                else:
                    st.info("Not enough price history to compute rolling beta.")
        except Exception as e:
            st.info(f"Rolling beta chart unavailable: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5 – OWNERSHIP
    # ══════════════════════════════════════════════════════════════════════════
    with tab_own:
        st.subheader("Institutional Holders – Top 10")
        if inst_holders is not None and not inst_holders.empty:
            try:
                ih = inst_holders.copy()
                # normalise column names
                ih.columns = [str(c).strip() for c in ih.columns]
                # show top 10
                ih_top = ih.head(10).reset_index(drop=True)
                st.dataframe(ih_top, use_container_width=True)

                # pie chart of top holders by shares / value
                val_col = next((c for c in ih.columns if "Value" in c or "Shares" in c), None)
                name_col= next((c for c in ih.columns if "Holder" in c or "Name" in c), None)
                if val_col and name_col:
                    pie_df = ih_top[[name_col, val_col]].dropna()
                    fig_ih = go.Figure(go.Pie(
                        labels=pie_df[name_col].tolist(),
                        values=pie_df[val_col].tolist(),
                        hole=0.4,
                        marker=dict(colors=px.colors.qualitative.Plotly),
                        textinfo="percent+label",
                    ))
                    fig_ih.update_layout(
                        paper_bgcolor="#07080d",
                        font=dict(color="#9ca3af"),
                        title="Top 10 Institutional Holders Breakdown",
                        height=420,
                        margin=dict(l=20, r=20, t=60, b=20),
                    )
                    st.plotly_chart(fig_ih, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not render institutional holders: {e}")
        else:
            st.info("No institutional holder data available.")

        # ── Major holders breakdown ────────────────────────────────────────────
        st.subheader("Major Holders Breakdown")
        try:
            insider_pct = info.get("heldPercentInsiders")
            inst_pct    = info.get("heldPercentInstitutions")
            if insider_pct is not None and inst_pct is not None:
                public_pct = max(0.0, 1.0 - insider_pct - inst_pct)
                fig_major = go.Figure(go.Pie(
                    labels=["Insiders", "Institutions", "Public Float"],
                    values=[insider_pct * 100, inst_pct * 100, public_pct * 100],
                    hole=0.45,
                    marker=dict(colors=[ACCENT, GREEN, YELLOW]),
                    textinfo="percent+label",
                ))
                fig_major.update_layout(
                    paper_bgcolor="#07080d",
                    font=dict(color="#9ca3af"),
                    title="Ownership Structure",
                    height=380,
                    margin=dict(l=20, r=20, t=60, b=20),
                )
                st.plotly_chart(fig_major, use_container_width=True)
            else:
                st.info("Insider / institutional ownership percentages not available.")
        except Exception as e:
            st.warning(f"Could not render major holders chart: {e}")

        # ── Insider Transactions ───────────────────────────────────────────────
        st.subheader("Insider Transactions (last 6 months)")
        if insider_tx is not None and not insider_tx.empty:
            try:
                it = insider_tx.copy()
                it.columns = [str(c).strip() for c in it.columns]
                date_col = next((c for c in it.columns if "Date" in c or "date" in c), None)
                if date_col:
                    it[date_col] = pd.to_datetime(it[date_col], errors="coerce")
                    cutoff = pd.Timestamp.now() - pd.DateOffset(months=6)
                    it = it[it[date_col] >= cutoff]
                st.dataframe(it.reset_index(drop=True), use_container_width=True)
            except Exception as e:
                st.warning(f"Could not render insider transactions: {e}")
        else:
            st.info("No insider transaction data available.")
