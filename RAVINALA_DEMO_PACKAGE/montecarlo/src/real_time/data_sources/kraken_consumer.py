"""
Kraken WebSocket Consumer

Connects to Kraken's public WebSocket API for real-time crypto data:
- Ticker data (bid/ask spreads)
- Trade data
- OHLC candles
- Order book updates

No API key required for public data streams.

Kraken WebSocket: wss://ws.kraken.com/

Usage:
    from data_sources.kraken_consumer import init_kraken
    asyncio.create_task(init_kraken())
"""

import websocket
import json
import logging
import asyncio
import os
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class KrakenConsumer:
    """
    Connects to Kraken WebSocket API for cryptocurrency real-time data.
    """
    
    def __init__(self, on_message_callback: Callable):
        self.callback = on_message_callback
        self.ws = None
        self.connected = False
        
        # Kraken symbols (format: XXX/YYY, e.g., XBT/USD = Bitcoin/USD)
        self.pairs = [
            "BTC/USD",   # Bitcoin
            "ETH/USD",   # Ethereum
            "XRP/USD",   # Ripple
            "ADA/USD",   # Cardano
            "SOL/USD",   # Solana
            "DOGE/USD",  # Dogecoin
            "MATIC/USD", # Polygon
        ]
        
    def on_message(self, ws, message: str) -> None:
        """
        Parse Kraken WebSocket message format.
        
        Example ticker message:
            [
                123,                          # Channel ID
                {
                    "a": [150.25, 456],      # Ask [price, wholeLots]
                    "b": [150.24, 789],      # Bid [price, wholeLots]
                    "c": [150.25, 100],      # Close [price, lot volume]
                    "h": [150.50, 150.40],   # High [today, 24h]
                    "l": [150.00, 149.50],   # Low [today, 24h]
                    "o": [150.10, 150.05],   # Open [today, 24h]
                    "p": [150.27, 150.20],   # VWAP [today, 24h]
                    "t": [1245, 5890],       # Trades [today, 24h]
                    "v": [1234567, 1234567], # Volume [today, 24h]
                },
                "ticker",
                "BTC/USD"
            ]
        """
        try:
            if isinstance(message, str):
                message = json.loads(message)
            
            # Kraken format: [channel_id, data, type, symbol]
            if isinstance(message, list) and len(message) >= 3:
                if message[2] == "ticker" and len(message) >= 4:
                    pair = message[3]
                    ticker = message[1]
                    
                    # Extract the lastmost values
                    ask_price = float(ticker.get("a", [0])[0]) if ticker.get("a") else 0
                    bid_price = float(ticker.get("b", [0])[0]) if ticker.get("b") else 0
                    close_price = float(ticker.get("c", [0])[0]) if ticker.get("c") else (ask_price + bid_price) / 2
                    volume = float(ticker.get("v", [0])[0]) if ticker.get("v") else 0
                    
                    market_data = {
                        "source": "kraken",
                        "symbol": pair.replace("/", ""),  # BTCUSD format
                        "pair": pair,
                        "price": close_price,
                        "bid": bid_price,
                        "ask": ask_price,
                        "spread": ask_price - bid_price,
                        "volume": volume,
                    }
                    
                    # Broadcast asynchronously
                    asyncio.create_task(self.callback(market_data))
                    
        except json.JSONDecodeError as e:
            logger.error(f"Kraken JSON parse error: {e}")
        except Exception as e:
            logger.error(f"Kraken message error: {e}")
    
    def on_error(self, ws, error: Exception) -> None:
        """Handle WebSocket error"""
        logger.error(f"Kraken error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg) -> None:
        """Handle connection closure"""
        self.connected = False
        logger.warning(f"Kraken connection closed (code: {close_status_code})")
        asyncio.sleep(5)
        self.connect()
    
    def on_open(self, ws) -> None:
        """Handle connection opened"""
        self.connected = True
        logger.info("Kraken WebSocket connected")
        
        # Subscribe to ticker updates
        subscription = {
            "event": "subscribe",
            "pair": self.pairs,
            "subscription": {"name": "ticker"}
        }
        
        try:
            ws.send(json.dumps(subscription))
            logger.debug(f"  → Subscribed to {len(self.pairs)} crypto pairs")
        except Exception as e:
            logger.error(f"Failed to subscribe: {e}")
    
    def connect(self) -> None:
        """Establish WebSocket connection to Kraken"""
        try:
            logger.info("Connecting to Kraken WebSocket...")
            
            self.ws = websocket.WebSocketApp(
                "wss://ws.kraken.com/",
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
            )
            self.ws.on_open = self.on_open
            
            # Run forever (blocks)
            self.ws.run_forever()
            
        except Exception as e:
            logger.error(f"Failed to connect to Kraken: {e}")
            self.connected = False

# Global consumer instance
_kraken_consumer: Optional[KrakenConsumer] = None

async def init_kraken(callback: Callable) -> None:
    """
    Initialize Kraken consumer in a background task.
    
    Kraken requires no API key for public data.
    
    Args:
        callback: Async function to call with market data
    """
    global _kraken_consumer
    
    logger.info("Starting Kraken consumer...")
    
    _kraken_consumer = KrakenConsumer(
        on_message_callback=callback
    )
    
    # Run in thread pool (WebSocket blocks)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _kraken_consumer.connect)

async def kraken_consumer() -> None:
    """
    Entry point for FastAPI startup.
    
    Usage in websocket_server.py:
        asyncio.create_task(kraken_consumer())
    """
    from websocket_server import manager
    
    await init_kraken(
        callback=lambda msg: manager.broadcast(msg, throttle_key=f"kraken_{msg.get('symbol')}")
    )
