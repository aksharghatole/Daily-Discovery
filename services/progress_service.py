"""Learning streak and knowledge XP business rules."""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from database.models import User, UserProgress
from database.repository import Repository


@dataclass(frozen=True)
class ProgressSnapshot:
    xp: int
    current_streak: int
    longest_streak: int
    level: int
    level_name: str
    xp_to_next_level: int


class ProgressService:
    VIEW_XP = 5
    FAVORITE_XP = 5
    QUIZ_XP = 25
    PERFECT_QUIZ_XP = 50
    MILESTONE_XP = {7: 100, 30: 500}
    LEVELS = (
        (1, 0, "Curious"),
        (5, 100, "Learner"),
        (10, 300, "Knowledge Seeker"),
        (25, 1_000, "Scholar"),
        (50, 3_000, "Polymath"),
    )

    def __init__(self, session: Session):
        self.repository = Repository(session)

    def record_view(self, user: User, activity_date: date) -> ProgressSnapshot:
        progress = self.repository.get_or_create_progress(user)
        last_date = progress.last_active_date
        if last_date is None or activity_date > last_date:
            if last_date == activity_date - timedelta(days=1):
                progress.current_streak += 1
            else:
                progress.current_streak = 1
            progress.longest_streak = max(
                progress.longest_streak, progress.current_streak
            )
            progress.last_active_date = activity_date
            progress.xp += self.VIEW_XP
            progress.xp += self.MILESTONE_XP.get(progress.current_streak, 0)
        return self.snapshot(progress)

    def record_favorite(self, user: User) -> ProgressSnapshot:
        progress = self.repository.get_or_create_progress(user)
        progress.xp += self.FAVORITE_XP
        return self.snapshot(progress)

    def record_quiz(
        self, user: User, score: int, total_questions: int
    ) -> ProgressSnapshot:
        progress = self.repository.get_or_create_progress(user)
        progress.xp += self.QUIZ_XP
        if total_questions > 0 and score == total_questions:
            progress.xp += self.PERFECT_QUIZ_XP
        return self.snapshot(progress)

    @classmethod
    def snapshot(cls, progress: UserProgress) -> ProgressSnapshot:
        selected = cls.LEVELS[0]
        for level in cls.LEVELS:
            if progress.xp >= level[1]:
                selected = level
        next_levels = [level[1] for level in cls.LEVELS if level[1] > progress.xp]
        next_threshold = next_levels[0] if next_levels else selected[1]
        return ProgressSnapshot(
            xp=progress.xp,
            current_streak=progress.current_streak,
            longest_streak=progress.longest_streak,
            level=selected[0],
            level_name=selected[2],
            xp_to_next_level=max(0, next_threshold - progress.xp),
        )