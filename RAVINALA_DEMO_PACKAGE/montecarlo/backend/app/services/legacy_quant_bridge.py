"""
services/legacy_quant_bridge.py - isolated bridge to legacy code under `src/`.

This module centralises the fallback import path to legacy project code so
backend services and agent nodes do not each manipulate `sys.path`.
"""

from __future__ import annotations

import importlib
import os
import sys
from functools import lru_cache


@lru_cache(maxsize=1)
def ensure_src_on_path() -> str:
    """
    Ensure both the project root and `src/` package path exist on `sys.path`.
    """
    montecarlo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    project_root = os.path.abspath(os.path.join(montecarlo_root, ".."))
    src_package_root = os.path.join(montecarlo_root, "src")

    for path in (project_root, src_package_root):
        if path not in sys.path:
            sys.path.insert(0, path)

    return src_package_root


def import_legacy_module(module_path: str):
    """Import a legacy module after ensuring the shared `src` bridge is ready."""
    ensure_src_on_path()
    return importlib.import_module(module_path)


def get_legacy_attr(module_path: str, attr_name: str):
    """Return an attribute from a legacy module loaded through the shared bridge."""
    module = import_legacy_module(module_path)
    return getattr(module, attr_name)


@lru_cache(maxsize=1)
def get_black_scholes_greeks_class():
    """Return the legacy Black-Scholes Greeks class, or ``None`` if unavailable."""
    try:
        return get_legacy_attr("src.engine", "BlackScholesGreeks")
    except (ImportError, AttributeError):
        return None


def quant_engine_available() -> bool:
    """Whether the legacy quantitative engine is importable."""
    return get_black_scholes_greeks_class() is not None
