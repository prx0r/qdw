"""R2-Router integration — joint model+budget routing.

R2-Router routes queries to optimal (model, token_budget) pairs
using quality predictors. Fits QDW's CPVS concept perfectly.

Unlike simple routing (which model?), R2-Router asks:
"Which model AND how many tokens for this specific task?"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qdw.core import new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger


@dataclass(frozen=True)
class R2Route:
    """A route with both model AND budget."""
    model_id: str
    token_budget: int
    predicted_quality: float
    predicted_cost: float
    risk_score: float


class R2Router:
    """QDW adapter for R2-Router's joint model+budget optimization.

    R2-Router predicts quality at each (model, budget) pair using
    Ridge regressors, then selects the pair that maximizes:
        risk = (1-λ) × quality - λ × cost

    This is the missing primitive: CPVS(model, provider, token_budget, task_cell).
    """

    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger

    def register_model(self, model_id: str, provider: str, max_tokens: int = 4000) -> str:
        """Register a model for R2 routing."""
        mid = new_id("r2model")
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO r2_models(model_id, provider, max_tokens, created_at)
                VALUES(?,?,?,?)""",
                (model_id, provider, max_tokens, utc_now()),
            )
        self.ledger.append("r2.model_registered", "r2_model", mid, {
            "model_id": model_id, "provider": provider, "max_tokens": max_tokens,
        })
        return mid

    def predict_quality(self, model_id: str, budget: int, query_complexity: float = 0.5) -> float:
        """Predict quality for (model, budget) pair.

        In production, this calls R2-Router's trained Ridge regressors.
        For now, uses a heuristic: longer budgets help harder queries.
        """
        # Simulate: quality improves with budget, but diminishing returns
        base_quality = 0.7
        budget_bonus = min(0.3, budget / 10000)
        complexity_penalty = query_complexity * 0.2
        return min(1.0, max(0.0, base_quality + budget_bonus - complexity_penalty))

    def route(self, query: str, models: list[dict] | None = None,
              lambda_val: float = 0.99999) -> R2Route:
        """Route query to optimal (model, budget) pair.

        Uses R2-Router's risk formula:
            risk = (1-λ) × quality - λ × cost

        λ close to 1 means prioritize cost savings.
        λ close to 0 means prioritize quality.
        """
        if models is None:
            models = [
                {"model_id": "gpt-4o", "provider": "openai", "max_tokens": 4000, "cost_per_1k": 0.005},
                {"model_id": "gpt-3.5-turbo", "provider": "openai", "max_tokens": 4000, "cost_per_1k": 0.0005},
            ]

        # Evaluate query complexity
        query_complexity = min(1.0, len(query) / 500)

        best_risk = -float("inf")
        best_route = None

        for model in models:
            # Evaluate at multiple budget points
            for budget in [100, 500, 1000, 2000, 4000]:
                if budget > model.get("max_tokens", 4000):
                    continue

                quality = self.predict_quality(model["model_id"], budget, query_complexity)
                cost = model.get("cost_per_1k", 0.001) * budget / 1000

                # R2-Router risk formula
                risk = (1 - lambda_val) * quality - lambda_val * cost

                if risk > best_risk:
                    best_risk = risk
                    best_route = R2Route(
                        model_id=model["model_id"],
                        token_budget=budget,
                        predicted_quality=quality,
                        predicted_cost=cost,
                        risk_score=risk,
                    )

        return best_route

    def register_outcome(self, route: R2Route, success: bool, actual_tokens: int) -> None:
        """Record outcome for learning."""
        self.ledger.append("r2.outcome", "r2_route", new_id("r2out"), {
            "model_id": route.model_id,
            "budget": route.token_budget,
            "success": success,
            "actual_tokens": actual_tokens,
            "predicted_quality": route.predicted_quality,
        })
