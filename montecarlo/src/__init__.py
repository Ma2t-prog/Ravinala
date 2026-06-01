"""
Ravinala: The Cross-Asset Quantum Structuring Lab
Professional-grade platform for pricing and structuring derivatives.

Version: 2.0
Author: TSIVAHINY Matthias
"""

__version__ = "2.0.0"
__author__ = "TSIVAHINY Matthias"
__copyright__ = "© 2026 All Rights Reserved"

try:
    from .engine import BlackScholesGreeks, MultiAssetPricer, ZeroCouponBond, CouponSolver
    from .payoffs import PayoffLibrary, StructuredProductBuilder
    from .options import Call, Put
    from .pricing import BlackScholes, MonteCarlo
except ImportError:
    # Graceful fallback if imports fail
    pass

__all__ = [
    "BlackScholesGreeks",
    "MultiAssetPricer", 
    "ZeroCouponBond",
    "CouponSolver",
    "PayoffLibrary",
    "StructuredProductBuilder",
    "Call",
    "Put",
    "BlackScholes",
    "MonteCarlo",
    "__version__",
    "__author__",
]
