"""Simple spaced-repetition scheduling for previously learned discoveries."""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from database.models import Discovery, SpacedReview, User
from database.repository import Repository


@dataclass(frozen=True)
class ReviewResult:
    discovery: Discovery
    remembered: bool
    next_review_date: date
    interval_days: int


class ReviewService:
    """Schedule reviews using a small, transparent interval algorithm."""

    MAX_INTERVAL_DAYS = 30

    def __init__(self, session: Session):
        self.repository = Repository(session)

    def due_reviews(self, user: User, review_date: date) -> list[SpacedReview]:
        return self.repository.list_due_reviews(user, review_date)

    def bootstrap_viewed(self, user: User, review_date: date) -> None:
        """Make previously viewed discoveries available for their first review."""

        for discovery in self.repository.list_viewed_discoveries(user):
            if self.repository.get_spaced_review(user, discovery) is None:
                self.repository.session.add(
                    SpacedReview(
                        user=user,
                        discovery=discovery,
                        last_seen=review_date,
                        next_review_date=review_date,
                        interval_days=1,
                    )
                )
        self.repository.session.flush()

    def record_review(
        self,
        user: User,
        discovery: Discovery,
        remembered: bool,
        review_date: date,
    ) -> ReviewResult:
        review = self.repository.get_spaced_review(user, discovery)
        if review is None:
            review = SpacedReview(
                user=user,
                discovery=discovery,
                last_seen=review_date,
                times_correct=0,
                times_incorrect=0,
                interval_days=1,
                next_review_date=review_date + timedelta(days=1),
            )
            self.repository.session.add(review)

        review.last_seen = review_date
        if remembered:
            review.times_correct += 1
            review.interval_days = min(
                self.MAX_INTERVAL_DAYS, max(1, review.interval_days * 2)
            )
        else:
            review.times_incorrect += 1
            review.interval_days = 1
        review.next_review_date = review_date + timedelta(days=review.interval_days)
        self.repository.session.flush()
        return ReviewResult(
            discovery=discovery,
            remembered=remembered,
            next_review_date=review.next_review_date,
            interval_days=review.interval_days,
        )