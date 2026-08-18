"""Native deterministic reviewer adapter.

For integration, port the full rule set from `reference/src/qdw_review/checks.py` here. This minimal
engine provides the canonical storage contract and supports plugin rules.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol,Iterable
import hashlib
from .models import ReviewerFinding,ReviewerResult

class StaticRule(Protocol):
    rule_id:str
    version:str
    def check(self, repo_root:Path) -> Iterable[ReviewerFinding]: ...

class StaticRuleEngine:
    reviewer_id="review.static"
    version="2.0.0"

    def __init__(self,rules:Iterable[StaticRule]):
        self.rules=tuple(rules)

    def run(self,repo_root:str|Path)->ReviewerResult:
        root=Path(repo_root).resolve()
        findings=[]
        for rule in self.rules:
            produced=list(rule.check(root))
            for finding in produced:
                if finding.severity in {"CRITICAL","HIGH"} and not finding.acceptance_specs:
                    raise ValueError(
                        f"blocking static rule {finding.rule_id} has no frozen acceptance_specs"
                    )
            findings.extend(produced)
        return ReviewerResult(
            self.reviewer_id,self.version,"ok",tuple(findings),
            summary=f"{len(findings)} deterministic findings",
        )

def file_evidence(root:Path,rel:str,detail:str)->dict:
    p=root/rel
    return {
        "kind":"source",
        "path":rel,
        "detail":detail,
        "content_sha256":hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,
    }
