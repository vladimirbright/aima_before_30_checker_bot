"""User service layer for database operations using raw SQL."""

from datetime import datetime
from typing import Optional
import aiosqlite
from app.config import settings


async def create_user(
    telegram_user_id: int,
    email_encrypted: str,
    password_encrypted: str
) -> int:
    """
    Create a new user with encrypted credentials.

    Args:
        telegram_user_id: Telegram user ID
        email_encrypted: Encrypted email
        password_encrypted: Encrypted password

    Returns:
        int: ID of created user

    Raises:
        aiosqlite.IntegrityError: If user already exists
    """
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(settings.database_path) as conn:
        cursor = await conn.execute("""
            INSERT INTO users (
                telegram_user_id,
                email_encrypted,
                password_encrypted,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (telegram_user_id, email_encrypted, password_encrypted, now, now))

        await conn.commit()
        return cursor.lastrowid


async def get_user_by_telegram_id(telegram_user_id: int) -> Optional[dict]:
    """
    Get user by Telegram user ID.

    Args:
        telegram_user_id: Telegram user ID

    Returns:
        dict | None: User data as dictionary, or None if not found
    """
    async with aiosqlite.connect(settings.database_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("""
            SELECT * FROM users WHERE telegram_user_id = ?
        """, (telegram_user_id,))

        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_user_credentials(
    telegram_user_id: int,
    email_encrypted: str,
    password_encrypted: str
) -> None:
    """
    Update user credentials.

    Args:
        telegram_user_id: Telegram user ID
        email_encrypted: New encrypted email
        password_encrypted: New encrypted password
    """
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(settings.database_path) as conn:
        await conn.execute("""
            UPDATE users
            SET email_encrypted = ?,
                password_encrypted = ?,
                updated_at = ?
            WHERE telegram_user_id = ?
        """, (email_encrypted, password_encrypted, now, telegram_user_id))

        await conn.commit()


async def update_last_status(
    telegram_user_id: int,
    status: str,
    checked_at: str
) -> None:
    """
    Update user's last status and check time.

    Args:
        telegram_user_id: Telegram user ID
        status: Status text
        checked_at: ISO format timestamp
    """
    now = datetime.utcnow().isoformat()

    async with aiosqlite.connect(settings.database_path) as conn:
        await conn.execute("""
            UPDATE users
            SET last_status = ?,
                last_checked_at = ?,
                updated_at = ?
            WHERE telegram_user_id = ?
        """, (status, checked_at, now, telegram_user_id))

        await conn.commit()


async def set_periodic_check(telegram_user_id: int, enabled: bool) -> None:
    """
    Enable or disable periodic checks for a user.

    Args:
        telegram_user_id: Telegram user ID
        enabled: True to enable, False to disable
    """
    now = datetime.utcnow().isoformat()
    enabled_int = 1 if enabled else 0

    async with aiosqlite.connect(settings.database_path) as conn:
        await conn.execute("""
            UPDATE users
            SET periodic_check_enabled = ?,
                updated_at = ?
            WHERE telegram_user_id = ?
        """, (enabled_int, now, telegram_user_id))

        await conn.commit()


async def get_users_with_periodic_check() -> list[dict]:
    """
    Get all users who have periodic checks enabled.

    Returns:
        list[dict]: List of user records
    """
    async with aiosqlite.connect(settings.database_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute("""
            SELECT * FROM users
            WHERE periodic_check_enabled = 1
            ORDER BY id
        """)

        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_user(telegram_user_id: int) -> None:
    """
    Delete a user and all their data.

    Args:
        telegram_user_id: Telegram user ID
    """
    async with aiosqlite.connect(settings.database_path) as conn:
        await conn.execute("""
            DELETE FROM users WHERE telegram_user_id = ?
        """, (telegram_user_id,))

        await conn.commit()
