from __future__ import annotations
from dataclasses import dataclass,field
from enum import IntEnum
from typing import Any

class Severity(IntEnum):
    INFO=10;LOW=20;MEDIUM=30;HIGH=40;CRITICAL=50
    @classmethod
    def parse(cls,x):
        return x if isinstance(x,cls) else cls[str(x).upper()]

@dataclass(frozen=True)
class ReviewPolicy:
    policy_id:str
    policy_hash:str
    block_at:Severity=Severity.HIGH
    required_reviewers:tuple[str,...]=()
    required_attacks:tuple[str,...]=()
    max_rounds:int=4
    max_cost_usd:float|None=5.0
    require_clean_subject:bool=True
    require_remote_ci:bool=False
    require_independent_certifier:bool=True

@dataclass(frozen=True)
class ReviewRequest:
    subject_git_sha:str
    subject_dirty:bool
    base_git_sha:str|None
    changed_paths:tuple[str,...]
    trigger_type:str
    profile:str
    policy:ReviewPolicy
    producer_worker_id:str|None=None

@dataclass(frozen=True)
class ReviewerFinding:
    rule_id:str
    severity:str
    title:str
    summary:str
    invariant:str
    remediation:str
    evidence:tuple[dict[str,Any],...]=()
    acceptance_tests:tuple[str,...]=()
    acceptance_specs:tuple[dict[str,Any],...]=()
    confidence:float=1.0

@dataclass(frozen=True)
class ReviewerResult:
    reviewer_id:str
    reviewer_version:str
    status:str
    findings:tuple[ReviewerFinding,...]
    summary:str=""
    evidence:tuple[dict[str,Any],...]=()
    cost_usd:float=0.0

@dataclass(frozen=True)
class ControllerOutcome:
    review_run_id:str
    status:str
    round_no:int
    blocker_count:int
    fix_graph_id:str|None=None
    certificate_id:str|None=None
    stop_reason:str|None=None
