"""
providers/coingecko_adapter.py - thin adapter for CoinGecko public pricing.

Keeps HTTP details out of services so external data access stays behind the
provider boundary used elsewhere in the backend.
"""

from __future__ import annotations

from typing import Any

import requests


class CoinGeckoProvider:
    """Minimal sync adapter around the public CoinGecko simple price endpoint."""

    BASE_URL = "https://api.coingecko.com/api/v3/simple/price"

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def fetch_simple_prices(
        self,
        *,
        ids: list[str],
        vs_currency: str = "usd",
        include_24hr_change: bool = True,
    ) -> dict[str, Any]:
        response = requests.get(
            self.BASE_URL,
            params={
                "ids": ",".join(ids),
                "vs_currencies": vs_currency,
                "include_24hr_change": str(include_24hr_change).lower(),
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected CoinGecko payload type")
        return payload
