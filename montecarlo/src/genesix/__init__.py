"""
GenesiX: Risk Intelligence & Market Knowledge Engine
Integrated sub-module for Ravinala cross-asset derivatives platform.
"""

__version__ = "0.1.0"
__author__ = "Ravinala Team"

from . import data
from . import risk
from . import ml
from . import physics
from . import dashboard
from . import utils

__all__ = [
    "data",
    "risk",
    "ml",
    "physics",
    "dashboard",
    "utils",
]
