from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class ProofCheck(Check):
    module_id = "review.proof"

    def run(self, repo: Repo):
        fs=[]
        script=repo.read("scripts/build_certificate.py")
        cert=repo.read("src/qdw/proof/certificate.py")
        if "required_commands=[]" in script.replace(" ", "") or "required_commands = []" in script:
            fs.append(finding(
                rule_id="QDW-PROOF-001",module_id=self.module_id,severity=Severity.CRITICAL,
                title="Build certificate can be vacuously PROVEN",
                summary="The production certificate script supplies no required commands, so a trivial unrelated receipt can satisfy the proof boundary.",
                invariant="PROVEN requires a frozen non-empty acceptance specification and every mandatory receipt.",
                evidence=[self.evidence(repo,"scripts/build_certificate.py","builder.issue() receives an empty required_commands list")],
                remediation="Load a frozen AcceptanceSpec by task/build ID; require every command and negative test from that spec. Refuse empty mandatory command sets for release certificates.",
                acceptance_tests=[
                    "A single successful `python -c print(1)` receipt cannot certify a release.",
                    "Deleting one mandatory receipt makes issuance fail.",
                    "A release acceptance spec with zero required commands is rejected."
                ],
                tags=["certificate","anti-cheat"]
            ))
        if 'acceptance_spec_hash="manual_review"' in script or "acceptance_spec_hash='manual_review'" in script:
            fs.append(finding(
                rule_id="QDW-PROOF-002",module_id=self.module_id,severity=Severity.HIGH,
                title="Acceptance spec hash is not a hash",
                summary="The release script hard-codes `manual_review` instead of binding a frozen acceptance specification.",
                invariant="Every certificate binds immutable acceptance criteria by content hash.",
                evidence=[self.evidence(repo,"scripts/build_certificate.py","hard-coded manual_review acceptance hash")],
                remediation="Load the task's frozen spec, recompute SHA-256, and bind that digest into the certificate.",
                acceptance_tests=["Changing the acceptance spec after execution invalidates certification."],
                tags=["certificate","acceptance"]
            ))
        if "def verify_certificate" in cert and "artifact" not in cert.split("def verify_certificate",1)[1]:
            fs.append(finding(
                rule_id="QDW-PROOF-003",module_id=self.module_id,severity=Severity.HIGH,
                title="Certificate verification checks envelope hash but not evidence",
                summary="The verifier checks the self-contained certificate hash/status but does not recompute artifact hashes, validate receipts, or validate the acceptance spec.",
                invariant="Certificate verification must revalidate every bound subject and mandatory receipt.",
                evidence=[self.evidence(repo,"src/qdw/proof/certificate.py","verify_certificate does not re-verify artifacts/receipts/spec")],
                remediation="Implement full verification: certificate hash, acceptance spec hash, receipt files/log hashes/exit codes/git state, artifact hashes, ledger root and optional signature.",
                acceptance_tests=[
                    "Mutating a certified artifact makes verification fail.",
                    "Deleting a receipt makes verification fail.",
                    "Replacing the acceptance spec makes verification fail."
                ],
                tags=["certificate","provenance"]
            ))
        return self.result(fs)
