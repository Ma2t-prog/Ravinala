from __future__ import annotations

import io
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from sidebar_assets import ASSET_CLASSES, AssetItem
from sidebar_favorites import load_favorites, save_favorites


@dataclass(frozen=True)
class SearchResult:
    id: str
    ticker: str
    name: str
    asset_class: str
    exchange: str = ""
    seed_price: Optional[float] = None
    seed_change_pct: Optional[float] = None


ASSET_BADGE = {
    "equity": "EQUITY",
    "bond": "BOND",
    "etf": "ETF",
    "commodity": "COMMODITY",
    "derivative": "DERIVATIVE",
    "crypto": "₿ CRYPTO",
}

ASSET_COLORS = {
    "equity": "#3B82F6",
    "bond": "#10B981",
    "etf": "#8B5CF6",
    "commodity": "#EF4444",
    "derivative": "#F59E0B",
    "crypto": "#F97316",
}


TRENDING = ["AAPL", "MSFT", "SPY", "GLD", "^VIX", "BTC-USD"]
POPULAR = ["NVDA", "QQQ", "TLT", "CL=F", "GC=F", "ETH-USD"]


def _class_from_category(category_id: str) -> str:
    mapping = {
        "equities": "equity",
        "fixed-income": "bond",
        "etfs": "etf",
        "commodities": "commodity",
        "derivatives": "derivative",
        "crypto": "crypto",
    }
    return mapping.get(category_id, "equity")


def _normalize_symbol(symbol: str) -> str:
    custom = {
        "US10Y": "^TNX",
        "US2Y": "^FVX",
        "BUND10Y": "^TNX",
        "GOLD": "GC=F",
        "SILVER": "SI=F",
        "COPPER": "HG=F",
        "WTI": "CL=F",
        "BRENT": "BZ=F",
        "NATGAS": "NG=F",
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "ES": "ES=F",
        "NQ": "NQ=F",
        "VIX": "^VIX",
    }
    return custom.get(symbol.upper(), symbol.upper())


def _build_universe() -> List[SearchResult]:
    records: List[SearchResult] = []
    seen = set()

    for category in ASSET_CLASSES:
        asset_class = _class_from_category(category.id)
        for subcategory in category.subcategories:
            for item in subcategory.items:
                ticker = _normalize_symbol(item.symbol)
                key = ticker.upper()
                if key in seen:
                    continue
                seen.add(key)
                records.append(
                    SearchResult(
                        id=item.id,
                        ticker=ticker,
                        name=item.name,
                        asset_class=asset_class,
                        exchange=subcategory.name,
                        seed_price=item.price,
                        seed_change_pct=item.change_percent,
                    )
                )

    extras = [
        SearchResult("eq_aapl", "AAPL", "Apple Inc.", "equity", "NASDAQ", 192.53, 1.14),
        SearchResult("eq_msft", "MSFT", "Microsoft Corporation", "equity", "NASDAQ", 412.56, 0.87),
        SearchResult("eq_googl", "GOOGL", "Alphabet Inc.", "equity", "NASDAQ", 177.83, 1.05),
        SearchResult("eq_amzn", "AMZN", "Amazon.com Inc.", "equity", "NASDAQ", 187.23, -0.45),
        SearchResult("eq_nvda", "NVDA", "NVIDIA Corporation", "equity", "NASDAQ", 892.34, 2.87),
        SearchResult("bond_us10", "^TNX", "US 10Y Treasury Yield", "bond", "US Rates", 4.22, -0.12),
        SearchResult("bond_us2", "^FVX", "US 5Y Treasury Yield", "bond", "US Rates", 4.12, 0.08),
        SearchResult("etf_spy", "SPY", "SPDR S&P 500 ETF", "etf", "NYSE", 456.78, 1.14),
        SearchResult("etf_qqq", "QQQ", "Invesco QQQ", "etf", "NASDAQ", 387.23, 1.25),
        SearchResult("com_gold", "GC=F", "Gold Futures", "commodity", "COMEX", 2087.30, 0.52),
        SearchResult("com_oil", "CL=F", "WTI Crude Oil Futures", "commodity", "NYMEX", 94.73, 4.03),
        SearchResult("der_vix", "^VIX", "CBOE Volatility Index", "derivative", "CBOE", 23.7, -9.34),
        SearchResult("cr_btc", "BTC-USD", "Bitcoin USD", "crypto", "Crypto", 67543.25, 2.34),
        SearchResult("cr_eth", "ETH-USD", "Ethereum USD", "crypto", "Crypto", 3421.50, -1.15),
    ]
    for rec in extras:
        if rec.ticker.upper() not in seen:
            records.append(rec)
            seen.add(rec.ticker.upper())
    return records


UNIVERSE = _build_universe()
UNIVERSE_BY_TICKER = {r.ticker.upper(): r for r in UNIVERSE}


@st.cache_data(ttl=60)
def _fetch_asset_snapshot(ticker: str) -> Dict:
    result = {
        "price": None,
        "change": None,
        "change_pct": None,
        "volume": None,
        "avg_volume": None,
        "market_cap": None,
        "pe": None,
        "eps": None,
        "dividend_yield": None,
        "beta": None,
        "exchange": None,
        "name": ticker,
        "currency": "USD",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    try:
        tk = yf.Ticker(ticker)
        info = tk.fast_info or {}
        meta = tk.info or {}

        prev = info.get("previous_close") or meta.get("previousClose")
        price = info.get("last_price") or meta.get("currentPrice") or meta.get("regularMarketPrice")

        result["price"] = float(price) if price is not None else None
        result["volume"] = info.get("last_volume") or meta.get("volume")
        result["avg_volume"] = info.get("ten_day_average_volume") or meta.get("averageVolume")
        result["market_cap"] = info.get("market_cap") or meta.get("marketCap")
        result["pe"] = meta.get("trailingPE")
        result["eps"] = meta.get("trailingEps")
        result["dividend_yield"] = meta.get("dividendYield")
        result["beta"] = meta.get("beta")
        result["exchange"] = meta.get("exchange") or meta.get("fullExchangeName")
        result["name"] = meta.get("longName") or meta.get("shortName") or ticker
        result["currency"] = meta.get("currency") or "USD"

        if result["price"] is not None and prev:
            chg = float(result["price"] - prev)
            result["change"] = chg
            result["change_pct"] = (chg / prev) * 100 if prev else None
    except Exception:
        return result
    return result


@st.cache_data(ttl=300)
def _fetch_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        hist = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
        if hist is None or hist.empty:
            return pd.DataFrame()
        return hist
    except Exception:
        return pd.DataFrame()


def _format_large(n: Optional[float]) -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "N/A"
    x = float(n)
    if abs(x) >= 1e12:
        return f"${x/1e12:.2f}T"
    if abs(x) >= 1e9:
        return f"${x/1e9:.2f}B"
    if abs(x) >= 1e6:
        return f"${x/1e6:.2f}M"
    return f"${x:,.0f}"


def _price_string(price: Optional[float], asset_class: str) -> str:
    if price is None:
        return "N/A"
    if asset_class in {"bond", "commodity", "derivative"}:
        return f"{price:,.2f}"
    return f"${price:,.2f}"


def _fuzzy_search(query: str, asset_class: str = "All", exchange: str = "All") -> List[SearchResult]:
    q = query.strip().lower()

    def score(asset: SearchResult) -> int:
        t = asset.ticker.lower()
        n = asset.name.lower()
        if not q:
            return 0
        if t == q:
            return 120
        if t.startswith(q):
            return 100
        if q in t:
            return 80
        if n.startswith(q):
            return 70
        if q in n:
            return 60
        return 0

    rows = UNIVERSE
    if asset_class != "All":
        rows = [r for r in rows if r.asset_class == asset_class]
    if exchange != "All":
        rows = [r for r in rows if r.exchange == exchange]

    if not q:
        return rows[:10]

    ranked = [(score(r), r) for r in rows]
    ranked = [x for x in ranked if x[0] > 0]
    ranked.sort(key=lambda x: (-x[0], x[1].ticker))
    return [r for _, r in ranked[:10]]


def _init_state():
    st.session_state.setdefault("uae_query", "")
    st.session_state.setdefault("uae_asset_class", "All")
    st.session_state.setdefault("uae_exchange", "All")
    st.session_state.setdefault("uae_recents", [])
    st.session_state.setdefault("uae_selected", None)
    st.session_state.setdefault("uae_compare", [])


def _push_recent(asset: SearchResult):
    current = st.session_state["uae_recents"]
    new_list = [asset.ticker] + [x for x in current if x != asset.ticker]
    st.session_state["uae_recents"] = new_list[:8]


def _select_asset(asset: SearchResult):
    st.session_state["uae_selected"] = asset.ticker
    _push_recent(asset)


def _asset_from_ticker(ticker: str) -> Optional[SearchResult]:
    return UNIVERSE_BY_TICKER.get(ticker.upper())


def _badge_html(asset_class: str) -> str:
    color = ASSET_COLORS.get(asset_class, "#64748B")
    label = ASSET_BADGE.get(asset_class, asset_class.upper())
    return (
        f'<span class="uae-badge" style="border-color:{color}55;color:{color};background:{color}1f">'
        f"{label}</span>"
    )


def _inject_styles():
    st.markdown(
        """
        <style>
        .uae-title{font-size:1.35rem;font-weight:700;color:#F8FAFC;letter-spacing:.01em;margin-bottom:2px}
        .uae-sub{font-size:.78rem;color:#94A3B8;letter-spacing:.06em;text-transform:uppercase}
        .uae-block{background:linear-gradient(135deg,rgba(19,24,35,.62),rgba(15,18,24,.62));
            border:1px solid rgba(51,65,85,.30);border-radius:12px;padding:12px 14px;margin-bottom:10px}
        .uae-result-card{background:rgba(15,23,42,.45);border:1px solid rgba(51,65,85,.30);
            border-radius:10px;padding:9px 11px}
        .uae-result-top{display:flex;align-items:center;gap:8px}
        .uae-result-ticker{font-weight:700;color:#F1F5F9;font-size:.92rem}
        .uae-result-name{font-size:.78rem;color:#94A3B8;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .uae-badge{font-size:.62rem;font-weight:700;padding:2px 7px;border-radius:999px;border:1px solid;letter-spacing:.05em}
        .uae-mini{font-size:.70rem;color:#64748B}
        div[data-testid="stMetric"]{background:rgba(15,23,42,.28);border:1px solid rgba(51,65,85,.28);border-radius:10px;padding:8px 10px}
        div[data-testid="stMetricLabel"]{font-size:.68rem!important;letter-spacing:.05em;text-transform:uppercase}
        div[data-testid="stMetricValue"]{font-size:1.1rem!important}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _export_pdf(asset: SearchResult, snapshot: Dict) -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    pdf.setTitle(f"{asset.ticker} Asset Snapshot")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, h - 50, "RAVINALA — Asset Snapshot")

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, h - 85, f"{asset.ticker} | {snapshot.get('name', asset.name)}")

    pdf.setFont("Helvetica", 10)
    y = h - 110
    rows = [
        ("Asset Class", asset.asset_class.upper()),
        ("Exchange", snapshot.get("exchange") or asset.exchange or "N/A"),
        ("Price", _price_string(snapshot.get("price"), asset.asset_class)),
        ("Change (%)", f"{(snapshot.get('change_pct') or 0):+.2f}%"),
        ("Market Cap", _format_large(snapshot.get("market_cap"))),
        ("Volume", f"{int(snapshot['volume']):,}" if snapshot.get("volume") else "N/A"),
        ("P/E", f"{snapshot['pe']:.2f}" if snapshot.get("pe") else "N/A"),
        ("Beta", f"{snapshot['beta']:.2f}" if snapshot.get("beta") else "N/A"),
        ("Timestamp", snapshot.get("timestamp", "N/A")),
    ]

    for k, v in rows:
        pdf.drawString(40, y, f"{k}: {v}")
        y -= 16

    pdf.showPage()
    pdf.save()
    buf.seek(0)
    return buf.getvalue()


def _render_search_bar():
    st.markdown(
        """
        <div class="uae-block">
            <div class="uae-title">Unified Asset Search</div>
            <div class="uae-sub">Global lookup across all asset classes</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        st.session_state["uae_query"] = st.text_input(
            "Search any ticker",
            value=st.session_state["uae_query"],
            placeholder="AAPL, US10Y, SPY, GC=F, ^VIX, BTC-USD…",
            label_visibility="collapsed",
            key="uae_query_input",
        )
    with c2:
        choices = ["All", "equity", "bond", "etf", "commodity", "derivative", "crypto"]
        st.session_state["uae_asset_class"] = st.selectbox(
            "Asset class",
            options=choices,
            index=choices.index(st.session_state["uae_asset_class"]),
            key="uae_class_filter",
        )
    with c3:
        exchanges = ["All"] + sorted({r.exchange for r in UNIVERSE if r.exchange})
        current = st.session_state["uae_exchange"]
        if current not in exchanges:
            current = "All"
        st.session_state["uae_exchange"] = st.selectbox(
            "Exchange",
            options=exchanges,
            index=exchanges.index(current),
            key="uae_exchange_filter",
        )

    st.markdown(
        f'<div class="uae-mini">Universe indexed: <b>{len(UNIVERSE):,}</b> assets</div>',
        unsafe_allow_html=True,
    )

    chips_cols = st.columns(3)
    with chips_cols[0]:
        st.write("**Recents**")
        recents = st.session_state["uae_recents"][:5]
        if recents:
            for t in recents:
                if st.button(t, key=f"uae_recent_{t}", width="stretch"):
                    asset = _asset_from_ticker(t)
                    if asset:
                        _select_asset(asset)
                        st.rerun()
        else:
            st.caption("No recent searches")
    with chips_cols[1]:
        st.write("**Trending**")
        for t in TRENDING:
            if st.button(t, key=f"uae_trending_{t}", width="stretch"):
                asset = _asset_from_ticker(t)
                if asset:
                    _select_asset(asset)
                    st.rerun()
    with chips_cols[2]:
        st.write("**Popular**")
        for t in POPULAR:
            if st.button(t, key=f"uae_pop_{t}", width="stretch"):
                asset = _asset_from_ticker(t)
                if asset:
                    _select_asset(asset)
                    st.rerun()

    results = _fuzzy_search(
        st.session_state["uae_query"],
        st.session_state["uae_asset_class"],
        st.session_state["uae_exchange"],
    )

    st.markdown('<div class="uae-sub" style="margin-top:8px">Results</div>', unsafe_allow_html=True)
    if not results:
        st.info("No results found.")
        return

    for idx, r in enumerate(results):
        c1, c2, c3 = st.columns([3, 2, 1])
        with c1:
            st.markdown(
                f"""
                <div class="uae-result-card">
                    <div class="uae-result-top">
                        <span class="uae-result-ticker">{r.ticker}</span>
                        {_badge_html(r.asset_class)}
                        <span class="uae-mini">{r.exchange or 'N/A'}</span>
                    </div>
                    <div class="uae-result-name">{r.name}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            seed_price = _price_string(r.seed_price, r.asset_class) if r.seed_price is not None else "N/A"
            seed_chg = f"{(r.seed_change_pct or 0):+.2f}%" if r.seed_change_pct is not None else "--"
            st.write(seed_price)
            st.caption(seed_chg)
        with c3:
            if st.button("Open", key=f"uae_open_{r.ticker}_{idx}", width="stretch"):
                _select_asset(r)
                st.rerun()


def _render_chart(asset: SearchResult, hist: pd.DataFrame):
    if hist.empty:
        st.info("No price history available for this instrument.")
        return

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hist.index,
            y=hist["Close"],
            mode="lines",
            name=asset.ticker,
            line=dict(color="#00D9FF", width=2),
        )
    )
    if "Volume" in hist.columns:
        fig.add_trace(
            go.Bar(
                x=hist.index,
                y=hist["Volume"],
                name="Volume",
                yaxis="y2",
                marker_color="rgba(148,163,184,0.35)",
            )
        )

    fig.update_layout(
        height=360,
        template="plotly_dark",
        paper_bgcolor="#0A0E1A",
        plot_bgcolor="#0A0E1A",
        margin=dict(l=8, r=8, t=24, b=8),
        yaxis2=dict(overlaying="y", side="right", showgrid=False, title="Volume"),
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, width="stretch")


def _render_related_assets(asset: SearchResult, hist: pd.DataFrame):
    peers = [x for x in UNIVERSE if x.asset_class == asset.asset_class and x.ticker != asset.ticker][:10]
    if not peers:
        st.info("No related assets available.")
        return

    related_rows = []
    if not hist.empty and "Close" in hist.columns:
        base_returns = hist["Close"].pct_change().dropna()
    else:
        base_returns = pd.Series(dtype=float)

    for peer in peers:
        corr = None
        if not base_returns.empty:
            ph = _fetch_history(peer.ticker, period="6mo")
            if not ph.empty and "Close" in ph.columns:
                merged = pd.concat([base_returns, ph["Close"].pct_change().dropna()], axis=1).dropna()
                if len(merged) > 10:
                    corr = float(merged.iloc[:, 0].corr(merged.iloc[:, 1]))
        related_rows.append({
            "Ticker": peer.ticker,
            "Name": peer.name,
            "Asset Class": peer.asset_class,
            "Correlation": round(corr, 2) if corr is not None else np.nan,
        })

    df = pd.DataFrame(related_rows).sort_values(by="Correlation", ascending=False, na_position="last").head(6)
    st.dataframe(df, width="stretch", hide_index=True)


def _render_comparison(compare_assets: List[SearchResult]):
    if not compare_assets:
        return

    st.divider()
    st.markdown("### Multi-Asset Comparison")

    rows = []
    for asset in compare_assets:
        snap = _fetch_asset_snapshot(asset.ticker)
        rows.append(
            {
                "Ticker": asset.ticker,
                "Class": asset.asset_class,
                "Price": snap.get("price"),
                "Change %": snap.get("change_pct"),
                "Market Cap": _format_large(snap.get("market_cap")),
                "Volume": snap.get("volume"),
                "P/E": snap.get("pe"),
                "Beta": snap.get("beta"),
            }
        )
    cmp_df = pd.DataFrame(rows)
    st.dataframe(cmp_df, width="stretch", hide_index=True)

    tickers = [a.ticker for a in compare_assets]
    corr_data = pd.DataFrame()
    for t in tickers:
        hist = _fetch_history(t, period="6mo")
        if not hist.empty:
            corr_data[t] = hist["Close"].pct_change()
    corr_data = corr_data.dropna()
    if corr_data.shape[1] >= 2 and len(corr_data) > 10:
        st.markdown("#### Correlation Matrix")
        st.dataframe(corr_data.corr().round(2), width="stretch")


def render_unified_asset_explorer():
    _init_state()
    _inject_styles()

    st.markdown(
        """
        <div class="uae-block" style="margin-bottom:14px">
            <div class="uae-title">Universal Asset Explorer</div>
            <div class="uae-sub">Unified search, analytics and comparison across Equities, Bonds, ETFs, Commodities, Derivatives and Crypto</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_search_bar()

    selected_ticker = st.session_state.get("uae_selected")
    if not selected_ticker:
        st.info("Start by selecting an asset from the search results.")
        return

    asset = _asset_from_ticker(selected_ticker)
    if asset is None:
        st.warning("Selected asset is no longer available in the universe.")
        return

    snap = _fetch_asset_snapshot(asset.ticker)
    hist = _fetch_history(asset.ticker, period="1y")

    header_left, header_mid, header_right = st.columns([3, 2, 2])
    with header_left:
        st.markdown(
            f"""
            <div class="uae-block" style="margin-bottom:6px">
                <div class="uae-title">{asset.ticker} | {snap.get('name') or asset.name}</div>
                <div style="display:flex;align-items:center;gap:8px;margin-top:4px">
                    {_badge_html(asset.asset_class)}
                    <span class="uae-mini">{snap.get('exchange') or asset.exchange or 'N/A'}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with header_mid:
        price = snap.get("price") if snap.get("price") is not None else asset.seed_price
        chg = snap.get("change_pct") if snap.get("change_pct") is not None else asset.seed_change_pct
        st.metric("Current", _price_string(price, asset.asset_class), f"{(chg or 0):+.2f}%" if chg is not None else "--")
    with header_right:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Add Watchlist", width="stretch", key=f"uae_pin_{asset.ticker}"):
                favorites = load_favorites()
                existing = {x.symbol.upper() for x in favorites}
                if asset.ticker.upper() not in existing:
                    favorites.append(
                        AssetItem(
                            id=f"uae_{asset.ticker.lower()}",
                            symbol=asset.ticker,
                            name=snap.get("name") or asset.name,
                            price=price,
                            change_percent=chg,
                            is_favorite=True,
                        )
                    )
                    save_favorites(favorites)
                    st.success(f"{asset.ticker} added to watchlist")
                else:
                    st.info("Already in watchlist")
        with b2:
            compare = st.session_state["uae_compare"]
            label = "Remove Compare" if asset.ticker in compare else "Add Compare"
            if st.button(label, width="stretch", key=f"uae_cmp_{asset.ticker}"):
                if asset.ticker in compare:
                    st.session_state["uae_compare"] = [x for x in compare if x != asset.ticker]
                else:
                    st.session_state["uae_compare"] = (compare + [asset.ticker])[:4]
                st.rerun()

    export_col1, export_col2, export_col3 = st.columns([1, 1, 2])
    with export_col1:
        payload = {
            "asset": asdict(asset),
            "snapshot": snap,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        st.download_button(
            "Export JSON",
            data=json.dumps(payload, indent=2, default=str),
            file_name=f"{asset.ticker}_snapshot.json",
            mime="application/json",
            width="stretch",
        )
    with export_col2:
        pdf_bytes = _export_pdf(asset, snap)
        st.download_button(
            "Export PDF",
            data=pdf_bytes,
            file_name=f"{asset.ticker}_snapshot.pdf",
            mime="application/pdf",
            width="stretch",
        )
    with export_col3:
        subject = f"RAVINALA Asset Snapshot - {asset.ticker}"
        body = f"Ticker: {asset.ticker}%0D%0APrice: {_price_string(snap.get('price'), asset.asset_class)}"
        st.markdown(f"[Share by Email](mailto:?subject={subject}&body={body})")

    metric_cols = st.columns(5)
    with metric_cols[0]:
        st.metric("Mkt Cap", _format_large(snap.get("market_cap")))
    with metric_cols[1]:
        pe = snap.get("pe")
        st.metric("P/E", f"{pe:.2f}" if pe else "N/A")
    with metric_cols[2]:
        dy = snap.get("dividend_yield")
        st.metric("Div Yield", f"{dy*100:.2f}%" if dy else "N/A")
    with metric_cols[3]:
        beta = snap.get("beta")
        st.metric("Beta", f"{beta:.2f}" if beta else "N/A")
    with metric_cols[4]:
        vol = snap.get("avg_volume") or snap.get("volume")
        st.metric("Avg Vol", f"{int(vol):,}" if vol else "N/A")

    tabs = st.tabs(["Overview", "Valuation", "Technical", "Fundamentals", "Analytics", "News", "Related"])

    with tabs[0]:
        st.markdown("#### Price & Change")
        price = snap.get("price") if snap.get("price") is not None else asset.seed_price
        chg_abs = snap.get("change")
        chg_pct = snap.get("change_pct") if snap.get("change_pct") is not None else asset.seed_change_pct
        st.write(f"Current: {_price_string(price, asset.asset_class)}")
        st.write(f"Change: {f'{chg_abs:+.2f}' if chg_abs is not None else 'N/A'} ({f'{chg_pct:+.2f}%' if chg_pct is not None else 'N/A'})")
        if not hist.empty:
            lo = hist["Close"].min()
            hi = hist["Close"].max()
            st.write(f"52W Range: {lo:,.2f} - {hi:,.2f}")
        _render_chart(asset, hist)

    with tabs[1]:
        st.markdown("#### Valuation Metrics")
        if asset.asset_class == "equity":
            st.write(f"EPS: {snap['eps']:.2f}" if snap.get("eps") else "EPS: N/A")
            st.write(f"P/E: {snap['pe']:.2f}" if snap.get("pe") else "P/E: N/A")
            st.write(f"Market Cap: {_format_large(snap.get('market_cap'))}")
        elif asset.asset_class == "bond":
            st.write("Yield and spread analytics available via bond pricing desks.")
            st.write(f"Current yield proxy: {_price_string(snap.get('price'), asset.asset_class)}")
        elif asset.asset_class == "etf":
            st.write(f"AUM proxy (market cap): {_format_large(snap.get('market_cap'))}")
            st.write(f"Volume: {int(snap['volume']):,}" if snap.get("volume") else "Volume: N/A")
        elif asset.asset_class == "commodity":
            st.write("Commodity valuation driven by term-structure, convenience yield and carry.")
        elif asset.asset_class == "derivative":
            st.write("Derivative valuation linked to implied vol and underlying dynamics.")
        else:
            st.write("Crypto valuation includes momentum, volatility and liquidity overlays.")

    with tabs[2]:
        st.markdown("#### Technical")
        if hist.empty:
            st.info("No technical data available.")
        else:
            close = hist["Close"].dropna()
            rsi = None
            if len(close) > 20:
                delta = close.diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = -delta.clip(upper=0).rolling(14).mean()
                rs = gain / loss.replace(0, np.nan)
                rsi = 100 - (100 / (1 + rs))
            sma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else np.nan
            sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else np.nan
            st.metric("RSI(14)", f"{rsi.iloc[-1]:.2f}" if rsi is not None and not np.isnan(rsi.iloc[-1]) else "N/A")
            c1, c2 = st.columns(2)
            with c1:
                st.metric("SMA 20", f"{sma20:,.2f}" if not np.isnan(sma20) else "N/A")
            with c2:
                st.metric("SMA 50", f"{sma50:,.2f}" if not np.isnan(sma50) else "N/A")

    with tabs[3]:
        st.markdown("#### Fundamentals")
        data = {
            "Name": snap.get("name") or asset.name,
            "Exchange": snap.get("exchange") or asset.exchange,
            "Currency": snap.get("currency"),
            "Market Cap": _format_large(snap.get("market_cap")),
            "P/E": f"{snap['pe']:.2f}" if snap.get("pe") else "N/A",
            "EPS": f"{snap['eps']:.2f}" if snap.get("eps") else "N/A",
            "Dividend Yield": f"{(snap['dividend_yield'] or 0)*100:.2f}%" if snap.get("dividend_yield") else "N/A",
            "Beta": f"{snap['beta']:.2f}" if snap.get("beta") else "N/A",
        }
        st.dataframe(pd.DataFrame(data.items(), columns=["Field", "Value"]), hide_index=True, width="stretch")

    with tabs[4]:
        st.markdown("#### Advanced Analytics")
        if hist.empty:
            st.info("No analytics available.")
        else:
            rets = hist["Close"].pct_change().dropna()
            vol30 = rets.tail(30).std() * np.sqrt(252) if len(rets) >= 30 else np.nan
            vol1y = rets.std() * np.sqrt(252) if len(rets) > 10 else np.nan
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Vol (30d)", f"{vol30*100:.2f}%" if not np.isnan(vol30) else "N/A")
            with c2:
                st.metric("Vol (1Y)", f"{vol1y*100:.2f}%" if not np.isnan(vol1y) else "N/A")
            with c3:
                st.metric("Return (1Y)", f"{((hist['Close'].iloc[-1]/hist['Close'].iloc[0]-1)*100):+.2f}%")

    with tabs[5]:
        st.markdown("#### Latest News & Events")
        try:
            items = yf.Ticker(asset.ticker).news or []
        except Exception:
            items = []
        if not items:
            st.info("No news feed available for this instrument.")
        else:
            for n in items[:8]:
                title = n.get("title", "Untitled")
                link = n.get("link", "")
                src = n.get("publisher", "Source")
                if link:
                    st.markdown(f"- [{title}]({link}) · {src}")
                else:
                    st.markdown(f"- {title} · {src}")

    with tabs[6]:
        st.markdown("#### Related Assets")
        _render_related_assets(asset, hist)

    compare_list = [_asset_from_ticker(t) for t in st.session_state["uae_compare"]]
    compare_assets = [x for x in compare_list if x is not None]
    _render_comparison(compare_assets)
