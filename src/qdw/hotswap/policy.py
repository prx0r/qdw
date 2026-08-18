"""HotSwap policy — hard exclusions, budget limits, capability checks."""

from __future__ import annotations

from qdw.hotswap.types import Route, TaskSpec


def hard_exclusions(task: TaskSpec, route: Route) -> list[str]:
    reasons = []
    if not route.active:
        reasons.append("ROUTE_INACTIVE")
    if route.breaker_open:
        reasons.append("CIRCUIT_OPEN")
    if task.context_tokens_min:
        if route.context_tokens is None:
            reasons.append("CONTEXT_UNKNOWN")
        elif route.context_tokens < task.context_tokens_min:
            reasons.append("CONTEXT_INSUFFICIENT")
    if task.tools_required:
        if route.tools_supported is None:
            reasons.append("TOOLS_UNKNOWN")
        elif not route.tools_supported:
            reasons.append("TOOLS_NOT_SUPPORTED")
    if task.json_required:
        if route.json_supported is None:
            reasons.append("JSON_UNKNOWN")
        elif not route.json_supported:
            reasons.append("JSON_NOT_SUPPORTED")
    if task.free_policy == "require" and not route.free:
        reasons.append("NOT_FREE")
    if not task.paid_allowed and not route.free:
        reasons.append("PAID_NOT_ALLOWED")
    cost = route.request_cost(task)
    if not route.free and cost is None:
        reasons.append("COST_UNKNOWN")
    if task.task_budget_usd is not None and cost is not None and cost > task.task_budget_usd:
        reasons.append("TASK_BUDGET_EXCEEDED")
    return reasons


def reserve_priority(criticality: str) -> int:
    return {
        "disposable": 0,
        "routine": 1,
        "important": 2,
        "release_gate": 3,
        "production": 3,
    }.get(criticality, 1)
