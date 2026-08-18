"""Dell → API → LiteLLM → Router pipeline.

The flow:
1. Dell discovers a deal (provider/model with good pricing)
2. QDW creates a route for it
3. Route gets registered in LiteLLM's model list
4. HotSwap/LiteLLM can now route to it
5. Performance is tracked
6. If it performs well, it stays. If not, circuit-broken.

This is the self-improving routing system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qdw.core import hash_object, new_id, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.federation.contracts import ExternalSnapshot, ExternalStatus, FederatedRef
from qdw.federation.dell_adapter import DellFederationAdapter
from qdw.federation.litellm_registry import LiteLLMRegistry, ModelPricing
from qdw.hotswap.types import Route, TaskSpec


@dataclass(frozen=True)
class DealRoute:
    """A route created from a Dell deal, registered in LiteLLM."""
    route_id: str
    model_id: str
    provider_id: str
    deal_score: float
    litellm_pricing: ModelPricing | None
    fixed_cost_usd: float | None
    created_at: str
    source: str  # "litellm_baseline" or "dell_deal"


class DellLiteLLMPipeline:
    """Finds deals via Dell, creates routes, registers in LiteLLM router.

    Architecture:
    Dell finds deal → QDW creates route → LiteLLM pricing baseline
    → HotSwap decides → performance tracked → circuit breaker
    """

    def __init__(self, db: Database, ledger: Ledger, litellm: LiteLLMRegistry):
        self.db = db
        self.ledger = ledger
        self.litellm = litellm
        self.dell_adapter = DellFederationAdapter()

    def find_deal_routes(self, dell_response: dict) -> list[DealRoute]:
        """Process Dell response and create routes from deals."""
        snap, _ = self.dell_adapter.normalize({}, dell_response)
        routes = []

        for candidate in snap.normalized.get("candidates", []):
            model_id = candidate.get("model_id", "")
            provider_id = candidate.get("provider_id", "")

            # Check if LiteLLM knows this model's baseline pricing
            litellm_pricing = self.litellm.get(model_id)

            # Dell's deal price vs LiteLLM baseline
            dell_cost = candidate.get("estimated_cost_usd")
            baseline_cost = litellm_pricing.input_cost_per_million if litellm_pricing else None

            # Create route
            route = DealRoute(
                route_id=f"dell:{provider_id}:{model_id}",
                model_id=model_id,
                provider_id=provider_id,
                deal_score=candidate.get("score", 0),
                litellm_pricing=litellm_pricing,
                fixed_cost_usd=dell_cost,
                created_at=utc_now(),
                source="dell_deal" if dell_cost else "litellm_baseline",
            )
            routes.append(route)

        return routes

    def create_routes_from_litellm(self, model_ids: list[str] | None = None) -> list[DealRoute]:
        """Create routes from LiteLLM's model pricing data."""
        litellm_routes = self.litellm.to_routes(model_ids)
        routes = []
        for lr in litellm_routes:
            pricing = self.litellm.get(lr["model_id"])
            route = DealRoute(
                route_id=lr["route_id"],
                model_id=lr["model_id"],
                provider_id=lr["provider_id"],
                deal_score=0.5,  # baseline score
                litellm_pricing=pricing,
                fixed_cost_usd=None,  # use per-token pricing
                created_at=utc_now(),
                source="litellm_baseline",
            )
            routes.append(route)
        return routes

    def to_hotswap_routes(self, deal_routes: list[DealRoute]) -> list[Route]:
        """Convert DealRoutes to QDW HotSwap Routes."""
        routes = []
        for dr in deal_routes:
            # Prefer Dell's fixed cost if available, otherwise use LiteLLM per-token
            if dr.fixed_cost_usd is not None:
                routes.append(Route(
                    route_id=dr.route_id,
                    model_id=dr.model_id,
                    provider_id=dr.provider_id,
                    free=False,
                    fixed_request_cost_usd=dr.fixed_cost_usd,
                ))
            elif dr.litellm_pricing:
                routes.append(Route(
                    route_id=dr.route_id,
                    model_id=dr.model_id,
                    provider_id=dr.provider_id,
                    free=False,
                    input_per_m=dr.litellm_pricing.input_cost_per_million,
                    output_per_m=dr.litellm_pricing.output_cost_per_million,
                    context_tokens=dr.litellm_pricing.max_input_tokens,
                ))
            else:
                # Unknown pricing — mark as free (will be circuit-broken if wrong)
                routes.append(Route(
                    route_id=dr.route_id,
                    model_id=dr.model_id,
                    provider_id=dr.provider_id,
                    free=True,
                ))
        return routes

    def register_deal(self, deal_route: DealRoute) -> str:
        """Register a deal route in the database."""
        rid = new_id("dealroute")
        with self.db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO deal_routes(route_id, model_id, provider_id, deal_score,
                litellm_model, fixed_cost_usd, source, created_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (deal_route.route_id, deal_route.model_id, deal_route.provider_id,
                 deal_route.deal_score, deal_route.litellm_pricing.model_id if deal_route.litellm_pricing else None,
                 deal_route.fixed_cost_usd, deal_route.source, deal_route.created_at),
            )
        self.ledger.append("deal.registered", "deal_route", deal_route.route_id, {
            "model_id": deal_route.model_id, "source": deal_route.source,
        })
        return rid
