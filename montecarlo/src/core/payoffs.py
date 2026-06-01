"""
ZetaOrigins by TSIVAHINY Matthias - Structured Products Catalog
Implements modern and vintage exotic payoffs for cross-asset structuring.
"""

import numpy as np
from typing import Callable, List, Optional, Dict


class PayoffLibrary:
    """Collection of structured product payoff functions."""
    
    # ==================== MODERN PRODUCTS ====================
    
    @staticmethod
    def phoenix(
        spot_vector: np.ndarray,
        strikes: np.ndarray,
        coupons: List[float],
        barrier_levels: List[float],
        memory_buffer: Dict = None,
        **kwargs
    ) -> float:
        """
        Phoenix with coupon memory and recall logic.
        
        - Coupon is paid at each observation date if no barrier is crossed.
        - If a barrier is touched, accumulated coupons are paid at maturity.
        - Autocall feature: product recalled if spot > autocall barrier.
        
        Args:
            spot_vector: Final spot prices (n_assets,)
            strikes: Strike levels for each asset
            coupons: Coupon rates by observation date
            barrier_levels: Protection/coupon barriers
            memory_buffer: Dict tracking coupon history
        """
        n_assets = len(spot_vector)
        worst_performer = np.min(spot_vector / strikes)
        
        # Check barrier touch
        barrier_hit = worst_performer < min(barrier_levels)
        
        # Base payoff: protection below strike, memory coupon accumulation
        if barrier_hit:
            payoff = np.sum(strikes) / n_assets  # Protection level
            # Add accumulated coupons (simplified)
            accumulated_coupon = sum(coupons) * 100
            payoff += accumulated_coupon
        else:
            payoff = 100 + coupons[-1] * 100  # Par + final coupon
        
        return max(payoff, 0)
    
    @staticmethod
    def athena(
        spot_vector: np.ndarray,
        strikes: np.ndarray,
        coupon: float,
        barrier: float,
        autocall_level: float,
        **kwargs
    ) -> float:
        """
        Athena: Pure Autocall with fixed coupon and barrier protection.
        
        - Pays fixed coupon at each date.
        - Recalls (early termination) if spot > autocall level.
        - Protection below barrier.
        """
        n_assets = len(spot_vector)
        worst_performer = np.min(spot_vector / strikes)
        
        # Autocall logic
        if worst_performer >= autocall_level:
            return 100 + coupon * 100
        
        # Barrier protection logic
        if worst_performer < barrier:
            return np.min(spot_vector)  # Inverse performance
        
        return 100 + coupon * 100
    
    @staticmethod
    def reverse_convertible(
        spot_final: float,
        strike: float,
        coupon: float,
        barrier: float = 0.5,
        **kwargs
    ) -> float:
        """
        Reverse Convertible: Bond + Short Put structure.
        
        - Investor receives coupon (high yield).
        - At maturity, must buy stock if it falls below barrier.
        - Equivalent to: Par + Coupon - Short Put Payoff
        """
        # Coupon leg
        coupon_pv = 100 + coupon * 100
        
        # Short put leg (converted to shares if below barrier)
        if spot_final < barrier * strike:
            # Investor receives shares at strike (loses if stock down)
            shares_loss = strike - spot_final
            return coupon_pv - shares_loss
        
        return coupon_pv
    
    # ==================== MOUNTAIN RANGE (VINTAGE EXOTICS) ====================
    
    @staticmethod
    def himalaya(
        spot_paths: np.ndarray,
        observation_dates_idx: List[int],
        **kwargs
    ) -> float:
        """
        Himalaya: Path-dependent option on best-performing assets.
        
        Logic:
        - At each observation date, identify the best-performing asset YTD.
        - Lock in its performance and remove it from the basket.
        - At maturity, sum the locked-in performances.
        
        Args:
            spot_paths: (n_steps, n_assets) array of spot prices along path
            observation_dates_idx: Indices of observation dates in the path
        """
        n_assets = spot_paths.shape[1]
        initial_spots = spot_paths[0, :]
        
        total_return = 0
        remaining_assets = np.arange(n_assets)
        
        for i, obs_idx in enumerate(observation_dates_idx):
            if len(remaining_assets) == 0:
                break
            
            spot_at_obs = spot_paths[obs_idx, remaining_assets]
            perf_at_obs = spot_at_obs / initial_spots[remaining_assets] - 1
            
            best_asset_idx = remaining_assets[np.argmax(perf_at_obs)]
            total_return += np.max(perf_at_obs)
            
            # Remove best asset from future observations
            remaining_assets = remaining_assets[remaining_assets != best_asset_idx]
        
        payoff = 100 * (1 + max(total_return, -0.5))  # Min -50% protection
        return max(payoff, 0)
    
    @staticmethod
    def everest(
        spot_final: np.ndarray,
        spot_initial: np.ndarray,
        barrier_level: float = 0.5,
        **kwargs
    ) -> float:
        """
        Everest: Performance of the worst-performing asset on large basket.
        
        - Designed for long-term visions on uncorrelated basket.
        - Payoff = 100 * (1 + min_performance).
        - Barrier protection if worst performer falls too far.
        """
        worst_perf = np.min(spot_final / spot_initial) - 1
        
        # Barrier protection
        if worst_perf < -barrier_level:
            payoff = 100 * barrier_level
        else:
            payoff = 100 * (1 + worst_perf)
        
        return max(payoff, 50)  # Min floor @ 50
    
    @staticmethod
    def altiplano(
        spot_vector: np.ndarray,
        strikes: np.ndarray,
        coupon: float,
        touch_barrier: float = 0.7,
        **kwargs
    ) -> float:
        """
        Altiplano: Digital coupon conditioned on barrier non-crossing.
        
        - Coupon paid if NO barrier has been breached throughout life.
        - If any asset touches barrier, coupon is forfeited.
        """
        worst_performer = np.min(spot_vector / strikes)
        
        if worst_performer >= touch_barrier:
            return 100 + coupon * 100  # Coupon earned
        else:
            return 100  # Barrier touched, coupon lost
    
    @staticmethod
    def napoleon(
        spot_returns: np.ndarray,
        n_baskets: int = 10,
        observation_windows: int = 4,
        **kwargs
    ) -> float:
        """
        Napoleon: Performance on lowest returns over multiple observation windows.
        
        - Divide observation period into windows.
        - At each window, identify the worst-performing asset.
        - Final payoff = 100 + avg(worst_returns).
        """
        window_size = len(spot_returns) // observation_windows
        worst_returns_per_window = []
        
        for window_idx in range(observation_windows):
            start_idx = window_idx * window_size
            end_idx = min((window_idx + 1) * window_size, len(spot_returns))
            
            window_returns = spot_returns[start_idx:end_idx]
            if len(window_returns) > 0:
                worst_return = np.min(window_returns)
                worst_returns_per_window.append(worst_return)
        
        avg_worst = np.mean(worst_returns_per_window) if worst_returns_per_window else 0
        payoff = 100 * (1 + avg_worst)
        return max(payoff, 50)
    
    # ==================== CUSTOM / HYBRID PRODUCTS ====================
    
    @staticmethod
    def contingent_coupon(
        spot_equity: float,
        spot_fx: float,
        strike_equity: float,
        strike_fx: float,
        coupon: float,
        equity_barrier: float = 1.0,
        fx_barrier_depreciation: float = -0.10,
        **kwargs
    ) -> float:
        """
        Cross-Asset Contingent Coupon:
        - Coupon paid if Equity > Equity_Barrier AND FX_Return > FX_Barrier.
        """
        equity_perf = spot_equity / strike_equity
        fx_perf = spot_fx / strike_fx - 1
        
        if equity_perf >= equity_barrier and fx_perf > fx_barrier_depreciation:
            return 100 + coupon * 100
        else:
            return 100
    
    @staticmethod
    def worst_of_basket_call(
        spot_vector: np.ndarray,
        strikes: np.ndarray,
        payoff_ratio: float = 1.0,
        **kwargs
    ) -> float:
        """
        Worst-of Basket Call.
        Payoff = max(0, (worst_perf / initial) - 1) * payoff_ratio * 100
        """
        worst_perf = np.min(spot_vector / strikes)
        intrinsic = max(worst_perf - 1, 0) * payoff_ratio * 100
        return min(intrinsic, 100)
    
    @staticmethod
    def best_of_basket_call(
        spot_vector: np.ndarray,
        strikes: np.ndarray,
        payoff_ratio: float = 1.0,
        **kwargs
    ) -> float:
        """
        Best-of Basket Call.
        Payoff = max(0, (best_perf / initial) - 1) * payoff_ratio * 100
        """
        best_perf = np.max(spot_vector / strikes)
        intrinsic = max(best_perf - 1, 0) * payoff_ratio * 100
        return min(intrinsic, 200)


class StructuredProductBuilder:
    """Helper class to construct and validate structured products."""
    
    PRODUCT_CATALOG = {
        'phoenix': {
            'func': PayoffLibrary.phoenix,
            'description': 'Memory coupon + protection with autocall',
            'category': 'Modern',
        },
        'athena': {
            'func': PayoffLibrary.athena,
            'description': 'Pure autocall with fixed coupon',
            'category': 'Modern',
        },
        'reverse_convertible': {
            'func': PayoffLibrary.reverse_convertible,
            'description': 'High yield bond with stock downside',
            'category': 'Modern',
        },
        'himalaya': {
            'func': PayoffLibrary.himalaya,
            'description': 'Best asset performance by observation date',
            'category': 'Vintage',
        },
        'everest': {
            'func': PayoffLibrary.everest,
            'description': 'Worst performer on large basket',
            'category': 'Vintage',
        },
        'altiplano': {
            'func': PayoffLibrary.altiplano,
            'description': 'Digital coupon if no barrier breach',
            'category': 'Vintage',
        },
        'napoleon': {
            'func': PayoffLibrary.napoleon,
            'description': 'Worst returns across observation windows',
            'category': 'Vintage',
        },
        'contingent_coupon': {
            'func': PayoffLibrary.contingent_coupon,
            'description': 'Cross-asset coupon (Equity + FX)',
            'category': 'Hybrid',
        },
        'worst_of_basket_call': {
            'func': PayoffLibrary.worst_of_basket_call,
            'description': 'Call on worst-performing asset',
            'category': 'Hybrid',
        },
        'best_of_basket_call': {
            'func': PayoffLibrary.best_of_basket_call,
            'description': 'Call on best-performing asset',
            'category': 'Hybrid',
        },
    }
    
    @classmethod
    def get_product(cls, product_name: str) -> Dict:
        """Retrieve product specifications."""
        return cls.PRODUCT_CATALOG.get(product_name.lower(), None)
    
    @classmethod
    def list_products(cls, category: Optional[str] = None) -> List[str]:
        """List available products, optionally filtered by category."""
        if category:
            return [name for name, spec in cls.PRODUCT_CATALOG.items() 
                   if spec['category'].lower() == category.lower()]
        return list(cls.PRODUCT_CATALOG.keys())
