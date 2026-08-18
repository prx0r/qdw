"""HotSwap router — Pareto-frontier route selection with bandit learning."""

from __future__ import annotations

import random

from qdw.hotswap.bandit import BanditStore
from qdw.hotswap.policy import hard_exclusions
from qdw.hotswap.quota import QuotaLedger
from qdw.hotswap.types import CandidateAssessment, ExecutionPlan, Route, TaskSpec


class HotSwapRouter:
    def __init__(self, bandits: BanditStore | None = None, quotas: QuotaLedger | None = None):
        self.bandits = bandits or BanditStore()
        self.quotas = quotas or QuotaLedger()

    def _assess(self, task: TaskSpec, route: Route, escalation_cost: float, rng=None) -> CandidateAssessment:
        mean, lower = self.bandits.mean_and_lower(task.cell_id, route)
        p = lower if task.criticality in {"release_gate", "production"} else mean

        exploration_sample = None
        if task.exploration_allowed and task.criticality in {"disposable", "routine"}:
            exploration_sample = self.bandits.thompson(task.cell_id, route, rng=rng)
            p_for_rank = exploration_sample
        else:
            p_for_rank = p

        request_cost = route.request_cost(task)
        if request_cost is None:
            request_cost = float("inf")

        shadow = 0.0
        if route.free:
            shadow = self.quotas.quota_shadow_cost(
                route.route_id,
                route.cheapest_paid_replacement_cost,
                task.criticality,
            )

        reliability_penalty = 0.0
        if route.reliability is not None:
            reliability_penalty = max(0.0, 1.0 - route.reliability) * escalation_cost * 0.25

        expected = request_cost + shadow + (1.0 - p_for_rank) * escalation_cost + reliability_penalty

        return CandidateAssessment(
            route=route,
            p_success=mean,
            p_lower=lower,
            request_cost=request_cost,
            quota_shadow_cost=shadow,
            expected_completion_cost=expected,
            exploration_sample=exploration_sample,
        )

    @staticmethod
    def _dominates(a: CandidateAssessment, b: CandidateAssessment) -> bool:
        a_rel = a.route.reliability if a.route.reliability is not None else -1
        b_rel = b.route.reliability if b.route.reliability is not None else -1
        a_lat = a.route.latency_ms if a.route.latency_ms is not None else float("inf")
        b_lat = b.route.latency_ms if b.route.latency_ms is not None else float("inf")
        no_worse = (
            a.p_lower >= b.p_lower
            and a.expected_completion_cost <= b.expected_completion_cost
            and a_rel >= b_rel
            and a_lat <= b_lat
        )
        strictly = (
            a.p_lower > b.p_lower
            or a.expected_completion_cost < b.expected_completion_cost
            or a_rel > b_rel
            or a_lat < b_lat
        )
        return no_worse and strictly

    def pareto(self, xs: list[CandidateAssessment]) -> list[CandidateAssessment]:
        return [x for x in xs if not any(self._dominates(y, x) for y in xs if y is not x)]

    def plan(self, task: TaskSpec, routes: list[Route], rng: random.Random | None = None) -> ExecutionPlan:
        excluded: dict[str, list[str]] = {}
        viable: list[Route] = []

        for route in routes:
            reasons = hard_exclusions(task, route)
            q_ok, q_reasons = self.quotas.feasible(route.route_id, task)
            if not q_ok:
                reasons.extend(q_reasons)
            if reasons:
                excluded[route.route_id] = reasons
            else:
                viable.append(route)

        if not viable:
            return ExecutionPlan(task.task_id, None, [], excluded, ["NO_CANDIDATES"])

        finite_costs = [r.request_cost(task) for r in viable if r.request_cost(task) is not None]
        escalation_cost = max(finite_costs, default=0.0)

        assessed = [self._assess(task, r, escalation_cost, rng=rng) for r in viable]

        qualified = []
        for a in assessed:
            quality_metric = a.p_lower if task.criticality in {"release_gate", "production"} else a.p_success
            if quality_metric >= task.quality_floor:
                qualified.append(a)
            else:
                excluded[a.route.route_id] = ["QUALITY_FLOOR_NOT_MET"]

        if not qualified:
            return ExecutionPlan(task.task_id, None, [], excluded, ["NO_ROUTE_MEETS_QUALITY_FLOOR"])

        frontier = self.pareto(qualified)
        free = [a for a in frontier if a.route.free]

        reason_codes = []
        if task.free_policy in {"require", "prefer"} and free:
            candidates = free
            reason_codes.append("QUALIFIED_FREE_FRONTIER")
        else:
            candidates = frontier
            if task.free_policy == "prefer":
                reason_codes.append("NO_QUALIFIED_FREE_ROUTE")

        candidates.sort(key=lambda a: (
            a.expected_completion_cost,
            -a.p_lower,
            a.route.latency_ms if a.route.latency_ms is not None else float("inf"),
            a.route.route_id,
        ))

        primary = candidates[0]

        rest = [a for a in frontier if a.route.route_id != primary.route.route_id]
        rest.sort(key=lambda a: (
            0 if a.route.model_id == primary.route.model_id else 1,
            a.expected_completion_cost,
            -a.p_lower,
        ))

        return ExecutionPlan(task.task_id, primary, rest[:4], excluded, reason_codes)

    def record(self, task: TaskSpec, route_id: str, success: bool, weight: float = 1.0):
        return self.bandits.update(task.cell_id, route_id, success, weight=weight)
