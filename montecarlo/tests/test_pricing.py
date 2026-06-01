"""Unit tests for option pricing models"""

import pytest
import numpy as np
from src.pricing import BlackScholes, MonteCarlo


class TestBlackScholes:
    """Test Black-Scholes pricing model"""
    
    def test_call_price_positive(self):
        """Call price should be positive"""
        price = BlackScholes.call_price(S=100, K=100, T=1, r=0.05, sigma=0.2)
        assert price > 0
    
    def test_put_price_positive(self):
        """Put price should be positive"""
        price = BlackScholes.put_price(S=100, K=100, T=1, r=0.05, sigma=0.2)
        assert price > 0
    
    def test_call_price_itm(self):
        """In-the-money call should be worth at least intrinsic value"""
        S, K = 110, 100
        price = BlackScholes.call_price(S=S, K=K, T=1, r=0.05, sigma=0.2)
        intrinsic = S - K
        assert price >= intrinsic
    
    def test_put_price_itm(self):
        """In-the-money put should be worth at least intrinsic value"""
        S, K = 90, 100
        price = BlackScholes.put_price(S=S, K=K, T=1, r=0.05, sigma=0.2)
        intrinsic = K - S
        assert price >= intrinsic
    
    def test_delta_call_range(self):
        """Call delta should be between 0 and 1"""
        delta = BlackScholes.delta_call(S=100, K=100, T=1, r=0.05, sigma=0.2)
        assert 0 <= delta <= 1
    
    def test_delta_put_range(self):
        """Put delta should be between -1 and 0"""
        delta = BlackScholes.delta_put(S=100, K=100, T=1, r=0.05, sigma=0.2)
        assert -1 <= delta <= 0
    
    def test_gamma_positive(self):
        """Gamma should be positive for both calls and puts"""
        gamma = BlackScholes.gamma(S=100, K=100, T=1, r=0.05, sigma=0.2)
        assert gamma > 0
    
    def test_vega_positive(self):
        """Vega should be positive for both calls and puts"""
        vega = BlackScholes.vega(S=100, K=100, T=1, r=0.05, sigma=0.2)
        assert vega > 0
    
    def test_invalid_inputs(self):
        """Test that invalid inputs raise ValueError"""
        with pytest.raises(ValueError):
            BlackScholes.call_price(S=-100, K=100, T=1, r=0.05, sigma=0.2)
        
        with pytest.raises(ValueError):
            BlackScholes.call_price(S=100, K=0, T=1, r=0.05, sigma=0.2)
        
        with pytest.raises(ValueError):
            BlackScholes.call_price(S=100, K=100, T=0, r=0.05, sigma=0.2)
        
        with pytest.raises(ValueError):
            BlackScholes.call_price(S=100, K=100, T=1, r=0.05, sigma=0)


class TestMonteCarlo:
    """Test Monte Carlo pricing model"""
    
    def test_call_price_positive(self):
        """Call price should be positive"""
        price = MonteCarlo.call_price(S=100, K=100, T=1, r=0.05, sigma=0.2, num_simulations=1000)
        assert price > 0
    
    def test_put_price_positive(self):
        """Put price should be positive"""
        price = MonteCarlo.put_price(S=100, K=100, T=1, r=0.05, sigma=0.2, num_simulations=1000)
        assert price > 0
    
    def test_convergence_to_bs(self):
        """Monte Carlo should converge to Black-Scholes with many simulations"""
        S, K, T, r, sigma = 100, 100, 1, 0.05, 0.2
        
        bs_call = BlackScholes.call_price(S, K, T, r, sigma)
        mc_call = MonteCarlo.call_price(S, K, T, r, sigma, num_simulations=50000)
        
        # Should be within 5% of Black-Scholes
        assert abs(mc_call - bs_call) / bs_call < 0.05
    
    def test_invalid_inputs(self):
        """Test that invalid inputs raise ValueError"""
        with pytest.raises(ValueError):
            MonteCarlo.call_price(S=-100, K=100, T=1, r=0.05, sigma=0.2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
