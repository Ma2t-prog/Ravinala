"""
Constants and asset universe for GenesiX.

Comprehensive lists of assets across equity, crypto, forex, commodities, indices.
Default parameters and thresholds for risk models.
"""

from typing import Final

from .quant_conventions import (
    ANNUALIZATION_FACTOR_RETURN as _ANNUALIZATION_FACTOR_RETURN,
    ANNUALIZATION_FACTOR_VOL as _ANNUALIZATION_FACTOR_VOL,
    CONVENTIONS as _CONVENTIONS,
    RISK_FREE_RATE as _RISK_FREE_RATE,
    RISK_FREE_RATE_LAST_UPDATED as _RISK_FREE_RATE_LAST_UPDATED,
    RISK_FREE_RATE_SOURCE as _RISK_FREE_RATE_SOURCE,
    STANDARD_HORIZONS as _STANDARD_HORIZONS,
    TRADING_DAYS as _TRADING_DAYS,
)

# ============== EQUITIES ==============
# S&P 500 & Major Indices
MAJOR_INDICES: Final[dict[str, str]] = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "Dow Jones": "^DJI",
    "Russell 2000": "^RUT",
    "CAC 40": "^FCHI",
    "DAX": "^GDAXI",
    "FTSE 100": "^FTSE",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Shanghai Composite": "000001.SS",
    "Sensex 30": "^BSESN",
    "Bovespa": "^BVSP",
}

# Top 20 US Stocks by Market Cap (as of 2024)
TOP_US_STOCKS: Final[dict[str, str]] = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Google": "GOOGL",
    "Amazon": "AMZN",
    "Tesla": "TSLA",
    "Berkshire Hathaway": "BRK.B",
    "Nvidia": "NVDA",
    "Meta": "META",
    "Broadcom": "AVGO",
    "Eli Lilly": "LLY",
    "Saudi Aramco": "2222.SR",
    "JPMorgan Chase": "JPM",
    "Johnson & Johnson": "JNJ",
    "Visa": "V",
    "Keyence": "6861.T",
    "Taiwan Semicon": "TSM",
    "UnitedHealth": "UNH",
    "Mastercard": "MA",
    "ASML": "ASML",
    "Roche": "ROCHE.VX",
}

# Sector ETFs
SECTOR_ETFS: Final[dict[str, str]] = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communications": "XLC",
}

# ============== CRYPTOCURRENCIES ==============
# Top 50 cryptocurrencies by market cap (all available via CoinGecko)
TOP_CRYPTOS: Final[dict[str, str]] = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana",
    "Binance Coin": "binancecoin",
    "XRP": "ripple",
    "Cardano": "cardano",
    "Avalanche": "avalanche-2",
    "Polygon": "matic-network",
    "Polkadot": "polkadot",
    "Chainlink": "chainlink",
    "Litecoin": "litecoin",
    "Bitcoin Cash": "bitcoin-cash",
    "Dogecoin": "dogecoin",
    "Uniswap": "uniswap",
    "Cosmos": "cosmos",
    "Monero": "monero",
    "Stellar": "stellar",
    "EOS": "eos",
    "Tezos": "tezos",
    "Vechain": "vechain",
}

# ============== FOREIGN EXCHANGE ==============
# Major currency pairs
MAJOR_FX_PAIRS: Final[dict[str, str]] = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "USD/SGD": "USDSGD=X",
    "USD/HKD": "USDHKD=X",
    "USD/INR": "USDINR=X",
    "USD/CNY": "USDCNY=X",
    "USD/BRL": "USDBRL=X",
    "USD/MXN": "USDMXN=X",
    "USD/ZAR": "USDZAR=X",
}

# ============== COMMODITIES ==============
# Energy, metals, agriculture
COMMODITIES: Final[dict[str, str]] = {
    # Energy
    "WTI Crude Oil": "CL=F",
    "Brent Crude": "BZ=F",
    "Natural Gas": "NG=F",
    "RBOB Gasoline": "RB=F",
    "Heating Oil": "HO=F",
    # Metals
    "Gold": "GC=F",
    "Silver": "SI=F",
    "Copper": "HG=F",
    "Platinum": "PL=F",
    "Palladium": "PA=F",
    "Aluminum": "ALU=F",
    "Zinc": "ZNC=F",
    "Nickel": "NI=F",
    # Agriculture
    "Wheat": "ZW=F",
    "Corn": "ZC=F",
    "Soybean": "ZS=F",
    "Soybean Oil": "ZL=F",
    "Soybean Meal": "ZM=F",
    "Sugar": "SB=F",
    "Coffee": "KC=F",
    "Cocoa": "CC=F",
    "Cotton": "CT=F",
    "Lumber": "LBS=F",
    # Fertilizers
    "Urea": "UREA.NS",
    "Potash": "POT",
}

# ============== FIXED INCOME ==============
TREASURIES: Final[dict[str, str]] = {
    "US 2Y": "^IRX",
    "US 10Y": "^TNX",
    "US 30Y": "^TYX",
    "US 3M": "^FVX",
    "US 5Y": "^FVX",  # Use 5Y Note futures as proxy
}

BOND_ETFS: Final[dict[str, str]] = {
    "US Aggregate Bonds": "AGG",
    "US Treasury Bonds": "SHV",
    "High Yield (HY)": "HYG",
    "Corporate Bonds": "LQD",
    "International Bonds": "IAGG",
}

# ============== VOLATILITY & FEAR INDICES ==============
VOLATILITY_INDICES: Final[dict[str, str]] = {
    "VIX (S&P 500)": "^VIX",
    "VXEMD (Emerging Markets)": "^VXEMD",
    "VXEEM (EM Equity)": "^VXEEM",
    "VXTYN (2Y Yield Vol)": "^VXTYN",
    "VXST (Short-term Vol)": "^VXST",
    "SKEW (Tail Risk)": "^SKEW",
}

# ============== ECONOMIC INDICATORS ==============
MACRO_INDICATORS: Final[dict[str, str]] = {
    # FRED Series IDs
    "Fed Funds Rate": "FEDFUNDS",
    "CPI-U": "CPIAUCSL",
    "CPI Core": "CPILFESL",
    "PPI": "PPIACO",
    "Unemployment Rate": "UNRATE",
    "Non-farm Payroll": "PAYEMS",
    "GDP": "GDP",
    "Real GDP": "GDPPOT",
    "GDP Per Capita": "A939RA3Q086SBEA",
    "M2 Money Supply": "M2SL",
    "M3 Money Supply": "MMNRNJ",
    "10Y Treasury Yield": "DGS10",
    "2Y Treasury Yield": "DGS2",
    "3M Treasury Yield": "DGS3MO",
    "Yield Spread (10Y-2Y)": "T10Y2Y",
    "Consumer Confidence": "UMCSENT",
    "ISM Manufacturing": "MMNRNJ",
    "ISM Services": "NAPMPSI",
    "Durable Goods Orders": "DGORDER",
}

# ============== SENTIMENT & ALTERNATIVE DATA ==============
SENTIMENT_KEYWORDS: Final[list[str]] = [
    "bitcoin",
    "ethereum",
    "stock market",
    "crash",
    "recession",
    "bull market",
    "fed rate hike",
    "inflation",
    "unemployment",
    "earnings",
    "earnings miss",
    "fed cut",
    "housing market",
    "inflation data",
]

REDDIT_SUBREDDITS: Final[list[str]] = [
    "wallstreetbets",
    "investing",
    "stocks",
    "cryptocurrency",
    "PersonalFinance",
    "options",
]

WEATHER_REGIONS: Final[dict[str, tuple[float, float]]] = {
    # Major agricultural regions: (latitude, longitude)
    "US Midwest Corn Belt": (41.5, -93.5),
    "Brazil Cerrado": (-15.5, -52.0),
    "EU Poland/Ukraine": (51.0, 20.0),
    "India Cotton Belt": (19.0, 77.0),
    "Australia Wheat": (-33.0, 143.0),
    "Russia Black Earth": (52.0, 47.0),
}

# ============== THRESHOLD & PARAMETERS ==============
RISK_FREE_RATE: Final[float] = _RISK_FREE_RATE
RISK_FREE_RATE_SOURCE: Final[str] = _RISK_FREE_RATE_SOURCE
RISK_FREE_RATE_LAST_UPDATED: Final[str] = _RISK_FREE_RATE_LAST_UPDATED
TRADING_DAYS: Final[int] = _TRADING_DAYS
ANNUALIZATION_FACTOR_RETURN: Final[float] = _ANNUALIZATION_FACTOR_RETURN
ANNUALIZATION_FACTOR_VOL: Final[float] = _ANNUALIZATION_FACTOR_VOL
STANDARD_HORIZONS: Final[tuple[int, ...]] = _STANDARD_HORIZONS
QUANT_CONVENTIONS = _CONVENTIONS

RISK_PARAMETERS: Final[dict[str, float]] = {
    "var_confidence": 0.95,
    "cvar_confidence": 0.95,
    "max_lookback_years": 2.0,
    "volatility_window_days": 20,
    "correlation_window_days": 60,
    "stress_test_percentile_shock": 0.05,  # 5th percentile historical shock
}

ML_PARAMETERS: Final[dict[str, float | int]] = {
    "train_window_days": 252,
    "validation_window_days": 60,
    "test_size": 0.2,
    "random_seed": 42,
    "xgboost_max_depth": 6,
    "lightgbm_num_leaves": 31,
    "lstm_lookback": 60,
    "ensemble_weights": {
        "xgboost": 0.35,
        "lightgbm": 0.35,
        "random_forest": 0.15,
        "garch": 0.15,
    },
}

SCENARIO_DEFINITIONS: Final[dict[str, dict[str, float]]] = {
    "bull": {
        "probability": 0.25,
        "equity_shock": 0.08,
        "bond_shock": -0.02,
        "vol_shock": -0.30,
        "description": "Strong economic growth, rising earnings",
    },
    "base": {
        "probability": 0.50,
        "equity_shock": 0.02,
        "bond_shock": 0.00,
        "vol_shock": 0.00,
        "description": "Baseline: slow steady growth",
    },
    "bear": {
        "probability": 0.20,
        "equity_shock": -0.06,
        "bond_shock": 0.02,
        "vol_shock": 0.50,
        "description": "Slowdown, earnings disappointment",
    },
    "crash": {
        "probability": 0.05,
        "equity_shock": -0.20,
        "bond_shock": 0.10,
        "vol_shock": 2.00,
        "description": "Systemic crisis: recession/financial stress",
    },
}

HISTORICAL_STRESS_EVENTS: Final[dict[str, dict[str, float]]] = {
    "covid_2020": {
        "date": "2020-03-16",
        "SPY": -0.34,
        "QQQ": -0.28,
        "IWM": -0.37,
        "GLD": -0.12,
        "UUP": 0.04,
        "AGG": -0.02,
        "HYG": -0.12,
        "^VIX": 2.80,
        "description": "COVID-19 crash",
    },
    "gfc_2008": {
        "date": "2008-09-15",
        "SPY": -0.57,
        "GLD": 0.25,
        "USO": -0.70,
        "HYG": -0.30,
        "^VIX": 1.80,
        "description": "Global Financial Crisis - Lehman collapse",
    },
    "dotcom_2000": {
        "date": "2000-03-10",
        "SPY": -0.49,
        "QQQ": -0.83,
        "IYZ": -0.85,
        "description": "Tech bubble burst",
    },
    "rate_hike_2022": {
        "date": "2022-06-15",
        "SPY": -0.25,
        "QQQ": -0.35,
        "TLT": -0.30,
        "IEF": -0.12,
        "BTC": -0.65,
        "^VIX": 0.80,
        "description": "Fed hiking cycle - growth stocks, bonds, crypto hit",
    },
    "black_monday_1987": {
        "date": "1987-10-19",
        "SPY": -0.22,
        "^VIX": 3.00,
        "description": "1987 stock market crash",
    },
    "brexit_2016": {
        "date": "2016-06-23",
        "^FTSE": -0.05,
        "^FCHI": -0.08,
        "^GDAXI": -0.07,
        "description": "UK votes to leave EU - European bourses hit",
    },
}

# ============== FEATURE ENGINEERING ==============
FEATURE_DEFINITIONS: Final[dict[str, dict[str, str | int]]] = {
    # Price features
    "daily_return": {"type": "price", "description": "Daily log return"},
    "volatility_20d": {"type": "price", "description": "20-day rolling volatility"},
    "volatility_60d": {"type": "price", "description": "60-day rolling volatility"},
    "momentum_10d": {"type": "price", "description": "10-day momentum (rate of change)"},
    "momentum_30d": {"type": "price", "description": "30-day momentum"},
    "rsi_14": {"type": "price", "description": "Relative Strength Index (14-period)"},
    "macd": {"type": "price", "description": "MACD line"},
    "macd_signal": {"type": "price", "description": "MACD signal line"},
    "bb_upper": {"type": "price", "description": "Bollinger Band upper (20, 2std)"},
    "bb_lower": {"type": "price", "description": "Bollinger Band lower"},
    "bb_percent": {"type": "price", "description": "Bollinger Band %B"},
    # Macro features
    "unemployment_rate": {"type": "macro", "description": "Monthly unemployment %"},
    "unemployment_change": {"type": "macro", "description": "Change in unemployment"},
    "cpi_yoy": {"type": "macro", "description": "CPI year-over-year %"},
    "cpi_change": {"type": "macro", "description": "Monthly CPI change"},
    "gdp_growth": {"type": "macro", "description": "GDP growth rate"},
    "yield_spread_10y2y": {"type": "macro", "description": "10Y-2Y spread"},
    "fed_funds_rate": {"type": "macro", "description": "Fed Funds target rate"},
    "m2_growth": {"type": "macro", "description": "M2 money supply growth"},
    "consumer_confidence": {"type": "macro", "description": "Conference Board Consumer Confidence"},
    # Alternative features
    "weather_score": {"type": "alt", "description": "Agricultural weather impact"},
    "sentiment_composite": {"type": "alt", "description": "Weighted sentiment index"},
    "google_trends_momentum": {"type": "alt", "description": "Google Trends interest spike"},
    "vix_level": {"type": "alt", "description": "VIX index level"},
    "vix_change": {"type": "alt", "description": "VIX daily change"},
    "put_call_ratio": {"type": "alt", "description": "S&P 500 put/call ratio"},
    "bdi_change": {"type": "alt", "description": "Baltic Dry Index change"},
    "dxy_change": {"type": "alt", "description": "Dollar Index change"},
    # Cross features
    "vix_x_sentiment": {"type": "cross", "description": "VIX × sentiment interaction"},
    "yield_x_momentum": {"type": "cross", "description": "Yield spread × price momentum"},
}

# ============== FORMATTING ==============
DEFAULT_CURRENCY: Final[str] = "EUR"
CURRENCY_SYMBOLS: Final[dict[str, str]] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CHF": "CHF ",
    "CAD": "C$",
    "AUD": "A$",
    "BTC": "฿",
}

# ============== CONVENIENCE LOOKUP ==============
ALL_ASSETS: Final[dict[str, dict[str, str]]] = {
    "indices": MAJOR_INDICES,
    "equities": TOP_US_STOCKS,
    "sectors": SECTOR_ETFS,
    "forex": MAJOR_FX_PAIRS,
    "commodities": COMMODITIES,
    "crypto": TOP_CRYPTOS,
    "bonds": BOND_ETFS,
    "volatility": VOLATILITY_INDICES,
}
