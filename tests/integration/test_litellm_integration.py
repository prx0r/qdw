"""Tests for LiteLLM integration + Dell → API → Router pipeline."""

from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.federation.litellm_registry import LiteLLMRegistry, ModelPricing
from qdw.federation.litellm_pipeline import DellLiteLLMPipeline, DealRoute
from qdw.hotswap.types import Route


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    d.migrate()
    fs_sql = Path("migrations/0010_federation.sql").read_text()
    with d.connect() as con:
        con.executescript(fs_sql)
    return d


class TestLiteLLMRegistry:
    def test_load_pricing(self) -> None:
        registry = LiteLLMRegistry()
        count = registry.load()
        assert count > 0, "No models loaded"

    def test_get_model(self) -> None:
        registry = LiteLLMRegistry()
        registry.load()
        # Find any model with pricing
        models = registry.search("gpt", limit=1)
        assert len(models) >= 1
        assert models[0].input_cost_per_token > 0

    def test_cheapest_models(self) -> None:
        registry = LiteLLMRegistry()
        registry.load()
        cheapest = registry.cheapest(limit=3)
        assert len(cheapest) == 3
        # Cheapest should have lowest input cost
        for i in range(len(cheapest) - 1):
            assert cheapest[i].input_cost_per_token <= cheapest[i + 1].input_cost_per_token

    def test_to_routes(self) -> None:
        registry = LiteLLMRegistry()
        registry.load()
        routes = registry.to_routes(["gpt-4o"])
        assert len(routes) == 1
        assert routes[0]["model_id"] == "gpt-4o"
        assert routes[0]["input_per_m"] > 0

    def test_model_cost_estimation(self) -> None:
        pricing = ModelPricing("test", 0.005, 0.015)
        cost = pricing.estimate_cost(1000, 500)
        assert cost == 0.005 * 1000 + 0.015 * 500


class TestDellLiteLLMPipeline:
    def test_find_deal_routes(self, db: Database) -> None:
        ledger = Ledger(db)
        litellm = LiteLLMRegistry()
        pipeline = DellLiteLLMPipeline(db, ledger, litellm)

        dell_response = {
            "schema_version": "qdw-federation-resource/1", "candidates": [
                {"offer_id": "o1", "provider_id": "openai", "model_id": "gpt-4o",
                 "score": 0.9, "input_per_m": 0.005, "output_per_m": 0.015, "estimated_cost": 0.03},
            ],
            "alternatives": [],
            "recommended": {"offer_id": "o1", "provider_id": "openai", "model_id": "gpt-4o", "score": 0.9},
            "excluded": [],
            "decision": {"status": "RESOLVED", "method": "dell"},
        }
        routes = pipeline.find_deal_routes(dell_response)
        assert len(routes) == 1
        # When LiteLLM knows the model, it uses per-token pricing (source = dell_deal but pricing from litellm)
        # When LiteLLM doesn't know, it uses fixed cost
        assert routes[0].model_id == "gpt-4o"

    def test_litellm_baseline_routes(self) -> None:
        litellm = LiteLLMRegistry()
        litellm.load()
        pipeline = DellLiteLLMPipeline(None, None, litellm)
        routes = pipeline.create_routes_from_litellm(["gpt-4o"])
        assert len(routes) == 1
        assert routes[0].source == "litellm_baseline"
        assert routes[0].litellm_pricing is not None

    def test_to_hotswap_routes_with_fixed_cost(self) -> None:
        litellm = LiteLLMRegistry()
        pipeline = DellLiteLLMPipeline(None, None, litellm)
        deal = DealRoute(
            route_id="r1", model_id="m", provider_id="p",
            deal_score=0.9, litellm_pricing=None,
            fixed_cost_usd=0.03, created_at="now", source="dell",
        )
        routes = pipeline.to_hotswap_routes([deal])
        assert len(routes) == 1
        assert routes[0].fixed_request_cost_usd == 0.03

    def test_to_hotswap_routes_with_litellm_pricing(self) -> None:
        litellm = LiteLLMRegistry()
        litellm.load()
        pipeline = DellLiteLLMPipeline(None, None, litellm)
        pricing = litellm.get("gpt-4o")
        deal = DealRoute(
            route_id="r1", model_id="gpt-4o", provider_id="openai",
            deal_score=0.5, litellm_pricing=pricing,
            fixed_cost_usd=None, created_at="now", source="litellm",
        )
        routes = pipeline.to_hotswap_routes([deal])
        assert len(routes) == 1
        assert routes[0].input_per_m == pricing.input_cost_per_million

    def test_register_deal(self, db: Database) -> None:
        ledger = Ledger(db)
        pipeline = DellLiteLLMPipeline(db, ledger, LiteLLMRegistry())
        deal = DealRoute(
            route_id="r1", model_id="m", provider_id="p",
            deal_score=0.9, litellm_pricing=None,
            fixed_cost_usd=0.03, created_at="now", source="dell",
        )
        rid = pipeline.register_deal(deal)
        assert rid.startswith("dealroute_")

    def test_full_dell_to_hotswap_flow(self, db: Database) -> None:
        """Full flow: Dell response → deal routes → HotSwap routes."""
        ledger = Ledger(db)
        litellm = LiteLLMRegistry()
        litellm.load()
        pipeline = DellLiteLLMPipeline(db, ledger, litellm)

        # Dell finds a deal for a model LiteLLM knows
        dell_response = {
            "schema_version": "qdw-federation-resource/1", "candidates": [
                {"offer_id": "o1", "provider_id": "openai", "model_id": "gpt-4o",
                 "score": 0.9, "estimated_cost": 0.03},
            ],
            "alternatives": [],
            "recommended": {"offer_id": "o1", "provider_id": "openai", "model_id": "gpt-4o", "score": 0.9},
            "excluded": [],
            "decision": {"status": "RESOLVED", "method": "dell"},
        }

        # Step 1: Find deal routes
        deal_routes = pipeline.find_deal_routes(dell_response)
        assert len(deal_routes) == 1

        # Step 2: Convert to HotSwap routes
        hotswap_routes = pipeline.to_hotswap_routes(deal_routes)
        assert len(hotswap_routes) == 1
        # Dell's fixed cost takes precedence over LiteLLM per-token
        assert hotswap_routes[0].fixed_request_cost_usd == 0.03

        # Step 3: Register in database
        pipeline.register_deal(deal_routes[0])

        # Step 4: Verify HotSwap can use it
        from qdw.hotswap.router import HotSwapRouter
        from qdw.hotswap.types import TaskSpec
        router = HotSwapRouter()
        plan = router.plan(TaskSpec("t1", "coding", quality_floor=0.3), hotswap_routes)
        assert plan.primary is not None
        assert plan.primary.route.model_id == "gpt-4o"
