"""HotSwap extended routing — Estate algorithms absorbed into QDW.

These are the routing algorithms from qdw-sandbox/estate, adapted
to work with HotSwap's Route/TaskSpec types instead of Estate's
ResourceDescriptor/CapabilityRequest types.

HistoricalProfilePolicy: ranks by cost-per-verified-success (CPVS)
ClusterProfilePolicy: groups similar objectives, routes within clusters
CascadePolicy: ordered fallback with cost awareness
"""

from __future__ import annotations

import hashlib
import math
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from qdw.hotswap.types import CandidateAssessment, ExecutionPlan, Route, TaskSpec


@dataclass(frozen=True)
class RouteAssessment:
    route_id: str
    eligible: bool
    reason_codes: tuple[str, ...] = ()
    predicted_success: float | None = None
    expected_cost: float | None = None
    score: float | None = None


# ── Historical Profile ──

def historical_plan(
    task: TaskSpec,
    routes: list[Route],
    assessments: dict[str, Any] | None = None,
) -> list[RouteAssessment]:
    """Rank routes by cost-per-verified-success (CPVS).

    Known CPVS ranks first; unknown ranks later for cold-start exploration.
    """
    assessments = assessments or {}
    result = []
    for route in routes:
        a = assessments.get(route.route_id, {})
        success = a.get("success_mean")
        cost = a.get("mean_cost_usd") or route.fixed_request_cost_usd
        cpvs = None if success in (None, 0) or cost is None else float(cost) / float(success)
        eligible = task.quality_floor is None or success is None or success >= task.quality_floor
        score = None if cpvs is None else -cpvs  # negative because lower CPVS is better
        result.append(RouteAssessment(
            route_id=route.route_id,
            eligible=eligible,
            predicted_success=success,
            expected_cost=cost,
            score=score,
        ))
    return sorted(result, key=lambda c: (c.score is None, -(c.score or -1e30), c.route_id))


# ── Cluster Profile ──

def _vec(text: str, dims: int = 128) -> list[float]:
    """Deterministic hashed token vector (no embedding provider needed)."""
    v = [0.0] * dims
    for t in re.findall(r"[a-z0-9_]+", text.lower()):
        h = int.from_bytes(hashlib.sha256(t.encode()).digest()[:8], "big")
        i = h % dims
        sign = 1 if (h >> 8) & 1 else -1
        v[i] += sign
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class ClusterRouter:
    """Deterministic cluster routing using hashed token vectors."""

    def __init__(self, k: int = 16, dims: int = 128):
        self.k = k
        self.dims = dims
        self.centroids: list[list[float]] = []
        self.stats: list[dict[str, Any]] = []

    def fit(self, examples: list[tuple[str, str, bool, float]], iterations: int = 12) -> None:
        """Fit clusters from (text, resource_id, success, cost) examples."""
        if not examples:
            self.centroids = []
            self.stats = []
            return
        xs = [_vec(text, self.dims) for text, _, _, _ in examples]
        k = min(self.k, len(xs))
        cent = [xs[i * len(xs) // k][:] for i in range(k)]
        assign = [0] * len(xs)
        for _ in range(iterations):
            assign = [max(range(k), key=lambda j: _dot(x, cent[j])) for x in xs]
            new = []
            for j in range(k):
                members = [xs[i] for i, a in enumerate(assign) if a == j]
                if not members:
                    new.append(cent[j])
                    continue
                c = [sum(m[d] for m in members) / len(members) for d in range(self.dims)]
                n = math.sqrt(sum(z * z for z in c)) or 1
                new.append([z / n for z in c])
            cent = new
        stats: list[dict] = [{} for _ in range(k)]
        for e, a in zip(examples, assign):
            text, resource_id, success, cost = e
            s = stats[a].setdefault(resource_id, {"ok": 0, "n": 0, "cost": 0.0})
            s["n"] += 1
            s["ok"] += int(success)
            s["cost"] += cost
        self.centroids = cent
        self.stats = stats

    def plan(self, task: TaskSpec, routes: list[Route]) -> list[RouteAssessment]:
        """Route using cluster similarity."""
        if not self.centroids:
            return historical_plan(task, routes)
        x = _vec(task.task_kind, self.dims)
        ci = max(range(len(self.centroids)), key=lambda j: _dot(x, self.centroids[j]))
        st = self.stats[ci]
        result = []
        for route in routes:
            ss = st.get(route.route_id)
            success = (ss["ok"] / ss["n"]) if ss else None
            cost = (ss["cost"] / ss["n"]) if ss else route.fixed_request_cost_usd
            eligible = task.quality_floor is None or success is None or success >= task.quality_floor
            score = None if success is None else success - (float(cost or 0) * 0.05)
            result.append(RouteAssessment(
                route_id=route.route_id, eligible=eligible,
                predicted_success=success, expected_cost=cost, score=score,
            ))
        return sorted(result, key=lambda c: (c.score is None, -(c.score or -1e30), c.route_id))


# ── Cascade ──

def cascade_plan(task: TaskSpec, routes: list[Route]) -> list[RouteAssessment]:
    """Ordered fallback: try routes in CPVS order."""
    return historical_plan(task, routes)
