"""
GenesiX Physics Module — Econophysics & Cross-Science Engine

Applies cutting-edge physics to financial markets:

1. SEISMOLOGY: Gutenberg-Richter power laws, Omori aftershock decay
2. LPPL: Log-Periodic Power Law bubble detection (Sornette)
3. CRITICALITY: Phase transitions, market temperature, susceptibility
4. PERCOLATION: Financial R₀, epidemic contagion, network cascades
5. WAVELETS: Multi-scale decomposition, frequency-dependent correlation
6. SCALING: Power laws, stable distributions, Hurst exponents

This is the quantitative physics that Renaissance Technologies applies to markets.
What you'll find here has published empirical validation on real market data.
"""

from .seismology import GutenbergRichter, OmoriAftershock, FinancialSeismograph
from .lppl import LPPLModel
from .criticality import CriticalityAnalyzer
from .percolation import FinancialEpidemic
from .wavelets import WaveletAnalyzer
from .scaling import ScalingAnalyzer

__all__ = [
    'GutenbergRichter',
    'OmoriAftershock',
    'FinancialSeismograph',
    'LPPLModel',
    'CriticalityAnalyzer',
    'FinancialEpidemic',
    'WaveletAnalyzer',
    'ScalingAnalyzer',
]
