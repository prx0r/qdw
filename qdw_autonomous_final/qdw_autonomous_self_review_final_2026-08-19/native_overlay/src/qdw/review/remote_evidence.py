from __future__ import annotations
from typing import Protocol

class RemoteEvidenceProvider(Protocol):
    def ci_for_sha(self,sha:str)->dict: ...
    def branch_policy(self,branch:str)->dict: ...

class NullRemoteEvidence:
    def ci_for_sha(self,sha:str)->dict:
        return {"status":"UNVERIFIED","subject_git_sha":sha}
    def branch_policy(self,branch:str)->dict:
        return {"status":"UNVERIFIED","branch":branch}
