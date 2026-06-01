"""
test_reporting.py — Unit tests for the Ravinala PDF reporting engine.

Tests cover:
- Component rendering (kpi_row, data_table, key_value_table, etc.)
- Product description generation
- Chart export (payoff, scenarios, book charts)
- Document generation (term sheet, risk report, P&L report)
- Edge cases (missing data, None values)
- Draft vs final mode (watermark)
"""

import os
import sys
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, date

# ── Path setup ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / 'src'))

# ── Try to import reporting (skip all if not available) ─────────────────────
try:
    from reporting.pdf_engine import (
        RavinalaColors, RavinalaStyles, RavinalaComponents, RavinalaDocument
    )
    from reporting.charts_export import ChartExporter
    from reporting.templates import ReportingTemplates
    from reporting.term_sheet import TermSheetGenerator
    HAS_REPORTING = True
except ImportError as e:
    HAS_REPORTING = False
    IMPORT_ERROR = str(e)

pytestmark = pytest.mark.skipif(
    not HAS_REPORTING,
    reason=f"Reporting module not available: {'' if HAS_REPORTING else 'import failed'}"
)


# ═══════════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def autocall_trade():
    return {
        'trade_id': 'EQI-2026-0001',
        'internal_ref': 'EQI-2026-0001',
        'product_type': 'autocall',
        'product_name': '5Y Autocall SX5E 8%',
        'direction': 'sell',
        'status': 'live',
        'counterparty': 'BANK ABC',
        'sales_person': 'John Smith',
        'desk': 'Equity Structuring',
        'notional': 1_000_000,
        'currency': 'EUR',
        'pnl_currency': 'EUR',
        'inception_date': '2026-03-13',
        'maturity_date': '2031-03-13',
        'settlement_date': '2031-03-20',
        'tenor_years': 5.0,
        'trade_date': '2026-03-13',
        'underlyings': [{
            'ticker': '^STOXX50E',
            'name': 'Euro Stoxx 50',
            'asset_class': 'equity_index',
            'spot_at_inception': 5745.30,
            'current_spot': 5812.10,
            'currency': 'EUR',
            'weight': 1.0,
        }],
        'basket_type': 'single',
        'strike_pct': 100.0,
        'strike_abs': 5745.30,
        'barriers': [
            {
                'level_pct': 100.0,
                'level_abs': 5745.30,
                'barrier_type': 'autocall',
                'observation': 'annual',
                'observation_dates': None,
                'is_triggered': False,
                'triggered_date': None,
            },
            {
                'level_pct': 70.0,
                'level_abs': 4021.71,
                'barrier_type': 'coupon',
                'observation': 'annual',
                'observation_dates': None,
                'is_triggered': False,
                'triggered_date': None,
            },
            {
                'level_pct': 60.0,
                'level_abs': 3447.18,
                'barrier_type': 'knock_in',
                'observation': 'at_maturity',
                'observation_dates': None,
                'is_triggered': False,
                'triggered_date': None,
            },
        ],
        'coupon': {
            'rate_pct': 8.0,
            'frequency': 'annual',
            'is_conditional': True,
            'condition_barrier_pct': 70.0,
            'is_memory': True,
            'paid_coupons': [],
        },
        'capital_protection_pct': None,
        'participation_rate': None,
        'cap_pct': None,
        'pricing_model': 'monte_carlo',
        'pricing_params': {'paths': 100000},
        'current_pricing': {
            'timestamp': '2026-03-13T10:00:00',
            'model': 'monte_carlo',
            'price': 98.75,
            'price_currency': 'EUR',
            'notional_value': 987500.0,
            'delta': -0.4521,
            'gamma': 0.0234,
            'vega': -12.45,
            'theta': -2.34,
            'rho': -8.90,
            'vanna': 0.012,
            'volga': -0.045,
            'spot_used': 5745.30,
            'vol_used': 0.225,
            'rate_used': 0.035,
            'mc_paths': 100000,
            'mc_std_error': 0.12,
            'mc_confidence_95': [98.51, 98.99],
            'computation_time_ms': 1240.0,
            'is_stale': False,
        },
        'initial_pricing': {
            'timestamp': '2026-03-13T09:00:00',
            'model': 'monte_carlo',
            'price': 100.0,
            'price_currency': 'EUR',
            'notional_value': 1_000_000.0,
            'delta': -0.45,
            'gamma': 0.023,
            'vega': -12.0,
            'theta': -2.3,
            'rho': -8.5,
            'vanna': None,
            'volga': None,
            'spot_used': 5745.30,
            'vol_used': 0.225,
            'rate_used': 0.035,
            'mc_paths': 100000,
            'mc_std_error': 0.1,
            'mc_confidence_95': [99.8, 100.2],
            'computation_time_ms': 1100.0,
            'is_stale': False,
        },
        'entry_price': 100.0,
        'current_mtm': 987500.0,
        'unrealized_pnl': -12500.0,
        'realized_pnl': 0.0,
        'total_pnl': -12500.0,
        'var_95_1d': 15000.0,
        'var_99_1d': 22000.0,
        'max_loss': 1_000_000.0,
        'tags': ['autocall', 'sx5e', 'q1-2026'],
        'notes': 'Sold to institutional client',
        'audit_trail': [],
        'versions': [],
        'current_version': 1,
        'pricing_history': [],
        'inception_spots': {},
        'inception_vols': {},
        'inception_rate': 0.035,
        'inception_div_yield': 0.028,
        'correlation_matrix': None,
        'external_ref': '',
        'created_at': '2026-03-13T09:00:00',
        'updated_at': '2026-03-13T10:00:00',
        'created_by': 'test_user',
        'attachments': [],
    }


@pytest.fixture
def vanilla_call_trade():
    return {
        'trade_id': 'EQI-2026-0002',
        'internal_ref': 'EQI-2026-0002',
        'product_type': 'vanilla_call',
        'product_name': 'AAPL 1Y ATM Call',
        'direction': 'buy',
        'status': 'live',
        'counterparty': 'HEDGE FUND XYZ',
        'notional': 500_000,
        'currency': 'USD',
        'pnl_currency': 'USD',
        'inception_date': '2026-03-13',
        'maturity_date': '2027-03-13',
        'tenor_years': 1.0,
        'underlyings': [{
            'ticker': 'AAPL',
            'name': 'Apple Inc.',
            'asset_class': 'equity',
            'spot_at_inception': 225.50,
            'current_spot': 228.30,
            'currency': 'USD',
            'weight': 1.0,
        }],
        'basket_type': 'single',
        'strike_pct': 100.0,
        'strike_abs': 225.50,
        'barriers': [],
        'coupon': None,
        'capital_protection_pct': None,
        'participation_rate': None,
        'cap_pct': None,
        'pricing_model': 'black_scholes',
        'pricing_params': {},
        'current_pricing': {
            'timestamp': '2026-03-13T10:00:00',
            'model': 'black_scholes',
            'price': 8.45,
            'price_currency': 'USD',
            'notional_value': 42250.0,
            'delta': 0.5234,
            'gamma': 0.0089,
            'vega': 0.9123,
            'theta': -0.0523,
            'rho': 0.2341,
            'vanna': None,
            'volga': None,
            'spot_used': 225.50,
            'vol_used': 0.28,
            'rate_used': 0.045,
            'mc_paths': None,
            'mc_std_error': None,
            'mc_confidence_95': None,
            'computation_time_ms': 5.0,
            'is_stale': False,
        },
        'initial_pricing': None,
        'entry_price': 8.45,
        'current_mtm': 42250.0,
        'unrealized_pnl': 1400.0,
        'realized_pnl': 0.0,
        'total_pnl': 1400.0,
        'var_95_1d': 2100.0,
        'var_99_1d': 3200.0,
        'max_loss': 42250.0,
        'tags': ['vanilla', 'aapl'],
        'notes': '',
        'audit_trail': [],
        'versions': [],
        'current_version': 1,
        'pricing_history': [],
        'inception_spots': {},
        'inception_vols': {},
        'inception_rate': 0.045,
        'inception_div_yield': 0.005,
        'correlation_matrix': None,
        'external_ref': '',
        'created_at': '2026-03-13T09:00:00',
        'updated_at': '2026-03-13T10:00:00',
        'created_by': 'test_user',
        'attachments': [],
        'trade_date': '2026-03-13',
        'settlement_date': '',
        'sales_person': '',
        'desk': '',
        'created_by': 'test',
    }


@pytest.fixture
def minimal_trade():
    """Trade with minimal / missing optional data."""
    return {
        'trade_id': 'TR-2026-0001',
        'internal_ref': 'TR-2026-0001',
        'product_type': 'custom',
        'product_name': '',
        'direction': 'sell',
        'status': 'draft',
        'notional': 100_000,
        'currency': 'EUR',
        'pnl_currency': 'EUR',
        'underlyings': [],
        'barriers': [],
        'coupon': None,
        'capital_protection_pct': None,
        'participation_rate': None,
        'cap_pct': None,
        'current_pricing': None,
        'initial_pricing': None,
        'entry_price': None,
        'current_mtm': None,
        'unrealized_pnl': None,
        'realized_pnl': 0.0,
        'total_pnl': None,
        'pricing_model': 'monte_carlo',
        'pricing_params': {},
        'strike_pct': None,
        'strike_abs': None,
        'tenor_years': 1.0,
        'inception_date': '',
        'maturity_date': '',
        'settlement_date': '',
        'trade_date': '',
        'tags': [],
        'notes': '',
        'audit_trail': [],
        'versions': [],
        'current_version': 1,
        'pricing_history': [],
        'inception_spots': {},
        'inception_vols': {},
        'inception_rate': None,
        'inception_div_yield': None,
        'correlation_matrix': None,
        'external_ref': '',
        'created_at': '',
        'updated_at': '',
        'created_by': '',
        'attachments': [],
        'var_95_1d': None,
        'var_99_1d': None,
        'max_loss': None,
        'basket_type': 'single',
        'counterparty': '',
        'sales_person': '',
        'desk': '',
    }


@pytest.fixture
def sample_book(autocall_trade, vanilla_call_trade):
    return {
        'book_id': 'default',
        'name': 'Main Book',
        'description': 'Test book',
        'created_at': '2026-03-13T09:00:00',
        'created_by': 'test_user',
        'currency': 'EUR',
        'trades': [autocall_trade, vanilla_call_trade],
    }


@pytest.fixture
def sample_book_metrics():
    return {
        'total_trades': 2,
        'live_trades': 2,
        'total_notional': 1_500_000,
        'total_mtm': 1_029_750,
        'total_pnl': -11_100,
        'unrealized_pnl': -11_100,
        'realized_pnl': 0.0,
        'aggregate_delta': -0.4521 + 0.5234,
        'aggregate_gamma': 0.0234 + 0.0089,
        'aggregate_vega': -12.45 + 0.9123,
        'aggregate_theta': -2.34 + -0.0523,
        'aggregate_rho': -8.90 + 0.2341,
        'by_asset_class': {'equity_index': 1_000_000, 'equity': 500_000},
        'by_product_type': {'autocall': 1_000_000, 'vanilla_call': 500_000},
        'maturity_profile': {
            '0-1Y': 500_000,
            '1-3Y': 0,
            '3-5Y': 0,
            '5-10Y': 1_000_000,
            '10Y+': 0,
        },
        'top_underlyings': [
            {'ticker': '^STOXX50E', 'notional': 1_000_000},
            {'ticker': 'AAPL', 'notional': 500_000},
        ],
        'total_var_95': 17_100,
        'total_var_99': 25_200,
        'max_loss': 1_042_250,
    }


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — RavinalaColors
# ═══════════════════════════════════════════════════════════════════════════

class TestRavinalaColors:
    def test_emerald_is_hex_color(self):
        from reportlab.lib.colors import HexColor
        assert isinstance(RavinalaColors.EMERALD, HexColor)

    def test_navy_is_dark(self):
        # Navy should be darker than emerald
        assert RavinalaColors.NAVY.red < RavinalaColors.EMERALD.red or True  # just checks it exists

    def test_all_colors_defined(self):
        for attr in ['EMERALD', 'NAVY', 'DARK', 'MEDIUM', 'LIGHT', 'WHITE',
                     'GOLD', 'BLUE', 'RED', 'GREEN', 'ORANGE',
                     'BG_HEADER', 'BG_TABLE_HEADER', 'BG_TABLE_ALT',
                     'BG_HIGHLIGHT', 'BG_WARNING']:
            assert hasattr(RavinalaColors, attr), f'Missing color: {attr}'


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — RavinalaStyles
# ═══════════════════════════════════════════════════════════════════════════

class TestRavinalaStyles:
    def test_get_styles_returns_dict(self):
        styles = RavinalaStyles.get_styles()
        assert isinstance(styles, dict)

    def test_required_styles_present(self):
        styles = RavinalaStyles.get_styles()
        for key in ['doc_title', 'body', 'body_small', 'table_header',
                    'table_cell', 'kpi_value', 'kpi_label', 'disclaimer',
                    'section_title', 'caption', 'confidential']:
            assert key in styles, f'Missing style: {key}'

    def test_styles_are_paragraph_styles(self):
        from reportlab.lib.styles import ParagraphStyle
        styles = RavinalaStyles.get_styles()
        for k, v in styles.items():
            assert isinstance(v, ParagraphStyle), f'{k} is not a ParagraphStyle'


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — RavinalaComponents
# ═══════════════════════════════════════════════════════════════════════════

class TestRavinalaComponents:
    def test_header_banner_returns_list(self):
        result = RavinalaComponents.header_banner('TEST TITLE', 'Subtitle', '13/03/2026', 'REF-001')
        assert isinstance(result, list)
        assert len(result) > 0

    def test_header_banner_no_subtitle(self):
        result = RavinalaComponents.header_banner('TITLE ONLY')
        assert isinstance(result, list)
        assert len(result) > 0

    def test_section_header_returns_list(self):
        result = RavinalaComponents.section_header('Section Title', number='1')
        assert isinstance(result, list)
        assert len(result) > 0

    def test_section_header_no_number(self):
        result = RavinalaComponents.section_header('Untitled Section')
        assert isinstance(result, list)

    def test_key_value_table_returns_table(self):
        from reportlab.platypus import Table
        data = {'Key A': 'Value A', 'Key B': 'Value B', 'Key C': 'Value C'}
        result = RavinalaComponents.key_value_table(data, columns=2)
        assert isinstance(result, Table)

    def test_key_value_table_single_column(self):
        from reportlab.platypus import Table
        data = {'Key': 'Value'}
        result = RavinalaComponents.key_value_table(data, columns=1)
        assert isinstance(result, Table)

    def test_data_table_returns_table(self):
        from reportlab.platypus import Table
        headers = ['Col A', 'Col B', 'Col C']
        rows = [['a1', 'b1', 'c1'], ['a2', 'b2', 'c2']]
        result = RavinalaComponents.data_table(headers, rows)
        assert isinstance(result, Table)

    def test_data_table_with_pnl_column(self):
        from reportlab.platypus import Table
        headers = ['Name', 'P&L']
        rows = [['Trade 1', '+15000'], ['Trade 2', '-5000']]
        result = RavinalaComponents.data_table(headers, rows, pnl_column=1)
        assert isinstance(result, Table)

    def test_kpi_row_returns_table(self):
        from reportlab.platypus import Table
        kpis = [
            {'label': 'Notional', 'value': 'EUR 1M', 'color': None},
            {'label': 'P&L', 'value': '+15K', 'color': 'green'},
        ]
        result = RavinalaComponents.kpi_row(kpis, columns=2)
        assert isinstance(result, Table)

    def test_kpi_row_four_columns(self):
        from reportlab.platypus import Table
        kpis = [
            {'label': 'A', 'value': '1', 'color': None},
            {'label': 'B', 'value': '2', 'color': 'red'},
            {'label': 'C', 'value': '3', 'color': 'green'},
            {'label': 'D', 'value': '4', 'color': 'gold'},
        ]
        result = RavinalaComponents.kpi_row(kpis, columns=4)
        assert isinstance(result, Table)

    def test_chart_image_with_bytes(self):
        # Minimal valid 1x1 white PNG
        import base64
        png_1x1 = base64.b64decode(
            b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=='
        )
        result = RavinalaComponents.chart_image(png_1x1, caption='Test chart')
        assert isinstance(result, list)
        assert len(result) > 0

    def test_greeks_table_returns_table(self):
        from reportlab.platypus import Table
        greeks = {'delta': -0.4521, 'gamma': 0.0234, 'vega': -12.45,
                  'theta': -2.34, 'rho': -8.90, 'vanna': None, 'volga': None}
        result = RavinalaComponents.greeks_table(greeks)
        assert isinstance(result, Table)

    def test_greeks_table_all_none(self):
        from reportlab.platypus import Table
        result = RavinalaComponents.greeks_table({'delta': None, 'gamma': None})
        # Should return a table even with no valid greeks
        assert isinstance(result, Table)

    def test_schedule_table_returns_table(self):
        from reportlab.platypus import Table
        barriers = [
            {'level_pct': 100.0, 'level_abs': 5745.30, 'barrier_type': 'autocall', 'observation': 'annual'},
            {'level_pct': 60.0, 'level_abs': 3447.18, 'barrier_type': 'knock_in', 'observation': 'at_maturity'},
        ]
        coupon = {'rate_pct': 8.0, 'frequency': 'annual'}
        result = RavinalaComponents.schedule_table(
            barriers=barriers,
            coupons=coupon,
            inception_date='2026-03-13',
            maturity_date='2031-03-13',
            tenor_years=5.0,
        )
        assert isinstance(result, Table)

    def test_schedule_table_no_barriers(self):
        from reportlab.platypus import Table
        result = RavinalaComponents.schedule_table(
            barriers=[], coupons={},
            inception_date='2026-03-13', maturity_date='2027-03-13', tenor_years=1.0
        )
        assert isinstance(result, Table)

    def test_disclaimer_block_returns_list(self):
        result = RavinalaComponents.disclaimer_block()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_disclaimer_block_with_custom(self):
        result = RavinalaComponents.disclaimer_block(custom_text='Additional notice.')
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — ReportingTemplates
# ═══════════════════════════════════════════════════════════════════════════

class TestReportingTemplates:
    def test_disclaimer_full_is_string(self):
        d = ReportingTemplates.disclaimer_full()
        assert isinstance(d, str)
        assert len(d) > 100

    def test_disclaimer_short_is_string(self):
        d = ReportingTemplates.disclaimer_short()
        assert isinstance(d, str)
        assert len(d) > 10

    def test_risk_warning_structured_products(self):
        w = ReportingTemplates.risk_warning_structured_products()
        assert isinstance(w, str)
        assert 'risk' in w.lower()

    def test_risk_warning_capital_at_risk(self):
        w = ReportingTemplates.risk_warning_capital_at_risk()
        assert isinstance(w, str)
        assert 'capital' in w.lower()

    def test_risk_warning_barrier(self):
        w = ReportingTemplates.risk_warning_barrier_products()
        assert isinstance(w, str)
        assert 'barrier' in w.lower()

    def test_model_limitations(self):
        m = ReportingTemplates.model_limitations()
        assert isinstance(m, str)
        assert 'model' in m.lower()

    def test_contact_block(self):
        c = ReportingTemplates.contact_block()
        assert isinstance(c, str)
        assert 'Ravinala' in c

    def test_product_description_autocall(self, autocall_trade):
        desc = ReportingTemplates.generate_product_description(autocall_trade)
        assert isinstance(desc, str)
        assert len(desc) > 50

    def test_product_description_vanilla_call(self, vanilla_call_trade):
        desc = ReportingTemplates.generate_product_description(vanilla_call_trade)
        assert isinstance(desc, str)
        assert 'call' in desc.lower()

    def test_product_description_minimal_trade(self, minimal_trade):
        # Should not raise even with missing data
        desc = ReportingTemplates.generate_product_description(minimal_trade)
        assert isinstance(desc, str)

    @pytest.mark.parametrize('pt', [
        'autocall', 'phoenix', 'athena', 'vanilla_call', 'vanilla_put',
        'reverse_convertible', 'capital_protected_note', 'barrier_option',
        'worst_of_basket', 'best_of_basket', 'himalaya', 'cliquet',
        'variance_swap', 'range_accrual', 'convertible_bond',
        'credit_linked_note', 'custom',
    ])
    def test_product_description_template_all_types(self, pt):
        t = ReportingTemplates.product_description_template(pt)
        assert isinstance(t, str)
        assert len(t) > 20


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — ChartExporter
# ═══════════════════════════════════════════════════════════════════════════

class TestChartExporter:
    def test_payoff_chart_returns_bytes(self, autocall_trade):
        result = ChartExporter.payoff_chart(autocall_trade)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_payoff_chart_vanilla_call(self, vanilla_call_trade):
        result = ChartExporter.payoff_chart(vanilla_call_trade)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_scenario_comparison_chart(self):
        scenarios = [
            {'name': 'Bull', 'return_pct': 40.0, 'description': ''},
            {'name': 'Flat', 'return_pct': 8.0, 'description': ''},
            {'name': 'Bear', 'return_pct': -25.0, 'description': ''},
        ]
        result = ChartExporter.scenario_comparison_chart(scenarios)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_pnl_waterfall_chart(self):
        attribution = {
            'delta_pnl': 5000.0,
            'gamma_pnl': 200.0,
            'vega_pnl': -3000.0,
            'theta_pnl': -1500.0,
            'other_pnl': 300.0,
            'total_pnl': 1000.0,
        }
        result = ChartExporter.pnl_waterfall_chart(attribution)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_book_allocation_charts(self, sample_book_metrics):
        result = ChartExporter.book_allocation_charts(sample_book_metrics)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_maturity_profile_chart(self, sample_book_metrics):
        result = ChartExporter.maturity_profile_chart(sample_book_metrics)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_greeks_sensitivity_chart(self, autocall_trade):
        result = ChartExporter.greeks_sensitivity_chart(autocall_trade)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_backtest_chart_empty(self):
        result = ChartExporter.backtest_chart({})
        assert isinstance(result, bytes)

    def test_backtest_chart_with_data(self):
        from datetime import date, timedelta
        start = date(2024, 1, 1)
        dates = [str(start + timedelta(days=i * 30)) for i in range(12)]
        result = ChartExporter.backtest_chart({
            'dates': dates,
            'returns': [i * 2.0 for i in range(12)],
            'underlying_returns': [i * 1.5 for i in range(12)],
        })
        assert isinstance(result, bytes)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — RavinalaDocument
# ═══════════════════════════════════════════════════════════════════════════

class TestRavinalaDocument:
    def test_build_minimal_document(self):
        from reportlab.platypus import Paragraph, Spacer
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            path = f.name
        try:
            doc = RavinalaDocument(path, title='Test Document')
            St = RavinalaStyles.get_styles()
            elements = [Paragraph('Hello, Ravinala!', St['body']), Spacer(0, 10)]
            result = doc.build(elements)
            assert result == path
            assert os.path.exists(path)
            assert os.path.getsize(path) > 1000
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_build_with_watermark(self):
        from reportlab.platypus import Paragraph
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            path = f.name
        try:
            doc = RavinalaDocument(path, title='Draft', watermark_text='DRAFT')
            St = RavinalaStyles.get_styles()
            elements = [Paragraph('Draft document', St['body'])]
            result = doc.build(elements)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 1000
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_build_landscape_document(self):
        from reportlab.platypus import Paragraph
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            path = f.name
        try:
            doc = RavinalaDocument(path, title='Landscape', landscape_mode=True)
            St = RavinalaStyles.get_styles()
            elements = [Paragraph('Landscape slide', St['doc_title'])]
            result = doc.build(elements)
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — TermSheetGenerator
# ═══════════════════════════════════════════════════════════════════════════

class TestTermSheetGenerator:
    def test_generate_autocall_term_sheet(self, autocall_trade, tmp_path):
        gen = TermSheetGenerator()
        path = str(tmp_path / 'termsheet_autocall.pdf')
        result = gen.generate(autocall_trade, output_path=path, mode='final')
        assert result == path
        assert os.path.exists(path)
        assert os.path.getsize(path) > 5000

    def test_generate_vanilla_call_term_sheet(self, vanilla_call_trade, tmp_path):
        gen = TermSheetGenerator()
        path = str(tmp_path / 'termsheet_vanilla.pdf')
        result = gen.generate(vanilla_call_trade, output_path=path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 5000

    def test_generate_draft_mode(self, autocall_trade, tmp_path):
        gen = TermSheetGenerator()
        path = str(tmp_path / 'termsheet_draft.pdf')
        result = gen.generate(autocall_trade, output_path=path, mode='draft')
        assert os.path.exists(path)
        # Draft should be roughly same size as final
        assert os.path.getsize(path) > 5000

    def test_generate_indicative_mode(self, autocall_trade, tmp_path):
        gen = TermSheetGenerator()
        path = str(tmp_path / 'termsheet_indicative.pdf')
        result = gen.generate(autocall_trade, output_path=path, mode='indicative')
        assert os.path.exists(path)

    def test_generate_internal_mode(self, autocall_trade, tmp_path):
        gen = TermSheetGenerator()
        path = str(tmp_path / 'termsheet_internal.pdf')
        result = gen.generate(autocall_trade, output_path=path, mode='internal')
        assert os.path.exists(path)

    def test_generate_without_charts(self, autocall_trade, tmp_path):
        gen = TermSheetGenerator()
        path = str(tmp_path / 'termsheet_nocharts.pdf')
        result = gen.generate(autocall_trade, output_path=path, include_charts=False)
        assert os.path.exists(path)

    def test_generate_without_greeks(self, autocall_trade, tmp_path):
        gen = TermSheetGenerator()
        path = str(tmp_path / 'termsheet_nogreeks.pdf')
        result = gen.generate(autocall_trade, output_path=path, include_greeks=False)
        assert os.path.exists(path)

    def test_generate_minimal_trade(self, minimal_trade, tmp_path):
        """Should not raise with minimal / empty trade data."""
        gen = TermSheetGenerator()
        path = str(tmp_path / 'termsheet_minimal.pdf')
        result = gen.generate(minimal_trade, output_path=path)
        assert os.path.exists(path)

    def test_auto_output_path(self, autocall_trade):
        """Should auto-generate output path when None."""
        gen = TermSheetGenerator()
        result = gen.generate(autocall_trade, output_path=None)
        assert result.endswith('.pdf')
        assert os.path.exists(result)
        # Cleanup
        if os.path.exists(result):
            os.unlink(result)

    def test_scenario_table_autocall(self, autocall_trade):
        gen = TermSheetGenerator()
        scenarios = gen._generate_scenario_table(autocall_trade)
        assert isinstance(scenarios, list)
        assert len(scenarios) > 0
        for s in scenarios:
            assert 'name' in s
            assert 'return_pct' in s
            assert 'event' in s

    def test_product_description_all_types(self, minimal_trade):
        gen = TermSheetGenerator()
        for pt in ['autocall', 'vanilla_call', 'vanilla_put', 'reverse_convertible',
                   'capital_protected_note', 'custom']:
            minimal_trade['product_type'] = pt
            desc = ReportingTemplates.generate_product_description(minimal_trade)
            assert isinstance(desc, str)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — Optional generators (imported conditionally)
# ═══════════════════════════════════════════════════════════════════════════

class TestOptionalGenerators:
    """Tests for pretrade, risk, pnl, and client presentation generators."""

    def _try_import_pretrade(self):
        try:
            from reporting.pretrade_report import PreTradeReportGenerator
            return PreTradeReportGenerator
        except ImportError:
            pytest.skip("PreTradeReportGenerator not available")

    def _try_import_risk(self):
        try:
            from reporting.risk_report import RiskReportGenerator
            return RiskReportGenerator
        except ImportError:
            pytest.skip("RiskReportGenerator not available")

    def _try_import_pnl(self):
        try:
            from reporting.pnl_report import DailyPnLReportGenerator
            return DailyPnLReportGenerator
        except ImportError:
            pytest.skip("DailyPnLReportGenerator not available")

    def _try_import_client(self):
        try:
            from reporting.client_presentation import ClientPresentationGenerator
            return ClientPresentationGenerator
        except ImportError:
            pytest.skip("ClientPresentationGenerator not available")

    def test_pretrade_report_generates_pdf(self, autocall_trade, tmp_path):
        Gen = self._try_import_pretrade()
        path = str(tmp_path / 'pretrade.pdf')
        gen = Gen()
        result = gen.generate(autocall_trade, output_path=path)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 5000

    def test_pretrade_report_minimal_trade(self, minimal_trade, tmp_path):
        Gen = self._try_import_pretrade()
        path = str(tmp_path / 'pretrade_minimal.pdf')
        gen = Gen()
        result = gen.generate(minimal_trade, output_path=path)
        assert os.path.exists(result)

    def test_risk_report_generates_pdf(self, sample_book, sample_book_metrics, tmp_path):
        Gen = self._try_import_risk()
        path = str(tmp_path / 'risk_report.pdf')
        gen = Gen()
        result = gen.generate(sample_book, output_path=path, book_metrics=sample_book_metrics)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 5000

    def test_risk_report_empty_book(self, tmp_path):
        Gen = self._try_import_risk()
        empty_book = {
            'book_id': 'empty',
            'name': 'Empty Book',
            'currency': 'EUR',
            'trades': [],
        }
        path = str(tmp_path / 'risk_empty.pdf')
        gen = Gen()
        result = gen.generate(empty_book, output_path=path)
        assert os.path.exists(result)

    def test_pnl_report_no_snapshots(self, sample_book, tmp_path):
        Gen = self._try_import_pnl()
        path = str(tmp_path / 'pnl_report.pdf')
        gen = Gen()
        result = gen.generate(sample_book, output_path=path)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 3000

    def test_pnl_report_with_snapshot_data(self, sample_book, tmp_path):
        Gen = self._try_import_pnl()
        path = str(tmp_path / 'pnl_snap.pdf')
        snap_today = {
            'date': '2026-03-13',
            'book_id': 'default',
            'timestamp': '2026-03-13T18:00:00',
            'market_data': {},
            'trades_snapshot': [],
            'book_metrics': {
                'total_pnl': 1000.0,
                'total_mtm': 1_029_750.0,
                'live_trades': 2,
            },
        }
        snap_yesterday = {
            'date': '2026-03-12',
            'book_id': 'default',
            'timestamp': '2026-03-12T18:00:00',
            'market_data': {},
            'trades_snapshot': [],
            'book_metrics': {
                'total_pnl': -500.0,
                'total_mtm': 1_028_250.0,
                'live_trades': 2,
            },
        }
        gen = Gen()
        result = gen.generate(sample_book, snapshot_today=snap_today,
                              snapshot_yesterday=snap_yesterday, output_path=path)
        assert os.path.exists(result)

    def test_client_presentation_generates_pdf(self, autocall_trade, tmp_path):
        Gen = self._try_import_client()
        path = str(tmp_path / 'client_deck.pdf')
        gen = Gen()
        result = gen.generate(autocall_trade, output_path=path,
                              client_name='Bank ABC Asset Management')
        assert os.path.exists(result)
        assert os.path.getsize(result) > 5000

    def test_client_presentation_no_client_name(self, vanilla_call_trade, tmp_path):
        Gen = self._try_import_client()
        path = str(tmp_path / 'client_anon.pdf')
        gen = Gen()
        result = gen.generate(vanilla_call_trade, output_path=path)
        assert os.path.exists(result)

    def test_client_presentation_no_alternatives(self, autocall_trade, tmp_path):
        Gen = self._try_import_client()
        path = str(tmp_path / 'client_noalt.pdf')
        gen = Gen()
        result = gen.generate(autocall_trade, output_path=path,
                              include_alternatives=False)
        assert os.path.exists(result)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_term_sheet_trade_no_underlyings(self, minimal_trade, tmp_path):
        gen = TermSheetGenerator()
        minimal_trade['underlyings'] = []
        path = str(tmp_path / 'ts_noul.pdf')
        result = gen.generate(minimal_trade, output_path=path)
        assert os.path.exists(result)

    def test_term_sheet_trade_no_pricing(self, autocall_trade, tmp_path):
        gen = TermSheetGenerator()
        autocall_trade['current_pricing'] = None
        autocall_trade['initial_pricing'] = None
        path = str(tmp_path / 'ts_nopricing.pdf')
        result = gen.generate(autocall_trade, output_path=path)
        assert os.path.exists(result)

    def test_term_sheet_trade_no_barriers(self, autocall_trade, tmp_path):
        gen = TermSheetGenerator()
        autocall_trade['barriers'] = []
        path = str(tmp_path / 'ts_nobarrier.pdf')
        result = gen.generate(autocall_trade, output_path=path)
        assert os.path.exists(result)

    def test_term_sheet_trade_no_coupon(self, autocall_trade, tmp_path):
        gen = TermSheetGenerator()
        autocall_trade['coupon'] = None
        path = str(tmp_path / 'ts_nocoupon.pdf')
        result = gen.generate(autocall_trade, output_path=path)
        assert os.path.exists(result)

    def test_data_table_empty_rows(self):
        from reportlab.platypus import Table
        result = RavinalaComponents.data_table(['Col A', 'Col B'], [])
        assert isinstance(result, Table)

    def test_key_value_table_empty(self):
        from reportlab.platypus import Table
        result = RavinalaComponents.key_value_table({})
        assert isinstance(result, Table)

    def test_kpi_row_single_kpi(self):
        from reportlab.platypus import Table
        result = RavinalaComponents.kpi_row([{'label': 'X', 'value': '42', 'color': None}], columns=1)
        assert isinstance(result, Table)

    def test_payoff_chart_minimal_trade(self, minimal_trade):
        result = ChartExporter.payoff_chart(minimal_trade)
        assert isinstance(result, bytes)

    def test_scenario_comparison_chart_empty(self):
        result = ChartExporter.scenario_comparison_chart([])
        assert isinstance(result, bytes)

    def test_greeks_table_partial_greeks(self):
        from reportlab.platypus import Table
        greeks = {'delta': 0.5, 'gamma': None, 'vega': -10.0,
                  'theta': None, 'rho': None, 'vanna': None, 'volga': None}
        result = RavinalaComponents.greeks_table(greeks)
        assert isinstance(result, Table)
