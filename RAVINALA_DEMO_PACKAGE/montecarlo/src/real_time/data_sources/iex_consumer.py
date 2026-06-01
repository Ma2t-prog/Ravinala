"""
IEX Cloud WebSocket Consumer (Optional)

Alternative real-time data source for US stocks.
IEX Cloud provides lower latency than Finnhub for US markets.

Setup:
1. Create account at https://iexcloud.io
2. Get API key from dashboard
3. Add to .env: IEX_API_KEY=your_key_here

Note: IEX Cloud has been deprecated/restructured. This is included for completeness
but Finnhub is recommended for production use.

Usage:
    from data_sources.iex_consumer import init_iex
    asyncio.create_task(init_iex())
"""

import websocket
import json
import logging
import asyncio
import os
from typing import Callable, Optional

logger = logging.getLogger(__name__)

IEX_TOKEN = os.getenv("IEX_API_KEY", "")

class IEXConsumer:
    """
    Connects to IEX Cloud WebSocket for US stock data.
    
    Note: IEX Cloud's WebSocket API has changed. This is a template
    for connecting to alternative US stock feeds.
    """
    
    def __init__(self, api_key: str, on_message_callback: Callable):
        self.api_key = api_key
        self.callback = on_message_callback
        self.ws = None
        self.connected = False
        
        # Top US stocks
        self.symbols = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
            "NFLX", "UBER", "COIN"
        ]
        
    def on_message(self, ws, message: str) -> None:
        """
        Parse IEX Cloud message format.
        """
        try:
            if isinstance(message, str):
                data = json.loads(message)
            else:
                data = message
            
            # IEX format varies, but typically includes symbol, price, etc.
            if isinstance(data, dict) and "symbol" in data:
                market_data = {
                    "source": "iex",
                    "symbol": data.get("symbol"),
                    "price": data.get("price"),
                    "size": data.get("size"),
                    "timestamp": data.get("time"),
                }
                
                asyncio.create_task(self.callback(market_data))
                
        except json.JSONDecodeError:
            pass  # Ignore parse errors
        except Exception as e:
            logger.error(f"IEX message error: {e}")
    
    def on_error(self, ws, error: Exception) -> None:
        logger.error(f"IEX error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg) -> None:
        self.connected = False
        logger.warning(f"IEX connection closed")
    
    def on_open(self, ws) -> None:
        self.connected = True
        logger.info("IEX WebSocket connected")
    
    def connect(self) -> None:
        """Connect to IEX Cloud WebSocket"""
        try:
            logger.info("Connecting to IEX Cloud...")
            # IEX Cloud endpoint (check current docs at https://iexcloud.io)
            # This is a placeholder URL:
            ws_url = f"wss://ws-api.iextrading.com/1.0/last?token={self.api_key}"
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
            )
            self.ws.on_open = self.on_open
            self.ws.run_forever()
            
        except Exception as e:
            logger.error(f"Failed to connect to IEX: {e}")
            self.connected = False

async def init_iex(callback: Callable) -> None:
    """Initialize IEX consumer"""
    if not IEX_TOKEN:
        logger.warning("IEX_API_KEY not set - skipping IEX consumer")
        return
    
    logger.info("Starting IEX consumer...")
    consumer = IEXConsumer(IEX_TOKEN, callback)
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, consumer.connect)

async def iex_consumer() -> None:
    """Entry point for FastAPI startup"""
    from websocket_server import manager
    
    await init_iex(
        callback=lambda msg: manager.broadcast(msg, throttle_key=f"iex_{msg.get('symbol')}")
    )
