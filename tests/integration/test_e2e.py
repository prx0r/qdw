"""Integration test — canonical QDW E2E flow.

world → intelligence → ideas → factory → product
This is the most important test in QDW.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.human.queue import HumanQueue
from qdw.ideas.pipeline import IdeaReviewPipeline
from qdw.ideas.service import IdeaService
from qdw.intelligence.opportunities import OpportunityStore, OpportunitySynthesizer
from qdw.intelligence.painfinder import PainFinder
from qdw.intelligence.stack_oracle import StackOracle
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
        """Canonical E2E: source observation → pain → opportunity → idea → product."""
        # 1. Record a source observation
        result = SourceResult.success("hackernews", "forum", [
            {"id": 1, "title": "I hate manually configuring MCP servers",
             "text": "It's painful and slow", "score": 50},
        ])
        obs_ids = world.record_source_result(result)
        assert len(obs_ids) == 1

        # 2. Ingest pain from observation
        painfinder = PainFinder(db, ledger)
        pain_id, cluster_id = painfinder.ingest(
            obs_ids[0], "I hate manually configuring MCP servers",
            intensity=0.8, recurrence_hint=0.7,
        )
        assert pain_id.startswith("pain")
        assert cluster_id.startswith("paincluster")

        # 3. Synthesize opportunity from pain
        opp_store = OpportunityStore(db, ledger)
        synth = OpportunitySynthesizer(db, opp_store)
        opp_id = synth.from_pain_cluster(cluster_id)
        assert opp_id.startswith("opp")

        # 4. Propose an idea
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

        # 5. Review through pipeline
        pipeline = IdeaReviewPipeline(db, ideas)
        for stage in ["DISCOVERY", "EVIDENCE_REVIEW", "ADVERSARIAL_REVIEW",
                       "PORTFOLIO_REVIEW", "ARCHITECTURE_REVIEW"]:
            decision = pipeline.review(
                idea_id, stage, passed=True,
                score={"confidence": 0.8}, reason_codes=["evidence_strong"],
                snapshot={"stage": stage},
            )
            assert decision.decision == "PASS"

        # Final stage → BUILD_READY
        decision = pipeline.review(
            idea_id, "BUILD_READY", passed=True,
            score={"confidence": 0.9}, reason_codes=["all_gates_pass"],
            snapshot={"final": True},
        )
        assert decision.decision == "BUILD_READY"

        # 6. Create product
        products = ProductRegistry(db, ledger)
        product_id = products.create(
            "MCP Config Generator", "mcp-config-gen", "cli",
            idea_id=idea_id,
        )
        assert product_id.startswith("prod")

        # 7. Record outcome
        outcome_id = products.outcome(product_id, "users", value=42.0, source="test")
        assert outcome_id.startswith("outcomeevent")

        # 8. Verify ledger chain
        ok, _, _ = ledger.verify_chain()
        assert ok is True

        # 9. Verify product passport
        passport = products.passport(product_id)
        assert passport["product"]["name"] == "MCP Config Generator"
        assert passport["idea"]["idea_id"] == idea_id
        assert len(passport["outcomes"]) == 1

    def test_world_entity_graph(self, world: WorldStore) -> None:
        """Entity relationships persist and graph correctly."""
        ent1 = world.upsert_entity("company", "Acme Corp", external_key="acme")
        ent2 = world.upsert_entity("product", "Acme Tool")
        rel_id = world.relate(ent1, "produces", ent2)
        assert rel_id.startswith("rel")

        g = world.graph(ent1)
        assert len(g["relations"]) == 1

    def test_stack_oracle_recommendation(self, db: Database, ledger: Ledger, world: WorldStore) -> None:
        """StackOracle recommends resources based on measurements."""
        stack = StackOracle(db, ledger, world)
        stack.ensure_capability("tts", "Text-to-Speech", "voice")
        res_id = stack.register_resource("tts", "OpenAI TTS", resource_key="openai-tts")
        stack.measure(res_id, "quality", value=0.9)
        stack.measure(res_id, "cost", value=0.01)

        recs = stack.recommend("tts")
        assert len(recs) == 1
        assert recs[0].name == "OpenAI TTS"
        assert recs[0].score > 0

    def test_human_queue_lifecycle(self, db: Database, ledger: Ledger) -> None:
        """HumanQueue strict state machine: REQUESTED→APPROVED→COMPLETED."""
        hq = HumanQueue(db, ledger)
        action_id = hq.request(
            "domain_purchase", "Buy example.com",
            {"price": 12.99}, idempotency_key="domain_001",
        )
        assert action_id.startswith("human")

        hq.approve(action_id, {"approved_by": "admin"})
        hq.complete(action_id, {"purchased": True})

        pending = hq.pending()
        assert len(pending) == 0

    def test_idea_cemetery(self, db: Database, ledger: Ledger) -> None:
        """Rejected ideas go to cemetery, can be revived."""
        ideas = IdeaService(db, ledger)
        idea_id, _ = ideas.propose(
            problem_key="test problem", solution_key="test solution",
            title="Test Idea", summary="Test", customer="test", product_form="cli",
        )
        ideas.bury(idea_id, "COST_TOO_HIGH", assumptions={"cost": 1000},
                   revisit_triggers=[{"metric": "tts_cost", "below": 0.01}])

        cemetery = ideas.cemetery()
        assert len(cemetery) == 1
        assert cemetery[0]["reason_code"] == "COST_TOO_HIGH"

        ideas.revive(idea_id, {"trigger": "cost_dropped"})
        cemetery2 = ideas.cemetery()
        assert len([c for c in cemetery2 if c["status"] == "DORMANT"]) == 0

    def test_watch_triggers(self, db: Database, ledger: Ledger) -> None:
        """Watch triggers fire on matching signals."""
        from qdw.watch.service import WatchService
        watch = WatchService(db, ledger)
        watch.add("idea", "idea_001", "cost_change", {"metric": "tts_cost", "below": 0.01})

        # Non-matching signal
        hits = watch.due_for_signal({"metric": "tts_cost", "value": 0.05})
        assert len(hits) == 0

        # Matching signal
        hits = watch.due_for_signal({"metric": "tts_cost", "below": 0.01})
        assert len(hits) == 1

    def test_contractor_registration(self, db: Database, ledger: Ledger) -> None:
        """Contractors register from manifests."""
        from qdw.contractors.registry import ContractorRegistry
        cr = ContractorRegistry(db, ledger)
        manifest = Path(__file__).parent.parent.parent / "qdw_global_infra" / \
            "qdw_global_infrastructure_2026-08-18" / "manifests" / "contractors" / "qa.api.json"
        if manifest.exists():
            cid, ver = cr.register_manifest(manifest)
            assert cid == "qa.api"

    def test_distribution_registry(self, db: Database, ledger: Ledger) -> None:
        """Distribution surfaces register from manifests."""
        from qdw.publishing.registry import DistributionRegistry
        dr = DistributionRegistry(db, ledger)
        manifest = Path(__file__).parent.parent.parent / "qdw_global_infra" / \
            "qdw_global_infrastructure_2026-08-18" / "manifests" / "distributions" / "pypi.json"
        if manifest.exists():
            sid = dr.register_manifest(manifest)
            assert sid == "pypi"

    def test_proof_runner(self, tmp_path: Path) -> None:
        """VerificationRunner produces real receipts."""
        from qdw.proof.runner import VerificationRunner
        runner = VerificationRunner(tmp_path / "runs")
        receipt = runner.run("test-task", ["python3", "-c", "print('hello')"])
        assert receipt.status == "PASS"
        assert receipt.exit_code == 0
        assert receipt.stdout_sha256 != ""

        receipts = runner.load_receipts()
        assert len(receipts) == 1

    def test_test_guard_detects_fake(self, tmp_path: Path) -> None:
        """TestGuard catches assert True and empty tests."""
        from qdw.proof.test_guard import scan_test_file
        test_file = tmp_path / "test_fake.py"
        test_file.write_text("def test_fake():\n    assert True\n")
        findings = scan_test_file(test_file)
        assert any(f.code == "ASSERT_TRUE" for f in findings)

    def test_build_certificate_rejects_missing(self, tmp_path: Path) -> None:
        """BuildCertificateBuilder refuses to certify without receipts."""
        from qdw.proof.certificate import BuildCertificateBuilder
        from qdw.proof.runner import VerificationRunner
        runner = VerificationRunner(tmp_path / "runs")
        builder = BuildCertificateBuilder(runner)

        with pytest.raises(ValueError, match="cannot certify"):
            builder.issue(
                task_id="nonexistent",
                acceptance_spec_hash="abc",
                required_commands=[["python3", "-c", "print('ok')"]],
                required_negative_tests=[],
                artifact_paths=[],
            )
