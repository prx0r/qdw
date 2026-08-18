"""HotSwap account opportunity — provider promo value ranking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AccountOpportunity:
    provider_id: str
    offer_id: str
    forecast_eligible_tasks: int
    baseline_ecps: float
    candidate_ecps: float
    promo_survival_probability: float
    evidence_confidence: float
    setup_friction: int

    def projected_value(self) -> float:
        gross = self.forecast_eligible_tasks * max(0.0, self.baseline_ecps - self.candidate_ecps)
        return gross * self.promo_survival_probability * self.evidence_confidence

    def rank_score(self) -> float:
        return self.projected_value() / max(1, self.setup_friction)
