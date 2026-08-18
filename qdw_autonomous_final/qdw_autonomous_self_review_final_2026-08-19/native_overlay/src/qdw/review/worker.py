from __future__ import annotations
from typing import Any
from qdw.executors.protocol import ExecutionRequest,Executor
from .models import ReviewerFinding,ReviewerResult

_REQUIRED_FINDING={"rule_id","severity","title","summary","invariant","remediation"}

def _parse_findings(items)->tuple[ReviewerFinding,...]:
    out=[]
    for raw in items or []:
        missing=_REQUIRED_FINDING-set(raw)
        if missing:
            raise ValueError(f"reviewer finding missing {sorted(missing)}")
        specs=tuple(raw.get("acceptance_specs",()))
        if raw["severity"] in {"CRITICAL","HIGH"} and not specs:
            raise ValueError(
                f"blocking reviewer finding {raw['rule_id']} requires executable acceptance_specs"
            )
        out.append(ReviewerFinding(
            raw["rule_id"],raw["severity"],raw["title"],raw["summary"],raw["invariant"],
            raw["remediation"],tuple(raw.get("evidence",())),tuple(raw.get("acceptance_tests",())),
            specs,float(raw.get("confidence",1.0)),
        ))
    return tuple(out)

class SemanticReviewWorker:
    """Run one semantic reviewer through the normal QDW Executor protocol.

    The executor cannot certify. It only returns a typed review artifact.
    """
    def __init__(self,executor:Executor):
        self.executor=executor

    def run(self,*,review_run_id:str,module_run_id:str,definition:dict,prompt:str,
            subject_sha:str,workspace:str,changed_paths:tuple[str,...],budget_usd:float|None=None)->ReviewerResult:
        contract = """
Return a JSON object using the executor's normal envelope and include:
"review_result": {
  "status": "ok|blocked|failed",
  "summary": "...",
  "findings": [{
    "rule_id":"...", "severity":"CRITICAL|HIGH|MEDIUM|LOW|INFO",
    "title":"...", "summary":"...", "invariant":"...",
    "remediation":"...", "evidence":[...], "acceptance_tests":[...],
    "acceptance_specs":[
      {"kind":"command","id":"...","argv":["pytest","..."],"expected_exit_code":0},
      {"kind":"inline_pytest","id":"...","filename":"test_review_x.py","content":"..."},
      {"kind":"attack","attack_id":"A01"},
      {"kind":"static_rule","rule_id":"..."}
    ],
    "confidence":0.0
  }]
}
A PASS statement is not certification. Findings require evidence.
"""
        request=ExecutionRequest(
            run_id=review_run_id,node_id=module_run_id,task_kind="peer_review",
            prompt=prompt+"\n\n"+contract,
            payload={
                "subject_git_sha":subject_sha,
                "reviewer_id":definition["contractor_id"],
                "reviewer_version":definition["version"],
                "definition_hash":definition["definition_hash"],
                "changed_paths":changed_paths,
            },
            workspace=workspace,
            timeout_seconds=int(definition.get("timeout_seconds",900)),
            budget_usd=budget_usd if budget_usd is not None else definition.get("default_budget_usd"),
            required_capabilities=tuple(definition.get("required_capabilities",())),
        )
        result=self.executor.execute(request)
        if not result.ok:
            return ReviewerResult(
                definition["contractor_id"],definition["version"],"failed",(),
                summary=result.stderr or result.status,
            )
        rr=result.final.get("review_result")
        if not isinstance(rr,dict):
            raise ValueError("executor returned no typed review_result")
        status=rr.get("status","failed")
        findings=_parse_findings(rr.get("findings",()))
        return ReviewerResult(
            definition["contractor_id"],definition["version"],status,findings,
            rr.get("summary",""),tuple(result.final.get("evidence",())),
            float(result.metadata.get("cost_usd",0.0) or 0.0),
        )
