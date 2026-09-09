from datetime import date

import pytest

from database.models import User
from services.discovery_service import DiscoveryCandidate
from services.preferences_service import PreferencesService


def test_preferences_filter_theme_categories():
    user = User(
        daily_theme="Science",
        enabled_categories=["Science", "History", "Space"],
    )
    candidates = [
        DiscoveryCandidate("Science", "Sky", "A sufficiently long science entry.", "NASA", "https://nasa.gov"),
        DiscoveryCandidate("History", "Rome", "A sufficiently long history entry.", "Museum", "https://museum.test"),
        DiscoveryCandidate("Space", "Stars", "A sufficiently long space entry.", "NASA", "https://nasa.gov/stars"),
    ]

    filtered = PreferencesService().filter_candidates(user, date(2026, 9, 9), candidates)

    assert {candidate.category for candidate in filtered} == {"Science", "Space"}


def test_preferences_reject_empty_categories():
    user = User()

    with pytest.raises(ValueError):
        PreferencesService().set_preferences(
            user, theme="Completely Random", enabled_categories=[]
        )