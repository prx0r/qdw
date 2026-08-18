from __future__ import annotations
import json
from qdw.core import canonical_json,hash_object,new_id,utc_now

class FindingClosureService:
    """Closes an old finding only after frozen acceptance + independent re-review."""
    def __init__(self,db,ledger):self.db,self.ledger=db,ledger

    def close(self,finding_id:str,*,new_subject_sha:str,recheck_round_id:str,certifier_id:str="qdw-closure") -> bool:
        with self.db.connect() as con:
            finding=con.execute("SELECT * FROM review_findings WHERE finding_id=?",(finding_id,)).fetchone()
            if not finding:raise KeyError(finding_id)
            acceptance=[dict(r) for r in con.execute("""SELECT fa.*,a.spec_hash FROM review_finding_acceptance fa
                JOIN review_acceptance_specs a ON a.acceptance_spec_id=fa.acceptance_spec_id
                WHERE fa.finding_id=? ORDER BY a.spec_hash""",(finding_id,)).fetchall()]
            if not acceptance or any(x["status"]!="PASS" for x in acceptance):return False
            repeated=con.execute("""SELECT 1 FROM review_findings WHERE review_round_id=? AND fingerprint=?
                AND status IN ('OPEN','REGRESSION') LIMIT 1""",(recheck_round_id,finding["fingerprint"])).fetchone()
            if repeated:return False
            rr=con.execute("SELECT subject_git_sha FROM review_rounds WHERE review_round_id=?",(recheck_round_id,)).fetchone()
            if not rr or rr["subject_git_sha"]!=new_subject_sha:return False
        aset=hash_object([(x["acceptance_spec_id"],x["spec_hash"]) for x in acceptance])
        vhash=hash_object([(x["acceptance_spec_id"],x["verification_run_id"],x["status"]) for x in acceptance])
        cid=new_id("closure")
        body={
            "schema":"qdw.finding-closure.v1","closure_id":cid,"finding_id":finding_id,
            "finding_fingerprint":finding["fingerprint"],"old_subject_git_sha":finding["first_seen_sha"],
            "new_subject_git_sha":new_subject_sha,"acceptance_set_hash":aset,
            "acceptance_verification_hash":vhash,"recheck_review_round_id":recheck_round_id,
            "certifier_id":certifier_id,"closed_at":utc_now(),
        }
        body["closure_hash"]=hash_object(body)
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO review_finding_closures(
                closure_id,finding_id,finding_fingerprint,old_subject_git_sha,new_subject_git_sha,
                acceptance_set_hash,acceptance_verification_hash,recheck_review_round_id,certifier_id,
                closure_json,closure_hash,closed_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid,finding_id,finding["fingerprint"],finding["first_seen_sha"],new_subject_sha,aset,vhash,
             recheck_round_id,certifier_id,canonical_json(body).decode(),body["closure_hash"],body["closed_at"]))
            con.execute("UPDATE review_findings SET status='FIXED',last_seen_sha=?,updated_at=? WHERE finding_id=?",
                        (new_subject_sha,utc_now(),finding_id))
            self.ledger.append_in_tx(con,"review.finding_closed","review_finding",finding_id,{
                "closure_id":cid,"new_subject_git_sha":new_subject_sha,"recheck_review_round_id":recheck_round_id})
        return True
