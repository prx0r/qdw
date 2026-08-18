"""Run frozen reviewer acceptance specifications against a later exact subject."""
from __future__ import annotations
from pathlib import Path
import json,tempfile
from qdw.core import utc_now
from qdw.proof.plan import VerificationCommand,VerificationPlan

class AcceptanceRunner:
    def __init__(self,db,ledger,verification,static_rule_checker=None,attack_runner=None):
        self.db,self.ledger,self.verification=db,ledger,verification
        self.static_rule_checker=static_rule_checker
        self.attack_runner=attack_runner

    def run_for_finding(self,finding_id:str,*,cwd:str|Path)->list[dict]:
        with self.db.connect() as con:
            rows=con.execute("""SELECT a.*,fa.status AS acceptance_status
                FROM review_finding_acceptance fa
                JOIN review_acceptance_specs a ON a.acceptance_spec_id=fa.acceptance_spec_id
                WHERE fa.finding_id=? ORDER BY a.frozen_at""",(finding_id,)).fetchall()
        results=[]
        for row in rows:
            body=json.loads(row["spec_json"])
            from hashlib import sha256
            from qdw.core import canonical_json
            if sha256(canonical_json(body)).hexdigest()!=row["spec_hash"]:
                status="FAIL";run_id=None;detail={"reason":"ACCEPTANCE_HASH_MISMATCH"}
                with self.db.tx(immediate=True) as con:
                    con.execute("""UPDATE review_finding_acceptance SET status='FAIL',checked_at=?
                        WHERE finding_id=? AND acceptance_spec_id=?""",
                        (utc_now(),finding_id,row["acceptance_spec_id"]))
                    self.ledger.append_in_tx(con,"review.acceptance_checked","review_finding",finding_id,{
                        "acceptance_spec_id":row["acceptance_spec_id"],"status":"FAIL",
                        "reason":"ACCEPTANCE_HASH_MISMATCH",
                    })
                results.append({"acceptance_spec_id":row["acceptance_spec_id"],"status":"FAIL",
                                "verification_run_id":None,**detail})
                continue
            spec=body.get("spec",body)
            kind=spec.get("kind","static_rule" if body.get("rule_recheck") else "unknown")
            status="UNVERIFIED";run_id=None;detail={}
            if kind=="command":
                plan=VerificationPlan(
                    plan_id=f"acceptance:{row['spec_hash']}",version="1",
                    commands=(VerificationCommand(
                        spec["id"],tuple(spec["argv"]),int(spec.get("timeout_seconds",300)),
                        True,int(spec.get("expected_exit_code",0)),
                    ),),
                )
                run_id=self.verification.execute(plan,task_id=f"acceptance:{finding_id}",cwd=cwd,require_clean=True)
                ok,_=self.verification.verify_evidence(run_id)
                status="PASS" if ok else "FAIL"
            elif kind=="inline_pytest":
                with tempfile.TemporaryDirectory(prefix="qdw-frozen-acceptance-") as td:
                    test=Path(td)/spec.get("filename","test_frozen_acceptance.py")
                    test.write_text(spec["content"],encoding="utf-8")
                    plan=VerificationPlan(
                        plan_id=f"acceptance:{row['spec_hash']}",version="1",
                        commands=(VerificationCommand(
                            spec.get("id","pytest"),
                            ("python","-m","pytest",str(test),"-q"),
                            int(spec.get("timeout_seconds",300)),True,0,
                        ),),
                    )
                    run_id=self.verification.execute(
                        plan,task_id=f"acceptance:{finding_id}",cwd=cwd,require_clean=True
                    )
                    ok,_=self.verification.verify_evidence(run_id)
                    status="PASS" if ok else "FAIL"
            elif kind=="static_rule" and self.static_rule_checker is not None:
                still_fires=self.static_rule_checker(spec["rule_id"],cwd)
                status="FAIL" if still_fires else "PASS"
            elif kind=="attack" and self.attack_runner is not None:
                # Full attack execution is normally handled at round level. This hook can target one attack.
                status="UNVERIFIED"
                detail={"attack_id":spec["attack_id"],"reason":"execute via round AttackRunner"}
            else:
                detail={"reason":f"unsupported acceptance kind {kind}"}

            with self.db.tx(immediate=True) as con:
                con.execute("""UPDATE review_finding_acceptance SET status=?,verification_run_id=?,checked_at=?
                    WHERE finding_id=? AND acceptance_spec_id=?""",
                    (status,run_id,utc_now(),finding_id,row["acceptance_spec_id"]))
                self.ledger.append_in_tx(con,"review.acceptance_checked","review_finding",finding_id,{
                    "acceptance_spec_id":row["acceptance_spec_id"],"status":status,
                })
            results.append({"acceptance_spec_id":row["acceptance_spec_id"],"status":status,
                            "verification_run_id":run_id,**detail})
        return results

    def close_if_proven(self,finding_id:str,new_subject_sha:str)->bool:
        with self.db.connect() as con:
            rows=con.execute(
                "SELECT status FROM review_finding_acceptance WHERE finding_id=?",(finding_id,)
            ).fetchall()
        if not rows or any(r["status"]!="PASS" for r in rows):
            return False
        with self.db.tx(immediate=True) as con:
            con.execute("""UPDATE review_findings SET status='FIXED',last_seen_sha=?,updated_at=?
                WHERE finding_id=?""",(new_subject_sha,utc_now(),finding_id))
            self.ledger.append_in_tx(con,"review.finding_fixed","review_finding",finding_id,{
                "subject_git_sha":new_subject_sha,
            })
        return True
