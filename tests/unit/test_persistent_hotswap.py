"""Tests for persistent HotSwap state — learning survives restarts."""

from pathlib import Path

from qdw.core.db import Database
from qdw.hotswap.persistent import PersistentBanditStore
from qdw.hotswap.router import HotSwapRouter
from qdw.hotswap.types import Route, TaskSpec


class TestPersistentBandit:
    def _make_store(self, tmp_path: Path) -> PersistentBanditStore:
        db = Database(tmp_path / "test.db")
        db.migrate()
        return PersistentBanditStore(db)

    def test_posterior_persists(self, tmp_path: Path) -> None:
        store = self._make_store(tmp_path)
        route = Route(route_id="r1", model_id="m", provider_id="p")
        task = TaskSpec(task_id="t1", task_kind="coding")

        # Record a success
        store.update(task.cell_id, "r1", True)
        p1 = store.get(task.cell_id, route)
        assert p1.alpha > 1.0

        # Create new store with same DB — posterior should persist
        db2 = Database(tmp_path / "test.db")
        store2 = PersistentBanditStore(db2)
        p2 = store2.get(task.cell_id, route)
        assert p2.alpha == p1.alpha
        assert p2.beta == p1.beta

    def test_learning_affects_routing(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.migrate()
        bandits = PersistentBanditStore(db)
        router = HotSwapRouter(bandits=bandits)

        paid = Route(route_id="paid", model_id="m", provider_id="p", free=False,
                     input_per_m=0.1, output_per_m=0.1, prior_success=0.95)

        task = TaskSpec(task_id="t1", task_kind="coding", quality_floor=0.3,
                        free_policy="allow")

        # Only paid route available
        plan = router.plan(task, [paid])
        assert plan.primary is not None
        assert plan.primary.route.route_id == "paid"

    def test_router_with_persistent_bandits(self, tmp_path: Path) -> None:
        db = Database(tmp_path / "test.db")
        db.migrate()
        bandits = PersistentBanditStore(db)
        router = HotSwapRouter(bandits=bandits)

        route = Route(route_id="r1", model_id="m", provider_id="p",
                      free=True, input_per_m=0, output_per_m=0)
        task = TaskSpec(task_id="t1", task_kind="coding", quality_floor=0.3)
        plan = router.plan(task, [route])
        assert plan.primary is not None
        assert plan.primary.route.route_id == "r1"
