from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

EXPECTED_IF_PRESENT = {
    "src/qdw/world/store.py": "WorldStore",
    "src/qdw/intelligence/painfinder.py": "PainFinder",
    "src/qdw/intelligence/stack_oracle.py": "StackOracle",
    "src/qdw/intelligence/opportunities.py": "OpportunityStore",
    "src/qdw/ideas/service.py": "IdeaService",
    "src/qdw/human/queue.py": "HumanQueue",
    "src/qdw/contractors/registry.py": "ContractorRegistry",
    "src/qdw/products/registry.py": "ProductRegistry",
    "src/qdw/watch/service.py": "WatchService",
    "src/qdw/catalog/service.py": "GlobalCatalog",
}

class CompositionCheck(Check):
    module_id="review.architecture"

    def run(self,repo:Repo):
        fs=[]
        system=repo.read("src/qdw/system.py")
        missing=[name for path,name in EXPECTED_IF_PRESENT.items() if repo.exists(path) and name not in system]
        if missing:
            fs.append(finding(
                rule_id="QDW-ARCH-001",module_id=self.module_id,severity=Severity.HIGH,
                title="QDWSystem is not yet the single composition root it claims to be",
                summary="Global infrastructure modules exist but are not composed/injected by QDWSystem: "+", ".join(missing),
                invariant="Interfaces and workflows obtain one shared canonical service graph from QDWSystem.",
                evidence=[self.evidence(repo,"src/qdw/system.py","global services absent from composition root")],
                remediation="Compose global services once in dependency order and make API/MCP/CLI/fixtures use that system instance rather than manually constructing services.",
                acceptance_tests=["Canonical E2E uses QDWSystem only for service access.", "No interface creates private DB/router/service instances."],
                tags=["composition","wiring"]
            ))
        return self.result(fs,notes=[f"Expected global services missing from system: {len(missing)}"])
