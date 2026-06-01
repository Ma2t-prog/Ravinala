"""
test_tradebook.py — Test suite for the Ravinala Trade Book system.
Run with: pytest tests/test_tradebook.py -v

Covers: CRUD, search/filter, book metrics, repricing, snapshots,
        templates, export, edge cases, versioning, ID generation.
"""

import sys
import os
import json
import tempfile
import shutil
import pytest
from datetime import datetime, date, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure src/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tradebook_models import (
    Trade, Book, DailySnapshot, PricingResult, TradeStatus, ProductType,
    PRODUCT_TYPE_LABELS, STATUS_ICONS, ASSET_PREFIXES
)
from tradebook import BookManager, TradeIDGenerator, build_trade_from_pricing, _bs_greeks


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def tmp_dir():
    """Temporary directory for each test."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def bm(tmp_dir):
    """BookManager backed by a temp directory."""
    return BookManager(data_dir=tmp_dir)


@pytest.fixture
def sample_pricing():
    return PricingResult(
        timestamp=datetime.utcnow().isoformat(),
        model='black_scholes',
        price=98.75,
        price_currency='EUR',
        notional_value=987_500.0,
        delta=-0.452,
        gamma=0.023,
        vega=-12.45,
        theta=-2.34,
        rho=-8.90,
        spot_used=5745.30,
        vol_used=0.225,
        rate_used=0.035,
    )


@pytest.fixture
def sample_trade(sample_pricing):
    """A complete sample Trade object."""
    return Trade(
        product_type='autocall',
        product_name='5Y Autocall on Euro Stoxx 50',
        direction='sell',
        notional=1_000_000.0,
        currency='EUR',
        inception_date='2026-01-12',
        maturity_date='2031-01-12',
        tenor_years=5.0,
        underlyings=[{
            'ticker': '^STOXX50E',
            'name': 'Euro Stoxx 50',
            'asset_class': 'equity_index',
            'spot_at_inception': 5745.30,
            'current_spot': 5680.0,
            'currency': 'EUR',
            'weight': 1.0,
        }],
        strike_pct=100.0,
        barriers=[{
            'level_pct': 60.0,
            'level_abs': 3447.18,
            'barrier_type': 'knock_in',
            'observation': 'at_maturity',
            'is_triggered': False,
        }],
        coupon={
            'rate_pct': 8.0,
            'frequency': 'annual',
            'is_conditional': True,
            'condition_barrier_pct': 70.0,
            'is_memory': True,
            'paid_coupons': [],
        },
        entry_price=sample_pricing.price,
        current_pricing=sample_pricing.to_dict(),
        initial_pricing=sample_pricing.to_dict(),
        current_mtm=sample_pricing.notional_value,
        unrealized_pnl=0.0,
        realized_pnl=0.0,
        total_pnl=0.0,
        inception_spots={'^STOXX50E': 5745.30},
        inception_vols={'^STOXX50E': 0.225},
        inception_rate=0.035,
        counterparty='Client ABC',
        desk='Equity Derivatives',
        tags=['autocall', 'sx5e', 'client_abc'],
        notes='Standard 5Y autocall.',
        status='live',
        created_by='testuser',
    )


# ═══════════════════════════════════════════════════════════════
# 1. BOOK CRUD
# ═══════════════════════════════════════════════════════════════

class TestBookCRUD:

    def test_default_book_created(self, bm):
        """Default book is created automatically."""
        books = bm.list_books()
        assert any(b['book_id'] == 'default' for b in books)

    def test_create_book(self, bm):
        book = bm.create_book("Test Book", description="desc", currency="USD")
        assert book.name == "Test Book"
        assert book.currency == "USD"
        loaded = bm.load_book(book.book_id)
        assert loaded.name == "Test Book"

    def test_list_books(self, bm):
        bm.create_book("Book A")
        bm.create_book("Book B")
        books = bm.list_books()
        names = [b['name'] for b in books]
        assert "Book A" in names
        assert "Book B" in names

    def test_load_nonexistent_book_raises(self, bm):
        with pytest.raises(FileNotFoundError):
            bm.load_book("nonexistent_id")

    def test_delete_book(self, bm):
        book = bm.create_book("To Delete")
        bid = book.book_id
        result = bm.delete_book(bid)
        assert result is True
        with pytest.raises(FileNotFoundError):
            bm.load_book(bid)

    def test_cannot_delete_default_book(self, bm):
        result = bm.delete_book('default')
        assert result is False

    def test_duplicate_book(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        dup = bm.duplicate_book('default', 'Duplicate')
        assert dup.name == 'Duplicate'
        assert len(dup.trades) == len(bm.load_book('default').trades)
        # Trade IDs must be different
        orig_ids = {t['trade_id'] for t in bm.load_book('default').trades}
        dup_ids = {t['trade_id'] for t in dup.trades}
        assert not orig_ids.intersection(dup_ids)

    def test_save_and_reload_book(self, bm):
        book = bm.load_book('default')
        book.description = "updated description"
        bm.save_book(book)
        reloaded = bm.load_book('default')
        assert reloaded.description == "updated description"


# ═══════════════════════════════════════════════════════════════
# 2. TRADE CRUD
# ═══════════════════════════════════════════════════════════════

class TestTradeCRUD:

    def test_add_trade_returns_id(self, bm, sample_trade):
        tid = bm.add_trade('default', sample_trade)
        assert tid == sample_trade.trade_id

    def test_add_trade_auto_assigns_ref(self, bm, sample_trade):
        sample_trade.internal_ref = ''
        bm.add_trade('default', sample_trade)
        t = bm.get_trade('default', sample_trade.trade_id)
        assert t.internal_ref != ''
        assert 'EQI' in t.internal_ref or 'EQ' in t.internal_ref

    def test_get_trade(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        t = bm.get_trade('default', sample_trade.trade_id)
        assert t.trade_id == sample_trade.trade_id
        assert t.product_name == sample_trade.product_name

    def test_get_nonexistent_trade_raises(self, bm):
        with pytest.raises(KeyError):
            bm.get_trade('default', 'nonexistent')

    def test_update_trade(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        result = bm.update_trade(
            'default', sample_trade.trade_id,
            {'notes': 'Updated notes', 'counterparty': 'New Client'},
            updated_by='testuser', change_description='Test update'
        )
        assert result is True
        t = bm.get_trade('default', sample_trade.trade_id)
        assert t.notes == 'Updated notes'
        assert t.counterparty == 'New Client'

    def test_update_creates_new_version(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.update_trade('default', sample_trade.trade_id, {'notes': 'V2'})
        t = bm.get_trade('default', sample_trade.trade_id)
        assert t.current_version == 2
        assert len(t.versions) == 2

    def test_delete_trade_soft(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        result = bm.delete_trade('default', sample_trade.trade_id)
        assert result is True
        t = bm.get_trade('default', sample_trade.trade_id)
        assert t.status == TradeStatus.CANCELLED.value

    def test_delete_trade_hard(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.delete_trade('default', sample_trade.trade_id, force=True)
        with pytest.raises(KeyError):
            bm.get_trade('default', sample_trade.trade_id)

    def test_clone_trade(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        new_tid = bm.clone_trade('default', sample_trade.trade_id,
                                  modifications={'notes': 'Cloned trade'})
        cloned = bm.get_trade('default', new_tid)
        assert cloned.trade_id != sample_trade.trade_id
        assert cloned.notes == 'Cloned trade'
        assert cloned.product_type == sample_trade.product_type

    def test_add_multiple_trades(self, bm, sample_trade):
        import copy, uuid as _u
        for i in range(5):
            t = Trade.from_dict(copy.deepcopy(sample_trade.to_dict()))
            t.trade_id = str(_u.uuid4())[:12]
            t.internal_ref = ''
            bm.add_trade('default', t)
        book = bm.load_book('default')
        assert len(book.trades) == 5


# ═══════════════════════════════════════════════════════════════
# 3. TRADE ID GENERATION
# ═══════════════════════════════════════════════════════════════

class TestTradeIDGenerator:

    def test_id_format(self, bm):
        book = bm.load_book('default')
        tid = TradeIDGenerator.next_id('equity_index', book)
        year = datetime.utcnow().year
        assert tid == f"EQI-{year}-0001"

    def test_sequential_ids(self, bm, sample_trade):
        import copy, uuid as _u
        bm.add_trade('default', sample_trade)
        book = bm.load_book('default')
        tid2 = TradeIDGenerator.next_id('equity_index', book)
        year = datetime.utcnow().year
        assert tid2 == f"EQI-{year}-0002"

    def test_different_asset_class_prefix(self, bm):
        book = bm.load_book('default')
        fx_id = TradeIDGenerator.next_id('fx', book)
        year = datetime.utcnow().year
        assert fx_id.startswith(f"FX-{year}")

    def test_unknown_asset_class_uses_tr(self, bm):
        book = bm.load_book('default')
        tid = TradeIDGenerator.next_id('unknown', book)
        assert tid.startswith("TR-")


# ═══════════════════════════════════════════════════════════════
# 4. SEARCH & FILTER
# ═══════════════════════════════════════════════════════════════

class TestSearchFilter:

    def _add_trades(self, bm):
        import copy, uuid as _u
        trades = []
        configs = [
            {'status': 'live', 'product_type': 'autocall', 'notional': 1_000_000, 'counterparty': 'Client A', 'tags': ['sx5e']},
            {'status': 'live', 'product_type': 'phoenix', 'notional': 2_000_000, 'counterparty': 'Client B', 'tags': ['spx']},
            {'status': 'draft', 'product_type': 'vanilla_call', 'notional': 500_000, 'counterparty': 'Client A', 'tags': []},
            {'status': 'matured', 'product_type': 'autocall', 'notional': 3_000_000, 'counterparty': 'Client C', 'tags': ['sx5e', 'old']},
        ]
        for c in configs:
            t = Trade(
                trade_id=str(_u.uuid4())[:12],
                product_type=c['product_type'],
                notional=float(c['notional']),
                currency='EUR',
                counterparty=c['counterparty'],
                tags=c['tags'],
                underlyings=[{'ticker': 'TEST', 'asset_class': 'equity_index',
                              'spot_at_inception': 100, 'name': 'Test'}],
                total_pnl=1000.0 if c['status'] == 'live' else -500.0,
                trade_date='2026-01-15',
                maturity_date='2031-01-15',
                created_by='test',
            )
            t.status = c['status']
            bm.add_trade('default', t)
            trades.append(t)
        return trades

    def test_filter_by_status(self, bm):
        self._add_trades(bm)
        results = bm.search_trades('default', filters={'status': ['live']})
        assert all(t.status == 'live' for t in results)
        assert len(results) == 2

    def test_filter_by_product_type(self, bm):
        self._add_trades(bm)
        results = bm.search_trades('default', filters={
            'status': ['live', 'draft', 'matured'],
            'product_type': ['autocall']
        }, include_cancelled=True)
        assert all(t.product_type == 'autocall' for t in results)

    def test_filter_by_counterparty(self, bm):
        self._add_trades(bm)
        results = bm.search_trades('default', filters={
            'status': ['live', 'draft'],
            'counterparty': 'Client A'
        })
        assert all('Client A' in t.counterparty for t in results)

    def test_filter_by_notional_range(self, bm):
        self._add_trades(bm)
        results = bm.search_trades('default', filters={
            'status': ['live', 'draft'],
            'notional_min': 1_000_000,
            'notional_max': 2_500_000,
        })
        assert all(1_000_000 <= t.notional <= 2_500_000 for t in results)

    def test_filter_by_tags(self, bm):
        self._add_trades(bm)
        results = bm.search_trades('default', filters={
            'status': ['live', 'draft', 'matured'],
            'tags': ['sx5e']
        }, include_cancelled=True)
        assert all('sx5e' in t.tags for t in results)

    def test_filter_pnl_positive(self, bm):
        self._add_trades(bm)
        results = bm.search_trades('default', filters={
            'status': ['live'],
            'pnl_positive': True
        })
        assert all((t.total_pnl or 0) >= 0 for t in results)

    def test_text_search(self, bm):
        import uuid as _u
        t = Trade(
            trade_id=str(_u.uuid4())[:12],
            status='live',
            product_type='custom',
            product_name='Special Himalaya Note',
            notes='This is a himalaya structure for client xyz',
            underlyings=[],
            notional=1_000_000,
            currency='EUR',
            created_by='test'
        )
        bm.add_trade('default', t)
        results = bm.search_trades('default', filters={'text_search': 'himalaya'})
        assert any('himalaya' in (r.product_name + r.notes).lower() for r in results)

    def test_empty_filters_returns_all_live(self, bm):
        self._add_trades(bm)
        results = bm.search_trades('default')
        # Only live and draft by default (not matured/cancelled)
        for t in results:
            assert t.status not in ('cancelled', 'expired')

    def test_combined_filters(self, bm):
        self._add_trades(bm)
        results = bm.search_trades('default', filters={
            'status': ['live'],
            'product_type': ['autocall'],
            'counterparty': 'Client A',
        })
        for t in results:
            assert t.status == 'live'
            assert t.product_type == 'autocall'
            assert 'Client A' in t.counterparty


# ═══════════════════════════════════════════════════════════════
# 5. BOOK METRICS
# ═══════════════════════════════════════════════════════════════

class TestBookMetrics:

    def _setup_book(self, bm):
        import uuid as _u
        for i in range(3):
            t = Trade(
                trade_id=str(_u.uuid4())[:12],
                status='live',
                product_type='autocall',
                notional=1_000_000.0 * (i + 1),
                currency='EUR',
                total_pnl=50_000.0 * (i + 1),
                current_mtm=1_000_000.0 * (i + 1),
                unrealized_pnl=50_000.0 * (i + 1),
                realized_pnl=0.0,
                underlyings=[{'ticker': f'TICK{i}', 'asset_class': 'equity_index',
                               'spot_at_inception': 100, 'name': f'Tick {i}'}],
                current_pricing=PricingResult(
                    timestamp=datetime.utcnow().isoformat(),
                    model='bs', price=100.0, price_currency='EUR',
                    notional_value=1e6 * (i+1),
                    delta=-0.5, vega=10.0, theta=-1.0, gamma=0.01, rho=-2.0
                ).to_dict(),
                created_by='test',
            )
            bm.add_trade('default', t)

    def test_total_notional(self, bm):
        self._setup_book(bm)
        metrics = bm.compute_book_metrics('default')
        assert metrics['total_notional'] == 6_000_000.0

    def test_live_trade_count(self, bm):
        self._setup_book(bm)
        metrics = bm.compute_book_metrics('default')
        assert metrics['live_trades'] == 3

    def test_total_pnl(self, bm):
        self._setup_book(bm)
        metrics = bm.compute_book_metrics('default')
        assert metrics['total_pnl'] == pytest.approx(300_000.0)

    def test_aggregate_greeks(self, bm):
        self._setup_book(bm)
        metrics = bm.compute_book_metrics('default')
        assert metrics['aggregate_delta'] == pytest.approx(-1.5, abs=0.01)
        assert metrics['aggregate_vega'] == pytest.approx(30.0, abs=0.01)

    def test_empty_book_metrics(self, bm):
        metrics = bm.compute_book_metrics('default')
        assert metrics['total_trades'] == 0
        assert metrics['total_notional'] == 0.0
        assert metrics['total_pnl'] == 0.0

    def test_maturity_profile(self, bm):
        import uuid as _u
        today = date.today()
        for bucket, days in [('<1Y', 180), ('1-2Y', 400), ('5Y+', 2000)]:
            mat = (today + timedelta(days=days)).isoformat()
            t = Trade(
                trade_id=str(_u.uuid4())[:12],
                status='live',
                product_type='autocall',
                notional=1_000_000.0,
                currency='EUR',
                maturity_date=mat,
                underlyings=[],
                created_by='test',
            )
            bm.add_trade('default', t)
        metrics = bm.compute_book_metrics('default')
        mp = metrics['maturity_profile']
        assert mp['<1Y'] == 1_000_000.0
        assert mp['1-2Y'] == 1_000_000.0
        assert mp['5Y+'] == 1_000_000.0


# ═══════════════════════════════════════════════════════════════
# 6. REPRICING
# ═══════════════════════════════════════════════════════════════

class TestRepricing:

    def test_reprice_trade_vanilla_call(self, bm):
        import uuid as _u
        t = Trade(
            trade_id=str(_u.uuid4())[:12],
            status='live',
            product_type='vanilla_call',
            notional=1_000_000.0,
            currency='USD',
            entry_price=5.0,
            current_mtm=50_000.0,
            underlyings=[{'ticker': 'AAPL', 'asset_class': 'equity',
                           'spot_at_inception': 200.0, 'name': 'Apple'}],
            strike_pct=100.0,
            tenor_years=1.0,
            inception_rate=0.035,
            inception_vols={'AAPL': 0.25},
            inception_spots={'AAPL': 200.0},
            created_by='test',
        )
        bm.add_trade('default', t)
        market_data = {
            'spots': {'AAPL': 210.0},
            'vols': {'AAPL': 0.25},
            'rate': 0.035,
            'div_yields': {'AAPL': 0.005},
        }
        result = bm.reprice_trade('default', t.trade_id, market_data=market_data)
        assert result.price > 0
        assert result.delta is not None
        assert 0 < result.delta < 1  # Call delta between 0 and 1

    def test_reprice_updates_mtm(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        market_data = {
            'spots': {'^STOXX50E': 5800.0},
            'vols': {'^STOXX50E': 0.22},
            'rate': 0.035,
            'div_yields': {'^STOXX50E': 0.03},
        }
        # Override with custom pricer that returns a fixed price
        def mock_pricer(trade, mkt):
            return PricingResult(
                timestamp=datetime.utcnow().isoformat(),
                model='mock',
                price=97.0,
                price_currency=trade.currency,
                notional_value=970_000.0,
                delta=-0.40,
            )
        bm.pricer = mock_pricer
        result = bm.reprice_trade('default', sample_trade.trade_id, market_data=market_data)
        t = bm.get_trade('default', sample_trade.trade_id)
        assert t.current_mtm == pytest.approx(970_000.0)
        assert t.unrealized_pnl == pytest.approx(970_000.0 - 987_500.0)

    def test_reprice_adds_to_history(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        market_data = {'spots': {'^STOXX50E': 5800.0}, 'vols': {'^STOXX50E': 0.22},
                       'rate': 0.035, 'div_yields': {'^STOXX50E': 0.03}}

        def mock_pricer(trade, mkt):
            return PricingResult(timestamp=datetime.utcnow().isoformat(),
                                  model='mock', price=96.0, price_currency='EUR',
                                  notional_value=960_000.0)
        bm.pricer = mock_pricer

        for _ in range(3):
            bm.reprice_trade('default', sample_trade.trade_id, market_data=market_data)

        t = bm.get_trade('default', sample_trade.trade_id)
        assert len(t.pricing_history) == 3  # Initial pricing + 3 reprices... actually just 3

    def test_reprice_book_all_live(self, bm, sample_trade):
        import copy, uuid as _u
        for i in range(3):
            tc = Trade.from_dict(copy.deepcopy(sample_trade.to_dict()))
            tc.trade_id = str(_u.uuid4())[:12]
            tc.internal_ref = ''
            tc.product_type = 'vanilla_call'  # So default BS pricer handles it
            bm.add_trade('default', tc)

        market_data = {'spots': {'^STOXX50E': 5800.0}, 'vols': {'^STOXX50E': 0.22},
                       'rate': 0.035, 'div_yields': {'^STOXX50E': 0.03}}
        result = bm.reprice_book('default', market_data=market_data)
        assert result['repriced_count'] == 3
        assert result['failed_count'] == 0


# ═══════════════════════════════════════════════════════════════
# 7. SNAPSHOTS
# ═══════════════════════════════════════════════════════════════

class TestSnapshots:

    def test_take_snapshot(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        path = bm.take_snapshot('default')
        assert Path(path).exists()

    def test_load_snapshot(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.take_snapshot('default')
        today = date.today().isoformat()
        snap = bm.load_snapshot('default', today)
        assert snap is not None
        assert snap.book_id == 'default'
        assert snap.date == today

    def test_list_snapshots(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.take_snapshot('default')
        snaps = bm.list_snapshots('default')
        assert len(snaps) >= 1

    def test_snapshot_contains_metrics(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.take_snapshot('default')
        today = date.today().isoformat()
        snap = bm.load_snapshot('default', today)
        assert 'total_trades' in snap.book_metrics
        assert 'total_notional' in snap.book_metrics

    def test_historical_pnl_with_snapshots(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.take_snapshot('default')
        history = bm.compute_historical_pnl('default')
        assert len(history) >= 1


# ═══════════════════════════════════════════════════════════════
# 8. TEMPLATES
# ═══════════════════════════════════════════════════════════════

class TestTemplates:

    def test_save_and_load_template(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.save_as_template('default', sample_trade.trade_id, '5Y Autocall SX5E')
        tpl = bm.load_template('5Y Autocall SX5E')
        assert tpl is not None
        assert tpl['product_type'] == 'autocall'

    def test_list_templates(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.save_as_template('default', sample_trade.trade_id, 'My Template')
        templates = bm.list_templates()
        assert any(t['template_name'] == 'My Template' for t in templates)

    def test_delete_template(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.save_as_template('default', sample_trade.trade_id, 'Delete Me')
        bm.delete_template('Delete Me')
        assert bm.load_template('Delete Me') is None

    def test_create_trade_from_template(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.save_as_template('default', sample_trade.trade_id, '5Y Autocall Standard')
        new_trade = bm.create_trade_from_template(
            '5Y Autocall Standard',
            underlyings=[{'ticker': '^GSPC', 'name': 'S&P 500',
                           'asset_class': 'equity_index',
                           'spot_at_inception': 5000.0, 'currency': 'USD'}],
            notional=2_000_000.0,
        )
        assert new_trade.product_type == 'autocall'
        assert new_trade.notional == 2_000_000.0
        assert new_trade.underlyings[0]['ticker'] == '^GSPC'

    def test_template_overrides(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.save_as_template('default', sample_trade.trade_id, 'Override Test')
        new_trade = bm.create_trade_from_template(
            'Override Test',
            underlyings=[{'ticker': 'SPY', 'name': 'S&P', 'asset_class': 'equity_index',
                           'spot_at_inception': 500.0, 'currency': 'USD'}],
            notional=500_000.0,
            overrides={'tenor_years': 3.0, 'strike_pct': 95.0}
        )
        assert new_trade.tenor_years == 3.0
        assert new_trade.strike_pct == 95.0

    def test_load_nonexistent_template(self, bm):
        assert bm.load_template('Nonexistent') is None


# ═══════════════════════════════════════════════════════════════
# 9. VERSIONING
# ═══════════════════════════════════════════════════════════════

class TestVersioning:

    def test_initial_trade_is_v1(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        t = bm.get_trade('default', sample_trade.trade_id)
        assert t.current_version == 1
        assert len(t.versions) == 1

    def test_update_creates_v2(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        bm.update_trade('default', sample_trade.trade_id,
                         {'notes': 'V2 notes'}, change_description='V2 update')
        t = bm.get_trade('default', sample_trade.trade_id)
        assert t.current_version == 2
        assert t.versions[1]['version'] == 2
        assert t.versions[1]['change_description'] == 'V2 update'

    def test_multiple_versions(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        for i in range(4):
            bm.update_trade('default', sample_trade.trade_id,
                             {'notes': f'Update {i}'}, change_description=f'Change {i}')
        t = bm.get_trade('default', sample_trade.trade_id)
        assert t.current_version == 5
        assert len(t.versions) == 5

    def test_version_preserves_params(self, bm, sample_trade):
        sample_trade.strike_pct = 100.0
        bm.add_trade('default', sample_trade)
        bm.update_trade('default', sample_trade.trade_id, {'strike_pct': 105.0})
        t = bm.get_trade('default', sample_trade.trade_id)
        # V1 should have strike_pct=100, V2 should have 105
        assert t.versions[0]['parameters']['strike_pct'] == 100.0
        assert t.versions[1]['parameters']['strike_pct'] == 105.0


# ═══════════════════════════════════════════════════════════════
# 10. BLACK-SCHOLES PRICER
# ═══════════════════════════════════════════════════════════════

class TestBlackScholes:

    def test_call_price_positive(self):
        price, delta, gamma, vega, theta, rho = _bs_greeks(100, 100, 1, 0.05, 0.2)
        assert price > 0

    def test_call_delta_between_0_and_1(self):
        _, delta, *_ = _bs_greeks(100, 100, 1, 0.05, 0.2, is_call=True)
        assert 0 < delta < 1

    def test_put_delta_between_minus1_and_0(self):
        _, delta, *_ = _bs_greeks(100, 100, 1, 0.05, 0.2, is_call=False)
        assert -1 < delta < 0

    def test_put_call_parity(self):
        S, K, T, r, sigma = 100, 100, 1, 0.05, 0.2
        call_pct, *_ = _bs_greeks(S, K, T, r, sigma, is_call=True)
        put_pct, *_ = _bs_greeks(S, K, T, r, sigma, is_call=False)
        # C - P = S - K*e^(-rT)
        call_price = call_pct / 100 * S
        put_price = put_pct / 100 * S
        import math
        expected = S - K * math.exp(-r * T)
        assert abs(call_price - put_price - expected) < 0.01

    def test_zero_tenor_returns_zero(self):
        price, *_ = _bs_greeks(100, 100, 0.0, 0.05, 0.2)
        assert price == 0.0

    def test_deep_itm_call_delta_near_1(self):
        _, delta, *_ = _bs_greeks(200, 100, 1, 0.05, 0.2, is_call=True)
        assert delta > 0.95

    def test_deep_otm_call_delta_near_0(self):
        _, delta, *_ = _bs_greeks(50, 100, 1, 0.05, 0.2, is_call=True)
        assert delta < 0.05


# ═══════════════════════════════════════════════════════════════
# 11. EXPORT
# ═══════════════════════════════════════════════════════════════

class TestExport:

    def test_export_csv_bytes(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        book = bm.load_book('default')
        from tradebook_export import TradeBookExporter
        exp = TradeBookExporter()
        csv_bytes = exp.export_csv_bytes(book)
        assert len(csv_bytes) > 0
        text = csv_bytes.decode('utf-8')
        assert 'ref' in text  # header

    def test_export_excel_creates_file(self, bm, sample_trade, tmp_dir):
        try:
            import openpyxl
        except ImportError:
            pytest.skip("openpyxl not installed")
        bm.add_trade('default', sample_trade)
        book = bm.load_book('default')
        from tradebook_export import TradeBookExporter
        exp = TradeBookExporter()
        path = os.path.join(tmp_dir, 'test.xlsx')
        result = exp.export_book_to_excel(book, filepath=path)
        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    def test_export_pdf_creates_file(self, bm, sample_trade, tmp_dir):
        try:
            from reportlab.lib.pagesizes import A4
        except ImportError:
            pytest.skip("reportlab not installed")
        bm.add_trade('default', sample_trade)
        trade = bm.get_trade('default', sample_trade.trade_id)
        from tradebook_export import TradeBookExporter
        exp = TradeBookExporter()
        path = os.path.join(tmp_dir, 'test.pdf')
        result = exp.export_trade_to_pdf(trade, filepath=path)
        assert Path(result).exists()
        assert Path(result).stat().st_size > 0

    def test_export_blotter_to_csv_file(self, bm, sample_trade, tmp_dir):
        bm.add_trade('default', sample_trade)
        book = bm.load_book('default')
        from tradebook_export import TradeBookExporter
        exp = TradeBookExporter()
        path = os.path.join(tmp_dir, 'blotter.csv')
        result = exp.export_blotter_to_csv(book, filepath=path)
        assert Path(result).exists()


# ═══════════════════════════════════════════════════════════════
# 12. EDGE CASES
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_corrupted_json_falls_back_to_bak(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        # Corrupt the main JSON file
        book_path = bm.books_dir / 'default.json'
        bak_path = book_path.with_suffix('.bak')
        # Save a .bak
        shutil.copy2(book_path, bak_path)
        # Corrupt main
        with open(book_path, 'w') as f:
            f.write("INVALID JSON {{{{")
        # Should fall back to .bak
        book = bm.load_book('default')
        assert book is not None

    def test_empty_book_metrics(self, bm):
        metrics = bm.compute_book_metrics('default')
        assert metrics['total_trades'] == 0
        assert metrics['live_trades'] == 0

    def test_trade_without_pricing(self, bm):
        import uuid as _u
        t = Trade(
            trade_id=str(_u.uuid4())[:12],
            status='draft',
            product_type='custom',
            notional=500_000.0,
            currency='USD',
            underlyings=[],
            created_by='test',
        )
        tid = bm.add_trade('default', t)
        fetched = bm.get_trade('default', tid)
        assert fetched.get_current_pricing() is None

    def test_trade_serialization_roundtrip(self, sample_trade):
        d = sample_trade.to_dict()
        restored = Trade.from_dict(d)
        assert restored.trade_id == sample_trade.trade_id
        assert restored.product_type == sample_trade.product_type
        assert restored.notional == sample_trade.notional
        assert restored.barriers == sample_trade.barriers

    def test_pricing_result_roundtrip(self, sample_pricing):
        d = sample_pricing.to_dict()
        restored = PricingResult.from_dict(d)
        assert restored.price == sample_pricing.price
        assert restored.delta == sample_pricing.delta

    def test_build_trade_from_pricing(self, sample_pricing):
        trade = build_trade_from_pricing(
            product_type='vanilla_call',
            product_name='Test Call',
            underlyings=[{'ticker': 'AAPL', 'name': 'Apple', 'asset_class': 'equity',
                           'spot_at_inception': 200.0, 'currency': 'USD'}],
            notional=500_000.0,
            currency='USD',
            pricing_result=sample_pricing,
            tenor_years=1.0,
        )
        assert trade.entry_price == sample_pricing.price
        assert trade.current_mtm == sample_pricing.notional_value
        assert trade.status == 'live'

    def test_import_export_book_json(self, bm, sample_trade):
        bm.add_trade('default', sample_trade)
        data = bm.export_book_json('default')
        assert 'trades' in data
        assert len(data['trades']) == 1

        imported = bm.import_book_json(data, new_name='Imported')
        assert imported.name == 'Imported'
        assert len(imported.trades) == 1

    def test_reprice_nonexistent_trade_raises(self, bm):
        with pytest.raises(KeyError):
            bm.reprice_trade('default', 'nonexistent_id')
