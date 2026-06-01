"""
RAVINALA Real-Time WebSocket Server

FastAPI server that:
1. Accepts WebSocket connections from clients
2. Consumes real-time data from multiple sources (Finnhub, Kraken, IEX)
3. Aggregates and broadcasts to all connected clients
4. Implements throttling (max 100 msgs/sec)
5. Handles disconnections gracefully

Usage:
    python websocket_server.py
    # Server runs at http://localhost:8000
    # WebSocket endpoint: ws://localhost:8000/ws/marketdata
    # Health check: http://localhost:8000/health
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import logging
import time
from typing import Set, Dict, Optional
from datetime import datetime
from collections import deque

# ================================
# CONFIGURATION
# ================================

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# ================================
# FastAPI APP SETUP
# ================================

app = FastAPI(
    title="RAVINALA Real-Time Market Data Server",
    description="Streaming market data from Finnhub, Kraken, IEX Cloud",
    version="3.0.0",
)

# CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================
# MARKET DATA MANAGER
# ================================

class MarketDataManager:
    """
    Manages WebSocket connections and broadcasts market data.
    
    Features:
    - Track active connections
    - Broadcast messages to all clients
    - Implement throttling (max 100 msgs/sec per symbol)
    - Track last update times
    """
    
    def __init__(self, throttle_interval: float = 0.01):
        self.active_connections: Set[WebSocket] = set()
        self.last_update_time: Dict[str, float] = {}
        self.throttle_interval = throttle_interval  # 0.01s = 100 msgs/sec
        self.message_count = 0
        self.start_time = time.time()
        self.subscription_filters: Dict[WebSocket, Set[str]] = {}  # Per-client symbol filters
        
    async def connect(self, websocket: WebSocket) -> None:
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscription_filters[websocket] = set()  # Empty = receive all
        
        logger.info(
            f"Client connected [{len(self.active_connections)} active]"
        )
        
    def disconnect(self, websocket: WebSocket) -> None:
        """Remove disconnected client"""
        self.active_connections.discard(websocket)
        self.subscription_filters.pop(websocket, None)
        
        logger.info(
            f"Client disconnected [{len(self.active_connections)} active]"
        )
    
    def add_subscription(self, websocket: WebSocket, symbol: str) -> None:
        """Add symbol to client's subscription filter"""
        if websocket not in self.subscription_filters:
            self.subscription_filters[websocket] = set()
        self.subscription_filters[websocket].add(symbol.upper())
        logger.debug(f"  → Client subscribed to {symbol}")
    
    def remove_subscription(self, websocket: WebSocket, symbol: str) -> None:
        """Remove symbol from client's subscription filter"""
        if websocket in self.subscription_filters:
            self.subscription_filters[websocket].discard(symbol.upper())
            logger.debug(f"  → Client unsubscribed from {symbol}")
    
    async def broadcast(
        self, 
        message: dict, 
        throttle_key: Optional[str] = None
    ) -> None:
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Dict to send (will be JSON-serialized)
            throttle_key: Key for throttling check (e.g., "finnhub_AAPL")
                         If provided, limits to 1 msg per throttle_interval
        """
        import time
        
        # Throttle check: skip if message too recent
        if throttle_key:
            now = time.time()
            if throttle_key in self.last_update_time:
                if now - self.last_update_time[throttle_key] < self.throttle_interval:
                    return  # Skip this message (throttled)
            self.last_update_time[throttle_key] = now
        
        # Ensure message has timestamp
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        # Track stats
        self.message_count += 1
        
        # Broadcast to all connections
        disconnected = []
        symbol = message.get("symbol", "").upper()
        
        for connection in self.active_connections:
            # Check if client is subscribed to this symbol
            subscriptions = self.subscription_filters.get(connection, set())
            if subscriptions and symbol not in subscriptions:
                continue  # Client didn't subscribe to this symbol
            
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"  Broadcast error: {e}")
                disconnected.append(connection)
        
        # Cleanup disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    def get_stats(self) -> dict:
        """Get server statistics"""
        uptime = time.time() - self.start_time
        return {
            "connected_clients": len(self.active_connections),
            "messages_broadcasted": self.message_count,
            "uptime_seconds": uptime,
            "messages_per_second": self.message_count / uptime if uptime > 0 else 0,
        }

# Singleton manager
manager = MarketDataManager()

# ================================
# WEBSOCKET ENDPOINT
# ================================

@app.websocket("/ws/marketdata")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Main WebSocket endpoint for real-time market data.
    
    Clients connect here and can:
    - Receive broadcast price updates
    - Subscribe/unsubscribe to specific symbols
    
    Message format from client:
        {"action": "subscribe", "symbol": "AAPL"}
        {"action": "unsubscribe", "symbol": "AAPL"}
    
    Message format to client:
        {
            "source": "finnhub",
            "symbol": "AAPL",
            "price": 150.25,
            "volume": 1000000,
            "bid": 150.24,
            "ask": 150.26,
            "timestamp": "2026-03-16T10:30:00.000Z"
        }
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive commands from client
            data = await websocket.receive_text()
            command = json.loads(data)
            
            action = command.get("action")
            symbol = command.get("symbol", "").upper()
            
            if action == "subscribe":
                manager.add_subscription(websocket, symbol)
                
                # Send confirmation
                await websocket.send_json({
                    "type": "subscription_confirmed",
                    "symbol": symbol,
                    "action": "subscribe"
                })
                
            elif action == "unsubscribe":
                manager.remove_subscription(websocket, symbol)
                
                await websocket.send_json({
                    "type": "subscription_confirmed",
                    "symbol": symbol,
                    "action": "unsubscribe"
                })
                
            else:
                logger.warning(f"Unknown action: {action}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# ================================
# HTTP ENDPOINTS
# ================================

@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint with server stats"""
    stats = manager.get_stats()
    return JSONResponse({
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        **stats
    })

@app.get("/stats")
async def get_stats() -> JSONResponse:
    """Get detailed server statistics"""
    return JSONResponse(manager.get_stats())

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "RAVINALA Real-Time Market Data Server",
        "version": "3.0.0",
        "endpoints": {
            "websocket": "ws://localhost:8000/ws/marketdata",
            "health": "http://localhost:8000/health",
            "stats": "http://localhost:8000/stats",
        },
        "docs": "http://localhost:8000/docs"
    }

# ================================
# STARTUP/SHUTDOWN EVENTS
# ================================

@app.on_event("startup")
async def startup_event():
    """
    On server startup, initialize data consumers.
    
    This will be called when the FastAPI app starts.
    """
    logger.info("=" * 60)
    logger.info("RAVINALA Real-Time Server Starting....")
    logger.info("=" * 60)
    
    # Import consumers (they'll create tasks)
    try:
        from data_sources.finnhub_consumer import finnhub_consumer
        from data_sources.kraken_consumer import kraken_consumer
        
        # Create background tasks for data consumers
        logger.info("Starting market data consumers...")
        
        # Note: In production, these would be started in background tasks
        # For now, they're commented to avoid import errors without API keys
        
        # asyncio.create_task(finnhub_consumer())
        # asyncio.create_task(kraken_consumer())
        
        logger.info("Data consumers ready (awaiting API keys in .env)")
        
    except ImportError as e:
        logger.warning(f"Could not import data consumers: {e}")
        logger.warning("Make sure .env has valid API keys to enable streaming")

@app.on_event("shutdown")
async def shutdown_event():
    """On server shutdown"""
    logger.info("=" * 60)
    logger.info("RAVINALA Real-Time Server Shutting Down")
    logger.info(f"   Final stats: {manager.get_stats()}")
    logger.info("=" * 60)

# ================================
# MAIN
# ================================

if __name__ == "__main__":
    import uvicorn
    import os
    
    host = os.getenv("WS_HOST", "0.0.0.0")
    port = int(os.getenv("WS_PORT", 8000))
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
