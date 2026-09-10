"""Initial schema

Revision ID: 20260910_initial_schema
Revises: 
Create Date: 2026-09-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260910_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("daily_notification_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("preferred_categories", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("enabled_categories", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("daily_theme", sa.String(length=40), nullable=False, server_default="Completely Random"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("source_date", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "discoveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("normalized_title", sa.String(length=300), nullable=False),
        sa.Column("subtitle", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", "category_id", "title", name="uq_discovery_day_category_title"),
    )
    op.create_index(op.f("ix_discoveries_date"), "discoveries", ["date"], unique=False)
    op.create_index(op.f("ix_discoveries_title"), "discoveries", ["title"], unique=False)
    op.create_index("ix_discoveries_date_category", "discoveries", ["date", "category_id"], unique=False)
    op.create_table(
        "user_discoveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("discovery_id", sa.Integer(), nullable=False),
        sa.Column("viewed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["discovery_id"], ["discoveries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "discovery_id", name="uq_user_discovery"),
    )
    op.create_index("ix_user_discoveries_user_id", "user_discoveries", ["user_id"], unique=False)
    op.create_table(
        "user_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_progress_user"),
    )
    op.create_index(op.f("ix_user_progress_user_id"), "user_progress", ["user_id"], unique=False)
    op.create_table(
        "quizzes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("option_a", sa.String(length=500), nullable=False),
        sa.Column("option_b", sa.String(length=500), nullable=False),
        sa.Column("option_c", sa.String(length=500), nullable=False),
        sa.Column("option_d", sa.String(length=500), nullable=False),
        sa.Column("correct_answer", sa.String(length=1), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("discovery_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["discovery_id"], ["discoveries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quizzes_date"), "quizzes", ["date"], unique=False)
    op.create_index(op.f("ix_quizzes_discovery_id"), "quizzes", ["discovery_id"], unique=False)
    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("total_questions", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quiz_attempts_user_date", "quiz_attempts", ["user_id", "date"], unique=False)
    op.create_table(
        "learning_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("discovery_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("interaction_type", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["discovery_id"], ["discoveries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_history_user_date", "learning_history", ["user_id", "date"], unique=False)
    op.create_table(
        "spaced_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("discovery_id", sa.Integer(), nullable=False),
        sa.Column("last_seen", sa.Date(), nullable=False),
        sa.Column("times_correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("times_incorrect", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("next_review_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["discovery_id"], ["discoveries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "discovery_id", name="uq_spaced_review"),
    )
    op.create_index("ix_spaced_reviews_due", "spaced_reviews", ["user_id", "next_review_date"], unique=False)
    op.create_index(op.f("ix_spaced_reviews_next_review_date"), "spaced_reviews", ["next_review_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_spaced_reviews_next_review_date"), table_name="spaced_reviews")
    op.drop_index("ix_spaced_reviews_due", table_name="spaced_reviews")
    op.drop_table("spaced_reviews")
    op.drop_index("ix_learning_history_user_date", table_name="learning_history")
    op.drop_table("learning_history")
    op.drop_index("ix_quiz_attempts_user_date", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")
    op.drop_index(op.f("ix_quizzes_discovery_id"), table_name="quizzes")
    op.drop_index(op.f("ix_quizzes_date"), table_name="quizzes")
    op.drop_table("quizzes")
    op.drop_index(op.f("ix_user_progress_user_id"), table_name="user_progress")
    op.drop_table("user_progress")
    op.drop_index("ix_user_discoveries_user_id", table_name="user_discoveries")
    op.drop_table("user_discoveries")
    op.drop_index("ix_discoveries_date_category", table_name="discoveries")
    op.drop_index(op.f("ix_discoveries_title"), table_name="discoveries")
    op.drop_index(op.f("ix_discoveries_date"), table_name="discoveries")
    op.drop_table("discoveries")
    op.drop_table("sources")
    op.drop_table("categories")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
