"""
Data models for Universe Explorer
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class AssetClass(str, Enum):
    """Asset class enumeration"""
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    COMMODITY = "commodity"
    CRYPTO = "crypto"
    REAL_ESTATE = "real_estate"
    CASH = "cash"
    OTHER = "other"


class Instrument(BaseModel):
    """Core instrument model (Pydantic)"""
    ticker: str = Field(..., description="Ticker symbol (e.g., 'AAPL')")
    isin: Optional[str] = Field(None, description="ISIN code")
    name: str = Field(..., description="Full instrument name")
    asset_class: AssetClass = Field(..., description="Asset class")
    sector: Optional[str] = Field(None, description="GICS sector (e.g., 'Technology')")
    industry: Optional[str] = Field(None, description="GICS industry")
    country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    exchange: str = Field(..., description="Exchange (e.g., 'NASDAQ')")
    currency: str = Field(default="USD", description="Trading currency")
    
    # Pricing
    price: float = Field(..., description="Last close price")
    price_change_1d: float = Field(default=0.0, description="1-day change (%)")
    price_change_1m: Optional[float] = Field(None, description="1-month change (%)")
    price_change_1y: Optional[float] = Field(None, description="1-year change (%)")
    
    # Volume & liquidity
    volume_avg_30d: Optional[float] = Field(None, description="Avg daily volume (30d)")
    market_cap: Optional[float] = Field(None, description="Market cap in local currency")
    
    # Fundamentals
    pe_ratio: Optional[float] = Field(None, description="Price-to-earnings ratio")
    pb_ratio: Optional[float] = Field(None, description="Price-to-book ratio")
    dividend_yield: Optional[float] = Field(None, description="Dividend yield (%)")
    eps_growth: Optional[float] = Field(None, description="EPS growth (%)")
    revenue_growth: Optional[float] = Field(None, description="Revenue growth (%)")
    debt_to_equity: Optional[float] = Field(None, description="Debt-to-equity ratio")
    roe: Optional[float] = Field(None, description="Return on equity (%)")
    
    # Risk metrics
    volatility_1y: Optional[float] = Field(None, description="Annualized volatility (%)")
    beta: Optional[float] = Field(None, description="Beta vs S&P 500")
    max_drawdown_1y: Optional[float] = Field(None, description="Max drawdown 1Y (%)")
    sharpe_1y: Optional[float] = Field(None, description="Sharpe ratio 1Y")
    
    # ESG & ratings
    esg_score: Optional[float] = Field(None, description="ESG score (0-100)")
    credit_rating: Optional[str] = Field(None, description="Credit rating (e.g., 'AA+')")
    
    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    data_source: str = Field(default="openbb", description="Data source")

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "asset_class": "equity",
                "sector": "Technology",
                "country": "US",
                "exchange": "NASDAQ",
                "price": 189.45,
                "price_change_1d": 1.23,
            }
        }


class ScreenerCriteria(BaseModel):
    """Screener filter criteria"""
    pe_min: Optional[float] = None
    pe_max: Optional[float] = None
    pb_min: Optional[float] = None
    pb_max: Optional[float] = None
    dividend_yield_min: Optional[float] = None
    dividend_yield_max: Optional[float] = None
    market_cap_min: Optional[float] = None
    market_cap_max: Optional[float] = None
    volatility_max: Optional[float] = None
    sharpe_min: Optional[float] = None
    esg_score_min: Optional[float] = None
    sectors: Optional[List[str]] = None
    countries: Optional[List[str]] = None
    asset_classes: Optional[List[AssetClass]] = None
    price_change_min: Optional[float] = None
    price_change_max: Optional[float] = None
    search_query: Optional[str] = None  # Free-text search in name/ticker


class ScreenerResult(BaseModel):
    """Screener result with metadata"""
    instruments: List[Instrument]
    total_count: int
    criteria_applied: ScreenerCriteria
    execution_time_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
