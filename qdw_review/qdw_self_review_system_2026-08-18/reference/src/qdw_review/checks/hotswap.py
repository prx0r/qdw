from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class HotSwapCheck(Check):
    module_id="review.hotswap"

    def run(self,repo:Repo):
        fs=[]
        p=repo.read("src/qdw/hotswap/persistent.py")
        sys=repo.read("src/qdw/system.py")
        if "SELECT alpha, beta" in p and "self._upsert(" in p and "with self.db.tx(immediate=True)" not in p.split("def update",1)[1].split("def mean_and_lower",1)[0]:
            fs.append(finding(
                rule_id="QDW-HOTSWAP-001",module_id=self.module_id,severity=Severity.HIGH,
                title="Persistent bandit update has a lost-update race",
                summary="update reads alpha/beta in one connection and writes the increment later. Concurrent successes can overwrite each other.",
                invariant="Learning updates are atomic and monotonic under concurrency.",
                evidence=[self.evidence(repo,"src/qdw/hotswap/persistent.py","read-modify-write split across transactions")],
                remediation="Use one BEGIN IMMEDIATE transaction or atomic SQL `SET alpha=alpha+?` / `beta=beta+?`; return the committed posterior.",
                acceptance_tests=["Two synchronized concurrent successes increase alpha by exactly 2.", "100 concurrent updates preserve all weight."],
                tags=["bandit","concurrency","learning"]
            ))
        if "self.routes: list[Route] = []" in sys:
            fs.append(finding(
                rule_id="QDW-HOTSWAP-002",module_id=self.module_id,severity=Severity.HIGH,
                title="Route definitions are not actually persistent",
                summary="Posteriors persist, but QDWSystem initializes an empty in-memory route list on restart. The route_definitions table is not used by the composition root.",
                invariant="Routing knowledge includes durable route definitions as well as durable posteriors.",
                evidence=[self.evidence(repo,"src/qdw/system.py","self.routes starts empty on every process")],
                remediation="Implement RouteRegistry backed by route_definitions; load active routes during composition; version dynamic price/capability observations separately.",
                acceptance_tests=["Register route, recreate QDWSystem, route remains available."],
                tags=["routes","persistence"]
            ))
        quota=repo.read("src/qdw/hotswap/quota.py")
        if quota and "self." in quota and "Database" not in quota:
            fs.append(finding(
                rule_id="QDW-HOTSWAP-003",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Quota state appears process-local",
                summary="HotSwap posteriors persist but quota accounting is not backed by the canonical DB.",
                invariant="Quota decisions survive restart when they affect economic routing.",
                evidence=[self.evidence(repo,"src/qdw/hotswap/quota.py","QuotaLedger has no durable Database dependency")],
                remediation="Persist quota reservations/usage or clearly scope QuotaLedger to ephemeral provider snapshots with durable source observations.",
                acceptance_tests=["Restart cannot reset consumed durable quota to full."],
                tags=["quota","persistence"]
            ))
        return self.result(fs)
