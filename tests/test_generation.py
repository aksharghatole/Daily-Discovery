from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import Base, create_engine_from_settings
from database.models import Discovery, GenerationRun, Source
from providers.base import ProviderItem, ProviderUnavailable
from scheduler.daily import create_scheduler, run_daily_generation
from services.daily_generation_service import (
    DailyGenerationService,
    GenerationInProgress,
    application_date,
)
from services.discovery_service import DiscoveryCandidate


def _session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)
    return Session(engine)


def _candidate(category: str, title: str, content: str = "A verified piece of content that is long enough."):
    return DiscoveryCandidate(category, title, content, "Seed Source", f"https://seed.test/{title.lower().replace(' ', '-')}")


class SuccessfulProvider:
    def get_item(self, query: str) -> ProviderItem:
        return ProviderItem(
            title=f"External {query}",
            content="This provider returned a sufficiently detailed sourced explanation.",
            source_name="Test Provider",
            source_url="https://provider.test/item",
            metadata={"page_id": "provider-1"},
        )


class FailingProvider:
    def get_item(self, query: str) -> ProviderItem:
        raise ProviderUnavailable("provider offline")


def test_provider_success_persists_source_metadata_and_quiz(monkeypatch):
    session = _session(monkeypatch)
    try:
        service = DailyGenerationService(
            session,
            candidates=[_candidate("Science", "Sky"), _candidate("History", "Moon")],
            providers={"Science": SuccessfulProvider()},
        )
        result = service.generate_daily_discovery(date(2026, 9, 10))

        assert result.status == "READY"
        assert {item.category.name for item in result.discoveries} == {"Science", "History"}
        source = session.scalars(
            select(Source).where(Source.source_identifier == "provider-1")
        ).one()
        assert source.source_identifier == "provider-1"
        assert len(result.discoveries) == 2
        assert session.scalar(select(GenerationRun).where(GenerationRun.date == date(2026, 9, 10))).status == "READY"
    finally:
        session.close()


def test_provider_failure_uses_seed_fallback(monkeypatch):
    session = _session(monkeypatch)
    try:
        result = DailyGenerationService(
            session,
            candidates=[_candidate("Science", "Sky")],
            providers={"Science": FailingProvider()},
        ).generate_daily_discovery(date(2026, 9, 10))

        assert result.status == "READY"
        assert result.discoveries[0].title == "Sky"
    finally:
        session.close()


def test_partial_generation_recovers_only_missing_category(monkeypatch):
    session = _session(monkeypatch)
    try:
        first = DailyGenerationService(
            session,
            candidates=[_candidate("Science", "Sky"), _candidate("History", "")],
            providers={},
        ).generate_daily_discovery(date(2026, 9, 10))
        assert first.status == "PARTIAL"
        assert first.failed_categories == ("History",)

        second = DailyGenerationService(
            session,
            candidates=[_candidate("Science", "Another Sky"), _candidate("History", "Moon")],
            providers={},
        ).generate_daily_discovery(date(2026, 9, 10))
        assert second.status == "READY"
        assert {item.category.name for item in second.discoveries} == {"Science", "History"}
        assert len(session.scalars(select(Discovery)).all()) == 2
    finally:
        session.close()


def test_generation_is_idempotent_and_locks_active_run(monkeypatch):
    session = _session(monkeypatch)
    try:
        candidates = [_candidate("Science", "Sky"), _candidate("History", "Moon")]
        service = DailyGenerationService(session, candidates=candidates, providers={})
        first = service.generate_daily_discovery(date(2026, 9, 10))
        repeated = service.generate_daily_discovery(date(2026, 9, 10))
        assert [item.id for item in repeated.discoveries] == [item.id for item in first.discoveries]

        session.add(GenerationRun(date=date(2026, 9, 11), status="GENERATING"))
        session.commit()
        with pytest.raises(GenerationInProgress):
            service.generate_daily_discovery(date(2026, 9, 11))
    finally:
        session.close()


def test_application_date_uses_configured_timezone(monkeypatch):
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Kolkata")
    moment = datetime(2026, 9, 9, 20, 0, tzinfo=timezone.utc)
    assert application_date(moment) == date(2026, 9, 10)


def test_scheduler_registers_local_time_job(monkeypatch):
    monkeypatch.setenv("APP_TIMEZONE", "UTC")
    scheduler = create_scheduler(lambda: None)
    try:
        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "daily-discovery-generation"
        fields = {field.name: str(field) for field in jobs[0].trigger.fields}
        assert fields["hour"] == "0"
        assert fields["minute"] == "5"
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


def test_scheduler_runner_closes_session(monkeypatch):
    session = _session(monkeypatch)
    class Factory:
        def __call__(self):
            return session

    run_daily_generation(Factory(), discovery_date=date(2026, 9, 10))
    assert session.is_active
    session.close()