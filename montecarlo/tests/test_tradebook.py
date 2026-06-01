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
from datetime import datetime, date, timedelta, timezone
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
        timestamp=datetime.now(timezone.utc).isoformat(),
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
# TEST BASIC FUNCTIONALITY
# ═══════════════════════════════════════════════════════════════

class TestBasicFunctionality:

    def test_sample_trade_creation(self, sample_trade):
        assert sample_trade.notional == 1_000_000.0
        assert sample_trade.product_type == 'autocall'

    def test_pricing_result_to_dict(self, sample_pricing):
        d = sample_pricing.to_dict()
        assert isinstance(d, dict)
        assert d['price'] == 98.75
