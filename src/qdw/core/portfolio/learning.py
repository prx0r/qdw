"""Factory learning — Beta posteriors, cost/utility tracking."""

from __future__ import annotations

from dataclasses import dataclass

from qdw.core import utc_now
from qdw.core.db import Database


@dataclass(frozen=True)
class FactoryPosterior:
    runs: int
    alpha: float
    beta: float
    mean_success: float
    mean_utility: float
    mean_cost: float


class FactoryLearning:
    def __init__(self, db: Database):
        self.db = db

    def update(
        self,
        factory_id: str,
        version: str,
        *,
        certified: bool,
        outcome_success: bool,
        utility: float,
        cost_usd: float,
    ) -> None:
        with self.db.tx(immediate=True) as con:
            r = con.execute(
                "SELECT * FROM factory_stats WHERE factory_id=? AND factory_version=?",
                (factory_id, version),
            ).fetchone()
            if not r:
                con.execute(
                    """INSERT INTO factory_stats(factory_id, factory_version, runs, certified_runs,
                    success_alpha, success_beta, total_cost_usd, total_utility, updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (factory_id, version, 1, 1 if certified else 0,
                     2 if outcome_success else 1, 1 if outcome_success else 2,
                     cost_usd, utility, utc_now()),
                )
            else:
                con.execute(
                    """UPDATE factory_stats SET runs=runs+1, certified_runs=certified_runs+?,
                    success_alpha=success_alpha+?, success_beta=success_beta+?,
                    total_cost_usd=total_cost_usd+?, total_utility=total_utility+?, updated_at=?
                    WHERE factory_id=? AND factory_version=?""",
                    (1 if certified else 0, 1 if outcome_success else 0, 0 if outcome_success else 1,
                     cost_usd, utility, utc_now(), factory_id, version),
                )

    def posterior(self, factory_id: str, version: str) -> FactoryPosterior | None:
        with self.db.connect() as con:
            r = con.execute(
                "SELECT * FROM factory_stats WHERE factory_id=? AND factory_version=?",
                (factory_id, version),
            ).fetchone()
        if not r:
            return None
        runs = max(1, r["runs"])
        a = r["success_alpha"]
        b = r["success_beta"]
        return FactoryPosterior(r["runs"], a, b, a / (a + b), r["total_utility"] / runs, r["total_cost_usd"] / runs)
