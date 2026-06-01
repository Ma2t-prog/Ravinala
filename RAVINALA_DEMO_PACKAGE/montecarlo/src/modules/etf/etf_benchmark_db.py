"""
UCITS ETF Benchmark Database
Stores benchmark index definitions and ETF → benchmark mappings.
"""

# ── Benchmark definitions ────────────────────────────────────────────────────
BENCHMARK_DB = {
    "MSCI World": {
        "ticker": "URTH",           # iShares MSCI World ETF (USD proxy)
        "description": "Large & mid-cap equities across 23 developed markets (~1 500 constituents)",
        "asset_class": "Global Equity",
        "currency": "USD",
        "region": "Global",
        "constituents": 1_504,
    },
    "MSCI Emerging Markets": {
        "ticker": "EEM",
        "description": "Large & mid-cap equities across 24 emerging-market countries (~1 400 constituents)",
        "asset_class": "Emerging Equity",
        "currency": "USD",
        "region": "Emerging Markets",
        "constituents": 1_385,
    },
    "MSCI Europe": {
        "ticker": "IMEU",
        "description": "Large & mid-cap equities across 15 developed European markets",
        "asset_class": "European Equity",
        "currency": "EUR",
        "region": "Europe",
        "constituents": 428,
    },
    "S&P 500": {
        "ticker": "SPY",
        "description": "500 leading US large-cap companies, representing ~80 % of available US market cap",
        "asset_class": "US Equity",
        "currency": "USD",
        "region": "United States",
        "constituents": 500,
    },
    "Euro Stoxx 50": {
        "ticker": "FEZ",
        "description": "50 blue-chip eurozone companies across 11 countries",
        "asset_class": "European Equity",
        "currency": "EUR",
        "region": "Eurozone",
        "constituents": 50,
    },
    "Bloomberg Global Aggregate": {
        "ticker": "BNDW",
        "description": "Investment-grade government and corporate bonds from 70+ countries",
        "asset_class": "Global Fixed Income",
        "currency": "USD",
        "region": "Global",
        "constituents": 18_000,
    },
    "Bloomberg Euro Aggregate": {
        "ticker": "IEAG.AS",
        "description": "Euro-denominated investment-grade bonds (govt + corp + securitised)",
        "asset_class": "European Fixed Income",
        "currency": "EUR",
        "region": "Europe",
        "constituents": 4_200,
    },
    "MSCI World ESG Leaders": {
        "ticker": "SUWS.L",
        "description": "Highest ESG-rated securities within each sector of the MSCI World Index",
        "asset_class": "Global Equity ESG",
        "currency": "USD",
        "region": "Global",
        "constituents": 737,
    },
    "NASDAQ-100": {
        "ticker": "QQQ",
        "description": "100 largest non-financial companies listed on the NASDAQ",
        "asset_class": "US Technology Equity",
        "currency": "USD",
        "region": "United States",
        "constituents": 100,
    },
    "FTSE 100": {
        "ticker": "ISF.L",
        "description": "100 largest companies listed on the London Stock Exchange by market cap",
        "asset_class": "UK Equity",
        "currency": "GBP",
        "region": "United Kingdom",
        "constituents": 100,
    },
}

# ── ISIN → benchmark name lookup ─────────────────────────────────────────────
ETF_BENCHMARK_MAPPING: dict[str, str] = {
    # iShares Core MSCI World
    "IE00B4L5Y983": "MSCI World",
    # iShares Core S&P 500
    "IE00B5BMR087": "S&P 500",
    # iShares Core MSCI EM IMI
    "IE00BKM4GZ66": "MSCI Emerging Markets",
    # Xtrackers MSCI World Swap
    "LU0274208692": "MSCI World",
    # Amundi MSCI World
    "LU1681043599": "MSCI World",
    # iShares MSCI Europe
    "IE00B4K48X80": "MSCI Europe",
    # iShares Euro Stoxx 50
    "IE0008471009": "Euro Stoxx 50",
    # Lyxor Euro Stoxx 50
    "FR0007054358": "Euro Stoxx 50",
    # iShares Global Aggregate Bond
    "IE00B3F81409": "Bloomberg Global Aggregate",
    # Vanguard FTSE All-World
    "IE00B3RBWM25": "MSCI World",
    # iShares Core MSCI World ESG
    "IE00BHZPJ620": "MSCI World ESG Leaders",
    # Amundi NASDAQ-100
    "LU1829221024": "NASDAQ-100",
    # iShares NASDAQ-100
    "IE00B53SZB19": "NASDAQ-100",
    # iShares Core FTSE 100
    "IE0005042456": "FTSE 100",
    # Lyxor S&P 500
    "LU0496786574": "S&P 500",
}


def get_benchmark(isin: str) -> dict | None:
    """Return benchmark info for a given ISIN, or None if not mapped."""
    name = ETF_BENCHMARK_MAPPING.get(isin)
    if name is None:
        return None
    return {"name": name, **BENCHMARK_DB[name]}


def list_benchmarks() -> list[str]:
    """Return sorted list of benchmark names."""
    return sorted(BENCHMARK_DB.keys())
