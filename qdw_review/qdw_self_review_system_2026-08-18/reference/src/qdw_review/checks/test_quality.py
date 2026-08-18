from __future__ import annotations
import ast
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class TestQualityCheck(Check):
    module_id="review.test-quality"

    def run(self,repo:Repo):
        fs=[]
        skip_hits=[]
        for p in repo.rglob("test_*.py"):
            rel=repo.rel(p);text=repo.read(rel)
            if "pytest.skip(" in text or "pytest.xfail(" in text or "@pytest.mark.skip" in text or "@pytest.mark.xfail" in text:
                skip_hits.append(rel)
        if skip_hits:
            fs.append(finding(
                rule_id="QDW-TEST-001",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Required test tree contains skip/xfail escape hatches",
                summary="Tests contain skip/xfail constructs that can weaken release evidence unless policy explicitly classifies them optional.",
                invariant="Mandatory release gates have zero skips/xfails.",
                evidence=[self.evidence(repo,p,"skip/xfail present") for p in skip_hits[:10]],
                remediation="Remove from mandatory tests or explicitly classify optional suites and assert zero skipped mandatory tests from JUnit.",
                acceptance_tests=["Release JUnit has skipped=0 for mandatory suites."],
                tags=["anti-cheat","tests"]
            ))
        return self.result(fs)
