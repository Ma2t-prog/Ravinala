"""
charts_export.py — Chart generation for the Ravinala PDF reporting engine.

All methods return PNG bytes suitable for embedding in PDF reports.
Charts use a clean white print layout, not dark themes.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math
from io import BytesIO
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# Print-optimised base layout (white background, dark text)
# ─────────────────────────────────────────────────────────────────────────────

PRINT_LAYOUT = dict(
    paper_bgcolor='white',
    plot_bgcolor='white',
    font=dict(color='#1E293B', family='Helvetica'),
    margin=dict(t=40, b=40, l=60, r=40),
)

# Brand colours (hex strings for plotly)
_EMERALD = '#059669'
_NAVY    = '#0F172A'
_DARK    = '#1E293B'
_MEDIUM  = '#475569'
_LIGHT   = '#94A3B8'
_PALE    = '#F1F5F9'
_GOLD    = '#D97706'
_BLUE    = '#2563EB'
_RED     = '#DC2626'
_GREEN   = '#16A34A'
_ORANGE  = '#EA580C'
_TEAL    = '#2DD4BF'

# Emerald palette for pie charts
_EMERALD_SHADES = [
    '#059669', '#34D399', '#047857', '#6EE7B7',
    '#065F46', '#A7F3D0', '#2563EB', '#D97706',
    '#DC2626', '#475569',
]


def _placeholder_png(width: int = 800, height: int = 400) -> bytes:
    """
    Return a minimal white PNG placeholder when chart export fails.
    Tries PIL first; falls back to a hand-crafted 1×1 white PNG.
    """
    try:
        from PIL import Image as PILImage
        img = PILImage.new('RGB', (width, height), color=(255, 255, 255))
        buf = BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()
    except Exception:
        # Minimal valid 1×1 white PNG (hardcoded bytes)
        return (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe'
            b'\xdc\xccY\xe7'
            b'\x00\x00\x00\x00IEND\xaeB`\x82'
        )


def _fig_to_png(fig: go.Figure, width: int, height: int) -> bytes:
    """Export a plotly figure to PNG bytes using kaleido, with fallback."""
    try:
        return fig.to_image(format='png', width=width, height=height)
    except Exception:
        return _placeholder_png(width, height)


def _apply_print_layout(fig: go.Figure) -> go.Figure:
    """Apply the standard print layout to a figure."""
    fig.update_layout(**PRINT_LAYOUT)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Black-Scholes helpers for greeks_sensitivity_chart
# ─────────────────────────────────────────────────────────────────────────────

def _norm_cdf(x: float) -> float:
    """Standard normal CDF via math.erfc."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _bs_price(S: float, K: float, T: float, r: float, sigma: float, is_call: bool) -> float:
    """Black-Scholes option price."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return max(0.0, (S - K) if is_call else (K - S))
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if is_call:
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def _bs_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Black-Scholes vega (sensitivity to 1-point vol change)."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    pdf_d1 = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)
    return S * pdf_d1 * math.sqrt(T)


# ─────────────────────────────────────────────────────────────────────────────
# ChartExporter
# ─────────────────────────────────────────────────────────────────────────────

class ChartExporter:
    """
    Generates publication-quality PNG charts for embedding in Ravinala PDF reports.

    All methods return bytes (PNG image data).
    """

    # ─────────────────────────────────────────────────────────────────────
    # 1. Payoff diagram
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def payoff_chart(trade: dict, width: int = 800, height: int = 400) -> bytes:
        """
        Payoff at maturity diagram for the given trade.

        X-axis : spot final as % of initial (40 % to 150 %, 500 points)
        Y-axis : total return to investor (% of notional)
        """
        import numpy as np

        product_type      = trade.get('product_type', 'custom')
        product_name      = trade.get('product_name', product_type)
        strike_pct        = trade.get('strike_pct') or 100.0
        capital_prot_pct  = trade.get('capital_protection_pct') or 100.0
        participation     = trade.get('participation_rate') or 100.0
        cap_pct           = trade.get('cap_pct')
        entry_price       = trade.get('entry_price') or 0.0

        # Estimate premium as % of notional from entry_price
        notional   = trade.get('notional') or 1.0
        premium_pct = (abs(entry_price) / notional * 100.0) if notional else 2.0
        if premium_pct == 0.0:
            premium_pct = 2.0  # sensible default

        spot_range = list(range(40, 151))   # 40 % to 150 %
        spots      = [s / 100.0 for s in spot_range]  # as decimals

        # ── Payoff calculation ───────────────────────────────────────
        barriers = trade.get('barriers') or []

        # Find KI and autocall barrier levels (as pct of initial)
        ki_pct   = None
        au_pct   = None
        for b in barriers:
            bt = str(b.get('barrier_type', '')).lower()
            lp = b.get('level_pct')
            if lp is None:
                continue
            if 'knock' in bt or 'ki' in bt or 'down' in bt:
                ki_pct = lp / 100.0
            elif 'autocall' in bt or 'call' in bt or 'up' in bt:
                au_pct = lp / 100.0

        coupon_dict     = trade.get('coupon') or {}
        coupon_rate_pct = coupon_dict.get('rate_pct') or 5.0
        tenor           = trade.get('tenor_years') or 1.0

        def calc_payoff(s: float) -> float:
            pt = product_type
            if pt == 'vanilla_call':
                return max(0.0, s * 100 - strike_pct) - premium_pct
            elif pt == 'vanilla_put':
                return max(0.0, strike_pct - s * 100) - premium_pct
            elif pt in ('autocall', 'phoenix', 'athena'):
                ki = ki_pct if ki_pct is not None else 0.6
                accumulated = coupon_rate_pct * tenor  # max coupons if held to maturity
                if s >= ki:
                    return accumulated + 100.0 - 100.0   # net return (0% base + coupons - notional returned → show as coupon return %)
                else:
                    return s * 100 - 100.0  # capital loss
            elif pt == 'reverse_convertible':
                ki = ki_pct if ki_pct is not None else 0.7
                total_coupon = coupon_rate_pct * tenor
                if s >= ki:
                    return total_coupon   # full capital back + coupon
                else:
                    return s * 100 - 100.0 + total_coupon  # capital loss + coupon
            elif pt == 'capital_protected_note':
                base   = capital_prot_pct - 100.0  # net vs 100% invested
                upside = (participation / 100.0) * max(0.0, s * 100 - 100.0)
                gross  = base + upside
                if cap_pct is not None:
                    gross = min(gross, cap_pct - 100.0)
                return gross
            else:
                # Generic: flat at par
                return 0.0

        y_vals = [calc_payoff(s) for s in spots]
        x_vals = [s * 100 for s in spots]   # display as %

        fig = go.Figure()

        # Shade loss zone (y < 0) — light red fill
        fig.add_hrect(
            y0=-200, y1=0,
            fillcolor='rgba(220,38,38,0.06)',
            layer='below', line_width=0,
        )
        # Shade gain zone (y > 0) — light green fill
        fig.add_hrect(
            y0=0, y1=200,
            fillcolor='rgba(22,163,74,0.06)',
            layer='below', line_width=0,
        )

        # Breakeven line at y = 0
        fig.add_hline(y=0, line_dash='dash', line_color=_MEDIUM, line_width=1)

        # Payoff line
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode='lines',
            name='Payoff',
            line=dict(color=_EMERALD, width=2.5),
        ))

        # Barrier vertical lines
        for b in barriers:
            lp = b.get('level_pct')
            if lp is None:
                continue
            bt = str(b.get('barrier_type', '')).lower()
            if 'knock' in bt or 'ki' in bt or 'down' in bt:
                bar_color = _RED
                bar_label = f'KI {lp:.0f}%'
            elif 'autocall' in bt or 'call' in bt:
                bar_color = _ORANGE
                bar_label = f'Autocall {lp:.0f}%'
            else:
                bar_color = _GREEN
                bar_label = f'Coupon {lp:.0f}%'

            fig.add_vline(
                x=lp, line_dash='dot', line_color=bar_color,
                line_width=1.5,
                annotation_text=bar_label,
                annotation_position='top',
                annotation_font_size=9,
            )

        fig.update_layout(
            title=dict(text=f'Payoff at Maturity — {product_name}', font=dict(size=13, color=_DARK)),
            xaxis=dict(title='Spot at Maturity (% of Initial)', ticksuffix='%', gridcolor=_PALE),
            yaxis=dict(title='Return (% of Notional)', ticksuffix='%', gridcolor=_PALE),
            showlegend=False,
            **PRINT_LAYOUT,
        )

        return _fig_to_png(fig, width, height)

    # ─────────────────────────────────────────────────────────────────────
    # 2. Scenario comparison bar chart
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def scenario_comparison_chart(scenarios: list, width: int = 800, height: int = 350) -> bytes:
        """
        Bar chart comparing scenario returns.

        Each scenario dict: {'name': str, 'return_pct': float, 'description': str}
        Green bars for positive, red for negative.
        """
        names   = [s.get('name', f'S{i}') for i, s in enumerate(scenarios)]
        returns = [s.get('return_pct', 0.0) for s in scenarios]
        colors  = [_GREEN if r >= 0 else _RED for r in returns]

        text_vals = [f'{r:+.1f}%' for r in returns]

        fig = go.Figure(go.Bar(
            x=names,
            y=returns,
            marker_color=colors,
            text=text_vals,
            textposition='outside',
            textfont=dict(size=10, color=_DARK),
        ))

        fig.add_hline(y=0, line_color=_DARK, line_width=1)

        fig.update_layout(
            title=dict(text='Scenario Analysis', font=dict(size=13, color=_DARK)),
            xaxis=dict(title='Scenario', gridcolor=_PALE),
            yaxis=dict(title='Return (% of Notional)', ticksuffix='%', gridcolor=_PALE),
            showlegend=False,
            **PRINT_LAYOUT,
        )

        return _fig_to_png(fig, width, height)

    # ─────────────────────────────────────────────────────────────────────
    # 3. P&L waterfall chart
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def pnl_waterfall_chart(attribution: dict, width: int = 800, height: int = 350) -> bytes:
        """
        Waterfall chart showing P&L attribution.

        attribution: {
            'delta_pnl', 'gamma_pnl', 'vega_pnl', 'theta_pnl',
            'other_pnl', 'total_pnl'
        }
        """
        component_keys = ['delta_pnl', 'gamma_pnl', 'vega_pnl', 'theta_pnl', 'other_pnl']
        labels_map = {
            'delta_pnl': 'Delta',
            'gamma_pnl': 'Gamma',
            'vega_pnl':  'Vega',
            'theta_pnl': 'Theta',
            'other_pnl': 'Other',
            'total_pnl': 'Total',
        }

        names    = []
        measures = []
        values   = []
        colors   = []

        for k in component_keys:
            v = attribution.get(k, 0.0) or 0.0
            names.append(labels_map[k])
            measures.append('relative')
            values.append(v)
            colors.append(_GREEN if v >= 0 else _RED)

        total = attribution.get('total_pnl', 0.0) or 0.0
        names.append('Total')
        measures.append('total')
        values.append(total)
        colors.append(_NAVY)

        fig = go.Figure(go.Waterfall(
            name='P&L Attribution',
            orientation='v',
            measure=measures,
            x=names,
            y=values,
            text=[f'{v:+,.0f}' for v in values],
            textposition='outside',
            connector=dict(line=dict(color=_LIGHT, width=1)),
            increasing=dict(marker=dict(color=_GREEN)),
            decreasing=dict(marker=dict(color=_RED)),
            totals=dict(marker=dict(color=_NAVY)),
        ))

        fig.update_layout(
            title=dict(text='P&L Attribution', font=dict(size=13, color=_DARK)),
            xaxis=dict(title='Greek Component', gridcolor=_PALE),
            yaxis=dict(title='P&L (currency)', gridcolor=_PALE),
            showlegend=False,
            **PRINT_LAYOUT,
        )

        return _fig_to_png(fig, width, height)

    # ─────────────────────────────────────────────────────────────────────
    # 4. Book allocation dual pie charts
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def book_allocation_charts(book_metrics: dict, width: int = 800, height: int = 350) -> bytes:
        """
        Two pie charts: notional by asset class (left) and by product type (right).

        book_metrics: {
            'by_asset_class':   {name: notional, ...},
            'by_product_type':  {name: notional, ...},
        }
        """
        by_ac = book_metrics.get('by_asset_class', {}) or {}
        by_pt = book_metrics.get('by_product_type', {}) or {}

        # Fallback data if empty
        if not by_ac:
            by_ac = {'No Data': 1}
        if not by_pt:
            by_pt = {'No Data': 1}

        fig = make_subplots(
            rows=1, cols=2,
            specs=[[{'type': 'pie'}, {'type': 'pie'}]],
            subplot_titles=['Notional by Asset Class', 'Notional by Product Type'],
        )

        fig.add_trace(
            go.Pie(
                labels=list(by_ac.keys()),
                values=list(by_ac.values()),
                marker=dict(colors=_EMERALD_SHADES[:len(by_ac)]),
                textinfo='label+percent',
                textfont=dict(size=9),
                hole=0.35,
                name='Asset Class',
            ),
            row=1, col=1,
        )

        fig.add_trace(
            go.Pie(
                labels=list(by_pt.keys()),
                values=list(by_pt.values()),
                marker=dict(colors=_EMERALD_SHADES[:len(by_pt)]),
                textinfo='label+percent',
                textfont=dict(size=9),
                hole=0.35,
                name='Product Type',
            ),
            row=1, col=2,
        )

        fig.update_layout(
            title=dict(text='Book Allocation', font=dict(size=13, color=_DARK)),
            showlegend=True,
            legend=dict(font=dict(size=9), orientation='v'),
            **PRINT_LAYOUT,
        )

        return _fig_to_png(fig, width, height)

    # ─────────────────────────────────────────────────────────────────────
    # 5. Maturity profile bar chart
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def maturity_profile_chart(book_metrics: dict, width: int = 800, height: int = 300) -> bytes:
        """
        Bar chart of notional by maturity bucket.

        book_metrics['maturity_profile']: {'0-1Y': 500000, '1-3Y': 2000000, ...}
        """
        profile = book_metrics.get('maturity_profile', {}) or {}
        if not profile:
            profile = {'No Data': 0}

        buckets   = list(profile.keys())
        notionals = list(profile.values())

        def _fmt(n: float) -> str:
            if abs(n) >= 1_000_000:
                return f'{n / 1_000_000:.1f}M'
            if abs(n) >= 1_000:
                return f'{n / 1_000:.0f}K'
            return str(int(n))

        text_labels = [_fmt(n) for n in notionals]

        fig = go.Figure(go.Bar(
            x=buckets,
            y=notionals,
            marker_color=_TEAL,
            text=text_labels,
            textposition='outside',
            textfont=dict(size=10, color=_DARK),
        ))

        fig.update_layout(
            title=dict(text='Notional by Maturity Bucket', font=dict(size=13, color=_DARK)),
            xaxis=dict(title='Tenor Bucket', gridcolor=_PALE),
            yaxis=dict(title='Notional', gridcolor=_PALE),
            showlegend=False,
            **PRINT_LAYOUT,
        )

        return _fig_to_png(fig, width, height)

    # ─────────────────────────────────────────────────────────────────────
    # 6. Greeks sensitivity chart (delta + vega vs spot)
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def greeks_sensitivity_chart(trade: dict, width: int = 800, height: int = 300) -> bytes:
        """
        Delta and Vega vs Spot level (60 %–140 % of spot_at_inception).

        Uses Black-Scholes for vanilla options; linear approximation otherwise.
        """
        product_type = trade.get('product_type', 'custom')
        underlyings  = trade.get('underlyings') or [{}]
        spot_0       = (underlyings[0].get('spot_at_inception') or
                        underlyings[0].get('current_spot') or 100.0)

        strike_pct = trade.get('strike_pct') or 100.0
        K          = spot_0 * strike_pct / 100.0
        T          = trade.get('tenor_years') or 1.0
        r          = 0.02     # risk-free rate assumption
        sigma      = 0.20     # vol assumption

        # Override sigma from pricing params if available
        pp = trade.get('pricing_params') or {}
        if pp.get('volatility'):
            sigma = float(pp['volatility'])
        elif pp.get('vol'):
            sigma = float(pp['vol'])

        # Current pricing vol
        cp = trade.get('current_pricing') or {}
        if cp.get('vol_used'):
            sigma = float(cp['vol_used'])

        spot_range = [spot_0 * (60 + i) / 100.0 for i in range(81)]  # 60 % to 140 %
        x_pct      = [(s / spot_0) * 100 for s in spot_range]

        is_call = product_type != 'vanilla_put'
        is_bs   = product_type in ('vanilla_call', 'vanilla_put')

        deltas = []
        vegas  = []
        eps    = spot_0 * 0.01  # 1 % bump

        for S in spot_range:
            if is_bs:
                p_up   = _bs_price(S + eps, K, T, r, sigma, is_call)
                p_down = _bs_price(S - eps, K, T, r, sigma, is_call)
                delta  = (p_up - p_down) / (2 * eps)
                vega   = _bs_vega(S, K, T, r, sigma)
            else:
                # Generic linear delta approximation: ramp from 0 to 1 around strike ±10 %
                strike = spot_0 * (trade.get('strike_pct') or 100.0) / 100.0
                width_  = strike * 0.20
                if S < strike - width_:
                    delta = 0.05
                elif S > strike + width_:
                    delta = 0.95
                else:
                    delta = 0.05 + 0.90 * (S - (strike - width_)) / (2 * width_)
                # Vega: bell-shaped approximation around the strike
                vega = 0.5 * math.exp(-0.5 * ((S - strike) / (strike * 0.15)) ** 2)

            deltas.append(round(delta, 6))
            vegas.append(round(vega, 4))

        fig = make_subplots(specs=[[{'secondary_y': True}]])

        fig.add_trace(
            go.Scatter(
                x=x_pct, y=deltas,
                name='Delta',
                line=dict(color=_BLUE, width=2),
                mode='lines',
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=x_pct, y=vegas,
                name='Vega',
                line=dict(color=_ORANGE, width=2, dash='dot'),
                mode='lines',
            ),
            secondary_y=True,
        )

        fig.update_xaxes(title_text='Spot (% of Inception)', ticksuffix='%', gridcolor=_PALE)
        fig.update_yaxes(title_text='Delta', secondary_y=False, gridcolor=_PALE)
        fig.update_yaxes(title_text='Vega', secondary_y=True, showgrid=False)

        product_name = trade.get('product_name', product_type)
        fig.update_layout(
            title=dict(text=f'Greeks vs Spot — {product_name}', font=dict(size=13, color=_DARK)),
            legend=dict(orientation='h', y=1.08, font=dict(size=9)),
            **PRINT_LAYOUT,
        )

        return _fig_to_png(fig, width, height)

    # ─────────────────────────────────────────────────────────────────────
    # 7. Historical spot price chart
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def spot_history_chart(
        ticker: str,
        period: str = '5y',
        barriers: list = None,
        width: int = 800,
        height: int = 300,
    ) -> bytes:
        """
        Fetch or generate a historical price chart for the given ticker.

        Tries yfinance first; falls back to a random-walk simulation.
        Overlays barrier levels as horizontal dashed lines.
        """
        import random

        dates_  = []
        prices_ = []

        # ── Try yfinance ──────────────────────────────────────────────
        try:
            import yfinance as yf
            hist = yf.Ticker(ticker).history(period=period)
            if not hist.empty:
                dates_  = [d.strftime('%Y-%m-%d') for d in hist.index]
                prices_ = list(hist['Close'].values)
        except Exception:
            pass

        # ── Fallback: mock random-walk ────────────────────────────────
        if not dates_:
            period_days_map = {
                '1y': 252, '2y': 504, '3y': 756, '5y': 1260, '10y': 2520,
            }
            n_days    = period_days_map.get(period, 1260)
            end_date  = datetime.now()
            start_date = end_date - timedelta(days=n_days)

            rng   = random.Random(hash(ticker) % (2**31))
            price = 100.0
            cur   = start_date

            while cur <= end_date:
                if cur.weekday() < 5:   # Mon–Fri
                    dates_.append(cur.strftime('%Y-%m-%d'))
                    price = max(1.0, price * (1 + rng.gauss(0.0002, 0.012)))
                    prices_.append(round(price, 4))
                cur += timedelta(days=1)

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dates_,
            y=prices_,
            mode='lines',
            name=ticker,
            line=dict(color=_NAVY, width=1.5),
        ))

        # Barrier overlays
        if barriers:
            for b in barriers:
                level = b.get('level_abs')
                if level is None:
                    continue
                bt    = str(b.get('barrier_type', '')).lower()
                color = _RED if ('knock' in bt or 'ki' in bt) else _ORANGE
                label = f'{bt.title()} {level:,.2f}'
                fig.add_hline(
                    y=level,
                    line_dash='dot',
                    line_color=color,
                    line_width=1.5,
                    annotation_text=label,
                    annotation_position='right',
                    annotation_font_size=8,
                )

        fig.update_layout(
            title=dict(text=f'{ticker} — Historical Price', font=dict(size=13, color=_DARK)),
            xaxis=dict(title='Date', gridcolor=_PALE, tickangle=-30),
            yaxis=dict(title='Price', gridcolor=_PALE),
            showlegend=False,
            **PRINT_LAYOUT,
        )

        return _fig_to_png(fig, width, height)

    # ─────────────────────────────────────────────────────────────────────
    # 8. Backtest chart
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def backtest_chart(backtest_results: dict, width: int = 800, height: int = 350) -> bytes:
        """
        Line chart comparing product returns vs underlying over a backtest period.

        backtest_results: {
            'dates':               list[str],
            'returns':             list[float],   # product cumulative return %
            'underlying_returns':  list[float],   # underlying cumulative return %
        }
        """
        dates      = backtest_results.get('dates', [])
        prod_ret   = backtest_results.get('returns', [])
        under_ret  = backtest_results.get('underlying_returns', [])

        # Fallback: empty chart with message
        if not dates:
            fig = go.Figure()
            fig.add_annotation(
                text='No backtest data available',
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color=_MEDIUM),
            )
            fig.update_layout(
                title=dict(text='Historical Backtest Analysis', font=dict(size=13, color=_DARK)),
                **PRINT_LAYOUT,
            )
            return _fig_to_png(fig, width, height)

        fig = go.Figure()

        # Filled area under product return
        if prod_ret:
            fig.add_trace(go.Scatter(
                x=dates, y=prod_ret,
                mode='lines',
                name='Product Return',
                line=dict(color=_EMERALD, width=2),
                fill='tozeroy',
                fillcolor='rgba(5,150,105,0.10)',
            ))

        # Underlying return line
        if under_ret:
            fig.add_trace(go.Scatter(
                x=dates, y=under_ret,
                mode='lines',
                name='Underlying Return',
                line=dict(color=_NAVY, width=1.5, dash='dot'),
            ))

        # Zero line
        fig.add_hline(y=0, line_color=_MEDIUM, line_width=0.8, line_dash='dash')

        fig.update_layout(
            title=dict(text='Historical Backtest Analysis', font=dict(size=13, color=_DARK)),
            xaxis=dict(title='Date', gridcolor=_PALE, tickangle=-30),
            yaxis=dict(title='Cumulative Return (%)', ticksuffix='%', gridcolor=_PALE),
            legend=dict(orientation='h', y=1.08, font=dict(size=9)),
            **PRINT_LAYOUT,
        )

        return _fig_to_png(fig, width, height)
