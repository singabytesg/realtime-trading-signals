"""
Production Server Runner for Real-time Trading Signals
Properly configured for server deployment with WebSockets and background tasks
"""

import uvicorn
import asyncio
import logging
from api.index import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 Starting Real-time Trading Signal Server")

    # Run with uvicorn server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
        workers=1,  # Single worker for WebSocket state management
        loop="asyncio"
    )