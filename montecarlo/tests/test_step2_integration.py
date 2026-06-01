"""Pytest smoke coverage for Step 2 data-layer modules."""


def test_step2_data_layer_initialization_smoke():
    from src.genesix.data.alt_data_fetcher import AltDataFetcher
    from src.genesix.data.feature_store import FeatureStore
    from src.genesix.data.macro_fetcher import MacroDataFetcher
    from src.genesix.data.market_fetcher import MarketDataFetcher

    market = MarketDataFetcher()
    macro = MacroDataFetcher()
    alt = AltDataFetcher()
    features = FeatureStore()

    assert market is not None
    assert macro is not None
    assert alt is not None
    assert features.cache_dir.exists()
