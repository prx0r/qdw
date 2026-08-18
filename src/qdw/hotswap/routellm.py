"""RouteLLM integration — smart routing on top of litellm.

RouteLLM trains routing models that decide: "does this query need
an expensive model or can a cheap one handle it?"

Uses litellm as backend. Complements HotSwap's policy layer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from qdw.core import hash_object, new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger


@dataclass(frozen=True)
class RouteLLMResult:
    """Result from RouteLLM routing decision."""
    selected_model: str
    confidence: float
    strong_win_rate: float
    strategy: str
    cost_savings_estimate: float


class RouteLLMRouter:
    """QDW adapter for RouteLLM smart routing.

    RouteLLM uses trained models to predict whether a query needs
    an expensive model or can be handled by a cheaper one.

    This is proactive (predicts before execute), while HotSwap
    is reactive (learns after execute).
    """

    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger
        self._models: dict[str, Any] = {}

    def register_model_pair(self, strong: str, weak: str, strategy: str = "sw_ranking") -> str:
        """Register a model pair for routing."""
        pair_id = new_id("modelpair")
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO route_llm_pairs(pair_id, strong_model, weak_model, strategy, created_at)
                VALUES(?,?,?,?,?)""",
                (pair_id, strong, weak, strategy, utc_now()),
            )
        self.ledger.append("routellm.pair_registered", "model_pair", pair_id, {
            "strong": strong, "weak": weak, "strategy": strategy,
        })
        return pair_id

    def calculate_win_rate(self, prompt: str, pair_id: str | None = None) -> float:
        """Calculate strong model win rate for a prompt.

        In production, this would call RouteLLM's trained model.
        For now, returns a simulated score based on prompt complexity.
        """
        # Simulate: longer prompts favor strong models
        prompt_len = len(prompt)
        if prompt_len < 100:
            return 0.3  # Short prompts can use cheap models
        elif prompt_len < 500:
            return 0.5  # Medium prompts
        else:
            return 0.8  # Long prompts need strong models

    def route(self, prompt: str, threshold: float = 0.5, strong_model: str = "gpt-4",
              weak_model: str = "gpt-3.5-turbo") -> RouteLLMResult:
        """Route a prompt to the appropriate model.

        Returns RouteLLMResult with selected model and confidence.
        """
        win_rate = self.calculate_win_rate(prompt)
        selected = strong_model if win_rate >= threshold else weak_model
        confidence = win_rate if win_rate >= threshold else 1.0 - win_rate

        # Estimate cost savings
        cost_savings = 0.0
        if selected == weak_model:
            cost_savings = 0.7  # ~70% savings by using cheap model

        return RouteLLMResult(
            selected_model=selected,
            confidence=confidence,
            strong_win_rate=win_rate,
            strategy="simulated",
            cost_savings_estimate=cost_savings,
        )

    def get_model_pairs(self) -> list[dict]:
        """Get all registered model pairs."""
        with self.db.connect() as con:
            rows = con.execute(
                "SELECT * FROM route_llm_pairs ORDER BY created_at"
            ).fetchall()
        return [dict(r) for r in rows]
