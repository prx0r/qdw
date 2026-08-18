from __future__ import annotations
from pathlib import Path
from qdw.core.system import VentureLabSystem as CoreSystem
from qdw.world.store import WorldStore
from qdw.intelligence.painfinder import PainFinder
from qdw.intelligence.startup_radar import StartupRadar
from qdw.intelligence.stack_oracle import StackOracle
from qdw.intelligence.opportunities import OpportunityStore, OpportunitySynthesizer
from qdw.intelligence.alternative_api import AlternativeAPI
from qdw.ideas.service import IdeaService
from qdw.ideas.library import IdeaLibrary
from qdw.ideas.pipeline import IdeaReviewPipeline
from qdw.human.queue import HumanQueue
from qdw.contractors.registry import ContractorRegistry
from qdw.products.registry import ProductRegistry
from qdw.publishing.registry import DistributionRegistry
from qdw.publishing.domain import DomainPlanner
from qdw.publishing.portfolio import PortfolioPublisher
from qdw.publishing.docs import DocsPublisher
from qdw.watch.service import WatchService
from qdw.catalog.service import GlobalCatalog

_REQUIRED_TABLES = {
    "entities","observations","claims","relations","pain_clusters","startup_events","capabilities","resources",
    "opportunities_global","ideas","cemetery_entries","contractor_definitions","human_actions","products",
    "distribution_surfaces","publications","domains","outcome_events",
}

class QDWSystem:
    """Single composition root. All global modules share CoreSystem.db and CoreSystem.ledger."""

    def __init__(self,db_path:str|Path):
        self.core=CoreSystem(db_path)
        self.db=self.core.db
        self.ledger=self.core.ledger
        self.graphs=self.core.graphs
        self.factories=self.core.factories
        self.costs=self.core.costs
        self.learning=self.core.learning

        self.world=WorldStore(self.db,self.ledger)
        self.pain=PainFinder(self.db,self.ledger)
        self.startups=StartupRadar(self.db,self.ledger,self.world)
        self.stack=StackOracle(self.db,self.ledger,self.world)
        self.opportunities=OpportunityStore(self.db,self.ledger)
        self.synthesize=OpportunitySynthesizer(self.db,self.opportunities)
        self.alternatives=AlternativeAPI(self.stack,self.synthesize)
        self.ideas=IdeaService(self.db,self.ledger)
        self.idea_library=IdeaLibrary(self.db)
        self.idea_reviews=IdeaReviewPipeline(self.db,self.ideas)
        self.human=HumanQueue(self.db,self.ledger)
        self.contractors=ContractorRegistry(self.db,self.ledger)
        self.products=ProductRegistry(self.db,self.ledger)
        self.distributions=DistributionRegistry(self.db,self.ledger)
        self.domains=DomainPlanner(self.db,self.ledger,self.human)
        self.portfolio=PortfolioPublisher(self.db)
        self.docs=DocsPublisher()
        self.watch=WatchService(self.db,self.ledger)
        self.catalog=GlobalCatalog(self.db)

    def doctor(self)->dict:
        core=self.core.doctor()
        with self.db.connect() as con:
            tables={r["name"] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            fk=[dict(r) for r in con.execute("PRAGMA foreign_key_check").fetchall()]
        missing=sorted(_REQUIRED_TABLES-tables)
        return {
            "ok":bool(core["ok"] and not missing and not fk),
            "core":core,
            "global":{"missing_tables":missing,"foreign_key_violations":fk},
        }
