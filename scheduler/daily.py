"""APScheduler integration for automatic daily generation."""

from collections.abc import Callable
from datetime import date
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import sessionmaker

from config.settings import get_settings
from services.daily_generation_service import DailyGenerationService, application_date


def run_daily_generation(
    session_factory: sessionmaker,
    *,
    discovery_date: date | None = None,
) -> None:
    """Run one scheduled generation using a short-lived database session."""

    session = session_factory()
    try:
        DailyGenerationService(session).generate_daily_discovery(
            discovery_date or application_date()
        )
    finally:
        session.close()


def create_scheduler(
    session_factory: sessionmaker,
    *,
    job_runner: Callable[..., None] = run_daily_generation,
) -> BackgroundScheduler:
    """Create, but do not start, the daily scheduler."""

    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=ZoneInfo(settings.app_timezone))
    scheduler.add_job(
        job_runner,
        CronTrigger(hour=0, minute=5, timezone=ZoneInfo(settings.app_timezone)),
        kwargs={"session_factory": session_factory},
        id="daily-discovery-generation",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler