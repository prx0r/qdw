from __future__ import annotations
from dataclasses import dataclass

OWNERS={
    "portfolio_decision":"qdw",
    "workgraph":"qdw",
    "work_scheduling":"qdw",
    "final_execution_route":"qdw",
    "qdw_verification":"qdw",
    "product_release":"qdw",
    "provider_model_truth":"dell",
    "technical_frontier_truth":"gitgoblin",
    "capability_asset_registry":"forge",
    "capability_lease":"forge",
    "capability_invocation":"forge",
    "sandbox_experiments":"sandbox",
}

FORBIDDEN={
    ("forge","workgraph"),
    ("forge","portfolio_decision"),
    ("dell","final_execution_route"),
    ("gitgoblin","portfolio_decision"),
    ("sandbox","work_scheduling"),
    ("sandbox","qdw_verification"),
    ("sandbox","final_execution_route"),
}

@dataclass(frozen=True)
class AuthorityDecision:
    concern:str
    owner:str
    allowed:bool
    reason:str

def authorize(system:str,concern:str)->AuthorityDecision:
    owner=OWNERS.get(concern)
    if owner is None:return AuthorityDecision(concern,"unknown",False,"unknown concern")
    if (system,concern) in FORBIDDEN:
        return AuthorityDecision(concern,owner,False,f"{system} is explicitly forbidden from owning {concern}")
    return AuthorityDecision(concern,owner,system==owner,
                             "canonical owner" if system==owner else f"{system} may advise but {owner} owns truth")

def assert_authority(system:str,concern:str)->None:
    d=authorize(system,concern)
    if not d.allowed:raise PermissionError(d.reason)
