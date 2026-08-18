"""Executor protocol — typed request/result, no self-certification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ExecutionRequest:
    run_id: str
    node_id: str
    task_kind: str
    prompt: str
    payload: dict[str, Any]
    workspace: str | None = None
    timeout_seconds: int = 900
    budget_usd: float | None = None
    required_capabilities: tuple[str, ...] = ()


@dataclass
class ExecutionResult:
    ok: bool
    status: str
    final: dict[str, Any] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Executor(Protocol):
    executor_id: str
    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...
