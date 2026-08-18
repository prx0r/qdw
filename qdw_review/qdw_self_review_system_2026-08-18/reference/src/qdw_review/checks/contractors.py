from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class ContractorCheck(Check):
    module_id="review.contractors"

    def run(self,repo:Repo):
        fs=[]
        text=repo.read("src/qdw/contractors/registry.py")
        if "ON CONFLICT(contractor_id,version) DO UPDATE" in text:
            fs.append(finding(
                rule_id="QDW-CONTRACTOR-001",module_id=self.module_id,severity=Severity.HIGH,
                title="Contractor versions are mutable",
                summary="Re-registering contractor_id@version overwrites definition_hash and manifest_json.",
                invariant="A versioned contractor definition is immutable; history must remain reproducible.",
                evidence=[self.evidence(repo,"src/qdw/contractors/registry.py","ON CONFLICT updates same contractor version")],
                remediation="If existing hash differs, raise and require a version bump. Identical manifest registration may be idempotent.",
                acceptance_tests=["Mutating one gate without version bump is rejected.", "Old Product Genome resolves the original contractor hash."],
                tags=["contractor","immutability"]
            ))
        if "def activate" in text and "certificate" not in text.split("def activate",1)[1]:
            fs.append(finding(
                rule_id="QDW-CONTRACTOR-002",module_id=self.module_id,severity=Severity.HIGH,
                title="Contractor activation is not certified",
                summary="Activation is a status flip without proving fixture behavior or required gates.",
                invariant="Global reusable quality contractors are activated only after their own contract is proven.",
                evidence=[self.evidence(repo,"src/qdw/contractors/registry.py","activate has no evidence/certificate input")],
                remediation="Add contractor_fixture_runs/certificates and require a bound certificate.",
                acceptance_tests=["A CANDIDATE contractor cannot become ACTIVE without fixture certificate."],
                tags=["contractor","verification"]
            ))
        return self.result(fs)
