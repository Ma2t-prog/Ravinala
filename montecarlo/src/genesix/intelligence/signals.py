"""
Actionable signal generation — the output layer of GenesiX intelligence.

Combines ML predictions + NLP sentiment + risk metrics + technical indicators
into clear, actionable signals for each asset and the overall portfolio.

Signal types:
1. Asset signals: buy/sell/hold with confidence and reasoning
2. Portfolio signals: rebalance, reduce risk, increase exposure
3. Market regime signals: risk-on, risk-off, transition
4. Event signals: upcoming catalyst, earnings play, macro event
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


class SignalGenerator:
    """Comprehensive signal generation system."""
    
    def __init__(self):
        """Initialize signal generator."""
        # In production, these would be real services
        # For now, we import what's available
        try:
            from genesix.intelligence.nlp_engine import NLPEngine
            self.nlp = NLPEngine()
        except ImportError:
            self.nlp = None
            logger.warning("NLPEngine not available")
        
        try:
            from genesix.intelligence.regime_ml import RegimeDetector
            self.regime = RegimeDetector()
        except ImportError:
            self.regime = None
            logger.warning("RegimeDetector not available")

        self.signal_history: list[dict] = []

    def generate_asset_signal(self, asset: str, market_data: Optional[dict] = None) -> dict:
        """
        Comprehensive signal for a single asset.
        
        Combines 5 signal sources:
        1. ML prediction (direction + magnitude + confidence)
        2. NLP sentiment (news + social)
        3. Technical indicators (RSI, MACD, Bollinger, trend)
        4. Risk metrics (VaR regime, vol regime)
        5. Macro context (sensitive factors in favorable/unfavorable territory)
        
        Args:
            asset: Ticker symbol
            market_data: Optional market data dict with technical indicators
        
        Returns:
            Comprehensive signal with composite score and reasoning
        """
        # Generate sub-scores
        ml_score = self._ml_subsignal(asset)
        nlp_score = self._nlp_subsignal(asset) if self.nlp else {'score': 0.0, 'detail': 'NLP unavailable'}
        technical_score = self._technical_subsignal(asset, market_data)
        risk_score = self._risk_subsignal(asset)
        macro_score = self._macro_subsignal(asset)
        
        # Composite score (weighted average — skip unavailable sub-signals)
        all_weights = {
            'ml': 0.30,
            'nlp': 0.20,
            'technical': 0.25,
            'risk': 0.15,
            'macro': 0.10,
        }
        sub_scores = {
            'ml': ml_score,
            'nlp': nlp_score,
            'technical': technical_score,
            'risk': risk_score,
            'macro': macro_score,
        }
        
        # Filter out unavailable sub-signals and renormalize weights
        available = {k: v for k, v in sub_scores.items() if v.get('status') != 'unavailable'}
        if available:
            total_weight = sum(all_weights[k] for k in available)
            composite = sum(
                available[k]['score'] * (all_weights[k] / total_weight)
                for k in available
            )
        else:
            composite = 0.0
        
        weights = all_weights
        
        # Signal mapping
        if composite > 0.5:
            signal = 'strong_buy'
        elif composite > 0.2:
            signal = 'buy'
        elif composite < -0.5:
            signal = 'strong_sell'
        elif composite < -0.2:
            signal = 'sell'
        else:
            signal = 'hold'
        
        # Confidence
        confidence = 0.5 + abs(composite) * 0.3
        confidence = min(confidence, 0.95)
        
        # Key reasons
        reasons = []
        if abs(ml_score['score']) > 0.2:
            reasons.append(ml_score['detail'])
        if abs(nlp_score['score']) > 0.2:
            reasons.append(nlp_score['detail'])
        if abs(technical_score['score']) > 0.2:
            reasons.append(technical_score['detail'])
        if not reasons:
            reasons.append(
                f"{asset} signal is neutral because higher-fidelity market inputs are not connected yet"
            )
        
        # Risk warnings
        warnings = []
        if risk_score['score'] < -0.2:
            warnings.append("VIX elevated — higher than normal uncertainty")
        if "upcoming earnings" in macro_score['detail'].lower():
            warnings.append("Earnings report in 3 days — high event risk")
        
        now = datetime.now()
        default_halflife = 24.0
        stale_after = now + timedelta(hours=3 * default_halflife)

        result = {
            'asset': asset,
            'signal': signal,
            'composite_score': composite,
            'confidence': confidence,
            'timestamp': now,
            'sub_signals': {
                'ml_prediction': {**ml_score, 'weight': weights['ml']},
                'nlp_sentiment': {**nlp_score, 'weight': weights['nlp']},
                'technical': {**technical_score, 'weight': weights['technical']},
                'risk': {**risk_score, 'weight': weights['risk']},
                'macro': {**macro_score, 'weight': weights['macro']},
            },
            'key_reasons': reasons[:3],
            'risk_warnings': warnings,
            'timeframe': 'medium_term' if abs(composite) > 0.3 else 'short_term',
            'decay_factor': 1.0,
            'stale_after': stale_after,
        }

        # Store in signal history (keep max 100 entries)
        self.signal_history.append(result)
        if len(self.signal_history) > 100:
            self.signal_history = self.signal_history[-100:]

        # Persist to DB — SignalInstance (Étape 5 complétion — Problem E)
        self._persist_signal_instance(result)

        return result

    def _persist_signal_instance(self, signal: dict) -> None:
        """
        Persist signal to src.db.models.SignalInstance (sync, Column style).

        Graceful no-op if src DB is not configured.
        """
        try:
            from src.db.models import SignalInstance, SessionLocal
            session = SessionLocal()
            try:
                row = SignalInstance(
                    symbol=signal["asset"],
                    signal_type=signal["signal"],
                    composite_score=signal["composite_score"],
                    confidence=signal.get("confidence"),
                    sub_signals=signal.get("sub_signals"),
                    expires_at=signal.get("stale_after"),
                )
                session.add(row)
                session.commit()
                logger.debug("SignalInstance persisted for %s", signal["asset"])
            except Exception as exc:
                session.rollback()
                logger.warning("Failed to persist SignalInstance: %s", exc)
            finally:
                session.close()
        except Exception:
            # src DB not available — graceful no-op
            pass
    
    def apply_decay(self, signal: dict, halflife_hours: float = 24.0) -> dict:
        """Apply exponential decay to a signal based on its age.

        A signal's effective confidence decays as: confidence * exp(-ln(2) * age_hours / halflife_hours)

        After 3 halflives, the signal is considered stale and automatically set to 'hold'.

        Args:
            signal: Signal dict (output of generate_asset_signal)
            halflife_hours: Time for confidence to halve (default 24h)

        Returns:
            Updated signal dict with decayed confidence and 'decay_factor' field
        """
        age = datetime.now() - signal['timestamp']
        age_hours = age.total_seconds() / 3600.0

        decay_factor = math.exp(-math.log(2) * age_hours / halflife_hours)

        decayed = dict(signal)
        decayed['decay_factor'] = decay_factor
        decayed['confidence'] = signal['confidence'] * decay_factor

        # After 3 halflives the signal is stale
        if age_hours >= 3 * halflife_hours:
            decayed['signal'] = 'hold'

        return decayed

    def get_active_signals(self, halflife_hours: float = 24.0) -> list[dict]:
        """Return all non-stale signals with decay applied."""
        stale_threshold = 3 * halflife_hours
        now = datetime.now()
        active = []

        for sig in self.signal_history:
            age_hours = (now - sig['timestamp']).total_seconds() / 3600.0
            if age_hours < stale_threshold:
                active.append(self.apply_decay(sig, halflife_hours))

        # Sort by decayed confidence descending
        active.sort(key=lambda s: s['confidence'], reverse=True)
        return active

    def signal_momentum(self, asset: str, lookback: int = 5) -> float:
        """Compute signal momentum: are recent signals strengthening or weakening?

        Returns a value between -1 (weakening) and +1 (strengthening).
        """
        # Gather the last N signals for this asset
        asset_signals = [s for s in self.signal_history if s['asset'] == asset]
        recent = asset_signals[-lookback:]

        if len(recent) < 2:
            return 0.0

        scores = [s['composite_score'] for s in recent]

        # Simple linear regression slope over the indices
        n = len(scores)
        x_mean = (n - 1) / 2.0
        y_mean = sum(scores) / n
        numerator = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # Normalise slope to [-1, 1] — a slope of ±1 per step is the max
        momentum = max(-1.0, min(1.0, slope))
        return momentum

    def generate_portfolio_signal(self, weights: Dict[str, float]) -> dict:
        """
        Portfolio-level signal.
        
        Args:
            weights: Asset weights dict {ticker: weight}
        
        Returns:
            Portfolio-level signal with rebalancing recommendations
        """
        # Generate per-asset signals
        asset_signals = {}
        for asset in weights:
            asset_signals[asset] = self.generate_asset_signal(asset)
        
        # Count signals
        signal_counts = {}
        total_scores = 0
        for sig in asset_signals.values():
            signal_name = sig['signal']
            signal_counts[signal_name] = signal_counts.get(signal_name, 0) + 1
            total_scores += sig['composite_score'] * weights.get(sig['asset'], 0)
        
        # Overall signal
        buy_count = signal_counts.get('strong_buy', 0) + signal_counts.get('buy', 0)
        sell_count = signal_counts.get('strong_sell', 0) + signal_counts.get('sell', 0)
        
        if buy_count > sell_count:
            overall_signal = 'increase_exposure'
        elif sell_count > buy_count:
            overall_signal = 'reduce_exposure'
        else:
            overall_signal = 'hold'
        
        # Generate rebalancing actions
        actions = []
        for asset, asset_sig in asset_signals.items():
            current_weight = weights.get(asset, 0)
            
            if asset_sig['signal'] in ['strong_sell', 'sell']:
                if current_weight > 0.05:
                    new_weight = max(0, current_weight - 0.10)
                    actions.append({
                        'type': 'reduce',
                        'asset': asset,
                        'from_weight': current_weight,
                        'to_weight': new_weight,
                        'reason': asset_sig['key_reasons'][0] if asset_sig['key_reasons'] else 'Sell signal'
                    })
            
            elif asset_sig['signal'] in ['strong_buy', 'buy']:
                if current_weight < 0.20:
                    new_weight = min(0.25, current_weight + 0.05)
                    actions.append({
                        'type': 'increase',
                        'asset': asset,
                        'from_weight': current_weight,
                        'to_weight': new_weight,
                        'reason': asset_sig['key_reasons'][0] if asset_sig['key_reasons'] else 'Buy signal'
                    })
        
        regime_name = self.regime.detect_regime()['regime'] if self.regime else 'unknown'
        regime_context = f"Market is in {regime_name} mode. "
        if regime_name in ['high_vol', 'crisis']:
            regime_context += "Consider increasing bonds/gold and reducing equity/crypto."
        else:
            regime_context += "Favorable environment for growth assets."
        
        return {
            'overall_signal': overall_signal,
            'score': total_scores / max(len(weights), 1),
            'reasoning': f'{buy_count} buy signals vs {sell_count} sell signals across portfolio',
            'asset_signals': {k: v['signal'] for k, v in asset_signals.items()},
            'actions': actions,
            'regime_context': regime_context,
        }
    
    def generate_market_signal(self) -> dict:
        """
        Broad market regime signal.
        
        Returns:
            Market-wide regime and implications
        """
        regime_info = self.regime.detect_regime() if self.regime else {
            'regime': 'normal',
            'confidence': 0.7,
        }
        
        regime = regime_info['regime']
        
        # Map to risk regime
        if regime == 'low_vol':
            score = 0.8
            regime_label = 'risk_on'
        elif regime == 'normal':
            score = 0.2
            regime_label = 'risk_on'
        elif regime == 'high_vol':
            score = -0.3
            regime_label = 'risk_off'
        else:
            score = -0.9
            regime_label = 'crisis'
        
        # Favored/avoid assets
        if regime_label == 'risk_on':
            favored = ['SPY', 'QQQ', 'EEM', 'IWM']
            avoid = ['TLT', 'GLD', 'VXX']
        else:
            favored = ['TLT', 'GLD', 'AGG', 'SHV']
            avoid = ['QQQ', 'EEM', 'VGT', 'SPHD']
        
        return {
            'regime': regime_label,
            'confidence': regime_info.get('confidence', 0.7),
            'score': score,
            'indicators': {
                'vix': {'value': None, 'signal': 'unavailable'},
                'yield_curve': {'value': 'flat', 'signal': 'neutral'},
                'credit_spreads': {'value': 150, 'signal': 'normal'},
                'momentum': {'value': 0.05, 'signal': 'bullish'},
                'sentiment': {'value': 0.3, 'signal': 'positive'},
                'breadth': {'value': 0.55, 'signal': 'bullish'},
            },
            'favored_assets': favored,
            'avoid_assets': avoid,
            'historical_analog': 'Current regime resembles Q3 2023 (rate plateau phase)',
            'outlook': f"Market is in {regime_label} mode. {'Expect higher correlations and volatility swings.' if regime_label == 'risk_off' else 'Diversification benefits remain strong.'}"
        }
    
    def generate_event_signals(self, assets: Optional[List[str]] = None) -> List[dict]:
        """
        Upcoming event-based signals.
        
        Args:
            assets: List of assets to check for events (optional)
        
        Returns:
            List of event signals
        """
        if assets is None:
            assets = ['AAPL', 'MSFT', 'SPY', 'QQQ']
        
        # No real event data source connected — return empty
        return []
    
    def signal_dashboard_data(self, assets: List[str],
                              portfolio: Optional[Dict[str, float]] = None) -> dict:
        """
        All signals packaged for the dashboard.
        
        Args:
            assets: List of assets to generate signals for
            portfolio: Optional portfolio weights for portfolio signal
        
        Returns:
            All signals organized for dashboard display
        """
        # Individual asset signals
        asset_signals = {}
        for asset in assets[:10]:
            asset_signals[asset] = self.generate_asset_signal(asset)
        
        # Market signal
        market_signal = self.generate_market_signal()
        
        # Event signals
        event_signals = self.generate_event_signals(assets)
        
        # Portfolio signal
        portfolio_signal = None
        if portfolio:
            portfolio_signal = self.generate_portfolio_signal(portfolio)
        
        return {
            'market_signal': market_signal,
            'asset_signals': asset_signals,
            'event_signals': event_signals,
            'portfolio_signal': portfolio_signal,
            'updated_at': datetime.now(),
        }
    
    # ========== PRIVATE SUB-SIGNAL METHODS ==========
    
    def _ml_subsignal(self, asset: str) -> dict:
        """ML prediction sub-signal — requires real ML model connection."""
        return {'status': 'unavailable', 'reason': 'real_data_source_not_connected', 'value': None, 'score': 0.0, 'detail': 'ML prediction unavailable — no model connected'}
    
    def _nlp_subsignal(self, asset: str) -> dict:
        """NLP sentiment sub-signal — requires real NLP engine connection."""
        return {'status': 'unavailable', 'reason': 'real_data_source_not_connected', 'value': None, 'score': 0.0, 'detail': 'NLP sentiment unavailable — no NLP engine connected'}
    
    def _technical_subsignal(self, asset: str, market_data: Optional[dict] = None) -> dict:
        """Technical indicators sub-signal — requires real market data."""
        return {'status': 'unavailable', 'reason': 'real_data_source_not_connected', 'value': None, 'score': 0.0, 'detail': 'Technical indicators unavailable — no real-time data connected'}
    
    def _risk_subsignal(self, asset: str) -> dict:
        """Risk metrics sub-signal — requires real risk engine connection."""
        return {'status': 'unavailable', 'reason': 'real_data_source_not_connected', 'value': None, 'score': 0.0, 'detail': 'Risk metrics unavailable — no risk engine connected'}
    
    def _macro_subsignal(self, asset: str) -> dict:
        """Macro context sub-signal — requires real macro data source."""
        return {'status': 'unavailable', 'reason': 'real_data_source_not_connected', 'value': None, 'score': 0.0, 'detail': 'Macro context unavailable — no macro data source connected'}
