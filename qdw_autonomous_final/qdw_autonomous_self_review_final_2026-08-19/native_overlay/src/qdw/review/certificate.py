from __future__ import annotations
import json
from qdw.core import canonical_json,hash_object,new_id,utc_now
from .policy import evaluate

class ReviewCertificateService:
    def __init__(self,store):
        self.store=store

    def issue(self,review_run_id:str,policy,*,certifier_worker_id:str,remote_ci:bool|None=None)->dict:
        with self.store.db.connect() as con:
            run=con.execute("SELECT * FROM review_runs WHERE review_run_id=?",(review_run_id,)).fetchone()
            if not run:raise KeyError(review_run_id)
            rounds=[dict(r) for r in con.execute(
                "SELECT * FROM review_rounds WHERE review_run_id=? ORDER BY round_no",(review_run_id,)
            ).fetchall()]
            modules=[dict(r) for r in con.execute("""SELECT m.* FROM review_module_runs m
                JOIN review_rounds rr ON rr.review_round_id=m.review_round_id
                WHERE rr.review_run_id=? ORDER BY m.reviewer_id""",(review_run_id,)).fetchall()]
            attacks=[dict(r) for r in con.execute("""SELECT a.* FROM review_attack_results a
                JOIN review_rounds rr ON rr.review_round_id=a.review_round_id
                WHERE rr.review_run_id=? ORDER BY a.attack_id""",(review_run_id,)).fetchall()]
        gate=evaluate(self.store,review_run_id,policy,remote_ci=remote_ci)
        if gate["status"]!="PASS":
            raise ValueError("review cannot certify: "+",".join(gate["reasons"]))
        if policy.require_independent_certifier:
            if run["producer_worker_id"] and run["producer_worker_id"]==certifier_worker_id:
                raise ValueError("producer cannot independently certify")
            reviewer_workers={m["worker_id"] for m in modules if m.get("worker_id")}
            if certifier_worker_id in reviewer_workers:
                raise ValueError("reviewer worker cannot independently certify its own review")
        report_hash=hash_object({"run":dict(run),"rounds":rounds})
        reviewer_set_hash=hash_object([(m["reviewer_id"],m["reviewer_version"],m["reviewer_definition_hash"]) for m in modules])
        attack_set_hash=hash_object([(a["attack_id"],a["attack_version"],a["status"]) for a in attacks])
        cid=new_id("reviewcert")
        cert={
            "schema":"qdw.review-certificate.v2",
            "review_certificate_id":cid,
            "review_run_id":review_run_id,
            "subject_git_sha":run["subject_git_sha"],
            "policy_hash":run["policy_hash"],
            "report_hash":report_hash,
            "reviewer_set_hash":reviewer_set_hash,
            "attack_set_hash":attack_set_hash,
            "certifier_worker_id":certifier_worker_id,
            "producer_worker_id":run["producer_worker_id"],
            "status":"REVIEW_CERTIFIED",
            "issued_at":utc_now(),
        }
        cert["certificate_hash"]=hash_object(cert)
        with self.store.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO review_certificates(
                review_certificate_id,review_run_id,subject_git_sha,policy_hash,report_hash,
                reviewer_set_hash,attack_set_hash,certifier_worker_id,producer_worker_id,status,
                certificate_json,certificate_hash,issued_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid,review_run_id,run["subject_git_sha"],run["policy_hash"],report_hash,
             reviewer_set_hash,attack_set_hash,certifier_worker_id,run["producer_worker_id"],
             "REVIEW_CERTIFIED",canonical_json(cert).decode(),cert["certificate_hash"],cert["issued_at"]))
            con.execute("UPDATE review_runs SET status='CERTIFIED',finished_at=?,updated_at=? WHERE review_run_id=?",
                        (utc_now(),utc_now(),review_run_id))
            self.store.ledger.append_in_tx(con,"review.certificate_issued","review_certificate",cid,{
                "review_run_id":review_run_id,"subject_git_sha":run["subject_git_sha"],
            })
        return cert
