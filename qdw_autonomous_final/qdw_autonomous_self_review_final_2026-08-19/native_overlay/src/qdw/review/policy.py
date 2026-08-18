from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
from .models import ReviewPolicy,Severity

def load_policy(path:str|Path)->ReviewPolicy:
    d=json.loads(Path(path).read_text(encoding="utf-8"))
    body=json.dumps(d,sort_keys=True,separators=(",",":")).encode()
    return ReviewPolicy(
        policy_id=d["policy_id"],
        policy_hash=sha256(body).hexdigest(),
        block_at=Severity.parse(d.get("block_at","HIGH")),
        required_reviewers=tuple(d.get("required_reviewers",())),
        required_attacks=tuple(d.get("required_attacks",())),
        max_rounds=int(d.get("max_rounds",4)),
        max_cost_usd=d.get("max_cost_usd",5.0),
        require_clean_subject=bool(d.get("require_clean_subject",True)),
        require_remote_ci=bool(d.get("require_remote_ci",False)),
        require_independent_certifier=bool(d.get("require_independent_certifier",True)),
    )

def evaluate(store,review_run_id:str,policy:ReviewPolicy,*,remote_ci:bool|None=None)->dict:
    blockers=store.open_findings(review_run_id,policy.block_at)
    with store.db.connect() as con:
        row=con.execute("""SELECT rr.review_round_id FROM review_rounds rr
            WHERE rr.review_run_id=? ORDER BY rr.round_no DESC LIMIT 1""",(review_run_id,)).fetchone()
        attacks=[]
        if row:
            attacks=[dict(r) for r in con.execute(
                "SELECT * FROM review_attack_results WHERE review_round_id=?",(row["review_round_id"],)
            ).fetchall()]
        modules=[]
        if row:
            modules=[dict(r) for r in con.execute(
                "SELECT * FROM review_module_runs WHERE review_round_id=?",(row["review_round_id"],)
            ).fetchall()]
        run=con.execute("SELECT * FROM review_runs WHERE review_run_id=?",(review_run_id,)).fetchone()
    by_attack={a["attack_id"]:a for a in attacks}
    by_module={m["reviewer_id"]:m for m in modules}
    missing_reviewers=[x for x in policy.required_reviewers if x not in by_module or by_module[x]["status"]!="PASS"]
    missing_attacks=[x for x in policy.required_attacks if x not in by_attack or by_attack[x]["status"]!="PASS"]
    reasons=[]
    if blockers:reasons.append("BLOCKING_FINDINGS")
    if missing_reviewers:reasons.append("REVIEWERS_INCOMPLETE")
    if missing_attacks:reasons.append("ATTACKS_INCOMPLETE")
    if policy.require_clean_subject and run and run["subject_dirty"]:reasons.append("DIRTY_SUBJECT")
    if policy.require_remote_ci and remote_ci is not True:reasons.append("REMOTE_CI_UNPROVEN")
    return {
        "status":"PASS" if not reasons else "FAIL",
        "reasons":reasons,
        "blocker_count":len(blockers),
        "missing_reviewers":missing_reviewers,
        "missing_attacks":missing_attacks,
    }
