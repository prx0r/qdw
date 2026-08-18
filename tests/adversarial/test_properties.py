"""Property-based tests — Hypothesis proofs for critical invariants."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from qdw.core.graph.scheduler import Candidate, allocation_index, net_value, opportunity_cost
from qdw.core.ledger.merkle import inclusion_path, merkle_root, verify_inclusion
from qdw.core.portfolio.reward import OutcomeMetrics, bounded_utility, contribution_margin


class TestMerkleProperties:
    @given(items=st.lists(st.binary(min_size=1, max_size=100), min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_inclusion_always_verifies(self, items: list[bytes]) -> None:
        root = merkle_root(items)
        for i in range(len(items)):
            path = inclusion_path(items, i)
            assert verify_inclusion(items[i], i, len(items), path, root)

    @given(
        items=st.lists(st.binary(min_size=1, max_size=50), min_size=2, max_size=30),
        index=st.integers(min_value=0, max_value=29),
    )
    @settings(max_examples=50)
    def test_wrong_item_fails(self, items: list[bytes], index: int) -> None:
        root = merkle_root(items)
        path = inclusion_path(items, 0)
        min(index, len(items) - 1)
        wrong = b"X" + items[0]
        assert not verify_inclusion(wrong, 0, len(items), path, root)

    @given(n=st.integers(min_value=1, max_value=200))
    @settings(max_examples=50)
    def test_single_item_root_deterministic(self, n: int) -> None:
        items = [bytes([n % 256])]
        r1 = merkle_root(items)
        r2 = merkle_root(items)
        assert r1 == r2


class TestSchedulerProperties:
    @given(
        value=st.floats(min_value=0, max_value=1000),
        cost=st.floats(min_value=0, max_value=100),
        confidence=st.floats(min_value=0.1, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_net_value_non_negative_when_value_exceeds_cost(
        self, value: float, cost: float, confidence: float
    ) -> None:
        c = Candidate(node_id="n", expected_value=value, expected_cost=cost, confidence=confidence)
        nv = net_value(c)
        if value * confidence >= cost:
            assert nv >= 0

    @given(
        values=st.lists(
            st.floats(min_value=0, max_value=1000, allow_nan=False, allow_infinity=False),
            min_size=2,
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_opportunity_cost_non_positive_for_chosen(self, values: list[float]) -> None:
        candidates = [
            Candidate(node_id=f"n{i}", expected_value=v, expected_cost=0)
            for i, v in enumerate(values)
        ]
        chosen = max(candidates, key=lambda c: c.expected_value)
        oc = opportunity_cost(chosen, candidates)
        assert oc <= 0  # chosen is best, so opportunity cost is <= 0

    @given(
        mean_utility=st.floats(min_value=0, max_value=100),
        sample_count=st.integers(min_value=1, max_value=1000),
        total_samples=st.integers(min_value=1, max_value=10000),
    )
    @settings(max_examples=100)
    def test_allocation_index_positive(
        self, mean_utility: float, sample_count: int, total_samples: int
    ) -> None:
        ai = allocation_index(mean_utility, sample_count, total_samples)
        assert ai >= 0


class TestRewardProperties:
    @given(m=st.builds(OutcomeMetrics))
    @settings(max_examples=100)
    def test_bounded_utility_in_range(self, m: OutcomeMetrics) -> None:
        u = bounded_utility(m)
        assert -1.0 <= u <= 1.0

    @given(
        revenue=st.floats(min_value=0, max_value=10000),
        variable_cost=st.floats(min_value=0, max_value=10000),
    )
    @settings(max_examples=100)
    def test_contribution_margin(self, revenue: float, variable_cost: float) -> None:
        m = OutcomeMetrics(revenue_usd=revenue, variable_cost_usd=variable_cost)
        cm = contribution_margin(m)
        assert cm == revenue - variable_cost
