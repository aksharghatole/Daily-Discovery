from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import Base, create_engine_from_settings
from database.models import Discovery, Source
from services.discovery_service import (
    DailyDiscoveryService,
    DiscoveryCandidate,
    GenerationError,
)


def _engine(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)
    return engine


def _candidates():
    return [
        DiscoveryCandidate(
            "Science",
            "Blue sky",
            "Atmospheric molecules scatter short blue wavelengths more strongly.",
            "NASA",
            "https://spaceplace.nasa.gov/blue-sky/en/",
        ),
        DiscoveryCandidate(
            "Science",
            "Water cycle",
            "Water moves through evaporation, condensation, and precipitation.",
            "USGS",
            "https://www.usgs.gov/special-topics/water-science-school/science/water-cycle",
        ),
        DiscoveryCandidate(
            "History",
            "Moon landing",
            "Apollo 11 landed on the Moon and its crew walked on the surface.",
            "NASA",
            "https://www.nasa.gov/mission/apollo-11/",
        ),
        DiscoveryCandidate(
            "History",
            "Rosetta Stone",
            "The stone helped scholars decipher Egyptian hieroglyphs.",
            "British Museum",
            "https://www.britishmuseum.org/collection/object/Y_EA24",
        ),
    ]


def test_generation_is_idempotent_and_avoids_previous_titles(monkeypatch):
    engine = _engine(monkeypatch)

    with Session(engine) as session:
        service = DailyDiscoveryService(session, _candidates())
        first = service.generate(date(2026, 9, 9))
        repeated = service.generate(date(2026, 9, 9))
        second_day = service.generate(date(2026, 9, 10))

        assert len(first) == 2
        assert [item.id for item in repeated] == [item.id for item in first]
        assert {item.title for item in first}.isdisjoint(
            {item.title for item in second_day}
        )
        assert session.scalars(select(Source)).all()
        assert len(session.scalars(select(Discovery)).all()) == 4


def test_invalid_candidate_fails_before_writing(monkeypatch):
    engine = _engine(monkeypatch)
    invalid = DiscoveryCandidate(
        "Science", "Too short", "No", "Example", "not-a-url"
    )

    with Session(engine) as session:
        service = DailyDiscoveryService(session, [invalid])

        with pytest.raises(GenerationError):
            service.generate(date(2026, 9, 9))

        assert session.scalars(select(Discovery)).all() == []