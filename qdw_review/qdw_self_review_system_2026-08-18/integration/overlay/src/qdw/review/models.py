from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ReviewRequest:
    subject_git_sha:str
    policy_hash:str
    profile:str
    changed_paths:tuple[str,...]=()
    producer_run_id:str|None=None

@dataclass(frozen=True)
class ReviewOutcome:
    review_run_id:str
    status:str
    blocker_count:int
    report_hash:str|None=None
    certificate_id:str|None=None

@dataclass(frozen=True)
class ReviewerOutput:
    reviewer_id:str
    version:str
    status:str
    findings:tuple[dict[str,Any],...]
    output_hash:str
