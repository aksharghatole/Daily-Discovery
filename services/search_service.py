"""Reusable global discovery search operations."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from database.models import Discovery, User
from database.repository import Repository


@dataclass(frozen=True)
class SearchResult:
    """UI-neutral search result metadata."""

    discovery: Discovery
    category: str
    date: date
    source_name: str | None


class SearchService:
    """Search persisted discoveries across all user-facing metadata."""

    def __init__(self, session: Session):
        self.repository = Repository(session)

    def search(
        self,
        query: str,
        *,
        user: User | None = None,
        category_name: str | None = None,
        discovery_date: date | None = None,
        favorites_only: bool = False,
    ) -> list[SearchResult]:
        discoveries = self.repository.list_discoveries(
            discovery_date=discovery_date,
            category_name=category_name,
            search=query.strip() or None,
            user=user,
            favorites_only=favorites_only,
        )
        return [
            SearchResult(
                discovery=discovery,
                category=discovery.category.name,
                date=discovery.date,
                source_name=discovery.source.name if discovery.source else None,
            )
            for discovery in discoveries
        ]