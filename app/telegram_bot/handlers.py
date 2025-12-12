"""Telegram bot handlers for AIMA status checking."""

import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from app import aima_checker
from app.services import user_service
from app.crypto import get_encryption_key, encrypt_value, decrypt_value, EncryptionError
from app.config import settings
from app.utils import format_timestamp


logger = logging.getLogger(__name__)

# Conversation states
AWAITING_EMAIL, AWAITING_PASSWORD, AWAITING_PERIODIC_CHOICE = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /start command - begin credential setup."""
    user = update.effective_user
    await update.message.reply_text(
        f"Hello {user.first_name}! 👋\n\n"
        "I can help you check your AIMA application status automatically.\n\n"
        "First, I need your AIMA login credentials.\n"
        "🔒 Don't worry - they will be encrypted and stored securely.\n\n"
        "Please send me your email address:\n\n"
        "💡 Tip: Use /help to see all available commands"
    )
    return AWAITING_EMAIL


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle email input."""
    email = update.message.text.strip()

    # Basic email validation
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        await update.message.reply_text(
            "That doesn't look like a valid email address.\n"
            "Please try again:"
        )
        return AWAITING_EMAIL

    # Store email in context
    context.user_data['email'] = email

    await update.message.reply_text(
        "Great! Now please send me your password:"
    )

    return AWAITING_PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle password input and perform first check."""
    password = update.message.text
    email = context.user_data.get('email')
    user_id = update.effective_user.id

    if not email:
        await update.message.reply_text(
            "Something went wrong. Please start over with /start"
        )
        return ConversationHandler.END

    # Delete the message containing password for security
    try:
        await update.message.delete()
    except Exception:
        pass

    # Send checking message
    status_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Checking your credentials... ⏳"
    )

    # Check credentials
    result = await aima_checker.login_and_get_status(email, password)

    if result['status'] == 'error':
        await status_msg.edit_text(
            f"❌ Error: {result['error']}\n\n"
            "Please check your credentials and try again with /start"
        )
        return ConversationHandler.END

    # Success - encrypt and store credentials
    try:
        encryption_key = get_encryption_key(settings.telegram_bot_token, user_id)
        email_encrypted = encrypt_value(email, encryption_key)
        password_encrypted = encrypt_value(password, encryption_key)

        # Check if user exists
        existing_user = await user_service.get_user_by_telegram_id(user_id)

        if existing_user:
            # Update existing user
            await user_service.update_user_credentials(
                user_id,
                email_encrypted,
                password_encrypted
            )
        else:
            # Create new user
            await user_service.create_user(
                user_id,
                email_encrypted,
                password_encrypted
            )

        # Update last status
        await user_service.update_last_status(
            user_id,
            result['status_text'],
            result['timestamp']
        )

    except Exception as e:
        logger.error(f"Failed to store credentials: {e}")
        await status_msg.edit_text(
            "❌ Error saving your credentials. Please try again later."
        )
        return ConversationHandler.END

    # Send status result
    timestamp_formatted = format_timestamp(result['timestamp'])
    await status_msg.edit_text(
        f"✅ Status Retrieved Successfully!\n\n"
        f"{result['status_text']}\n\n"
        f"Last checked: {timestamp_formatted}"
    )

    # Ask about periodic checks
    keyboard = [
        [
            InlineKeyboardButton("Yes ✅", callback_data="periodic_yes"),
            InlineKeyboardButton("No ❌", callback_data="periodic_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Would you like me to check your status periodically and notify you of any changes?",
        reply_markup=reply_markup
    )

    return AWAITING_PERIODIC_CHOICE


async def periodic_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle periodic check preference."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    enabled = query.data == "periodic_yes"

    try:
        await user_service.set_periodic_check(user_id, enabled)

        if enabled:
            await query.edit_message_text(
                "✅ Periodic checks enabled!\n\n"
                "I will check your status every hour and notify you immediately if there are any changes.\n"
                "Additionally, I'll send you updates at 10 AM and 7 PM (Lisbon time) even if there's no change.\n\n"
                "Commands:\n"
                "/status - Check status now\n"
                "/stop - Disable periodic checks\n"
                "/delete - Delete all your data"
            )
        else:
            await query.edit_message_text(
                "Periodic checks disabled.\n\n"
                "You can still check your status anytime with /status\n"
                "To enable periodic checks later, use /start again."
            )

    except Exception as e:
        logger.error(f"Failed to set periodic check: {e}")
        await query.edit_message_text(
            "❌ Error saving your preference. Please try again later."
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text(
        "Setup cancelled. Use /start to begin again."
    )
    return ConversationHandler.END


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - check status immediately."""
    user_id = update.effective_user.id

    # Get user from database
    user = await user_service.get_user_by_telegram_id(user_id)

    if not user:
        await update.message.reply_text(
            "You haven't set up your credentials yet.\n"
            "Use /start to get started."
        )
        return

    # Decrypt credentials
    try:
        encryption_key = get_encryption_key(settings.telegram_bot_token, user_id)
        email = decrypt_value(user['email_encrypted'], encryption_key)
        password = decrypt_value(user['password_encrypted'], encryption_key)
    except EncryptionError as e:
        logger.error(f"Decryption error for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Error decrypting your credentials.\n"
            "Please set up again with /start"
        )
        return

    # Check status
    status_msg = await update.message.reply_text("Checking... ⏳")

    result = await aima_checker.login_and_get_status(email, password)

    if result['status'] == 'error':
        timestamp_formatted = format_timestamp(result['timestamp'])
        await status_msg.edit_text(
            f"❌ Error: {result['error']}\n\n"
            f"Time: {timestamp_formatted}"
        )
    else:
        # Update last status
        await user_service.update_last_status(
            user_id,
            result['status_text'],
            result['timestamp']
        )

        timestamp_formatted = format_timestamp(result['timestamp'])
        await status_msg.edit_text(
            f"✅ Current Status:\n\n"
            f"{result['status_text']}\n\n"
            f"Last checked: {timestamp_formatted}"
        )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stop command - disable periodic checks."""
    user_id = update.effective_user.id

    user = await user_service.get_user_by_telegram_id(user_id)

    if not user:
        await update.message.reply_text(
            "You don't have any active monitoring."
        )
        return

    await user_service.set_periodic_check(user_id, False)

    await update.message.reply_text(
        "✅ Periodic checks disabled.\n\n"
        "Your credentials are still saved.\n"
        "You can check status anytime with /status\n"
        "To re-enable periodic checks, use /start\n"
        "To completely delete your data, use /delete"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command - show bot information and commands."""
    help_text = (
        "🤖 *AIMA Status Checker Bot*\n\n"
        "I help you monitor your AIMA application status automatically.\n\n"
        "*Available Commands:*\n"
        "/start - Set up your credentials and begin monitoring\n"
        "/status - Check your application status right now\n"
        "/stop - Disable automatic periodic checks\n"
        "/delete - Permanently delete all your data\n"
        "/help - Show this help message\n"
        "/cancel - Cancel current operation\n\n"
        "*How It Works:*\n"
        "1️⃣ Use /start to securely save your AIMA credentials\n"
        "2️⃣ Choose to enable periodic monitoring\n"
        "3️⃣ Receive instant notifications when your status changes\n"
        "4️⃣ Get scheduled updates at 10 AM and 7 PM (Lisbon time)\n\n"
        "*Privacy & Security:*\n"
        "🔒 Your credentials are encrypted with military-grade encryption\n"
        "🗑️ Use /delete to remove all your data anytime\n"
        "🔄 Data is auto-deleted if you block the bot\n"
        "🔐 Your password is never stored in plain text\n\n"
        "*Monitoring Schedule:*\n"
        "• Checks every hour with smart distribution\n"
        "• Immediate notification on status changes\n"
        "• Daily updates at 10 AM & 7 PM if no changes\n\n"
        "Need help? Just ask! 😊"
    )

    await update.message.reply_text(
        help_text,
        parse_mode='Markdown'
    )


async def delete_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete command - completely delete user data."""
    user_id = update.effective_user.id

    user = await user_service.get_user_by_telegram_id(user_id)

    if not user:
        await update.message.reply_text(
            "You don't have any data stored."
        )
        return

    # Delete user data
    await user_service.delete_user(user_id)

    await update.message.reply_text(
        "🗑️ Your data has been completely deleted.\n\n"
        "All your credentials and settings have been removed from our database.\n\n"
        "You can use /start again if you want to set up monitoring in the future."
    )

    logger.info(f"User {user_id} deleted their data")


async def handle_bot_blocked(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when user blocks or deletes the bot."""
    if not update.my_chat_member:
        return

    user_id = update.my_chat_member.from_user.id
    old_status = update.my_chat_member.old_chat_member.status
    new_status = update.my_chat_member.new_chat_member.status

    # If user blocked or kicked the bot, delete their data
    if old_status in ["member", "administrator"] and new_status in ["kicked", "left"]:
        logger.info(f"User {user_id} blocked/removed the bot - deleting their data")

        try:
            user = await user_service.get_user_by_telegram_id(user_id)
            if user:
                await user_service.delete_user(user_id)
                logger.info(f"Successfully deleted data for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting data for user {user_id}: {e}")


def get_conversation_handler():
    """Create and return the conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AWAITING_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)
            ],
            AWAITING_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)
            ],
            AWAITING_PERIODIC_CHOICE: [
                CallbackQueryHandler(periodic_choice, pattern='^periodic_')
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
