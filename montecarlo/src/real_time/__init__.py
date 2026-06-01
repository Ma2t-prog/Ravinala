"""
RAVINALA Real-Time Data Pipeline Module

Provides WebSocket streaming of market data from multiple sources:
- Finnhub (stocks, forex, crypto)
- Kraken (crypto exchange)
- IEX Cloud (US stocks alternative)

Usage:
    from real_time.websocket_server import app
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

__version__ = "3.0.0"
__author__ = "RAVINALA Real-Time Team"

import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
