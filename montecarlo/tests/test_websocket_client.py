"""
Test Client for RAVINALA Real-Time WebSocket

Simple Python client to test WebSocket connection and data streaming.

Usage:
    python test_client.py
    # Should connect and display live market data
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestClient:
    """Simple WebSocket client for testing"""
    
    def __init__(self, uri: str = "ws://localhost:8000/ws/marketdata"):
        self.uri = uri
        self.symbols = ["AAPL", "MSFT", "BTCUSD", "ETHUSD"]
        self.message_count = 0
        
    async def connect_and_listen(self):
        """Connect to WebSocket and listen for messages"""
        try:
            async with websockets.connect(self.uri) as websocket:
                logger.info(f"✓ Connected to {self.uri}")
                
                # Subscribe to symbols
                for symbol in self.symbols:
                    msg = json.dumps({"action": "subscribe", "symbol": symbol})
                    await websocket.send(msg)
                    logger.info(f"  → Subscribed to {symbol}")
                
                logger.info("Listening for market data (press Ctrl+C to stop)...\n")
                
                # Listen for messages
                async for message in websocket:
                    data = json.loads(message)
                    self.message_count += 1
                    
                    # Display message
                    if data.get("type") == "subscription_confirmed":
                        logger.info(f"✓ Subscription confirmed: {data.get('symbol')}")
                    else:
                        symbol = data.get("symbol", "UNKNOWN")
                        price = data.get("price", "---")
                        source = data.get("source", "---")
                        
                        print(f"  [{self.message_count:04d}] {symbol:10} ${price:>10} | {source}")
                        
        except asyncio.CancelledError:
            logger.info(f"\n✓ Received {self.message_count} messages")
        except Exception as e:
            logger.error(f"✗ Connection error: {e}")
    
    def run(self):
        """Run the test client"""
        try:
            asyncio.run(self.connect_and_listen())
        except KeyboardInterrupt:
            logger.info("\n✓ Test client stopped")

if __name__ == "__main__":
    client = TestClient()
    client.run()
