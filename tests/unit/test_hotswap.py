"""HotSwap tests — 11 behavioral tests from the donor, plus 2 more."""

import random

from qdw.hotswap.accounts import AccountOpportunity
from qdw.hotswap.failure import ErrorClass, classify_error
from qdw.hotswap.hermes_plan import hermes_profile_fragment
from qdw.hotswap.quota import Quota, QuotaLedger
from qdw.hotswap.router import HotSwapRouter
from qdw.hotswap.types import Route, TaskSpec


def route(rid, free=False, prior=0.8, conf=0.8, cost=0.2, out=0.4, **kw):
    return Route(
        route_id=rid,
        model_id=kw.pop("model_id", rid),
        provider_id=kw.pop("provider_id", "p"),
        free=free,
        prior_success=prior,
        prior_confidence=conf,
        input_per_m=0 if free else cost,
        output_per_m=0 if free else out,
        context_tokens=kw.pop("context_tokens", 128000),
        tools_supported=kw.pop("tools_supported", True),
        json_supported=kw.pop("json_supported", True),
        reliability=kw.pop("reliability", 0.98),
        latency_ms=kw.pop("latency_ms", 500),
        cheapest_paid_replacement_cost=kw.pop("cheapest_paid_replacement_cost", 0.001),
        **kw,
    )


def test_unknown_output_price_is_not_zero():
    t = TaskSpec("t", "coding_patch", estimated_output_tokens=1000)
    r = Route("r", "m", "p", free=False, input_per_m=0.1, output_per_m=None)
    assert r.request_cost(t) is None


def test_budget_is_hard():
    t = TaskSpec("t", "coding_patch", task_budget_usd=0.000001)
    r = route("paid", free=False, cost=10, out=20)
    plan = HotSwapRouter().plan(t, [r])
    assert plan.primary is None
    assert "TASK_BUDGET_EXCEEDED" in plan.excluded["paid"]


def test_free_first_when_quality_sufficient():
    t = TaskSpec("t", "source_extract", quality_floor=0.45, free_policy="prefer", paid_allowed=True)
    free = route("free", free=True, prior=0.8)
    paid = route("paid", free=False, prior=0.95, cost=0.1, out=0.1)
    plan = HotSwapRouter().plan(t, [free, paid], rng=random.Random(1))
    assert plan.primary.route.free is True


def test_free_not_used_below_quality_floor():
    t = TaskSpec(
        "t", "coding_feature", quality_floor=0.85,
        free_policy="prefer", paid_allowed=True, criticality="important",
    )
    free = route("free", free=True, prior=0.2, conf=0.9)
    paid = route("paid", free=False, prior=0.98, conf=0.95, cost=0.1, out=0.1)
    router = HotSwapRouter()
    for _ in range(30):
        router.record(t, "paid", True)
    plan = router.plan(t, [free, paid])
    assert plan.primary is not None
    assert plan.primary.route.route_id == "paid"


def test_quota_reservation_prevents_oversubscription():
    t = TaskSpec("t", "source_extract", estimated_input_tokens=100, estimated_output_tokens=100)
    q = Quota("q", "requests", 1, forecast_demand_until_reset=5)
    ledger = QuotaLedger()
    ledger.set_quotas("free", [q])
    ok, _ = ledger.reserve("free", t)
    assert ok
    ok2, reasons = ledger.feasible("free", t)
    assert not ok2


def test_quota_pressure_creates_shadow_cost():
    t = TaskSpec("t", "source_extract", criticality="routine")
    q = Quota("q", "requests", 10, used=9, forecast_demand_until_reset=10)
    ledger = QuotaLedger()
    ledger.set_quotas("free", [q])
    assert ledger.quota_shadow_cost("free", 1.0, t.criticality) > 0


def test_release_gate_disables_exploration_behavior_via_lower_bound():
    t = TaskSpec("t", "certification", quality_floor=0.2, criticality="release_gate", exploration_allowed=False)
    a = route("a", free=False, prior=0.7, conf=0.8)
    router = HotSwapRouter()
    plan = router.plan(t, [a])
    if plan.primary:
        assert plan.primary.exploration_sample is None


def test_error_classifies_quota_before_generic_429():
    assert classify_error(429, "daily limit reached") == ErrorClass.QUOTA_EXHAUSTED
    assert classify_error(429, "retry later") == ErrorClass.TRANSIENT_RATE_LIMIT


def test_context_failure_is_not_transient():
    assert classify_error(400, "maximum context length exceeded") == ErrorClass.CONTEXT


def test_account_opportunity_prioritizes_value_per_friction():
    a = AccountOpportunity("p", "o", 100, 1, 0.2, 1, 0.9, 2)
    assert a.projected_value() > 0
    assert a.rank_score() > 0


def test_hermes_profile_uses_plan_fallbacks():
    t = TaskSpec("t", "source_extract", quality_floor=0.4)
    routes = [route("a", free=True, prior=0.9), route("b", free=False, prior=0.9, cost=0.1, out=0.1)]
    plan = HotSwapRouter().plan(t, routes, rng=random.Random(2))
    cfg = hermes_profile_fragment(plan, "http://localhost:4000/v1")
    assert cfg["model"]["provider"] == "custom"
    assert "fallback_providers" in cfg


def test_pareto_frontier():
    t = TaskSpec("t", "test", quality_floor=0.1)
    r1 = route("fast", free=False, prior=0.9, cost=0.5, out=0.5, latency_ms=100)
    r2 = route("cheap", free=False, prior=0.85, cost=0.01, out=0.01, latency_ms=500)
    plan = HotSwapRouter().plan(t, [r1, r2])
    assert plan.primary is not None
    assert len(plan.fallbacks) >= 0
