from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class TrustBoundaryCheck(Check):
    module_id="review.trust-boundary"

    def run(self,repo:Repo):
        fs=[]
        factory=repo.read("src/qdw/factories/registry.py")
        product=repo.read("src/qdw/products/registry.py")
        contractor=repo.read("src/qdw/contractors/registry.py")
        idea=repo.read("src/qdw/ideas/pipeline.py")

        if "SELECT * FROM gate_results WHERE gate_result_id=?" in factory:
            fs.append(finding(
                rule_id="QDW-TRUST-001",module_id=self.module_id,severity=Severity.CRITICAL,
                title="Factory activation accepts an unrelated passing gate as a certificate",
                summary="Factory activation resolves fixture_certificate_id against gate_results and only checks `passed`; it does not bind factory/version/fixture/artifacts.",
                invariant="Evidence IDs must prove the exact subject, version, fixture and artifacts they authorize.",
                evidence=[self.evidence(repo,"src/qdw/factories/registry.py","activation queries gate_results by arbitrary ID")],
                remediation="Require a real fixture certificate record containing factory_id, factory_version, fixture_id, artifact digests, acceptance hash and independent gate evidence. Verify all bindings before activation.",
                acceptance_tests=[
                    "A passing gate from another factory cannot activate this factory.",
                    "A certificate for another version cannot activate this version.",
                    "Mutating fixture artifacts prevents activation."
                ],
                tags=["factory","substitution-attack"]
            ))
        if "SET status='RELEASED',certificate_id=?" in product and "SELECT" not in product.split("def release",1)[1].split("def passport",1)[0]:
            fs.append(finding(
                rule_id="QDW-TRUST-002",module_id=self.module_id,severity=Severity.CRITICAL,
                title="Product release accepts arbitrary certificate IDs",
                summary="ProductRegistry.release writes a supplied certificate_id without validating its existence, status, run/product binding or artifact hashes.",
                invariant="Release is authorized only by a valid certificate bound to the product build.",
                evidence=[self.evidence(repo,"src/qdw/products/registry.py","release updates certificate_id without certificate lookup")],
                remediation="Resolve and fully verify certificate; require product.build_run_id == certificate.factory_run_id and release artifacts match certified subjects.",
                acceptance_tests=[
                    "Unknown certificate ID cannot release a product.",
                    "Certificate from another product/run cannot release a product.",
                    "Failed/revoked certificate cannot release."
                ],
                tags=["release","certificate"]
            ))
        if "def activate" in contractor and "fixture" not in contractor.split("def activate",1)[1]:
            fs.append(finding(
                rule_id="QDW-TRUST-003",module_id=self.module_id,severity=Severity.HIGH,
                title="Contractor activation has no proof gate",
                summary="Any registered contractor version can be marked ACTIVE without fixture, acceptance or certification evidence.",
                invariant="Reusable global contractors must prove their contract before activation.",
                evidence=[self.evidence(repo,"src/qdw/contractors/registry.py","activate only flips status")],
                remediation="Give each contractor manifest a fixture/acceptance contract and require a bound contractor fixture certificate for activation.",
                acceptance_tests=["Uncertified contractor activation is rejected."],
                tags=["contractor","activation"]
            ))
        if "passed: bool" in idea:
            fs.append(finding(
                rule_id="QDW-TRUST-004",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Idea review trusts caller-supplied PASS",
                summary="IdeaReviewPipeline converts a boolean supplied by the caller directly into PASS/BUILD_READY.",
                invariant="Important review decisions should reference reviewer evidence, not an unbound boolean.",
                evidence=[self.evidence(repo,"src/qdw/ideas/pipeline.py","review accepts passed: bool")],
                remediation="Accept a ReviewDecision/ReviewCertificate ID from a registered reviewer; independently check evidence and policy. Keep manual decisions explicitly typed as HUMAN_OVERRIDE.",
                acceptance_tests=["BUILD_READY cannot be produced from only `passed=True`."],
                tags=["ideas","review"]
            ))
        return self.result(fs)
