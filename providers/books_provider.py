"""Open Library books provider."""

from urllib.parse import quote

from providers.base import ProviderItem, ProviderUnavailable
from providers.http import JsonHttpClient


class BooksProvider:
    api_url = "https://openlibrary.org/search.json"
    source_name = "Open Library"

    def __init__(self, client: JsonHttpClient | None = None):
        self.client = client or JsonHttpClient()

    def get_item(self, query: str) -> ProviderItem:
        items = self.search(query, limit=1)
        if not items:
            raise ProviderUnavailable(f"Book not found: {query}")
        return items[0]

    def search(self, query: str, limit: int = 5) -> list[ProviderItem]:
        payload = self.client.get_json(
            self.api_url,
            params={"q": query, "limit": max(1, min(limit, 20)), "fields": "key,title,author_name,first_publish_year,cover_i,subject"},
        )
        root = JsonHttpClient.require_mapping(payload, "book search")
        docs = JsonHttpClient.require_list(root.get("docs"), "book search")
        return [self._to_item(doc) for doc in docs if isinstance(doc, dict) and doc.get("title")]

    def _to_item(self, book: dict) -> ProviderItem:
        title = str(book["title"]).strip()
        key = str(book.get("key", ""))
        source_url = f"https://openlibrary.org{key}" if key.startswith("/") else f"https://openlibrary.org/search?q={quote(title)}"
        authors = ", ".join(book.get("author_name", [])) or "Unknown author"
        year = book.get("first_publish_year", "Unknown year")
        subjects = ", ".join(book.get("subject", [])[:3]) if book.get("subject") else None
        return ProviderItem(
            title=title,
            content=f"{title} was first published in {year}. The listed author is {authors}.",
            source_name=self.source_name,
            source_url=source_url,
            subtitle=f"By {authors}",
            description=f"Subjects: {subjects}" if subjects else None,
            image_url=(f"https://covers.openlibrary.org/b/id/{book['cover_i']}-L.jpg" if book.get("cover_i") else None),
            metadata={"authors": book.get("author_name", []), "first_publish_year": year, "key": key},
        )

    def validate(self, item: ProviderItem) -> bool:
        return bool(item.title.strip() and len(item.content.strip()) >= 20 and item.source_url)