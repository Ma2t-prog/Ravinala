"""
GenesiX Math Module — Stochastic Calculus & Advanced Mathematical Foundations.

This module is the theoretical backbone of GenesiX. Every quant model
traces back to one of these components.

Modules:
    brownian   — Brownian motion, GBM, path simulation
    ito        — Itô calculus, Itô's lemma, Girsanov
    sde        — SDE solvers (Euler-Maruyama, Milstein, Heston, CIR)
    measures   — Risk-neutral pricing, Feynman-Kac
    levy       — Lévy processes, Kou double-exponential, Variance Gamma
    fractals   — Hurst exponent, R/S analysis, DFA, multifractal
    entropy    — Shannon, sample entropy, transfer entropy
    rmt        — Random Matrix Theory, Marchenko-Pastur, correlation cleaning
"""

from .brownian import BrownianMotion, GeometricBrownianMotion
from .ito import ItoCalculus
from .sde import SDESolver, OrnsteinUhlenbeck, CIRProcess, HestonModel, MertonJumpDiffusion
from .measures import RiskNeutralPricing
from .levy import KouDoubleExponential, VarianceGamma, NormalInverseGaussian
from .fractals import FractalAnalyzer, LyapunovExponent
from .entropy import EntropyAnalyzer
from .rmt import CorrelationCleaner

__all__ = [
    "BrownianMotion",
    "GeometricBrownianMotion",
    "ItoCalculus",
    "SDESolver",
    "OrnsteinUhlenbeck",
    "CIRProcess",
    "HestonModel",
    "MertonJumpDiffusion",
    "RiskNeutralPricing",
    "KouDoubleExponential",
    "VarianceGamma",
    "NormalInverseGaussian",
    "FractalAnalyzer",
    "LyapunovExponent",
    "EntropyAnalyzer",
    "CorrelationCleaner",
]
