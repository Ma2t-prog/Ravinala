"""
Market anomaly and regime detection.

Detects:
1. Volatility regimes (low/normal/elevated/high/extreme)
2. Correlation regime changes
3. Bubble indicators
4. Composite market health scoring (GREEN to BLACK alert levels)
"""

import logging
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Market anomaly and regime detection engine."""
    
    def __init__(self):
        """Initialize detector."""
        try:
            from ..risk.risk_engine import GenesiXRiskEngine
            from ..risk.correlation import CorrelationAnalyzer
            from ..data.feature_store import FeatureStore
            
            self.risk_engine = GenesiXRiskEngine()
            self.correlation = CorrelationAnalyzer()
            self.feature_store = FeatureStore()
        except ImportError:
            logger.warning("Some dependencies not available for anomaly detection")
            self.risk_engine = None
            self.correlation = None
            self.feature_store = None
    
    def detect_volatility_regime(self, asset: str) -> dict:
        """Current volatility regime for an asset."""
        try:
            from ..data.market_fetcher import MarketDataFetcher
            market = MarketDataFetcher()
            data = market.get_historical_ohlcv(asset)

            if data is None or len(data) == 0:
                return {'regime': 'normal', 'error': 'No data available'}

            returns = data['close'].pct_change().dropna()
            
            # Current volatility (annualized)
            current_vol = returns.tail(20).std() * np.sqrt(252)
            
            # Historical distribution
            hist_vols = []
            for i in range(60, len(returns)):
                vol = returns.iloc[i-60:i].std() * np.sqrt(252)
                hist_vols.append(vol)
            
            hist_vols = np.array(hist_vols)
            hist_mean = float(hist_vols.mean()) if hist_vols.size > 0 else float(current_vol)
            percentile = (hist_vols < current_vol).sum() / len(hist_vols) * 100 if hist_vols.size > 0 else 50
            
            # Regime classification
            if current_vol < percentile / 100 * hist_mean * 0.5:
                regime = 'low'
            elif current_vol < percentile / 100 * hist_mean * 0.8:
                regime = 'normal'
            elif current_vol < percentile / 100 * hist_mean * 1.2:
                regime = 'elevated'
            elif current_vol < percentile / 100 * hist_mean * 1.5:
                regime = 'high'
            else:
                regime = 'extreme'
            
            return {
                'asset': asset,
                'regime': regime,
                'current_vol_annualized': float(current_vol),
                'percentile_1y': float(percentile),
                'vix_confirmation': regime in ['high', 'extreme'],
            }
        except Exception as e:
            logger.warning(f"Volatility regime detection failed for {asset}: {e}")
            return {'asset': asset, 'regime': 'normal', 'error': str(e)}
    
    def detect_regime_change(self, asset: str, lookback_days: int = 252) -> dict:
        """Detect if a regime change occurred recently."""
        try:
            from ..data.market_fetcher import MarketDataFetcher
            market = MarketDataFetcher()
            data = market.get_historical_ohlcv(asset)

            if data is None or len(data) < lookback_days + 20:
                return {'regime_change_detected': False, 'change_type': None}

            returns = data['close'].pct_change().dropna()
            
            # Compare last 20 days vs previous 60 days
            vol_recent = returns.tail(20).std() * np.sqrt(252)
            vol_prior = returns.iloc[-80:-20].std() * np.sqrt(252)
            
            ratio = vol_recent / (vol_prior + 1e-10)
            
            if ratio > 2.0:
                change_type = 'vol_spike'
                detected = True
            elif ratio < 0.5:
                change_type = 'vol_collapse'
                detected = True
            else:
                change_type = None
                detected = False
            
            return {
                'regime_change_detected': detected,
                'change_type': change_type,
                'magnitude': float(abs(ratio - 1.0)),
                'date_detected': datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"Regime change detection failed: {e}")
            return {'regime_change_detected': False, 'change_type': None}
    
    def detect_bubble_risk(self, asset: str) -> dict:
        """Bubble indicators for an asset."""
        try:
            from ..data.market_fetcher import MarketDataFetcher
            market = MarketDataFetcher()
            data = market.get_historical_ohlcv(asset)
            
            if data is None or len(data) < 200:
                return {
                    'asset': asset,
                    'bubble_score': 0.0,
                    'risk_level': 'none',
                    'signals': {},
                }
            
            prices = data['close'] if 'close' in data.columns else data
            
            # Price deviation signal
            ma200 = prices.rolling(200).mean()
            deviation = (prices.iloc[-1] / ma200.iloc[-1] - 1) if ma200.iloc[-1] > 0 else 0
            price_dev_score = min(1.0, abs(deviation) / 1.0)  # 1.0 = 100% above MA
            
            # Volume divergence (simplified)
            volume_div_score = 0.3  # Placeholder
            
            # Momentum (price 2nd derivative)
            mom_score = 0.2  # Placeholder
            
            # Composite score
            bubble_score = min(1.0, (price_dev_score + volume_div_score + mom_score) / 3)
            
            if bubble_score < 0.3:
                risk_level = 'none'
            elif bubble_score < 0.5:
                risk_level = 'low'
            elif bubble_score < 0.7:
                risk_level = 'moderate'
            elif bubble_score < 0.85:
                risk_level = 'high'
            else:
                risk_level = 'extreme'
            
            return {
                'asset': asset,
                'bubble_score': float(bubble_score),
                'risk_level': risk_level,
                'signals': {
                    'price_deviation': {'score': float(price_dev_score), 'detail': f'price is {deviation*100:.1f}% from 200d MA'},
                },
            }
        except Exception as e:
            logger.warning(f"Bubble detection failed: {e}")
            return {'asset': asset, 'bubble_score': 0.0, 'risk_level': 'none', 'signals': {}}
    
    def detect_momentum_crash_risk(self, assets: list[str]) -> dict:
        """Detect if momentum factor is at risk of crashing."""
        try:
            from ..data.market_fetcher import MarketDataFetcher
            market = MarketDataFetcher()
            
            momentums = []
            for asset in assets:
                data = market.get_historical_ohlcv(asset)
                if data is not None and len(data) >= 126:
                    momentum = (data['close'].iloc[-1] / data['close'].iloc[-126] - 1)
                    momentums.append((asset, momentum))
            
            if not momentums:
                return {'crash_risk': 'low', 'momentum_spread_percentile': 50}
            
            momentums.sort(key=lambda x: x[1])
            bucket = max(1, len(momentums) // 5)
            winners_slice = momentums[-bucket:]
            losers_slice = momentums[:bucket]
            winners = [m[0] for m in winners_slice]
            losers = [m[0] for m in losers_slice]

            winner_mean = float(np.mean([m[1] for m in winners_slice])) if winners_slice else 0.0
            loser_mean = float(np.mean([m[1] for m in losers_slice])) if losers_slice else 0.0
            spread = winner_mean - loser_mean
            
            # Compute percentile from actual spread data
            percentile = min(max(spread * 100 + 50, 0), 100)  # Map spread to 0-100 percentile
            
            if percentile > 80:
                crash_risk = 'high'
            elif percentile > 60:
                crash_risk = 'moderate'
            else:
                crash_risk = 'low'
            
            return {
                'crash_risk': crash_risk,
                'momentum_spread_percentile': float(percentile),
                'winners': winners,
                'losers': losers,
            }
        except Exception as e:
            logger.warning(f"Momentum crash detection failed: {e}")
            return {'crash_risk': 'low', 'momentum_spread_percentile': 50}
    
    def composite_alert_level(self) -> dict:
        """THE overall market health check."""
        try:
            # Base score
            score = 50
            
            # Volatility component (assume normal for now)
            vol_regime = self.detect_volatility_regime('SPY')
            vol_regime_map = {'low': -10, 'normal': 0, 'elevated': +10, 'high': +15, 'extreme': +25}
            score += vol_regime_map.get(vol_regime.get('regime', 'normal'), 0)
            
            # Bubble risk
            bubble = self.detect_bubble_risk('SPY')
            if bubble.get('bubble_score', 0) > 0.7:
                score += 10
            
            # Momentum crash risk
            momentum = self.detect_momentum_crash_risk(['SPY', 'QQQ', 'IWM'])
            if momentum.get('crash_risk') == 'high':
                score += 10
            
            # Determine alert level
            if score <= 25:
                level = 'green'
                label = 'Markets calm, risk appetite strong'
            elif score <= 45:
                level = 'yellow'
                label = 'Some caution warranted'
            elif score <= 65:
                level = 'orange'
                label = 'Elevated risk, consider reducing exposure'
            elif score <= 85:
                level = 'red'
                label = 'High risk, defensive positioning recommended'
            else:
                level = 'black'
                label = 'Extreme risk, capital preservation mode'
            
            return {
                'score': int(score),
                'level': level,
                'label': label,
                'components': {
                    'volatility': {'value': vol_regime.get('regime', 'unknown'), 'contribution': vol_regime_map.get(vol_regime.get('regime', 'normal'), 0), 'status': 'monitored'},
                    'bubble_risk': {'value': bubble.get('bubble_score', 0), 'contribution': 10 if bubble.get('bubble_score', 0) > 0.7 else 0},
                    'momentum_risk': {'value': momentum.get('crash_risk', 'low'), 'contribution': 10 if momentum.get('crash_risk') == 'high' else 0},
                },
                'top_concerns': ['High VIX', 'Momentum concentration'] if score > 50 else [],
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Composite alert failed: {e}")
            return {
                'score': 50,
                'level': 'yellow',
                'label': 'Unable to assess market conditions',
                'error': str(e),
            }
    
    def generate_alerts(self, assets: list[str] | None = None) -> list[dict]:
        """Generate all current alerts."""
        alerts = []
        
        try:
            # Volatility alerts
            if assets:
                for asset in assets[:3]:  # Limit to top 3
                    vol_regime = self.detect_volatility_regime(asset)
                    if vol_regime.get('regime') in ['high', 'extreme']:
                        alerts.append({
                            'id': f'vol_{asset}',
                            'timestamp': datetime.now().isoformat(),
                            'type': 'vol_regime',
                            'severity': 'critical' if vol_regime.get('regime') == 'extreme' else 'warning',
                            'title': f'{asset} volatility {vol_regime.get("regime")}',
                            'description': f'Current annualized volatility: {vol_regime.get("current_vol_annualized", 0):.1%}',
                            'affected_assets': [asset],
                        })
            
            # Composite market alert
            composite = self.composite_alert_level()
            if composite.get('level') in ['red', 'black']:
                alerts.append({
                    'id': 'market_composite',
                    'timestamp': datetime.now().isoformat(),
                    'type': 'macro',
                    'severity': 'critical' if composite.get('level') == 'black' else 'warning',
                    'title': f'Market alert: {composite.get("label")}',
                    'description': f'Composite score: {composite.get("score")}',
                    'affected_assets': ['SPY', 'QQQ'],
                })
        except Exception as e:
            logger.warning(f"Alert generation failed: {e}")
        
        return alerts
