"""HotSwap bandit — Thompson sampling, Wilson lower bound, Beta posteriors."""

from __future__ import annotations

import random

from qdw.hotswap.stats import beta_pseudo_counts, clamp, wilson_lower
from qdw.hotswap.types import Posterior, Route


class BanditStore:
    def __init__(self):
        self._data: dict[tuple[str, str], Posterior] = {}

    def get(self, cell_id: str, route: Route) -> Posterior:
        key = (cell_id, route.route_id)
        if key in self._data:
            return self._data[key]
        p = route.prior_success if route.prior_success is not None else 0.5
        strength = 2.0 + 8.0 * clamp(route.prior_confidence)
        posterior = Posterior(
            alpha=1.0 + strength * p,
            beta=1.0 + strength * (1.0 - p),
        )
        self._data[key] = posterior
        return posterior

    def update(self, cell_id: str, route_id: str, success: bool, weight: float = 1.0):
        key = (cell_id, route_id)
        current = self._data.get(key, Posterior(1.0, 1.0))
        if success:
            nxt = Posterior(current.alpha + weight, current.beta)
        else:
            nxt = Posterior(current.alpha, current.beta + weight)
        self._data[key] = nxt
        return nxt

    def mean_and_lower(self, cell_id: str, route: Route) -> tuple[float, float]:
        p = self.get(cell_id, route)
        successes, trials = beta_pseudo_counts(p.alpha, p.beta)
        lower = wilson_lower(successes, trials)
        return p.mean, lower

    def thompson(self, cell_id: str, route: Route, rng: random.Random | None = None) -> float:
        r = rng or random
        p = self.get(cell_id, route)
        return r.betavariate(p.alpha, p.beta)
