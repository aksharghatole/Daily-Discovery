from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import Base, create_engine_from_settings
from database.models import Quiz, QuizAttempt
from services.discovery_service import DailyDiscoveryService
from services.quiz_service import QuizService


def test_quiz_generation_is_persisted_and_idempotent(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        discoveries = DailyDiscoveryService(session).generate(date(2026, 9, 9))
        service = QuizService(session)
        first = service.get_or_generate(date(2026, 9, 9), discoveries)
        repeated = service.get_or_generate(date(2026, 9, 9), discoveries)

        assert len(first) == 5
        assert [question.id for question in repeated] == [question.id for question in first]
        assert len(session.scalars(select(Quiz)).all()) == 5


def test_quiz_scoring_and_attempt_persistence(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        discoveries = DailyDiscoveryService(session).generate(date(2026, 9, 9))
        service = QuizService(session)
        questions = service.get_or_generate(date(2026, 9, 9), discoveries)
        answers = {question.id: question.correct_answer for question in questions}
        score, results = service.score_answers(questions, answers)
        user = service.repository.get_or_create_local_user()
        service.repository.create_quiz_attempt(user, date(2026, 9, 9), score, len(questions))
        session.commit()

        assert score == 5
        assert all(results)
        assert len(session.scalars(select(QuizAttempt)).all()) == 1