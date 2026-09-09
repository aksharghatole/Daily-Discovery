"""Aggregations for the learning statistics dashboard."""

from collections import Counter
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database.models import (
    Category,
    Discovery,
    LearningHistory,
    QuizAttempt,
    User,
    UserDiscovery,
)


@dataclass(frozen=True)
class StatisticsSnapshot:
    discoveries_viewed: int
    favorites: int
    quiz_questions_answered: int
    quiz_accuracy: float
    category_counts: dict[str, int]
    monthly_activity: dict[str, int]


class StatisticsService:
    """Compute user statistics from persisted interactions and attempts."""

    def __init__(self, session: Session):
        self.session = session

    def snapshot(self, user: User) -> StatisticsSnapshot:
        viewed = self.session.scalar(
            select(func.count(UserDiscovery.id)).where(
                UserDiscovery.user_id == user.id,
                UserDiscovery.viewed.is_(True),
            )
        ) or 0
        favorites = self.session.scalar(
            select(func.count(UserDiscovery.id)).where(
                UserDiscovery.user_id == user.id,
                UserDiscovery.favorite.is_(True),
            )
        ) or 0
        attempts = list(
            self.session.scalars(
                select(QuizAttempt).where(QuizAttempt.user_id == user.id)
            ).all()
        )
        questions_answered = sum(attempt.total_questions for attempt in attempts)
        correct_answers = sum(attempt.score for attempt in attempts)
        accuracy = correct_answers / questions_answered if questions_answered else 0.0
        category_counts = self._category_counts(user)
        monthly_activity = self._monthly_activity(user)
        return StatisticsSnapshot(
            discoveries_viewed=viewed,
            favorites=favorites,
            quiz_questions_answered=questions_answered,
            quiz_accuracy=accuracy,
            category_counts=category_counts,
            monthly_activity=monthly_activity,
        )

    def _category_counts(self, user: User) -> dict[str, int]:
        statement = (
            select(Category.name, func.count(UserDiscovery.id))
            .join(Discovery, Discovery.category_id == Category.id)
            .join(UserDiscovery, UserDiscovery.discovery_id == Discovery.id)
            .where(
                UserDiscovery.user_id == user.id,
                UserDiscovery.viewed.is_(True),
            )
            .group_by(Category.name)
            .order_by(func.count(UserDiscovery.id).desc())
        )
        return {name: count for name, count in self.session.execute(statement)}

    def _monthly_activity(self, user: User) -> dict[str, int]:
        entries = self.session.scalars(
            select(LearningHistory).where(LearningHistory.user_id == user.id)
        ).all()
        counts = Counter(entry.date.strftime("%Y-%m") for entry in entries)
        return dict(sorted(counts.items()))