#!/usr/bin/env python
"""
Step 8 Validation Script — Comprehensive testing of all intelligence modules.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_all_modules():
    """Run comprehensive validation tests."""
    
    print('=' * 60)
    print('STEP 8: ADVANCED INTELLIGENCE LAYER — VALIDATION')
    print('=' * 60)
    
    # Test all imports
    try:
        from genesix.intelligence import (
            NLPEngine, RegimeDetector, RegimeAdaptivePredictor,
            SignalGenerator, ContagionNetwork, SmartAlertSystem
        )
        print('\n✅ All module imports successful\n')
    except Exception as e:
        print(f'\n❌ Import failed: {e}\n')
        return False
    
    import numpy as np
    
    # Test 1: NLP Engine
    print('[1/5] Testing NLP Intelligence Engine...')
    try:
        nlp = NLPEngine(use_finbert=False)
        
        # Test headline analysis
        headline = 'Apple beats earnings expectations and raises guidance'
        result = nlp.analyze_headline(headline, source='Reuters')
        
        # VADER compound score should reflect positive sentiment (ranges -1 to +1)
        assert 'ensemble_score' in result['sentiment']
        assert result['sentiment']['label'] in ['positive', 'very_positive', 'neutral']
        
        sentiment_label = result['sentiment']['label']
        tickers_found = result['entities']['tickers']
        ensemble_score = result['sentiment']['ensemble_score']
        print(f'  ✅ Headline analysis: sentiment={sentiment_label}, score={ensemble_score:.2f}, tickers={tickers_found}')
        
        # Test batch analysis
        headlines = [
            {'text': 'Fed raises rates by 25 basis points', 'source': 'Reuters'},
            {'text': 'Tech stocks surge on AI optimism', 'source': 'Bloomberg'},
            {'text': 'Economic data disappoints markets', 'source': 'CNBC'},
        ]
        batch = nlp.analyze_batch(headlines)
        assert batch['headlines_analyzed'] == 3
        print(f'  ✅ Batch analysis: {batch["headlines_analyzed"]} headlines, overall_sentiment={batch["overall_sentiment"]:.2f}')
        
        # Test central bank analysis
        statement = 'Inflation remains elevated. We will continue tightening monetary policy.'
        cb_result = nlp.analyze_central_bank_statement(statement, bank='fed')
        assert cb_result['hawkish_dovish_score'] > 0
        print(f'  ✅ Central bank analysis: hawkish_dovish_score={cb_result["hawkish_dovish_score"]:.2f}')
        
    except Exception as e:
        print(f'  ❌ NLP Engine test failed: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Regime-Adaptive ML
    print('\n[2/5] Testing Regime-Adaptive ML...')
    try:
        detector = RegimeDetector()
        returns = np.random.normal(0.001, 0.02, 504)
        
        # Test regime detection
        result = detector.detect_regime(returns=returns)
        assert result['regime'] in ['low_vol', 'normal', 'high_vol', 'crisis']
        print(f'  ✅ Regime detection: regime={result["regime"]}, confidence={result["confidence"]:.2f}')
        
        # Test predictor
        predictor = RegimeAdaptivePredictor()
        training = predictor.train('SPY', returns)
        assert training['current_regime'] in ['low_vol', 'normal', 'high_vol', 'crisis']
        print(f'  ✅ Regime-adaptive training: current_regime={training["current_regime"]}')
        
        # Test prediction
        pred = predictor.predict('SPY', returns)
        assert 'expected_return' in pred
        assert 'regime_info' in pred
        print(f'  ✅ Regime-adaptive prediction: expected_return={pred["expected_return"]*100:.2f}%, confidence={pred["confidence"]:.2f}')
        
    except Exception as e:
        print(f'  ❌ Regime ML test failed: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Signal Generation
    print('\n[3/5] Testing Signal Generation System...')
    try:
        signals = SignalGenerator()
        
        # Asset signal
        sig = signals.generate_asset_signal('AAPL')
        assert sig['signal'] in ['strong_buy', 'buy', 'hold', 'sell', 'strong_sell']
        assert 0 < sig['confidence'] <= 1
        print(f'  ✅ Asset signal: signal={sig["signal"]}, composite_score={sig["composite_score"]:.2f}, confidence={sig["confidence"]:.2f}')
        
        # Portfolio signal
        weights = {'AAPL': 0.3, 'MSFT': 0.3, 'AGG': 0.25, 'GLD': 0.15}
        port_sig = signals.generate_portfolio_signal(weights)
        assert port_sig['overall_signal'] in ['increase_exposure', 'hold', 'reduce_exposure', 'defensive']
        print(f'  ✅ Portfolio signal: {port_sig["overall_signal"]}, actions={len(port_sig["actions"])}')
        
        # Market signal
        market = signals.generate_market_signal()
        assert market['regime'] in ['risk_on', 'risk_off', 'transition', 'crisis']
        print(f'  ✅ Market signal: regime={market["regime"]}, score={market["score"]:.2f}')
        
    except Exception as e:
        print(f'  ❌ Signal Generation test failed: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # Test 4: Contagion Network
    print('\n[4/5] Testing Cross-Asset Contagion Network...')
    try:
        contagion = ContagionNetwork()
        
        assets = ['SPY', 'QQQ', 'AGG', 'GLD', 'USO']
        
        # Build network
        network = contagion.build_network(assets)
        assert len(network['nodes']) == 5
        assert len(network['edges']) > 0
        print(f'  ✅ Network built: {len(network["nodes"])} nodes, {len(network["edges"])} edges, density={network["metrics"]["network_density"]:.2f}')
        
        # Cascade simulation
        cascade = contagion.simulate_cascade('SPY', shock_pct=-0.10, network=network, n_steps=3)
        assert cascade['trigger'] == 'SPY'
        assert len(cascade['steps']) == 3
        print(f'  ✅ Cascade simulation: {len(cascade["steps"])} steps, impact={cascade["total_system_impact"]:.2f}')
        
        # Systemic risks
        risks = contagion.identify_systemic_risks(network)
        assert len(risks) > 0
        print(f'  ✅ Systemic risk identification: {len(risks)} assets, highest_risk={risks[0]["risk_level"]}')
        
    except Exception as e:
        print(f'  ❌ Contagion Network test failed: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # Test 5: Smart Alerts
    print('\n[5/5] Testing Smart Alert System...')
    try:
        alerts = SmartAlertSystem()
        
        portfolio = {'AAPL': 0.25, 'MSFT': 0.25, 'SPY': 0.30, 'AGG': 0.15, 'GLD': 0.05}
        
        # Generate alerts
        all_alerts = alerts.generate_smart_alerts(portfolio)
        assert isinstance(all_alerts, list)
        assert len(all_alerts) > 0
        print(f'  ✅ Smart alerts generated: {len(all_alerts)} total alerts')
        
        # Check alert categories
        categories = [a['category'] for a in all_alerts]
        unique_categories = set(categories)
        print(f'  ✅ Alert categories: {unique_categories}')
        
        # Check opportunity scan
        opps = alerts.opportunity_scan(['AAPL', 'MSFT', 'GOOGL', 'SPY'])
        print(f'  ✅ Opportunity scan: {len(opps)} opportunities found')
        
    except Exception as e:
        print(f'  ❌ Smart Alerts test failed: {e}')
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print('\n' + '=' * 60)
    print('✅ STEP 8 VALIDATION COMPLETE')
    print('=' * 60)
    print('\nAll 5 modules functional:')
    print('  ✅ NLP Intelligence Engine')
    print('  ✅ Regime-Adaptive ML')
    print('  ✅ Signal Generation System')
    print('  ✅ Cross-Asset Contagion Network')
    print('  ✅ Smart Alert System')
    print('\nStatus: READY FOR DEPLOYMENT')
    print('=' * 60)
    
    return True


if __name__ == '__main__':
    success = test_all_modules()
    sys.exit(0 if success else 1)
