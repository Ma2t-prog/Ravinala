"""
Finnhub WebSocket Consumer

Connects to Finnhub WebSocket API and streams real-time market data:
- Stocks (AAPL, MSFT, GOOGL, etc.)
- Forex (EURUSD, GBPUSD, etc.)
- Crypto (Bitcoin, Ethereum, etc.)

Setup:
1. Create free account at https://finnhub.io
2. Get API key from dashboard
3. Add to .env: FINNHUB_API_KEY=your_key_here

Usage:
    from data_sources.finnhub_consumer import init_finnhub
    asyncio.create_task(init_finnhub())
"""

import websocket
import json
import logging
import asyncio
import os
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Get API key from environment
FINNHUB_TOKEN = os.getenv("FINNHUB_API_KEY", "")

class FinnhubConsumer:
    """
    Connects to Finnhub WebSocket and consumes market data.
    """
    
    def __init__(self, api_key: str, on_message_callback: Callable):
        self.api_key = api_key
        self.callback = on_message_callback
        self.ws = None
        self.connected = False
        
        # Symbols to track (30 indices + major stocks, forex, crypto)
        self.symbols = [
            # US Tech Mega-Cap
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
            
            # US Finance/Industrial
            "JPM", "BA", "GS", "CVX", "XOM",
            
            # Major Forex pairs
            "EURUSD=X", "GBPUSD=X", "JPYUSD=X", "CHFUSD=X",
            
            # Crypto (Finnhub format)
            "BINANCE:BTCUSDT", "BINANCE:ETHUSDT",
            
            # Commodities (via Finnhub)
            "GOLD", "SILVER",
        ]
        
    def on_message(self, ws, message: str) -> None:
        """
        Handle incoming message from Finnhub WebSocket.
        
        Example message format:
            {
                "type": "trade",
                "data": [
                    {
                        "s": "AAPL",
                        "p": 150.25,
                        "v": 1000,
                        "t": 1647425400000
                    }
                ]
            }
        """
        try:
            data = json.loads(message)
            
            if data.get("type") == "trade":
                trades = data.get("data", [])
                for trade in trades:
                    market_data = {
                        "source": "finnhub",
                        "symbol": trade.get("s"),
                        "price": trade.get("p"),
                        "volume": trade.get("v"),
                        "timestamp": trade.get("t"),
                    }
                    
                    # Call the broadcast callback (async-safe)
                    asyncio.create_task(self.callback(market_data))
                    
            elif data.get("type") == "ping":
                # Respond to ping
                ws.send(json.dumps({"type": "pong"}))
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
        except Exception as e:
            logger.error(f"Finnhub message error: {e}")
    
    def on_error(self, ws, error: Exception) -> None:
        """Handle WebSocket error"""
        logger.error(f"Finnhub error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg) -> None:
        """Handle connection closure"""
        self.connected = False
        logger.warning(f"Finnhub connection closed (code: {close_status_code})")
        
        # Reconnect after delay
        asyncio.sleep(5)
        self.connect()
    
    def on_open(self, ws) -> None:
        """Handle connection opened"""
        self.connected = True
        logger.info("Finnhub WebSocket connected")
        
        # Subscribe to all symbols
        for symbol in self.symbols:
            try:
                ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                logger.debug(f"  → Subscribed to {symbol}")
            except Exception as e:
                logger.error(f"  Failed to subscribe to {symbol}: {e}")
    
    def connect(self) -> None:
        """Establish WebSocket connection to Finnhub"""
        try:
            logger.info("Connecting to Finnhub WebSocket...")
            
            self.ws = websocket.WebSocketApp(
                f"wss://ws.finnhub.io?token={self.api_key}",
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
            )
            self.ws.on_open = self.on_open
            
            # Run forever (blocks)
            self.ws.run_forever()
            
        except Exception as e:
            logger.error(f"Failed to connect to Finnhub: {e}")
            self.connected = False

# Global consumer instance
_finnhub_consumer: Optional[FinnhubConsumer] = None

async def init_finnhub(callback: Callable) -> None:
    """
    Initialize Finnhub consumer in a background task.
    
    Args:
        callback: Async function to call with market data
    """
    global _finnhub_consumer
    
    if not FINNHUB_TOKEN or FINNHUB_TOKEN == "":
        logger.warning("FINNHUB_API_KEY not set in .env - skipping Finnhub consumer")
        return
    
    logger.info("Starting Finnhub consumer...")
    
    _finnhub_consumer = FinnhubConsumer(
        api_key=FINNHUB_TOKEN,
        on_message_callback=callback
    )
    
    # Run in thread pool (WebSocket blocks)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _finnhub_consumer.connect)

async def finnhub_consumer() -> None:
    """
    Entry point for FastAPI startup.
    
    Usage in websocket_server.py:
        asyncio.create_task(finnhub_consumer())
    """
    from websocket_server import manager
    
    await init_finnhub(
        callback=lambda msg: manager.broadcast(msg, throttle_key=f"finnhub_{msg.get('symbol')}")
    )
