"""Daily theme and content preference rules."""

from dataclasses import dataclass
from datetime import date

from database.models import User
from services.discovery_service import DiscoveryCandidate


THEME_CATEGORIES = {
    "Science": {"Science", "Space", "Animal"},
    "History": {"History", "Person", "Invention"},
    "Geography": {"Country", "Place"},
    "Technology": {"Science", "Space", "Invention"},
    "Culture": {"Word", "Book", "Place"},
    "Deep Dive": {"Science", "History", "Space"},
    "Completely Random": set(),
}

DEFAULT_CATEGORIES = [
    "Word",
    "Fact",
    "Country",
    "Animal",
    "Science",
    "Space",
    "History",
    "Place",
]


@dataclass(frozen=True)
class PreferenceSnapshot:
    theme: str
    enabled_categories: tuple[str, ...]


class PreferencesService:
    """Keep preference validation and theme selection outside Streamlit."""

    def snapshot(self, user: User) -> PreferenceSnapshot:
        enabled = tuple(user.enabled_categories or DEFAULT_CATEGORIES)
        theme = user.daily_theme or "Completely Random"
        return PreferenceSnapshot(theme=theme, enabled_categories=enabled)

    def set_preferences(
        self,
        user: User,
        *,
        theme: str,
        enabled_categories: list[str],
    ) -> PreferenceSnapshot:
        if theme not in THEME_CATEGORIES:
            raise ValueError(f"Unknown daily theme: {theme}")
        if not enabled_categories:
            raise ValueError("At least one category must remain enabled")
        user.daily_theme = theme
        user.enabled_categories = sorted(set(enabled_categories))
        return self.snapshot(user)

    def categories_for_date(self, user: User, discovery_date: date) -> set[str]:
        snapshot = self.snapshot(user)
        enabled = set(snapshot.enabled_categories)
        themed = THEME_CATEGORIES.get(snapshot.theme, set())
        if not themed:
            return enabled
        # Theme categories are prioritized while enabled categories remain valid.
        themed_enabled = enabled & themed
        return themed_enabled or enabled

    def filter_candidates(
        self,
        user: User,
        discovery_date: date,
        candidates: list[DiscoveryCandidate],
    ) -> list[DiscoveryCandidate]:
        categories = self.categories_for_date(user, discovery_date)
        return [candidate for candidate in candidates if candidate.category in categories]