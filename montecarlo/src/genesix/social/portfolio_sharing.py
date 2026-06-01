"""
Social Trading & Portfolio Sharing System.

Users can:
1. Save portfolio configurations with names
2. Share via unique URL or code
3. Track performance over time
4. View leaderboard of best-performing portfolios
5. Clone other users' portfolios

Storage: local JSON (v2), upgradeable to SQLite/API backend
Privacy: anonymous by default, public opt-in
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
import logging
import pandas as pd

logger = logging.getLogger(__name__)

class PortfolioManager:
    """Portfolio saving, sharing, and leaderboard system."""
    
    def __init__(self, storage_dir: str = '.genesix/portfolios'):
        """Initialize portfolio manager."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.portfolios_file = self.storage_dir / 'portfolios.json'
        self.performance_file = self.storage_dir / 'performance.json'
        self._ensure_files()
    
    def _ensure_files(self):
        """Ensure storage files exist."""
        if not self.portfolios_file.exists():
            self.portfolios_file.write_text(json.dumps({}))
        if not self.performance_file.exists():
            self.performance_file.write_text(json.dumps({}))
    
    def save_portfolio(self, 
                       name: str, 
                       weights: dict[str, float],
                       description: str = "", 
                       public: bool = False) -> str:
        """
        Save portfolio configuration.
        
        Args:
            name: Display name
            weights: {'AAPL': 0.4, 'MSFT': 0.3, 'BND': 0.3}
            description: Optional description
            public: If True, portfolio visible on leaderboard
        
        Returns:
            portfolio_id (8-char hash)
        """
        try:
            # Generate unique ID
            data_str = json.dumps(weights) + datetime.now().isoformat()
            portfolio_id = hashlib.md5(data_str.encode()).hexdigest()[:8]
            
            # Load existing
            with open(self.portfolios_file) as f:
                portfolios = json.load(f)
            
            # Save new
            portfolios[portfolio_id] = {
                'id': portfolio_id,
                'name': name,
                'description': description,
                'weights': weights,
                'public': public,
                'created_date': datetime.now().isoformat(),
                'creator': f'user_{hashlib.md5(portfolio_id.encode()).hexdigest()[:6]}',
            }
            
            with open(self.portfolios_file, 'w') as f:
                json.dump(portfolios, f, indent=2)
            
            logger.info(f"Portfolio {portfolio_id} saved: {name}")
            return portfolio_id
        
        except Exception as e:
            logger.error(f"Failed to save portfolio: {e}")
            raise
    
    def load_portfolio(self, portfolio_id: str) -> dict:
        """Load a saved portfolio by ID."""
        try:
            with open(self.portfolios_file) as f:
                portfolios = json.load(f)
            
            return portfolios.get(portfolio_id, {})
        
        except Exception as e:
            logger.error(f"Failed to load portfolio {portfolio_id}: {e}")
            raise
    
    def list_portfolios(self, public_only: bool = False) -> list[dict]:
        """List all saved portfolios."""
        try:
            with open(self.portfolios_file) as f:
                portfolios = json.load(f)
            
            result = list(portfolios.values())
            if public_only:
                result = [p for p in result if p.get('public', False)]
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to list portfolios: {e}")
            return []
    
    def track_performance(self, portfolio_id: str) -> dict:
        """
        Track real performance of a saved portfolio since creation.
        
        Returns:
            {
                'portfolio_id': str,
                'name': str,
                'performance': {
                    'total_return': float,
                    'annualized_return': float,
                    'sharpe': float,
                },
                'equity_curve': list[float],
            }
        """
        try:
            portfolio = self.load_portfolio(portfolio_id)
            
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found")
            
            # Load performance data
            with open(self.performance_file) as f:
                perf_data = json.load(f)
            
            portfolio_perf = perf_data.get(portfolio_id, {})
            
            return {
                'portfolio_id': portfolio_id,
                'name': portfolio.get('name', ''),
                'created_date': portfolio.get('created_date'),
                'weights': portfolio.get('weights'),
                'performance': portfolio_perf.get('metrics', {}),
                'equity_curve': portfolio_perf.get('equity_curve', []),
            }
        
        except Exception as e:
            logger.error(f"Failed to track performance: {e}")
            raise
    
    def leaderboard(self, period: str = '1m', limit: int = 20) -> pd.DataFrame:
        """
        Top performing public portfolios.
        
        period: '1w', '1m', '3m', 'ytd', '1y'
        
        Returns:
            DataFrame with rank, name, creator, return, sharpe, n_assets
        """
        try:
            portfolios = self.list_portfolios(public_only=True)
            
            # Would fetch performance from backend in real system
            # For now, return template
            results = []
            for i, p in enumerate(portfolios[:limit], 1):
                results.append({
                    'rank': i,
                    'name': p.get('name', 'Portfolio'),
                    'creator': p.get('creator', 'Anonymous'),
                    'return_pct': 0.0,  # would calculate
                    'sharpe': 0.0,      # would calculate
                    'max_dd': 0.0,      # would calculate
                    'n_assets': len(p.get('weights', {})),
                })
            
            return pd.DataFrame(results)
        
        except Exception as e:
            logger.error(f"Failed to generate leaderboard: {e}")
            return pd.DataFrame()
    
    def generate_share_url(self, portfolio_id: str) -> str:
        """Generate shareable URL with portfolio encoded in params."""
        portfolio = self.load_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # URL format: would be built by frontend
        # Example: /genesix?page=screener&portfolio={portfolio_id}
        return f"genesix://portfolio/{portfolio_id}"
    
    def clone_portfolio(self, portfolio_id: str, new_name: str) -> str:
        """Clone someone else's public portfolio."""
        try:
            original = self.load_portfolio(portfolio_id)
            
            if not original or not original.get('public'):
                raise ValueError("Portfolio is private or not found")
            
            # Save as new portfolio
            new_id = self.save_portfolio(
                name=new_name,
                weights=original.get('weights', {}),
                description=f"Cloned from '{original.get('name')}' by {original.get('creator')}",
                public=False
            )
            
            logger.info(f"Cloned {portfolio_id} as {new_id}")
            return new_id
        
        except Exception as e:
            logger.error(f"Failed to clone portfolio: {e}")
            raise
