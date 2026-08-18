"""Benchmark: HotSwap vs LiteLLM-style vs HotSwap+LiteLLM.

Compares routing strategies on synthetic workloads.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from qdw.hotswap.bandit import BanditStore
from qdw.hotswap.litellm_router import LiteLLMRouter
from qdw.hotswap.quota import QuotaLedger
from qdw.hotswap.router import HotSwapRouter
from qdw.hotswap.types import Route, TaskSpec


@dataclass
class BenchmarkResult:
    strategy: str
    total_cost: float
    success_rate: float
    routes_used: int
    free_used: int


def simulate(
    router: Any,
    tasks: list[TaskSpec],
    routes: list[Route],
    outcomes: dict[str, bool] | None = None,
    seed: int = 42,
) -> BenchmarkResult:
    """Simulate routing decisions and track outcomes."""
    rng = random.Random(seed)
    outcomes = outcomes or {}
    total_cost = 0.0
    successes = 0
    routes_used = set()
    free_used = 0

    for task in tasks:
        plan = router.plan(task, routes)
        if plan.primary is None:
            continue

        route = plan.primary.route
        route_id = route.route_id
        routes_used.add(route_id)

        # Simulate outcome
        if route_id in outcomes:
            success = outcomes[route_id]
        else:
            success = rng.random() < 0.8  # default 80% success

        # Record outcome for learning
        router.record(task, route_id, success)

        # Track costs
        cost = route.request_cost(task)
        if cost is not None:
            total_cost += cost
        if route.free:
            free_used += 1
        if success:
            successes += 1

    return BenchmarkResult(
        strategy=getattr(router, '__class__', type(router)).__name__,
        total_cost=total_cost,
        success_rate=successes / max(len(tasks), 1),
        routes_used=len(routes_used),
        free_used=free_used,
    )


def run_benchmark(n_tasks: int = 100, seed: int = 42) -> dict[str, BenchmarkResult]:
    """Run benchmark comparing routing strategies."""
    rng = random.Random(seed)

    # Create routes
    routes = [
        Route("free", "m", "p", free=True),
        Route("cheap", "m", "p", fixed_request_cost_usd=0.001),
        Route("medium", "m", "p", fixed_request_cost_usd=0.01),
        Route("expensive", "m", "p", fixed_request_cost_usd=0.10),
    ]

    # Create tasks
    tasks = [
        TaskSpec(f"t{i}", rng.choice(["coding", "research", "analysis"]),
                quality_floor=rng.uniform(0.3, 0.9),
                free_policy=rng.choice(["prefer", "allow", "require"]))
        for i in range(n_tasks)
    ]

    # Define outcomes (some routes succeed more than others)
    outcomes = {
        "free": True,  # free always succeeds
        "cheap": True,  # cheap usually succeeds
        "medium": True,
        "expensive": True,
    }

    results = {}

    # Strategy 1: HotSwap only
    bandits1 = BanditStore()
    hotswap = HotSwapRouter(bandits=bandits1)
    results["HotSwap"] = simulate(hotswap, tasks, routes, outcomes, seed)

    # Strategy 2: LiteLLM-style (just cost-based selection)
    # Simulate by sorting routes by cost and picking cheapest
    class LiteLLMStyle:
        def plan(self, task, routes):
            # Just pick cheapest viable route
            viable = [r for r in routes if r.request_cost(task) is not None]
            if not viable:
                viable = [r for r in routes]
            viable.sort(key=lambda r: r.request_cost(task) or float("inf"))
            from qdw.hotswap.types import ExecutionPlan, CandidateAssessment
            return ExecutionPlan(
                task.task_id,
                CandidateAssessment(viable[0], 0.8, 0.7, viable[0].request_cost(task) or 0, 0, 0),
                [], {}, ["LITELLM_COST"],
            )
        def record(self, task, route_id, success, weight=1.0):
            pass

    results["LiteLLM-Style"] = simulate(LiteLLMStyle(), tasks, routes, outcomes, seed)

    # Strategy 3: HotSwap + LiteLLM (hybrid)
    bandits3 = BanditStore()
    hybrid = LiteLLMRouter(bandits=bandits3)
    results["HotSwap+LiteLLM"] = simulate(hybrid, tasks, routes, outcomes, seed)

    return results


if __name__ == "__main__":
    results = run_benchmark()
    print("BENCHMARK RESULTS")
    print("=" * 60)
    for name, r in results.items():
        print(f"\n{name}:")
        print(f"  Total cost:    ${r.total_cost:.4f}")
        print(f"  Success rate:  {r.success_rate:.1%}")
        print(f"  Routes used:   {r.routes_used}")
        print(f"  Free routes:   {r.free_used}")
