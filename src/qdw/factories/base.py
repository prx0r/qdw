"""Factory definition — immutable manifest, versioned."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FactoryDefinition:
    factory_id: str
    version: str
    kind: str
    name: str
    phases: tuple[str, ...]
    mandatory_teams: tuple[str, ...]
    conditional_teams: dict[str, tuple[str, ...]] = field(default_factory=dict)
    default_budget_usd: float = 0
    fixture_id: str = ""
    fixture_max_cost_usd: float = 0

    @classmethod
    def from_manifest(cls, m: dict[str, Any]) -> FactoryDefinition:
        f = m["fixture"]
        return cls(
            m["factory_id"],
            m["version"],
            m["kind"],
            m["name"],
            tuple(m["phases"]),
            tuple(m.get("mandatory_teams", [])),
            {k: tuple(v) for k, v in m.get("conditional_teams", {}).items()},
            float(m.get("default_budget_usd", 0)),
            f["fixture_id"],
            float(f["max_cost_usd"]),
        )


@dataclass(frozen=True)
class FactoryPlanNode:
    key: str
    kind: str
    title: str
    payload: dict[str, Any]
    depends_on: tuple[str, ...] = ()
    expected_cost: float = 0
    expected_value: float = 0


@dataclass(frozen=True)
class FactoryPlan:
    factory_id: str
    factory_version: str
    nodes: tuple[FactoryPlanNode, ...]
