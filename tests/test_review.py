from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import Base, create_engine_from_settings
from database.models import SpacedReview
from database.repository import Repository
from services.review_service import ReviewService


def test_review_schedule_expands_and_resets(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(session)
        user = repository.get_or_create_local_user()
        category = repository.get_or_create_category("Science")
        discovery = repository.create_discovery(
            date(2026, 9, 9), category, "Blue sky", "Atmospheric scattering explains blue light."
        )
        service = ReviewService(session)

        first = service.record_review(user, discovery, True, date(2026, 9, 9))
        second = service.record_review(user, discovery, True, date(2026, 9, 10))
        missed = service.record_review(user, discovery, False, date(2026, 9, 14))
        session.commit()

        assert first.interval_days == 2
        assert second.interval_days == 4
        assert missed.interval_days == 1
        review = session.scalar(select(SpacedReview))
        assert (review.times_correct, review.times_incorrect) == (2, 1)
        assert service.due_reviews(user, date(2026, 9, 15))[0].discovery.title == "Blue sky"