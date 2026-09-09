"""Dictionary API provider."""

from urllib.parse import quote

from providers.base import ProviderItem, ProviderUnavailable
from providers.http import JsonHttpClient


class DictionaryProvider:
    api_url = "https://api.dictionaryapi.dev/api/v2/entries/en"
    source_name = "Dictionary API"

    def __init__(self, client: JsonHttpClient | None = None):
        self.client = client or JsonHttpClient()

    def get_item(self, word: str) -> ProviderItem:
        payload = self.client.get_json(f"{self.api_url}/{quote(word.strip())}")
        entries = JsonHttpClient.require_list(payload, "dictionary")
        if not entries or not isinstance(entries[0], dict):
            raise ProviderUnavailable(f"Word not found: {word}")
        entry = entries[0]
        meanings = entry.get("meanings", [])
        meaning = meanings[0] if meanings and isinstance(meanings[0], dict) else {}
        definitions = meaning.get("definitions", [])
        definition = definitions[0] if definitions and isinstance(definitions[0], dict) else {}
        content = str(definition.get("definition", "")).strip()
        if not content:
            raise ProviderUnavailable(f"Definition missing for: {word}")
        example = definition.get("example")
        description = f"Example: {example}" if example else None
        phonetics = entry.get("phonetics", [])
        pronunciation = next(
            (phonetic.get("text") for phonetic in phonetics if isinstance(phonetic, dict) and phonetic.get("text")),
            None,
        )
        return ProviderItem(
            title=str(entry.get("word", word)),
            content=content,
            source_name=self.source_name,
            source_url=f"{self.api_url}/{quote(word.strip())}",
            subtitle=meaning.get("partOfSpeech"),
            description=description,
            metadata={"pronunciation": pronunciation, "origin": entry.get("origin")},
        )

    def search(self, query: str, limit: int = 5) -> list[ProviderItem]:
        return [self.get_item(query)] if query.strip() else []

    def validate(self, item: ProviderItem) -> bool:
        return bool(item.title.strip() and item.content.strip() and item.source_url)