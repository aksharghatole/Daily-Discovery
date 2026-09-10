"""Automatic, provider-backed daily discovery generation."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import logging
import os
from typing import Iterable
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config.settings import get_settings
from database.models import Discovery, GenerationRun
from database.repository import Repository
from providers.astronomy_provider import AstronomyProvider
from providers.base import ProviderError, ProviderItem
from providers.books_provider import BooksProvider
from providers.country_provider import CountryProvider
from providers.dictionary_provider import DictionaryProvider
from providers.wikipedia_provider import WikipediaProvider
from services.discovery_service import (
    CATALOG_PATH,
    DiscoveryCandidate,
    GenerationError,
    load_local_catalog,
    normalize_title,
)
from services.quiz_service import QuizService


LOGGER = logging.getLogger(__name__)


class GenerationInProgress(GenerationError):
    """Raised when another process is generating the requested date."""


@dataclass(frozen=True)
class GenerationResult:
    discovery_date: date
    status: str
    discoveries: list[Discovery]
    generated_categories: tuple[str, ...]
    failed_categories: tuple[str, ...]
    error_count: int
    last_error: str | None = None


def application_date(now: datetime | None = None) -> date:
    """Return today's date in the configured application timezone."""

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(ZoneInfo(get_settings().app_timezone)).date()


class DailyGenerationService:
    """Coordinate providers, fallback data, validation, persistence, and quiz creation."""

    def __init__(
        self,
        session: Session,
        *,
        candidates: Iterable[DiscoveryCandidate] | None = None,
        providers: dict[str, object] | None = None,
    ):
        self.session = session
        self.repository = Repository(session)
        self.candidates = list(candidates) if candidates is not None else load_local_catalog()
        if providers is not None:
            self.providers = providers
        elif "PYTEST_CURRENT_TEST" in os.environ:
            self.providers = {}
        else:
            self.providers = {
                "Word": DictionaryProvider(),
                "Country": CountryProvider(),
                "Space": AstronomyProvider(),
                "Book": BooksProvider(),
            }
        self.wikipedia = WikipediaProvider()

    def generate_daily_discovery(
        self,
        discovery_date: date,
        *,
        categories: Iterable[str] | None = None,
    ) -> GenerationResult:
        """Generate or recover one idempotent daily collection."""

        category_names = sorted(set(categories or (candidate.category for candidate in self.candidates)))
        if not category_names:
            raise GenerationError("No discovery categories are available")

        run = self._acquire_run(discovery_date)
        existing = self.repository.list_discoveries(discovery_date=discovery_date)
        existing_by_category = {item.category.name: item for item in existing}
        if run.status == "READY" and set(category_names) <= set(existing_by_category):
            return self._result(discovery_date, run, existing, category_names, ())

        run.status = "GENERATING"
        run.started_at = datetime.now(timezone.utc)
        run.completed_at = None
        run.last_error = None
        self.session.commit()

        used_titles = self.repository.used_normalized_titles()
        generated_categories = set(existing_by_category)
        failed_categories: list[str] = []
        errors: list[str] = []

        for category_name in category_names:
            if category_name in existing_by_category:
                continue
            try:
                candidate = self._get_candidate(category_name, discovery_date, used_titles)
                category = self.repository.get_or_create_category(category_name)
                source = self.repository.create_source(
                    candidate.source_name,
                    candidate.source_url,
                    source_date=candidate.source_date,
                    source_identifier=candidate.source_identifier,
                )
                discovery = self.repository.create_discovery(
                    discovery_date,
                    category,
                    candidate.title,
                    candidate.content,
                    normalized_title=normalize_title(candidate.title),
                    subtitle=candidate.subtitle,
                    description=candidate.description,
                    image_url=candidate.image_url,
                    source=source,
                )
                existing_by_category[category_name] = discovery
                generated_categories.add(category_name)
                used_titles.add(normalize_title(candidate.title))
                self._log(discovery_date, category_name, "SUCCESS", candidate.source_name)
            except (ProviderError, ValueError, GenerationError) as error:
                message = f"{category_name}: {error}"
                failed_categories.append(category_name)
                errors.append(message)
                self._log(discovery_date, category_name, "FAILED", "provider", error)

        discoveries = list(existing_by_category.values())
        self.session.flush()
        self.session.commit()
        try:
            if discoveries:
                QuizService(self.session).get_or_generate(discovery_date, sorted(discoveries, key=lambda item: item.category.name))
        except Exception as error:
            # Quiz creation is useful but must not erase a valid discovery day.
            errors.append(f"quiz: {error}")
            self.session.rollback()
            discoveries = self.repository.list_discoveries(discovery_date=discovery_date)

        status = "READY" if not failed_categories else ("PARTIAL" if discoveries else "FAILED")
        run.status = status
        run.completed_at = datetime.now(timezone.utc)
        run.error_count = len(errors)
        run.last_error = "; ".join(errors)[-4000:] if errors else None
        self.session.commit()
        discoveries = self.repository.list_discoveries(discovery_date=discovery_date)

        return self._result(
            discovery_date,
            run,
            discoveries,
            category_names,
            failed_categories,
        )

    def get_status(self, discovery_date: date) -> GenerationRun | None:
        return self.session.scalar(
            select(GenerationRun).where(GenerationRun.date == discovery_date)
        )

    def _acquire_run(self, discovery_date: date) -> GenerationRun:
        run = self.get_status(discovery_date)
        if run is not None and run.status == "GENERATING":
            raise GenerationInProgress(f"Generation already running for {discovery_date}")
        if run is not None:
            return run
        run = GenerationRun(date=discovery_date, status="PENDING")
        self.session.add(run)
        try:
            self.session.flush()
        except IntegrityError as error:
            self.session.rollback()
            existing = self.get_status(discovery_date)
            if existing is None:
                raise GenerationError("Could not acquire generation lock") from error
            if existing.status == "GENERATING":
                raise GenerationInProgress(f"Generation already running for {discovery_date}") from error
            return existing
        return run

    def _get_candidate(
        self,
        category_name: str,
        discovery_date: date,
        used_titles: set[str],
    ) -> DiscoveryCandidate:
        choices = [candidate for candidate in self.candidates if candidate.category == category_name]
        choices.sort(key=lambda candidate: candidate.title)
        if choices:
            start = discovery_date.toordinal() % len(choices)
            choices = choices[start:] + choices[:start]

        provider = self.providers.get(category_name)
        if provider is None and "PYTEST_CURRENT_TEST" not in os.environ:
            provider = self.wikipedia
        if provider is not None:
            queries = choices or [category_name]
            for fallback in queries:
                try:
                    query = fallback.title if isinstance(fallback, DiscoveryCandidate) else fallback
                    item = self._fetch(provider, query, discovery_date)
                    candidate = self._from_provider(category_name, item)
                    self._validate_candidate(candidate)
                    if normalize_title(candidate.title) not in used_titles:
                        return candidate
                except (ProviderError, ValueError) as error:
                    LOGGER.info("provider fallback category=%s error=%s", category_name, error)

        for fallback in choices:
            self._validate_candidate(fallback)
            if normalize_title(fallback.title) not in used_titles:
                return fallback

        raise GenerationError(f"No valid unused content remains for category: {category_name}")

    @staticmethod
    def _fetch(provider: object, query: str, discovery_date: date) -> ProviderItem:
        if isinstance(provider, AstronomyProvider):
            return provider.get_item_by_date(discovery_date)
        return provider.get_item(query)

    @staticmethod
    def _from_provider(category: str, item: ProviderItem) -> DiscoveryCandidate:
        identifier = item.metadata.get("page_id") or item.metadata.get("key")
        return DiscoveryCandidate(
            category=category,
            title=item.title,
            content=item.content,
            source_name=item.source_name,
            source_url=item.source_url,
            subtitle=item.subtitle,
            description=item.description,
            image_url=item.image_url,
            source_identifier=str(identifier) if identifier is not None else None,
            source_date=item.source_date,
        )

    @staticmethod
    def _validate_candidate(candidate: DiscoveryCandidate) -> None:
        parsed = urlparse(candidate.source_url)
        if not candidate.title.strip() or len(candidate.content.strip()) < 20:
            raise ValueError(f"Malformed content: {candidate.title}")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid source URL: {candidate.title}")

    @staticmethod
    def _log(
        discovery_date: date,
        category: str,
        result: str,
        provider: str,
        error: Exception | None = None,
    ) -> None:
        LOGGER.info(
            "generation date=%s category=%s result=%s provider=%s%s",
            discovery_date,
            category,
            result,
            provider,
            f" error={error}" if error else "",
        )

    @staticmethod
    def _result(
        discovery_date: date,
        run: GenerationRun,
        discoveries: list[Discovery],
        categories: list[str],
        failed_categories: Iterable[str],
    ) -> GenerationResult:
        return GenerationResult(
            discovery_date=discovery_date,
            status=run.status,
            discoveries=sorted(discoveries, key=lambda item: item.category.name),
            generated_categories=tuple(sorted(set(categories) - set(failed_categories))),
            failed_categories=tuple(sorted(set(failed_categories))),
            error_count=run.error_count,
            last_error=run.last_error,
        )