"""NASA Astronomy Picture of the Day provider."""

from datetime import date
import os

from providers.base import ProviderItem, ProviderUnavailable
from providers.http import JsonHttpClient


class AstronomyProvider:
    api_url = "https://api.nasa.gov/planetary/apod"
    source_name = "NASA Astronomy Picture of the Day"

    def __init__(self, client: JsonHttpClient | None = None, api_key: str | None = None):
        self.client = client or JsonHttpClient()
        self.api_key = api_key or os.getenv("NASA_API_KEY", "DEMO_KEY")

    def get_item(self, query: str = "") -> ProviderItem:
        return self.get_item_by_date(date.today())

    def get_item_by_date(self, requested_date: date) -> ProviderItem:
        payload = self.client.get_json(
            self.api_url,
            params={"api_key": self.api_key, "date": requested_date.isoformat()},
        )
        if not isinstance(payload, dict) or payload.get("date") != requested_date.isoformat():
            raise ProviderUnavailable("NASA returned an unexpected APOD date")
        title = str(payload.get("title", "")).strip()
        explanation = str(payload.get("explanation", "")).strip()
        source_url = str(payload.get("url", "")).strip()
        if not title or not explanation or not source_url:
            raise ProviderUnavailable("NASA APOD response is incomplete")
        return ProviderItem(
            title=title,
            content=explanation,
            source_name=self.source_name,
            source_url=source_url,
            image_url=payload.get("hdurl") or source_url if payload.get("media_type") == "image" else None,
            source_date=requested_date,
            metadata={"media_type": payload.get("media_type"), "copyright": payload.get("copyright")},
        )

    def search(self, query: str, limit: int = 5) -> list[ProviderItem]:
        return [self.get_item()] if not query.strip() else []

    def validate(self, item: ProviderItem) -> bool:
        return bool(item.title.strip() and len(item.content.strip()) >= 20 and item.source_url)