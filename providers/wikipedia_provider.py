"""Wikipedia MediaWiki API provider."""

from urllib.parse import quote

from providers.base import ProviderItem, ProviderUnavailable
from providers.http import JsonHttpClient


class WikipediaProvider:
    api_url = "https://en.wikipedia.org/w/api.php"
    source_name = "Wikipedia"

    def __init__(self, client: JsonHttpClient | None = None):
        self.client = client or JsonHttpClient()

    def get_item(self, title: str) -> ProviderItem:
        payload = self.client.get_json(
            self.api_url,
            params={
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "extracts|pageimages",
                "exintro": "1",
                "explaintext": "1",
                "piprop": "thumbnail",
                "pithumbsize": "800",
                "redirects": "1",
                "titles": title,
            },
        )
        query = JsonHttpClient.require_mapping(payload, "Wikipedia")
        query_data = query.get("query")
        if not isinstance(query_data, dict):
            raise ProviderUnavailable("Wikipedia response has no query data")
        pages = JsonHttpClient.require_list(query_data.get("pages"), "Wikipedia")
        page = pages[0] if pages else None
        if not isinstance(page, dict) or page.get("missing") or not page.get("extract"):
            raise ProviderUnavailable(f"Wikipedia page not found: {title}")
        page_title = str(page.get("title", title))
        return ProviderItem(
            title=page_title,
            content=str(page["extract"]),
            source_name=self.source_name,
            source_url=f"https://en.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}",
            image_url=(page.get("thumbnail") or {}).get("source"),
            metadata={"page_id": page.get("pageid")},
        )

    def search(self, query: str, limit: int = 5) -> list[ProviderItem]:
        payload = self.client.get_json(
            self.api_url,
            params={
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
                "srlimit": max(1, min(limit, 50)),
            },
        )
        root = JsonHttpClient.require_mapping(payload, "Wikipedia search")
        query_data = root.get("query")
        if not isinstance(query_data, dict):
            raise ProviderUnavailable("Wikipedia search response has no query data")
        results = JsonHttpClient.require_list(query_data.get("search"), "Wikipedia search")
        items: list[ProviderItem] = []
        for result in results:
            if isinstance(result, dict) and result.get("title"):
                items.append(
                    ProviderItem(
                        title=str(result["title"]),
                        content=str(result.get("snippet", "")).replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                        source_name=self.source_name,
                        source_url=f"https://en.wikipedia.org/wiki/{quote(str(result['title']).replace(' ', '_'))}",
                    )
                )
        return items

    def related_titles(self, title: str, limit: int = 6) -> list[str]:
        """Return linked article titles from a page in the main namespace."""

        payload = self.client.get_json(
            self.api_url,
            params={
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "links",
                "plnamespace": "0",
                "pllimit": max(1, min(limit, 20)),
                "redirects": "1",
                "titles": title,
            },
        )
        root = JsonHttpClient.require_mapping(payload, "Wikipedia links")
        query_data = root.get("query")
        if not isinstance(query_data, dict):
            raise ProviderUnavailable("Wikipedia links response has no query data")
        pages = JsonHttpClient.require_list(query_data.get("pages"), "Wikipedia links")
        page = pages[0] if pages else None
        if not isinstance(page, dict):
            raise ProviderUnavailable(f"Wikipedia page not found: {title}")
        links = page.get("links", [])
        if not isinstance(links, list):
            raise ProviderUnavailable("Wikipedia links response is malformed")
        return [
            str(link["title"])
            for link in links
            if isinstance(link, dict) and link.get("title")
        ][:limit]

    def validate(self, item: ProviderItem) -> bool:
        return bool(item.title.strip() and len(item.content.strip()) >= 20 and item.source_url)