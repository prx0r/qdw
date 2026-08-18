from __future__ import annotations
from pathlib import Path
from qdw.core import hash_object,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from .models import ReviewRequest,ReviewOutcome

class ReviewService:
    """Canonical review-run coordinator.

    Static scanners and agent reviewers return bounded artifacts. This service owns review lifecycle truth.
    """

    def __init__(self,db:Database,ledger:Ledger,workgraphs,contractors):
        self.db,self.ledger,self.workgraphs,self.contractors=db,ledger,workgraphs,contractors

    def create(self,req:ReviewRequest)->str:
        rid=new_id("review")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO review_runs(
                review_run_id,subject_git_sha,git_dirty,policy_hash,profile,producer_run_id,status,started_at
            ) VALUES(?,?,0,?,?,?,'PLANNED',?)""",
            (rid,req.subject_git_sha,req.policy_hash,req.profile,req.producer_run_id,utc_now()))
            # REQUIRED: append ledger event using same transaction/outbox mechanism.
        return rid

    def plan_full_review(self,review_run_id:str)->str:
        """Expand manifests/formulas/full-peer-review.json into an ordinary WorkGraph."""
        raise NotImplementedError("implement formula -> WorkGraph expansion")

    def certify(self,review_run_id:str,certifier_worker_id:str)->ReviewOutcome:
        """Aggregate evidence; may not trust reviewer PASS booleans without stored evidence/receipts."""
        raise NotImplementedError("implement policy-bound independent review certification")
