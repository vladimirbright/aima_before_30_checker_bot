"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Telegram Bot Configuration
    telegram_bot_token: str

    # Database
    database_path: str = "./data/aima.db"

    # Logging
    log_level: str = "INFO"

    # AIMA URLs
    aima_login_url: str = "https://services.aima.gov.pt/RAR/login.php"
    aima_check_url: str = "https://services.aima.gov.pt/RAR/login_check3.php"

    # SSL verification (set to False if AIMA has certificate issues)
    verify_ssl: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
