"""Adversarial tests — proving critical findings are fixed.

These tests MUST fail against unfixed code and PASS against fixed code.
Each test targets a specific finding from the peer review.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.graph.store import WorkGraphStore
from qdw.core.ledger.events import Ledger
from qdw.factories.registry import FactoryRegistry
from qdw.products.registry import ProductRegistry


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    d.migrate()
    return d


@pytest.fixture
def ledger(db: Database) -> Ledger:
    return Ledger(db)


class TestFactoryActivationEvidence:
    """QDW-CUR-003: Factory activation vulnerable to evidence substitution."""

    def test_cannot_activate_with_unrelated_gate(self, db: Database) -> None:
        """A passing gate from unrelated work cannot activate a factory."""
        reg = FactoryRegistry(db)
        manifest = Path(__file__).parent.parent.parent / "manifests" / "factories" / "factory-api.json"
        reg.register_manifest(manifest)

        # Create an unrelated passing gate
        with db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO gate_results(gate_result_id, gate_id, passed, result_hash, detail_json, created_at)
                VALUES('gate_unrelated', 'unrelated_test', 1, 'abc', '{}', datetime('now'))""",
            )

        # Attempt activation with unrelated gate — MUST fail
        with pytest.raises(ValueError, match="does not identify a factory"):
            reg.activate("factory-api", "1.0.0", "gate_unrelated")

    def test_cannot_activate_with_wrong_version(self, db: Database) -> None:
        """A gate for factory-api@1.0.0 cannot activate factory-api@2.0.0."""
        reg = FactoryRegistry(db)
        manifest = Path(__file__).parent.parent.parent / "manifests" / "factories" / "factory-api.json"
        reg.register_manifest(manifest)

        # Create gate for wrong version
        detail = json.dumps({"factory_id": "factory-api", "factory_version": "9.9.9"})
        with db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO gate_results(gate_result_id, gate_id, passed, result_hash, detail_json, created_at)
                VALUES('gate_wrong_ver', 'fixture_test', 1, 'abc', ?, datetime('now'))""",
                (detail,),
            )

        # Try to activate v1.0.0 with gate for v9.9.9 — MUST fail
        with pytest.raises(ValueError):
            reg.activate("factory-api", "1.0.0", "gate_wrong_ver")


class TestProductReleaseCertificate:
    """QDW-CUR-004: Product release accepts arbitrary certificate ID."""

    def test_cannot_release_with_unrelated_cert(self, db: Database, ledger: Ledger) -> None:
        """A certificate from unrelated work cannot release a product."""
        products = ProductRegistry(db, ledger)
        pid = products.create("Test", "test", "cli")

        # Create unrelated passing gate
        with db.tx(immediate=True) as con:
            con.execute(
                """INSERT INTO gate_results(gate_result_id, gate_id, passed, result_hash, detail_json, created_at)
                VALUES('cert_unrelated', 'unrelated', 1, 'abc', '{}', datetime('now'))""",
            )

        # Attempt release with unrelated cert — MUST fail
        with pytest.raises(ValueError, match="does not identify a product"):
            products.release(pid, "cert_unrelated")


class TestMigrationImmutability:
    """QDW-CUR-009/010: Migration drift detection."""

    def test_migration_content_hash_recorded(self, db: Database) -> None:
        """Applied migrations record content hash."""
        with db.connect() as con:
            rows = con.execute("SELECT version, content_hash FROM schema_versions ORDER BY version").fetchall()
            for r in rows:
                assert r["content_hash"] is not None, f"migration {r['version']} has no content_hash"

    def test_migration_drift_detected(self, db: Database, tmp_path: Path) -> None:
        """Changing an applied migration file is detected."""
        from qdw.core.migrations import migrate
        # First apply
        migrate(db, tmp_path)
        # Create a migration
        mdir = tmp_path / "migrations"
        mdir.mkdir()
        (mdir / "9999_test.sql").write_text("SELECT 1;")
        migrate(db, mdir)
        # Now change the file
        (mdir / "9999_test.sql").write_text("SELECT 2;")
        # Re-running should detect drift
        with pytest.raises(ValueError, match="MIGRATION_DRIFT"):
            migrate(db, mdir)


class TestUnknownEconomics:
    """UNKNOWN cost is not zero cost."""

    def test_unknown_cost_preserved_in_candidate(self) -> None:
        """None expected_cost stays None, not coerced to 0."""
        from qdw.core.graph.scheduler import Candidate, net_value
        c = Candidate(node_id="n", expected_value=5.0, expected_cost=None)
        assert c.expected_cost is None
        # net_value returns None when cost is unknown
        assert net_value(c) is None

    def test_unknown_value_preserved_in_candidate(self) -> None:
        """None expected_value stays None, not coerced to 0."""
        from qdw.core.graph.scheduler import Candidate, net_value
        c = Candidate(node_id="n", expected_value=None, expected_cost=1.0)
        assert c.expected_value is None
        assert net_value(c) is None

    def test_unknown_economics_eligible_but_not_rankable(self) -> None:
        """Nodes with unknown economics are eligible but ranked below known-positive."""
        from qdw.core.graph.scheduler import Candidate, choose
        known = Candidate(node_id="known", expected_value=10.0, expected_cost=1.0)
        unknown = Candidate(node_id="unknown", expected_value=None, expected_cost=None)
        chosen = choose([known, unknown])
        assert chosen is not None
        assert chosen.node_id == "known"

    def test_only_unknown_economics_still_eligible(self) -> None:
        """When only unknown-economics nodes exist, one is still chosen."""
        from qdw.core.graph.scheduler import Candidate, choose
        u1 = Candidate(node_id="u1", expected_value=None, expected_cost=None)
        u2 = Candidate(node_id="u2", expected_value=None, expected_cost=None, urgency=1.0)
        chosen = choose([u1, u2])
        assert chosen is not None
        assert chosen.node_id == "u2"  # higher urgency


class TestWorkGraphAtomicity:
    """State + provenance should be atomic."""

    def test_claim_and_ledger_both_exist(self, db: Database, ledger: Ledger) -> None:
        """After claiming, both node state and ledger event exist."""
        graphs = WorkGraphStore(db, ledger)
        gid = graphs.create_graph()
        graphs.add_node(gid, "task", "A", {})
        graphs.refresh_ready(gid)
        claimed = graphs.claim_ready("w1")
        assert claimed is not None

        # Verify both node state and ledger event exist
        with db.connect() as con:
            node = con.execute(
                "SELECT state FROM work_nodes WHERE node_id=?",
                (claimed["node_id"],),
            ).fetchone()
            assert node["state"] == "LEASED"

            events = con.execute(
                "SELECT * FROM ledger_events WHERE subject_id=?",
                (claimed["node_id"],),
            ).fetchall()
            assert len(events) >= 1  # At least the claim event
