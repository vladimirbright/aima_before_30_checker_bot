"""Database connection and initialization with aiosqlite."""

import aiosqlite
from pathlib import Path
from app.config import settings


async def get_db_connection() -> aiosqlite.Connection:
    """
    Get a database connection with row factory enabled.

    Returns:
        aiosqlite.Connection: Database connection
    """
    conn = await aiosqlite.connect(settings.database_path)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db() -> None:
    """Initialize database schema - create tables if they don't exist."""

    # Ensure data directory exists
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(settings.database_path) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER UNIQUE NOT NULL,
                email_encrypted TEXT NOT NULL,
                password_encrypted TEXT NOT NULL,
                last_status TEXT,
                last_checked_at TEXT,
                periodic_check_enabled INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_telegram_user_id
            ON users(telegram_user_id)
        """)

        await conn.commit()


async def close_db() -> None:
    """Cleanup database connections. Called on application shutdown."""
    # With aiosqlite, connections are managed per-operation
    # This is a placeholder for future cleanup if needed
    pass
