"""Hacker News source adapter."""

from __future__ import annotations

from qdw.core import utc_now
from qdw.sources.http import JSONFetcher
from qdw.sources.protocol import SourceResult


class HackerNewsSource:
    source_id = "hackernews"
    source_family = "forum"
    BASE = "https://hacker-news.firebaseio.com/v0"

    def __init__(self, fetcher: JSONFetcher | None = None):
        self.fetcher = fetcher or JSONFetcher()

    def ask(self, limit: int = 30) -> SourceResult:
        try:
            ids = self.fetcher.get(f"{self.BASE}/askstories.json")[:limit]
            items = []
            for iid in ids:
                x = self.fetcher.get(f"{self.BASE}/item/{iid}.json") or {}
                items.append({
                    "id": x.get("id"), "title": x.get("title", ""), "text": x.get("text", ""),
                    "author": x.get("by"), "score": x.get("score"), "descendants": x.get("descendants"),
                    "published_at": x.get("time"),
                    "url": f"https://news.ycombinator.com/item?id={iid}",
                })
            return SourceResult.success(self.source_id, self.source_family, items, utc_now())
        except Exception as e:
            return SourceResult.failure(self.source_id, self.source_family, f"{type(e).__name__}:{e}", utc_now())
