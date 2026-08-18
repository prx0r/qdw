"""E2E tests — source observation through product creation."""

from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.intelligence.opportunities import OpportunityStore, OpportunitySynthesizer
from qdw.intelligence.painfinder import PainFinder
from qdw.products.registry import ProductRegistry
from qdw.sources.protocol import SourceResult
from qdw.world.store import WorldStore


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    d.migrate()
    return d


@pytest.fixture
def ledger(db: Database) -> Ledger:
    return Ledger(db)


@pytest.fixture
def world(db: Database, ledger: Ledger) -> WorldStore:
    return WorldStore(db, ledger)


class TestE2EFlow:
    def test_world_to_product(self, db: Database, ledger: Ledger, world: WorldStore) -> None:
        """Source → observation → pain → opportunity → idea → product."""
        from qdw.ideas.service import IdeaService

        # 1. Source observation
        result = SourceResult.success("hackernews", "forum", [
            {"id": 1, "title": "I hate manually configuring MCP servers"},
        ])
        obs_ids = world.record_source_result(result)
        assert len(obs_ids) == 1

        # 2. Ingest pain
        painfinder = PainFinder(db, ledger)
        pain_id, cluster_id = painfinder.ingest(
            obs_ids[0], "I hate manually configuring MCP servers",
            intensity=0.8, recurrence_hint=0.7,
        )
        assert pain_id.startswith("pain")

        # 3. Synthesize opportunity
        opp_store = OpportunityStore(db, ledger)
        synth = OpportunitySynthesizer(db, opp_store)
        opp_id = synth.from_pain_cluster(cluster_id)
        assert opp_id.startswith("opp")

        # 4. Propose idea
        ideas = IdeaService(db, ledger)
        idea_id, created = ideas.propose(
            problem_key="mcp configuration manual",
            solution_key="automated mcp config generator",
            title="MCP Config Generator",
            summary="Auto-generate MCP server configs from API specs",
            customer="developers",
            product_form="cli",
            opportunity_id=opp_id,
        )
        assert created is True

        # 5. Create product
        products = ProductRegistry(db, ledger)
        product_id = products.create("MCP Config Generator", "mcp-config-gen", "cli", idea_id=idea_id)
        assert product_id.startswith("prod")

        # 6. Record outcome
        outcome_id = products.outcome(product_id, "users", value=42.0, source="test")
        assert outcome_id.startswith("outcomeevent")

        # 7. Verify ledger chain
        ok, _, _ = ledger.verify_chain()
        assert ok is True

        # 8. Verify product passport
        passport = products.passport(product_id)
        assert passport["product"]["name"] == "MCP Config Generator"
        assert passport["idea"]["idea_id"] == idea_id
        assert len(passport["outcomes"]) == 1

    def test_proof_runner(self, tmp_path: Path) -> None:
        """VerificationService produces real receipts."""
        from qdw.proof.verification_service import VerificationService
        from qdw.proof.plan import VerificationPlan, VerificationCommand
        db = Database(str(tmp_path / "db.db"))
        db.migrate()
        ledger = Ledger(db)
        service = VerificationService(db, ledger, str(tmp_path / "runs"))
        plan = VerificationPlan(
            "test", "1", (VerificationCommand("x", ["python3", "-c", "print('hello')"]),),
        )
        run_id = service.execute(plan, task_id="test", cwd=tmp_path)
        record = service.run_record(run_id)
        assert record["run"]["status"] == "PASS"

    def test_test_guard_detects_fake(self, tmp_path: Path) -> None:
        """TestGuard catches assert True and empty tests."""
        from qdw.proof.test_guard import scan_test_file
        test_file = tmp_path / "test_fake.py"
        test_file.write_text("def test_fake():\n    assert True\n")
        findings = scan_test_file(test_file)
        assert any(f.code == "ASSERT_TRUE" for f in findings)

    def test_build_certificate_rejects_missing(self, tmp_path: Path) -> None:
        """BuildCertificateV2 refuses to certify without evidence."""
        from qdw.proof.verification_service import VerificationService
        from qdw.proof.certificate_v2 import BuildCertificateV2
        db = Database(str(tmp_path / "db.db"))
        db.migrate()
        ledger = Ledger(db)
        service = VerificationService(db, ledger, str(tmp_path / "runs"))
        builder = BuildCertificateV2(service)

        with pytest.raises((ValueError, KeyError)):
            builder.issue("nonexistent_run", allow_dirty=True)
