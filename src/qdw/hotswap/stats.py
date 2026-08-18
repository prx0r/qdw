"""HotSwap statistics — Wilson lower bound, Beta pseudo-counts."""

from __future__ import annotations

import math


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def wilson_lower(successes: float, trials: float, z: float = 1.6448536269514722) -> float:
    """Approximate one-sided 95% lower bound. Supports pseudo-counts."""
    if trials <= 0:
        return 0.0
    p = successes / trials
    denom = 1.0 + z * z / trials
    centre = p + z * z / (2 * trials)
    adj = z * math.sqrt((p * (1 - p) + z * z / (4 * trials)) / trials)
    return clamp((centre - adj) / denom)


def beta_pseudo_counts(alpha: float, beta: float) -> tuple[float, float]:
    """Return successes, trials implied by a Beta posterior with Beta(1,1) base."""
    successes = max(0.0, alpha - 1.0)
    failures = max(0.0, beta - 1.0)
    return successes, successes + failures
