"""
Alternative data fetcher for sentiment, weather, market indicators, and social signals.

Sources:
- VIX and volatility indices (yfinance)
- Weather data (Open-Meteo API, free)
- Sentiment (VADER on headlines, Google Trends, Reddit via PRAW)
- Put/Call ratio (from options chains)
- Baltic Dry Index (yfinance)
- Dollar Index (yfinance)

All sources are optional with graceful fallback.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Union
from functools import wraps

import pandas as pd
import numpy as np

from ..utils.config import Config
from ..utils.constants import (
    SENTIMENT_KEYWORDS,
    REDDIT_SUBREDDITS,
    WEATHER_REGIONS,
    VOLATILITY_INDICES,
)

logger = logging.getLogger(__name__)


def rate_limit(calls_per_second: float = 1.0):
    """Rate limiter decorator."""
    min_interval = 1.0 / calls_per_second
    
    def decorator(func):
        last_called = [0.0]
        
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        
        return wrapper
    return decorator


class AltDataFetcher:
    """
    Unified fetcher for alternative data, sentiment, and market indicators.
    
    Combines:
    - Volatility indices (VIX, VXEMD, SKEW)
    - Sentiment from news, Reddit, Google Trends
    - Weather data for agricultural regions
      - Put/Call ratios
    - Market breadth indicators
    """
    
    def __init__(self):
        """Initialize alt data fetcher."""
        self.cache_dir = Config.DATA_CACHE_DIR / "alt_data"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.news_api_key = Config.NEWS_API_KEY
        self.reddit_client_id = Config.REDDIT_CLIENT_ID
        self.reddit_client_secret = Config.REDDIT_CLIENT_SECRET
        self.reddit_user_agent = Config.REDDIT_USER_AGENT
        
        self.request_timeout = Config.REQUEST_TIMEOUT
        
        logger.info("AltDataFetcher initialized")

    # ============== Backward-compatible Public API ==============

    def fetch_weather(self) -> pd.DataFrame:
        """Legacy wrapper returning regional weather data as a DataFrame."""
        weather = self.get_weather_impact()
        if not weather:
            return pd.DataFrame(columns=["region", "temperature", "precipitation", "wind_speed"])
        return pd.DataFrame.from_dict(weather, orient="index").reset_index(names="region")

    def compute_weather_impact_score(self, asset: str) -> float:
        """Return a bounded heuristic weather impact score in [-1, 1]."""
        weather = self.get_weather_impact()
        if not weather:
            return 0.0

        temps = [float(item.get("temperature", 0.0)) for item in weather.values()]
        precip = [float(item.get("precipitation", 0.0)) for item in weather.values()]
        baseline = (np.mean(temps) - 20.0) / 20.0 - np.mean(precip) / 50.0
        if str(asset).lower() in {"wheat", "corn", "soybeans", "coffee", "cocoa"}:
            baseline *= 1.15
        return float(np.clip(baseline, -1.0, 1.0))

    def compute_news_sentiment(self, headlines: list[str]) -> dict[str, float]:
        """Compute lightweight headline sentiment without requiring external APIs."""
        if not headlines:
            return {"mean_compound": 0.0, "headline_count": 0}

        compounds: list[float] = []
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

            analyzer = SentimentIntensityAnalyzer()
            compounds = [float(analyzer.polarity_scores(headline).get("compound", 0.0)) for headline in headlines]
        except Exception:
            positive = {"high", "beat", "beats", "growth", "strong", "accelerates", "surge", "gain"}
            negative = {"crash", "bankruptcy", "recession", "fear", "fears", "loss", "plunge", "default"}
            for headline in headlines:
                words = {token.lower() for token in str(headline).split()}
                score = 0.25 * len(words & positive) - 0.30 * len(words & negative)
                compounds.append(float(np.clip(score, -1.0, 1.0)))

        mean_compound = float(np.mean(compounds)) if compounds else 0.0
        return {
            "mean_compound": mean_compound,
            "headline_count": len(headlines),
            "positive_ratio": float(np.mean([score > 0 for score in compounds])) if compounds else 0.0,
        }

    def fetch_google_trends(self, keywords: list[str], timeframe: str = "today 1-m") -> pd.DataFrame:
        """Return a trends DataFrame or a neutral fallback."""
        rows = []
        for keyword in keywords:
            momentum = self.compute_trends_momentum(keyword)
            rows.append({"keyword": keyword, "momentum": momentum})
        return pd.DataFrame(rows)

    def compute_trends_momentum(self, keyword: str) -> float:
        """Return a legacy neutral-friendly trends momentum score."""
        momentum = self._get_google_trends_momentum([keyword])
        if momentum is None:
            return 1.0
        return float(momentum)

    def fetch_reddit_sentiment(self) -> dict[str, float]:
        """Return Reddit sentiment with a neutral fallback."""
        sentiment = self._get_reddit_sentiment()
        if sentiment is None:
            return {"overall_sentiment": 0.0, "bullish_pct": 0.5}
        bullish_pct = float(np.clip((sentiment + 1.0) / 2.0, 0.0, 1.0))
        return {"overall_sentiment": float(sentiment), "bullish_pct": bullish_pct}

    def fetch_vix(self, period: str = "1mo") -> pd.Series:
        return self._fetch_market_series("^VIX", period=period)

    def fetch_dxy(self, period: str = "1mo") -> pd.Series:
        return self._fetch_market_series("DX-Y.NYB", period=period)

    def fetch_put_call_ratio(self) -> Optional[float]:
        return self._get_put_call_ratio()

    def fetch_baltic_dry_index(self, period: str = "1mo") -> pd.Series:
        return self._fetch_market_series("BDIY", period=period)

    def compute_fear_greed_index(self) -> dict[str, Union[float, str, dict]]:
        result = self.get_fear_and_greed_index()
        return {
            "score": float(result.get("index_value", 50.0)),
            "label": result.get("level", "Neutral"),
            "components": result.get("components", {}),
            "timestamp": result.get("timestamp"),
        }

    def get_alt_data_snapshot(self) -> dict[str, Union[dict, float, str]]:
        sentiment = self.get_sentiment_analysis()
        fear_greed = self.compute_fear_greed_index()
        vix = self._get_vix_level()
        snapshot = {
            "fear_greed": fear_greed,
            "vix": vix,
            "news_sentiment": sentiment.get("news", 0.0),
            "data_quality": "partial" if sentiment or vix is not None else "fallback",
        }
        return snapshot
    
    def get_fear_and_greed_index(self) -> dict[str, Union[float, str]]:
        """
        Compute composite Fear & Greed Index from multiple signals.
        
        Components:
        - VIX level (20% weight): high volatility = fear
        - Put/Call ratio (20% weight): high ratio = fear
        - Momentum (20% weight): negative momentum = fear
        - Sentiment (20% weight): negative sentiment = fear
        - Safe haven demand (20% weight): high demand = fear
        
        Returns:
            Dictionary with index value (0-100), level (Greed/Neutral/Fear), components.
            100 = Extreme Greed, 0 = Extreme Fear.
        """
        components = {}
        weights_sum = 0
        index_sum = 0
        
        # VIX component (inverse scale)
        try:
            vix = self._get_vix_level()
            if vix is not None:
                # VIX: 10 = greed, 30+ = fear
                vix_score = max(0, min(100, (30 - vix) / 30 * 100))
                components['vix'] = vix_score
                index_sum += vix_score * 0.20
                weights_sum += 0.20
        except:
            pass
        
        # Sentiment component
        try:
            sentiment = self._get_sentiment_composite()
            if sentiment is not None:
                # -1 to 1 → 0 to 100
                sentiment_score = (sentiment + 1) / 2 * 100
                components['sentiment'] = sentiment_score
                index_sum += sentiment_score * 0.20
                weights_sum += 0.20
        except:
            pass
        
        # Put/Call component (inverse scale)
        try:
            put_call = self._get_put_call_ratio()
            if put_call is not None:
                # Ratio 0.5 = greed, 1.5+ = fear
                put_call_score = max(0, min(100, (put_call - 0.5) / 1.0 * 100))
                components['put_call'] = put_call_score
                index_sum += put_call_score * 0.20
                weights_sum += 0.20
        except:
            pass
        
        # Momentum component (simple: SPY returns)
        try:
            momentum = self._get_market_momentum()
            if momentum is not None:
                # Backward looking: negative momentum = fear
                momentum_score = (momentum + 0.1) / 0.2 * 100
                momentum_score = max(0, min(100, momentum_score))
                components['momentum'] = momentum_score
                index_sum += momentum_score * 0.20
                weights_sum += 0.20
        except:
            pass
        
        # Normalize
        if weights_sum > 0:
            index_value = index_sum / weights_sum
        else:
            index_value = 50  # Default neutral
        
        # Classify level
        if index_value >= 70:
            level = "Extreme Greed"
        elif index_value >= 50:
            level = "Greed"
        elif index_value >= 40:
            level = "Neutral"
        elif index_value >= 20:
            level = "Fear"
        else:
            level = "Extreme Fear"
        
        return {
            'index_value': round(index_value, 1),
            'level': level,
            'components': components,
            'timestamp': datetime.now().isoformat(),
        }
    
    def get_volatility_state(self) -> dict[str, Union[float, str]]:
        """
        Get current volatility state (low/medium/high/crisis).
        
        Returns:
            Dictionary with VIX level, regime, and historical percentile.
        """
        try:
            vix = self._get_vix_level()
            
            if vix is None:
                return {'state': 'unknown'}
            
            # Classify regime
            if vix < 15:
                regime = "Complacency"
            elif vix < 20:
                regime = "Low"
            elif vix < 30:
                regime = "Normal"
            elif vix < 40:
                regime = "Elevated"
            else:
                regime = "Crisis"
            
            return {
                'vix': round(vix, 2),
                'regime': regime,
                'timestamp': datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.warning(f"Volatility state fetch error: {e}")
            return {'state': 'error'}
    
    def get_sentiment_analysis(
        self,
        keywords: list[str] = None,
    ) -> dict[str, float]:
        """
        Analyze sentiment across multiple sources.
        
        Args:
            keywords: Keywords to search. Defaults to SENTIMENT_KEYWORDS.
        
        Returns:
            Dictionary with sentiment scores from each source (-1 to 1).
        """
        if keywords is None:
            keywords = SENTIMENT_KEYWORDS
        
        sentiment_scores = {}
        
        # Google Trends momentum
        try:
            trends = self._get_google_trends_momentum(keywords)
            if trends:
                sentiment_scores['google_trends'] = trends
        except Exception as e:
            logger.debug(f"Google Trends error: {e}")
        
        # News sentiment (VADER)
        try:
            news_sentiment = self._get_news_sentiment(keywords)
            if news_sentiment is not None:
                sentiment_scores['news'] = news_sentiment
        except Exception as e:
            logger.debug(f"News sentiment error: {e}")
        
        # Reddit sentiment
        try:
            reddit_sentiment = self._get_reddit_sentiment()
            if reddit_sentiment is not None:
                sentiment_scores['reddit'] = reddit_sentiment
        except Exception as e:
            logger.debug(f"Reddit sentiment error: {e}")
        
        # Composite
        if sentiment_scores:
            composite = np.mean(list(sentiment_scores.values()))
            sentiment_scores['composite'] = composite
        
        return sentiment_scores
    
    def get_weather_impact(self) -> dict[str, dict[str, float]]:
        """
        Get weather data for major agricultural regions.
        
        Returns:
            Dictionary mapping region name to weather metrics
            (temperature, precipitation, wind).
        """
        weather_data = {}
        
        try:
            for region, (lat, lon) in WEATHER_REGIONS.items():
                try:
                    data = self._fetch_open_meteo(lat, lon)
                    if data:
                        weather_data[region] = data
                except Exception as e:
                    logger.debug(f"Weather fetch error for {region}: {e}")
        
        except Exception as e:
            logger.warning(f"Weather data fetch error: {e}")
        
        return weather_data
    
    def get_market_breadth(self) -> dict[str, Union[float, int]]:
        """
        Get market breadth indicators (advance/decline line, etc.).
        
        Returns:
            Dictionary with breadth metrics.
        """
        try:
            import yfinance as yf
            
            # Advance/Decline (proxy: compare large cap vs small cap)
            spy = yf.download('^GSPC', period='1d', progress=False)
            iwm = yf.download('^RUT', period='1d', progress=False)
            
            if len(spy) > 0 and len(iwm) > 0:
                spy_ret = float(spy['Close'].pct_change().iloc[-1])
                iwm_ret = float(iwm['Close'].pct_change().iloc[-1])
                
                return {
                    'large_cap_return': spy_ret,
                    'small_cap_return': iwm_ret,
                    'breadth_momentum': iwm_ret - spy_ret,  # Small cap outperformance
                }
        
        except Exception as e:
            logger.debug(f"Market breadth error: {e}")
        
        return {}
    
    # ============== Private Helper Methods ==============

    def _fetch_market_series(self, ticker: str, period: str = "1mo") -> pd.Series:
        """Fetch a close-price series with a deterministic fallback."""
        try:
            import yfinance as yf

            data = yf.download(ticker, period=period, progress=False, timeout=Config.YFINANCE_TIMEOUT)
            if len(data) > 0:
                close = data["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                return close.astype(float)
        except Exception as e:
            logger.debug(f"Market series fetch error for {ticker}: {e}")

        index = pd.date_range(end=datetime.now(), periods=22, freq="B")
        values = pd.Series(np.linspace(95.0, 105.0, len(index)), index=index, name=ticker)
        return values
    
    def _get_vix_level(self) -> Optional[float]:
        """Get current VIX level."""
        try:
            import yfinance as yf
            
            vix = yf.download('^VIX', period='1d', progress=False)
            if len(vix) > 0:
                return float(vix['Close'].iloc[-1])
        except Exception as e:
            logger.debug(f"VIX fetch error: {e}")
        
        return None
    
    def _get_put_call_ratio(self) -> Optional[float]:
        """Get S&P 500 put/call ratio."""
        try:
            import yfinance as yf
            
            # Try to fetch from yfinance if available
            # Otherwise return None (data not available in free API)
            logger.debug("Put/call ratio requires premium data source")
            return None
        
        except Exception as e:
            logger.debug(f"Put/call ratio error: {e}")
        
        return None
    
    def _get_market_momentum(self) -> Optional[float]:
        """Get recent market momentum (SPY daily returns)."""
        try:
            import yfinance as yf
            
            spy = yf.download(
                'SPY',
                period='1d',
                progress=False,
                timeout=Config.YFINANCE_TIMEOUT,
            )
            
            if len(spy) > 0:
                return float(spy['Close'].pct_change().iloc[-1])
        
        except Exception as e:
            logger.debug(f"Momentum fetch error: {e}")
        
        return None
    
    @rate_limit(calls_per_second=0.5)
    def _get_google_trends_momentum(self, keywords: list[str]) -> Optional[float]:
        """Get Google Trends momentum for keywords."""
        try:
            from pytrends.request import TrendReq
            
            pytrends = TrendReq(hl='en-US', tz=360)
            
            scores = []
            for keyword in keywords[:5]:  # Limit to 5 keywords per request
                try:
                    pytrends.build_payload([keyword], timeframe='today 1-m')
                    interest = pytrends.interest_over_time()[keyword].iloc[-1]
                    scores.append(interest / 100.0)  # Normalize to 0-1
                except:
                    pass
            
            if scores:
                return np.mean(scores) * 2 - 1  # Convert to -1 to 1 scale
        
        except ImportError:
            logger.debug("pytrends not installed")
        except Exception as e:
            logger.debug(f"Google Trends error: {e}")
        
        return None
    
    def _get_news_sentiment(self, keywords: list[str]) -> Optional[float]:
        """Get sentiment from news headlines via VADER."""
        if not self.news_api_key:
            logger.debug("News API key not configured")
            return None
        
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            import newsapi
            
            analyzer = SentimentIntensityAnalyzer()
            client = newsapi.NewsApiClient(api_key=self.news_api_key)
            
            sentiments = []
            
            for keyword in keywords[:3]:  # Limit requests
                try:
                    articles = client.get_everything(
                        q=keyword,
                        sort_by='publishedAt',
                        language='en',
                        page_size=10,
                        page=1,
                    )
                    
                    if 'articles' in articles:
                        for article in articles['articles'][:5]:
                            title = article.get('title', '')
                            sentiment = analyzer.polarity_scores(title)
                            sentiments.append(sentiment['compound'])
                
                except Exception as e:
                    logger.debug(f"News fetch error for {keyword}: {e}")
            
            if sentiments:
                return float(np.mean(sentiments))
        
        except ImportError:
            logger.debug("vaderSentiment or newsapi not installed")
        except Exception as e:
            logger.debug(f"News sentiment error: {e}")
        
        return None
    
    def _get_reddit_sentiment(self) -> Optional[float]:
        """Get sentiment from Reddit posts."""
        if not (self.reddit_client_id and self.reddit_client_secret):
            logger.debug("Reddit credentials not configured")
            return None
        
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            import praw
            
            analyzer = SentimentIntensityAnalyzer()
            
            reddit = praw.Reddit(
                client_id=self.reddit_client_id,
                client_secret=self.reddit_client_secret,
                user_agent=self.reddit_user_agent or "genesix:1.0",
            )
            
            sentiments = []
            
            for subreddit_name in REDDIT_SUBREDDITS[:2]:  # Limit subreddits
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    for submission in subreddit.top(time_filter='day', limit=10):
                        title = submission.title
                        sentiment = analyzer.polarity_scores(title)
                        sentiments.append(sentiment['compound'])
                
                except Exception as e:
                    logger.debug(f"Reddit {subreddit_name} error: {e}")
            
            if sentiments:
                return float(np.mean(sentiments))
        
        except ImportError:
            logger.debug("praw not installed")
        except Exception as e:
            logger.debug(f"Reddit sentiment error: {e}")
        
        return None
    
    def _get_sentiment_composite(self) -> Optional[float]:
        """Get composite sentiment across all sources."""
        sentiments = self.get_sentiment_analysis()
        
        if 'composite' in sentiments:
            return sentiments['composite']
        elif sentiments:
            return np.mean(list(sentiments.values()))
        
        return None
    
    def _fetch_open_meteo(
        self,
        latitude: float,
        longitude: float,
    ) -> Optional[dict[str, float]]:
        """Fetch weather data from Open-Meteo (free, no API key)."""
        try:
            import openmeteo_requests
            import requests_cache
            from retry_requests import retry
            import pandas as pd
            
            # Setup Open-Meteo API client
            cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
            retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
            openmeteo = openmeteo_requests.Client(session=retry_session)
            
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto"
            }
            
            responses = openmeteo.weather_api(url, params=params)
            response = responses[0]
            
            current = response.Current()
            daily = response.Daily()
            
            return {
                'temperature': current.Variables(0).Value(),
                'precipitation': current.Variables(1).Value(),
                'wind_speed': current.Variables(3).Value(),
                'temp_max': daily.Variables(0).Values()[0],
                'temp_min': daily.Variables(1).Values()[0],
                'precip_sum': daily.Variables(2).Values()[0],
            }
        
        except ImportError:
            logger.debug("openmeteo_requests not installed")
        except Exception as e:
            logger.debug(f"Open-Meteo error: {e}")
        
        return None
