"""Gitgoblin client — contract only. Implementation stays independent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class GitgoblinSignal:
    signal_id: str
    kind: str
    observed_at: str
    payload: dict[str, Any]
    evidence_refs: tuple[str, ...] = ()


class GitgoblinClient(Protocol):
    def emerging_capabilities(self, *, since: str | None = None, limit: int = 100) -> list[GitgoblinSignal]: ...
    def people_signals(self, *, since: str | None = None, limit: int = 100) -> list[GitgoblinSignal]: ...
    def repo_signals(self, *, since: str | None = None, limit: int = 100) -> list[GitgoblinSignal]: ...
