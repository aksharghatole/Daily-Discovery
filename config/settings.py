"""Environment-backed application settings."""

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    app_timezone: str
    daily_notification_enabled: bool
    nasa_api_key: str


def get_settings() -> Settings:
    """Load settings from the environment, with safe local defaults."""

    return Settings(
        database_url=os.getenv(
            "DATABASE_URL", "sqlite:///./data/daily_discovery.db"
        ),
        app_timezone=os.getenv("APP_TIMEZONE", "UTC"),
        daily_notification_enabled=_as_bool(
            os.getenv("DAILY_NOTIFICATION_ENABLED")
        ),
        nasa_api_key=os.getenv("NASA_API_KEY", "DEMO_KEY"),
    )