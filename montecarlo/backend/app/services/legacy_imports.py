"""
Centralized backend bridge for legacy imports from `src/`.

This keeps mutable import-path changes in one place instead of scattering
`sys.path` edits across multiple services and agent nodes.
"""

from __future__ import annotations

import importlib
import os
import sys
from functools import lru_cache
from threading import Lock
from types import ModuleType

_PATH_LOCK = Lock()


def _abs_path(*parts: str) -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), *parts))


def _ensure_import_path(path: str) -> str:
    abs_path = os.path.abspath(path)
    with _PATH_LOCK:
        if abs_path not in sys.path:
            sys.path.insert(0, abs_path)
    return abs_path


def _src_root() -> str:
    return _abs_path("..", "..", "..", "src")


def _repo_root() -> str:
    return _abs_path("..", "..", "..", "..")


@lru_cache(maxsize=1)
def get_fundamental_analyzer_class():
    _ensure_import_path(_src_root())
    module = importlib.import_module("analysis.fundamentals")
    return module.FundamentalAnalyzer


@lru_cache(maxsize=1)
def get_portfolio_optimizer_class():
    _ensure_import_path(_src_root())
    module = importlib.import_module("genesix.optimizer")
    return module.PortfolioOptimizer


@lru_cache(maxsize=1)
def get_universe_explorer_module() -> ModuleType:
    _ensure_import_path(_src_root())
    return importlib.import_module("genesix.universe_explorer")


@lru_cache(maxsize=1)
def get_black_scholes_greeks_class():
    _ensure_import_path(_repo_root())
    try:
        module = importlib.import_module("src.engine")
    except ImportError:
        return None
    return getattr(module, "BlackScholesGreeks", None)
