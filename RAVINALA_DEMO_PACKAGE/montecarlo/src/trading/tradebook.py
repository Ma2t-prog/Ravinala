"""
tradebook.py — BookManager: full backend for the Ravinala Trade Book.
Handles CRUD, search, analytics, repricing, snapshots, templates.
Storage: JSON files in data/tradebook/ (atomic writes, .bak backups).
"""

import json
import gzip
import shutil
import re
import math
import threading
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

from tradebook_models import (
    Trade, Book, DailySnapshot, PricingResult,
    TradeVersion, TradeStatus, ASSET_PREFIXES
)


# ═══════════════════════════════════════════════════════════════
# TRADE ID GENERATOR
# ═══════════════════════════════════════════════════════════════

class TradeIDGenerator:
    """
    Generates readable sequential trade IDs.
    Format: {ASSET_PREFIX}-{YEAR}-{SEQ:04d}
    e.g. EQI-2026-0001, FX-2026-0042
    """

    @staticmethod
    def next_id(asset_class: str, book: Book) -> str:
        prefix = ASSET_PREFIXES.get(asset_class, 'TR')
        year = datetime.utcnow().year
        pattern = re.compile(rf'^{re.escape(prefix)}-{year}-(\d+)$')

        max_seq = 0
        for t_dict in book.trades:
            ref = t_dict.get('internal_ref', '')
            m = pattern.match(ref)
            if m:
                max_seq = max(max_seq, int(m.group(1)))

        return f"{prefix}-{year}-{max_seq + 1:04d}"


# ═══════════════════════════════════════════════════════════════
# BOOK MANAGER
# ═══════════════════════════════════════════════════════════════

class BookManager:
    """
    Manages all book/trade operations. Pure Python — no Streamlit dependency.

    Directory layout:
        data/tradebook/
            books/         → one JSON per book
            snapshots/     → YYYY-MM-DD/ subdirs
            templates/     → one JSON per template
            archive/       → deleted books/trades
    """

    MAX_REPRICE_WORKERS = 10

    def __init__(self, data_dir: str = 'data/tradebook',
                 pricer: Optional[Callable] = None):
        """
        pricer : optional callable(trade: Trade, market_data: dict) → PricingResult
                 If None, a built-in Black-Scholes pricer is used for vanilla
                 options, and last-known price is kept for complex structures.
        """
        self.root = Path(data_dir)
        self.books_dir = self.root / 'books'
        self.snapshots_dir = self.root / 'snapshots'
        self.templates_dir = self.root / 'templates'
        self.archive_dir = self.root / 'archive'

        for d in [self.books_dir, self.snapshots_dir,
                  self.templates_dir, self.archive_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.pricer = pricer or self._default_pricer
        self._file_lock = threading.Lock()
        self._ensure_default_book()

    # ─────────────────────────────────────────────────────────
    # JSON I/O helpers
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _write_json(path: Path, data: dict) -> None:
        """Atomic write: unique .tmp → rename. Creates .bak before overwriting."""
        import uuid as _u
        path = Path(path)
        if path.exists():
            shutil.copy2(path, path.with_suffix('.bak'))
        tmp = path.with_name(f"{path.stem}_{_u.uuid4().hex[:8]}.tmp")
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        tmp.replace(path)

    @staticmethod
    def _read_json(path: Path) -> Optional[dict]:
        """Read JSON. On corruption, try .bak. Returns None if both fail."""
        path = Path(path)
        for try_path in [path, path.with_suffix('.bak')]:
            if try_path.exists():
                try:
                    with open(try_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except (json.JSONDecodeError, OSError):
                    continue
        return None

    @staticmethod
    def _write_json_gz(path: Path, data: dict) -> None:
        """Write gzip-compressed JSON (for large snapshots)."""
        path = Path(path)
        tmp = path.with_suffix('.tmp')
        with gzip.open(tmp, 'wt', encoding='utf-8') as f:
            json.dump(data, f, default=str)
        tmp.replace(path)

    @staticmethod
    def _read_json_gz(path: Path) -> Optional[dict]:
        path = Path(path)
        if not path.exists():
            return None
        try:
            with gzip.open(path, 'rt', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def _book_path(self, book_id: str) -> Path:
        return self.books_dir / f"{book_id}.json"

    # ─────────────────────────────────────────────────────────
    # Default book init
    # ─────────────────────────────────────────────────────────

    def _ensure_default_book(self):
        default_path = self._book_path('default')
        if not default_path.exists():
            self.create_book(
                name='Default Book',
                description='Main trading book',
                currency='EUR',
                created_by='system',
                book_id='default'
            )

    # ─────────────────────────────────────────────────────────
    # BOOKS CRUD
    # ─────────────────────────────────────────────────────────

    def create_book(self, name: str, description: str = '',
                    currency: str = 'EUR', created_by: str = '',
                    book_id: str = None) -> Book:
        book = Book(
            book_id=book_id or Book.__dataclass_fields__['book_id'].default_factory(),
            name=name,
            description=description,
            created_at=datetime.utcnow().isoformat(),
            created_by=created_by,
            currency=currency,
            trades=[]
        )
        self._write_json(self._book_path(book.book_id), book.to_dict())
        return book

    def list_books(self) -> list:
        result = []
        for f in sorted(self.books_dir.glob('*.json')):
            data = self._read_json(f)
            if data:
                result.append({
                    'book_id': data.get('book_id', f.stem),
                    'name': data.get('name', '?'),
                    'description': data.get('description', ''),
                    'currency': data.get('currency', 'EUR'),
                    'trade_count': len(data.get('trades', [])),
                    'created_at': data.get('created_at', ''),
                    'created_by': data.get('created_by', ''),
                })
        return result

    def load_book(self, book_id: str) -> Book:
        data = self._read_json(self._book_path(book_id))
        if data is None:
            raise FileNotFoundError(f"Book '{book_id}' not found.")
        return Book.from_dict(data)

    def save_book(self, book: Book) -> None:
        with self._file_lock:
            self._write_json(self._book_path(book.book_id), book.to_dict())

    def delete_book(self, book_id: str, force: bool = False) -> bool:
        if book_id == 'default' and not force:
            return False
        path = self._book_path(book_id)
        if not path.exists():
            return False
        archive_path = self.archive_dir / f"book_{book_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy2(path, archive_path)
        path.unlink()
        bak = path.with_suffix('.bak')
        if bak.exists():
            bak.unlink()
        return True

    def duplicate_book(self, book_id: str, new_name: str) -> Book:
        original = self.load_book(book_id)
        import uuid as _uuid
        new_id = str(_uuid.uuid4())[:8]
        new_book = Book(
            book_id=new_id,
            name=new_name,
            description=f"Copy of {original.name}",
            created_at=datetime.utcnow().isoformat(),
            currency=original.currency,
            trades=[]  # Deep copy trades with new IDs
        )
        import copy
        for t_dict in original.trades:
            import uuid as _u
            t_copy = copy.deepcopy(t_dict)
            t_copy['trade_id'] = str(_u.uuid4())[:12]
            t_copy['internal_ref'] = ''   # Will be reassigned on next add
            new_book.trades.append(t_copy)
        self.save_book(new_book)
        return new_book

    # ─────────────────────────────────────────────────────────
    # TRADES CRUD
    # ─────────────────────────────────────────────────────────

    def add_trade(self, book_id: str, trade: Trade) -> str:
        book = self.load_book(book_id)

        # Auto-assign internal_ref if missing
        if not trade.internal_ref:
            asset_class = 'custom'
            if trade.underlyings:
                asset_class = trade.underlyings[0].get('asset_class', 'custom')
            trade.internal_ref = TradeIDGenerator.next_id(asset_class, book)

        # Set metadata
        now = datetime.utcnow().isoformat()
        if not trade.created_at:
            trade.created_at = now
        if not trade.trade_date:
            trade.trade_date = datetime.utcnow().date().isoformat()
        trade.updated_at = now

        # First version
        trade.current_version = 1
        v1 = TradeVersion(
            version=1,
            created_at=now,
            created_by=trade.created_by or 'user',
            change_description='Initial trade',
            parameters=self._extract_params(trade),
            pricing_result=trade.current_pricing,
        )
        trade.versions = [v1.to_dict()]

        # Audit
        trade.add_audit(trade.created_by or 'user', 'CREATED', f'Ref: {trade.internal_ref}')

        book.trades.append(trade.to_dict())
        self.save_book(book)
        return trade.trade_id

    def update_trade(self, book_id: str, trade_id: str,
                     updates: dict, updated_by: str = 'user',
                     change_description: str = '') -> bool:
        book = self.load_book(book_id)
        idx = self._find_trade_idx(book, trade_id)
        if idx < 0:
            return False

        trade = Trade.from_dict(book.trades[idx])
        old_params = self._extract_params(trade)

        # Apply updates
        for key, val in updates.items():
            if hasattr(trade, key):
                setattr(trade, key, val)

        # New version
        trade.current_version += 1
        new_version = TradeVersion(
            version=trade.current_version,
            created_at=datetime.utcnow().isoformat(),
            created_by=updated_by,
            change_description=change_description or f'Version {trade.current_version}',
            parameters=self._extract_params(trade),
            pricing_result=trade.current_pricing,
        )
        trade.versions.append(new_version.to_dict())

        trade.updated_at = datetime.utcnow().isoformat()
        trade.add_audit(updated_by, 'UPDATED', change_description)

        book.trades[idx] = trade.to_dict()
        self.save_book(book)
        return True

    def delete_trade(self, book_id: str, trade_id: str,
                     deleted_by: str = 'user', force: bool = False) -> bool:
        book = self.load_book(book_id)
        idx = self._find_trade_idx(book, trade_id)
        if idx < 0:
            return False

        if force:
            del book.trades[idx]
        else:
            # Soft delete
            trade = Trade.from_dict(book.trades[idx])
            trade.status = TradeStatus.CANCELLED.value
            trade.updated_at = datetime.utcnow().isoformat()
            trade.add_audit(deleted_by, 'CANCELLED', 'Soft delete')
            book.trades[idx] = trade.to_dict()

        self.save_book(book)
        return True

    def get_trade(self, book_id: str, trade_id: str) -> Trade:
        book = self.load_book(book_id)
        idx = self._find_trade_idx(book, trade_id)
        if idx < 0:
            raise KeyError(f"Trade '{trade_id}' not found in book '{book_id}'.")
        return Trade.from_dict(book.trades[idx])

    def clone_trade(self, book_id: str, trade_id: str,
                    modifications: dict = None, cloned_by: str = 'user') -> str:
        import copy, uuid as _u
        original = self.get_trade(book_id, trade_id)
        clone = Trade.from_dict(copy.deepcopy(original.to_dict()))

        clone.trade_id = str(_u.uuid4())[:12]
        clone.internal_ref = ''   # Will be assigned by add_trade
        clone.created_at = ''
        clone.trade_date = ''
        clone.status = TradeStatus.DRAFT.value
        clone.versions = []
        clone.audit_trail = []
        clone.created_by = cloned_by
        clone.notes = f"[Clone of {original.internal_ref}] {original.notes}"

        if modifications:
            for k, v in modifications.items():
                if hasattr(clone, k):
                    setattr(clone, k, v)

        return self.add_trade(book_id, clone)

    # ─────────────────────────────────────────────────────────
    # SEARCH & FILTER
    # ─────────────────────────────────────────────────────────

    def search_trades(self, book_id: str, filters: dict = None,
                      sort_by: str = 'trade_date',
                      sort_desc: bool = True,
                      include_cancelled: bool = False) -> list:
        book = self.load_book(book_id)
        trades = [Trade.from_dict(t) for t in book.trades]

        # Default: hide cancelled
        if not include_cancelled:
            default_excl = {TradeStatus.CANCELLED.value, TradeStatus.EXPIRED.value}
        else:
            default_excl = set()

        if filters is None:
            filters = {}

        result = []
        for t in trades:
            if t.status in default_excl:
                continue
            if not self._trade_matches(t, filters):
                continue
            result.append(t)

        # Sort
        def sort_key(t):
            v = getattr(t, sort_by, '') or ''
            return v

        result.sort(key=sort_key, reverse=sort_desc)
        return result

    def _trade_matches(self, trade: Trade, filters: dict) -> bool:
        f = filters

        if 'status' in f and f['status']:
            if trade.status not in f['status']:
                return False

        if 'product_type' in f and f['product_type']:
            if trade.product_type not in f['product_type']:
                return False

        if 'asset_class' in f and f['asset_class']:
            acs = {u.get('asset_class', '') for u in trade.underlyings}
            if not acs.intersection(set(f['asset_class'])):
                return False

        if 'counterparty' in f and f['counterparty']:
            if f['counterparty'].lower() not in trade.counterparty.lower():
                return False

        if 'underlying_ticker' in f and f['underlying_ticker']:
            tickers = {u.get('ticker', '') for u in trade.underlyings}
            if f['underlying_ticker'].upper() not in tickers:
                return False

        if 'trade_date_from' in f and f['trade_date_from']:
            if trade.trade_date < f['trade_date_from']:
                return False

        if 'trade_date_to' in f and f['trade_date_to']:
            if trade.trade_date > f['trade_date_to']:
                return False

        if 'maturity_from' in f and f['maturity_from']:
            if trade.maturity_date and trade.maturity_date < f['maturity_from']:
                return False

        if 'maturity_to' in f and f['maturity_to']:
            if trade.maturity_date and trade.maturity_date > f['maturity_to']:
                return False

        if 'notional_min' in f and f['notional_min'] is not None:
            if trade.notional < f['notional_min']:
                return False

        if 'notional_max' in f and f['notional_max'] is not None:
            if trade.notional > f['notional_max']:
                return False

        if 'tags' in f and f['tags']:
            req_tags = set(f['tags'])
            trade_tags = set(trade.tags)
            if not req_tags.intersection(trade_tags):
                return False

        if 'pnl_positive' in f and f['pnl_positive'] is not None:
            pnl = trade.total_pnl
            if pnl is None:
                return False
            if f['pnl_positive'] and pnl < 0:
                return False
            if not f['pnl_positive'] and pnl >= 0:
                return False

        if 'text_search' in f and f['text_search']:
            q = f['text_search'].lower()
            searchable = ' '.join([
                trade.product_name, trade.counterparty,
                trade.internal_ref, trade.notes,
                ' '.join(trade.tags),
            ]).lower()
            if q not in searchable:
                return False

        return True

    # ─────────────────────────────────────────────────────────
    # BOOK ANALYTICS
    # ─────────────────────────────────────────────────────────

    def compute_book_metrics(self, book_id: str) -> dict:
        book = self.load_book(book_id)
        trades = [Trade.from_dict(t) for t in book.trades]
        live = [t for t in trades if t.status == TradeStatus.LIVE.value]
        draft = [t for t in trades if t.status == TradeStatus.DRAFT.value]
        matured = [t for t in trades if t.status == TradeStatus.MATURED.value]

        # Notional aggregation
        total_notional = sum(t.notional for t in live)
        by_currency: dict = {}
        by_ac: dict = {}
        by_pt: dict = {}

        for t in live:
            by_currency[t.currency] = by_currency.get(t.currency, 0) + t.notional
            for u in t.underlyings:
                ac = u.get('asset_class', 'unknown')
                by_ac[ac] = by_ac.get(ac, 0) + t.notional
            pt = t.product_type
            by_pt[pt] = by_pt.get(pt, 0) + t.notional

        # P&L
        total_unrealized = sum(t.unrealized_pnl or 0 for t in live)
        total_realized = sum(t.realized_pnl or 0 for t in live)
        total_pnl = total_unrealized + total_realized
        total_mtm = sum(t.current_mtm or (t.entry_price / 100 * t.notional if t.entry_price else 0)
                        for t in live)

        # Aggregate Greeks (notional-weighted)
        def agg_greek(name):
            s = 0.0
            for t in live:
                pr = t.get_current_pricing()
                if pr:
                    val = getattr(pr, name, None)
                    if val is not None:
                        s += val
            return round(s, 6)

        # Risk
        var_95 = sum((t.var_95_1d or 0) for t in live)
        largest = max(live, key=lambda t: t.notional, default=None)
        most_loss = min(live, key=lambda t: (t.total_pnl or 0), default=None)

        # Concentration by underlying
        conc: dict = {}
        for t in live:
            for u in t.underlyings:
                tk = u.get('ticker', '?')
                conc[tk] = conc.get(tk, 0) + t.notional
        top5 = sorted(conc.items(), key=lambda x: x[1], reverse=True)[:5]

        # Maturity profile
        mp = {'<1Y': 0, '1-2Y': 0, '2-3Y': 0, '3-5Y': 0, '5Y+': 0}
        today = date.today().isoformat()
        for t in live:
            if t.maturity_date:
                try:
                    from datetime import date as _date
                    mat = _date.fromisoformat(t.maturity_date)
                    tod = _date.fromisoformat(today)
                    yrs = (mat - tod).days / 365.25
                    if yrs < 1:
                        mp['<1Y'] += t.notional
                    elif yrs < 2:
                        mp['1-2Y'] += t.notional
                    elif yrs < 3:
                        mp['2-3Y'] += t.notional
                    elif yrs < 5:
                        mp['3-5Y'] += t.notional
                    else:
                        mp['5Y+'] += t.notional
                except Exception:
                    pass

        return {
            'total_trades': len(trades),
            'live_trades': len(live),
            'draft_trades': len(draft),
            'matured_trades': len(matured),
            'total_notional': total_notional,
            'total_notional_by_currency': by_currency,
            'total_notional_by_asset_class': by_ac,
            'total_notional_by_product_type': by_pt,
            'total_mtm': total_mtm,
            'total_unrealized_pnl': total_unrealized,
            'total_realized_pnl': total_realized,
            'total_pnl': total_pnl,
            'aggregate_delta': agg_greek('delta'),
            'aggregate_gamma': agg_greek('gamma'),
            'aggregate_vega': agg_greek('vega'),
            'aggregate_theta': agg_greek('theta'),
            'aggregate_rho': agg_greek('rho'),
            'portfolio_var_95': var_95,
            'largest_exposure': {
                'ref': largest.internal_ref, 'notional': largest.notional
            } if largest else {},
            'largest_loss': {
                'ref': most_loss.internal_ref,
                'pnl': most_loss.total_pnl
            } if most_loss else {},
            'concentration': dict(top5),
            'maturity_profile': mp,
        }

    def compute_pnl_attribution(self, book_id: str) -> dict:
        book = self.load_book(book_id)
        live = [Trade.from_dict(t) for t in book.trades
                if t.get('status') == TradeStatus.LIVE.value]

        delta_pnl = vega_pnl = theta_pnl = rho_pnl = 0.0
        total_pnl = sum((t.total_pnl or 0) for t in live)

        for t in live:
            pr = t.get_current_pricing()
            if pr and pr.delta is not None:
                # Approximate contributions (simplified)
                for u in t.underlyings:
                    s0 = u.get('spot_at_inception', 0)
                    sc = u.get('current_spot') or s0
                    if s0 and pr.delta:
                        delta_pnl += pr.delta * (sc - s0) * t.notional / (s0 or 1) / 100
            if pr and pr.theta is not None:
                theta_pnl += pr.theta * (t.tenor_years * 365 if t.tenor_years else 0)
            if pr and pr.vega is not None:
                vega_pnl += pr.vega  # simplified
            if pr and pr.rho is not None:
                rho_pnl += pr.rho

        unexplained = total_pnl - (delta_pnl + vega_pnl + theta_pnl + rho_pnl)

        return {
            'delta_pnl': round(delta_pnl, 2),
            'gamma_pnl': 0.0,
            'vega_pnl': round(vega_pnl, 2),
            'theta_pnl': round(theta_pnl, 2),
            'rho_pnl': round(rho_pnl, 2),
            'unexplained': round(unexplained, 2),
            'total_pnl': round(total_pnl, 2),
            'by_product_type': {},
        }

    # ─────────────────────────────────────────────────────────
    # REPRICING
    # ─────────────────────────────────────────────────────────

    def reprice_trade(self, book_id: str, trade_id: str,
                      market_data: dict = None) -> PricingResult:
        import time
        book = self.load_book(book_id)
        idx = self._find_trade_idx(book, trade_id)
        if idx < 0:
            raise KeyError(f"Trade '{trade_id}' not found.")

        trade = Trade.from_dict(book.trades[idx])
        t0 = time.time()

        if market_data is None:
            market_data = self._fetch_market_data(trade)

        result = self.pricer(trade, market_data)
        result.computation_time_ms = (time.time() - t0) * 1000

        # Update trade
        trade.current_pricing = result.to_dict()
        trade.current_mtm = result.notional_value
        if trade.entry_price is not None:
            trade.unrealized_pnl = result.notional_value - (trade.entry_price / 100 * trade.notional)
        trade.total_pnl = (trade.unrealized_pnl or 0) + (trade.realized_pnl or 0)
        trade.updated_at = datetime.utcnow().isoformat()
        trade.add_pricing_to_history(result)
        trade.add_audit('system', 'REPRICED', f"MTM: {result.notional_value:,.0f}")

        book.trades[idx] = trade.to_dict()
        self.save_book(book)
        return result

    def reprice_book(self, book_id: str, market_data: dict = None) -> dict:
        import time
        book = self.load_book(book_id)
        live_ids = [
            t['trade_id'] for t in book.trades
            if t.get('status') == TradeStatus.LIVE.value
        ]

        repriced, failed, failed_ids = 0, 0, []
        t0 = time.time()

        def reprice_one(tid):
            try:
                self.reprice_trade(book_id, tid, market_data)
                return tid, True, None
            except Exception as e:
                return tid, False, str(e)

        with ThreadPoolExecutor(max_workers=self.MAX_REPRICE_WORKERS) as executor:
            futures = {executor.submit(reprice_one, tid): tid for tid in live_ids}
            for fut in as_completed(futures):
                tid, ok, err = fut.result()
                if ok:
                    repriced += 1
                else:
                    failed += 1
                    failed_ids.append(tid)

        metrics = self.compute_book_metrics(book_id)

        return {
            'repriced_count': repriced,
            'failed_count': failed,
            'failed_trades': failed_ids,
            'total_time_ms': (time.time() - t0) * 1000,
            'book_metrics': metrics,
        }

    def _fetch_market_data(self, trade: Trade) -> dict:
        """Attempt to fetch live market data via yfinance."""
        spots, vols = {}, {}
        tickers = [u.get('ticker') for u in trade.underlyings if u.get('ticker')]

        try:
            import yfinance as yf
            for tk in tickers:
                try:
                    data = yf.download(tk, period='5d', interval='1d',
                                       progress=False, auto_adjust=True)
                    if not data.empty:
                        spots[tk] = float(data['Close'].iloc[-1])
                        returns = data['Close'].pct_change().dropna()
                        if len(returns) >= 2:
                            vols[tk] = float(returns.std() * (252 ** 0.5))
                        else:
                            vols[tk] = trade.inception_vols.get(tk, 0.20)
                    else:
                        spots[tk] = trade.inception_spots.get(tk, 100.0)
                        vols[tk] = trade.inception_vols.get(tk, 0.20)
                except Exception:
                    spots[tk] = trade.inception_spots.get(tk, 100.0)
                    vols[tk] = trade.inception_vols.get(tk, 0.20)
        except ImportError:
            for tk in tickers:
                spots[tk] = trade.inception_spots.get(tk, 100.0)
                vols[tk] = trade.inception_vols.get(tk, 0.20)

        return {
            'spots': spots,
            'vols': vols,
            'rate': trade.inception_rate or 0.035,
            'div_yields': {tk: trade.inception_div_yield or 0.02 for tk in tickers},
        }

    @staticmethod
    def _default_pricer(trade: Trade, market_data: dict) -> PricingResult:
        """
        Default pricer: Black-Scholes for vanilla options.
        For complex structures, keeps last known price (STALE flag).
        """
        now = datetime.utcnow().isoformat()
        spots = market_data.get('spots', {})
        vols = market_data.get('vols', {})
        rate = market_data.get('rate', 0.035)

        ticker = trade.underlyings[0].get('ticker') if trade.underlyings else None
        S = spots.get(ticker, 100.0) if ticker else 100.0
        sigma = vols.get(ticker, 0.20) if ticker else 0.20
        K_pct = trade.strike_pct or 100.0
        S0 = trade.underlyings[0].get('spot_at_inception', S) if trade.underlyings else S
        K = (K_pct / 100) * S0
        T = max(trade.tenor_years or 1.0, 0.001)

        if trade.product_type in ('vanilla_call', 'vanilla_put'):
            price_pct, delta, gamma, vega, theta, rho = _bs_greeks(
                S, K, T, rate, sigma,
                is_call=(trade.product_type == 'vanilla_call')
            )
        else:
            # For complex structures: return last known price with STALE flag
            last = trade.get_current_pricing()
            if last:
                return PricingResult(
                    timestamp=now,
                    model=last.model,
                    price=last.price,
                    price_currency=trade.currency,
                    notional_value=last.notional_value,
                    delta=last.delta, gamma=last.gamma,
                    vega=last.vega, theta=last.theta, rho=last.rho,
                    spot_used=S, vol_used=sigma, rate_used=rate,
                    is_stale=True,
                )
            price_pct = 100.0
            delta = gamma = vega = theta = rho = None

        return PricingResult(
            timestamp=now,
            model='black_scholes',
            price=price_pct,
            price_currency=trade.currency,
            notional_value=(price_pct / 100) * trade.notional,
            delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho,
            spot_used=S, vol_used=sigma, rate_used=rate,
            is_stale=False,
        )

    # ─────────────────────────────────────────────────────────
    # SNAPSHOTS
    # ─────────────────────────────────────────────────────────

    def take_snapshot(self, book_id: str) -> str:
        today = datetime.utcnow()
        date_str = today.date().isoformat()
        snap_dir = self.snapshots_dir / date_str
        snap_dir.mkdir(parents=True, exist_ok=True)
        snap_path = snap_dir / f"{book_id}.json.gz"

        book = self.load_book(book_id)
        metrics = self.compute_book_metrics(book_id)

        trades_snap = []
        for t_dict in book.trades:
            t = Trade.from_dict(t_dict)
            trades_snap.append({
                'trade_id': t.trade_id,
                'internal_ref': t.internal_ref,
                'product_name': t.product_name,
                'status': t.status,
                'notional': t.notional,
                'currency': t.currency,
                'current_mtm': t.current_mtm,
                'total_pnl': t.total_pnl,
                'current_pricing': t.current_pricing,
            })

        snap = DailySnapshot(
            date=date_str,
            book_id=book_id,
            timestamp=today.isoformat(),
            market_data={},
            trades_snapshot=trades_snap,
            book_metrics=metrics,
        )

        data = snap.to_dict()
        # Compress if large
        raw = json.dumps(data, default=str)
        if len(raw) > 500_000:
            self._write_json_gz(snap_path, data)
        else:
            self._write_json(snap_path.with_suffix('').with_suffix('.json'), data)
            snap_path = snap_path.with_suffix('').with_suffix('.json')

        return str(snap_path)

    def load_snapshot(self, book_id: str, date_str: str) -> Optional[DailySnapshot]:
        snap_dir = self.snapshots_dir / date_str
        for ext in ['.json.gz', '.json']:
            p = snap_dir / f"{book_id}{ext}"
            if p.exists():
                data = self._read_json_gz(p) if ext == '.json.gz' else self._read_json(p)
                if data:
                    return DailySnapshot.from_dict(data)
        return None

    def list_snapshots(self, book_id: str) -> list:
        result = []
        for d in sorted(self.snapshots_dir.iterdir(), reverse=True):
            if d.is_dir():
                for ext in ['.json.gz', '.json']:
                    p = d / f"{book_id}{ext}"
                    if p.exists():
                        result.append({
                            'date': d.name,
                            'path': str(p),
                            'size_kb': round(p.stat().st_size / 1024, 1),
                        })
                        break
        return result

    def compute_historical_pnl(self, book_id: str,
                                from_date: str = None,
                                to_date: str = None):
        """Returns a list of dicts (or DataFrame if pandas available)."""
        snaps = self.list_snapshots(book_id)
        rows = []
        for s in snaps:
            d = s['date']
            if from_date and d < from_date:
                continue
            if to_date and d > to_date:
                continue
            snap = self.load_snapshot(book_id, d)
            if snap:
                m = snap.book_metrics
                rows.append({
                    'date': d,
                    'total_mtm': m.get('total_mtm', 0),
                    'total_pnl': m.get('total_pnl', 0),
                    'unrealized_pnl': m.get('total_unrealized_pnl', 0),
                    'realized_pnl': m.get('total_realized_pnl', 0),
                    'live_trades': m.get('live_trades', 0),
                })

        rows.sort(key=lambda x: x['date'])
        if HAS_PANDAS:
            import pandas as pd
            if rows:
                df = pd.DataFrame(rows)
                df['date'] = pd.to_datetime(df['date'])
                return df
            return pd.DataFrame()
        return rows

    def compute_trade_pnl_history(self, book_id: str, trade_id: str):
        snaps = self.list_snapshots(book_id)
        rows = []
        for s in snaps:
            snap = self.load_snapshot(book_id, s['date'])
            if snap:
                for t in snap.trades_snapshot:
                    if t.get('trade_id') == trade_id:
                        rows.append({
                            'date': s['date'],
                            'mtm': t.get('current_mtm'),
                            'pnl': t.get('total_pnl'),
                        })

        rows.sort(key=lambda x: x['date'])
        if HAS_PANDAS:
            import pandas as pd
            return pd.DataFrame(rows) if rows else pd.DataFrame()
        return rows

    # ─────────────────────────────────────────────────────────
    # TEMPLATES
    # ─────────────────────────────────────────────────────────

    def save_as_template(self, book_id: str, trade_id: str,
                         template_name: str) -> str:
        trade = self.get_trade(book_id, trade_id)
        # Strip market-data-sensitive fields
        params = {
            'template_name': template_name,
            'product_type': trade.product_type,
            'product_name': trade.product_name,
            'direction': trade.direction,
            'currency': trade.currency,
            'tenor_years': trade.tenor_years,
            'strike_pct': trade.strike_pct,
            'barriers': trade.barriers,
            'coupon': trade.coupon,
            'capital_protection_pct': trade.capital_protection_pct,
            'participation_rate': trade.participation_rate,
            'cap_pct': trade.cap_pct,
            'pricing_model': trade.pricing_model,
            'pricing_params': trade.pricing_params,
            'desk': trade.desk,
            'basket_type': trade.basket_type,
            'saved_at': datetime.utcnow().isoformat(),
            'saved_from': trade.internal_ref,
        }
        safe_name = re.sub(r'[^\w\-]', '_', template_name)
        path = self.templates_dir / f"{safe_name}.json"
        self._write_json(path, params)
        return str(path)

    def load_template(self, template_name: str) -> Optional[dict]:
        safe_name = re.sub(r'[^\w\-]', '_', template_name)
        path = self.templates_dir / f"{safe_name}.json"
        return self._read_json(path)

    def list_templates(self) -> list:
        result = []
        for f in sorted(self.templates_dir.glob('*.json')):
            data = self._read_json(f)
            if data:
                result.append({
                    'template_name': data.get('template_name', f.stem),
                    'product_type': data.get('product_type', ''),
                    'product_name': data.get('product_name', ''),
                    'saved_at': data.get('saved_at', ''),
                    'saved_from': data.get('saved_from', ''),
                    'file': f.name,
                })
        return result

    def delete_template(self, template_name: str) -> bool:
        safe_name = re.sub(r'[^\w\-]', '_', template_name)
        path = self.templates_dir / f"{safe_name}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def create_trade_from_template(self, template_name: str,
                                   underlyings: list,
                                   notional: float,
                                   overrides: dict = None) -> Trade:
        tpl = self.load_template(template_name)
        if not tpl:
            raise FileNotFoundError(f"Template '{template_name}' not found.")

        now = datetime.utcnow()
        trade = Trade(
            product_type=tpl.get('product_type', 'custom'),
            product_name=tpl.get('product_name', ''),
            direction=tpl.get('direction', 'sell'),
            currency=tpl.get('currency', 'EUR'),
            tenor_years=tpl.get('tenor_years', 1.0),
            notional=notional,
            underlyings=underlyings,
            basket_type=tpl.get('basket_type', 'single'),
            strike_pct=tpl.get('strike_pct'),
            barriers=tpl.get('barriers', []),
            coupon=tpl.get('coupon'),
            capital_protection_pct=tpl.get('capital_protection_pct'),
            participation_rate=tpl.get('participation_rate'),
            cap_pct=tpl.get('cap_pct'),
            pricing_model=tpl.get('pricing_model', 'monte_carlo'),
            pricing_params=tpl.get('pricing_params', {}),
            desk=tpl.get('desk', ''),
            inception_date=now.date().isoformat(),
        )

        # Compute maturity from tenor
        from datetime import timedelta
        if trade.tenor_years:
            days = int(trade.tenor_years * 365.25)
            trade.maturity_date = (now.date() + timedelta(days=days)).isoformat()

        # Apply overrides (supports dotted paths like 'coupon.rate_pct')
        if overrides:
            for key, val in overrides.items():
                if '.' in key:
                    obj_key, sub_key = key.split('.', 1)
                    obj = getattr(trade, obj_key, None)
                    if isinstance(obj, dict):
                        obj[sub_key] = val
                        setattr(trade, obj_key, obj)
                elif hasattr(trade, key):
                    setattr(trade, key, val)

        return trade

    # ─────────────────────────────────────────────────────────
    # IMPORT / EXPORT JSON
    # ─────────────────────────────────────────────────────────

    def export_book_json(self, book_id: str) -> dict:
        """Return the book as a plain dict (for download)."""
        return self.load_book(book_id).to_dict()

    def import_book_json(self, data: dict, new_name: str = None) -> Book:
        """Import a book from a dict. Reassigns book_id to avoid collision."""
        import uuid as _u
        new_id = str(_u.uuid4())[:8]
        data['book_id'] = new_id
        if new_name:
            data['name'] = new_name
        data['created_at'] = datetime.utcnow().isoformat()
        book = Book.from_dict(data)
        self.save_book(book)
        return book

    # ─────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _find_trade_idx(book: Book, trade_id: str) -> int:
        for i, t in enumerate(book.trades):
            if t.get('trade_id') == trade_id:
                return i
        return -1

    @staticmethod
    def _extract_params(trade: Trade) -> dict:
        """Extract pricing-relevant parameters for versioning."""
        return {
            'product_type': trade.product_type,
            'notional': trade.notional,
            'currency': trade.currency,
            'tenor_years': trade.tenor_years,
            'strike_pct': trade.strike_pct,
            'barriers': trade.barriers,
            'coupon': trade.coupon,
            'capital_protection_pct': trade.capital_protection_pct,
            'participation_rate': trade.participation_rate,
            'pricing_model': trade.pricing_model,
            'pricing_params': trade.pricing_params,
        }

    def get_active_session_count(self):
        """Compatibility shim (not used but prevents import errors)."""
        return 0


# ═══════════════════════════════════════════════════════════════
# BLACK-SCHOLES PRICER (standalone, no external deps)
# ═══════════════════════════════════════════════════════════════

def _norm_cdf(x: float) -> float:
    """Standard normal CDF via math.erf."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def _bs_greeks(S: float, K: float, T: float, r: float, sigma: float,
               is_call: bool = True, q: float = 0.0) -> tuple:
    """
    Returns (price_pct, delta, gamma, vega, theta, rho).
    price_pct is the option price as a % of current spot S.
    """
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if is_call:
        price = S * math.exp(-q * T) * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
        delta = math.exp(-q * T) * _norm_cdf(d1)
        rho = K * T * math.exp(-r * T) * _norm_cdf(d2) / 100
    else:
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * math.exp(-q * T) * _norm_cdf(-d1)
        delta = math.exp(-q * T) * (_norm_cdf(d1) - 1)
        rho = -K * T * math.exp(-r * T) * _norm_cdf(-d2) / 100

    gamma = math.exp(-q * T) * _norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega = S * math.exp(-q * T) * _norm_pdf(d1) * math.sqrt(T) / 100  # per 1% vol
    theta = (
        -(S * math.exp(-q * T) * _norm_pdf(d1) * sigma / (2 * math.sqrt(T)))
        - r * K * math.exp(-r * T) * _norm_cdf(d2 if is_call else -d2)
    ) / 365  # per day

    price_pct = price / S * 100  # as % of spot
    return round(price_pct, 4), round(delta, 6), round(gamma, 8), round(vega, 6), round(theta, 6), round(rho, 6)


# ═══════════════════════════════════════════════════════════════
# HELPER: Build Trade from pricing session state
# ═══════════════════════════════════════════════════════════════

def build_trade_from_pricing(
    product_type: str,
    product_name: str,
    underlyings: list,
    notional: float,
    currency: str,
    pricing_result: PricingResult,
    direction: str = 'sell',
    tenor_years: float = 1.0,
    inception_date: str = '',
    maturity_date: str = '',
    strike_pct: float = None,
    barriers: list = None,
    coupon: dict = None,
    capital_protection_pct: float = None,
    participation_rate: float = None,
    pricing_model: str = 'monte_carlo',
    pricing_params: dict = None,
    counterparty: str = '',
    desk: str = '',
    tags: list = None,
    notes: str = '',
    created_by: str = 'user',
) -> Trade:
    """
    Helper: constructs a Trade from any pricing tab's results.
    Sets entry_price from the pricing result.
    """
    now = datetime.utcnow()
    if not inception_date:
        inception_date = now.date().isoformat()
    if not maturity_date and tenor_years:
        from datetime import timedelta
        from datetime import date as _date
        mat = _date.fromisoformat(inception_date) + timedelta(days=int(tenor_years * 365.25))
        maturity_date = mat.isoformat()

    # Build inception spots
    inception_spots = {}
    inception_vols = {}
    for u in underlyings:
        tk = u.get('ticker', '')
        if tk:
            inception_spots[tk] = u.get('spot_at_inception', pricing_result.spot_used or 100.0)
            inception_vols[tk] = pricing_result.vol_used or 0.20

    trade = Trade(
        product_type=product_type,
        product_name=product_name,
        direction=direction,
        underlyings=underlyings,
        notional=notional,
        currency=currency,
        inception_date=inception_date,
        maturity_date=maturity_date,
        tenor_years=tenor_years,
        strike_pct=strike_pct,
        barriers=barriers or [],
        coupon=coupon,
        capital_protection_pct=capital_protection_pct,
        participation_rate=participation_rate,
        pricing_model=pricing_model,
        pricing_params=pricing_params or {},
        initial_pricing=pricing_result.to_dict(),
        current_pricing=pricing_result.to_dict(),
        entry_price=pricing_result.price,
        current_mtm=pricing_result.notional_value,
        unrealized_pnl=0.0,
        total_pnl=0.0,
        inception_spots=inception_spots,
        inception_vols=inception_vols,
        inception_rate=pricing_result.rate_used,
        counterparty=counterparty,
        desk=desk,
        tags=tags or [],
        notes=notes,
        created_by=created_by,
        status=TradeStatus.LIVE.value,
    )

    return trade
