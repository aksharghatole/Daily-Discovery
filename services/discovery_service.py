"""Daily Discovery generation using validated, source-backed candidates."""

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re
from typing import Iterable

from sqlalchemy.orm import Session

from database.models import Discovery
from database.repository import Repository


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "data" / "seed_data.json"


class GenerationError(RuntimeError):
    """Raised when a daily collection cannot be generated safely."""


@dataclass(frozen=True)
class DiscoveryCandidate:
    category: str
    title: str
    content: str
    source_name: str
    source_url: str
    subtitle: str | None = None
    description: str | None = None
    image_url: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "DiscoveryCandidate":
        required = ("category", "title", "content", "source_name", "source_url")
        missing = [field for field in required if not str(value.get(field, "")).strip()]
        if missing:
            raise ValueError(f"Candidate is missing required fields: {', '.join(missing)}")
        return cls(
            category=str(value["category"]).strip(),
            title=str(value["title"]).strip(),
            content=str(value["content"]).strip(),
            source_name=str(value["source_name"]).strip(),
            source_url=str(value["source_url"]).strip(),
            subtitle=_optional_text(value.get("subtitle")),
            description=_optional_text(value.get("description")),
            image_url=_optional_text(value.get("image_url")),
        )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_title(title: str) -> str:
    """Normalize punctuation and whitespace for stable duplicate detection."""

    return re.sub(r"[^a-z0-9 ]", "", title.casefold()).strip()


def load_local_catalog(path: Path = CATALOG_PATH) -> list[DiscoveryCandidate]:
    """Load the checked-in offline catalog without contacting external services."""

    with path.open(encoding="utf-8") as file:
        values = json.load(file)
    if not isinstance(values, list):
        raise GenerationError("The local discovery catalog must contain a list")
    return [DiscoveryCandidate.from_dict(value) for value in values]


class DailyDiscoveryService:
    """Generate one idempotent, source-backed collection for a calendar date."""

    def __init__(self, session: Session, candidates: Iterable[DiscoveryCandidate] | None = None):
        self.repository = Repository(session)
        self.candidates = list(candidates) if candidates is not None else load_local_catalog()

    def generate(self, discovery_date: date) -> list[Discovery]:
        self._validate_catalog()
        existing = self.repository.list_discoveries(discovery_date=discovery_date)
        by_category = {discovery.category.name: discovery for discovery in existing}
        categories = sorted({candidate.category for candidate in self.candidates})
        used_titles = self.repository.used_normalized_titles()
        generated: list[Discovery] = list(existing)

        try:
            for category_name in categories:
                if category_name in by_category:
                    continue
                candidate = self._select_candidate(
                    category_name, discovery_date, used_titles
                )
                category = self.repository.get_or_create_category(category_name)
                source = self.repository.create_source(
                    candidate.source_name, candidate.source_url
                )
                discovery = self.repository.create_discovery(
                    discovery_date,
                    category,
                    candidate.title,
                    candidate.content,
                    normalized_title=normalize_title(candidate.title),
                    subtitle=candidate.subtitle,
                    description=candidate.description,
                    image_url=candidate.image_url,
                    source=source,
                )
                generated.append(discovery)
                used_titles.add(normalize_title(candidate.title))
            self.repository.session.commit()
        except Exception:
            self.repository.session.rollback()
            raise

        committed = self.repository.list_discoveries(discovery_date=discovery_date)
        return sorted(committed, key=lambda discovery: discovery.category.name)

    def _validate_catalog(self) -> None:
        if not self.candidates:
            raise GenerationError("No discovery candidates are available")
        for candidate in self.candidates:
            if len(candidate.content) < 20:
                raise GenerationError(
                    f"Candidate content is too short: {candidate.title}"
                )
            if not candidate.source_url.startswith(("http://", "https://")):
                raise GenerationError(f"Candidate source URL is invalid: {candidate.title}")

    def _select_candidate(
        self,
        category_name: str,
        discovery_date: date,
        used_titles: set[str],
    ) -> DiscoveryCandidate:
        choices = [
            candidate
            for candidate in self.candidates
            if candidate.category == category_name
        ]
        start = discovery_date.toordinal() % len(choices)
        for offset in range(len(choices)):
            candidate = choices[(start + offset) % len(choices)]
            if normalize_title(candidate.title) not in used_titles:
                return candidate
        raise GenerationError(f"No unused candidate remains for category: {category_name}")