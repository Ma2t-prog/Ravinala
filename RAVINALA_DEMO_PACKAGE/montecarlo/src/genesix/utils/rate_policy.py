"""
Shared rate quote policy for src-side market and UI modules.

The goal is to preserve live-rate support where available while keeping a
traceable baseline/fallback policy aligned with the backend quant conventions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from .quant_conventions import (
    RISK_FREE_RATE,
    RISK_FREE_RATE_LAST_UPDATED,
    RISK_FREE_RATE_SOURCE,
)


RateMode = Literal["live", "fallback", "static", "baseline_default"]


@dataclass(frozen=True)
class RateQuote:
    """Structured rate quote with provenance metadata."""

    currency: str
    rate: float
    source_label: str
    as_of_utc: str
    mode: RateMode

    def to_legacy(self) -> tuple[float, str]:
        """Backward-compatible tuple used by legacy UI callers."""

        return float(self.rate), self.source_label

    def to_dict(self) -> dict[str, str | float]:
        """JSON/session-state friendly shape."""

        return {
            "currency": self.currency,
            "rate": float(self.rate),
            "source_label": self.source_label,
            "as_of_utc": self.as_of_utc,
            "mode": self.mode,
        }


_FALLBACK_RATES: dict[str, float] = {
    "USD": RISK_FREE_RATE,
    "EUR": 0.039,
    "GBP": 0.052,
    "JPY": 0.001,
}

_KNOWN_CURRENCIES = ("USD", "EUR", "GBP", "JPY")


def quote_as_of_today() -> str:
    """UTC date string used for live quotes."""

    return datetime.now(timezone.utc).date().isoformat()


def policy_rate_quote(currency: str) -> RateQuote:
    """
    Return the platform policy quote for a currency when live data is absent.

    The mapping mirrors the public market-data contract:
    - USD -> fallback anchored to the shared platform baseline
    - EUR/GBP -> documented fallback curves
    - JPY -> static policy rate placeholder
    - Unknown currencies -> explicit baseline_default mode
    """

    code = (currency or "USD").upper()
    if code not in _KNOWN_CURRENCIES:
        return RateQuote(
            currency=code,
            rate=RISK_FREE_RATE,
            source_label=(
                f"{code} quant baseline fallback "
                f"({RISK_FREE_RATE_SOURCE}, {RISK_FREE_RATE_LAST_UPDATED})"
            ),
            as_of_utc=RISK_FREE_RATE_LAST_UPDATED,
            mode="baseline_default",
        )

    if code == "USD":
        return RateQuote(
            currency="USD",
            rate=_FALLBACK_RATES["USD"],
            source_label="US 13W T-Bill (fallback, shared baseline anchored)",
            as_of_utc=RISK_FREE_RATE_LAST_UPDATED,
            mode="fallback",
        )

    if code == "EUR":
        return RateQuote(
            currency="EUR",
            rate=_FALLBACK_RATES["EUR"],
            source_label="€STER (fallback)",
            as_of_utc=RISK_FREE_RATE_LAST_UPDATED,
            mode="fallback",
        )

    if code == "GBP":
        return RateQuote(
            currency="GBP",
            rate=_FALLBACK_RATES["GBP"],
            source_label="SONIA (fallback)",
            as_of_utc=RISK_FREE_RATE_LAST_UPDATED,
            mode="fallback",
        )

    return RateQuote(
        currency="JPY",
        rate=_FALLBACK_RATES["JPY"],
        source_label="BOJ Policy Rate (~0%, static)",
        as_of_utc=RISK_FREE_RATE_LAST_UPDATED,
        mode="static",
    )


def live_rate_quote(currency: str, rate: float, source_label: str) -> RateQuote:
    """Create a live quote with current UTC dating."""

    return RateQuote(
        currency=(currency or "USD").upper(),
        rate=float(rate),
        source_label=source_label,
        as_of_utc=quote_as_of_today(),
        mode="live",
    )
