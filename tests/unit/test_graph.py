"""Tests for WorkGraph — freeze, claim, lifecycle."""

from pathlib import Path

import pytest

from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.core.graph.store import WorkGraphStore


@pytest.fixture
def env(tmp_path: Path):
    db = Database(str(tmp_path / "db.db"))
    db.migrate()
    ledger = Ledger(db)
    store = WorkGraphStore(db, ledger)
    return db, ledger, store


class TestWorkGraph:
    def test_create_graph(self, env) -> None:
        _, _, store = env
        gid = store.create_graph()
        assert gid.startswith("graph_")

    def test_add_node_and_edge(self, env) -> None:
        _, _, store = env
        gid = store.create_graph()
        n1 = store.add_node(gid, "task", "A", {})
        n2 = store.add_node(gid, "task", "B", {})
        store.add_edge(gid, n1, n2)

    def test_self_dependency_rejected(self, env) -> None:
        _, _, store = env
        gid = store.create_graph()
        n1 = store.add_node(gid, "task", "A", {})
        with pytest.raises(ValueError, match="self dependency"):
            store.add_edge(gid, n1, n1)

    def test_cycle_detected_at_add_edge(self, env) -> None:
        _, _, store = env
        gid = store.create_graph()
        n1 = store.add_node(gid, "task", "A", {})
        n2 = store.add_node(gid, "task", "B", {})
        store.add_edge(gid, n1, n2)
        # This creates a cycle: n2 → n1 → n2
        with pytest.raises(ValueError, match="cycle"):
            store.add_edge(gid, n2, n1)

    def test_claim_requires_freeze(self, env) -> None:
        _, _, store = env
        gid = store.create_graph()
        store.add_node(gid, "task", "A", {})
        # DRAFT graph returns None (no eligible nodes)
        c = store.claim_ready("w1")
        assert c is None

    def test_claim_one_winner(self, env) -> None:
        _, _, store = env
        gid = store.create_graph()
        store.add_node(gid, "task", "A", {})
        store.freeze(gid)
        store.refresh_ready(gid)
        c1 = store.claim_ready("w1")
        c2 = store.claim_ready("w2")
        assert c1 is not None
        assert c2 is None

    def test_complete_node(self, env) -> None:
        _, _, store = env
        gid = store.create_graph()
        n1 = store.add_node(gid, "task", "A", {})
        store.freeze(gid)
        store.refresh_ready(gid)
        c = store.claim_ready("w1")
        store.start(c["node_id"], "w1")
        store.verifying(c["node_id"])
        store.complete(c["node_id"], {"result": "ok"})

    def test_fail_retryable(self, env) -> None:
        _, _, store = env
        gid = store.create_graph()
        store.add_node(gid, "task", "A", {}, max_retries=2)
        store.freeze(gid)
        store.refresh_ready(gid)
        c = store.claim_ready("w1")
        store.start(c["node_id"], "w1")
        state = store.fail(c["node_id"], {"error": "timeout"}, retryable=True)
        assert state == "RETRY_WAIT"

    def test_fail_terminal(self, env) -> None:
        _, _, store = env
        gid = store.create_graph()
        store.add_node(gid, "task", "A", {})
        store.freeze(gid)
        store.refresh_ready(gid)
        c = store.claim_ready("w1")
        store.start(c["node_id"], "w1")
        state = store.fail(c["node_id"], {"error": "fatal"}, retryable=False)
        assert state == "FAILED"

    def test_concurrent_claim_one_winner(self, env) -> None:
        import threading
        _, _, store = env
        gid = store.create_graph()
        store.add_node(gid, "task", "X", {})
        store.freeze(gid)
        store.refresh_ready(gid)

        results = []
        def claim(wid):
            c = store.claim_ready(wid)
            results.append((wid, c is not None))

        t1 = threading.Thread(target=claim, args=("w1",))
        t2 = threading.Thread(target=claim, args=("w2",))
        t1.start(); t2.start()
        t1.join(); t2.join()

        winners = [r for r in results if r[1]]
        assert len(winners) == 1

    def test_reclaim_stale(self, env) -> None:
        from datetime import UTC, datetime, timedelta
        _, _, store = env
        gid = store.create_graph()
        store.add_node(gid, "task", "A", {})
        store.freeze(gid)
        store.refresh_ready(gid)
        c = store.claim_ready("w1", lease_seconds=1)
        # Backdate lease
        expired = (datetime.now(UTC) - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
        with store.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("UPDATE work_nodes SET lease_until=? WHERE node_id=?", (expired, c["node_id"]))
            con.execute("COMMIT")
        reclaimed = store.reclaim_stale()
        assert reclaimed >= 1
