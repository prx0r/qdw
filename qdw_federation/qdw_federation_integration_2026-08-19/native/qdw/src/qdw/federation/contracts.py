"""Copy/adapt the reference federation models into QDW.

Do not import the integration-pack package at runtime. The final QDW package owns the stable protocol contract.
"""
from __future__ import annotations
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any

class ExternalStatus(StrEnum):
    OK="OK"; OK_EMPTY="OK_EMPTY"; DEGRADED="DEGRADED"; STALE="STALE"
    UNAVAILABLE="UNAVAILABLE"; INCOMPATIBLE_PROTOCOL="INCOMPATIBLE_PROTOCOL"
    UNAUTHORIZED="UNAUTHORIZED"; BUDGET_BLOCKED="BUDGET_BLOCKED"
    POLICY_BLOCKED="POLICY_BLOCKED"; FAILED="FAILED"

@dataclass(frozen=True)
class FederatedRef:
    system:str
    object_type:str
    object_id:str
    version:str|None=None
    revision:str|None=None
    digest:str|None=None

@dataclass(frozen=True)
class ExternalSnapshot:
    source_system:str
    kind:str
    protocol_version:str
    request_digest:str
    response_digest:str
    status:ExternalStatus
    fetched_at:str
    normalized:dict[str,Any]
    raw_artifact_id:str|None=None
    freshness_deadline:str|None=None
    source_revision:str|None=None
    adapter_version:str="1.0.0"
    warnings:tuple[str,...]=()

@dataclass(frozen=True)
class DecisionAdvisory:
    adviser_system:str
    external_advisory_id:str
    method:str
    snapshot_digest:str
    payload:dict[str,Any]
    as_of:str
    authority:str="ADVISORY"

@dataclass(frozen=True)
class CapabilityExecutionRequest:
    request_id:str
    capability:str
    selected_asset:FederatedRef
    arguments:dict[str,Any]
    max_spend_usd:float|None
    qdw_work_node_id:str
    qdw_route_digest:str

@dataclass(frozen=True)
class ExternalInvocationOutcome:
    invocation:FederatedRef
    selected_asset:FederatedRef
    status:str
    output:dict[str,Any]|None
    output_digest:str|None
    cost_usd:float|None
    nested_route_digest:str|None
    failure:str|None=None

@dataclass(frozen=True)
class VerificationCertificateRef:
    issuer_system:str
    certificate_id:str
    certificate_digest:str
    subject:FederatedRef
    output_digest:str
    policy_digest:str
    status:str
    verification_url:str|None=None
    signature:str|None=None
