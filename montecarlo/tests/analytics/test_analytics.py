"""
Unit Tests for Analytics Engines

Tests for correlation, risk, and greeks calculators.

Run with:
    python -m pytest tests/analytics/
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import pandas as pd
import pytest
from analytics.correlation import CorrelationEngine
from analytics.risk import RiskEngine
from analytics.greeks import GreeksCalculator

class TestCorrelationEngine:
    """Test correlation calculation"""
    
    def test_initialization(self):
        """Test engine initialization"""
        engine = CorrelationEngine(lookback_periods=100)
        assert engine.lookback == 100
        assert len(engine.price_history) == 0
    
    def test_add_prices(self):
        """Test adding prices"""
        engine = CorrelationEngine(lookback_periods=10)
        
        engine.add_price("AAPL", 150.0)
        engine.add_price("AAPL", 151.0)
        engine.add_price("MSFT", 345.0)
        
        assert "AAPL" in engine.price_history
        assert len(engine.price_history["AAPL"]) == 2
        assert engine.price_history["AAPL"][-1] == 151.0
    
    def test_lookback_limit(self):
        """Test that old prices are dropped"""
        engine = CorrelationEngine(lookback_periods=5)
        
        for i in range(10):
            engine.add_price("AAPL", 150.0 + i)
        
        # Should only have 5 prices
        assert len(engine.price_history["AAPL"]) == 5
    
    def test_correlation_calculation(self):
        """Test correlation matrix calculation"""
        engine = CorrelationEngine(lookback_periods=50)
        
        np.random.seed(42)
        for _ in range(50):
            engine.add_price("A", 100 + np.random.randn())
            engine.add_price("B", 100 + np.random.randn())
        
        corr = engine. calculate_matrix()
        
        assert corr is not None
        assert len(corr) == 2
        assert abs(corr.loc["A", "A"] - 1.0) < 0.01  # Self-correlation = 1

class TestRiskEngine:
    """Test risk calculations"""
    
    def test_initialization(self):
        """Test engine initialization"""
        risk = RiskEngine(confidence_level=0.95)
        assert risk.confidence == 0.95
        assert len(risk.price_history) == 0
    
    def test_var_calculation(self):
        """Test VaR calculation"""
        risk = RiskEngine(confidence_level=0.95)
        
        # Simulate prices with known distribution
        np.random.seed(42)
        base_price = 100.0
        for _ in range(252):
            price = base_price * (1 + np.random.normal(0.0005, 0.02))
            risk.add_price("TEST", price)
            base_price = price
        
        var_hist = risk.calculate_var_historical("TEST", 1_000_000)
        var_param = risk.calculate_var_parametric("TEST", 1_000_000)
        
        # VaR should be negative (represents a loss)
        assert var_hist < 0
        assert var_param < 0
        
        # Should be reasonable magnitude (not 0, not > 50%)
        assert -500000 < var_hist < 0
        assert -500000 < var_param < 0
    
    def test_cvar_calculation(self):
        """Test CVaR calculation"""
        risk = RiskEngine(confidence_level=0.95)
        
        np.random.seed(42)
        base_price = 100.0
        for _ in range(252):
            price = base_price * (1 + np.random.normal(0.0005, 0.02))
            risk.add_price("TEST", price)
            base_price = price
        
        cvar = risk.calculate_cvar("TEST", 1_000_000)
        var = risk.calculate_var_historical("TEST", 1_000_000)
        
        # CVaR should be more negative (more severe) than VaR
        assert cvar < var  # Both negative, but CVaR > VaR in magnitude
    
    def test_volatility_calculation(self):
        """Test volatility calculation"""
        risk = RiskEngine()
        
        # Create prices with known volatility
        np.random.seed(42)
        base_price = 100.0
        for _ in range(252):
            price = base_price * (1 + np.random.normal(0, 0.01))  # 1% daily vol
            risk.add_price("TEST", price)
            base_price = price
        
        vol = risk.calculate_volatility("TEST")
        
        # Should be roughly 16% (1% * sqrt(252)) annualized
        assert 0.10 < vol < 0.25  # Allow some estimation error
    
    def test_max_drawdown(self):
        """Test maximum drawdown calculation"""
        risk = RiskEngine()
        
        # Create prices with a known drawdown
        prices = [100, 110, 120, 100, 90, 100, 110]  # 25% drawdown
        for p in prices:
            risk.add_price("TEST", p)
        
        max_dd, from_idx, to_idx = risk.calculate_max_drawdown("TEST")
        
        assert max_dd < 0  # Should be negative
        assert abs(max_dd) > 0.20  # At least 20% drawdown

class TestGreeksCalculator:
    """Test options Greeks calculation"""
    
    def test_black_scholes_call(self):
        """Test Black-Scholes call pricing"""
        S = 100  # Spot
        K = 100  # Strike (ATM)
        r = 0.05
        sigma = 0.2
        T = 1.0  # 1 year
        
        price, d1, d2 = GreeksCalculator.black_scholes(S, K, r, sigma, T, "call")
        
        # ATM call should be worth something
        assert price > 0
        # Properties: ATM call ≈ 10% of spot
        assert 5 < price < 15
    
    def test_delta_calculation(self):
        """Test delta calculation"""
        S = 100
        K = 100
        r = 0.05
        sigma = 0.2
        T = 1.0
        
        delta = GreeksCalculator.delta(S, K, r, sigma, T, "call")
        
        # ATM call delta should be around 0.6
        assert 0.5 < delta < 0.7
        
        # ITM call (S > K)
        delta_itm = GreeksCalculator.delta(110, 100, r, sigma, T, "call")
        assert delta_itm > delta
        
        # OTM call (S < K)
        delta_otm = GreeksCalculator.delta(90, 100, r, sigma, T, "call")
        assert delta_otm < delta
    
    def test_gamma_calculation(self):
        """Test gamma calculation"""
        S = 100
        K = 100
        r = 0.05
        sigma = 0.2
        T = 1.0
        
        gamma = GreeksCalculator.gamma(S, K, r, sigma, T, "call")
        
        # Gamma should be positive and non-zero
        assert gamma > 0
        assert gamma < 0.05
    
    def test_vega_calculation(self):
        """Test vega calculation"""
        S = 100
        K = 100
        r = 0.05
        sigma = 0.2
        T = 1.0
        
        vega = GreeksCalculator.vega(S, K, r, sigma, T, "call")
        
        # Vega should be positive
        assert vega > 0
    
    def test_theta_calculation(self):
        """Test theta calculation"""
        S = 100
        K = 100
        r = 0.05
        sigma = 0.2
        T = 0.25  # 3 months
        
        # Theta should be negative (time value decays)
        theta = GreeksCalculator.theta(S, K, r, sigma, T, "call")
        assert theta < 0
    
    def test_put_call_parity(self):
        """Test put-call parity relationship"""
        S = 100
        K = 100
        r = 0.05
        sigma = 0.2
        T = 1.0
        
        call_price = GreeksCalculator.price(S, K, r, sigma, T, "call")
        put_price = GreeksCalculator.price(S, K, r, sigma, T, "put")
        
        # Put-Call Parity: C - P = S - K*e^(-rT)
        theoretical_diff = S - K * np.exp(-r * T)
        actual_diff = call_price - put_price
        
        # Should be approximately equal
        assert abs(actual_diff - theoretical_diff) < 0.01

# ================================
# INTEGRATION TESTS
# ================================

def test_full_scenario():
    """Test a full scenario with correlation + risk + Greeks"""
    
    # 1. Build correlation matrix
    corr_engine = CorrelationEngine(lookback_periods=100)
    np.random.seed(42)
    
    for _ in range(100):
        corr_engine.add_price("AAPL", 100 + np.random.randn())
        corr_engine.add_price("MSFT", 200 + np.random.randn())
    
    corr_matrix = corr_engine.calculate_matrix()
    assert corr_matrix is not None
    
    # 2. Calculate portfolio risk
    risk_engine = RiskEngine(confidence_level=0.95)
    
    for _ in range(252):
        risk_engine.add_price("AAPL", 100 + np.random.randn())
        risk_engine.add_price("MSFT", 200 + np.random.randn())
    
    positions = {"AAPL": 100000, "MSFT": 200000}
    port_var = risk_engine.calculate_portfolio_var(positions, corr_matrix)
    
    assert port_var < 0
    assert -300000 < port_var < 0
    
    # 3. Calculate Greeks
    call_price = GreeksCalculator.price(150, 150, 0.05, 0.25, 0.1667, "call")
    assert call_price > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
