from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.data_fetcher import DataFetcher


def test_data_fetcher_no_longer_calls_coingecko_directly() -> None:
    source = (BACKEND_DIR / "app" / "services" / "data_fetcher.py").read_text(encoding="utf-8")
    assert "requests.get(" not in source
    assert "CoinGeckoProvider" in source


def test_fetch_commodities_uses_crypto_provider_boundary() -> None:
    class _CryptoProvider:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], str, bool]] = []

        def fetch_simple_prices(
            self,
            *,
            ids: list[str],
            vs_currency: str = "usd",
            include_24hr_change: bool = True,
        ) -> dict[str, dict[str, float]]:
            self.calls.append((ids, vs_currency, include_24hr_change))
            return {
                "bitcoin": {"usd": 68000.0, "usd_24h_change": 1.5},
                "ethereum": {"usd": 3200.0, "usd_24h_change": 0.8},
            }

    fetcher = DataFetcher()
    fetcher._ticker_history = lambda ticker, period="5d": pd.DataFrame({"Close": [100.0, 101.0]})
    fetcher._crypto_provider = _CryptoProvider()

    payload = fetcher.fetch_commodities()

    assert fetcher._crypto_provider.calls == [(["bitcoin", "ethereum"], "usd", True)]
    assert any(item["symbol"] == "BTC-USD" for item in payload["crypto"])
    assert any(item["symbol"] == "ETH-USD" for item in payload["crypto"])
