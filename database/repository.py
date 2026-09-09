"""Persistence operations used by services and future UI layers."""

from datetime import date, datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from database.models import (
    Category,
    Discovery,
    LearningHistory,
    Quiz,
    QuizAttempt,
    Source,
    User,
    UserProgress,
    UserDiscovery,
    SpacedReview,
)


class Repository:
    """Small unit-of-work style repository around a caller-owned session."""

    def __init__(self, session: Session):
        self.session = session

    def create_user(
        self,
        timezone_name: str = "UTC",
        preferred_categories: list[str] | None = None,
    ) -> User:
        user = User(
            timezone=timezone_name,
            preferred_categories=preferred_categories or [],
        )
        self.session.add(user)
        self.session.flush()
        return user

    def get_or_create_local_user(self) -> User:
        """Return the one local profile used before authentication exists."""

        user = self.session.scalar(select(User).order_by(User.id).limit(1))
        if user is None:
            user = self.create_user()
        return user

    def get_or_create_progress(self, user: User) -> UserProgress:
        progress = self.session.scalar(
            select(UserProgress).where(UserProgress.user_id == user.id)
        )
        if progress is None:
            progress = UserProgress(user=user)
            self.session.add(progress)
            self.session.flush()
        return progress

    def get_or_create_category(
        self, name: str, description: str | None = None
    ) -> Category:
        category = self.session.scalar(select(Category).where(Category.name == name))
        if category is None:
            category = Category(name=name, description=description)
            self.session.add(category)
            self.session.flush()
        return category

    def list_categories(self) -> list[Category]:
        return list(self.session.scalars(select(Category).order_by(Category.name)).all())

    def create_source(
        self,
        name: str,
        url: str,
        source_date: date | None = None,
    ) -> Source:
        source = Source(name=name, url=url, source_date=source_date)
        self.session.add(source)
        self.session.flush()
        return source

    def create_discovery(
        self,
        discovery_date: date,
        category: Category,
        title: str,
        content: str,
        *,
        normalized_title: str | None = None,
        subtitle: str | None = None,
        description: str | None = None,
        image_url: str | None = None,
        source: Source | None = None,
    ) -> Discovery:
        discovery = Discovery(
            date=discovery_date,
            category=category,
            title=title,
            normalized_title=normalized_title or title.casefold(),
            subtitle=subtitle,
            content=content,
            description=description,
            image_url=image_url,
            source=source,
        )
        self.session.add(discovery)
        self.session.flush()
        return discovery

    def find_discovery(
        self, discovery_date: date, category_name: str, title: str
    ) -> Discovery | None:
        statement = (
            select(Discovery)
            .join(Discovery.category)
            .options(joinedload(Discovery.category), joinedload(Discovery.source))
            .where(
                Discovery.date == discovery_date,
                Category.name == category_name,
                Discovery.title == title,
            )
        )
        return self.session.scalar(statement)

    def list_discoveries(
        self,
        *,
        discovery_date: date | None = None,
        category_name: str | None = None,
        search: str | None = None,
        user: User | None = None,
        favorites_only: bool = False,
    ) -> list[Discovery]:
        statement = select(Discovery).options(
            joinedload(Discovery.category), joinedload(Discovery.source)
        )
        if discovery_date is not None:
            statement = statement.where(Discovery.date == discovery_date)
        if category_name is not None:
            statement = statement.join(Discovery.category).where(
                Category.name == category_name
            )
        elif search:
            statement = statement.join(Discovery.category)
        if search:
            statement = statement.join(Discovery.source, isouter=True)
        if favorites_only:
            if user is None:
                raise ValueError("A user is required for favorite-only searches")
            statement = statement.join(Discovery.interactions).where(
                UserDiscovery.user_id == user.id,
                UserDiscovery.favorite.is_(True),
            )
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    Discovery.title.ilike(pattern),
                    Discovery.content.ilike(pattern),
                    Discovery.description.ilike(pattern),
                    Category.name.ilike(pattern),
                    Source.name.ilike(pattern),
                )
            )
        return list(self.session.scalars(statement.order_by(Discovery.date.desc())).all())

    def used_normalized_titles(self) -> set[str]:
        """Return normalized titles already persisted for duplicate detection."""

        return set(self.session.scalars(select(Discovery.normalized_title)).all())

    def mark_viewed(
        self, user: User, discovery: Discovery, *, favorite: bool | None = None
    ) -> UserDiscovery:
        interaction = self.session.scalar(
            select(UserDiscovery).where(
                UserDiscovery.user_id == user.id,
                UserDiscovery.discovery_id == discovery.id,
            )
        )
        if interaction is None:
            interaction = UserDiscovery(user=user, discovery=discovery)
            self.session.add(interaction)
        interaction.viewed = True
        interaction.viewed_at = datetime.now(timezone.utc)
        if favorite is not None:
            interaction.favorite = favorite
        self.session.flush()
        return interaction

    def get_interaction(self, user: User, discovery: Discovery) -> UserDiscovery | None:
        return self.session.scalar(
            select(UserDiscovery).where(
                UserDiscovery.user_id == user.id,
                UserDiscovery.discovery_id == discovery.id,
            )
        )

    def set_favorite(
        self, user: User, discovery: Discovery, favorite: bool
    ) -> UserDiscovery:
        interaction = self.get_interaction(user, discovery)
        if interaction is None:
            interaction = self.mark_viewed(user, discovery)
        interaction.favorite = favorite
        self.session.flush()
        return interaction

    def add_learning_history(
        self,
        user: User,
        discovery: Discovery,
        interaction_type: str,
        interaction_date: date | None = None,
    ) -> LearningHistory:
        history = LearningHistory(
            user=user,
            discovery=discovery,
            date=interaction_date or date.today(),
            interaction_type=interaction_type,
        )
        self.session.add(history)
        self.session.flush()
        return history

    def add_learning_history_once(
        self,
        user: User,
        discovery: Discovery,
        interaction_type: str,
        interaction_date: date | None = None,
    ) -> LearningHistory:
        learning_date = interaction_date or date.today()
        existing = self.session.scalar(
            select(LearningHistory).where(
                LearningHistory.user_id == user.id,
                LearningHistory.discovery_id == discovery.id,
                LearningHistory.date == learning_date,
                LearningHistory.interaction_type == interaction_type,
            )
        )
        if existing is not None:
            return existing
        return self.add_learning_history(
            user, discovery, interaction_type, learning_date
        )

    def list_favorites(self, user: User) -> list[Discovery]:
        statement = (
            select(Discovery)
            .join(Discovery.interactions)
            .options(joinedload(Discovery.category), joinedload(Discovery.source))
            .where(UserDiscovery.user_id == user.id, UserDiscovery.favorite.is_(True))
            .order_by(Discovery.date.desc())
        )
        return list(self.session.scalars(statement).all())

    def list_learning_history(self, user: User) -> list[LearningHistory]:
        statement = (
            select(LearningHistory)
            .join(LearningHistory.discovery)
            .options(
                joinedload(LearningHistory.discovery).joinedload(Discovery.category),
                joinedload(LearningHistory.discovery).joinedload(Discovery.source),
            )
            .where(LearningHistory.user_id == user.id)
            .order_by(LearningHistory.date.desc(), LearningHistory.id.desc())
        )
        return list(self.session.scalars(statement).all())

    def list_quizzes(self, quiz_date: date) -> list[Quiz]:
        statement = (
            select(Quiz)
            .options(joinedload(Quiz.discovery).joinedload(Discovery.category))
            .where(Quiz.date == quiz_date)
            .order_by(Quiz.id)
        )
        return list(self.session.scalars(statement).all())

    def create_quiz(
        self,
        quiz_date: date,
        discovery: Discovery,
        question: str,
        options: tuple[str, str, str, str],
        correct_answer: str,
        explanation: str,
    ) -> Quiz:
        quiz = Quiz(
            date=quiz_date,
            discovery=discovery,
            question=question,
            option_a=options[0],
            option_b=options[1],
            option_c=options[2],
            option_d=options[3],
            correct_answer=correct_answer,
            explanation=explanation,
        )
        self.session.add(quiz)
        self.session.flush()
        return quiz

    def create_quiz_attempt(
        self,
        user: User,
        attempt_date: date,
        score: int,
        total_questions: int,
    ) -> QuizAttempt:
        attempt = QuizAttempt(
            user=user,
            date=attempt_date,
            score=score,
            total_questions=total_questions,
        )
        self.session.add(attempt)
        self.session.flush()
        return attempt

    def list_quiz_attempts(self, user: User) -> list[QuizAttempt]:
        statement = (
            select(QuizAttempt)
            .where(QuizAttempt.user_id == user.id)
            .order_by(QuizAttempt.date.desc(), QuizAttempt.id.desc())
        )
        return list(self.session.scalars(statement).all())

    def get_spaced_review(self, user: User, discovery: Discovery) -> SpacedReview | None:
        return self.session.scalar(
            select(SpacedReview).where(
                SpacedReview.user_id == user.id,
                SpacedReview.discovery_id == discovery.id,
            )
        )

    def list_due_reviews(self, user: User, review_date: date) -> list[SpacedReview]:
        statement = (
            select(SpacedReview)
            .options(
                joinedload(SpacedReview.discovery).joinedload(Discovery.category),
                joinedload(SpacedReview.discovery).joinedload(Discovery.source),
            )
            .where(
                SpacedReview.user_id == user.id,
                SpacedReview.next_review_date <= review_date,
            )
            .order_by(SpacedReview.next_review_date, SpacedReview.id)
        )
        return list(self.session.scalars(statement).all())

    def list_viewed_discoveries(self, user: User) -> list[Discovery]:
        statement = (
            select(Discovery)
            .join(Discovery.interactions)
            .options(joinedload(Discovery.category), joinedload(Discovery.source))
            .where(UserDiscovery.user_id == user.id, UserDiscovery.viewed.is_(True))
            .order_by(Discovery.date.desc())
        )
        return list(self.session.scalars(statement).all())