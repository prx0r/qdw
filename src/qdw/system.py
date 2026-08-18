"""QDW system — composition root with all registries injected.

No module should instantiate random private copies of these.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from qdw.core.db import Database
from qdw.core.graph.store import WorkGraphStore
from qdw.core.ledger.events import Ledger
from qdw.core.portfolio.costs import CostLedger
from qdw.core.portfolio.learning import FactoryLearning
from qdw.factories.registry import FactoryRegistry


class QDWSystem:
    def __init__(self, db_path: str | Path):
        self.db = Database(db_path)
        self.db.migrate()
        self.ledger = Ledger(self.db)
        self.graphs = WorkGraphStore(self.db, self.ledger)
        self.factories = FactoryRegistry(self.db)
        self.costs = CostLedger(self.db)
        self.learning = FactoryLearning(self.db)

    def doctor(self) -> dict[str, Any]:
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
        }
