from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class HumanQueueCheck(Check):
    module_id="review.human-queue"

    def run(self,repo:Repo):
        fs=[]
        text=repo.read("src/qdw/human/queue.py")
        transition=text.split("def _transition",1)[1] if "def _transition" in text else ""
        if transition and "actor" not in transition and "principal" not in transition:
            fs.append(finding(
                rule_id="QDW-HUMAN-001",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Human approvals do not bind an actor identity",
                summary="The state machine is strict, but approval/decline payloads are arbitrary dictionaries with no required decision principal or authentication envelope.",
                invariant="Irreversible human decisions are attributable to a specific authenticated principal or explicitly typed local override.",
                evidence=[self.evidence(repo,"src/qdw/human/queue.py","approval transition has no actor/principal field")],
                remediation="Add decision_actor, actor_type, decision_source, evidence/signature/session metadata as appropriate; distinguish local-owner override from remote authorization.",
                acceptance_tests=["Approval lacking required actor identity is rejected under production policy."],
                tags=["human","authorization"]
            ))
        return self.result(fs)
