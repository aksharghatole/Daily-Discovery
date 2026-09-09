"""REST Countries provider."""

from urllib.parse import quote

from providers.base import ProviderItem, ProviderUnavailable
from providers.http import JsonHttpClient


class CountryProvider:
    api_url = "https://restcountries.com/v3.1/name"
    source_name = "REST Countries"

    def __init__(self, client: JsonHttpClient | None = None):
        self.client = client or JsonHttpClient()

    def get_item(self, country: str) -> ProviderItem:
        payload = self.client.get_json(
            f"{self.api_url}/{quote(country.strip())}",
            params={"fullText": "true"},
        )
        countries = JsonHttpClient.require_list(payload, "country")
        if not countries or not isinstance(countries[0], dict):
            raise ProviderUnavailable(f"Country not found: {country}")
        return self._to_item(countries[0])

    def search(self, query: str, limit: int = 5) -> list[ProviderItem]:
        payload = self.client.get_json(f"{self.api_url}/{quote(query.strip())}")
        countries = JsonHttpClient.require_list(payload, "country search")
        return [self._to_item(country) for country in countries[: max(1, min(limit, 20))] if isinstance(country, dict)]

    def _to_item(self, country: dict) -> ProviderItem:
        name = country.get("name", {})
        title = str(name.get("common", "")).strip()
        capital = ", ".join(country.get("capital", [])) or "Unknown"
        region = str(country.get("region", "Unknown"))
        population = country.get("population", "Unknown")
        languages = ", ".join(country.get("languages", {}).values()) or "Unknown"
        currencies = ", ".join(
            currency.get("name", code)
            for code, currency in country.get("currencies", {}).items()
            if isinstance(currency, dict)
        ) or "Unknown"
        if not title:
            raise ProviderUnavailable("Country response has no name")
        return ProviderItem(
            title=title,
            content=f"{title} has capital {capital}, is in {region}, and has a population of {population}.",
            source_name=self.source_name,
            source_url=f"{self.api_url}/{quote(title)}",
            subtitle=f"Capital: {capital}",
            description=f"Languages: {languages}. Currency: {currencies}.",
            image_url=(country.get("flags") or {}).get("png"),
            metadata={"population": population, "region": region, "languages": languages, "currencies": currencies},
        )

    def validate(self, item: ProviderItem) -> bool:
        return bool(item.title.strip() and len(item.content.strip()) >= 20 and item.source_url)