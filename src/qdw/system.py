"""QDW system — the single composition root.

All registries and services are injected here.
Interfaces (API, MCP, CLI) contain no business logic — they delegate to QDWSystem.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qdw.catalog.service import GlobalCatalog
from qdw.contractors.registry import ContractorRegistry
from qdw.core.db import Database
from qdw.core.graph.store import WorkGraphStore
from qdw.core.ledger.events import Ledger
from qdw.core.portfolio.costs import CostLedger
from qdw.core.portfolio.learning import FactoryLearning
from qdw.factories.registry import FactoryRegistry
from qdw.hotswap.persistent import PersistentBanditStore
from qdw.hotswap.quota import QuotaLedger
from qdw.hotswap.router import HotSwapRouter
from qdw.hotswap.types import Route
from qdw.human.queue import HumanQueue
from qdw.ideas.service import IdeaService
from qdw.intelligence.opportunities import OpportunityStore, OpportunitySynthesizer
from qdw.intelligence.painfinder import PainFinder
from qdw.intelligence.stack_oracle import StackOracle
from qdw.intelligence.startup_radar import StartupRadar
from qdw.products.registry import ProductRegistry
from qdw.watch.service import WatchService
from qdw.world.store import WorldStore


class QDWSystem:
    def __init__(self, db_path: str | Path):
        self.db = Database(db_path)
        self.db.migrate()

        # Core
        self.ledger = Ledger(self.db)
        self.graphs = WorkGraphStore(self.db, self.ledger)

        # World state
        self.world = WorldStore(self.db, self.ledger)

        # Intelligence
        self.pain = PainFinder(self.db, self.ledger)
        self.stack = StackOracle(self.db, self.ledger, self.world)
        self.startup = StartupRadar(self.db, self.ledger, self.world)
        self.opportunities = OpportunityStore(self.db, self.ledger)
        self.opp_synth = OpportunitySynthesizer(self.db, self.opportunities)

        # Ideas
        self.ideas = IdeaService(self.db, self.ledger)

        # Human queue
        self.human = HumanQueue(self.db, self.ledger)

        # Contractors
        self.contractors = ContractorRegistry(self.db, self.ledger)

        # HotSwap (persistent state — survives restarts)
        self.bandits = PersistentBanditStore(self.db)
        self.quotas = QuotaLedger()
        self.router = HotSwapRouter(bandits=self.bandits, quotas=self.quotas)
        self.routes: list[Route] = self.bandits.load_routes()

        # Factories
        self.factories = FactoryRegistry(self.db)

        # Products
        self.products = ProductRegistry(self.db, self.ledger)

        # Watch + catalog
        self.watch = WatchService(self.db, self.ledger)
        self.catalog = GlobalCatalog(self.db)

        # Economics
        self.costs = CostLedger(self.db)
        self.learning = FactoryLearning(self.db)

    def register_route(self, route: Route) -> None:
        """Register a route for HotSwap routing. Persists to database."""
        self.routes.append(route)
        self.bandits.save_route(route)

    def route_task(self, task_kind: str, requirements: dict[str, Any] | None = None) -> dict[str, Any]:
        """Route a task through HotSwap using registered routes."""
        from qdw.hotswap.types import TaskSpec
        r = requirements or {}
        task = TaskSpec(
            task_id=r.get("task_id", "preview"),
            task_kind=task_kind,
            quality_floor=float(r.get("quality", 0.70)),
        )
        plan = self.router.plan(task, self.routes)

        def _c(x: Any) -> dict[str, Any] | None:
            if x is None:
                return None
            return {
                "route_id": x.route.route_id,
                "model_id": x.route.model_id,
                "provider_id": x.route.provider_id,
                "p_success": x.p_success,
                "expected_completion_cost": x.expected_completion_cost,
            }

        return {
            "task_id": task.task_id,
            "primary": _c(plan.primary),
            "fallbacks": [_c(x) for x in plan.fallbacks],
            "reason_codes": plan.reason_codes,
        }

    def doctor(self) -> dict[str, Any]:
        """System health check."""
        ok, seq, reason = self.ledger.verify_chain()
        with self.db.connect() as con:
            tables = [
                r["name"]
                for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
            ]
        return {
            "ok": ok,
            "ledger": {"ok": ok, "bad_seq": seq, "reason": reason},
            "tables": tables,
            "route_count": len(self.routes),
        }
