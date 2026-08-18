"""Persistent HotSwap state — route posteriors and quota state in SQLite.

BanditStore now persists to the database. Learning survives restarts.
"""

from __future__ import annotations

import random

from qdw.core import utc_now
from qdw.core.db import Database
from qdw.hotswap.stats import beta_pseudo_counts, wilson_lower
from qdw.hotswap.types import Posterior, Route


class PersistentBanditStore:
    """BanditStore backed by SQLite. Posteriors survive process restarts."""

    def __init__(self, db: Database):
        self.db = db

    def get(self, cell_id: str, route: Route) -> Posterior:
        with self.db.connect() as con:
            row = con.execute(
                "SELECT alpha, beta FROM route_posteriors WHERE cell_id=? AND route_id=?",
                (cell_id, route.route_id),
            ).fetchone()
            if row:
                return Posterior(row["alpha"], row["beta"])

        # Initialize from prior
        p = route.prior_success if route.prior_success is not None else 0.5
        from qdw.hotswap.stats import clamp
        strength = 2.0 + 8.0 * clamp(route.prior_confidence)
        posterior = Posterior(alpha=1.0 + strength * p, beta=1.0 + strength * (1.0 - p))
        self._upsert(cell_id, route.route_id, posterior)
        return posterior

    def update(self, cell_id: str, route_id: str, success: bool, weight: float = 1.0) -> Posterior:
        with self.db.connect() as con:
            row = con.execute(
                "SELECT alpha, beta FROM route_posteriors WHERE cell_id=? AND route_id=?",
                (cell_id, route_id),
            ).fetchone()
        current = Posterior(row["alpha"], row["beta"]) if row else Posterior(1.0, 1.0)
        if success:
            nxt = Posterior(current.alpha + weight, current.beta)
        else:
            nxt = Posterior(current.alpha, current.beta + weight)
        self._upsert(cell_id, route_id, nxt)
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

    def _upsert(self, cell_id: str, route_id: str, posterior: Posterior) -> None:
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO route_posteriors(cell_id, route_id, alpha, beta, updated_at)
                VALUES(?,?,?,?,?) ON CONFLICT(cell_id, route_id)
                DO UPDATE SET alpha=excluded.alpha, beta=excluded.beta, updated_at=excluded.updated_at""",
                (cell_id, route_id, posterior.alpha, posterior.beta, utc_now()),
            )
