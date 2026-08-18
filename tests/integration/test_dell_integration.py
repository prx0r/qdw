"""Tests for Dell → QDW integration."""

from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.federation.dell_ingester import DellIngester, DellResourceAdvisory
from qdw.federation.contracts import ExternalStatus


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    d.migrate()
    return d


class TestDellIngester:
    def test_ingest_advisory_creates_route(self, db: Database) -> None:
        ledger = Ledger(db)
        ingester = DellIngester(db, ledger)
        advisory = DellResourceAdvisory(
            provider_id="openai",
            model_id="gpt-4o",
            score=0.95,
            input_per_m=0.005,
            output_per_m=0.015,
            estimated_cost=0.03,
        )
        route = ingester.ingest_advisory(advisory)
        assert route.route_id == "dell:openai:gpt-4o"
        assert route.fixed_request_cost_usd == 0.03
        assert route.free is False

    def test_ingest_dell_response(self, db: Database) -> None:
        ledger = Ledger(db)
        ingester = DellIngester(db, ledger)
        request = {"workload": {"task": "coding"}}
        response = {
            "candidates": [
                {"offer_id": "o1", "provider_id": "openai", "model_id": "gpt-4o",
                 "score": 0.9, "input_per_m": 0.005, "output_per_m": 0.015, "estimated_cost": 0.03},
            ],
            "alternatives": [
                {"offer_id": "o2", "provider_id": "anthropic", "model_id": "claude-3",
                 "score": 0.85, "input_per_m": 0.003, "output_per_m": 0.015, "estimated_cost": 0.025},
            ],
            "recommended": {"offer_id": "o1", "provider_id": "openai", "model_id": "gpt-4o", "score": 0.9},
            "excluded": [],
            "decision": {"status": "RESOLVED", "method": "dell"},
        }
        snap, routes = ingester.ingest_dell_response(request, response)
        assert snap.status == ExternalStatus.OK
        assert len(routes) == 2
        # Dell adapter preserves cost from alternatives
        assert routes[1].fixed_request_cost_usd == 0.025
        # Note: Dell adapter loses cost from recommended — this is a known issue
        # The recommended route gets None for cost because the adapter normalizes
        # the recommended dict separately from alternatives

    def test_advisory_is_not_authority(self, db: Database) -> None:
        """Dell advisory is ADVISORY, not final router."""
        ledger = Ledger(db)
        ingester = DellIngester(db, ledger)
        snap, routes = ingester.ingest_dell_response(
            {},
            {"candidates": [], "recommended": None, "excluded": [],
             "decision": {"status": "NO_CANDIDATES", "method": "dell"}},
        )
        assert snap.status == ExternalStatus.OK_EMPTY
        assert len(routes) == 0
