from datetime import date

from sqlalchemy.orm import Session

from database.db import Base, create_engine_from_settings
from database.repository import Repository
from services.statistics_service import StatisticsService


def test_statistics_snapshot_aggregates_learning_activity(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(session)
        user = repository.get_or_create_local_user()
        science = repository.get_or_create_category("Science")
        history = repository.get_or_create_category("History")
        first = repository.create_discovery(
            date(2026, 8, 31), science, "Blue sky", "Atmospheric scattering explains blue light."
        )
        second = repository.create_discovery(
            date(2026, 9, 1), history, "Moon landing", "Apollo 11 landed on the Moon."
        )
        repository.mark_viewed(user, first, favorite=True)
        repository.mark_viewed(user, second)
        repository.add_learning_history(user, first, "viewed", date(2026, 8, 31))
        repository.add_learning_history(user, second, "viewed", date(2026, 9, 1))
        repository.create_quiz_attempt(user, date(2026, 9, 1), 4, 5)
        session.commit()

        snapshot = StatisticsService(session).snapshot(user)

        assert snapshot.discoveries_viewed == 2
        assert snapshot.favorites == 1
        assert snapshot.quiz_questions_answered == 5
        assert snapshot.quiz_accuracy == 0.8
        assert snapshot.category_counts == {"Science": 1, "History": 1}
        assert snapshot.monthly_activity == {"2026-08": 1, "2026-09": 1}