"""SQLAlchemy models for the Daily Discovery persistence layer."""

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    daily_notification_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    preferred_categories: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    enabled_categories: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    daily_theme: Mapped[str] = mapped_column(
        String(40), default="Completely Random", nullable=False
    )

    interactions: Mapped[list["UserDiscovery"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    quiz_attempts: Mapped[list["QuizAttempt"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    learning_history: Mapped[list["LearningHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    progress: Mapped["UserProgress | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    spaced_reviews: Mapped[list["SpacedReview"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("ix_user_sessions_user_expires", "user_id", "expires_at"),
        UniqueConstraint("user_id", "refresh_token_hash", name="uq_user_refresh_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class UserProgress(Base):
    __tablename__ = "user_progress"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_progress_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_active_date: Mapped[date | None] = mapped_column(Date)

    user: Mapped[User] = relationship(back_populates="progress")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    discoveries: Mapped[list["Discovery"]] = relationship(back_populates="category")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    url: Mapped[str] = mapped_column(String(2_048), nullable=False)
    source_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    discoveries: Mapped[list["Discovery"]] = relationship(back_populates="source")


class Discovery(Base):
    __tablename__ = "discoveries"
    __table_args__ = (
        Index("ix_discoveries_date_category", "date", "category_id"),
        Index("ix_discoveries_title", "title"),
        UniqueConstraint(
            "date", "category_id", "title", name="uq_discovery_day_category_title"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(300), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(2_048))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    category: Mapped[Category] = relationship(back_populates="discoveries")
    source: Mapped[Source | None] = relationship(back_populates="discoveries")
    interactions: Mapped[list["UserDiscovery"]] = relationship(
        back_populates="discovery", cascade="all, delete-orphan"
    )
    quiz_questions: Mapped[list["Quiz"]] = relationship(
        back_populates="discovery", cascade="all, delete-orphan"
    )
    learning_history: Mapped[list["LearningHistory"]] = relationship(
        back_populates="discovery", cascade="all, delete-orphan"
    )
    spaced_reviews: Mapped[list["SpacedReview"]] = relationship(
        back_populates="discovery", cascade="all, delete-orphan"
    )


class UserDiscovery(Base):
    __tablename__ = "user_discoveries"
    __table_args__ = (
        UniqueConstraint("user_id", "discovery_id", name="uq_user_discovery"),
        Index("ix_user_discoveries_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    discovery_id: Mapped[int] = mapped_column(
        ForeignKey("discoveries.id", ondelete="CASCADE"), nullable=False
    )
    viewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rating: Mapped[float | None] = mapped_column(Float)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="interactions")
    discovery: Mapped[Discovery] = relationship(back_populates="interactions")


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    option_a: Mapped[str] = mapped_column(String(500), nullable=False)
    option_b: Mapped[str] = mapped_column(String(500), nullable=False)
    option_c: Mapped[str] = mapped_column(String(500), nullable=False)
    option_d: Mapped[str] = mapped_column(String(500), nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(1), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    discovery_id: Mapped[int] = mapped_column(
        ForeignKey("discoveries.id", ondelete="CASCADE"), nullable=False, index=True
    )

    discovery: Mapped[Discovery] = relationship(back_populates="quiz_questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (Index("ix_quiz_attempts_user_date", "user_id", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="quiz_attempts")


class LearningHistory(Base):
    __tablename__ = "learning_history"
    __table_args__ = (Index("ix_learning_history_user_date", "user_id", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    discovery_id: Mapped[int] = mapped_column(
        ForeignKey("discoveries.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(40), nullable=False)

    user: Mapped[User] = relationship(back_populates="learning_history")
    discovery: Mapped[Discovery] = relationship(back_populates="learning_history")


class SpacedReview(Base):
    __tablename__ = "spaced_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "discovery_id", name="uq_spaced_review"),
        Index("ix_spaced_reviews_due", "user_id", "next_review_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    discovery_id: Mapped[int] = mapped_column(
        ForeignKey("discoveries.id", ondelete="CASCADE"), nullable=False
    )
    last_seen: Mapped[date] = mapped_column(Date, nullable=False)
    times_correct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    times_incorrect: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    next_review_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    user: Mapped[User] = relationship(back_populates="spaced_reviews")
    discovery: Mapped[Discovery] = relationship(back_populates="spaced_reviews")