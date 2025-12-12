"""Telegram bot initialization and management."""

import logging
from telegram.ext import Application, CommandHandler
from app.config import settings
from app.telegram_bot.handlers import (
    get_conversation_handler,
    status,
    stop
)


logger = logging.getLogger(__name__)


def create_bot_application() -> Application:
    """
    Create and configure the Telegram bot application.

    Returns:
        Application: Configured bot application
    """
    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()

    # Add conversation handler for /start flow
    application.add_handler(get_conversation_handler())

    # Add command handlers
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stop", stop))

    logger.info("Telegram bot handlers registered")

    return application


async def start_bot(application: Application) -> None:
    """
    Start the bot with polling.

    Args:
        application: The bot application
    """
    logger.info("Starting Telegram bot...")

    # Initialize the application
    await application.initialize()
    await application.start()

    # Start polling
    await application.updater.start_polling(
        allowed_updates=["message", "callback_query"]
    )

    logger.info("Telegram bot started successfully")


async def stop_bot(application: Application) -> None:
    """
    Stop the bot gracefully.

    Args:
        application: The bot application
    """
    logger.info("Stopping Telegram bot...")

    if application.updater.running:
        await application.updater.stop()

    await application.stop()
    await application.shutdown()

    logger.info("Telegram bot stopped")
