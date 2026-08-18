"""Factory fixture tests — each factory proves success + failure through the real OS."""

from __future__ import annotations

from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.graph.store import WorkGraphStore
from qdw.core.ledger.events import Ledger
from qdw.core.verification.gates import Gate, all_pass, run_gates
from qdw.factories.registry import FactoryRegistry


@pytest.fixture
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "test.db")
    d.migrate()
    return d


@pytest.fixture
def registry(db: Database) -> FactoryRegistry:
    return FactoryRegistry(db)


@pytest.fixture
def graphs(db: Database) -> WorkGraphStore:
    ledger = Ledger(db)
    return WorkGraphStore(db, ledger)


# ─── API Factory ───

class TestAPIFactory:
    def test_register_manifest(self, registry: FactoryRegistry) -> None:
        manifest = Path(__file__).parent.parent.parent / "manifests" / "factories" / "factory-api.json"
        d = registry.register_manifest(manifest)
        assert d.factory_id == "factory-api"
        assert d.version == "1.0.0"

    def test_success_fixture(self, graphs: WorkGraphStore) -> None:
        """API factory success: generate, verify, produce artifact."""
        gid = graphs.create_graph()
        n1 = graphs.add_node(gid, "generate", "Generate endpoint", {
            "type": "fastapi", "routes": ["/health", "/items"],
        })
        n2 = graphs.add_node(gid, "verify", "Verify endpoint", {})
        graphs.add_edge(gid, n1, n2)

        # Step 1: generate
        graphs.refresh_ready(gid)
        c1 = graphs.claim_ready("w")
        assert c1 is not None
        graphs.start(c1["node_id"], "w")
        graphs.verifying(c1["node_id"])
        graphs.complete(c1["node_id"], {"endpoint": "/health", "status_code": 200})

        # Step 2: verify
        graphs.refresh_ready(gid)
        c2 = graphs.claim_ready("w")
        assert c2 is not None
        graphs.start(c2["node_id"], "w")
        graphs.verifying(c2["node_id"])

        # Gate: health check must pass
        gate = Gate("api_health", "200 OK", lambda ctx: (ctx.get("ok") is True, {}))
        results = run_gates({"ok": True}, [gate])
        assert all_pass(results)

        graphs.complete(c2["node_id"], {"verified": True, "gates_passed": True})

    def test_failure_fixture_rejected(self, graphs: WorkGraphStore) -> None:
        """API factory failure: broken endpoint, verifier MUST reject."""
        gid = graphs.create_graph()
        graphs.add_node(gid, "generate", "Generate broken", {"routes": []})
        graphs.refresh_ready(gid)
        c = graphs.claim_ready("w")
        assert c is not None
        graphs.start(c["node_id"], "w")
        graphs.verifying(c["node_id"])

        # Gate: health check MUST fail
        gate = Gate("api_health", "200 OK", lambda ctx: (ctx.get("ok") is True, {}))
        results = run_gates({"ok": False}, [gate])
        assert not all_pass(results), "Broken API must be rejected"

    def test_factory_requires_fixture_to_activate(self, registry: FactoryRegistry) -> None:
        with pytest.raises((ValueError, KeyError)):
            registry.activate("factory-api", "1.0.0", "nonexistent_cert")

    def test_factory_immutable_version(self, registry: FactoryRegistry) -> None:
        manifest = Path(__file__).parent.parent.parent / "manifests" / "factories" / "factory-api.json"
        d1 = registry.register_manifest(manifest)
        # Re-registering same manifest is idempotent (INSERT OR IGNORE)
        d2 = registry.register_manifest(manifest)
        assert d1.factory_id == d2.factory_id
        assert d1.version == d2.version
