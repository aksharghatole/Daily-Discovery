"""Shared contracts for external discovery providers."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol


class ProviderError(RuntimeError):
    """Base error for expected provider failures."""


class ProviderUnavailable(ProviderError):
    """Raised when a provider cannot be reached or returns a bad response."""


@dataclass(frozen=True)
class ProviderItem:
    """Provider-neutral content that can be adapted into a discovery."""

    title: str
    content: str
    source_name: str
    source_url: str
    subtitle: str | None = None
    description: str | None = None
    image_url: str | None = None
    source_date: date | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ContentProvider(Protocol):
    """Interface implemented by content providers."""

    def get_item(self, query: str) -> ProviderItem:
        """Return one item for a query or raise ProviderError."""

    def search(self, query: str, limit: int = 5) -> list[ProviderItem]:
        """Return up to limit matching items."""

    def validate(self, item: ProviderItem) -> bool:
        """Check that an item contains usable, source-backed content."""