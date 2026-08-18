from __future__ import annotations
from qdw_review.checks.base import Check, finding
from qdw_review.models import Severity
from qdw_review.repo import Repo

class IdeaCheck(Check):
    module_id="review.ideas"

    def run(self,repo:Repo):
        fs=[]
        text=repo.read("src/qdw/ideas/service.py")
        if "ON CONFLICT(idea_id) DO UPDATE" in text:
            fs.append(finding(
                rule_id="QDW-IDEA-001",module_id=self.module_id,severity=Severity.MEDIUM,
                title="Idea Cemetery overwrites prior burial episodes",
                summary="Burying the same idea again updates its single cemetery row, erasing earlier rejection assumptions/triggers from the structured table.",
                invariant="Historical decisions are append-only; current status is a projection.",
                evidence=[self.evidence(repo,"src/qdw/ideas/service.py","cemetery upsert rewrites prior burial episode")],
                remediation="Make cemetery episodes append-only with unique cemetery_id; maintain a separate current idea status/projection.",
                acceptance_tests=["Bury→revive→bury retains both historical burial episodes."],
                tags=["idea","history"]
            ))
        return self.result(fs)
