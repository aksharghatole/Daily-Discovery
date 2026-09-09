from datetime import date

from sqlalchemy.orm import Session

from database.db import Base, create_engine_from_settings
from database.repository import Repository
from services.search_service import SearchService


def test_search_matches_source_and_filters_favorites(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(session)
        user = repository.get_or_create_local_user()
        category = repository.get_or_create_category("Science")
        source = repository.create_source("Oceanographic Institute", "https://example.test/ocean")
        favorite = repository.create_discovery(
            date(2026, 9, 9),
            category,
            "Blue current",
            "A current moves through the open water.",
            source=source,
        )
        other = repository.create_discovery(
            date(2026, 9, 8),
            category,
            "Ocean pressure",
            "Pressure changes with depth in the ocean.",
            source=source,
        )
        repository.set_favorite(user, favorite, True)
        session.commit()

        service = SearchService(session)
        all_results = service.search("Oceanographic")
        favorite_results = service.search(
            "Ocean", user=user, favorites_only=True
        )

        assert [result.discovery.title for result in all_results] == [
            "Blue current",
            "Ocean pressure",
        ]
        assert [result.discovery.title for result in favorite_results] == [
            "Blue current"
        ]
        assert favorite_results[0].source_name == "Oceanographic Institute"