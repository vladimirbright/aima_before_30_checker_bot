"""Scheduler for periodic AIMA status checks."""

import asyncio
import logging
import random
from datetime import datetime, time
from typing import Optional
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from app import aima_checker
from app.services import user_service
from app.crypto import get_encryption_key, decrypt_value, EncryptionError
from app.config import settings
from app.utils import format_timestamp


logger = logging.getLogger(__name__)

# Lisbon timezone
LISBON_TZ = pytz.timezone('Europe/Lisbon')

# Scheduled notification times (Lisbon time)
MORNING_HOUR = 10  # 10 AM
EVENING_HOUR = 19  # 7 PM


class StatusScheduler:
    """Manages periodic status checks for all users."""

    def __init__(self, bot: Bot):
        """
        Initialize scheduler.

        Args:
            bot: Telegram bot instance
        """
        self.bot = bot
        self.scheduler = AsyncIOScheduler(timezone=LISBON_TZ)
        self.is_running = False

    def start(self):
        """Start the scheduler."""
        if self.is_running:
            return

        # Schedule hourly checks (at minute 0 of each hour)
        self.scheduler.add_job(
            self.run_hourly_checks,
            trigger=CronTrigger(minute=0, timezone=LISBON_TZ),
            id='hourly_checks'
        )

        # Schedule morning notifications (10 AM Lisbon time)
        self.scheduler.add_job(
            self.send_scheduled_notifications,
            trigger=CronTrigger(hour=MORNING_HOUR, minute=0, timezone=LISBON_TZ),
            id='morning_notifications',
            kwargs={'is_morning': True}
        )

        # Schedule evening notifications (7 PM Lisbon time)
        self.scheduler.add_job(
            self.send_scheduled_notifications,
            trigger=CronTrigger(hour=EVENING_HOUR, minute=0, timezone=LISBON_TZ),
            id='evening_notifications',
            kwargs={'is_morning': False}
        )

        self.scheduler.start()
        self.is_running = True
        logger.info("Status checker scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return

        self.scheduler.shutdown()
        self.is_running = False
        logger.info("Status checker scheduler stopped")

    async def run_hourly_checks(self):
        """
        Run hourly status checks for all users with periodic checks enabled.
        Distributes checks evenly across the hour with jitter.
        """
        try:
            # Get all users with periodic checks enabled
            users = await user_service.get_users_with_periodic_check()

            if not users:
                logger.info("No users with periodic checks enabled")
                return

            num_users = len(users)
            logger.info(f"Starting hourly checks for {num_users} users")

            # Calculate even distribution across 60 minutes
            # Leave some buffer time (50 minutes instead of 60)
            interval_seconds = (50 * 60) / num_users if num_users > 0 else 60

            # Shuffle users to randomize order
            random.shuffle(users)

            # Process each user sequentially with delays
            for i, user in enumerate(users):
                try:
                    # Add small random jitter (±2 minutes)
                    jitter = random.uniform(-120, 120)
                    delay = (i * interval_seconds) + jitter

                    # Don't delay the first user
                    if i > 0 and delay > 0:
                        await asyncio.sleep(delay)

                    await self.check_user_status(user, is_scheduled_notification=False)

                except Exception as e:
                    logger.error(f"Error checking user {user['telegram_user_id']}: {e}")
                    continue

            logger.info("Hourly checks completed")

        except Exception as e:
            logger.error(f"Error in run_hourly_checks: {e}")

    async def check_user_status(
        self,
        user: dict,
        is_scheduled_notification: bool = False
    ):
        """
        Check status for a single user and notify if needed.

        Args:
            user: User record from database
            is_scheduled_notification: True if this is a scheduled 10 AM/7 PM check
        """
        user_id = user['telegram_user_id']

        try:
            # Decrypt credentials
            encryption_key = get_encryption_key(settings.telegram_bot_token, user_id)
            email = decrypt_value(user['email_encrypted'], encryption_key)
            password = decrypt_value(user['password_encrypted'], encryption_key)

            # Check status
            result = await aima_checker.login_and_get_status(email, password)

            # Handle errors
            if result['status'] == 'error':
                # Only notify about errors during scheduled notifications
                if is_scheduled_notification:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=f"⚠️ Status Check Failed\n\n"
                             f"Error: {result['error']}\n\n"
                             f"Time: {result['timestamp']}"
                    )
                logger.warning(f"Check failed for user {user_id}: {result['error']}")
                return

            # Compare with last status
            last_status = user.get('last_status', '')
            status_changed = last_status != result['status_text']

            # Update database
            await user_service.update_last_status(
                user_id,
                result['status_text'],
                result['timestamp']
            )

            # Determine if we should send notification
            should_notify = False
            notification_reason = ""

            if status_changed:
                should_notify = True
                notification_reason = "🔔 Status Changed!"
            elif is_scheduled_notification:
                should_notify = True
                notification_reason = "📋 Scheduled Update"

            # Send notification
            if should_notify:
                timestamp_formatted = format_timestamp(result['timestamp'])
                message = f"{notification_reason}\n\n{result['status_text']}\n\n"
                message += f"Last checked: {timestamp_formatted}"

                await self.bot.send_message(
                    chat_id=user_id,
                    text=message
                )

                logger.info(f"Notified user {user_id}: {notification_reason}")

        except EncryptionError as e:
            logger.error(f"Encryption error for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error checking status for user {user_id}: {e}")

    async def send_scheduled_notifications(self, is_morning: bool = True):
        """
        Send scheduled notifications at 10 AM or 7 PM.

        Args:
            is_morning: True for 10 AM, False for 7 PM
        """
        time_str = "10 AM" if is_morning else "7 PM"
        logger.info(f"Sending {time_str} scheduled notifications")

        try:
            users = await user_service.get_users_with_periodic_check()

            for user in users:
                try:
                    await self.check_user_status(user, is_scheduled_notification=True)
                    # Small delay between notifications to avoid rate limiting
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error in scheduled notification for user {user['telegram_user_id']}: {e}")
                    continue

            logger.info(f"{time_str} scheduled notifications completed")

        except Exception as e:
            logger.error(f"Error in send_scheduled_notifications: {e}")
