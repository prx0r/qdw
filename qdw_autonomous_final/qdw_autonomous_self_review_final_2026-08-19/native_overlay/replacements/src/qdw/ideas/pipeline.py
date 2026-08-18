"""IdeaReviewPipeline v2 consumes bound IdeaReviewEvidence IDs, not caller PASS booleans."""
from __future__ import annotations
from dataclasses import dataclass
import json
from qdw.core import hash_object

STAGES=(
    "DISCOVERY","EVIDENCE_REVIEW","ADVERSARIAL_REVIEW",
    "PORTFOLIO_REVIEW","ARCHITECTURE_REVIEW","BUILD_READY",
)

@dataclass(frozen=True)
class ReviewDecision:
    idea_id:str
    stage:str
    decision:str
    reason_codes:tuple[str,...]
    snapshot_hash:str
    evidence_ref:str

class IdeaReviewPipeline:
    def __init__(self,db,ideas,evidence_service):
        self.db,self.ideas,self.evidence=db,ideas,evidence_service

    def completed_stages(self,idea_id):
        with self.db.connect() as con:
            rows=con.execute("""SELECT stage,decision FROM idea_decisions
                WHERE idea_id=? ORDER BY created_at""",(idea_id,)).fetchall()
        return [r["stage"] for r in rows if r["decision"] in {"PASS","BUILD_READY"}]

    def next_stage(self,idea_id):
        done=set(self.completed_stages(idea_id))
        return next((stage for stage in STAGES if stage not in done),None)

    def review(self,idea_id,stage,*,evidence_ref,snapshot):
        expected=self.next_stage(idea_id)
        if stage!=expected:raise ValueError(f"expected stage {expected}, got {stage}")
        evidence=self.evidence.resolve(evidence_ref,idea_id=idea_id,stage=stage)
        passed=bool(evidence["passed"])
        score=json.loads(evidence["score_json"])
        reason_codes=json.loads(evidence["reason_codes_json"])
        decision="BUILD_READY" if passed and stage=="BUILD_READY" else ("PASS" if passed else "REJECT")
        self.ideas.decide(
            idea_id,stage,decision,score,reason_codes,snapshot,
            evidence_ref=evidence_ref,reviewer_id=evidence["reviewer_id"],
            reviewer_version=evidence["reviewer_version"],
        )
        return ReviewDecision(
            idea_id,stage,decision,tuple(reason_codes),hash_object(snapshot),evidence_ref
        )
