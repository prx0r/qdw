from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

REQUIRED_EXECUTION_TOKENS = [
    "WorkGraphStore",
    "FactoryRegistry",
    "Executor",
    "certificate",
    ".release(",
]

class E2ECheck(Check):
    module_id="review.e2e"

    def run(self,repo:Repo):
        fs=[]
        paths=[repo.rel(p) for p in repo.rglob("test_e2e.py")]
        text="\n".join(repo.read(p) for p in paths)
        missing=[x for x in REQUIRED_EXECUTION_TOKENS if x not in text]
        if paths and missing:
            fs.append(finding(
                rule_id="QDW-E2E-001",module_id=self.module_id,severity=Severity.HIGH,
                title="Current E2E does not cross the execution/certification spine",
                summary="The test reaches product creation by direct service calls but does not prove WorkGraph→executor→artifact→certificate→release. Missing signals: "+", ".join(missing),
                invariant="V10 proves the canonical economic/execution path, not only data-layer service interoperability.",
                evidence=[self.evidence(repo,p,"E2E test inspected") for p in paths[:3]],
                remediation="Create one gold-standard factory fixture driven through QDWSystem: observation→opportunity→idea→factory run→frozen graph→route→executor→artifact→independent review→certificate→release→outcome.",
                acceptance_tests=[
                    "Removing executor execution makes V10 fail.",
                    "Mutating artifact before release makes V10 fail.",
                    "Replacing certificate with unrelated valid certificate makes V10 fail."
                ],
                tags=["e2e","v10","factory"]
            ))
        return self.result(fs)
