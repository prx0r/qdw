"""Persistent HotSwap state — route posteriors and quota state in SQLite.

BanditStore now persists to the database. Learning survives restarts.
Route definitions are persisted to the database so they survive restarts.
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

    def save_route(self, route: Route) -> None:
        """Persist a route definition so it survives restarts."""
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO route_definitions(
                    route_id, model_id, provider_id, active, free,
                    input_per_m, output_per_m, context_tokens,
                    tools_supported, json_supported, reliability, latency_ms,
                    cheapest_paid_replacement_cost, created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(route_id) DO UPDATE SET
                    model_id=excluded.model_id, provider_id=excluded.provider_id,
                    active=excluded.active, free=excluded.free,
                    input_per_m=excluded.input_per_m, output_per_m=excluded.output_per_m,
                    context_tokens=excluded.context_tokens,
                    tools_supported=excluded.tools_supported, json_supported=excluded.json_supported,
                    reliability=excluded.reliability, latency_ms=excluded.latency_ms,
                    cheapest_paid_replacement_cost=excluded.cheapest_paid_replacement_cost,
                    updated_at=excluded.updated_at""",
                (route.route_id, route.model_id, route.provider_id,
                 1 if route.active else 0, 1 if route.free else 0,
                 route.input_per_m, route.output_per_m, route.context_tokens,
                 1 if route.tools_supported else (0 if route.tools_supported is not None else None),
                 1 if route.json_supported else (0 if route.json_supported is not None else None),
                 route.reliability, route.latency_ms, route.cheapest_paid_replacement_cost,
                 utc_now(), utc_now()),
            )

    def load_routes(self) -> list[Route]:
        """Load persisted route definitions from the database."""
        with self.db.connect() as con:
            rows = con.execute("SELECT * FROM route_definitions ORDER BY route_id").fetchall()
        return [
            Route(
                route_id=r["route_id"],
                model_id=r["model_id"],
                provider_id=r["provider_id"],
                active=bool(r["active"]),
                free=bool(r["free"]),
                input_per_m=r["input_per_m"],
                output_per_m=r["output_per_m"],
                context_tokens=r["context_tokens"],
                tools_supported=bool(r["tools_supported"]) if r["tools_supported"] is not None else None,
                json_supported=bool(r["json_supported"]) if r["json_supported"] is not None else None,
                reliability=r["reliability"],
                latency_ms=r["latency_ms"],
                cheapest_paid_replacement_cost=r["cheapest_paid_replacement_cost"] or 0.001,
            )
            for r in rows
        ]
