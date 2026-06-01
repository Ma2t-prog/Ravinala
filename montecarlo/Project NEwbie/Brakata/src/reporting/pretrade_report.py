"""
pretrade_report.py — Pre-Trade Analysis Report generator for Ravinala.

Produces an 8-page A4 PDF for pre-trade analysis — the document a
structurer shows to a client in a meeting before executing a trade.
"""

from datetime import datetime
from pathlib import Path
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, PageBreak, KeepTogether

from .pdf_engine import RavinalaColors, RavinalaStyles, RavinalaComponents, RavinalaDocument
from .charts_export import ChartExporter
from .templates import ReportingTemplates

PRODUCT_TYPE_LABELS = {
    'autocall': 'Autocall Note', 'phoenix': 'Phoenix Autocall', 'athena': 'Athena Autocall',
    'vanilla_call': 'Vanilla Call', 'vanilla_put': 'Vanilla Put',
    'european_digital': 'European Digital', 'barrier_option': 'Barrier Option',
    'reverse_convertible': 'Reverse Convertible', 'capital_protected_note': 'Capital Protected Note',
    'worst_of_basket': 'Worst-of Basket', 'best_of_basket': 'Best-of Basket',
    'himalaya': 'Himalaya', 'cliquet': 'Cliquet', 'variance_swap': 'Variance Swap',
    'range_accrual': 'Range Accrual', 'convertible_bond': 'Convertible Bond',
    'credit_linked_note': 'Credit Linked Note', 'custom': 'Bespoke Structure',
}


def _fmt_date(s):
    if not s: return '—'
    try: return datetime.strptime(s[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
    except: return s

def _fmt_num(v, decimals=2, suffix=''):
    if v is None: return 'N/A'
    try: return f'{float(v):,.{decimals}f}{suffix}'
    except: return 'N/A'

def _fmt_pct(v, decimals=2):
    if v is None: return 'N/A'
    try: return f'{float(v):.{decimals}f}%'
    except: return 'N/A'

def _fmt_ccy(v, currency=''):
    if v is None: return 'N/A'
    try: return f'{currency} {float(v):,.0f}'.strip()
    except: return 'N/A'


class PreTradeReportGenerator:
    """
    Generates a pre-trade analysis report — analytical document
    produced before executing a trade, used in client meetings.
    """

    OUTPUT_DIR = 'data/reports'

    def generate(
        self,
        trade: dict,
        output_path: str = None,
        include_backtest: bool = False,
        include_comparison: bool = True,
        comparable_trades: list = None,
    ) -> str:
        if output_path is None:
            ref = trade.get('internal_ref') or trade.get('trade_id', 'trade')
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            Path(self.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
            output_path = str(Path(self.OUTPUT_DIR) / f'pretrade_{ref}_{ts}.pdf')

        doc = RavinalaDocument(
            output_path=output_path,
            title=f"Pre-Trade Analysis — {trade.get('product_name', 'Structured Product')}",
            author='Ravinala Structuring',
            landscape_mode=False,
            watermark_text='INDICATIVE ONLY',
        )

        St = RavinalaStyles.get_styles()
        elems = []

        elems += self._page_executive_summary(trade, St)
        elems.append(PageBreak())
        elems += self._page_market_context(trade, St)
        elems.append(PageBreak())
        elems += self._page_product_structure(trade, St)
        elems.append(PageBreak())
        elems += self._page_scenario_analysis(trade, St)
        elems.append(PageBreak())
        elems += self._page_sensitivity(trade, St)
        elems.append(PageBreak())
        elems += self._page_risk_metrics(trade, St)
        elems.append(PageBreak())
        elems += self._page_pricing_details(trade, St)
        if include_comparison:
            elems.append(PageBreak())
            elems += self._page_comparison(trade, St)
        elems.append(PageBreak())
        elems += self._page_disclaimers(trade, St)

        return doc.build(elems)

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 1 — EXECUTIVE SUMMARY
    # ─────────────────────────────────────────────────────────────────────

    def _page_executive_summary(self, trade: dict, St: dict) -> list:
        elems = []
        product_name = trade.get('product_name') or PRODUCT_TYPE_LABELS.get(
            trade.get('product_type', 'custom'), 'Structured Product')
        today = datetime.now().strftime('%d %B %Y')
        ref = trade.get('internal_ref') or '—'

        elems += RavinalaComponents.header_banner(
            title='PRE-TRADE ANALYSIS',
            subtitle=product_name,
            date=today, ref=ref, confidential=True,
        )

        ccy = trade.get('currency', 'EUR')
        notional = trade.get('notional', 0)
        pr = trade.get('current_pricing') or trade.get('initial_pricing') or {}
        tenor = trade.get('tenor_years', 0)
        coupon = trade.get('coupon') or {}
        coupon_rate = coupon.get('rate_pct')
        barriers = trade.get('barriers', [])
        ki = next((b.get('level_pct') for b in barriers if b.get('barrier_type') == 'knock_in'), None)

        kpis = [
            {'label': 'Indicative Price', 'value': _fmt_pct(pr.get('price')), 'color': None},
            {'label': 'Notional', 'value': _fmt_ccy(notional, ccy), 'color': None},
            {'label': 'Coupon / Return', 'value': _fmt_pct(coupon_rate) if coupon_rate else 'N/A', 'color': 'green' if coupon_rate else None},
            {'label': 'Tenor', 'value': f'{tenor:.1f}Y', 'color': None},
        ]
        elems.append(RavinalaComponents.kpi_row(kpis, columns=4))
        elems.append(Spacer(0, 10))

        elems += RavinalaComponents.section_header('Product Summary', '1')
        desc = ReportingTemplates.generate_product_description(trade)
        elems.append(Paragraph(desc, St['body']))
        elems.append(Spacer(0, 10))

        elems += RavinalaComponents.section_header('Key Features', '2')
        features = self._key_features(trade)
        feat_data = {f['label']: f['value'] for f in features}
        elems += RavinalaComponents.key_value_table(feat_data, columns=2)

        return elems

    def _key_features(self, trade: dict) -> list:
        barriers = trade.get('barriers', [])
        coupon = trade.get('coupon') or {}
        ki = next((b for b in barriers if b.get('barrier_type') == 'knock_in'), {})
        ac = next((b for b in barriers if b.get('barrier_type') == 'autocall'), {})
        cb = next((b for b in barriers if b.get('barrier_type') == 'coupon'), {})
        ul = trade.get('underlyings', [{}])[0]

        features = [
            {'label': 'Product Type', 'value': PRODUCT_TYPE_LABELS.get(trade.get('product_type', 'custom'), 'Custom')},
            {'label': 'Underlying', 'value': ul.get('ticker', 'N/A')},
            {'label': 'Tenor', 'value': f"{trade.get('tenor_years', 0):.1f} years"},
            {'label': 'Currency', 'value': trade.get('currency', 'EUR')},
            {'label': 'Direction', 'value': trade.get('direction', '').upper()},
        ]
        if coupon.get('rate_pct'):
            features.append({'label': 'Coupon Rate', 'value': _fmt_pct(coupon.get('rate_pct'))})
        if ac.get('level_pct'):
            features.append({'label': 'Autocall Level', 'value': _fmt_pct(ac.get('level_pct'))})
        if ki.get('level_pct'):
            features.append({'label': 'Knock-In Barrier', 'value': _fmt_pct(ki.get('level_pct'))})
        cap = trade.get('capital_protection_pct')
        if cap is not None:
            features.append({'label': 'Capital Protection', 'value': _fmt_pct(cap)})
        return features

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 2 — MARKET CONTEXT
    # ─────────────────────────────────────────────────────────────────────

    def _page_market_context(self, trade: dict, St: dict) -> list:
        elems = []
        elems += RavinalaComponents.section_header('Market Context', '1')

        uls = trade.get('underlyings', [])
        if uls:
            ul = uls[0]
            ticker = ul.get('ticker', 'INDEX')
            spot = ul.get('current_spot') or ul.get('spot_at_inception', 0)
            spot0 = ul.get('spot_at_inception', spot)
            perf_since = (spot - spot0) / spot0 * 100 if spot0 else 0

            pr = trade.get('current_pricing') or {}
            vol = (pr.get('vol_used') or 0) * 100
            rate = (pr.get('rate_used') or 0) * 100

            mkt_data = {
                'Underlying':       f"{ul.get('name', '')} ({ticker})",
                'Current Spot':     _fmt_num(spot, 2),
                'Spot at Inception':_fmt_num(spot0, 2),
                'Perf. Since Inception': _fmt_pct(perf_since, 2),
                'Implied Volatility':    _fmt_pct(vol, 2),
                'Risk-Free Rate':        _fmt_pct(rate, 2),
                'Dividend Yield':        _fmt_pct((trade.get('inception_div_yield') or 0) * 100, 2),
                'Currency':              ul.get('currency', 'EUR'),
            }
            elems += RavinalaComponents.key_value_table(mkt_data, columns=2)
            elems.append(Spacer(0, 8))

            # Spot history chart
            try:
                barriers_for_chart = [
                    {'level_abs': b.get('level_abs', 0), 'barrier_type': b.get('barrier_type', '')}
                    for b in trade.get('barriers', [])
                ]
                chart_bytes = ChartExporter.spot_history_chart(
                    ticker, period='3y', barriers=barriers_for_chart)
                elems += RavinalaComponents.chart_image(
                    chart_bytes, width=15*cm, height=6*cm,
                    caption=f'{ticker} — 3-Year Price History with Barrier Levels')
            except Exception:
                pass

        elems += RavinalaComponents.section_header('Investment Rationale', '2')
        pt = trade.get('product_type', 'custom')
        rationale = self._investment_rationale(trade)
        elems.append(Paragraph(rationale, St['body']))

        return elems

    def _investment_rationale(self, trade: dict) -> str:
        pt = trade.get('product_type', 'custom')
        ul = trade.get('underlyings', [{}])[0]
        ticker = ul.get('ticker', 'the underlying')
        coupon = trade.get('coupon') or {}
        rate = coupon.get('rate_pct', '')

        rationales = {
            'autocall': (
                f"Current market conditions present an attractive entry point for a structured solution on {ticker}. "
                f"Implied volatility levels allow structuring an enhanced yield of {_fmt_pct(rate)} per annum "
                f"with conditional capital protection. The autocallable structure benefits from the current "
                f"interest rate environment and the mean-reversion tendency of equity indices. "
                f"The product monetizes the implied volatility premium over realized volatility, "
                f"providing significant carry for the investor relative to risk-free rates."
            ),
            'vanilla_call': (
                f"The current volatility environment offers an attractive entry point for directional exposure "
                f"to {ticker} via a vanilla call option. Implied volatility at current levels represents "
                f"fair value relative to historical realized volatility, limiting the cost of the option. "
                f"The structure provides unlimited upside participation with a defined maximum loss."
            ),
            'capital_protected_note': (
                f"For investors seeking equity market exposure with downside protection, this capital-protected "
                f"note on {ticker} offers an optimal risk/reward profile in the current environment. "
                f"The zero-coupon bond floor combined with participation in the equity upside provides "
                f"the benefit of equity returns with bond-like downside protection."
            ),
        }
        return rationales.get(pt, (
            f"This bespoke structure on {ticker} is designed to meet specific investment objectives, "
            f"combining targeted risk/return characteristics with appropriate capital protection. "
            f"Current market conditions are favorable for structuring this type of product."
        ))

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 3 — PRODUCT STRUCTURE
    # ─────────────────────────────────────────────────────────────────────

    def _page_product_structure(self, trade: dict, St: dict) -> list:
        elems = []
        elems += RavinalaComponents.section_header('Product Structure & Mechanism', '1')

        desc = ReportingTemplates.generate_product_description(trade)
        elems.append(Paragraph(desc, St['body']))
        elems.append(Spacer(0, 8))

        # Payoff diagram
        try:
            chart_bytes = ChartExporter.payoff_chart(trade)
            elems += RavinalaComponents.chart_image(
                chart_bytes, width=15*cm, height=7*cm,
                caption='Payoff diagram at maturity — illustrative, based on indicative parameters.')
        except Exception:
            pass

        # Key terms table
        elems += RavinalaComponents.section_header('Key Terms', '2')
        barriers = trade.get('barriers', [])
        coupon = trade.get('coupon') or {}
        terms = {
            'Notional':         _fmt_ccy(trade.get('notional'), trade.get('currency', 'EUR')),
            'Currency':         trade.get('currency', 'EUR'),
            'Inception':        _fmt_date(trade.get('inception_date', '')),
            'Maturity':         _fmt_date(trade.get('maturity_date', '')),
            'Tenor':            f"{trade.get('tenor_years', 0):.1f} years",
            'Strike':           _fmt_pct(trade.get('strike_pct')),
        }
        for b in barriers:
            btype = b.get('barrier_type', '').replace('_', ' ').title()
            terms[f'{btype} Barrier'] = _fmt_pct(b.get('level_pct'))
        if coupon.get('rate_pct'):
            terms['Coupon Rate']    = _fmt_pct(coupon.get('rate_pct'))
            terms['Coupon Freq.']   = coupon.get('frequency', 'annual').replace('_', ' ').title()
            terms['Memory Effect']  = 'Yes' if coupon.get('is_memory') else 'No'
        elems += RavinalaComponents.key_value_table(terms, columns=2)

        return elems

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 4 — SCENARIO ANALYSIS
    # ─────────────────────────────────────────────────────────────────────

    def _page_scenario_analysis(self, trade: dict, St: dict) -> list:
        elems = []
        elems += RavinalaComponents.section_header('Scenario Analysis', '1')
        elems.append(Paragraph(
            'The following table illustrates the potential outcome for the investor '
            'under different market scenarios. All scenarios are hypothetical and for '
            'illustrative purposes only.', St['body']))
        elems.append(Spacer(0, 6))

        scenarios = self._build_scenarios(trade)
        if scenarios:
            headers = ['Scenario', 'Spot Level', 'Underlying Perf.', 'Investor Return', 'Key Event', 'EUR Impact']
            rows = []
            notional = trade.get('notional', 1_000_000)
            ccy = trade.get('currency', 'EUR')
            for s in scenarios:
                ret = s.get('return_pct', 0) or 0
                eur_impact = notional * ret / 100
                rows.append([
                    s.get('name', '—'),
                    _fmt_num(s.get('spot_final'), 2) + f" ({_fmt_pct(s.get('spot_pct'), 0)})",
                    _fmt_pct(s.get('underlying_perf'), 1),
                    _fmt_pct(ret, 1),
                    s.get('event', '—'),
                    _fmt_ccy(eur_impact, ccy),
                ])
            elems += RavinalaComponents.data_table(
                headers, rows,
                col_alignments=['L', 'R', 'R', 'R', 'L', 'R'],
                pnl_column=3,
            )
            elems.append(Spacer(0, 8))

            # Scenario comparison chart
            try:
                chart_bytes = ChartExporter.scenario_comparison_chart(scenarios)
                elems += RavinalaComponents.chart_image(
                    chart_bytes, width=15*cm, height=6*cm,
                    caption='Investor return (% of notional) across market scenarios.')
            except Exception:
                pass

        return elems

    def _build_scenarios(self, trade: dict) -> list:
        uls = trade.get('underlyings', [])
        spot_init = uls[0].get('spot_at_inception', 100) if uls else 100
        pt = trade.get('product_type', 'custom')
        barriers = trade.get('barriers', [])
        coupon = trade.get('coupon') or {}
        coupon_rate = float(coupon.get('rate_pct', 0) or 0)
        tenor = float(trade.get('tenor_years', 1) or 1)
        ki = next((b.get('level_pct') for b in barriers if b.get('barrier_type') == 'knock_in'), None)
        ac = next((b.get('level_pct', 100) for b in barriers if b.get('barrier_type') == 'autocall'), None)
        cb = next((b.get('level_pct', 70) for b in barriers if b.get('barrier_type') == 'coupon'), None)
        strike = float(trade.get('strike_pct', 100) or 100)
        cap_p = float(trade.get('capital_protection_pct', 100) or 100)
        part = float(trade.get('participation_rate', 100) or 100)

        scenario_defs = [
            ('Strong Rally (+40%)', 140), ('Bull (+20%)', 120), ('Mild Bull (+10%)', 110),
            ('Flat (0%)', 100), ('Mild Bear (-10%)', 90), ('Bear (-25%)', 75),
            ('Crash (-45%)', 55),
        ]
        if ki: scenario_defs += [(f'Just Above KI ({ki+3:.0f}%)', ki+3), (f'Just Below KI ({ki-5:.0f}%)', ki-5)]

        scenarios = []
        for name, spot_pct in sorted(scenario_defs, key=lambda x: -x[1]):
            spot_final = spot_init * spot_pct / 100
            underlying_perf = spot_pct - 100

            if pt in ('autocall', 'phoenix', 'athena'):
                if ac and spot_pct >= ac:
                    ret = coupon_rate * 1; event = f'Autocalled Y1: +{coupon_rate:.1f}%'
                elif cb and spot_pct >= cb:
                    ret = coupon_rate * tenor; event = f'Held to mat. — coupons paid: +{ret:.1f}%'
                elif ki and spot_pct < ki:
                    ret = underlying_perf; event = 'KI triggered — capital at risk'
                else:
                    ret = 0; event = 'Held to mat. — coupons missed'
            elif pt == 'vanilla_call':
                ret = max(0, spot_pct - strike) - (trade.get('entry_price') or 2)
                event = 'Exercised' if spot_pct > strike else 'Expires worthless'
            elif pt == 'vanilla_put':
                ret = max(0, strike - spot_pct) - (trade.get('entry_price') or 2)
                event = 'Exercised' if spot_pct < strike else 'Expires worthless'
            elif pt == 'reverse_convertible':
                b_pct = barriers[0].get('level_pct', 70) if barriers else 70
                if spot_pct >= b_pct:
                    ret = coupon_rate * tenor; event = 'Capital protected + coupons'
                else:
                    ret = underlying_perf + coupon_rate * tenor; event = 'Capital at risk'
            elif pt == 'capital_protected_note':
                upside = max(0, underlying_perf) * part / 100
                if trade.get('cap_pct'): upside = min(upside, float(trade.get('cap_pct')))
                ret = cap_p - 100 + upside; event = 'Maturity redemption'
            else:
                ret = underlying_perf * 0.5; event = 'Maturity'

            scenarios.append({
                'name': name, 'spot_pct': spot_pct, 'spot_final': spot_final,
                'underlying_perf': underlying_perf, 'return_pct': ret, 'event': event,
            })

        return scenarios[:9]

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 5 — SENSITIVITY ANALYSIS
    # ─────────────────────────────────────────────────────────────────────

    def _page_sensitivity(self, trade: dict, St: dict) -> list:
        elems = []
        elems += RavinalaComponents.section_header('Sensitivity Analysis', '1')

        pr = trade.get('current_pricing') or {}
        greeks = {
            'delta': pr.get('delta'), 'gamma': pr.get('gamma'),
            'vega': pr.get('vega'), 'theta': pr.get('theta'),
            'rho': pr.get('rho'), 'vanna': pr.get('vanna'), 'volga': pr.get('volga'),
        }
        if any(v is not None for v in greeks.values()):
            elems += RavinalaComponents.section_header('Greeks at Current Level', '1.1')
            elems.append(RavinalaComponents.greeks_table(greeks))
            elems.append(Spacer(0, 8))

        # Greeks sensitivity chart
        try:
            chart_bytes = ChartExporter.greeks_sensitivity_chart(trade)
            elems += RavinalaComponents.chart_image(
                chart_bytes, width=15*cm, height=6*cm,
                caption='Delta and Vega as a function of the underlying spot level.')
        except Exception:
            pass

        # Spot sensitivity grid
        elems += RavinalaComponents.section_header('Price Sensitivity to Spot', '1.2')
        uls = trade.get('underlyings', [])
        spot0 = uls[0].get('spot_at_inception', 100) if uls else 100
        spot_c = uls[0].get('current_spot') or spot0 if uls else spot0
        base_price = pr.get('price') or 100
        delta_val = pr.get('delta') or 0

        headers = ['Spot Move', 'Spot Level', 'Approx. Price', 'Approx. MTM', 'Approx. P&L']
        rows = []
        notional = trade.get('notional', 1_000_000)
        entry_p = trade.get('entry_price') or base_price
        ccy = trade.get('currency', 'EUR')
        for move in [-30, -20, -10, -5, 0, +5, +10, +20, +30]:
            spot_m = spot_c * (1 + move / 100)
            dprice = delta_val * move  # simplified: delta * %move
            approx_price = max(0, base_price + dprice)
            approx_mtm = approx_price / 100 * notional
            approx_pnl = (approx_price - entry_p) / 100 * notional
            rows.append([
                f'{move:+.0f}%',
                _fmt_num(spot_m, 2),
                _fmt_pct(approx_price, 2),
                _fmt_ccy(approx_mtm, ccy),
                _fmt_ccy(approx_pnl, ccy),
            ])
        elems += RavinalaComponents.data_table(
            headers, rows,
            col_alignments=['C', 'R', 'R', 'R', 'R'],
            highlight_row=4,  # the 0% row
            pnl_column=4,
        )
        return elems

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 6 — RISK METRICS
    # ─────────────────────────────────────────────────────────────────────

    def _page_risk_metrics(self, trade: dict, St: dict) -> list:
        elems = []
        elems += RavinalaComponents.section_header('Risk Metrics', '1')

        notional = trade.get('notional', 1_000_000)
        ccy = trade.get('currency', 'EUR')
        pr = trade.get('current_pricing') or {}

        risk_data = {
            'VaR 95% (1 Day)':   _fmt_ccy(trade.get('var_95_1d'), ccy),
            'VaR 99% (1 Day)':   _fmt_ccy(trade.get('var_99_1d'), ccy),
            'Maximum Loss':      _fmt_ccy(trade.get('max_loss'), ccy),
            'Maximum Loss (%)':  _fmt_pct(trade.get('max_loss', 0) / notional * 100 if notional else None),
            'Delta':             _fmt_num(pr.get('delta'), 4),
            'Vega':              _fmt_num(pr.get('vega'), 4),
        }
        elems += RavinalaComponents.key_value_table(risk_data, columns=2)
        elems.append(Spacer(0, 10))

        elems += RavinalaComponents.section_header('Stress Scenarios', '2')
        elems.append(Paragraph(
            'Estimated impact on the portfolio under historical stress scenarios. '
            'These estimates are based on simplified delta/vega approximations.', St['body_small']))
        elems.append(Spacer(0, 6))

        delta = pr.get('delta') or 0
        vega  = pr.get('vega') or 0

        stress_defs = [
            ('2008 GFC',          'Global Financial Crisis',       -57, +200, -100),
            ('2020 COVID',        'COVID-19 Market Crash',         -34, +150,  -75),
            ('2022 Rate Shock',   'Rapid Interest Rate Increase',  -15,  +30, +200),
            ('Vol Spike +50%',    'Volatility Spike (VIX → 60)',    -5,  +50,    0),
            ('Geopolitical Shock','Geopolitical Risk Event',        -12,  +80,  -20),
        ]
        headers = ['Scenario', 'Description', 'Equity', 'Vol', 'Rates', 'Est. P&L Impact']
        rows = []
        for name, desc, eq_move, vol_move, rate_move in stress_defs:
            est_pnl = delta * eq_move * notional / 100 + vega * vol_move / 100 * notional / 100
            rows.append([
                name, desc,
                f'{eq_move:+.0f}%', f'{vol_move:+.0f}%', f'{rate_move:+.0f}bp',
                _fmt_ccy(est_pnl, ccy),
            ])
        elems += RavinalaComponents.data_table(
            headers, rows,
            col_alignments=['L', 'L', 'C', 'C', 'C', 'R'],
            pnl_column=5,
        )
        return elems

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 7 — PRICING DETAILS
    # ─────────────────────────────────────────────────────────────────────

    def _page_pricing_details(self, trade: dict, St: dict) -> list:
        elems = []
        pr = trade.get('current_pricing') or trade.get('initial_pricing') or {}
        ccy = trade.get('currency', 'EUR')

        elems += RavinalaComponents.section_header('Indicative Pricing', '1')
        pricing_data = {
            'Indicative Price':  _fmt_pct(pr.get('price'), 4),
            'Model':             (pr.get('model') or '—').replace('_', ' ').title(),
            'Notional Value':    _fmt_ccy(pr.get('notional_value'), ccy),
            'MC Paths':          f"{int(pr.get('mc_paths', 0)):,}" if pr.get('mc_paths') else 'N/A',
            'Std Error':         _fmt_pct(pr.get('mc_std_error'), 4) if pr.get('mc_std_error') else 'N/A',
            'Price Date':        (pr.get('timestamp') or '—')[:16],
        }
        elems += RavinalaComponents.key_value_table(pricing_data, columns=2)
        elems.append(Spacer(0, 8))

        elems += RavinalaComponents.section_header('Market Data Used', '2')
        mkt_data = {
            'Spot Level':       _fmt_num(pr.get('spot_used'), 2),
            'Implied Vol':      _fmt_pct((pr.get('vol_used') or 0) * 100, 2),
            'Risk-Free Rate':   _fmt_pct((pr.get('rate_used') or 0) * 100, 2),
            'Dividend Yield':   _fmt_pct((trade.get('inception_div_yield') or 0) * 100, 2),
        }
        elems += RavinalaComponents.key_value_table(mkt_data, columns=2)
        elems.append(Spacer(0, 8))

        greeks = {
            'delta': pr.get('delta'), 'gamma': pr.get('gamma'),
            'vega':  pr.get('vega'), 'theta': pr.get('theta'),
            'rho':   pr.get('rho'),
        }
        if any(v is not None for v in greeks.values()):
            elems += RavinalaComponents.section_header('Greeks at Indicative Price', '3')
            elems.append(RavinalaComponents.greeks_table(greeks))

        return elems

    # ─────────────────────────────────────────────────────────────────────
    # PAGE 8 — COMPARISON
    # ─────────────────────────────────────────────────────────────────────

    def _page_comparison(self, trade: dict, St: dict) -> list:
        elems = []
        elems += RavinalaComponents.section_header('Comparison with Alternatives', '1')
        elems.append(Paragraph(
            'The following comparison illustrates the risk/return profile of this product '
            'relative to commonly available investment alternatives.', St['body']))
        elems.append(Spacer(0, 6))

        coupon = trade.get('coupon') or {}
        rate = coupon.get('rate_pct') or 5
        tenor = trade.get('tenor_years', 1)
        barriers = trade.get('barriers', [])
        ki = next((b.get('level_pct') for b in barriers if b.get('barrier_type') == 'knock_in'), None)
        cap_p = trade.get('capital_protection_pct', 0) or 0
        product_name = PRODUCT_TYPE_LABELS.get(trade.get('product_type', 'custom'), 'Product')

        headers = ['Feature', product_name, 'Term Deposit', 'Equity ETF (Direct)']
        rows = [
            ['Expected Return', f'~{_fmt_pct(rate)} p.a.', '~3.5% p.a.', 'Market-linked'],
            ['Capital Protection', f'{_fmt_pct(cap_p)}' if cap_p else f'Partial (KI {_fmt_pct(ki)})' if ki else 'None', '100%', 'None'],
            ['Upside Potential', f'Coupon + redemption' if rate else 'Participation', 'None', 'Unlimited'],
            ['Liquidity', 'Low (OTC)', 'Low (locked)', 'High (listed)'],
            ['Key Risk', 'KI barrier breach' if ki else 'Credit / Market', 'Inflation / Rate', 'Full downside'],
            ['Tenor', f'{tenor:.0f} years', '1–5 years', 'Indefinite'],
            ['Min. Investment', 'EUR 100,000+', 'EUR 1,000+', 'EUR 100+'],
        ]
        elems += RavinalaComponents.data_table(
            headers, rows,
            col_alignments=['L', 'C', 'C', 'C'],
        )

        return elems

    # ─────────────────────────────────────────────────────────────────────
    # PAGE — DISCLAIMERS
    # ─────────────────────────────────────────────────────────────────────

    def _page_disclaimers(self, trade: dict, St: dict) -> list:
        elems = []
        elems += RavinalaComponents.section_header('Important Information & Disclaimers', '1')
        elems.append(Paragraph(ReportingTemplates.risk_warning_structured_products(), St['body_small']))
        elems.append(Spacer(0, 4))
        barriers = trade.get('barriers', [])
        if any(b.get('barrier_type') == 'knock_in' for b in barriers):
            elems.append(Paragraph(ReportingTemplates.risk_warning_barrier_products(), St['body_small']))
            elems.append(Spacer(0, 4))
        cap_p = trade.get('capital_protection_pct', 100) or 100
        if cap_p < 100:
            elems.append(Paragraph(ReportingTemplates.risk_warning_capital_at_risk(), St['body_small']))
            elems.append(Spacer(0, 4))
        elems.append(Paragraph(ReportingTemplates.model_limitations(), St['body_small']))
        elems.append(Spacer(0, 4))
        elems.append(Paragraph(ReportingTemplates.mifid_notice(), St['disclaimer']))
        elems.append(Spacer(0, 6))
        elems += RavinalaComponents.disclaimer_block()
        elems.append(Spacer(0, 6))
        elems.append(Paragraph(ReportingTemplates.contact_block(), St['body_small']))
        return elems
