"""HotSwap quota — quota reservation, pressure, shadow cost."""

from __future__ import annotations

from dataclasses import dataclass

from qdw.hotswap.stats import clamp


@dataclass
class Quota:
    quota_id: str
    metric: str
    limit: float
    used: float = 0
    reserved: float = 0
    forecast_demand_until_reset: float = 0

    @property
    def remaining(self) -> float:
        return max(0.0, self.limit - self.used - self.reserved)

    @property
    def pressure(self) -> float:
        return self.forecast_demand_until_reset / max(self.remaining, 1e-9)


class QuotaLedger:
    def __init__(self):
        self.by_route: dict[str, list[Quota]] = {}

    def set_quotas(self, route_id: str, quotas: list[Quota]):
        self.by_route[route_id] = quotas

    def requirements(self, task) -> dict[str, float]:
        return {
            "requests": 1,
            "input_tokens": task.estimated_input_tokens,
            "output_tokens": task.estimated_output_tokens,
            "total_tokens": task.estimated_input_tokens + task.estimated_output_tokens,
        }

    def feasible(self, route_id: str, task) -> tuple[bool, list[str]]:
        reasons = []
        req = self.requirements(task)
        for q in self.by_route.get(route_id, []):
            needed = req.get(q.metric, 0)
            if needed > q.remaining:
                reasons.append(f"QUOTA_INSUFFICIENT:{q.metric}")
        return (not reasons), reasons

    def max_pressure(self, route_id: str) -> float:
        qs = self.by_route.get(route_id, [])
        return max([q.pressure for q in qs], default=0.0)

    def reserve(self, route_id: str, task):
        ok, reasons = self.feasible(route_id, task)
        if not ok:
            return False, reasons
        req = self.requirements(task)
        for q in self.by_route.get(route_id, []):
            q.reserved += req.get(q.metric, 0)
        return True, []

    def quota_shadow_cost(self, route_id: str, replacement_cost: float, criticality: str) -> float:
        pressure = self.max_pressure(route_id)
        shadow_fraction = clamp((pressure - 0.67) / 0.83)
        factor = {
            "disposable": 1.0,
            "routine": 0.9,
            "important": 0.5,
            "release_gate": 0.15,
            "production": 0.15,
        }.get(criticality, 0.8)
        return replacement_cost * shadow_fraction * factor
