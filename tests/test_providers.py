from datetime import date

import pytest
import requests

from providers.astronomy_provider import AstronomyProvider
from providers.base import ProviderUnavailable
from providers.books_provider import BooksProvider
from providers.country_provider import CountryProvider
from providers.dictionary_provider import DictionaryProvider
from providers.http import JsonHttpClient
from providers.wikipedia_provider import WikipediaProvider


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get_json(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def test_wikipedia_provider_maps_summary_and_thumbnail():
    client = FakeClient(
        {
            "query": {
                "pages": [
                    {
                        "pageid": 42,
                        "title": "Blue sky",
                        "extract": "The blue sky is the appearance of Earth's atmosphere.",
                        "thumbnail": {"source": "https://image.test/sky.jpg"},
                    }
                ]
            }
        }
    )

    item = WikipediaProvider(client).get_item("Blue sky")

    assert item.title == "Blue sky"
    assert item.image_url == "https://image.test/sky.jpg"
    assert item.source_url.endswith("Blue_sky")


def test_wikipedia_provider_maps_related_titles():
    payload = {
        "query": {
            "pages": [
                {
                    "title": "Black hole",
                    "links": [
                        {"title": "Event horizon"},
                        {"title": "Hawking radiation"},
                    ],
                }
            ]
        }
    }

    titles = WikipediaProvider(FakeClient(payload)).related_titles("Black hole")

    assert titles == ["Event horizon", "Hawking radiation"]


def test_dictionary_provider_maps_definition_and_metadata():
    payload = [
        {
            "word": "petrichor",
            "phonetics": [{"text": "/ˈpɛtrɪkɔːr/"}],
            "meanings": [
                {
                    "partOfSpeech": "noun",
                    "definitions": [
                        {
                            "definition": "The pleasant smell after rain.",
                            "example": "The petrichor filled the air.",
                        }
                    ],
                }
            ],
        }
    ]

    item = DictionaryProvider(FakeClient(payload)).get_item("petrichor")

    assert item.subtitle == "noun"
    assert item.metadata["pronunciation"] == "/ˈpɛtrɪkɔːr/"
    assert "Example:" in item.description


def test_country_provider_maps_public_country_fields():
    payload = [
        {
            "name": {"common": "New Zealand"},
            "capital": ["Wellington"],
            "region": "Oceania",
            "population": 5000000,
            "languages": {"eng": "English"},
            "currencies": {"NZD": {"name": "New Zealand dollar"}},
            "flags": {"png": "https://image.test/nz.png"},
        }
    ]

    item = CountryProvider(FakeClient(payload)).get_item("New Zealand")

    assert item.title == "New Zealand"
    assert item.subtitle == "Capital: Wellington"
    assert item.image_url == "https://image.test/nz.png"
    assert "English" in item.description


def test_astronomy_provider_rejects_wrong_requested_date():
    client = FakeClient(
        {
            "date": "2026-09-08",
            "title": "Yesterday",
            "explanation": "A sufficiently long explanation for a test item.",
            "url": "https://image.test/yesterday.jpg",
            "media_type": "image",
        }
    )

    with pytest.raises(ProviderUnavailable):
        AstronomyProvider(client, api_key="test").get_item_by_date(date(2026, 9, 9))


def test_books_provider_maps_author_cover_and_source():
    payload = {
        "docs": [
            {
                "key": "/works/OL123W",
                "title": "A Book",
                "author_name": ["A. Writer"],
                "first_publish_year": 2020,
                "cover_i": 123,
                "subject": ["Science", "History"],
            }
        ]
    }

    item = BooksProvider(FakeClient(payload)).get_item("A Book")

    assert item.subtitle == "By A. Writer"
    assert item.image_url.endswith("123-L.jpg")
    assert item.source_url == "https://openlibrary.org/works/OL123W"


def test_http_client_retries_transient_failures():
    class Response:
        status_code = 503

        def raise_for_status(self):
            raise RuntimeError("temporary")

    class Session:
        def __init__(self):
            self.calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            raise requests.ConnectionError("offline")

    session = Session()
    client = JsonHttpClient(session=session, retries=2, retry_delay=0)

    with pytest.raises(ProviderUnavailable):
        client.get_json("https://provider.test")

    assert session.calls == 3


def test_http_client_caches_successful_responses():
    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"value": 1}

    class Session:
        def __init__(self):
            self.calls = 0

        def get(self, url, **kwargs):
            self.calls += 1
            return Response()

    session = Session()
    client = JsonHttpClient(session=session, cache_ttl=60)

    assert client.get_json("https://provider.test", params={"q": "sky"}) == {"value": 1}
    assert client.get_json("https://provider.test", params={"q": "sky"}) == {"value": 1}
    assert session.calls == 1