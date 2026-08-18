"""Tests for QDW WorkGraph — atomic claims, leases, recovery, dependency ordering."""

import threading
from pathlib import Path

from qdw.core.db import Database
from qdw.core.graph.store import WorkGraphStore
from qdw.core.ledger.events import Ledger


class TestWorkGraph:
    def _make_store(self, tmp_path: Path) -> WorkGraphStore:
        db = Database(tmp_path / "test.db")
        db.migrate()
        ledger = Ledger(db)
        return WorkGraphStore(db, ledger)

    def test_create_graph(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        assert gid.startswith("graph_")

    def test_add_node_and_edge(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        n1 = store.add_node(gid, "research", "Research", {"topic": "AI"})
        n2 = store.add_node(gid, "build", "Build", {"spec": "x"})
        store.add_edge(gid, n1, n2)
        count = store.refresh_ready(gid)
        assert count == 1  # only n1 is ready (n2 blocked by n1)

    def test_dependency_blocks(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        n1 = store.add_node(gid, "task", "A", {})
        n2 = store.add_node(gid, "task", "B", {})
        n3 = store.add_node(gid, "task", "C", {})
        store.add_edge(gid, n1, n2)
        store.add_edge(gid, n1, n3)
        ready = store.refresh_ready(gid)
        assert ready == 1  # only n1 ready

    def test_self_dependency_rejected(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        n1 = store.add_node(gid, "task", "A", {})
        import pytest
        with pytest.raises(ValueError, match="self dependency"):
            store.add_edge(gid, n1, n1)

    def test_claim_ready_returns_node(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        store.add_node(gid, "task", "A", {"data": 1})
        store.refresh_ready(gid)
        claimed = store.claim_ready("worker-1")
        assert claimed is not None
        assert claimed["state"] == "LEASED"
        assert claimed["lease_owner"] == "worker-1"
        assert claimed["payload"] == {"data": 1}

    def test_claim_only_one_worker_wins(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        store.add_node(gid, "task", "A", {})
        store.refresh_ready(gid)
        c1 = store.claim_ready("worker-1")
        c2 = store.claim_ready("worker-2")
        assert c1 is not None
        assert c2 is None  # only one worker wins

    def test_start_requires_valid_lease(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        n1 = store.add_node(gid, "task", "A", {})
        store.refresh_ready(gid)
        import pytest
        with pytest.raises(RuntimeError, match="invalid lease"):
            store.start(n1, "wrong-worker")

    def test_lifecycle_happy_path(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        n1 = store.add_node(gid, "task", "A", {})
        store.refresh_ready(gid)
        claimed = store.claim_ready("w1")
        store.start(claimed["node_id"], "w1")
        store.verifying(claimed["node_id"])
        store.complete(claimed["node_id"], {"result": "ok"})
        # After completion, dependent nodes should become ready
        n2 = store.add_node(gid, "task", "B", {})
        store.add_edge(gid, n1, n2)
        ready = store.refresh_ready(gid)
        assert ready == 1  # n2 now unblocked

    def test_fail_retryable(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        store.add_node(gid, "task", "A", {}, max_retries=3)
        store.refresh_ready(gid)
        claimed = store.claim_ready("w1")
        store.start(claimed["node_id"], "w1")
        # First fail: attempt_count=1 < max_retries=3 → RETRY_WAIT
        state = store.fail(claimed["node_id"], {"error": "timeout"}, retryable=True)
        assert state == "RETRY_WAIT"
        # Claim again (attempt_count becomes 2) and fail again
        store.refresh_ready(gid)
        claimed2 = store.claim_ready("w1")
        store.start(claimed2["node_id"], "w1")
        state2 = store.fail(claimed2["node_id"], {"error": "timeout"}, retryable=True)
        assert state2 == "RETRY_WAIT"
        # Claim again (attempt_count becomes 3) and fail again
        store.refresh_ready(gid)
        claimed3 = store.claim_ready("w1")
        store.start(claimed3["node_id"], "w1")
        state3 = store.fail(claimed3["node_id"], {"error": "timeout"}, retryable=True)
        # attempt_count=3 >= max_retries=3 → FAILED
        assert state3 == "FAILED"

    def test_fail_non_retryable(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        store.add_node(gid, "task", "A", {})
        store.refresh_ready(gid)
        claimed = store.claim_ready("w1")
        store.start(claimed["node_id"], "w1")
        state = store.fail(claimed["node_id"], {"error": "fatal"}, retryable=False)
        assert state == "FAILED"

    def test_concurrent_claim_exactly_one_winner(self, tmp_path: Path) -> None:
        """Real concurrent execution — two threads race to claim the same node."""
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        store.add_node(gid, "task", "Contested", {})
        store.refresh_ready(gid)

        results = []

        def claim(worker_id: str) -> None:
            c = store.claim_ready(worker_id)
            results.append((worker_id, c is not None))

        t1 = threading.Thread(target=claim, args=("w1",))
        t2 = threading.Thread(target=claim, args=("w2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        winners = [r for r in results if r[1]]
        assert len(winners) == 1, f"Expected exactly 1 winner, got {len(winners)}: {results}"

    def test_reclaim_stale_lease(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime, timedelta
        store = self._make_store(tmp_path)
        gid = store.create_graph()
        store.add_node(gid, "task", "A", {})
        store.refresh_ready(gid)
        claimed = store.claim_ready("w1", lease_seconds=1)
        # Simulate lease expiry by backdating
        expired = datetime.now(UTC) - timedelta(seconds=10)
        expired_s = expired.isoformat().replace("+00:00", "Z")
        with store.db.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "UPDATE work_nodes SET lease_until=? WHERE node_id=?",
                (expired_s, claimed["node_id"]),
            )
            con.execute("COMMIT")
        reclaimed = store.reclaim_stale()
        assert reclaimed == 1
        # Node should be READY again
        with store.db.connect() as con:
            row = con.execute("SELECT state FROM work_nodes WHERE node_id=?", (claimed["node_id"],)).fetchone()
            assert row["state"] == "READY"
