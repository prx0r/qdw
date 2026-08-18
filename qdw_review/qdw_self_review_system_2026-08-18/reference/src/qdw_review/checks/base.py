from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256
from qdw_review.models import Evidence, Finding, ModuleResult, Severity
from qdw_review.repo import Repo

class Check(ABC):
    module_id = "base"
    version = "1.0.0"

    @abstractmethod
    def run(self, repo: Repo) -> ModuleResult:
        raise NotImplementedError

    def result(self, findings: list[Finding], notes: list[str] | None = None) -> ModuleResult:
        return ModuleResult(
            module_id=self.module_id,
            version=self.version,
            status="FAIL" if any(f.severity >= Severity.HIGH for f in findings) else "PASS",
            findings=findings,
            notes=notes or [],
        )

    def evidence(self, repo: Repo, path: str, detail: str, line: int | None = None) -> Evidence:
        text = repo.read(path)
        return Evidence(
            kind="source",
            path=path,
            line=line,
            detail=detail,
            sha256=sha256(text.encode()).hexdigest() if text else None,
        )

def finding(
    *,
    rule_id: str,
    module_id: str,
    severity: Severity,
    title: str,
    summary: str,
    invariant: str,
    evidence: list[Evidence],
    remediation: str,
    acceptance_tests: list[str],
    reproduction: list[str] | None = None,
    confidence: float = 1.0,
    tags: list[str] | None = None,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        module_id=module_id,
        severity=severity,
        title=title,
        summary=summary,
        invariant=invariant,
        evidence=evidence,
        remediation=remediation,
        acceptance_tests=acceptance_tests,
        reproduction=reproduction or [],
        confidence=confidence,
        tags=tags or [],
    )
