from datetime import date

from sqlalchemy.orm import Session

from database.db import Base, create_engine_from_settings
from database.repository import Repository
from services.recommendation_service import RecommendationService


def test_recommendations_prioritize_preferences_and_expand_horizons(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(session)
        user = repository.create_user(preferred_categories=["Science"])
        science = repository.get_or_create_category("Science")
        history = repository.get_or_create_category("History")
        viewed = repository.create_discovery(
            date(2026, 9, 1), science, "Viewed science", "A viewed science discovery."
        )
        favorite = repository.create_discovery(
            date(2026, 9, 2), science, "Favorite science", "A favorite science discovery."
        )
        science_unseen = repository.create_discovery(
            date(2026, 9, 3), science, "New science", "A new science discovery."
        )
        horizon = repository.create_discovery(
            date(2026, 9, 4), history, "New history", "A new history discovery."
        )
        repository.mark_viewed(user, viewed)
        repository.set_favorite(user, favorite, True)
        session.commit()

        recommendations = RecommendationService(session).recommend(user, limit=2)

        assert [item.discovery.title for item in recommendations] == [
            "New science",
            "New history",
        ]
        assert recommendations[0].reason == "Because you enjoy Science"
        assert recommendations[1].reason == "Expand Your Horizons"
        assert science_unseen.id != horizon.id