from __future__ import annotations
from qdw.core import canonical_json,hash_object,new_id,utc_now

class IdeaReviewEvidenceService:
    def __init__(self,db,ledger):
        self.db,self.ledger=db,ledger

    def record(self,*,idea_id,stage,reviewer_id,reviewer_version,artifact_id,passed,
               score,reason_codes,snapshot)->str:
        eid=new_id("ideareview")
        snap=hash_object(snapshot)
        with self.db.tx(immediate=True) as con:
            if not con.execute("SELECT 1 FROM ideas WHERE idea_id=?",(idea_id,)).fetchone():
                raise KeyError(idea_id)
            if artifact_id and not con.execute("SELECT 1 FROM artifacts WHERE artifact_id=?",(artifact_id,)).fetchone():
                raise ValueError("review artifact missing")
            con.execute("""INSERT INTO idea_review_evidence(
                evidence_id,idea_id,stage,reviewer_id,reviewer_version,artifact_id,passed,
                score_json,reason_codes_json,snapshot_hash,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (eid,idea_id,stage,reviewer_id,reviewer_version,artifact_id,1 if passed else 0,
             canonical_json(score).decode(),canonical_json(reason_codes).decode(),snap,utc_now()))
            self.ledger.append_in_tx(con,"idea.review_evidence","idea_review",eid,{
                "idea_id":idea_id,"stage":stage,"passed":passed,
            })
        return eid

    def resolve(self,evidence_id,*,idea_id,stage)->dict:
        with self.db.connect() as con:
            row=con.execute("SELECT * FROM idea_review_evidence WHERE evidence_id=?",(evidence_id,)).fetchone()
        if not row:raise ValueError("review evidence missing")
        if row["idea_id"]!=idea_id or row["stage"]!=stage:
            raise ValueError("review evidence subject mismatch")
        return dict(row)
