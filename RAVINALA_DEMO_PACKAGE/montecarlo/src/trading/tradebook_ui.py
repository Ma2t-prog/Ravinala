"""
tradebook_ui.py — Streamlit UI for the Ravinala Trade Book.
7 sub-tabs: Deal Blotter | Book Analytics | P&L Tracker | Trade Inspector |
            New Trade | Templates | Book Settings
"""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Optional

from tradebook_models import (
    Trade, Book, PricingResult, TradeStatus, ProductType, AssetClass,
    Direction, PRODUCT_TYPE_LABELS, STATUS_ICONS, STATUS_COLORS,
    ASSET_CLASS_LABELS, ASSET_PREFIXES
)
from tradebook import BookManager, build_trade_from_pricing
from tradebook_export import TradeBookExporter

try:
    from reporting.term_sheet import TermSheetGenerator
    from reporting.pretrade_report import PreTradeReportGenerator
    from reporting.risk_report import RiskReportGenerator
    from reporting.pnl_report import DailyPnLReportGenerator
    from reporting.client_presentation import ClientPresentationGenerator
    HAS_REPORTING = True
except ImportError:
    HAS_REPORTING = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# ═══════════════════════════════════════════════════════════════
# SINGLETON ACCESSOR
# ═══════════════════════════════════════════════════════════════

def get_book_manager() -> BookManager:
    if 'book_manager' not in st.session_state:
        st.session_state.book_manager = BookManager(data_dir='data/tradebook')
    return st.session_state.book_manager


def get_active_book_id() -> str:
    return st.session_state.get('active_book_id', 'default')


def get_current_user() -> str:
    return st.session_state.get('user', {}).get('username', 'user')


# ═══════════════════════════════════════════════════════════════
# SHARED CSS
# ═══════════════════════════════════════════════════════════════

TRADEBOOK_CSS = """
<style>
.tb-metric-card {
    background: rgba(15,23,42,0.5);
    border: 1px solid rgba(52,211,153,0.2);
    border-radius: 12px;
    padding: 14px 18px;
    text-align: center;
}
.tb-metric-val {
    font-family: 'Orbitron', sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: #34D399;
    margin: 0;
}
.tb-metric-lbl {
    font-size: 10px;
    color: #64748B;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin: 4px 0 0 0;
}
.tb-pnl-pos { color: #22C55E; font-weight: 700; }
.tb-pnl-neg { color: #EF4444; font-weight: 700; }
.tb-ref {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: #34D399;
}
.tb-status-live   { background:#16A34A22; color:#22C55E; border:1px solid #22C55E33; border-radius:6px; padding:2px 8px; font-size:11px; }
.tb-status-draft  { background:#3B82F622; color:#60A5FA; border:1px solid #60A5FA33; border-radius:6px; padding:2px 8px; font-size:11px; }
.tb-status-other  { background:#6B728022; color:#9CA3AF; border:1px solid #6B728033; border-radius:6px; padding:2px 8px; font-size:11px; }
</style>
"""


# ═══════════════════════════════════════════════════════════════
# MAIN RENDER FUNCTION
# ═══════════════════════════════════════════════════════════════

def render_tradebook_tab():
    """Entry point: renders the full Trade Book tab."""
    st.markdown(TRADEBOOK_CSS, unsafe_allow_html=True)

    bm = get_book_manager()
    book_id = get_active_book_id()

    try:
        book = bm.load_book(book_id)
    except FileNotFoundError:
        st.warning(f"Book '{book_id}' not found. Loading default.")
        st.session_state.active_book_id = 'default'
        book = bm.load_book('default')
        book_id = 'default'

    tabs = st.tabs([
        "Deal Blotter",
        "Book Analytics",
        "P&L Tracker",
        "Trade Inspector",
        "New Trade",
        "Templates",
        "Book Settings",
    ])

    with tabs[0]:
        _render_deal_blotter(bm, book, book_id)
    with tabs[1]:
        _render_book_analytics(bm, book_id)
    with tabs[2]:
        _render_pnl_tracker(bm, book_id)
    with tabs[3]:
        _render_trade_inspector(bm, book, book_id)
    with tabs[4]:
        _render_new_trade(bm, book_id)
    with tabs[5]:
        _render_templates(bm, book_id)
    with tabs[6]:
        _render_book_settings(bm)


# ═══════════════════════════════════════════════════════════════
# TAB 1: DEAL BLOTTER
# ═══════════════════════════════════════════════════════════════

def _render_deal_blotter(bm: BookManager, book: Book, book_id: str):
    metrics = bm.compute_book_metrics(book_id)
    exporter = TradeBookExporter()

    # ── Header row ──────────────────────────────────────────
    h_col1, h_col2, h_col3 = st.columns([4, 3, 3])
    with h_col1:
        st.markdown(
            f"**{book.name}**  "
            f"<span style='color:#64748B;font-size:13px'>"
            f"({metrics['live_trades']} live / {metrics['total_trades']} total)</span>",
            unsafe_allow_html=True
        )
    with h_col2:
        if st.button("Reprice All", width="stretch", key="reprice_all_btn"):
            with st.spinner("Repricing all live trades..."):
                result = bm.reprice_book(book_id)
            st.success(
                f"Repriced {result['repriced_count']} trades "
                f"({result['failed_count']} failed, {result['total_time_ms']:.0f}ms)"
            )
            st.rerun()
    with h_col3:
        if st.button("Snapshot", width="stretch", key="snap_btn"):
            path = bm.take_snapshot(book_id)
            st.success(f"Snapshot saved.")

    # KPI row
    k1, k2, k3, k4 = st.columns(4)
    def _fmt(v, ccy=''):
        if v is None:
            return 'N/A'
        if abs(v) >= 1_000_000:
            return f"{ccy}{v/1_000_000:.1f}M"
        elif abs(v) >= 1_000:
            return f"{ccy}{v/1_000:.1f}K"
        return f"{ccy}{v:.0f}"

    with k1:
        st.metric("Total Notional", _fmt(metrics['total_notional'], book.currency + ' '))
    with k2:
        st.metric("Total MTM", _fmt(metrics['total_mtm'], book.currency + ' '))
    with k3:
        pnl = metrics.get('total_pnl', 0) or 0
        sign = '+' if pnl >= 0 else ''
        st.metric("Total P&L",
                  f"{sign}{_fmt(pnl, book.currency + ' ')}",
                  delta=None)
    with k4:
        st.metric("Live Trades", metrics['live_trades'])

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Filters ─────────────────────────────────────────────
    with st.expander("Filters", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            status_opts = [s.value for s in TradeStatus]
            f_status = st.multiselect("Status", status_opts,
                                      default=['live', 'draft'],
                                      key="blotter_f_status")
        with fc2:
            pt_opts = list(PRODUCT_TYPE_LABELS.keys())
            f_product = st.multiselect("Product Type", pt_opts, key="blotter_f_product")
        with fc3:
            f_search = st.text_input("Search", placeholder="ref, counterparty, notes...",
                                     key="blotter_f_search")
        with fc4:
            f_pnl = st.selectbox("P&L", ["All", "Positive only", "Negative only"],
                                 key="blotter_f_pnl")

        dc1, dc2 = st.columns(2)
        with dc1:
            f_date_from = st.date_input("Trade date from", value=None, key="blotter_df")
        with dc2:
            f_date_to = st.date_input("Trade date to", value=None, key="blotter_dt")

    filters = {}
    if f_status:
        filters['status'] = f_status
    if f_product:
        filters['product_type'] = f_product
    if f_search:
        filters['text_search'] = f_search
    if f_pnl == "Positive only":
        filters['pnl_positive'] = True
    elif f_pnl == "Negative only":
        filters['pnl_positive'] = False
    if 'f_date_from' in st.session_state and st.session_state.blotter_df:
        filters['trade_date_from'] = str(st.session_state.blotter_df)
    if 'f_date_to' in st.session_state and st.session_state.blotter_dt:
        filters['trade_date_to'] = str(st.session_state.blotter_dt)

    trades = bm.search_trades(book_id, filters=filters,
                               include_cancelled=True)

    # ── Export buttons ───────────────────────────────────────
    ec1, ec2, ec3 = st.columns([2, 2, 6])
    with ec1:
        try:
            xl_bytes = exporter.export_excel_bytes(book, metrics)
            st.download_button(
                "Excel",
                data=xl_bytes,
                file_name=f"ravinala_{book.name.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
                key="dl_excel"
            )
        except ImportError:
            st.button("Excel (install openpyxl)", disabled=True, width="stretch")
    with ec2:
        csv_bytes = exporter.export_csv_bytes(book)
        st.download_button(
            "CSV",
            data=csv_bytes,
            file_name=f"ravinala_{book.name.replace(' ', '_')}.csv",
            mime="text/csv",
            width="stretch",
            key="dl_csv"
        )

    st.markdown("---")

    # ── Trade table ─────────────────────────────────────────
    if not trades:
        st.info("No trades match the current filters. Use **New Trade** to add one.")
        return

    # Pagination
    PAGE_SIZE = 50
    total_pages = max(1, (len(trades) + PAGE_SIZE - 1) // PAGE_SIZE)
    if 'blotter_page' not in st.session_state:
        st.session_state.blotter_page = 0
    page = st.session_state.blotter_page
    page_trades = trades[page * PAGE_SIZE: (page + 1) * PAGE_SIZE]

    if HAS_PANDAS:
        rows = []
        for t in page_trades:
            pr = t.get_current_pricing()
            pnl_val = t.total_pnl or 0
            rows.append({
                'Ref': t.internal_ref or t.trade_id[:10],
                'Product': t.product_name or PRODUCT_TYPE_LABELS.get(t.product_type, t.product_type),
                'Underlyings': ' / '.join(u.get('ticker', '') for u in t.underlyings),
                'Dir': t.direction.upper(),
                'Notional': t.notional,
                'CCY': t.currency,
                'Inception': t.inception_date,
                'Maturity': t.maturity_date,
                'Entry %': t.entry_price,
                'MTM': t.current_mtm,
                f'P&L ({book.currency})': pnl_val,
                'Δ': round(pr.delta, 3) if pr and pr.delta is not None else None,
                'V': round(pr.vega, 3) if pr and pr.vega is not None else None,
                'Status': STATUS_ICONS.get(t.status, '') + ' ' + t.status.upper(),
            })
        df = pd.DataFrame(rows)
        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
            height=min(600, 60 + len(rows) * 36),
            column_config={
                'Notional': st.column_config.NumberColumn(format="%.0f"),
                'Entry %': st.column_config.NumberColumn(format="%.4f"),
                'MTM': st.column_config.NumberColumn(format="%.0f"),
                f'P&L ({book.currency})': st.column_config.NumberColumn(format="%.0f"),
                'Δ': st.column_config.NumberColumn(format="%.3f"),
                'V': st.column_config.NumberColumn(format="%.3f"),
            }
        )
    else:
        for t in page_trades:
            st.write(f"**{t.internal_ref}** — {t.product_name} — {t.status.upper()}")

    # Pagination controls
    if total_pages > 1:
        pc1, pc2, pc3 = st.columns([1, 4, 1])
        with pc1:
            if st.button("← Prev", disabled=(page == 0), key="blotter_prev"):
                st.session_state.blotter_page = max(0, page - 1)
                st.rerun()
        with pc2:
            st.markdown(f"<p style='text-align:center;color:#64748B;font-size:12px'>"
                        f"Page {page + 1} / {total_pages} ({len(trades)} trades)</p>",
                        unsafe_allow_html=True)
        with pc3:
            if st.button("Next →", disabled=(page >= total_pages - 1), key="blotter_next"):
                st.session_state.blotter_page = min(total_pages - 1, page + 1)
                st.rerun()

    # ── Click on trade → inspector ────────────────────────
    st.markdown("---")
    sel_ref = st.selectbox(
        "Open trade in Inspector →",
        options=[''] + [t.internal_ref or t.trade_id for t in page_trades],
        key="blotter_select_trade"
    )
    if sel_ref:
        # Find trade and set inspector
        for t in page_trades:
            if (t.internal_ref or t.trade_id) == sel_ref:
                st.session_state.inspector_trade_id = t.trade_id
                break
        st.info("Switch to **Trade Inspector** tab to view details.")


# ═══════════════════════════════════════════════════════════════
# TAB 2: BOOK ANALYTICS
# ═══════════════════════════════════════════════════════════════

def _render_book_analytics(bm: BookManager, book_id: str):
    st.subheader("Book Analytics")
    metrics = bm.compute_book_metrics(book_id)
    book = bm.load_book(book_id)

    # ── PDF Report Buttons ───────────────────────────────────
    if HAS_REPORTING:
        br1, br2, br3, _ = st.columns([2, 2, 2, 4])
        with br1:
            if st.button("Risk Report", width="stretch", key="btn_risk_rpt"):
                with st.spinner("Generating Risk Report..."):
                    try:
                        gen = RiskReportGenerator()
                        path = gen.generate(book.to_dict(), book_metrics=metrics)
                        with open(path, 'rb') as f:
                            st.download_button(
                                "Download Risk Report",
                                data=f.read(),
                                file_name=f"risk_report_{book_id}.pdf",
                                mime="application/pdf",
                                key="dl_risk_rpt",
                            )
                    except Exception as e:
                        st.error(f"Risk Report error: {e}")
        with br2:
            if st.button("P&L Report", width="stretch", key="btn_pnl_rpt"):
                with st.spinner("Generating P&L Report..."):
                    try:
                        snaps = bm.list_snapshots(book_id)
                        snap_today = bm.load_snapshot(book_id, snaps[0]['date']) if snaps else None
                        snap_yest  = bm.load_snapshot(book_id, snaps[1]['date']) if len(snaps) > 1 else None
                        gen = DailyPnLReportGenerator()
                        path = gen.generate(
                            book.to_dict(),
                            snapshot_today=snap_today.to_dict() if snap_today else None,
                            snapshot_yesterday=snap_yest.to_dict() if snap_yest else None,
                        )
                        with open(path, 'rb') as f:
                            st.download_button(
                                "Download P&L Report",
                                data=f.read(),
                                file_name=f"pnl_report_{book_id}.pdf",
                                mime="application/pdf",
                                key="dl_pnl_rpt",
                            )
                    except Exception as e:
                        st.error(f"P&L Report error: {e}")
        with br3:
            if st.button("Export Excel", width="stretch", key="btn_xl_rpt"):
                with st.spinner("Generating Excel..."):
                    try:
                        exporter = TradeBookExporter()
                        xl_bytes = exporter.export_excel_bytes(book)
                        st.download_button(
                            "Download Excel",
                            data=xl_bytes,
                            file_name=f"book_{book_id}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="dl_xl_rpt",
                        )
                    except Exception as e:
                        st.error(f"Excel export error: {e}")
    st.markdown("---")

    def _fmt_m(v, ccy=''):
        if v is None:
            return 'N/A'
        if abs(v) >= 1_000_000:
            return f"{ccy}{v/1_000_000:.2f}M"
        return f"{ccy}{v/1_000:.1f}K"

    # ── Row 1: KPIs ─────────────────────────────────────────
    st.markdown("##### Key Performance Indicators")
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Total Trades", metrics['total_trades'])
    with k2:
        st.metric("Live", metrics['live_trades'])
    with k3:
        st.metric("Notional", _fmt_m(metrics['total_notional'], book.currency + ' '))
    with k4:
        st.metric("Total MTM", _fmt_m(metrics['total_mtm'], book.currency + ' '))
    with k5:
        pnl = metrics.get('total_pnl', 0) or 0
        color = "normal" if pnl >= 0 else "inverse"
        st.metric("Total P&L", _fmt_m(pnl, book.currency + ' '),
                  delta=f"{pnl/max(metrics['total_notional'], 1)*100:.2f}%" if metrics['total_notional'] else None,
                  delta_color=color)

    st.markdown("---")

    if not HAS_PLOTLY:
        st.warning("Install plotly for charts: `pip install plotly`")
        return

    # ── Row 2: Composition Charts ────────────────────────────
    st.markdown("##### Portfolio Composition")
    c1, c2, c3 = st.columns(3)

    with c1:
        pt_data = metrics.get('total_notional_by_product_type', {})
        if pt_data:
            labels = [PRODUCT_TYPE_LABELS.get(k, k) for k in pt_data.keys()]
            fig = go.Figure(go.Pie(
                labels=labels, values=list(pt_data.values()),
                hole=0.45,
                marker_colors=['#34D399', '#2DD4BF', '#FBBF24', '#60A5FA',
                               '#A78BFA', '#F87171', '#FB923C', '#4ADE80']
            ))
            fig.update_layout(
                title="By Product Type", height=280,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94A3B8', margin=dict(t=40, b=10, l=10, r=10),
                legend=dict(font_size=9)
            )
            st.plotly_chart(fig, width="stretch")

    with c2:
        ac_data = metrics.get('total_notional_by_asset_class', {})
        if ac_data:
            labels = [ASSET_CLASS_LABELS.get(k, k) for k in ac_data.keys()]
            fig2 = go.Figure(go.Pie(
                labels=labels, values=list(ac_data.values()),
                hole=0.45,
                marker_colors=['#059669', '#0891B2', '#7C3AED', '#DC2626',
                               '#D97706', '#0D9488', '#9333EA', '#16A34A']
            ))
            fig2.update_layout(
                title="By Asset Class", height=280,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94A3B8', margin=dict(t=40, b=10, l=10, r=10),
                legend=dict(font_size=9)
            )
            st.plotly_chart(fig2, width="stretch")

    with c3:
        conc = metrics.get('concentration', {})
        if conc:
            tickers = list(conc.keys())[:8]
            values = [conc[k] for k in tickers]
            fig3 = go.Figure(go.Bar(
                x=tickers, y=values,
                marker_color='#34D399',
                text=[f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K" for v in values],
                textposition='auto'
            ))
            fig3.update_layout(
                title="Top Underlyings", height=280, xaxis_tickangle=-30,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color='#94A3B8', margin=dict(t=40, b=40, l=10, r=10)
            )
            st.plotly_chart(fig3, width="stretch")

    # ── Row 3: Greeks ───────────────────────────────────────
    st.markdown("---")
    st.markdown("##### Aggregate Greeks")
    g1, g2, g3, g4, g5 = st.columns(5)
    greeks = [
        ("Δ Delta", metrics.get('aggregate_delta', 0)),
        ("Γ Gamma", metrics.get('aggregate_gamma', 0)),
        ("V Vega", metrics.get('aggregate_vega', 0)),
        ("θ Theta", metrics.get('aggregate_theta', 0)),
        ("ρ Rho", metrics.get('aggregate_rho', 0)),
    ]
    for col, (name, val) in zip([g1, g2, g3, g4, g5], greeks):
        with col:
            st.metric(name, f"{val:.4f}" if val else "0.0000")

    # ── Row 4: P&L Waterfall ────────────────────────────────
    st.markdown("---")
    st.markdown("##### P&L by Trade")
    trades = bm.search_trades(book_id, filters={'status': ['live']})
    if trades and HAS_PLOTLY:
        trade_refs = [t.internal_ref or t.trade_id[:8] for t in trades]
        pnl_vals = [t.total_pnl or 0 for t in trades]
        colors_bar = ['#22C55E' if v >= 0 else '#EF4444' for v in pnl_vals]

        fig4 = go.Figure(go.Bar(
            x=trade_refs, y=pnl_vals,
            marker_color=colors_bar,
            text=[f"{v:+,.0f}" for v in pnl_vals],
            textposition='auto', textfont_size=9
        ))
        fig4.update_layout(
            title="P&L per Trade", height=300,
            xaxis_tickangle=-45,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94A3B8', margin=dict(t=40, b=60, l=10, r=10),
            yaxis_tickformat=',.0f'
        )
        fig4.add_hline(y=0, line_dash='dash', line_color='#475569')
        st.plotly_chart(fig4, width="stretch")

    # ── Row 5: Maturity Profile ──────────────────────────────
    st.markdown("---")
    st.markdown("##### Maturity Profile")
    mp = metrics.get('maturity_profile', {})
    if mp and HAS_PLOTLY:
        buckets = list(mp.keys())
        vals = [mp[k] for k in buckets]
        fig5 = go.Figure(go.Bar(
            x=buckets, y=vals,
            marker_color='#2DD4BF',
            text=[f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K" for v in vals],
            textposition='auto'
        ))
        fig5.update_layout(
            title=f"Notional by Maturity Bucket ({book.currency})", height=260,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94A3B8', margin=dict(t=40, b=20, l=10, r=10)
        )
        st.plotly_chart(fig5, width="stretch")


# ═══════════════════════════════════════════════════════════════
# TAB 3: P&L TRACKER
# ═══════════════════════════════════════════════════════════════

def _render_pnl_tracker(bm: BookManager, book_id: str):
    st.subheader("P&L Tracker")

    col1, col2 = st.columns([3, 1])
    with col1:
        period = st.select_slider(
            "Period",
            options=['1W', '1M', '3M', '6M', '1Y', 'YTD', 'ALL'],
            value='3M',
            key='pnl_period'
        )
    with col2:
        if st.button("Take Snapshot", width="stretch", key="pnl_snap"):
            bm.take_snapshot(book_id)
            st.success("Snapshot saved!")

    # Compute date range
    today = date.today()
    period_map = {
        '1W': today - timedelta(weeks=1),
        '1M': today - timedelta(days=30),
        '3M': today - timedelta(days=90),
        '6M': today - timedelta(days=180),
        '1Y': today - timedelta(days=365),
        'YTD': date(today.year, 1, 1),
        'ALL': None,
    }
    from_date = str(period_map[period]) if period_map.get(period) else None

    history = bm.compute_historical_pnl(book_id, from_date=from_date)

    snaps = bm.list_snapshots(book_id)
    if not snaps:
        st.info(
            "No snapshots yet. Take a snapshot daily to track P&L over time.\n\n"
            "Click **Take Snapshot** above to save today's state."
        )
        return

    if HAS_PANDAS and HAS_PLOTLY and isinstance(history, __import__('pandas').DataFrame) and not history.empty:
        # Cumulative P&L chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=history['date'], y=history['total_pnl'],
            mode='lines+markers', name='Total P&L',
            line=dict(color='#34D399', width=2),
            marker=dict(size=4),
            fill='tozeroy',
            fillcolor='rgba(52,211,153,0.08)'
        ))
        fig.update_layout(
            title="Cumulative P&L Over Time", height=320,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94A3B8',
            yaxis_tickformat=',.0f',
            xaxis_gridcolor='rgba(255,255,255,0.05)',
            yaxis_gridcolor='rgba(255,255,255,0.05)',
        )
        fig.add_hline(y=0, line_dash='dash', line_color='#475569')
        st.plotly_chart(fig, width="stretch")

        # MTM chart
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=history['date'], y=history['total_mtm'],
            mode='lines', name='Total MTM',
            line=dict(color='#2DD4BF', width=2),
        ))
        fig2.update_layout(
            title="Total Mark-to-Market", height=260,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color='#94A3B8', yaxis_tickformat=',.0f',
            xaxis_gridcolor='rgba(255,255,255,0.05)',
            yaxis_gridcolor='rgba(255,255,255,0.05)',
        )
        st.plotly_chart(fig2, width="stretch")

        # Table
        st.markdown("##### Snapshot History")
        st.dataframe(history, width="stretch", hide_index=True,
                     column_config={
                         'date': st.column_config.DateColumn(),
                         'total_mtm': st.column_config.NumberColumn(format="%.0f"),
                         'total_pnl': st.column_config.NumberColumn(format="%.0f"),
                         'unrealized_pnl': st.column_config.NumberColumn(format="%.0f"),
                         'realized_pnl': st.column_config.NumberColumn(format="%.0f"),
                     })
    else:
        st.markdown("##### Snapshot History")
        snap_list = bm.list_snapshots(book_id)
        for s in snap_list[:20]:
            snap = bm.load_snapshot(book_id, s['date'])
            if snap:
                m = snap.book_metrics
                pnl = m.get('total_pnl', 0) or 0
                color = "#22C55E" if pnl >= 0 else "#EF4444"
                st.markdown(
                    f"**{s['date']}** — MTM: {m.get('total_mtm', 0):,.0f}  |  "
                    f"P&L: <span style='color:{color}'>{pnl:+,.0f}</span>",
                    unsafe_allow_html=True
                )


# ═══════════════════════════════════════════════════════════════
# TAB 4: TRADE INSPECTOR
# ═══════════════════════════════════════════════════════════════

def _render_trade_inspector(bm: BookManager, book: Book, book_id: str):
    st.subheader("Trade Inspector")
    trades = book.get_trades()

    if not trades:
        st.info("No trades in book yet. Create one in **New Trade**.")
        return

    # Selector
    options = {(t.internal_ref or t.trade_id): t.trade_id for t in trades}
    default_sel = st.session_state.get('inspector_trade_id')
    opt_labels = list(options.keys())
    default_idx = 0
    if default_sel:
        for i, t in enumerate(trades):
            if t.trade_id == default_sel:
                default_idx = i
                break

    sel_label = st.selectbox("Select Trade", opt_labels, index=default_idx,
                              key="inspector_select")
    if not sel_label:
        return

    trade_id = options[sel_label]
    try:
        t = bm.get_trade(book_id, trade_id)
    except KeyError:
        st.error("Trade not found.")
        return

    # ── Action bar ──────────────────────────────────────────
    a1, a2, a3, a4, a5 = st.columns(5)
    with a1:
        if st.button("Reprice", key="insp_reprice", width="stretch"):
            with st.spinner("Repricing..."):
                try:
                    result = bm.reprice_trade(book_id, trade_id)
                    st.success(f"MTM: {result.notional_value:,.0f} {t.currency}")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
    with a2:
        if st.button("Clone", key="insp_clone", width="stretch"):
            new_id = bm.clone_trade(book_id, trade_id, cloned_by=get_current_user())
            new_trade = bm.get_trade(book_id, new_id)
            st.success(f"Cloned → {new_trade.internal_ref}")
    with a3:
        if st.button("Template", key="insp_tpl", width="stretch"):
            st.session_state['save_as_tpl_id'] = trade_id
    with a4:
        if t.status != TradeStatus.CANCELLED.value:
            if st.button("Delete", key="insp_del", width="stretch"):
                st.session_state['confirm_del_id'] = trade_id
    with a5:
        if st.button("Reports", key="insp_reports", width="stretch"):
            st.session_state['show_report_menu'] = trade_id

    # ── PDF Report Menu ────────────────────────────────────────
    if st.session_state.get('show_report_menu') == trade_id:
        if not HAS_REPORTING:
            st.warning("PDF reporting module not available. Check that `src/reporting/` is installed.")
        else:
            st.markdown("**Generate PDF Report:**")
            rc1, rc2, rc3, rc4 = st.columns(4)
            trade_dict = t.to_dict()

            with rc1:
                doc_mode = st.selectbox("Mode", ['final', 'draft', 'indicative', 'internal'],
                                         key=f"report_mode_{trade_id}")
            with rc2:
                if st.button("Term Sheet", key=f"btn_ts_{trade_id}", width="stretch"):
                    with st.spinner("Generating Term Sheet..."):
                        try:
                            gen = TermSheetGenerator()
                            path = gen.generate(trade_dict, mode=doc_mode)
                            with open(path, 'rb') as f:
                                pdf_data = f.read()
                            st.download_button(
                                "Download Term Sheet",
                                data=pdf_data,
                                file_name=f"termsheet_{t.internal_ref}.pdf",
                                mime="application/pdf",
                                key=f"dl_ts_{trade_id}",
                            )
                        except Exception as e:
                            st.error(f"Term Sheet error: {e}")
            with rc3:
                if st.button("Pre-Trade Report", key=f"btn_pt_{trade_id}", width="stretch"):
                    with st.spinner("Generating Pre-Trade Analysis..."):
                        try:
                            gen = PreTradeReportGenerator()
                            path = gen.generate(trade_dict)
                            with open(path, 'rb') as f:
                                pdf_data = f.read()
                            st.download_button(
                                "Download Pre-Trade Report",
                                data=pdf_data,
                                file_name=f"pretrade_{t.internal_ref}.pdf",
                                mime="application/pdf",
                                key=f"dl_pt_{trade_id}",
                            )
                        except Exception as e:
                            st.error(f"Pre-Trade Report error: {e}")
            with rc4:
                client_name_input = st.text_input("Client name", key=f"client_name_{trade_id}",
                                                   placeholder="Optional")
                if st.button("Client Deck", key=f"btn_cp_{trade_id}", width="stretch"):
                    with st.spinner("Generating Client Presentation..."):
                        try:
                            gen = ClientPresentationGenerator()
                            path = gen.generate(trade_dict,
                                                client_name=client_name_input or '',
                                                prepared_by=get_current_user())
                            with open(path, 'rb') as f:
                                pdf_data = f.read()
                            st.download_button(
                                "Download Client Deck",
                                data=pdf_data,
                                file_name=f"client_deck_{t.internal_ref}.pdf",
                                mime="application/pdf",
                                key=f"dl_cp_{trade_id}",
                            )
                        except Exception as e:
                            st.error(f"Client Presentation error: {e}")

    # Save as template
    if st.session_state.get('save_as_tpl_id') == trade_id:
        tpl_name = st.text_input("Template name", value=t.product_name or t.internal_ref,
                                  key="tpl_name_input")
        if st.button("Save Template", key="save_tpl_confirm"):
            bm.save_as_template(book_id, trade_id, tpl_name)
            st.success(f"Template '{tpl_name}' saved!")
            del st.session_state['save_as_tpl_id']

    # Confirm delete
    if st.session_state.get('confirm_del_id') == trade_id:
        st.warning(f"Soft-delete trade **{t.internal_ref}**? This sets status to CANCELLED.")
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("Confirm Delete", key="del_confirm"):
                bm.delete_trade(book_id, trade_id, deleted_by=get_current_user())
                del st.session_state['confirm_del_id']
                st.success("Trade cancelled.")
                st.rerun()
        with dc2:
            if st.button("Cancel", key="del_cancel"):
                del st.session_state['confirm_del_id']

    st.markdown("---")

    # ── Main info grid ───────────────────────────────────────
    pr = t.get_current_pricing()

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("##### Trade Details")
        st.markdown(f"""
| Field | Value |
|-------|-------|
| **Reference** | `{t.internal_ref}` |
| **Product** | {t.product_name} |
| **Type** | {PRODUCT_TYPE_LABELS.get(t.product_type, t.product_type)} |
| **Direction** | {t.direction.upper()} |
| **Status** | {STATUS_ICONS.get(t.status,'')} {t.status.upper()} |
| **Notional** | {t.currency} {t.notional:,.0f} |
| **Inception** | {t.inception_date or '—'} |
| **Maturity** | {t.maturity_date or '—'} |
| **Tenor** | {t.tenor_years:.2f}Y |
| **Counterparty** | {t.counterparty or '—'} |
| **Desk** | {t.desk or '—'} |
| **Version** | V{t.current_version} |
        """)

    with col_right:
        st.markdown("##### Pricing & P&L")
        if pr:
            pnl_color = "#22C55E" if (t.total_pnl or 0) >= 0 else "#EF4444"
            st.markdown(f"""
| Field | Value |
|-------|-------|
| **Model** | {pr.model.replace('_', ' ').title()} {'STALE' if pr.is_stale else ''} |
| **Entry Price** | {t.entry_price:.4f}% |
| **Current Price** | {pr.price:.4f}% |
| **MTM** | {t.currency} {pr.notional_value:,.0f} |
| **Unrealized P&L** | {t.unrealized_pnl:+,.0f} {t.pnl_currency} |
| **Realized P&L** | {t.realized_pnl:+,.0f} {t.pnl_currency} |
| **Total P&L** | {(t.total_pnl or 0):+,.0f} {t.pnl_currency} |
| **Implied Vol** | {pr.vol_used*100:.2f}% |
| **Rate** | {pr.rate_used*100:.2f}% |
| **Priced** | {(pr.timestamp or '')[:16]} |
            """)
        else:
            st.info("Not yet priced. Click **Reprice** above.")

    st.markdown("---")

    # ── Underlyings & Greeks ─────────────────────────────────
    col_ul, col_gr = st.columns(2)
    with col_ul:
        st.markdown("##### Underlyings")
        for u in t.underlyings:
            s0 = u.get('spot_at_inception', 0)
            sc = u.get('current_spot') or s0
            perf = (sc - s0) / s0 * 100 if s0 else None
            perf_str = (
                f"<span style='color:{'#22C55E' if perf >= 0 else '#EF4444'}'>"
                f"{perf:+.2f}%</span>"
            ) if perf is not None else "—"
            st.markdown(
                f"**{u.get('ticker','?')}** — {u.get('name','')}<br>"
                f"Spot @ inception: {s0:,.2f}  →  Current: {sc:,.2f}  {perf_str}",
                unsafe_allow_html=True
            )

    with col_gr:
        st.markdown("##### Greeks")
        if pr:
            for name, val in [
                ("Δ Delta", pr.delta), ("Γ Gamma", pr.gamma),
                ("V Vega", pr.vega), ("θ Theta", pr.theta),
                ("ρ Rho", pr.rho),
            ]:
                if val is not None:
                    st.markdown(f"**{name}:** `{val:.6f}`")

    st.markdown("---")

    # ── Barriers & Coupon ────────────────────────────────────
    if t.barriers or t.coupon:
        bc1, bc2 = st.columns(2)
        with bc1:
            if t.barriers:
                st.markdown("##### Barriers")
                for b in t.barriers:
                    trig = " TRIGGERED" if b.get('is_triggered') else ""
                    st.markdown(
                        f"**{b.get('barrier_type','').replace('_',' ').title()}** — "
                        f"{b.get('level_pct','')}% ({b.get('observation','').replace('_',' ')}){trig}"
                    )
        with bc2:
            if t.coupon:
                c = t.coupon
                st.markdown("##### Coupon")
                st.markdown(f"""
- **Rate:** {c.get('rate_pct','')}% {c.get('frequency','')}
- **Conditional:** {'Yes' if c.get('is_conditional') else 'No'}
- **Memory:** {'Yes' if c.get('is_memory') else 'No'}
- **Barrier:** {c.get('condition_barrier_pct', '—')}%
                """)
        st.markdown("---")

    # ── Versions ────────────────────────────────────────────
    if t.versions:
        st.markdown("##### Version History")
        for v in reversed(t.versions[-5:]):
            is_current = (v['version'] == t.current_version)
            badge = " ← **current**" if is_current else ""
            st.markdown(
                f"**V{v['version']}**{badge} — "
                f"{v.get('created_at','')[:10]} — "
                f"{v.get('created_by','?')} — "
                f"_{v.get('change_description','')}_"
            )
        st.markdown("---")

    # ── Notes & Tags ─────────────────────────────────────────
    st.markdown("##### Notes & Tags")
    tag_str = "  ".join(f"`{tag}`" for tag in t.tags) if t.tags else "—"
    st.markdown(f"**Tags:** {tag_str}")
    if t.notes:
        st.markdown(f"**Notes:** {t.notes}")

    with st.expander("Edit Notes & Tags"):
        new_notes = st.text_area("Notes", value=t.notes, key=f"notes_{trade_id}")
        new_tags = st.text_input("Tags (comma-separated)", value=', '.join(t.tags),
                                  key=f"tags_{trade_id}")
        if st.button("Save Changes", key=f"save_notes_{trade_id}"):
            bm.update_trade(book_id, trade_id, {
                'notes': new_notes,
                'tags': [tg.strip() for tg in new_tags.split(',') if tg.strip()],
            }, updated_by=get_current_user(), change_description="Notes/tags updated")
            st.success("Saved!")
            st.rerun()

    st.markdown("---")

    # ── Audit trail ─────────────────────────────────────────
    with st.expander("Audit Trail"):
        for entry in reversed(t.audit_trail[-20:]):
            ts = entry.get('timestamp', '')[:16]
            st.markdown(
                f"`{ts}` — **{entry.get('user','?')}** — "
                f"{entry.get('action','')} — {entry.get('details','')}"
            )


# ═══════════════════════════════════════════════════════════════
# TAB 5: NEW TRADE
# ═══════════════════════════════════════════════════════════════

def _render_new_trade(bm: BookManager, book_id: str):
    st.subheader("Create New Trade")

    with st.form("new_trade_form", clear_on_submit=False):
        st.markdown("#### 1. Product Type")
        product_type = st.selectbox(
            "Type",
            list(PRODUCT_TYPE_LABELS.keys()),
            format_func=lambda k: PRODUCT_TYPE_LABELS[k],
            key="nt_product_type"
        )

        st.markdown("#### 2. Underlying(s)")
        n_underlyings = st.number_input("Number of underlyings", 1, 5, 1,
                                         key="nt_n_ul")
        underlyings = []
        ul_cols = st.columns(min(int(n_underlyings), 3))
        for i in range(int(n_underlyings)):
            with ul_cols[i % len(ul_cols)]:
                st.markdown(f"**Underlying {i+1}**")
                ticker = st.text_input(f"Ticker", key=f"nt_ticker_{i}",
                                        placeholder="^STOXX50E")
                name = st.text_input(f"Name", key=f"nt_name_{i}",
                                      placeholder="Euro Stoxx 50")
                ac = st.selectbox(f"Asset Class", list(ASSET_CLASS_LABELS.keys()),
                                   format_func=lambda k: ASSET_CLASS_LABELS[k],
                                   key=f"nt_ac_{i}")
                spot = st.number_input(f"Spot", min_value=0.0, value=100.0,
                                        key=f"nt_spot_{i}", format="%.4f")
                ccy = st.text_input(f"Currency", value="USD", key=f"nt_ccy_{i}")
                underlyings.append({
                    'ticker': ticker.upper() if ticker else '',
                    'name': name,
                    'asset_class': ac,
                    'spot_at_inception': float(spot),
                    'current_spot': float(spot),
                    'currency': ccy,
                    'weight': 1.0 / max(int(n_underlyings), 1),
                })

        st.markdown("#### 3. Terms")
        t1, t2, t3 = st.columns(3)
        with t1:
            notional = st.number_input("Notional", min_value=1.0, value=1_000_000.0,
                                        step=100_000.0, key="nt_notional", format="%.0f")
            currency = st.selectbox("Currency", ["EUR", "USD", "GBP", "JPY", "CHF"],
                                     key="nt_currency")
        with t2:
            direction = st.selectbox("Direction", ["sell", "buy"], key="nt_direction")
            inception = st.date_input("Inception Date", value=date.today(), key="nt_inception")
        with t3:
            use_tenor = st.checkbox("Use tenor instead of maturity date", value=True,
                                     key="nt_use_tenor")
            if use_tenor:
                tenor = st.number_input("Tenor (years)", 0.1, 30.0, 1.0, 0.5,
                                         key="nt_tenor", format="%.2f")
                maturity_dt = inception + timedelta(days=int(float(tenor) * 365.25))
            else:
                tenor = 1.0
                maturity_dt = st.date_input("Maturity Date",
                                             value=inception + timedelta(days=365),
                                             key="nt_maturity")

        st.markdown("#### 4. Structure")
        s1, s2, s3 = st.columns(3)
        with s1:
            strike_pct = st.number_input("Strike (%)", 0.0, 300.0, 100.0, 5.0,
                                          key="nt_strike")
        with s2:
            has_barrier = st.checkbox("Has Barrier?", key="nt_has_barrier")
        with s3:
            has_coupon = st.checkbox("Has Coupon?", key="nt_has_coupon")

        barriers = []
        if has_barrier:
            st.markdown("**Barrier**")
            bb1, bb2, bb3 = st.columns(3)
            with bb1:
                b_level = st.number_input("Barrier Level (%)", 0.0, 200.0, 60.0,
                                           key="nt_b_level")
                b_type = st.selectbox("Type",
                                       ['knock_in', 'knock_out', 'autocall', 'coupon'],
                                       key="nt_b_type")
            with bb2:
                b_obs = st.selectbox("Observation",
                                      ['at_maturity', 'discrete', 'continuous'],
                                      key="nt_b_obs")
            barriers = [{
                'level_pct': float(b_level),
                'level_abs': float(b_level) / 100 * float(underlyings[0].get('spot_at_inception', 100)) if underlyings else 0,
                'barrier_type': b_type,
                'observation': b_obs,
                'is_triggered': False,
            }]

        coupon = None
        if has_coupon:
            st.markdown("**Coupon**")
            cb1, cb2, cb3 = st.columns(3)
            with cb1:
                c_rate = st.number_input("Coupon Rate (%)", 0.0, 50.0, 8.0, 0.5,
                                          key="nt_c_rate")
                c_freq = st.selectbox("Frequency",
                                       ['annual', 'semi_annual', 'quarterly', 'monthly'],
                                       key="nt_c_freq")
            with cb2:
                c_cond = st.checkbox("Conditional?", key="nt_c_cond")
                c_memory = st.checkbox("Memory effect?", key="nt_c_mem")
            with cb3:
                c_barrier = st.number_input("Coupon barrier (%)", 0.0, 200.0, 70.0,
                                             key="nt_c_bar") if c_cond else None
            coupon = {
                'rate_pct': float(c_rate),
                'frequency': c_freq,
                'is_conditional': c_cond,
                'condition_barrier_pct': float(c_barrier) if c_cond and c_barrier else None,
                'is_memory': c_memory,
                'paid_coupons': [],
            }

        st.markdown("#### 5. Pricing")
        p1, p2, p3 = st.columns(3)
        with p1:
            model = st.selectbox("Model", ["black_scholes", "monte_carlo", "binomial"],
                                  key="nt_model")
        with p2:
            vol = st.number_input("Implied Vol (%)", 0.1, 200.0, 20.0, 1.0,
                                   key="nt_vol", format="%.2f")
            rate = st.number_input("Risk-free Rate (%)", 0.0, 20.0, 3.5, 0.1,
                                    key="nt_rate", format="%.2f")
        with p3:
            div = st.number_input("Dividend Yield (%)", 0.0, 20.0, 2.0, 0.1,
                                   key="nt_div", format="%.2f")
            mc_paths = st.number_input("MC Paths", 1000, 500000, 10000, 1000,
                                        key="nt_mc") if model == 'monte_carlo' else None

        st.markdown("#### 6. Metadata")
        m1, m2, m3 = st.columns(3)
        with m1:
            counterparty = st.text_input("Counterparty", key="nt_cpty",
                                          placeholder="Client ABC")
        with m2:
            desk = st.text_input("Desk", key="nt_desk",
                                  placeholder="Equity Derivatives")
            product_name = st.text_input("Product Name", key="nt_pname",
                                          placeholder="5Y Autocall on SX5E")
        with m3:
            tags_str = st.text_input("Tags (comma-separated)", key="nt_tags",
                                      placeholder="autocall, sx5e, client_abc")
            notes = st.text_area("Notes", key="nt_notes", height=80)

        submitted = st.form_submit_button(
            "Price & Save to Book", width="stretch", type="primary"
        )

        if submitted:
            if not any(u.get('ticker') for u in underlyings):
                st.error("Please enter at least one ticker.")
            else:
                # Build a simple pricing result
                S = underlyings[0].get('spot_at_inception', 100.0)
                K_pct = float(strike_pct) if strike_pct else 100.0
                K = K_pct / 100 * S
                T = float(tenor) if tenor else 1.0
                sigma = float(vol) / 100
                r = float(rate) / 100
                q = float(div) / 100
                n = float(notional)

                from tradebook import _bs_greeks
                if product_type in ('vanilla_call', 'vanilla_put'):
                    price_pct, delta, gamma, vega, theta, rho = _bs_greeks(
                        S, K, T, r, sigma, is_call=(product_type == 'vanilla_call'), q=q
                    )
                else:
                    price_pct = 100.0
                    delta = gamma = vega = theta = rho = None

                pr_result = PricingResult(
                    timestamp=datetime.utcnow().isoformat(),
                    model=model,
                    price=price_pct,
                    price_currency=currency,
                    notional_value=price_pct / 100 * n,
                    delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho,
                    spot_used=S, vol_used=sigma, rate_used=r,
                    mc_paths=int(mc_paths) if mc_paths else None,
                )

                trade = build_trade_from_pricing(
                    product_type=product_type,
                    product_name=product_name or PRODUCT_TYPE_LABELS.get(product_type, ''),
                    underlyings=underlyings,
                    notional=n,
                    currency=currency,
                    pricing_result=pr_result,
                    direction=direction,
                    tenor_years=T,
                    inception_date=str(inception),
                    maturity_date=str(maturity_dt),
                    strike_pct=float(strike_pct) if strike_pct else None,
                    barriers=barriers,
                    coupon=coupon,
                    pricing_model=model,
                    pricing_params={'vol': sigma, 'rate': r, 'div': q},
                    counterparty=counterparty,
                    desk=desk,
                    tags=[t.strip() for t in tags_str.split(',') if t.strip()],
                    notes=notes,
                    created_by=get_current_user(),
                )

                trade_id = bm.add_trade(book_id, trade)
                st.success(f"Trade **{trade.internal_ref}** saved! Price: {price_pct:.4f}%")
                st.balloons()


# ═══════════════════════════════════════════════════════════════
# TAB 6: TEMPLATES
# ═══════════════════════════════════════════════════════════════

def _render_templates(bm: BookManager, book_id: str):
    st.subheader("Trade Templates")
    templates = bm.list_templates()

    if not templates:
        st.info(
            "No templates saved yet.\n\n"
            "Open a trade in **Trade Inspector** and click **Template** to save it."
        )
        return

    for tpl in templates:
        with st.expander(
            f"**{tpl['template_name']}** — "
            f"{PRODUCT_TYPE_LABELS.get(tpl['product_type'], tpl['product_type'])} — "
            f"saved {tpl.get('saved_at','')[:10]}"
        ):
            col1, col2 = st.columns([3, 1])
            with col1:
                data = bm.load_template(tpl['template_name'])
                if data:
                    st.json({k: v for k, v in data.items()
                             if k not in ('template_name', 'saved_at', 'saved_from')})
            with col2:
                if st.button("Use Template", key=f"use_tpl_{tpl['file']}"):
                    st.session_state['pending_template'] = tpl['template_name']
                    st.info("Template loaded. Go to **New Trade** to fill in details.")
                if st.button("Delete", key=f"del_tpl_{tpl['file']}"):
                    bm.delete_template(tpl['template_name'])
                    st.success("Template deleted.")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════
# TAB 7: BOOK SETTINGS
# ═══════════════════════════════════════════════════════════════

def _render_book_settings(bm: BookManager):
    st.subheader("Book Settings")

    books = bm.list_books()
    book_names = {b['name']: b['book_id'] for b in books}
    current_id = get_active_book_id()
    current_name = next((b['name'] for b in books if b['book_id'] == current_id), 'Default Book')

    # ── Select active book ───────────────────────────────────
    st.markdown("##### Active Book")
    sel = st.selectbox("Select active book", list(book_names.keys()),
                        index=list(book_names.keys()).index(current_name)
                        if current_name in book_names else 0,
                        key="settings_book_sel")
    if book_names.get(sel) != current_id:
        if st.button("Switch to this book", key="switch_book"):
            st.session_state.active_book_id = book_names[sel]
            st.success(f"Switched to **{sel}**")
            st.rerun()

    # ── Create new book ──────────────────────────────────────
    st.markdown("---")
    st.markdown("##### Create New Book")
    with st.form("create_book_form", clear_on_submit=True):
        nb_name = st.text_input("Book name", placeholder="Client ABC Portfolio")
        nb_desc = st.text_input("Description", placeholder="Optional description")
        nb_ccy = st.selectbox("Reporting Currency", ["EUR", "USD", "GBP", "JPY"])
        if st.form_submit_button("Create Book"):
            new_book = bm.create_book(
                name=nb_name, description=nb_desc, currency=nb_ccy,
                created_by=get_current_user()
            )
            st.success(f"Book **{new_book.name}** created (id: {new_book.book_id})")
            st.rerun()

    # ── Rename / Delete ──────────────────────────────────────
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### Rename Book")
        new_name = st.text_input("New name", value=current_name, key="rename_input")
        if st.button("Rename", key="rename_btn"):
            book = bm.load_book(current_id)
            book.name = new_name
            bm.save_book(book)
            st.success(f"Renamed to **{new_name}**")
            st.rerun()
    with col2:
        st.markdown("##### Duplicate Book")
        dup_name = st.text_input("Duplicate name",
                                  value=f"Copy of {current_name}",
                                  key="dup_input")
        if st.button("Duplicate", key="dup_btn"):
            new_b = bm.duplicate_book(current_id, dup_name)
            st.success(f"Created duplicate: **{new_b.name}**")
            st.rerun()

    # ── Import / Export JSON ─────────────────────────────────
    st.markdown("---")
    st.markdown("##### Import / Export Book (JSON)")
    exp_col, imp_col = st.columns(2)
    with exp_col:
        book_data = bm.export_book_json(current_id)
        import json
        st.download_button(
            "Export Book JSON",
            data=json.dumps(book_data, indent=2, default=str).encode(),
            file_name=f"book_{current_id}.json",
            mime="application/json",
            width="stretch",
            key="export_json_btn"
        )
    with imp_col:
        uploaded = st.file_uploader("Import Book JSON", type=['json'],
                                     key="import_json_upload")
        if uploaded:
            import json as _json
            try:
                data = _json.load(uploaded)
                if st.button("Import", key="import_confirm"):
                    new_b = bm.import_book_json(data, new_name=f"Imported: {data.get('name','?')}")
                    st.success(f"Imported book **{new_b.name}**")
                    st.rerun()
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

    # ── Danger zone ──────────────────────────────────────────
    st.markdown("---")
    with st.expander("Danger Zone"):
        st.warning("These operations are irreversible.")
        if current_id != 'default':
            if st.button(f"Delete '{current_name}'", key="del_book"):
                if bm.delete_book(current_id):
                    st.session_state.active_book_id = 'default'
                    st.success(f"Book '{current_name}' deleted. Switched to Default.")
                    st.rerun()
        else:
            st.info("The Default book cannot be deleted.")

        if st.button("Purge CANCELLED trades (older than 30 days)", key="purge_btn"):
            book = bm.load_book(current_id)
            cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
            before = len(book.trades)
            book.trades = [
                t for t in book.trades
                if not (t.get('status') == 'cancelled' and t.get('updated_at', '') < cutoff)
            ]
            bm.save_book(book)
            purged = before - len(book.trades)
            st.success(f"Purged {purged} cancelled trade(s).")
            st.rerun()

    # ── Book list overview ────────────────────────────────────
    st.markdown("---")
    st.markdown("##### All Books")
    if HAS_PANDAS:
        df = pd.DataFrame(books)
        if not df.empty:
            st.dataframe(df[['name', 'currency', 'trade_count', 'created_at', 'book_id']],
                         width="stretch", hide_index=True)
    else:
        for b in books:
            st.write(f"**{b['name']}** ({b['book_id']}) — {b['trade_count']} trades")


# ═══════════════════════════════════════════════════════════════
# SAVE TO BOOK HELPER (for other tabs)
# ═══════════════════════════════════════════════════════════════

def render_save_to_book_button(
    product_type: str,
    product_name: str,
    underlyings: list,
    notional: float,
    currency: str,
    pricing_result: 'PricingResult',
    **kwargs
) -> bool:
    """
    Renders a "Save to Book" button.
    Call this from any pricing tab after displaying results.
    Returns True if the trade was saved.
    """
    if st.button("Save to Book", key=f"save_to_book_{product_type}_{id(pricing_result)}",
                 type="primary"):
        bm = get_book_manager()
        book_id = get_active_book_id()
        user = get_current_user()

        trade = build_trade_from_pricing(
            product_type=product_type,
            product_name=product_name,
            underlyings=underlyings,
            notional=notional,
            currency=currency,
            pricing_result=pricing_result,
            created_by=user,
            **kwargs
        )

        trade_id = bm.add_trade(book_id, trade)
        st.success(f"Saved to book! Ref: **{trade.internal_ref}**")
        st.balloons()
        return True
    return False
