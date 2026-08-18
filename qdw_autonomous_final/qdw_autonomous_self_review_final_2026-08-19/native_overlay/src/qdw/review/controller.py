from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import subprocess
from typing import Protocol
from .models import ControllerOutcome,ReviewRequest
from .progress import stop_reason
from .service import ReviewPrerequisiteError

class GraphExecutor(Protocol):
    def execute_graph(self,graph_id:str)->None: ...

class SubjectProvider(Protocol):
    def snapshot(self)->tuple[str,bool,tuple[str,...]]: ...

class GitSubjectProvider:
    def __init__(self,repo_root:str|Path):self.root=Path(repo_root)
    def snapshot(self):
        sha=subprocess.run(["git","rev-parse","HEAD"],cwd=self.root,capture_output=True,text=True,check=True).stdout.strip()
        dirty=bool(subprocess.run(["git","status","--porcelain"],cwd=self.root,capture_output=True,text=True,check=True).stdout.strip())
        diff=subprocess.run(["git","diff","--name-only","HEAD~1","HEAD"],cwd=self.root,capture_output=True,text=True)
        changed=tuple(x for x in diff.stdout.splitlines() if x) if diff.returncode==0 else ()
        return sha,dirty,changed

class AutonomousReviewController:
    """Bounded review→fix→frozen-acceptance→re-review convergence.

    WorkGraphs are executed by the injected normal QDW graph executor. This controller owns no queue.
    A finding is closed only after the old frozen acceptance passes on a new clean SHA and the next
    independent review round does not reproduce the same fingerprint.
    """
    def __init__(self,review_service,graph_executor:GraphExecutor,subject_provider:SubjectProvider):
        self.review=review_service;self.graph_executor=graph_executor;self.subjects=subject_provider

    def run(self,request:ReviewRequest,*,policy,workspace:str|Path,certifier_worker_id:str,
            remote_ci:bool|None=None,pack_path:str|Path|None=None)->ControllerOutcome:
        review_run_id=self.review.start(request)
        previous_blockers=None
        pending_closure:list[str]=[]

        for round_no in range(1,policy.max_rounds+1):
            sha,dirty,changed=self.subjects.snapshot()
            if policy.require_clean_subject and dirty:
                self.review.store.set_status(review_run_id,"BLOCKED")
                return ControllerOutcome(review_run_id,"BLOCKED",round_no,0,stop_reason="DIRTY_SUBJECT")

            try:
                round_plan=self.review.begin_round(
                    review_run_id,subject_sha=sha,changed_paths=changed,profile=request.profile,
                    policy=policy,repo_root=workspace,
                )
            except ReviewPrerequisiteError as exc:
                return ControllerOutcome(review_run_id,"BLOCKED",round_no,0,stop_reason=str(exc))

            self.graph_executor.execute_graph(round_plan["review_graph_id"])
            self.review.run_attacks(review_run_id,round_plan["round_id"],policy,cwd=workspace,subject_sha=sha)

            # Only after a full independent re-review can previously acceptance-proven findings close.
            if pending_closure:
                self.review.close_prior_findings(
                    pending_closure,new_subject_sha=sha,recheck_round_id=round_plan["round_id"]
                )
                pending_closure=[]

            with self.review.db.connect() as con:
                round_cost=con.execute("""SELECT COALESCE(SUM(cost_usd),0) cost FROM review_module_runs
                    WHERE review_round_id=?""",(round_plan["round_id"],)).fetchone()["cost"]
                run_row=con.execute("SELECT spent_cost_usd FROM review_runs WHERE review_run_id=?",
                                    (review_run_id,)).fetchone()
            total_cost=float(run_row["spent_cost_usd"] or 0)+float(round_cost or 0)
            from qdw.core import utc_now
            with self.review.db.tx(immediate=True) as con:
                con.execute("UPDATE review_rounds SET cost_usd=? WHERE review_round_id=?",(round_cost,round_plan["round_id"]))
                con.execute("UPDATE review_runs SET spent_cost_usd=?,updated_at=? WHERE review_run_id=?",
                            (total_cost,utc_now(),review_run_id))

            blockers=self.review.store.open_findings(review_run_id,policy.block_at)
            fps=tuple(sorted({x["fingerprint"] for x in blockers}))
            if not blockers:
                cert=self.review.certificates.issue(
                    review_run_id,policy,certifier_worker_id=certifier_worker_id,remote_ci=remote_ci
                )
                if pack_path:self.review.export_pack(review_run_id,pack_path)
                return ControllerOutcome(review_run_id,"CERTIFIED",round_no,0,
                                         certificate_id=cert["review_certificate_id"])

            self.review.freeze_acceptance_for_open_findings(review_run_id,sha)
            reason=stop_reason(previous_blockers=previous_blockers,current_blockers=fps,
                               round_no=round_no,max_rounds=policy.max_rounds,
                               total_cost_usd=total_cost,max_cost_usd=policy.max_cost_usd)
            if reason:
                self.review.store.set_status(
                    review_run_id,"STALLED",blocker_set_hash=sha256("|".join(fps).encode()).hexdigest(),
                    spent_cost_usd=total_cost,
                )
                return ControllerOutcome(review_run_id,"STALLED",round_no,len(blockers),stop_reason=reason)
            previous_blockers=fps
            blocker_ids=[x["finding_id"] for x in blockers]

            gid=self.review.create_fix_graph(review_run_id)
            if not gid:
                self.review.store.set_status(review_run_id,"FAILED")
                return ControllerOutcome(review_run_id,"FAILED",round_no,len(blockers),stop_reason="FIX_GRAPH_MISSING")
            self.review.store.set_status(review_run_id,"WAITING_FIX")
            self.graph_executor.execute_graph(gid)

            new_sha,new_dirty,_=self.subjects.snapshot()
            if new_dirty:
                self.review.store.set_status(review_run_id,"BLOCKED",fix_graph_id=gid)
                return ControllerOutcome(review_run_id,"BLOCKED",round_no,len(blockers),gid,
                                         stop_reason="FIXES_NOT_COMMITTED")
            if new_sha==sha:
                self.review.store.set_status(review_run_id,"STALLED",fix_graph_id=gid)
                return ControllerOutcome(review_run_id,"STALLED",round_no,len(blockers),gid,
                                         stop_reason="NO_NEW_SUBJECT_SHA")

            # The producer cannot satisfy closure by saying tests passed. QDW independently reruns the
            # exact frozen acceptance specs on the new clean subject before allowing re-review closure.
            acceptance=self.review.verify_frozen_acceptance(blocker_ids,cwd=workspace)
            if acceptance["status"]!="PASS":
                self.review.store.set_status(review_run_id,"STALLED",fix_graph_id=gid)
                return ControllerOutcome(review_run_id,"STALLED",round_no,len(blockers),gid,
                                         stop_reason="FROZEN_ACCEPTANCE_FAILED")
            pending_closure=blocker_ids

        blockers=self.review.store.open_findings(review_run_id,policy.block_at)
        self.review.store.set_status(review_run_id,"STALLED")
        return ControllerOutcome(review_run_id,"STALLED",policy.max_rounds,len(blockers),stop_reason="MAX_ROUNDS")
