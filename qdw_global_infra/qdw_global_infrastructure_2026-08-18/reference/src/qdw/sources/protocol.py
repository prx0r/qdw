from __future__ import annotations
from dataclasses import dataclass
from typing import Any

class SourceError(RuntimeError):
    pass

@dataclass(frozen=True)
class SourceResult:
    ok: bool
    source_id: str
    source_family: str
    items: tuple[dict[str, Any], ...] = ()
    error: str | None = None
    observed_at: str | None = None
    context: dict[str, Any] | None = None

    @classmethod
    def success(cls, source_id: str, source_family: str, items: list[dict[str, Any]],
                observed_at: str | None=None, context: dict[str, Any] | None=None):
        return cls(True, source_id, source_family, tuple(items), None, observed_at, context or {})

    @classmethod
    def failure(cls, source_id: str, source_family: str, error: str,
                observed_at: str | None=None, context: dict[str, Any] | None=None):
        return cls(False, source_id, source_family, (), error, observed_at, context or {})
