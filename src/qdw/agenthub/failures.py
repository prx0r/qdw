"""AgentHub fault injection — cascade radius, detection/recovery rates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FaultResult:
    injected_node: str
    detected: bool
    recovered: bool
    affected_nodes: int
    total_nodes: int
    detection_time: float | None = None
    recovery_time: float | None = None

    @property
    def cascade_radius(self) -> float:
        return self.affected_nodes / max(1, self.total_nodes)


def aggregate_faults(results: list[FaultResult]) -> dict:
    n = len(results)
    if n == 0:
        return {"detection_rate": 0, "recovery_rate": 0, "mean_cascade_radius": 0}
    return {
        "detection_rate": sum(r.detected for r in results) / n,
        "recovery_rate": sum(r.recovered for r in results) / n,
        "mean_cascade_radius": sum(r.cascade_radius for r in results) / n,
    }
