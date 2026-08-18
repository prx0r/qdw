"""Tests for Estate routing absorption + Forge client + full pipeline."""

from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.hotswap.types import Route, TaskSpec
from qdw.hotswap.estate_routing import (
    historical_plan, ClusterRouter, cascade_plan, RouteAssessment,
)
from qdw.federation.forge_client import ForgeClient


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    d.migrate()
    return d


class TestHistoricalRouting:
    def test_ranks_by_cpvs(self) -> None:
        """Routes with known cost-per-verified-success rank first."""
        routes = [
            Route("fast_cheap", "m", "p", fixed_request_cost_usd=0.01),
            Route("slow_expensive", "m", "p", fixed_request_cost_usd=0.10),
        ]
        assessments = {
            "fast_cheap": {"success_mean": 0.95, "mean_cost_usd": 0.01},
            "slow_expensive": {"success_mean": 0.80, "mean_cost_usd": 0.10},
        }
        task = TaskSpec("t1", "coding", quality_floor=0.5)
        result = historical_plan(task, routes, assessments)
        # fast_cheap has CPVS=0.01/0.95=0.0105, slow_expensive has CPVS=0.10/0.80=0.125
        # Lower CPVS is better, so fast_cheap ranks first
        assert result[0].route_id == "fast_cheap"
        assert result[0].eligible is True

    def test_unknown_cpvs_ranks_later(self) -> None:
        """Routes without known CPVS rank after known ones."""
        routes = [
            Route("known", "m", "p", fixed_request_cost_usd=0.05),
            Route("unknown", "m", "p", fixed_request_cost_usd=0.03),
        ]
        assessments = {
            "known": {"success_mean": 0.90, "mean_cost_usd": 0.05},
            # unknown has no assessment
        }
        task = TaskSpec("t1", "coding", quality_floor=0.5)
        result = historical_plan(task, routes, assessments)
        # known has CPVS, unknown doesn't — known ranks first
        assert result[0].route_id == "known"

    def test_quality_floor_filters(self) -> None:
        routes = [Route("r1", "m", "p"), Route("r2", "m", "p")]
        assessments = {
            "r1": {"success_mean": 0.3, "mean_cost_usd": 0.05},  # below floor
            "r2": {"success_mean": 0.9, "mean_cost_usd": 0.03},  # above floor
        }
        task = TaskSpec("t1", "coding", quality_floor=0.5)
        result = historical_plan(task, routes, assessments)
        # r2 is above floor and has better CPVS, r1 is below floor
        assert result[0].route_id == "r2"
        assert result[0].eligible is True
        assert result[1].eligible is False


class TestClusterRouting:
    def test_fit_and_plan(self) -> None:
        """Cluster router learns from examples and routes new objectives."""
        router = ClusterRouter(k=2, dims=32)
        examples = [
            ("coding task", "r1", True, 0.01),
            ("coding task", "r1", True, 0.02),
            ("research task", "r2", True, 0.05),
            ("research task", "r2", True, 0.03),
        ]
        router.fit(examples)
        assert len(router.centroids) == 2

        task = TaskSpec("t1", "coding", quality_floor=0.5)
        routes = [Route("r1", "m", "p"), Route("r2", "m", "p")]
        result = router.plan(task, routes)
        assert len(result) == 2
        # r1 should be preferred for coding tasks
        assert result[0].route_id == "r1"

    def test_empty_examples_falls_back_to_historical(self) -> None:
        router = ClusterRouter()
        task = TaskSpec("t1", "coding", quality_floor=0.5)
        routes = [Route("r1", "m", "p")]
        result = router.plan(task, routes)
        assert len(result) == 1  # Falls back to historical


class TestCascadeRouting:
    def test_cascade_returns_cpvs_order(self) -> None:
        routes = [
            Route("fast", "m", "p", fixed_request_cost_usd=0.01),
            Route("slow", "m", "p", fixed_request_cost_usd=0.10),
        ]
        task = TaskSpec("t1", "coding", quality_floor=0.5)
        result = cascade_plan(task, routes)
        assert len(result) == 2


class TestForgeClient:
    def test_lease_creates_record(self, db: Database) -> None:
        ledger = Ledger(db)
        client = ForgeClient(db, ledger)
        lease = client.lease({
            "asset_id": "cap-a", "version": "1",
            "capability": "coding", "max_spend_usd": 0.50,
        })
        assert lease["lease_id"].startswith("lease_")
        assert lease["token"].startswith("tok_")

    def test_invoke_returns_result(self, db: Database) -> None:
        ledger = Ledger(db)
        client = ForgeClient(db, ledger)
        result = client.invoke({
            "lease_token": "tok_xxx", "capability": "coding",
            "arguments": {"prompt": "write code"},
        })
        assert result["status"] == "SUCCEEDED_UNVERIFIED"
        assert result["output_hash"] != ""

    def test_bind_certificate(self, db: Database) -> None:
        ledger = Ledger(db)
        client = ForgeClient(db, ledger)
        client.bind_certificate("inv_001", {
            "certificate_id": "cert_001", "passed": True,
        })
        with db.connect() as con:
            row = con.execute(
                "SELECT * FROM forge_invocation_certs WHERE invocation_id=?",
                ("inv_001",),
            ).fetchone()
            assert row is not None
            assert row["status"] == "BOUND"

    def test_full_forge_flow(self, db: Database) -> None:
        """Lease → invoke → verify → certificate."""
        ledger = Ledger(db)
        client = ForgeClient(db, ledger)

        # 1. Lease
        lease = client.lease({"asset_id": "cap-a", "version": "1", "capability": "coding"})
        assert lease["token"].startswith("tok_")

        # 2. Invoke
        result = client.invoke({
            "lease_token": lease["token"], "asset_id": "cap-a", "version": "1",
            "capability": "coding", "arguments": {"prompt": "test"},
        })
        assert result["status"] == "SUCCEEDED_UNVERIFIED"

        # 3. Bind certificate
        client.bind_certificate(result["invocation_id"], {
            "certificate_id": "cert_001", "passed": True,
        })

        # 4. Verify
        with db.connect() as con:
            cert = con.execute(
                "SELECT * FROM forge_invocation_certs WHERE invocation_id=?",
                (result["invocation_id"],),
            ).fetchone()
            assert cert is not None
            assert cert["status"] == "BOUND"
