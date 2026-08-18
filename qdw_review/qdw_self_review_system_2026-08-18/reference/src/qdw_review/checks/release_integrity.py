from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class ReleaseIntegrityCheck(Check):
    module_id="review.release-integrity"

    def run(self,repo:Repo):
        fs=[]
        branch_protection=repo.read(".qdw/review/branch_protection.json")
        # Local scan cannot query GitHub; absence is informational. Current pinned review records live result.
        if not branch_protection:
            fs.append(finding(
                rule_id="QDW-REL-001",module_id=self.module_id,severity=Severity.INFO,
                title="Branch protection cannot be proven from the checkout",
                summary="Release review should ingest GitHub branch-protection/status evidence separately.",
                invariant="V12 requires remote CI evidence and protected release branch policy.",
                evidence=[],
                remediation="Add a GitHub evidence adapter that stores branch protection, required checks and workflow run IDs in the review run.",
                acceptance_tests=["Review certificate distinguishes LOCAL_PROVEN from REMOTE_CI_PROVEN."],
                confidence=.7,
                tags=["github","ci"]
            ))
        return self.result(fs)
