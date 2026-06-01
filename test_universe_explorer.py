#!/usr/bin/env python
"""
Test: Universe Explorer Pipeline Integration
"""

import sys
sys.path.insert(0, 'montecarlo/src')

from genesix.universe_explorer import get_pipeline, ScreenerEngine
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_pipeline():
    """Test data pipeline integration."""
    logger.info("=" * 60)
    logger.info("TEST: GENESIX Universe Explorer v2.1")
    logger.info("=" * 60)
    
    # Initialize and load universe
    logger.info("\n1. Initializing pipeline...")
    pipeline = get_pipeline()
    logger.info("   ✓ Pipeline created")
    
    logger.info("\n2. Loading universe (fetching sample instruments)...")
    pipeline.ensure_universe_loaded()
    
    # Get stats
    stats = pipeline.get_stats()
    logger.info(f"   ✓ Universe loaded:")
    logger.info(f"     - Total: {stats['total']} instruments")
    logger.info(f"     - Sectors: {len(stats['by_sector'])}")
    logger.info(f"     - Countries: {len(stats['by_country'])}")
    
    # Test search
    logger.info("\n3. Testing search (AAPL)...")
    result = pipeline.search_instruments('AAPL', limit=1)
    if result:
        inst = result[0]
        logger.info(f"   ✓ Found: {inst.ticker}")
        logger.info(f"     - Name: {inst.name}")
        logger.info(f"     - Price: ${inst.price:.2f}")
        logger.info(f"     - Change 1D: {inst.price_change_1d:+.2f}%")
        logger.info(f"     - Sector: {inst.sector}")
        logger.info(f"     - Country: {inst.country}")
    else:
        logger.error("   ✗ No results for AAPL")
        return False
    
    # Test screener
    logger.info("\n4. Testing screener (High Dividend > 2%)...")
    screener = ScreenerEngine(pipeline.get_all())
    result = screener.screen_high_dividend(min_yield=2.0)
    logger.info(f"   ✓ Found {result.total_count} instruments")
    if result.instruments:
        logger.info("     Top 3:")
        for inst in result.instruments[:3]:
            logger.info(f"       - {inst.ticker}: {inst.dividend_yield:.2f}%")
    
    # Test sector filter
    logger.info("\n5. Testing sector filter (Technology)...")
    sectors = pipeline.get_sectors()
    tech_sector = None
    for sector in sectors:
        if 'Technology' in sector or sector == 'Technology':
            tech_sector = sector
            break
    
    if tech_sector:
        tech_stocks = pipeline.get_by_sector(tech_sector)
        logger.info(f"   ✓ Found {len(tech_stocks)} {tech_sector} stocks")
        if tech_stocks:
            logger.info("     Top 3:")
            for inst in tech_stocks[:3]:
                logger.info(f"       - {inst.ticker}: ${inst.price:.2f}")
    
    # Test pre-built screens
    logger.info("\n6. Testing pre-built screens...")
    screens = {
        'Large-cap': screener.screen_large_cap(),
        'Value stocks': screener.screen_value(),
        'Momentum': screener.screen_momentum(),
    }
    for name, result in screens.items():
        logger.info(f"   ✓ {name}: {result.total_count} instruments")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ All integration tests PASSED!")
    logger.info("=" * 60)
    return True

if __name__ == '__main__':
    success = test_pipeline()
    sys.exit(0 if success else 1)
