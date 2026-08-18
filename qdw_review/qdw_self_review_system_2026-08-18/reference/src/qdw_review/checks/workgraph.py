from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class WorkGraphCheck(Check):
    module_id="review.workgraph"

    def run(self,repo:Repo):
        fs=[]
        text=repo.read("src/qdw/core/graph/store.py")
        if "expected_value=nv if nv is not None else 1.0" in text or "expected_cost=nc if nc is not None else 0.0" in text:
            fs.append(finding(
                rule_id="QDW-GRAPH-001",module_id=self.module_id,severity=Severity.HIGH,
                title="UNKNOWN economics are still coerced to fabricated values",
                summary="claim_ready says UNKNOWN is preserved but substitutes unknown value with 1.0 and unknown cost with 0.0 before scheduling.",
                invariant="UNKNOWN != ZERO and UNKNOWN != arbitrary optimistic default.",
                evidence=[self.evidence(repo,"src/qdw/core/graph/store.py","None economics replaced with 1.0/0.0")],
                remediation="Represent unknown explicitly in Candidate; policy must either block, route to information-gathering, or use an explicit prior with provenance and uncertainty.",
                acceptance_tests=[
                    "Unknown expected_cost cannot silently beat a known positive cost.",
                    "Unknown expected_value is not treated as 1.0.",
                    "Scheduler emits a reason code for unknown economics."
                ],
                tags=["scheduler","economics","unknown"]
            ))
        claim=text.split("def claim_ready",1)[1] if "def claim_ready" in text else ""
        if "validate_dag(" not in claim:
            fs.append(finding(
                rule_id="QDW-GRAPH-002",module_id=self.module_id,severity=Severity.MEDIUM,
                title="DAG validation exists but is not enforced before execution",
                summary="validate_dag is callable, but claim_ready does not require a frozen/validated graph.",
                invariant="Only validated immutable WorkGraphs are executable.",
                evidence=[self.evidence(repo,"src/qdw/core/graph/store.py","claim_ready does not enforce validate_dag")],
                remediation="Introduce DRAFT→VALIDATED/FROZEN→RUNNING graph lifecycle and reject claims on non-validated graphs.",
                acceptance_tests=["A cyclic graph cannot yield a claim."],
                tags=["graph","lifecycle"]
            ))
        if 'n["attempt_count"] <= n["max_retries"]' in text and 'attempt_count"] >= r["max_retries"]' in text:
            fs.append(finding(
                rule_id="QDW-GRAPH-003",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Retry ceiling semantics are inconsistent",
                summary="Explicit failure allows retry at attempt_count == max_retries while stale reclaim fails at >= max_retries.",
                invariant="max_attempts/retries has one documented meaning across all failure paths.",
                evidence=[self.evidence(repo,"src/qdw/core/graph/store.py","retry boundary differs between fail and stale reclaim")],
                remediation="Rename to max_attempts or define max_retries precisely; centralize transition policy and property-test every boundary.",
                acceptance_tests=["All failure mechanisms agree at N-1/N/N+1 attempt boundaries."],
                tags=["retry","state-machine"]
            ))
        return self.result(fs)
