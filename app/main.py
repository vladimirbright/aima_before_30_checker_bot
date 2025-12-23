"""Main FastAPI application with Telegram bot integration."""

import logging
import sys
import asyncio
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, close_db
from app.routers import web
from app.telegram_bot.bot import create_bot_application, start_bot, stop_bot
from app.telegram_bot.scheduler import StatusScheduler


# Configure logging to output to stdout/stderr
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # Force reconfiguration
)

# Set log level for all loggers
logging.getLogger().setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

logger = logging.getLogger(__name__)

# Log startup configuration
logger.info("="*60)
logger.info("AIMA Status Checker - Configuration")
logger.info("="*60)
logger.info(f"Log Level: {settings.log_level}")
logger.info(f"Database Path: {settings.database_path}")
logger.info(f"AIMA Login URL: {settings.aima_login_url}")
logger.info(f"AIMA Check URL: {settings.aima_check_url}")
logger.info(f"SSL Verification: {settings.verify_ssl}")

# Mask credentials in proxy URL for logging
if settings.proxy_url:
    parsed = urlparse(settings.proxy_url)
    if parsed.username:
        masked_proxy = f"{parsed.scheme}://***:***@{parsed.hostname}:{parsed.port}"
    else:
        masked_proxy = settings.proxy_url
    logger.info(f"HTTP Proxy: {masked_proxy}")
else:
    logger.info("HTTP Proxy: Not configured")

logger.info("="*60)

# Global bot application and scheduler
bot_app = None
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Args:
        app: FastAPI application
    """
    # Startup
    logger.info("Starting AIMA Status Checker...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Create and start bot
    global bot_app, scheduler
    bot_app = create_bot_application()

    # Start bot in background
    await start_bot(bot_app)

    # Create and start scheduler
    scheduler = StatusScheduler(bot_app.bot)
    scheduler.start()

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Stop scheduler
    if scheduler:
        scheduler.stop()

    # Stop bot
    if bot_app:
        await stop_bot(bot_app)

    # Close database
    await close_db()

    logger.info("Application stopped")


# Create FastAPI app
app = FastAPI(
    title="AIMA Status Checker",
    description="Check AIMA application status via web interface or Telegram bot",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware (optional, for web interface)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(web.router, tags=["web"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
