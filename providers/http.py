"""Small retrying JSON client shared by external providers."""

from collections.abc import Mapping
import copy
import hashlib
import json
import time
from typing import Any

import requests

from providers.base import ProviderUnavailable


class JsonHttpClient:
    """HTTP client with bounded timeouts and retries for transient failures."""

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout: float = 8.0,
        retries: int = 2,
        retry_delay: float = 0.1,
        cache_ttl: float = 300.0,
    ):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[float, Any]] = {}

    def get_json(self, url: str, **kwargs: Any) -> Any:
        raw_cache_key = f"{url}?{json.dumps(kwargs, sort_keys=True, default=str)}"
        cache_key = hashlib.sha256(raw_cache_key.encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl:
            return copy.deepcopy(cached[1])

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                response.raise_for_status()
                payload = response.json()
                self._cache[cache_key] = (time.monotonic(), copy.deepcopy(payload))
                return payload
            except (requests.RequestException, ValueError) as error:
                last_error = error
                retryable = isinstance(error, requests.RequestException) and (
                    not hasattr(error, "response")
                    or error.response is None
                    or error.response.status_code == 429
                    or error.response.status_code >= 500
                )
                if retryable and attempt < self.retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                elif not retryable:
                    break
        raise ProviderUnavailable(f"Could not fetch provider response: {url}") from last_error

    @staticmethod
    def require_mapping(payload: Any, context: str) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise ProviderUnavailable(f"Provider returned invalid {context} data")
        return payload

    @staticmethod
    def require_list(payload: Any, context: str) -> list[Any]:
        if not isinstance(payload, list):
            raise ProviderUnavailable(f"Provider returned invalid {context} data")
        return payload