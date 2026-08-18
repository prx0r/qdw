"""Dell → QDW integration: resource advisory into HotSwap cost model.

Dell emits ResourceAdvisory with provider/model evidence.
QDW ingests these as Route candidates with fixed_request_cost_usd.
HotSwap decides whether to use them based on budget constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qdw.core import hash_object, utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.federation.contracts import ExternalSnapshot, ExternalStatus, FederatedRef
from qdw.federation.dell_adapter import DellFederationAdapter
from qdw.hotswap.types import Route


@dataclass(frozen=True)
class DellResourceAdvisory:
    provider_id: str
    model_id: str
    score: float
    input_per_m: float
    output_per_m: float
    estimated_cost: float
    reliability: float = 0.99
    evidence: dict[str, Any] | None = None


class DellIngester:
    """Ingests Dell resource advisories into QDW as Route candidates."""

    def __init__(self, db: Database, ledger: Ledger):
        self.db = db
        self.ledger = ledger
        self.adapter = DellFederationAdapter()

    def ingest_advisory(self, advisory: DellResourceAdvisory) -> Route:
        """Convert Dell advisory into a QDW Route with fixed cost."""
        return Route(
            route_id=f"dell:{advisory.provider_id}:{advisory.model_id}",
            model_id=advisory.model_id,
            provider_id=advisory.provider_id,
            free=False,
            fixed_request_cost_usd=advisory.estimated_cost,
            input_per_m=advisory.input_per_m,
            output_per_m=advisory.output_per_m,
            reliability=advisory.reliability,
        )

    def ingest_dell_response(self, request: dict, response: dict) -> tuple[ExternalSnapshot, list[Route]]:
        """Ingest a full Dell API response."""
        snap, advisory = self.adapter.normalize(request, response)

        routes = []
        for cand in snap.normalized.get("candidates", []):
            route = Route(
                route_id=f"dell:{cand.get('provider_id', 'unknown')}:{cand.get('model_id', 'unknown')}",
                model_id=cand.get("model_id", "unknown"),
                provider_id=cand.get("provider_id", "unknown"),
                free=cand.get("free", False),
                fixed_request_cost_usd=cand.get("estimated_cost_usd"),
                input_per_m=cand.get("input_per_m"),
                output_per_m=cand.get("output_per_m"),
                reliability=cand.get("reliability"),
            )
            routes.append(route)

        return snap, routes
