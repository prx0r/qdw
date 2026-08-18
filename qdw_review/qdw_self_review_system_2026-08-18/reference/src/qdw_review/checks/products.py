from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class ProductCheck(Check):
    module_id="review.products"

    def run(self,repo:Repo):
        fs=[]
        text=repo.read("src/qdw/products/registry.py")
        if "factory_id: str | None = None" in text and "build_run_id: str | None = None" in text:
            fs.append(finding(
                rule_id="QDW-PRODUCT-001",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Canonical product creation permits missing factory lineage",
                summary="ProductRegistry.create can create a product with no factory/version/build run, while Product Passport is intended to preserve build lineage.",
                invariant="Factory-produced products must bind their originating factory run; manually imported products must be explicitly typed.",
                evidence=[self.evidence(repo,"src/qdw/products/registry.py","factory/build lineage parameters are all optional")],
                remediation="Separate `create_from_factory(certified_run_id, ...)` from `import_external_product(...)`; make lineage mandatory for factory output.",
                acceptance_tests=["Factory-created product without certified run is rejected."],
                tags=["product","lineage"]
            ))
        if 'source: str = "manual"' in text:
            fs.append(finding(
                rule_id="QDW-PRODUCT-002",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Outcome authority is not typed",
                summary="Any caller can record numeric outcomes with arbitrary source strings; downstream learning could treat synthetic/manual values like measured telemetry.",
                invariant="Outcome learning distinguishes fixture, manual, estimated and externally measured evidence.",
                evidence=[self.evidence(repo,"src/qdw/products/registry.py","outcome accepts arbitrary source/evidence")],
                remediation="Add outcome authority/type, evidence digest, adapter identity and learning_eligible flag. Fixture/test outcomes must never update production policy.",
                acceptance_tests=["Fixture outcome is excluded from production learning.", "Measured outcome requires evidence/source adapter identity."],
                tags=["outcome","learning"]
            ))
        return self.result(fs)
