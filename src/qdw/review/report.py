from __future__ import annotations
import json
from qdw.core import hash_object

class ReviewReportService:
    def __init__(self,store):
        self.store=store

    def build(self,review_run_id:str)->dict:
        with self.store.db.connect() as con:
            run=con.execute("SELECT * FROM review_runs WHERE review_run_id=?",(review_run_id,)).fetchone()
            if not run:raise KeyError(review_run_id)
            rounds=[dict(r) for r in con.execute(
                "SELECT * FROM review_rounds WHERE review_run_id=? ORDER BY round_no",(review_run_id,)
            ).fetchall()]
            findings=[dict(r) for r in con.execute(
                "SELECT * FROM review_findings WHERE review_run_id=? ORDER BY created_at",(review_run_id,)
            ).fetchall()]
            attacks=[dict(r) for r in con.execute("""SELECT a.* FROM review_attack_results a
                JOIN review_rounds rr ON rr.review_round_id=a.review_round_id
                WHERE rr.review_run_id=? ORDER BY a.attack_id""",(review_run_id,)).fetchall()]
            modules=[dict(r) for r in con.execute("""SELECT m.* FROM review_module_runs m
                JOIN review_rounds rr ON rr.review_round_id=m.review_round_id
                WHERE rr.review_run_id=? ORDER BY rr.round_no,m.reviewer_id""",(review_run_id,)).fetchall()]
        report={
            "schema":"qdw.review-report.v2",
            "review_run":dict(run),
            "rounds":rounds,
            "modules":modules,
            "findings":findings,
            "attacks":attacks,
        }
        report["report_hash"]=hash_object(report)
        return report
