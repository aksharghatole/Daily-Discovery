from datetime import date

from sqlalchemy.orm import Session

from database.db import Base, create_engine_from_settings
from database.repository import Repository
from services.progress_service import ProgressService


def _progress_service(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)
    session = Session(engine)
    user = Repository(session).get_or_create_local_user()
    return session, user, ProgressService(session)


def test_streak_is_idempotent_and_handles_missed_days(monkeypatch):
    session, user, service = _progress_service(monkeypatch)

    first = service.record_view(user, date(2026, 9, 9))
    same_day = service.record_view(user, date(2026, 9, 9))
    consecutive = service.record_view(user, date(2026, 9, 10))
    missed = service.record_view(user, date(2026, 9, 12))

    assert (first.current_streak, first.xp) == (1, 5)
    assert (same_day.current_streak, same_day.xp) == (1, 5)
    assert (consecutive.current_streak, consecutive.xp) == (2, 10)
    assert (missed.current_streak, missed.longest_streak) == (1, 2)
    session.close()


def test_xp_events_and_seven_day_milestone(monkeypatch):
    session, user, service = _progress_service(monkeypatch)

    for day in range(7):
        snapshot = service.record_view(user, date(2026, 9, 9 + day))
    service.record_favorite(user)
    final = service.record_quiz(user, 5, 5)
    session.commit()

    assert snapshot.current_streak == 7
    assert snapshot.xp == 7 * 5 + 100
    assert final.xp == snapshot.xp + 5 + 25 + 50
    assert final.level_name == "Learner"
    assert final.xp_to_next_level == 300 - final.xp
    session.close()