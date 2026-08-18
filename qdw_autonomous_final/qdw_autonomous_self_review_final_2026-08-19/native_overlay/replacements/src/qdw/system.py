"""QDWSystem v2 — single composition root including autonomous review."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from qdw.core.db import Database
from qdw.core.graph.store import WorkGraphStore
from qdw.core.ledger.events import Ledger
from qdw.core.portfolio.costs import CostLedger
from qdw.core.portfolio.learning import FactoryLearning
from qdw.factories.registry import FactoryRegistry
from qdw.hotswap.persistent import PersistentBanditStore,RouteRegistry
from qdw.hotswap.quota import QuotaLedger
from qdw.hotswap.router import HotSwapRouter
from qdw.hotswap.types import Route
from qdw.world.store import WorldStore
from qdw.intelligence.painfinder import PainFinder
from qdw.intelligence.stack_oracle import StackOracle
from qdw.intelligence.startup_radar import StartupRadar
from qdw.intelligence.opportunities import OpportunityStore,OpportunitySynthesizer
from qdw.ideas.service import IdeaService
from qdw.ideas.library import IdeaLibrary
from qdw.ideas.review_evidence import IdeaReviewEvidenceService
from qdw.human.queue import HumanQueue
from qdw.contractors.registry import ContractorRegistry
from qdw.products.registry import ProductRegistry
from qdw.watch.service import WatchService
from qdw.catalog.service import GlobalCatalog
from qdw.proof.verification_service import VerificationService
from qdw.proof.certificate_v2 import BuildCertificateV2
from qdw.proof.subject_certificates import FixtureCertificateService,ReleaseAuthorizationService
from qdw.executors.hermes import HermesExecutor
from qdw.review.bootstrap import build_review_runtime
from qdw.review.bootstrap_reviewers import ReviewerBootstrapService

class QDWSystem:
    def __init__(self,db_path:str|Path,*,repo_root:str|Path=".",
                 review_executor=None,enable_review:bool=True):
        self.repo_root=Path(repo_root).resolve()
        self.db=Database(db_path)
        self.db.migrate()

        # Canonical core
        self.ledger=Ledger(self.db)
        self.graphs=WorkGraphStore(self.db,self.ledger)

        # One canonical verification/proof path
        self.verification=VerificationService(
            self.db,self.ledger,self.repo_root/".qdw/verification"
        )
        self.build_certificates=BuildCertificateV2(self.verification)
        self.fixture_certificates=FixtureCertificateService(
            self.db,self.ledger,self.build_certificates
        )
        self.release_authorizations=ReleaseAuthorizationService(
            self.db,self.ledger,self.build_certificates
        )

        # HotSwap durable identity + learning
        self.bandits=PersistentBanditStore(self.db)
        self.route_registry=RouteRegistry(self.bandits)
        self.quotas=QuotaLedger()
        self.router=HotSwapRouter(bandits=self.bandits,quotas=self.quotas)

        # Factory/economic substrate
        self.factories=FactoryRegistry(self.db)
        self.costs=CostLedger(self.db)
        self.learning=FactoryLearning(self.db)

        # Global intelligence
        self.world=WorldStore(self.db,self.ledger)
        self.pain=PainFinder(self.db,self.ledger)
        self.stack=StackOracle(self.db,self.ledger,self.world)
        self.startups=StartupRadar(self.db,self.ledger,self.world)
        self.opportunities=OpportunityStore(self.db,self.ledger)
        self.synthesize=OpportunitySynthesizer(self.db,self.opportunities)

        # Ideas / humans / contractors / products
        self.ideas=IdeaService(self.db,self.ledger)
        self.idea_library=IdeaLibrary(self.db)
        self.idea_review_evidence=IdeaReviewEvidenceService(self.db,self.ledger)
        self.human=HumanQueue(self.db,self.ledger)
        self.contractors=ContractorRegistry(self.db,self.ledger)
        self.products=ProductRegistry(self.db,self.ledger)
        self.watch=WatchService(self.db,self.ledger)
        self.catalog=GlobalCatalog(self.db)

        # Review itself uses the same Executor + WorkGraph substrate.
        self.review=None
        self.review_controller=None
        if enable_review:
            executor=review_executor or HermesExecutor(profile="qdw-review")
            self.verification,self.review,self.review_controller=build_review_runtime(
                self,repo_root=self.repo_root,executor=executor
            )
            self.reviewer_bootstrap=ReviewerBootstrapService(
                self,self.review.reviewers,self.repo_root
            )

    @property
    def routes(self)->list[Route]:
        return self.route_registry.active()

    def register_route(self,route:Route)->None:
        self.route_registry.register(route)

    def route_task(self,task_kind:str,requirements:dict[str,Any]|None=None)->dict[str,Any]:
        from qdw.hotswap.types import TaskSpec
        r=requirements or {}
        task=TaskSpec(
            task_id=r.get("task_id","preview"),
            task_kind=task_kind,
            quality_floor=float(r.get("quality",.70)),
        )
        plan=self.router.plan(task,self.route_registry.active())
        def candidate(x):
            if x is None:return None
            return {
                "route_id":x.route.route_id,"model_id":x.route.model_id,
                "provider_id":x.route.provider_id,"p_success":x.p_success,
                "expected_completion_cost":x.expected_completion_cost,
            }
        return {
            "task_id":task.task_id,
            "primary":candidate(plan.primary),
            "fallbacks":[candidate(x) for x in plan.fallbacks],
            "reason_codes":plan.reason_codes,
        }

    def doctor(self)->dict[str,Any]:
        from qdw.core.migrations import applied_versions,verify_applied_migrations
        ok,seq,reason=self.ledger.verify_chain()
        migration_error=None
        try:verify_applied_migrations(self.db)
        except Exception as exc:migration_error=str(exc)
        with self.db.connect() as con:
            tables=[r["name"] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()]
        healthy=ok and migration_error is None
        return {
            "ok":healthy,
            "ledger":{"ok":ok,"bad_seq":seq,"reason":reason},
            "migrations":{"versions":sorted(applied_versions(self.db)),"error":migration_error},
            "tables":tables,
            "route_count":len(self.route_registry.active()),
            "review_enabled":self.review is not None,
        }
