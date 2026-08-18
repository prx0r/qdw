"""Composition helper for adding native review to QDWSystem."""
from __future__ import annotations
from pathlib import Path
from qdw.proof.verification_service import VerificationService
from .reviewers import ReviewerCatalog
from .static_engine import StaticRuleEngine
from .static_rules import ALL_RULES
from .service import ReviewService
from .execution import ReviewWorkGraphExecutor
from .controller import AutonomousReviewController,GitSubjectProvider

def build_review_runtime(system,*,repo_root:str|Path,executor):
    root=Path(repo_root).resolve()
    verification=getattr(system,"verification",None) or VerificationService(
        system.db,system.ledger,runs_dir=root/".qdw/verification"
    )
    reviewers=ReviewerCatalog(
        root/"manifests/reviewers",
        root/"prompts/reviewers",
        db=system.db,
        active_only=True,
    )
    static_engine=StaticRuleEngine(ALL_RULES)
    review=ReviewService(
        db=system.db,ledger=system.ledger,graphs=system.graphs,
        reviewers=reviewers,verification=verification,
        attack_catalog_path=root/"attacks/ATTACK_CATALOG.json",
        static_engine=static_engine,
    )
    graph_executor=ReviewWorkGraphExecutor(
        graphs=system.graphs,store=review.store,reviewers=reviewers,
        executor=executor,workspace=str(root),
    )
    controller=AutonomousReviewController(
        review,graph_executor,GitSubjectProvider(root)
    )
    return verification,review,controller
