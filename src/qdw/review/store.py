from __future__ import annotations
import json,hashlib
from typing import Any
from qdw.core import canonical_json,hash_object,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from .models import ReviewRequest,ReviewerResult,Severity

def _fp(rule_id,module_id,evidence):
    paths=sorted((x.get("path") or "") for x in evidence)
    return hashlib.sha256(canonical_json({"rule_id":rule_id,"module_id":module_id,"paths":paths})).hexdigest()

class ReviewStore:
    def __init__(self,db:Database,ledger:Ledger):
        self.db,self.ledger=db,ledger

    def create_run(self,req:ReviewRequest)->str:
        rid=new_id("review")
        now=utc_now()
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO review_runs(
                review_run_id,subject_git_sha,subject_dirty,base_git_sha,policy_id,policy_hash,profile,
                trigger_type,changed_paths_json,status,current_round,max_rounds,max_cost_usd,spent_cost_usd,
                producer_worker_id,started_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,'PLANNED',0,?,?,0,?,?,?)""",
            (rid,req.subject_git_sha,1 if req.subject_dirty else 0,req.base_git_sha,
             req.policy.policy_id,req.policy.policy_hash,req.profile,req.trigger_type,
             canonical_json(req.changed_paths).decode(),req.policy.max_rounds,req.policy.max_cost_usd,
             req.producer_worker_id,now,now))
            self.ledger.append_in_tx(con,"review.created","review_run",rid,{
                "subject_git_sha":req.subject_git_sha,"policy_hash":req.policy.policy_hash,
                "trigger_type":req.trigger_type,
            })
        return rid

    def start_round(self,review_run_id:str,subject_sha:str,reviewer_set_hash:str,attack_set_hash:str)->str:
        rrid=new_id("reviewround")
        with self.db.tx(immediate=True) as con:
            row=con.execute("SELECT current_round,policy_hash FROM review_runs WHERE review_run_id=?",(review_run_id,)).fetchone()
            if not row:raise KeyError(review_run_id)
            n=row["current_round"]+1
            con.execute("""INSERT INTO review_rounds(
                review_round_id,review_run_id,round_no,subject_git_sha,policy_hash,reviewer_set_hash,
                attack_set_hash,status,started_at
            ) VALUES(?,?,?,?,?,?,?,'RUNNING',?)""",
            (rrid,review_run_id,n,subject_sha,row["policy_hash"],reviewer_set_hash,attack_set_hash,utc_now()))
            con.execute("UPDATE review_runs SET current_round=?,status='SCANNING',updated_at=? WHERE review_run_id=?",
                        (n,utc_now(),review_run_id))
            self.ledger.append_in_tx(con,"review.round_started","review_run",review_run_id,{"round_no":n,"subject_sha":subject_sha})
        return rrid

    def create_module_run(self,round_id:str,reviewer_id:str,version:str,definition_hash:str,
                          work_node_id=None,worker_id=None,executor_id=None)->str:
        mid=new_id("reviewmodule")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO review_module_runs(
                module_run_id,review_round_id,reviewer_id,reviewer_version,reviewer_definition_hash,
                work_node_id,worker_id,executor_id,status
            ) VALUES(?,?,?,?,?,?,?,?,'PENDING')""",
            (mid,round_id,reviewer_id,version,definition_hash,work_node_id,worker_id,executor_id))
            self.ledger.append_in_tx(con,"review.module_planned","review_module",mid,{"reviewer_id":reviewer_id,"version":version})
        return mid

    def ingest_result(self,review_run_id:str,round_id:str,module_run_id:str,result:ReviewerResult,subject_sha:str)->list[str]:
        ids=[]
        with self.db.tx(immediate=True) as con:
            con.execute("""UPDATE review_module_runs SET status=?,cost_usd=?,finished_at=?
                WHERE module_run_id=?""",
                ("PASS" if result.status=="ok" else "FAIL",result.cost_usd,utc_now(),module_run_id))
            for x in result.findings:
                evidence=list(x.evidence)
                fp=_fp(x.rule_id,result.reviewer_id,evidence)
                prior=con.execute("""SELECT finding_id,status FROM review_findings
                    WHERE fingerprint=? ORDER BY created_at DESC LIMIT 1""",(fp,)).fetchone()
                status="REGRESSION" if prior and prior["status"]=="FIXED" else "OPEN"
                fid=new_id("finding")
                con.execute("""INSERT INTO review_findings(
                    finding_id,fingerprint,review_run_id,review_round_id,module_run_id,rule_id,module_id,severity,
                    confidence,status,title,summary,invariant_text,remediation,first_seen_sha,last_seen_sha,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (fid,fp,review_run_id,round_id,module_run_id,x.rule_id,result.reviewer_id,x.severity,
                 x.confidence,status,x.title,x.summary,x.invariant,x.remediation,
                 subject_sha,subject_sha,utc_now(),utc_now()))
                for e in evidence:
                    eid=new_id("reviewevidence")
                    con.execute("""INSERT INTO review_evidence(
                        evidence_id,finding_id,kind,path,line,detail,content_sha256,receipt_id,artifact_id,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (eid,fid,e.get("kind","reviewer"),e.get("path"),e.get("line"),e.get("detail"),
                     e.get("content_sha256"),e.get("receipt_id"),e.get("artifact_id"),utc_now()))

                # Freeze executable reviewer acceptance before any producer sees the finding.
                # Inline pytest code is stored inside spec_json and content-hashed; the producer cannot
                # rewrite it without changing spec_hash.
                for spec in x.acceptance_specs:
                    spec_body={
                        "finding_fingerprint":fp,
                        "rule_id":x.rule_id,
                        "spec":spec,
                    }
                    spec_hash=hashlib.sha256(canonical_json(spec_body)).hexdigest()
                    aid=new_id("acceptance")
                    con.execute("""INSERT OR IGNORE INTO review_acceptance_specs(
                        acceptance_spec_id,finding_fingerprint,spec_hash,spec_json,frozen_at,frozen_subject_sha
                    ) VALUES(?,?,?,?,?,?)""",
                    (aid,fp,spec_hash,canonical_json(spec_body).decode(),utc_now(),subject_sha))
                    row=con.execute("SELECT acceptance_spec_id FROM review_acceptance_specs WHERE spec_hash=?",(spec_hash,)).fetchone()
                    con.execute("""INSERT OR IGNORE INTO review_finding_acceptance(
                        finding_id,acceptance_spec_id,status
                    ) VALUES(?,?,'PENDING')""",(fid,row["acceptance_spec_id"]))
                ids.append(fid)
            self.ledger.append_in_tx(con,"review.module_ingested","review_module",module_run_id,{
                "finding_count":len(ids),"status":result.status,
            })
        return ids

    def open_findings(self,review_run_id:str,min_severity:Severity=Severity.INFO)->list[dict]:
        names=[s.name for s in Severity if s>=min_severity]
        q=",".join("?" for _ in names)
        with self.db.connect() as con:
            rows=con.execute(f"""SELECT * FROM review_findings
                WHERE review_run_id=? AND status IN ('OPEN','REGRESSION') AND severity IN ({q})
                ORDER BY CASE severity WHEN 'CRITICAL' THEN 5 WHEN 'HIGH' THEN 4 WHEN 'MEDIUM' THEN 3
                    WHEN 'LOW' THEN 2 ELSE 1 END DESC, created_at""",(review_run_id,*names)).fetchall()
        return [dict(r) for r in rows]

    def set_status(self,review_run_id:str,status:str,**fields):
        allowed={"fix_graph_id","blocker_set_hash","spent_cost_usd","finished_at"}
        updates={"status":status,"updated_at":utc_now(),**{k:v for k,v in fields.items() if k in allowed}}
        parts=",".join(f"{k}=?" for k in updates)
        with self.db.tx(immediate=True) as con:
            con.execute(f"UPDATE review_runs SET {parts} WHERE review_run_id=?",(*updates.values(),review_run_id))
            self.ledger.append_in_tx(con,"review.status","review_run",review_run_id,{"status":status})
