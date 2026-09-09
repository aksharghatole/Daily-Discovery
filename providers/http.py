"""Small retrying JSON client shared by external providers."""

from collections.abc import Mapping
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
    ):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay

    def get_json(self, url: str, **kwargs: Any) -> Any:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout, **kwargs)
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                response.raise_for_status()
                return response.json()
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