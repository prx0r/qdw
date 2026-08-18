from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class ClaimConsistencyCheck(Check):
    module_id="review.claim-consistency"

    def run(self,repo:Repo):
        fs=[]
        graph=repo.read("src/qdw/core/graph/store.py")
        system=repo.read("src/qdw/system.py")
        migrations=repo.read("src/qdw/core/migrations.py")
        if "UNKNOWN cost is preserved as unknown" in graph and ("else 0.0" in graph or "else 1.0" in graph):
            fs.append(finding(
                rule_id="QDW-CLAIM-001",module_id=self.module_id,severity=Severity.HIGH,
                title="Code comment claims UNKNOWN preservation while code fabricates defaults",
                summary="This is a documentation/implementation contradiction that can cause false confidence in peer review.",
                invariant="High-level guarantees are mechanically consistent with implementation.",
                evidence=[self.evidence(repo,"src/qdw/core/graph/store.py","claim contradicts None→default conversion")],
                remediation="Fix semantics first, then make invariant executable as a test. Reviewer should treat invariant comments as hypotheses, never evidence.",
                acceptance_tests=["Invariant test proves unknown economic inputs remain typed unknown."],
                tags=["claims","unknown"]
            ))
        if "single composition root" in system.lower():
            expected=["WorldStore","IdeaService","HumanQueue","ProductRegistry","ContractorRegistry"]
            if any(x not in system for x in expected):
                fs.append(finding(
                    rule_id="QDW-CLAIM-002",module_id=self.module_id,severity=Severity.MEDIUM,
                    title="Composition-root claim is broader than actual wiring",
                    summary="QDWSystem docstring says all registries/services are injected there while multiple global services are absent.",
                    invariant="Architecture claims match the instantiated dependency graph.",
                    evidence=[self.evidence(repo,"src/qdw/system.py","single composition root claim")],
                    remediation="Either wire all canonical services or narrow the claim until complete.",
                    acceptance_tests=["Architecture reviewer maps every canonical service to exactly one composition owner."],
                    tags=["claims","architecture"]
                ))
        if "transactional" in migrations.lower() and "executescript(sql)" in migrations and "BEGIN" not in migrations:
            fs.append(finding(
                rule_id="QDW-CLAIM-003",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Migration runner claims transactional behavior not demonstrated by its code",
                summary="The module-level claim should be backed by a forced halfway-failure test.",
                invariant="Claims about durability are proven under injected failure.",
                evidence=[self.evidence(repo,"src/qdw/core/migrations.py","transactional docstring vs executescript pattern")],
                remediation="Add an explicit transactional strategy and negative test.",
                acceptance_tests=["Half-failing migration leaves DB unchanged."],
                tags=["claims","migration"]
            ))
        return self.result(fs)
