"""
Screener Engine — Multi-criteria filtering for instruments
"""

import logging
import time
from typing import List, Dict, Tuple
from .models import Instrument, ScreenerCriteria, ScreenerResult, AssetClass

logger = logging.getLogger(__name__)


class ScreenerEngine:
    """
    Advanced screener with multi-criteria filtering.
    """
    
    def __init__(self, instruments: List[Instrument]):
        """
        Initialize screener with instrument universe.
        
        Args:
            instruments: List of Instrument objects
        """
        self.instruments = instruments
        logger.info(f"ScreenerEngine initialized with {len(instruments)} instruments")
    
    def screen(self, criteria: ScreenerCriteria) -> ScreenerResult:
        """
        Apply screener criteria and return results.
        """
        start_time = time.time()
        
        filtered = self.instruments.copy()
        
        # Free-text search (ticker, name, sector)
        if criteria.search_query:
            q = criteria.search_query.lower()
            filtered = [
                inst for inst in filtered
                if q in inst.ticker.lower() 
                or q in inst.name.lower()
                or (inst.sector and q in inst.sector.lower())
            ]
            logger.debug(f"  After search: {len(filtered)} instruments")
        
        # Asset classes
        if criteria.asset_classes:
            filtered = [
                inst for inst in filtered
                if inst.asset_class in criteria.asset_classes
            ]
            logger.debug(f"  After asset_classes: {len(filtered)} instruments")
        
        # Sectors
        if criteria.sectors:
            filtered = [inst for inst in filtered if inst.sector in criteria.sectors]
            logger.debug(f"  After sectors: {len(filtered)} instruments")
        
        # Countries
        if criteria.countries:
            filtered = [inst for inst in filtered if inst.country in criteria.countries]
            logger.debug(f"  After countries: {len(filtered)} instruments")
        
        # P/E ratio
        if criteria.pe_min is not None:
            filtered = [
                inst for inst in filtered
                if inst.pe_ratio and inst.pe_ratio >= criteria.pe_min
            ]
            logger.debug(f"  After PE min: {len(filtered)} instruments")
        
        if criteria.pe_max is not None:
            filtered = [
                inst for inst in filtered
                if inst.pe_ratio and inst.pe_ratio <= criteria.pe_max
            ]
            logger.debug(f"  After PE max: {len(filtered)} instruments")
        
        # P/B ratio
        if criteria.pb_min is not None:
            filtered = [
                inst for inst in filtered
                if inst.pb_ratio and inst.pb_ratio >= criteria.pb_min
            ]
        if criteria.pb_max is not None:
            filtered = [
                inst for inst in filtered
                if inst.pb_ratio and inst.pb_ratio <= criteria.pb_max
            ]
        
        # Dividend yield (%)
        if criteria.dividend_yield_min is not None:
            filtered = [
                inst for inst in filtered
                if inst.dividend_yield and inst.dividend_yield >= criteria.dividend_yield_min
            ]
            logger.debug(f"  After div yield min: {len(filtered)} instruments")
        
        if criteria.dividend_yield_max is not None:
            filtered = [
                inst for inst in filtered
                if inst.dividend_yield and inst.dividend_yield <= criteria.dividend_yield_max
            ]
        
        # Market cap
        if criteria.market_cap_min is not None:
            filtered = [
                inst for inst in filtered
                if inst.market_cap and inst.market_cap >= criteria.market_cap_min
            ]
        if criteria.market_cap_max is not None:
            filtered = [
                inst for inst in filtered
                if inst.market_cap and inst.market_cap <= criteria.market_cap_max
            ]
        
        # Volatility (%)
        if criteria.volatility_max is not None:
            filtered = [
                inst for inst in filtered
                if inst.volatility_1y is None or inst.volatility_1y <= criteria.volatility_max
            ]
            logger.debug(f"  After vol max: {len(filtered)} instruments")
        
        # Sharpe ratio
        if criteria.sharpe_min is not None:
            filtered = [
                inst for inst in filtered
                if inst.sharpe_1y is None or inst.sharpe_1y >= criteria.sharpe_min
            ]
        
        # ESG score
        if criteria.esg_score_min is not None:
            filtered = [
                inst for inst in filtered
                if inst.esg_score is None or inst.esg_score >= criteria.esg_score_min
            ]
            logger.debug(f"  After ESG min: {len(filtered)} instruments")
        
        # Price change (%)
        if criteria.price_change_min is not None:
            filtered = [
                inst for inst in filtered
                if inst.price_change_1d >= criteria.price_change_min
            ]
        if criteria.price_change_max is not None:
            filtered = [
                inst for inst in filtered
                if inst.price_change_1d <= criteria.price_change_max
            ]
        
        # Sort by market cap (largest first)
        filtered.sort(key=lambda x: x.market_cap or 0, reverse=True)
        
        execution_time = (time.time() - start_time) * 1000  # ms
        
        result = ScreenerResult(
            instruments=filtered,
            total_count=len(filtered),
            criteria_applied=criteria,
            execution_time_ms=execution_time,
        )
        
        logger.info(f"Screener result: {len(filtered)} instruments in {execution_time:.1f}ms")
        return result
    
    # ========================================================================
    # Pre-built screens (common investor strategies)
    # ========================================================================
    
    def screen_high_dividend(self, min_yield: float = 4.0) -> ScreenerResult:
        """High dividend payers (income strategy)."""
        return self.screen(ScreenerCriteria(
            dividend_yield_min=min_yield,
            asset_classes=[AssetClass.EQUITY],
        ))
    
    def screen_growth(self) -> ScreenerResult:
        """Growth stocks (positive momentum, low P/E vs growth)."""
        return self.screen(ScreenerCriteria(
            price_change_min=0,  # Up in price
            pe_max=30,
            asset_classes=[AssetClass.EQUITY],
        ))
    
    def screen_value(self) -> ScreenerResult:
        """Value stocks (low P/E, low P/B, high dividend yield)."""
        return self.screen(ScreenerCriteria(
            pe_max=12,
            pb_max=1.5,
            dividend_yield_min=2.0,
            asset_classes=[AssetClass.EQUITY],
        ))
    
    def screen_large_cap(self) -> ScreenerResult:
        """Large-cap stocks (market cap > $50B)."""
        return self.screen(ScreenerCriteria(
            market_cap_min=50_000_000_000,
            asset_classes=[AssetClass.EQUITY],
        ))
    
    def screen_momentum(self) -> ScreenerResult:
        """Momentum players (up 5%+ in last day)."""
        return self.screen(ScreenerCriteria(
            price_change_min=5.0,
            asset_classes=[AssetClass.EQUITY],
        ))
    
    def screen_low_volatility(self) -> ScreenerResult:
        """Low volatility (defensive) stocks."""
        return self.screen(ScreenerCriteria(
            volatility_max=20,
            asset_classes=[AssetClass.EQUITY],
        ))
    
    def screen_esg_leaders(self, esg_min: float = 70.0) -> ScreenerResult:
        """ESG leaders (high ESG score)."""
        return self.screen(ScreenerCriteria(
            esg_score_min=esg_min,
            asset_classes=[AssetClass.EQUITY],
        ))
    
    def screen_sector(self, sector: str) -> ScreenerResult:
        """All instruments in a specific sector."""
        return self.screen(ScreenerCriteria(sectors=[sector]))
    
    def screen_country(self, country: str) -> ScreenerResult:
        """All instruments in a specific country."""
        return self.screen(ScreenerCriteria(countries=[country]))
    
    # ========================================================================
    # Utility methods
    # ========================================================================
    
    def get_top_by_metric(
        self,
        metric: str,
        n: int = 10,
        ascending: bool = False,
        asset_class: str = None
    ) -> List[Instrument]:
        """
        Get top N instruments by a given metric.
        
        Args:
            metric: 'price_change_1d', 'volatility_1y', 'pe_ratio', 'dividend_yield', etc.
            n: Number of results
            ascending: Sort ascending vs descending
            asset_class: Filter by asset class
        """
        filtered = self.instruments.copy()
        
        if asset_class:
            filtered = [i for i in filtered if i.asset_class.value == asset_class]
        
        # Filter out instruments with None value for this metric
        filtered = [i for i in filtered if getattr(i, metric, None) is not None]
        
        # Sort
        filtered.sort(
            key=lambda x: getattr(x, metric),
            reverse=not ascending
        )
        
        return filtered[:n]
    
    def get_correlation_pairs(self) -> Dict[Tuple[str, str], float]:
        """
        Get correlation matrix between all instruments (basic version).
        This would require historical price data - stub for now.
        """
        # TODO: Implement with price history
        return {}
