"""SQLAlchemy engine and session setup.

The database URL is intentionally configured outside the UI so the same
business layer can later be used by another frontend or a worker process.
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import get_settings


class Base(DeclarativeBase):
    """Base class for Phase 2 ORM models."""


def _sqlite_connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _ensure_sqlite_directory(database_url: str) -> None:
    if not database_url.startswith("sqlite:///") or database_url == "sqlite:///:memory:":
        return
    database_path = database_url.removeprefix("sqlite:///")
    if database_path.startswith("./"):
        database_path = database_path[2:]
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)


def create_engine_from_settings():
    """Create an engine from current environment settings."""

    database_url = get_settings().database_url
    _ensure_sqlite_directory(database_url)
    return create_engine(
        database_url,
        connect_args=_sqlite_connect_args(database_url),
        future=True,
    )


engine = create_engine_from_settings()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and always close it."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def initialize_database() -> None:
    """Create registered tables once models are added in Phase 2."""

    from database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        _upgrade_sqlite_preferences()


def _upgrade_sqlite_preferences() -> None:
    """Add small, backwards-compatible columns to an existing local database."""

    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    statements = []
    if "enabled_categories" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN enabled_categories JSON NOT NULL DEFAULT '[]'"
        )
    if "daily_theme" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN daily_theme VARCHAR(40) NOT NULL DEFAULT 'Completely Random'"
        )
    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))