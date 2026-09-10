"""Add daily generation status and source identifiers.

Revision ID: 20260910_generation_runs
Revises: 20260910_initial_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "20260910_generation_runs"
down_revision = "20260910_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("source_identifier", sa.String(length=255), nullable=True))
    op.create_table(
        "generation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("date", name="uq_generation_runs_date"),
    )
    op.create_index(op.f("ix_generation_runs_date"), "generation_runs", ["date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_generation_runs_date"), table_name="generation_runs")
    op.drop_table("generation_runs")
    op.drop_column("sources", "source_identifier")