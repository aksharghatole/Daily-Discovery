"""SQLAlchemy engine and session setup.

The database URL is intentionally configured outside the UI so the same
business layer can later be used by another frontend or a worker process.
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import get_settings


if "Base" not in globals():

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


def create_session_local() -> sessionmaker:
    """Create a fresh SQLAlchemy session factory using the active settings."""
    return sessionmaker(
        bind=create_engine_from_settings(),
        autoflush=False,
        autocommit=False,
    )


def initialize_database() -> None:
    """Create registered tables once models are added in Phase 2."""

    import database.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        _upgrade_sqlite_preferences()
        _upgrade_sqlite_sources()


def _upgrade_sqlite_preferences() -> None:
    """Add backwards-compatible columns to an existing local database."""

    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    statements = []
    if "email" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN email VARCHAR(255) NULL"
        )
    if "password_hash" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL"
        )
    if "display_name" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN display_name VARCHAR(120) NULL"
        )
    if "updated_at" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN updated_at DATETIME")
    if "last_login_at" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN last_login_at DATETIME NULL"
        )
    if "is_active" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
        )
    if "is_admin" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"
        )
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

    # Normalize legacy users to a safe local account without overwriting existing values.
    with engine.begin() as connection:
        stored_email = connection.execute(
            text("SELECT COUNT(*) FROM users WHERE email IS NOT NULL AND email != ''")
        ).scalar_one()
        if stored_email == 0:
            connection.execute(
                text("UPDATE users SET email = 'local@daily-discovery.local', display_name = 'Local User', is_active = 1 WHERE email IS NULL OR email = ''")
            )
        connection.execute(
            text("UPDATE users SET updated_at = COALESCE(updated_at, CURRENT_TIMESTAMP)")
        )
        connection.execute(
            text("UPDATE users SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP) WHERE created_at IS NULL")
        )
        connection.execute(
            text("UPDATE users SET timezone = COALESCE(timezone, 'UTC') WHERE timezone IS NULL")
        )
        connection.execute(
            text("UPDATE users SET preferred_categories = COALESCE(preferred_categories, '[]') WHERE preferred_categories IS NULL")
        )
        connection.execute(
            text("UPDATE users SET enabled_categories = COALESCE(enabled_categories, '[]') WHERE enabled_categories IS NULL")
        )
        connection.execute(
            text("UPDATE users SET daily_theme = COALESCE(daily_theme, 'Completely Random') WHERE daily_theme IS NULL OR daily_theme = ''")
        )


def _upgrade_sqlite_sources() -> None:
    """Add Phase 4 source identifiers to an existing local database."""

    columns = {column["name"] for column in inspect(engine).get_columns("sources")}
    if "source_identifier" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE sources ADD COLUMN source_identifier VARCHAR(255) NULL")
            )


initialize_database()


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and always close it."""

    session_factory = create_session_local()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
