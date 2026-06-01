"""
term_sheet.py — Professional term sheet generator for Ravinala.

Produces a 5-6 page A4 PDF term sheet suitable for sending to clients,
risk management, and middle office. Covers product summary, structure
details, payoff diagram, scenario analysis, Greeks, schedule, and disclaimers.
"""

from datetime import datetime, date, timedelta
from pathlib import Path
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, PageBreak, KeepTogether, HRFlowable

from .pdf_engine import (
    RavinalaColors, RavinalaStyles, RavinalaComponents, RavinalaDocument
)
from .charts_export import ChartExporter
from .templates import ReportingTemplates

# Product type labels (mirror tradebook_models)
PRODUCT_TYPE_LABELS = {
    'vanilla_call': 'Vanilla Call Option',
    'vanilla_put': 'Vanilla Put Option',
    'european_digital': 'European Digital Option',
    'barrier_option': 'Barrier Option',
    'autocall': 'Autocall Note',
    'phoenix': 'Phoenix Autocall Note',
    'athena': 'Athena Autocall Note',
    'reverse_convertible': 'Reverse Convertible',
    'capital_protected_note': 'Capital Protected Note',
    'worst_of_basket': 'Worst-of Basket Note',
    'best_of_basket': 'Best-of Basket Note',
    'himalaya': 'Himalaya Option',
    'cliquet': 'Cliquet Option',
    'variance_swap': 'Variance Swap',
    'range_accrual': 'Range Accrual Note',
    'convertible_bond': 'Convertible Bond',
    'credit_linked_note': 'Credit Linked Note',
    'custom': 'Bespoke Structure',
}

STATUS_LABELS = {
    'draft': 'Draft',
    'live': 'Live',
    'matured': 'Matured',
    'knocked': 'Knocked',
    'cancelled': 'Cancelled',
    'expired': 'Expired',
}


def _fmt_date(s: str) -> str:
    """Convert YYYY-MM-DD to DD/MM/YYYY."""
    if not s:
        return '—'
    try:
        return datetime.strptime(s[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
    except Exception:
        return s


def _fmt_num(v, decimals: int = 2, suffix: str = '') -> str:
    if v is None:
        return 'N/A'
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 'N/A'
    formatted = f'{v:,.{decimals}f}'
    return f'{formatted}{suffix}'


def _fmt_pct(v, decimals: int = 2) -> str:
    if v is None:
        return 'N/A'
    try:
        return f'{float(v):.{decimals}f}%'
    except (TypeError, ValueError):
        return 'N/A'


def _fmt_ccy(v, currency: str = '') -> str:
    if v is None:
        return 'N/A'
    try:
        return f'{currency} {float(v):,.0f}'.strip()
    except (TypeError, ValueError):
        return 'N/A'


class TermSheetGenerator:
    """
    Generates a professional term sheet PDF for a single trade.

    Usage:
        gen = TermSheetGenerator()
        path = gen.generate(trade_dict, output_path='/tmp/ts.pdf', mode='final')
    """

    OUTPUT_DIR = 'data/reports'

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate(
        self,
        trade: dict,
        output_path: str = None,
        mode: str = 'final',
        include_charts: bool = True,
        include_greeks: bool = True,
        include_scenarios: bool = True,
        language: str = 'en',
    ) -> str:
        """
        Generate the full term sheet PDF.

        Args:
            trade:            Trade dict (from Trade.to_dict()).
            output_path:      Destination path. Auto-generated if None.
            mode:             'final' | 'draft' | 'indicative' | 'internal'
            include_charts:   Embed payoff diagram and sensitivity charts.
            include_greeks:   Include Greeks page.
            include_scenarios: Include scenario analysis table.
            language:         'en' (French not yet implemented).

        Returns:
            Absolute path to the generated PDF.
        """
        # ── Output path ──────────────────────────────────────────────
        if output_path is None:
            ref = trade.get('internal_ref') or trade.get('trade_id', 'trade')
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            Path(self.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
            output_path = str(Path(self.OUTPUT_DIR) / f'termsheet_{ref}_{ts}.pdf')

        # ── Watermark ────────────────────────────────────────────────
        watermark_map = {
            'draft':      'DRAFT',
            'indicative': 'INDICATIVE ONLY',
            'internal':   'INTERNAL USE ONLY',
            'final':      None,
        }
        watermark = watermark_map.get(mode)

        # ── Build document ───────────────────────────────────────────
        doc = RavinalaDocument(
            output_path=output_path,
            title=f"Term Sheet — {trade.get('product_name', 'Structured Product')}",
            author='Ravinala Structuring',
            landscape_mode=False,
            watermark_text=watermark,
        )

        elements = []
        St = RavinalaStyles.get_styles()
        C = RavinalaColors

        # ──────────────────────────────────────────────────────────────
        # PAGE 1: COVER & SUMMARY
        # ──────────────────────────────────────────────────────────────
        elements += self._page_cover(trade, mode, St)

        # ──────────────────────────────────────────────────────────────
        # PAGE 2: STRUCTURE DETAILS
        # ──────────────────────────────────────────────────────────────
        elements.append(PageBreak())
        elements += self._page_structure(trade, St)

        # ──────────────────────────────────────────────────────────────
        # PAGE 3: PAYOFF & SCENARIOS
        # ──────────────────────────────────────────────────────────────
        if include_charts or include_scenarios:
            elements.append(PageBreak())
            elements += self._page_payoff_scenarios(trade, include_charts, include_scenarios, St)

        # ──────────────────────────────────────────────────────────────
        # PAGE 4: PRICING & GREEKS
        # ──────────────────────────────────────────────────────────────
        if include_greeks and trade.get('current_pricing'):
            elements.append(PageBreak())
            elements += self._page_pricing_greeks(trade, include_charts, St)

        # ──────────────────────────────────────────────────────────────
        # PAGE 5: SCHEDULE
        # ──────────────────────────────────────────────────────────────
        elements.append(PageBreak())
        elements += self._page_schedule(trade, St)

        # ──────────────────────────────────────────────────────────────
        # PAGE 6: DISCLAIMERS
        # ──────────────────────────────────────────────────────────────
        elements.append(PageBreak())
        elements += self._page_disclaimers(trade, mode, St)

        return doc.build(elements)

    # ------------------------------------------------------------------
    # PAGE 1 — COVER
    # ------------------------------------------------------------------

    def _page_cover(self, trade: dict, mode: str, St: dict) -> list:
        elems = []
        C = RavinalaColors

        product_name = trade.get('product_name') or PRODUCT_TYPE_LABELS.get(
            trade.get('product_type', 'custom'), 'Structured Product'
        )
        ref = trade.get('internal_ref') or trade.get('trade_id', '—')
        today_str = datetime.now().strftime('%d %B %Y')

        # ── Banner ───────────────────────────────────────────────────
        elems += RavinalaComponents.header_banner(
            title='TERM SHEET',
            subtitle=product_name,
            date=today_str,
            ref=ref,
            confidential=(mode != 'internal'),
        )

        # ── Executive Summary KPIs ────────────────────────────────────
        elems += RavinalaComponents.section_header('Executive Summary', '1')

        ccy = trade.get('currency', 'EUR')
        notional = trade.get('notional', 0)
        pr = trade.get('current_pricing') or trade.get('initial_pricing') or {}
        price = pr.get('price')
        mtm = pr.get('notional_value')
        tenor = trade.get('tenor_years', 0)

        def _color_pnl(v):
            if v is None:
                return None
            return 'green' if float(v) >= 0 else 'red'

        total_pnl = trade.get('total_pnl')
        kpis = [
            {'label': 'Notional', 'value': _fmt_ccy(notional, ccy), 'color': None},
            {'label': 'Price (% Nominal)', 'value': _fmt_pct(price), 'color': None},
            {'label': 'MTM Value', 'value': _fmt_ccy(mtm, ccy), 'color': None},
            {'label': 'Tenor', 'value': f'{tenor:.1f}Y', 'color': None},
        ]
        elems.append(RavinalaComponents.kpi_row(kpis, columns=4))
        elems.append(Spacer(0, 10))

        # ── Product Overview ─────────────────────────────────────────
        elems += RavinalaComponents.section_header('Product Overview', '2')
        overview_data = {
            'Product Type':    PRODUCT_TYPE_LABELS.get(trade.get('product_type', 'custom'), 'Custom'),
            'Direction':       trade.get('direction', '—').upper(),
            'Currency':        ccy,
            'Trade Date':      _fmt_date(trade.get('trade_date', '')),
            'Inception Date':  _fmt_date(trade.get('inception_date', '')),
            'Maturity Date':   _fmt_date(trade.get('maturity_date', '')),
            'Settlement Date': _fmt_date(trade.get('settlement_date', '')),
            'Status':          STATUS_LABELS.get(trade.get('status', 'draft'), trade.get('status', '—')),
            'Counterparty':    trade.get('counterparty', '—') or '—',
            'Sales':           trade.get('sales_person', '—') or '—',
            'Desk':            trade.get('desk', '—') or '—',
            'Pricing Model':   trade.get('pricing_model', '—').replace('_', ' ').title(),
        }
        elems += RavinalaComponents.key_value_table(overview_data, columns=2)
        elems.append(Spacer(0, 10))

        # ── Underlying(s) table ──────────────────────────────────────
        underlyings = trade.get('underlyings', [])
        if underlyings:
            elems += RavinalaComponents.section_header('Underlying(s)', '3')
            headers = ['Ticker', 'Name', 'Asset Class', 'Spot @ Inception', 'Current Spot', 'Currency', 'Weight']
            rows = []
            for u in underlyings:
                s0 = u.get('spot_at_inception', 0)
                sc = u.get('current_spot') or s0
                rows.append([
                    u.get('ticker', '—'),
                    u.get('name', '—'),
                    u.get('asset_class', '—').replace('_', ' ').title(),
                    _fmt_num(s0, 2),
                    _fmt_num(sc, 2),
                    u.get('currency', '—'),
                    _fmt_pct(u.get('weight', 1) * 100, 1),
                ])
            elems += RavinalaComponents.data_table(
                headers, rows,
                col_alignments=['L', 'L', 'L', 'R', 'R', 'C', 'R'],
            )

        return elems

    # ------------------------------------------------------------------
    # PAGE 2 — STRUCTURE DETAILS
    # ------------------------------------------------------------------

    def _page_structure(self, trade: dict, St: dict) -> list:
        elems = []

        # ── Product Mechanism (auto-generated description) ───────────
        elems += RavinalaComponents.section_header('Product Mechanism', '1')
        description = ReportingTemplates.generate_product_description(trade)
        elems.append(Paragraph(description, St['body']))
        elems.append(Spacer(0, 10))

        # ── Barriers & Levels ────────────────────────────────────────
        barriers = trade.get('barriers', [])
        if barriers:
            elems += RavinalaComponents.section_header('Barriers & Levels', '2')
            b_data = {}
            for i, b in enumerate(barriers):
                btype = b.get('barrier_type', '—').replace('_', ' ').title()
                obs   = b.get('observation', '—').replace('_', ' ').title()
                trig  = ' TRIGGERED' if b.get('is_triggered') else ''
                b_data[f'{btype} Barrier'] = f"{_fmt_pct(b.get('level_pct'))} ({_fmt_num(b.get('level_abs'), 2)}){trig}"
                b_data[f'{btype} Observation'] = obs
                if b.get('triggered_date'):
                    b_data[f'{btype} Triggered'] = _fmt_date(b.get('triggered_date', ''))
            elems += RavinalaComponents.key_value_table(b_data, columns=2)
            elems.append(Spacer(0, 8))

        # ── Coupon Structure ─────────────────────────────────────────
        coupon = trade.get('coupon')
        if coupon:
            elems += RavinalaComponents.section_header('Coupon Structure', '3')
            c_data = {
                'Coupon Rate':      _fmt_pct(coupon.get('rate_pct')),
                'Frequency':        coupon.get('frequency', '—').replace('_', ' ').title(),
                'Conditional':      'Yes' if coupon.get('is_conditional') else 'No',
                'Condition Barrier':_fmt_pct(coupon.get('condition_barrier_pct')),
                'Memory Effect':    'Yes' if coupon.get('is_memory') else 'No',
                'Paid Coupons':     str(len(coupon.get('paid_coupons', []))) or '0',
            }
            elems += RavinalaComponents.key_value_table(c_data, columns=2)
            elems.append(Spacer(0, 8))

        # ── Capital Protection ───────────────────────────────────────
        cap_prot = trade.get('capital_protection_pct')
        if cap_prot is not None:
            elems += RavinalaComponents.section_header('Capital Structure', '4')
            cp_data = {
                'Capital Protection': _fmt_pct(cap_prot),
                'Participation Rate': _fmt_pct(trade.get('participation_rate')),
                'Cap Level':          _fmt_pct(trade.get('cap_pct')) if trade.get('cap_pct') else 'Uncapped',
                'Strike':             _fmt_pct(trade.get('strike_pct')),
            }
            elems += RavinalaComponents.key_value_table(cp_data, columns=2)
            elems.append(Spacer(0, 8))

        # ── Redemption Scenarios (text) ──────────────────────────────
        elems += RavinalaComponents.section_header('Redemption Scenarios', '5')
        scenarios_text = self._redemption_scenarios_text(trade)
        for bullet in scenarios_text:
            elems.append(Paragraph(f'\u2022  {bullet}', St['body']))
        elems.append(Spacer(0, 6))

        return elems

    def _redemption_scenarios_text(self, trade: dict) -> list:
        """Returns a list of bullet strings describing key redemption scenarios."""
        pt = trade.get('product_type', 'custom')
        barriers = trade.get('barriers', [])
        coupon = trade.get('coupon') or {}
        coupon_rate = coupon.get('rate_pct', 'N/A')
        tenor = trade.get('tenor_years', 1)

        ki = next((b.get('level_pct') for b in barriers if b.get('barrier_type') == 'knock_in'), None)
        ac = next((b.get('level_pct', 100) for b in barriers if b.get('barrier_type') == 'autocall'), None)
        cb = next((b.get('level_pct') for b in barriers if b.get('barrier_type') == 'coupon'), None)
        cap_prot = trade.get('capital_protection_pct', 100) or 100
        participation = trade.get('participation_rate', 100) or 100

        if pt in ('autocall', 'phoenix', 'athena'):
            bullets = [
                f'Early Redemption: If the underlying closes at or above {_fmt_pct(ac)} '
                f'on any observation date, the note is redeemed at 100% + coupon.',
                f'No Autocall — Coupon Paid: If the underlying closes at or above '
                f'{_fmt_pct(cb) if cb else _fmt_pct(ac)}, '
                f'the coupon of {coupon_rate}% is paid (with memory if applicable).',
                f'No Autocall — Coupon Missed: If the underlying closes below '
                f'{_fmt_pct(cb) if cb else _fmt_pct(ac)}, no coupon is paid this period.',
                f'At Maturity — No KI: If the knock-in barrier ({_fmt_pct(ki)}) has not '
                f'been breached, the investor receives 100% of notional.' if ki else
                'At Maturity — Bull: Investor receives 100% of notional + final coupon.',
                f'At Maturity — KI Breached: If the {_fmt_pct(ki)} barrier was triggered, '
                f'the investor receives notional × (Spot_final / Spot_initial). '
                f'Capital is fully at risk.' if ki else
                'At Maturity — Bear: Investor may lose some capital depending on structure.',
            ]
        elif pt == 'reverse_convertible':
            bpct = barriers[0].get('level_pct', 70) if barriers else 70
            bullets = [
                f'Coupon: The investor receives a fixed coupon of {coupon_rate}% per annum regardless of market performance.',
                f'At Maturity — Above {_fmt_pct(bpct)}: The investor receives 100% of notional plus all coupons.',
                f'At Maturity — Below {_fmt_pct(bpct)}: The investor receives notional × (Spot_final / Spot_initial). Capital at risk.',
            ]
        elif pt == 'capital_protected_note':
            bullets = [
                f'Capital Protection: At maturity, the investor is guaranteed {cap_prot}% of initial notional.',
                f'Upside Participation: The investor receives {cap_prot}% + {participation}% × max(0, Spot_final/Spot_initial - 1).',
                f'Cap: Upside is {_fmt_pct(trade.get("cap_pct"))}.' if trade.get('cap_pct') else 'No Cap: Unlimited upside participation.',
            ]
        elif pt in ('vanilla_call', 'vanilla_put'):
            strike = trade.get('strike_pct', 100)
            is_call = (pt == 'vanilla_call')
            bullets = [
                f'At Expiry — In the Money: The holder exercises the option and receives '
                f'{"Spot - Strike" if is_call else "Strike - Spot"} per unit of underlying.',
                f'At Expiry — Out of the Money: The option expires worthless. Maximum loss = premium paid.',
                f'Strike Level: {_fmt_pct(strike)} of initial spot.',
            ]
        else:
            bullets = [
                'Please refer to the Product Mechanism section above for full details.',
                f'This is a {PRODUCT_TYPE_LABELS.get(pt, "bespoke")} structure with {tenor:.1f}-year tenor.',
                'All terms are indicative and subject to final confirmation.',
            ]
        return bullets

    # ------------------------------------------------------------------
    # PAGE 3 — PAYOFF & SCENARIOS
    # ------------------------------------------------------------------

    def _page_payoff_scenarios(
        self, trade: dict, include_charts: bool, include_scenarios: bool, St: dict
    ) -> list:
        elems = []

        # ── Payoff Diagram ───────────────────────────────────────────
        if include_charts:
            elems += RavinalaComponents.section_header('Payoff at Maturity', '1')
            try:
                chart_bytes = ChartExporter.payoff_chart(trade)
                elems += RavinalaComponents.chart_image(
                    chart_bytes,
                    width=15 * cm,
                    height=7 * cm,
                    caption='Illustrative payoff at maturity as a function of the underlying final level (% of initial).'
                )
            except Exception:
                elems.append(Paragraph('[Payoff chart unavailable]', St['caption']))
            elems.append(Spacer(0, 8))

        # ── Scenario Analysis ────────────────────────────────────────
        if include_scenarios:
            elems += RavinalaComponents.section_header('Scenario Analysis', '2')
            scenarios = self._generate_scenario_table(trade)
            if scenarios:
                headers = ['Scenario', 'Underlying Level', 'Performance', 'Investor Return', 'Event']
                rows = []
                for s in scenarios:
                    pnl_color_val = s.get('return_pct', 0) or 0
                    rows.append([
                        s.get('name', '—'),
                        _fmt_num(s.get('spot_final'), 2) + f" ({_fmt_pct(s.get('spot_pct'))})",
                        _fmt_pct(s.get('underlying_perf'), 1),
                        _fmt_pct(s.get('return_pct'), 1),
                        s.get('event', '—'),
                    ])
                # Find P&L column index (index 3)
                elems += RavinalaComponents.data_table(
                    headers, rows,
                    col_alignments=['L', 'R', 'R', 'R', 'L'],
                    pnl_column=3,
                )
                elems.append(Spacer(0, 6))

                # ── Scenario chart ────────────────────────────────────
                if include_charts:
                    try:
                        chart_bytes = ChartExporter.scenario_comparison_chart(scenarios)
                        elems += RavinalaComponents.chart_image(
                            chart_bytes,
                            width=15 * cm,
                            height=6 * cm,
                            caption='Investor return (% of notional) across market scenarios.'
                        )
                    except Exception:
                        pass

        # ── Probability Analysis (if MC data available) ───────────────
        pr = trade.get('current_pricing') or trade.get('initial_pricing') or {}
        mc_paths = pr.get('mc_paths')
        if mc_paths and int(mc_paths) > 0:
            elems.append(Spacer(0, 6))
            elems += RavinalaComponents.section_header('Pricing Confidence', '3')
            ci = pr.get('mc_confidence_95')
            prob_data = {
                'Monte Carlo Paths': f'{int(mc_paths):,}',
                'Standard Error':    _fmt_pct(pr.get('mc_std_error'), 3) if pr.get('mc_std_error') else 'N/A',
                '95% Confidence Interval': (
                    f'[{ci[0]:.4f}%, {ci[1]:.4f}%]' if ci and len(ci) == 2 else 'N/A'
                ),
                'Computation Time':  f'{pr.get("computation_time_ms", 0):.0f} ms' if pr.get('computation_time_ms') else 'N/A',
            }
            elems += RavinalaComponents.key_value_table(prob_data, columns=2)

        return elems

    def _generate_scenario_table(self, trade: dict) -> list:
        """
        Generate 6-7 market scenarios adapted to the trade's barriers.
        Returns a list of dicts with name, spot_pct, spot_final, underlying_perf, return_pct, event.
        """
        uls = trade.get('underlyings', [])
        spot_init = uls[0].get('spot_at_inception', 100) if uls else 100
        pt = trade.get('product_type', 'custom')
        barriers = trade.get('barriers', [])
        coupon = trade.get('coupon') or {}
        coupon_rate = coupon.get('rate_pct', 0) or 0
        tenor = trade.get('tenor_years', 1) or 1
        notional = trade.get('notional', 1_000_000)

        ki_pct  = next((b.get('level_pct', 60) for b in barriers if b.get('barrier_type') == 'knock_in'), None)
        ac_pct  = next((b.get('level_pct', 100) for b in barriers if b.get('barrier_type') == 'autocall'), None)
        cb_pct  = next((b.get('level_pct', 70) for b in barriers if b.get('barrier_type') == 'coupon'), None)
        strike  = trade.get('strike_pct', 100) or 100
        cap_p   = trade.get('capital_protection_pct', 100) or 100
        part    = trade.get('participation_rate', 100) or 100

        # Spot levels to test (as % of initial)
        test_spots = {
            'Strong Rally (+40%)':  140,
            'Bull (+20%)':          120,
            'Flat (+0%)':           100,
            'Mild Bear (-15%)':      85,
            'Bear (-30%)':           70,
            'Crash (-50%)':          50,
        }

        # Add barrier-aware spots
        if ki_pct:
            test_spots[f'Just Above KI ({ki_pct + 5:.0f}%)'] = ki_pct + 5
            test_spots[f'Just Below KI ({ki_pct - 5:.0f}%)'] = ki_pct - 5

        scenarios = []
        for name, spot_pct in sorted(test_spots.items(), key=lambda x: -x[1]):
            spot_final = spot_init * spot_pct / 100
            underlying_perf = spot_pct - 100

            # Compute investor return based on product type
            if pt in ('autocall', 'phoenix', 'athena'):
                if ac_pct and spot_pct >= ac_pct:
                    # Assume Y1 autocall for bull scenarios
                    annual_c = float(coupon_rate)
                    ret = annual_c * 1  # Y1 coupon
                    event = f'Autocalled Y1 — +{annual_c:.1f}%'
                elif cb_pct and spot_pct >= cb_pct:
                    ret = float(coupon_rate) * float(tenor)
                    event = f'Held to maturity — coupons paid — +{ret:.1f}%'
                elif ki_pct and spot_pct < ki_pct:
                    ret = underlying_perf  # capital loss
                    event = f'KI triggered — capital at risk'
                else:
                    ret = 0
                    event = 'Held to maturity — no KI, coupons missed'
            elif pt == 'vanilla_call':
                ret = max(0, spot_pct - strike) - (trade.get('entry_price') or 2)
                event = 'Exercised' if spot_pct > strike else 'Expires worthless'
            elif pt == 'vanilla_put':
                ret = max(0, strike - spot_pct) - (trade.get('entry_price') or 2)
                event = 'Exercised' if spot_pct < strike else 'Expires worthless'
            elif pt == 'reverse_convertible':
                bpct_val = barriers[0].get('level_pct', 70) if barriers else 70
                if spot_pct >= bpct_val:
                    ret = float(coupon_rate) * float(tenor)
                    event = 'Capital protected — coupons paid'
                else:
                    ret = underlying_perf + float(coupon_rate) * float(tenor)
                    event = 'Capital at risk — partial loss'
            elif pt == 'capital_protected_note':
                upside = max(0, underlying_perf) * float(part) / 100
                cap_val = trade.get('cap_pct')
                if cap_val:
                    upside = min(upside, float(cap_val))
                ret = float(cap_p) - 100 + upside
                event = 'Maturity redemption'
            else:
                ret = underlying_perf * 0.5  # generic
                event = 'Maturity'

            scenarios.append({
                'name': name,
                'spot_pct': spot_pct,
                'spot_final': spot_final,
                'underlying_perf': underlying_perf,
                'return_pct': ret,
                'event': event,
            })

        return scenarios[:8]  # cap at 8 rows

    # ------------------------------------------------------------------
    # PAGE 4 — PRICING & GREEKS
    # ------------------------------------------------------------------

    def _page_pricing_greeks(self, trade: dict, include_charts: bool, St: dict) -> list:
        elems = []
        pr = trade.get('current_pricing') or {}
        ip = trade.get('initial_pricing') or {}
        ccy = trade.get('currency', 'EUR')

        # ── Pricing Details ──────────────────────────────────────────
        elems += RavinalaComponents.section_header('Pricing Details', '1')
        pricing_data = {
            'Pricing Model':   pr.get('model', '—').replace('_', ' ').title(),
            'Price (% Notional)': _fmt_pct(pr.get('price'), 4),
            'Notional Value':  _fmt_ccy(pr.get('notional_value'), ccy),
            'Entry Price':     _fmt_pct(trade.get('entry_price'), 4),
            'Price Date':      (pr.get('timestamp') or '—')[:16],
            'Data Staleness':  'STALE' if pr.get('is_stale') else 'Live',
            'MC Paths':        f"{int(pr.get('mc_paths', 0)):,}" if pr.get('mc_paths') else 'N/A',
            'Std Error':       _fmt_pct(pr.get('mc_std_error'), 4) if pr.get('mc_std_error') else 'N/A',
        }
        elems += RavinalaComponents.key_value_table(pricing_data, columns=2)
        elems.append(Spacer(0, 8))

        # ── Market Data at Pricing ───────────────────────────────────
        elems += RavinalaComponents.section_header('Market Data at Pricing', '2')
        mkt_data = {
            'Spot Level':          _fmt_num(pr.get('spot_used'), 2),
            'Implied Volatility':  _fmt_pct(pr.get('vol_used') * 100 if pr.get('vol_used') else None),
            'Risk-Free Rate':      _fmt_pct(pr.get('rate_used') * 100 if pr.get('rate_used') else None),
            'Dividend Yield':      _fmt_pct(trade.get('inception_div_yield') * 100
                                            if trade.get('inception_div_yield') else None),
            'Correlation':         'N/A (single asset)' if len(trade.get('underlyings', [])) <= 1
                                   else 'See correlation matrix',
        }
        elems += RavinalaComponents.key_value_table(mkt_data, columns=2)
        elems.append(Spacer(0, 8))

        # ── Greeks ───────────────────────────────────────────────────
        greeks = {
            'delta': pr.get('delta'),
            'gamma': pr.get('gamma'),
            'vega':  pr.get('vega'),
            'theta': pr.get('theta'),
            'rho':   pr.get('rho'),
            'vanna': pr.get('vanna'),
            'volga': pr.get('volga'),
        }
        has_greeks = any(v is not None for v in greeks.values())
        if has_greeks:
            elems += RavinalaComponents.section_header('Greeks', '3')
            elems.append(RavinalaComponents.greeks_table(greeks))
            elems.append(Spacer(0, 8))

            # ── Sensitivity Chart ─────────────────────────────────────
            if include_charts:
                try:
                    chart_bytes = ChartExporter.greeks_sensitivity_chart(trade)
                    elems += RavinalaComponents.chart_image(
                        chart_bytes,
                        width=15 * cm,
                        height=6 * cm,
                        caption='Delta and Vega sensitivity as a function of underlying spot level.'
                    )
                except Exception:
                    pass

        # ── P&L Summary ──────────────────────────────────────────────
        if trade.get('total_pnl') is not None:
            elems += RavinalaComponents.section_header('P&L Summary', '4')
            pnl_ccy = trade.get('pnl_currency', ccy)
            pnl_data = {
                'Entry Price':     _fmt_pct(trade.get('entry_price'), 4),
                'Current MTM':     _fmt_ccy(trade.get('current_mtm'), pnl_ccy),
                'Unrealized P&L':  _fmt_ccy(trade.get('unrealized_pnl'), pnl_ccy),
                'Realized P&L':    _fmt_ccy(trade.get('realized_pnl'), pnl_ccy),
                'Total P&L':       _fmt_ccy(trade.get('total_pnl'), pnl_ccy),
            }
            elems += RavinalaComponents.key_value_table(pnl_data, columns=2)

        return elems

    # ------------------------------------------------------------------
    # PAGE 5 — SCHEDULE
    # ------------------------------------------------------------------

    def _page_schedule(self, trade: dict, St: dict) -> list:
        elems = []

        elems += RavinalaComponents.section_header('Observation Schedule', '1')

        barriers = trade.get('barriers', [])
        coupon   = trade.get('coupon') or {}
        elems.append(RavinalaComponents.schedule_table(
            barriers=barriers,
            coupons=coupon,
            inception_date=trade.get('inception_date', ''),
            maturity_date=trade.get('maturity_date', ''),
            tenor_years=trade.get('tenor_years', 1) or 1,
        ))
        elems.append(Spacer(0, 10))

        # ── Key Dates ─────────────────────────────────────────────
        elems += RavinalaComponents.section_header('Key Dates', '2')
        dates_data = {
            'Trade Date':        _fmt_date(trade.get('trade_date', '')),
            'Inception Date':    _fmt_date(trade.get('inception_date', '')),
            'Maturity Date':     _fmt_date(trade.get('maturity_date', '')),
            'Settlement Date':   _fmt_date(trade.get('settlement_date', '')),
            'Tenor':             f"{trade.get('tenor_years', 0):.2f} years",
        }
        elems += RavinalaComponents.key_value_table(dates_data, columns=2)

        return elems

    # ------------------------------------------------------------------
    # PAGE 6 — DISCLAIMERS
    # ------------------------------------------------------------------

    def _page_disclaimers(self, trade: dict, mode: str, St: dict) -> list:
        elems = []

        elems += RavinalaComponents.section_header('Important Information & Disclaimers', '1')

        # Risk warnings based on product type
        pt = trade.get('product_type', 'custom')
        barriers = trade.get('barriers', [])
        has_ki = any(b.get('barrier_type') == 'knock_in' for b in barriers)
        cap_prot = trade.get('capital_protection_pct', 100) or 100

        warnings = [ReportingTemplates.risk_warning_structured_products()]
        if has_ki:
            warnings.append(ReportingTemplates.risk_warning_barrier_products())
        if cap_prot < 100:
            warnings.append(ReportingTemplates.risk_warning_capital_at_risk())
        warnings.append(ReportingTemplates.model_limitations())

        for w in warnings:
            elems.append(Paragraph(w, St['body_small']))
            elems.append(Spacer(0, 6))

        # MiFID notice
        elems.append(Paragraph(ReportingTemplates.mifid_notice(), St['disclaimer']))
        elems.append(Spacer(0, 8))

        # Full disclaimer
        elems += RavinalaComponents.disclaimer_block(
            custom_text=f'Document mode: {mode.upper()}. '
                        f'Ref: {trade.get("internal_ref", "—")}. '
                        f'Generated: {datetime.now().strftime("%d %b %Y %H:%M UTC")}.'
        )

        # Contact
        elems.append(Spacer(0, 8))
        elems.append(Paragraph(ReportingTemplates.contact_block(), St['body_small']))

        return elems
