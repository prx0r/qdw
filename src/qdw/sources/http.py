"""HTTP JSON fetcher — shared by all source adapters."""

from __future__ import annotations

from typing import Any

import httpx


class JSONFetcher:
    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=20.0, follow_redirects=True)

    def get(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        r = self.client.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()
