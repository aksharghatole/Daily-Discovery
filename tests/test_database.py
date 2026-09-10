from datetime import date

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from config.settings import get_settings
from database.db import Base, create_engine_from_settings, initialize_database
from database.models import Discovery, User
from database.repository import Repository


def test_database_engine_can_create_tables(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()

    Base.metadata.create_all(engine)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1


def test_phase_two_schema_has_expected_tables_and_indexes(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "users",
        "categories",
        "sources",
        "discoveries",
        "user_discoveries",
        "quizzes",
        "quiz_attempts",
        "learning_history",
    } <= tables
    assert any(
        index["name"] == "ix_discoveries_title"
        for index in inspector.get_indexes("discoveries")
    )


def test_initialize_database_registers_phase_two_models(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    initialize_database()

    assert "discoveries" in Base.metadata.tables


def test_repository_persists_discovery_and_user_interaction(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(session)
        user = repository.create_user(preferred_categories=["Science"])
        category = repository.get_or_create_category("Science")
        source = repository.create_source("Example Source", "https://example.test")
        discovery = repository.create_discovery(
            date(2026, 9, 9),
            category,
            "A test discovery",
            "A verified test entry.",
            source=source,
        )
        interaction = repository.mark_viewed(user, discovery, favorite=True)
        session.commit()

        assert session.get(User, user.id).preferred_categories == ["Science"]
        assert session.get(Discovery, discovery.id).source.name == "Example Source"
        assert interaction.viewed is True
        assert repository.list_favorites(user)[0].title == "A test discovery"


def test_repository_filters_discoveries(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(session)
        science = repository.get_or_create_category("Science")
        history = repository.get_or_create_category("History")
        repository.create_discovery(
            date(2026, 9, 9), science, "Blue sky", "A science entry."
        )
        repository.create_discovery(
            date(2026, 9, 8), history, "Ancient Rome", "A history entry."
        )
        session.commit()

        results = repository.list_discoveries(category_name="Science", search="sky")

        assert [discovery.title for discovery in results] == ["Blue sky"]


def test_repository_persists_favorite_and_deduplicates_daily_history(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(session)
        user = repository.get_or_create_local_user()
        category = repository.get_or_create_category("Science")
        discovery = repository.create_discovery(
            date(2026, 9, 9),
            category,
            "Blue sky",
            "Atmospheric scattering explains the blue color of the sky.",
        )
        repository.set_favorite(user, discovery, True)
        repository.add_learning_history_once(user, discovery, "viewed", date(2026, 9, 9))
        repository.add_learning_history_once(user, discovery, "viewed", date(2026, 9, 9))
        session.commit()

        assert repository.list_favorites(user)[0].title == "Blue sky"
        assert len(repository.list_learning_history(user)) == 1


def test_repository_search_matches_category_and_content(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        repository = Repository(session)
        category = repository.get_or_create_category("Geography")
        repository.create_discovery(
            date(2026, 9, 9),
            category,
            "Island study",
            "A coastal place shaped by ocean currents.",
        )
        session.commit()

        assert len(repository.list_discoveries(search="ocean")) == 1
        assert len(repository.list_discoveries(search="geography")) == 1


def test_database_url_supports_sqlite_and_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./data/test.db")
    settings = get_settings()
    assert settings.database_url.startswith("sqlite")

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5432/daily_discovery",
    )
    settings = get_settings()
    assert settings.database_url.startswith("postgresql+psycopg")
