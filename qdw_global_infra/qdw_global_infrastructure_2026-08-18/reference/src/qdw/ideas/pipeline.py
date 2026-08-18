from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from qdw.core.core import hash_object
from qdw.core.db import Database
from qdw.ideas.service import IdeaService

STAGES = (
    "DISCOVERY",
    "EVIDENCE_REVIEW",
    "ADVERSARIAL_REVIEW",
    "PORTFOLIO_REVIEW",
    "ARCHITECTURE_REVIEW",
    "BUILD_READY",
)

@dataclass(frozen=True)
class ReviewDecision:
    idea_id:str
    stage:str
    decision:str
    reason_codes:tuple[str,...]
    snapshot_hash:str

class IdeaReviewPipeline:
    """Enforces staged review before an idea can reach BUILD_READY."""

    def __init__(self,db:Database,ideas:IdeaService):
        self.db,self.ideas=db,ideas

    def completed_stages(self,idea_id:str)->list[str]:
        with self.db.connect() as con:
            rows=con.execute("""SELECT stage,decision FROM idea_decisions WHERE idea_id=?
                ORDER BY created_at""",(idea_id,)).fetchall()
        return [r["stage"] for r in rows if r["decision"] in {"PASS","BUILD_READY"}]

    def next_stage(self,idea_id:str)->str|None:
        done=set(self.completed_stages(idea_id))
        for stage in STAGES:
            if stage not in done:return stage
        return None

    def review(self,idea_id:str,stage:str,*,passed:bool,score:dict[str,Any],
               reason_codes:list[str],snapshot:dict[str,Any])->ReviewDecision:
        expected=self.next_stage(idea_id)
        if stage!=expected:
            raise ValueError(f"expected stage {expected}, got {stage}")
        decision="BUILD_READY" if passed and stage=="BUILD_READY" else ("PASS" if passed else "REJECT")
        self.ideas.decide(idea_id,stage,decision,score,reason_codes,snapshot)
        return ReviewDecision(idea_id,stage,decision,tuple(reason_codes),hash_object(snapshot))
