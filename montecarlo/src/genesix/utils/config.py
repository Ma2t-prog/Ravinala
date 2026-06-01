"""
Configuration management for GenesiX.

Handles API keys, environment variables, and configuration settings.
Uses python-dotenv for .env file fallback.
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """
    Centralized configuration management.
    
    Reads from environment variables first, then falls back to .env file.
    Graceful degradation: missing API keys issue warnings but don't crash.
    """

    # Project paths
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    DATA_CACHE_DIR = PROJECT_ROOT / "data" / "cache"
    
    # Ensure cache directory exists
    DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ============== API Keys ==============
    # FRED (Federal Reserve Economic Data)
    FRED_API_KEY: Optional[str] = os.getenv("FRED_API_KEY")
    
    # Alpha Vantage (forex, stocks intraday)
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")
    
    # News API
    NEWS_API_KEY: Optional[str] = os.getenv("NEWS_API_KEY")
    
    # Reddit API (PRAW)
    REDDIT_CLIENT_ID: Optional[str] = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: Optional[str] = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT: Optional[str] = os.getenv("REDDIT_USER_AGENT")
    
    # ============== Data Source Settings ==============
    # yfinance: primary source (no key needed)
    YFINANCE_TIMEOUT: int = int(os.getenv("YFINANCE_TIMEOUT", "30"))
    YFINANCE_RETRIES: int = int(os.getenv("YFINANCE_RETRIES", "3"))
    
    # CoinGecko: cryptocurrencies (free tier, no key)
    COINGECKO_TIMEOUT: int = int(os.getenv("COINGECKO_TIMEOUT", "30"))
    COINGECKO_RETRIES: int = int(os.getenv("COINGECKO_RETRIES", "3"))
    
    # World Bank API (wbgapi)
    WORLD_BANK_TIMEOUT: int = int(os.getenv("WORLD_BANK_TIMEOUT", "30"))
    
    # Open-Meteo (weather, free tier)
    OPEN_METEO_TIMEOUT: int = int(os.getenv("OPEN_METEO_TIMEOUT", "30"))
    
    # ============== Feature Store ==============
    FEATURE_STORE_FORMAT: str = os.getenv("FEATURE_STORE_FORMAT", "parquet")  # parquet or sqlite
    FEATURE_LOOKBACK_DAYS: int = int(os.getenv("FEATURE_LOOKBACK_DAYS", "730"))  # 2 years default
    FEATURE_CACHE_TTL_HOURS: int = int(os.getenv("FEATURE_CACHE_TTL_HOURS", "24"))
    
    # ============== ML Settings ==============
    ML_VALIDATION_WINDOW_DAYS: int = int(os.getenv("ML_VALIDATION_WINDOW_DAYS", "60"))
    ML_TRAINING_WINDOW_DAYS: int = int(os.getenv("ML_TRAINING_WINDOW_DAYS", "252"))
    ML_TEST_SIZE: float = float(os.getenv("ML_TEST_SIZE", "0.2"))
    ML_RANDOM_SEED: int = int(os.getenv("ML_RANDOM_SEED", "42"))
    
    # ============== Risk Settings ==============
    VAR_CONFIDENCE_LEVEL: float = float(os.getenv("VAR_CONFIDENCE_LEVEL", "0.95"))
    STRESS_TEST_SCENARIOS: str = os.getenv("STRESS_TEST_SCENARIOS", "all")
    
    # ============== Logging ==============
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # ============== Performance ==============
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_WORKERS_PARALLEL: int = int(os.getenv("MAX_WORKERS_PARALLEL", "4"))
    
    @classmethod
    def validate_critical_dependencies(cls) -> dict[str, bool]:
        """
        Check which optional APIs are available.
        
        Returns:
            Dictionary mapping API name to availability (True/False).
        """
        status = {
            "fred": cls.FRED_API_KEY is not None,
            "alpha_vantage": cls.ALPHA_VANTAGE_API_KEY is not None,
            "news": cls.NEWS_API_KEY is not None,
            "reddit": (
                cls.REDDIT_CLIENT_ID is not None
                and cls.REDDIT_CLIENT_SECRET is not None
            ),
            "yfinance": True,  # Always available
            "coingecko": True,  # Always available
            "world_bank": True,  # Always available
            "open_meteo": True,  # Always available
        }
        
        # Log warnings for missing keys
        optional_apis = {
            "fred": "FRED (macro data - can fall back to yfinance treasuries)",
            "alpha_vantage": "Alpha Vantage (forex intraday - can fall back to daily)",
            "news": "News API (headlines - sentiment module will skip)",
            "reddit": "Reddit API (sentiment - will fall back to VADER on headlines)",
        }
        
        for api_name, description in optional_apis.items():
            if not status[api_name]:
                logger.warning(
                    f"Optional API not configured: {api_name}. {description} v"
                )
        
        return status
    
    @classmethod
    def load_from_env_file(cls, env_file_path: Optional[Path] = None) -> None:
        """
        Load environment variables from .env file.
        
        Args:
            env_file_path: Path to .env file. Defaults to project root.
        """
        if env_file_path is None:
            env_file_path = cls.PROJECT_ROOT / ".env"
        
        if env_file_path.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file_path)
                logger.info(f"Loaded .env file from {env_file_path}")
            except ImportError:
                logger.warning("python-dotenv not installed. Skipping .env file loading.")
        else:
            logger.debug(f".env file not found at {env_file_path}")


# Initialize on import
Config.load_from_env_file()
Config.validate_critical_dependencies()
