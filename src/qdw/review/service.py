from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from qdw.core import hash_object,canonical_json,new_id,utc_now
from .models import ReviewRequest,Severity
from .store import ReviewStore
from .planner import ReviewPlanner
from .fix_planner import FixPlanner
from .attacks import AttackCatalog,AttackRunner
from .certificate import ReviewCertificateService
from .report import ReviewReportService
from .pack import NativeReviewPackBuilder
from .acceptance import AcceptanceRunner
from .closure import FindingClosureService

class ReviewPrerequisiteError(RuntimeError):
    pass

class ReviewService:
    """Single canonical owner of review lifecycle state."""

    def __init__(self,*,db,ledger,graphs,reviewers,verification,attack_catalog_path,
                 static_engine=None):
        self.db,self.ledger,self.graphs=db,ledger,graphs
        self.store=ReviewStore(db,ledger)
        self.reviewers=reviewers
        self.planner=ReviewPlanner(graphs,reviewers)
        self.fix_planner=FixPlanner(graphs,db)
        self.attacks=AttackRunner(db,ledger,verification)
        self.attack_catalog=AttackCatalog(attack_catalog_path)
        self.certificates=ReviewCertificateService(self.store)
        self.reports=ReviewReportService(self.store)
        self.packs=NativeReviewPackBuilder(self.store,self.reports)
        self.static_engine=static_engine
        def _static_rule_fires(rule_id,cwd):
            if self.static_engine is None:return True
            result=self.static_engine.run(Path(cwd))
            return any(f.rule_id==rule_id for f in result.findings)
        self.acceptance=AcceptanceRunner(
            db,ledger,verification,static_rule_checker=_static_rule_fires,attack_runner=self.attacks
        )
        self.closures=FindingClosureService(db,ledger)

    def start(self,request:ReviewRequest)->str:
        return self.store.create_run(request)

    def begin_round(self,review_run_id:str,*,subject_sha:str,changed_paths:tuple[str,...],
                    profile:str,policy,repo_root:str|Path=".")->dict:
        definitions=self.reviewers.select(changed_paths,profile)
        required=set(policy.required_reviewers)
        all_defs={d["contractor_id"]:d for d in self.reviewers.definitions(include_inactive=True)}
        inactive=[
            rid for rid in sorted(required)
            if rid not in all_defs or all_defs[rid].get("registry_status")!="ACTIVE"
        ]
        if inactive:
            self.store.set_status(review_run_id,"BLOCKED")
            raise ReviewPrerequisiteError(
                "REVIEWER_NOT_ACTIVE: "+", ".join(inactive)
            )
        active_by_id={d["contractor_id"]:d for d in self.reviewers.definitions()}
        for rid in required:
            if rid in active_by_id and active_by_id[rid] not in definitions:
                definitions.append(active_by_id[rid])

        reviewer_set_hash=hash_object(sorted(
            (x["contractor_id"],x["version"],x["definition_hash"]) for x in definitions
        ))
        attacks=self.attack_catalog.select(policy.required_attacks)
        attack_set_hash=hash_object(sorted((x.attack_id,x.version) for x in attacks))
        round_id=self.store.start_round(review_run_id,subject_sha,reviewer_set_hash,attack_set_hash)

        static_finding_ids=[]
        if self.static_engine is not None:
            result=self.static_engine.run(Path(repo_root))
            mid=self.store.create_module_run(
                round_id,result.reviewer_id,result.reviewer_version,
                hash_object({"reviewer_id":result.reviewer_id,"version":result.reviewer_version}),
            )
            static_finding_ids=self.store.ingest_result(review_run_id,round_id,mid,result,subject_sha)

        graph_id,nodes=self.planner.plan_semantic_graph(
            review_run_id=review_run_id,round_id=round_id,changed_paths=changed_paths,
            profile=profile,policy=policy,subject_sha=subject_sha,
        )
        self.store.set_status(review_run_id,"REVIEWING")
        return {
            "round_id":round_id,
            "review_graph_id":graph_id,
            "reviewers":[x["definition"]["contractor_id"] for x in nodes],
            "static_finding_ids":static_finding_ids,
            "attacks":[x.attack_id for x in attacks],
        }

    def run_attacks(self,review_run_id:str,round_id:str,policy,*,cwd:str|Path,subject_sha:str)->list[dict]:
        self.store.set_status(review_run_id,"ATTACKING")
        return [
            self.attacks.run(round_id,attack,cwd=cwd,subject_sha=subject_sha)
            for attack in self.attack_catalog.select(policy.required_attacks)
        ]

    def freeze_acceptance_for_open_findings(self,review_run_id:str,subject_sha:str)->list[str]:
        """Return frozen acceptance IDs for blockers.

        Blocking findings must arrive with acceptance specs from the reviewer/static rule.
        The producer/controller is not allowed to invent the test after seeing the finding.
        """
        ids=[]
        missing=[]
        findings=self.store.open_findings(review_run_id,Severity.HIGH)
        with self.db.connect() as con:
            for finding in findings:
                rows=con.execute("""SELECT a.acceptance_spec_id,a.spec_hash
                    FROM review_acceptance_specs a
                    JOIN review_finding_acceptance fa
                      ON fa.acceptance_spec_id=a.acceptance_spec_id
                    WHERE fa.finding_id=? ORDER BY a.frozen_at""",
                    (finding["finding_id"],)).fetchall()
                if not rows:
                    missing.append(finding["finding_id"])
                else:
                    ids.extend(r["acceptance_spec_id"] for r in rows)
        if missing:
            self.store.set_status(review_run_id,"BLOCKED")
            raise ReviewPrerequisiteError(
                "BLOCKER_WITHOUT_FROZEN_ACCEPTANCE: "+", ".join(missing)
            )
        return ids


    def verify_frozen_acceptance(self,finding_ids:list[str],*,cwd:str|Path)->dict:
        results={}
        all_pass=True
        for fid in finding_ids:
            rows=self.acceptance.run_for_finding(fid,cwd=cwd)
            results[fid]=rows
            if not rows or any(x["status"]!="PASS" for x in rows):all_pass=False
        return {"status":"PASS" if all_pass else "FAIL","findings":results}

    def close_prior_findings(self,finding_ids:list[str],*,new_subject_sha:str,recheck_round_id:str)->list[str]:
        closed=[]
        for fid in finding_ids:
            if self.closures.close(fid,new_subject_sha=new_subject_sha,recheck_round_id=recheck_round_id):
                closed.append(fid)
        return closed

    def create_fix_graph(self,review_run_id:str)->str|None:
        blockers=self.store.open_findings(review_run_id,Severity.HIGH)
        if not blockers:
            return None
        gid=self.fix_planner.create_fix_graph(review_run_id,blockers)
        self.store.set_status(review_run_id,"NEEDS_FIX",fix_graph_id=gid)
        return gid

    def report(self,review_run_id:str)->dict:
        return self.reports.build(review_run_id)

    def export_pack(self,review_run_id:str,output_zip:str|Path)->dict:
        return self.packs.export(review_run_id,output_zip)
