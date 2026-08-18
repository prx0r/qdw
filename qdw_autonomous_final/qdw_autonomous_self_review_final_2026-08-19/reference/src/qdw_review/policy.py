from __future__ import annotations
from dataclasses import dataclass
from .models import ReviewReport,Severity

@dataclass(frozen=True)
class ReviewPolicy:
    policy_id:str
    block_at:Severity=Severity.HIGH
    required_modules:tuple[str,...]=()
    required_attacks:tuple[str,...]=()
    require_clean_subject:bool=True
    require_remote_ci:bool=False
    max_rounds:int=4
    max_cost_usd:float|None=5.0
    allow_suppressions:bool=True

    @classmethod
    def from_dict(cls,d):
        return cls(
            d["policy_id"],Severity.parse(d.get("block_at","HIGH")),
            tuple(d.get("required_modules",())),
            tuple(d.get("required_attacks",())),
            bool(d.get("require_clean_subject",True)),
            bool(d.get("require_remote_ci",False)),
            int(d.get("max_rounds",4)),
            d.get("max_cost_usd",5.0),
            bool(d.get("allow_suppressions",True)),
        )

def evaluate(report:ReviewReport,policy:ReviewPolicy,attack_results=(),remote_ci:bool|None=None)->dict:
    blockers=[
        f for f in report.findings
        if f.status=="OPEN" and f.severity>=policy.block_at
    ]
    ran={m.module_id for m in report.modules}
    missing_modules=sorted(set(policy.required_modules)-ran)
    by_attack={a.get("attack_id"):a for a in attack_results}
    missing_attacks=sorted(set(policy.required_attacks)-set(by_attack))
    failed_attacks=sorted(
        a for a in policy.required_attacks
        if a in by_attack and by_attack[a].get("status")!="PASS"
    )
    reasons=[]
    if policy.require_clean_subject and report.subject.dirty:
        reasons.append("DIRTY_SUBJECT")
    if blockers: reasons.append("BLOCKING_FINDINGS")
    if missing_modules: reasons.append("MISSING_REVIEWERS")
    if missing_attacks: reasons.append("MISSING_ATTACKS")
    if failed_attacks: reasons.append("FAILED_ATTACKS")
    if policy.require_remote_ci and remote_ci is not True: reasons.append("REMOTE_CI_UNPROVEN")
    return {
        "status":"PASS" if not reasons else "FAIL",
        "reasons":reasons,
        "blocker_fingerprints":[x.fingerprint for x in blockers],
        "missing_modules":missing_modules,
        "missing_attacks":missing_attacks,
        "failed_attacks":failed_attacks,
    }
