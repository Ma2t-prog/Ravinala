"""
Predictive alert system — alerts BEFORE things happen, not after.

Traditional alerts: "VIX just spiked 20%" (too late)
Smart alerts: "VIX is building pressure — 65% chance of >15% spike in next 3 days" (actionable)

Alert categories:
1. PREDICTIVE: something is LIKELY to happen based on leading indicators
2. REACTIVE: something just happened that needs attention
3. OPPORTUNITY: a favorable setup has been detected
4. PORTFOLIO: your specific portfolio is affected
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import numpy as np

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# ÉTAPE 1 — DEMO MODE WARNING
# ═══════════════════════════════════════════════════════════════════════
# Alert probabilities, VIX levels, Sharpe ratios, and momentum scores
# are generated with np.random when NLPEngine / SignalGenerator are
# unavailable (which is always the case without optional dependencies).
# Outputs such as "70% chance of VIX spike" are SYNTHETIC illustrations.
# DO NOT use for live risk monitoring or automated trading.
# ═══════════════════════════════════════════════════════════════════════
DEMO_MODE: bool = True  # Set False when real NLP + signal feeds are integrated


class SmartAlertSystem:
    """Predictive alert system combining multiple signal sources."""
    
    def __init__(self):
        """Initialize smart alert system."""
        # In production, would import real services
        try:
            from genesix.intelligence.nlp_engine import NLPEngine
            self.nlp = NLPEngine()
        except ImportError:
            self.nlp = None
        
        try:
            from genesix.intelligence.signals import SignalGenerator
            self.signals = SignalGenerator()
        except ImportError:
            self.signals = None
        
        try:
            from genesix.intelligence.contagion import ContagionNetwork
            self.contagion = ContagionNetwork()
        except ImportError:
            self.contagion = None
        
        try:
            from genesix.intelligence.regime_ml import RegimeDetector
            self.regime = RegimeDetector()
        except ImportError:
            self.regime = None
    
    def generate_smart_alerts(self, portfolio: Optional[Dict[str, float]] = None) -> List[dict]:
        """
        Generate all current smart alerts.
        
        Args:
            portfolio: Optional portfolio weights for portfolio-specific alerts
        
        Returns:
            List of smart alerts with categories and recommended actions
        """
        alerts = []
        
        # PREDICTIVE ALERTS
        alerts.extend(self._generate_predictive_alerts())
        
        # REACTIVE ALERTS
        alerts.extend(self._generate_reactive_alerts())
        
        # OPPORTUNITY ALERTS
        alerts.extend(self._generate_opportunity_alerts())
        
        # PORTFOLIO-SPECIFIC ALERTS
        if portfolio:
            alerts.extend(self._generate_portfolio_alerts(portfolio))
        
        return alerts
    
    def predictive_vol_alert(self) -> Optional[dict]:
        """Check if volatility compression suggests upcoming spike.
        Requires real volatility data source to function."""
        # No real vol data source connected — cannot generate predictive alert
        return None
    
    def predictive_correlation_alert(self, assets: Optional[List[str]] = None) -> Optional[dict]:
        """Check if correlations are building toward crisis levels."""
        if assets is None:
            assets = ['SPY', 'AGG', 'GLD']
        
        # No real correlation data source connected — cannot generate predictive alert
        return None
    
    def predictive_regime_alert(self) -> Optional[dict]:
        """Check if regime transition is imminent."""
        regime_info = self.regime.detect_regime() if self.regime else {
            'regime': 'normal',
            'transition_probability': 0.15,
        }
        
        if regime_info['transition_probability'] > 0.40:
            return {
                'id': 'regime_shift_001',
                'timestamp': datetime.now(),
                'category': 'predictive',
                'severity': 'info',
                'title': 'Regime transition likely',
                'description': f"Current regime ({regime_info['regime']}) has {regime_info['transition_probability']:.0%} chance of changing tomorrow. Model performance will degrade.",
                'data': {
                    'current_regime': regime_info['regime'],
                    'transition_prob': regime_info['transition_probability'],
                },
                'affected_assets': ['all'],
                'probability': regime_info['transition_probability'],
                'time_horizon': '1-3 days',
                'suggested_actions': [
                    'Reduce position sizes ahead of regime change',
                    'Widen stop losses',
                    'Consider selling illiquid positions',
                ],
                'dismiss_condition': 'Regime stabilizes or transition completes',
            }
        return None
    
    def earnings_calendar_alert(self, portfolio: Dict[str, float]) -> List[dict]:
        """Check upcoming earnings dates for portfolio holdings."""
        alerts = []
        
        # Simulated earnings calendar
        earnings_schedule = {
            'AAPL': 2, 'MSFT': 5, 'GOOGL': 3, 'AMZN': 8, 'NVDA': 4,
            'META': 6, 'TSLA': 10, 'BRK.B': 15, 'JPM': 3, 'XOM': 7,
        }
        
        earnings_this_week = []
        for asset, weight in portfolio.items():
            if asset in earnings_schedule:
                days_until = earnings_schedule[asset]
                if days_until <= 7 and weight > 0.02:
                    earnings_this_week.append((asset, days_until, weight))
        
        if earnings_this_week:
            affected = ', '.join([a[0] for a in earnings_this_week])
            total_weight = sum(a[2] for a in earnings_this_week)
            
            alerts.append({
                'id': 'earnings_001',
                'timestamp': datetime.now(),
                'category': 'portfolio',
                'severity': 'warning' if total_weight > 0.10 else 'info',
                'title': f'Earnings season — {len(earnings_this_week)} holdings reporting',
                'description': f'{affected} report this week. Combined portfolio weight: {total_weight:.1%}. Expect increased vol.',
                'data': {
                    'holdings_reporting': len(earnings_this_week),
                    'combined_weight': total_weight,
                    'dates': [f"{a[0]} in {a[1]} days" for a in earnings_this_week],
                },
                'affected_assets': [a[0] for a in earnings_this_week],
                'probability': 0.75,  # High Vol is certain
                'time_horizon': '7 days',
                'suggested_actions': [
                    'Consider reducing exposure before events',
                    'Use straddles or collars for protection',
                    'Be prepared for gap moves',
                ],
                'dismiss_condition': 'All earnings dates pass',
            })
        
        return alerts
    
    def contagion_risk_alert(self, portfolio: Dict[str, float]) -> Optional[dict]:
        """Check if a systemic risk hotspot could cascade into portfolio."""
        if not self.contagion:
            return None
        
        # Build network from portfolio assets
        assets = list(portfolio.keys())
        if len(assets) < 2:
            return None  # Need at least 2 assets for contagion analysis
        
        network = self.contagion.build_network(assets)
        risks = self.contagion.identify_systemic_risks(network)
        
        for risk in risks:
            if risk['risk_level'] == 'high' and any(
                asset in portfolio for asset in risk['monitoring_recommendation'].split()
            ):
                return {
                    'id': 'contagion_risk_001',
                    'timestamp': datetime.now(),
                    'category': 'predictive',
                    'severity': 'critical' if risk['systemic_score'] > 0.8 else 'warning',
                    'title': f'Contagion risk from {risk["asset"]}',
                    'description': f'{risk["asset"]} is in high stress. ' + 
                                 f'Systemic score {risk["systemic_score"]:.0%}. ' +
                                 f'Could affect {risk["n_assets_affected"]} assets including your holdings.',
                    'data': risk,
                    'affected_assets': [risk['asset']],
                    'probability': risk['systemic_score'],
                    'time_horizon': '5-10 days',
                    'suggested_actions': [
                        f'Monitor {risk["asset"]} daily',
                        'Review exposure to {risk["asset"]} and correlated assets',
                        'Consider hedging with protective puts',
                    ],
                    'dismiss_condition': f'{risk["asset"]} stress level improves',
                }
        
        return None
    
    def portfolio_health_alert(self, portfolio: Dict[str, float]) -> List[dict]:
        """Check portfolio-specific risk metrics for alerts.
        Requires real portfolio analytics (VaR, Sharpe) to function."""
        # No real portfolio risk metrics available — cannot generate health alerts
        return []
    
    def opportunity_scan(self, universe: Optional[List[str]] = None) -> List[dict]:
        """Scan for favorable setups across the universe."""
        if universe is None:
            universe = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'SPY', 'QQQ', 'TLT', 'GLD']
        
        # No real market data source connected — cannot compute RSI, momentum, or sentiment
        # Return empty list until a real data provider is integrated
        return []
    
    # ========== PRIVATE GENERATION METHODS ==========
    
    def _generate_predictive_alerts(self) -> List[dict]:
        """Generate all predictive alerts."""
        alerts = []
        
        vol_alert = self.predictive_vol_alert()
        if vol_alert:
            alerts.append(vol_alert)
        
        corr_alert = self.predictive_correlation_alert()
        if corr_alert:
            alerts.append(corr_alert)
        
        regime_alert = self.predictive_regime_alert()
        if regime_alert:
            alerts.append(regime_alert)
        
        return alerts
    
    def _generate_reactive_alerts(self) -> List[dict]:
        """Generate reactive alerts for something that just happened."""
        alerts = []
        
        # Reactive alerts require real-time market event feeds (VIX, yield curve, etc.)
        # No real event source connected — return empty list
        return alerts
    
    def _generate_opportunity_alerts(self) -> List[dict]:
        """Generate opportunity alerts."""
        return self.opportunity_scan()
    
    def _generate_portfolio_alerts(self, portfolio: Dict[str, float]) -> List[dict]:
        """Generate portfolio-specific alerts."""
        alerts = []
        
        earnings_alerts = self.earnings_calendar_alert(portfolio)
        alerts.extend(earnings_alerts)
        
        contagion_alert = self.contagion_risk_alert(portfolio)
        if contagion_alert:
            alerts.append(contagion_alert)
        
        health_alerts = self.portfolio_health_alert(portfolio)
        alerts.extend(health_alerts)
        
        return alerts
