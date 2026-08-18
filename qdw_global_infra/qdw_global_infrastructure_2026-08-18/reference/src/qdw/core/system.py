from __future__ import annotations
from pathlib import Path
from .db import Database
from .ledger.events import Ledger
from .graph.store import WorkGraphStore
from .factories.registry import FactoryRegistry
from .portfolio.costs import CostLedger
from .portfolio.learning import FactoryLearning

class VentureLabSystem:
    def __init__(self,db_path:str|Path):
        self.db=Database(db_path);self.db.migrate()
        self.ledger=Ledger(self.db)
        self.graphs=WorkGraphStore(self.db,self.ledger)
        self.factories=FactoryRegistry(self.db)
        self.costs=CostLedger(self.db)
        self.learning=FactoryLearning(self.db)

    def doctor(self)->dict:
        ok,seq,reason=self.ledger.verify_chain()
        with self.db.connect() as con:
            tables=[r["name"] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        return {"ok":ok,"ledger":{"ok":ok,"bad_seq":seq,"reason":reason},"tables":tables}
