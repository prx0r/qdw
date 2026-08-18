"""WorkGraph scheduler — candidate selection with UNKNOWN-aware ranking.

UNKNOWN cost is not zero cost. UNKNOWN value is not zero value.
Nodes with unknown economics are eligible but ranked below known-positive nodes.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import log, sqrt


@dataclass(frozen=True)
class Candidate:
    node_id: str
    expected_value: float | None = None
    expected_cost: float | None = None
    confidence: float = 1.0
    urgency: float = 0.0
    risk: float = 0.0
    sample_count: int = 0


def net_value(c: Candidate) -> float | None:
    """Compute net value. Returns None if either value or cost is unknown.

    UNKNOWN != ZERO: a node with unknown economics is eligible but
    not rankable above nodes with known positive net value.
    """
    if c.expected_value is None or c.expected_cost is None:
        return None
    return c.expected_value * c.confidence - c.expected_cost - c.risk + c.urgency


def opportunity_cost(chosen: Candidate, candidates: Iterable[Candidate]) -> float | None:
    alts = [net_value(c) for c in candidates if c.node_id != chosen.node_id and net_value(c) is not None]
    cv = net_value(chosen)
    if cv is None:
        return None
    return (max(alts) if alts else 0.0) - cv


def allocation_index(
    mean_utility: float,
    sample_count: int,
    total_samples: int,
    exploration: float = 0.25,
) -> float:
    if sample_count <= 0:
        return float("inf")
    return mean_utility + exploration * sqrt(max(0.0, log(max(2, total_samples))) / sample_count)


def choose(candidates: list[Candidate]) -> Candidate | None:
    """Select the best candidate.

    Ranking:
    1. Known positive net_value nodes (ranked by net_value)
    2. Unknown-economics nodes (ranked by urgency, then created_at)
    3. No eligible nodes → None
    """
    known = [(c, net_value(c)) for c in candidates]
    positive = [(c, v) for c, v in known if v is not None and v > 0]
    unknown = [c for c, v in known if v is None]

    if positive:
        # Rank known-positive by net_value descending
        positive.sort(key=lambda x: (-x[1], -x[0].confidence, x[0].risk))
        return positive[0][0]

    if unknown:
        # Unknown-economics nodes: rank by urgency, then fall back to first
        unknown.sort(key=lambda c: (-c.urgency, c.node_id))
        return unknown[0]

    return None
