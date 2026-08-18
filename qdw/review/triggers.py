from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ReviewTrigger:
    trigger_type:str
    profile:str
    policy_name:str

TRIGGERS={
    "commit":ReviewTrigger("commit","quick","quick"),
    "major_phase":ReviewTrigger("major_phase","change-aware","change-aware"),
    "release":ReviewTrigger("release","release","release"),
    "factory_activation":ReviewTrigger("factory_activation","release","release"),
    "contractor_activation":ReviewTrigger("contractor_activation","release","release"),
    "migration_change":ReviewTrigger("migration_change","change-aware","change-aware"),
    "reviewer_change":ReviewTrigger("reviewer_change","self-review","self-review"),
    "scheduled_deep_audit":ReviewTrigger("scheduled_deep_audit","full","release"),
}
