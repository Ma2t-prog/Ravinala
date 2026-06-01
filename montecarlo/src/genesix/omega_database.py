"""
OMEGA Database - Stock/ETF/Asset recommendations and Broker comparisons

Backend data layer for intelligent asset selection and broker optimization.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

# ============================================================================
# STOCK & ETF DATABASE
# ============================================================================

class AssetDatabase:
    """Database of recommended stocks, ETFs, and crypto assets by allocation profile."""
    
    # CONSERVATIVE ASSETS
    CONSERVATIVE_BONDS = [
        {
            'ticker': 'BND',
            'name': 'Vanguard Total Bond Market ETF',
            'type': 'ETF',
            'allocation': '30-40%',
            'expense_ratio': 0.03,
            'dividend_yield': 4.5,
            'risk_level': 1,
            'description': 'Broad bond market exposure with low fees'
        },
        {
            'ticker': 'AGG',
            'name': 'iShares Core U.S. Aggregate Bond ETF',
            'type': 'ETF',
            'allocation': '30-40%',
            'expense_ratio': 0.03,
            'dividend_yield': 4.8,
            'risk_level': 1,
            'description': 'Investment-grade bonds, most liquid'
        },
        {
            'ticker': 'SHV',
            'name': 'iShares Short Treasury Bond ETF',
            'type': 'ETF',
            'allocation': '10-15%',
            'expense_ratio': 0.15,
            'dividend_yield': 5.2,
            'risk_level': 0.5,
            'description': 'Short-duration treasuries for capital preservation'
        },
    ]
    
    CONSERVATIVE_DIVIDEND_STOCKS = [
        {
            'ticker': 'JNJ',
            'name': 'Johnson & Johnson',
            'type': 'Stock',
            'allocation': '5-8%',
            'expense_ratio': 0,
            'dividend_yield': 2.9,
            'risk_level': 2,
            'description': 'Pharma giant, 60+ years of dividend growth',
            'sector': 'Healthcare'
        },
        {
            'ticker': 'PG',
            'name': 'Procter & Gamble',
            'type': 'Stock',
            'allocation': '5-8%',
            'expense_ratio': 0,
            'dividend_yield': 2.5,
            'risk_level': 2,
            'description': 'Consumer staples, recession-resistant',
            'sector': 'Consumer Staples'
        },
        {
            'ticker': 'KO',
            'name': 'Coca-Cola',
            'type': 'Stock',
            'allocation': '3-5%',
            'expense_ratio': 0,
            'dividend_yield': 3.1,
            'risk_level': 2,
            'description': 'Beverage leader, global presence',
            'sector': 'Consumer Staples'
        },
        {
            'ticker': 'VYM',
            'name': 'Vanguard High Dividend Yield ETF',
            'type': 'ETF',
            'allocation': '7-10%',
            'expense_ratio': 0.06,
            'dividend_yield': 3.2,
            'risk_level': 2,
            'description': 'Diversified high-yield dividend stocks',
            'sector': 'Mixed'
        },
    ]
    
    CONSERVATIVE_GOLD = [
        {
            'ticker': 'GLD',
            'name': 'SPDR Gold Trust',
            'type': 'ETF',
            'allocation': '10-15%',
            'expense_ratio': 0.40,
            'dividend_yield': 0,
            'risk_level': 2,
            'description': 'Physical gold exposure, inflation hedge'
        },
        {
            'ticker': 'IAU',
            'name': 'iShares Gold Trust',
            'type': 'ETF',
            'allocation': '10-15%',
            'expense_ratio': 0.25,
            'dividend_yield': 0,
            'risk_level': 2,
            'description': 'Lower-cost gold ETF'
        },
    ]
    
    CONSERVATIVE_REITS = [
        {
            'ticker': 'VNQ',
            'name': 'Vanguard Real Estate ETF',
            'type': 'ETF',
            'allocation': '3-5%',
            'expense_ratio': 0.12,
            'dividend_yield': 3.8,
            'risk_level': 3,
            'description': 'Diversified REIT exposure across all property types'
        },
    ]
    
    # MODERATE ASSETS
    MODERATE_GROWTH_STOCKS = [
        {
            'ticker': 'VOO',
            'name': 'Vanguard S&P 500 ETF',
            'type': 'ETF',
            'allocation': '15-20%',
            'expense_ratio': 0.03,
            'dividend_yield': 1.8,
            'risk_level': 4,
            'description': 'Core US large cap, 500 largest companies'
        },
        {
            'ticker': 'VTI',
            'name': 'Vanguard Total Stock Market ETF',
            'type': 'ETF',
            'allocation': '15-20%',
            'expense_ratio': 0.03,
            'dividend_yield': 1.5,
            'risk_level': 4,
            'description': 'Total US market, includes mid/small caps'
        },
        {
            'ticker': 'MSFT',
            'name': 'Microsoft',
            'type': 'Stock',
            'allocation': '3-5%',
            'expense_ratio': 0,
            'dividend_yield': 0.7,
            'risk_level': 4,
            'description': 'Tech giant, cloud dominance, strong AI position',
            'sector': 'Technology'
        },
        {
            'ticker': 'AAPL',
            'name': 'Apple',
            'type': 'Stock',
            'allocation': '2-3%',
            'expense_ratio': 0,
            'dividend_yield': 0.4,
            'risk_level': 4,
            'description': 'Consumer tech, services growth story',
            'sector': 'Technology'
        },
    ]
    
    MODERATE_BONDS = [
        {
            'ticker': 'BND',
            'name': 'Vanguard Total Bond Market ETF',
            'type': 'ETF',
            'allocation': '20-30%',
            'expense_ratio': 0.03,
            'dividend_yield': 4.5,
            'risk_level': 1,
            'description': 'Broad bond market for stability'
        },
    ]
    
    MODERATE_REAL_ESTATE = [
        {
            'ticker': 'SCHH',
            'name': 'Schwab US REIT ETF',
            'type': 'ETF',
            'allocation': '10-15%',
            'expense_ratio': 0.07,
            'dividend_yield': 4.2,
            'risk_level': 3,
            'description': 'Diversified real estate across sectors'
        },
    ]
    
    MODERATE_COMMODITIES = [
        {
            'ticker': 'DBC',
            'name': 'Commodities ETF',
            'type': 'ETF',
            'allocation': '8-12%',
            'expense_ratio': 0.87,
            'dividend_yield': 0,
            'risk_level': 4,
            'description': 'Broad commodities exposure (energy, metals, agriculture)'
        },
        {
            'ticker': 'GLD',
            'name': 'SPDR Gold Trust',
            'type': 'ETF',
            'allocation': '3-5%',
            'expense_ratio': 0.40,
            'dividend_yield': 0,
            'risk_level': 3,
            'description': 'Gold hedge'
        },
    ]
    
    # AGGRESSIVE ASSETS
    AGGRESSIVE_GROWTH = [
        {
            'ticker': 'QQQ',
            'name': 'Invesco QQQ Nasdaq-100 ETF',
            'type': 'ETF',
            'allocation': '20-30%',
            'expense_ratio': 0.20,
            'dividend_yield': 0.4,
            'risk_level': 6,
            'description': 'Heavy tech exposure, highest growth potential'
        },
        {
            'ticker': 'VUG',
            'name': 'Vanguard Growth ETF',
            'type': 'ETF',
            'allocation': '15-25%',
            'expense_ratio': 0.04,
            'dividend_yield': 0.9,
            'risk_level': 5,
            'description': 'US growth stocks screening'
        },
        {
            'ticker': 'NVDA',
            'name': 'NVIDIA',
            'type': 'Stock',
            'allocation': '2-4%',
            'expense_ratio': 0,
            'dividend_yield': 0.03,
            'risk_level': 7,
            'description': 'AI and GPU leader, high volatility',
            'sector': 'Technology'
        },
        {
            'ticker': 'TSLA',
            'name': 'Tesla',
            'type': 'Stock',
            'allocation': '1-2%',
            'expense_ratio': 0,
            'dividend_yield': 0,
            'risk_level': 8,
            'description': 'EV and energy leader, high growth/risk',
            'sector': 'Consumer Cyclical'
        },
    ]
    
    AGGRESSIVE_EMERGING_MARKETS = [
        {
            'ticker': 'VWO',
            'name': 'Vanguard FTSE Emerging Markets ETF',
            'type': 'ETF',
            'allocation': '15-20%',
            'expense_ratio': 0.08,
            'dividend_yield': 2.5,
            'risk_level': 6,
            'description': 'Emerging market exposure (China, India, Brazil, etc.)'
        },
    ]
    
    AGGRESSIVE_TECH_INNOVATION = [
        {
            'ticker': 'ARK',
            'name': 'Cathie Wood Innovation ETF',
            'type': 'ETF',
            'allocation': '10-15%',
            'expense_ratio': 0.75,
            'dividend_yield': 0,
            'risk_level': 7,
            'description': 'Disruptive innovation (AI, biotech, robotics, blockchain)'
        },
        {
            'ticker': 'XBI',
            'name': 'SPDR S&P Biotech ETF',
            'type': 'ETF',
            'allocation': '5-10%',
            'expense_ratio': 0.35,
            'dividend_yield': 0,
            'risk_level': 7,
            'description': 'Biotech and gene therapy leaders'
        },
    ]
    
    AGGRESSIVE_CRYPTO = [
        {
            'ticker': 'GBTC',
            'name': 'Grayscale Bitcoin Mini Trust',
            'type': 'ETF',
            'allocation': '5-10%',
            'expense_ratio': 1.50,
            'dividend_yield': 0,
            'risk_level': 8,
            'description': 'Bitcoin exposure via trust'
        },
        {
            'ticker': 'ETHE',
            'name': 'Grayscale Ethereum Mini Trust',
            'type': 'ETF',
            'allocation': '2-5%',
            'expense_ratio': 1.50,
            'dividend_yield': 0,
            'risk_level': 8,
            'description': 'Ethereum exposure via trust'
        },
    ]
    
    @classmethod
    def get_recommendations(cls, risk_profile: str) -> Dict[str, List[Dict]]:
        """Get asset recommendations for a given risk profile."""
        if risk_profile == "Conservative":
            return {
                "Bonds": cls.CONSERVATIVE_BONDS,
                "Dividend Stocks": cls.CONSERVATIVE_DIVIDEND_STOCKS,
                "Gold": cls.CONSERVATIVE_GOLD,
                "REITs": cls.CONSERVATIVE_REITS,
            }
        elif risk_profile == "Moderate":
            return {
                "Growth Stocks": cls.MODERATE_GROWTH_STOCKS,
                "Bonds": cls.MODERATE_BONDS,
                "Real Estate": cls.MODERATE_REAL_ESTATE,
                "Commodities": cls.MODERATE_COMMODITIES,
            }
        elif risk_profile == "Aggressive":
            return {
                "Growth Stocks": cls.AGGRESSIVE_GROWTH,
                "Emerging Markets": cls.AGGRESSIVE_EMERGING_MARKETS,
                "Tech/Innovation": cls.AGGRESSIVE_TECH_INNOVATION,
                "Crypto": cls.AGGRESSIVE_CRYPTO,
            }
        
        return {}


# ============================================================================
# BROKER DATABASE
# ============================================================================

class BrokerDatabase:
    """Database of major brokers with fee structures and features."""
    
    BROKERS = [
        {
            'name': 'Interactive Brokers',
            'symbol': 'IBKR',
            'stock_commission': 0.001,  # $0.001 per share
            'etf_commission': 0,
            'forex_spread': 0.002,
            'options_per_contract': 0.65,
            'account_minimum': 100,
            'rating': 9.2,
            'best_for': 'Active traders, international access',
            'pros': [
                'v Lowest commissions',
                'v Global market access',
                'v Advanced tools',
                'v Margin available'
            ],
            'cons': [
                'x Steep learning curve',
                'x Less hand-holding',
            ]
        },
        {
            'name': 'Fidelity',
            'symbol': 'FDX',
            'stock_commission': 0,
            'etf_commission': 0,
            'forex_spread': 0.010,
            'options_per_contract': 0.65,
            'account_minimum': 0,
            'rating': 8.9,
            'best_for': 'Beginners and long-term investors',
            'pros': [
                'v Zero commissions',
                'v Great research',
                'v Excellent customer service',
                'v Robo-advisor (Fidelity Go)'
            ],
            'cons': [
                'x Less international access',
                'x Platform less advanced'
            ]
        },
        {
            'name': 'Charles Schwab',
            'symbol': 'SCHW',
            'stock_commission': 0,
            'etf_commission': 0,
            'forex_spread': 0.001,
            'options_per_contract': 0.65,
            'account_minimum': 0,
            'rating': 8.8,
            'best_for': 'Comprehensive investing needs',
            'pros': [
                'v Zero commissions',
                'v Excellent mobile app',
                'v Strong research',
                'v TDAmeritrade integration'
            ],
            'cons': [
                'x Similar to Fidelity',
            ]
        },
        {
            'name': 'Alpaca',
            'symbol': 'APCA',
            'stock_commission': 0,
            'etf_commission': 0,
            'forex_spread': 0.001,
            'options_per_contract': 0.00,  # Paper trading free
            'account_minimum': 100,
            'rating': 8.5,
            'best_for': 'Algo traders, API access',
            'pros': [
                'v Commission-free',
                'v Excellent API',
                'v Paper trading',
                'v Fractional shares'
            ],
            'cons': [
                'x Less research tools',
                'x Limited banking features'
            ]
        },
        {
            'name': 'Wise (Transferwise)',
            'symbol': 'WISE',
            'stock_commission': 0,
            'etf_commission': 0,
            'forex_spread': 0.0020,
            'options_per_contract': 'N/A',
            'account_minimum': 0,
            'rating': 9.4,
            'best_for': 'International transfers, multi-currency',
            'pros': [
                'v Lowest FX rates',
                'v Multi-currency accounts',
                'v Fast transfers',
                'v Great for expats'
            ],
            'cons': [
                'x Not full-service broker',
                'x Limited stock trading'
            ]
        },
    ]
    
    @classmethod
    def get_brokers_ranked(cls, priority: str = 'commission') -> List[Dict]:
        """Get brokers ranked by priority (commission, rating, etc.)."""
        if priority == 'commission':
            return sorted(cls.BROKERS, 
                         key=lambda x: x['stock_commission'] + x['etf_commission'])
        elif priority == 'rating':
            return sorted(cls.BROKERS, key=lambda x: x['rating'], reverse=True)
        else:
            return cls.BROKERS
    
    @classmethod
    def estimate_fees(cls, broker_name: str, portfolio_value: float, 
                     num_trades: int = 0) -> Dict:
        """Estimate fees for a given broker."""
        broker = next(b for b in cls.BROKERS if b['name'] == broker_name)
        
        annual_fees = {
            'commission': num_trades * 10 * broker['stock_commission'],  # Approx
            'forex': portfolio_value * broker['forex_spread'] * 0.1,  # If 10% forex
            'total': 0
        }
        annual_fees['total'] = annual_fees['commission'] + annual_fees['forex']
        
        annual_fees['percentage'] = (annual_fees['total'] / portfolio_value * 100) if portfolio_value > 0 else 0
        
        return annual_fees


if __name__ == "__main__":
    # Test
    assets = AssetDatabase.get_recommendations("Conservative")
    print("Conservative Recommendations:")
    for category, assets_list in assets.items():
        print(f"\n{category}:")
        for asset in assets_list[:2]:
            print(f"  - {asset['ticker']}: {asset['name']}")
    
    brokers = BrokerDatabase.get_brokers_ranked('rating')
    print("\n\nTop Brokers by Rating:")
    for broker in brokers[:3]:
        print(f"  {broker['name']}: {broker['rating']}/10")
