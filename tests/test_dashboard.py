from datetime import date

from sqlalchemy.orm import Session

from database.db import Base, create_engine_from_settings
from ui.dashboard import get_daily_discoveries


def test_dashboard_helper_returns_source_backed_collection(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        discoveries = get_daily_discoveries(session, date(2026, 9, 9))

    assert len(discoveries) == 8
    assert all(discovery.source is not None for discovery in discoveries)
    assert all(discovery.category.name for discovery in discoveries)