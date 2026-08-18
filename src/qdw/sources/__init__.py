"""Source adapters — typed failure semantics.

Key invariant: SOURCE FAILURE != ZERO RESULTS.

A failed source returns SearchResult(ok=False, ...) or raises SourceUnavailable.
An empty result set returns SearchResult(ok=True, items=[]).
These must never be conlated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class SourceUnavailable(Exception):
    """Raised when a source cannot be reached."""


@dataclass(frozen=True)
class SearchResult:
    ok: bool
    items: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    source: str = ""

    def __bool__(self) -> bool:
        return self.ok
