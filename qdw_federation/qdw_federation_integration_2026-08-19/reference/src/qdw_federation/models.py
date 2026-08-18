from __future__ import annotations
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from .hashing import digest

class ExternalStatus(StrEnum):
    OK="OK"
    OK_EMPTY="OK_EMPTY"
    DEGRADED="DEGRADED"
    STALE="STALE"
    UNAVAILABLE="UNAVAILABLE"
    INCOMPATIBLE_PROTOCOL="INCOMPATIBLE_PROTOCOL"
    UNAUTHORIZED="UNAUTHORIZED"
    BUDGET_BLOCKED="BUDGET_BLOCKED"
    POLICY_BLOCKED="POLICY_BLOCKED"
    FAILED="FAILED"

class AuthorityKind(StrEnum):
    OBSERVATION="OBSERVATION"
    ADVISORY="ADVISORY"
    CAPABILITY="CAPABILITY"
    EXECUTION_RESULT="EXECUTION_RESULT"
    CERTIFICATE="CERTIFICATE"

@dataclass(frozen=True)
class FederatedRef:
    system:str
    object_type:str
    object_id:str
    version:str|None=None
    revision:str|None=None
    digest:str|None=None

    def __post_init__(self):
        if not self.system or not self.object_type or not self.object_id:
            raise ValueError("federated ref requires system/object_type/object_id")

@dataclass(frozen=True)
class EvidenceEnvelope:
    source_system:str
    authority:AuthorityKind
    observed_at:str
    content_digest:str
    evidence_refs:tuple[FederatedRef,...]=()
    freshness_deadline:str|None=None
    confidence:float|None=None
    source_family:str|None=None

    def __post_init__(self):
        if self.confidence is not None and not 0<=self.confidence<=1:
            raise ValueError("confidence outside [0,1]")

@dataclass(frozen=True)
class ObservationRecord:
    external_ref:FederatedRef
    metric:str
    value:Any
    unit:str|None
    entity_key:str
    evidence:EvidenceEnvelope
    dimensions:dict[str,Any]=field(default_factory=dict)

@dataclass(frozen=True)
class ObservationBatch:
    source_system:str
    schema_version:str
    cursor:str
    observations:tuple[ObservationRecord,...]
    source_revision:str|None=None
    generated_at:str|None=None

    @property
    def batch_digest(self)->str:return digest(self)

    @property
    def idempotency_key(self)->str:
        return f"{self.source_system}:{self.schema_version}:{self.cursor}:{self.batch_digest}"

@dataclass(frozen=True)
class ResourceCandidate:
    external_ref:FederatedRef
    capability:str
    provider_id:str|None=None
    model_id:str|None=None
    endpoint_id:str|None=None
    asset_id:str|None=None
    asset_version:str|None=None
    free:bool|None=None
    estimated_cost_usd:float|None=None
    quality:float|None=None
    reliability:float|None=None
    context_tokens:int|None=None
    tools_supported:bool|None=None
    json_supported:bool|None=None
    latency_ms:float|None=None
    sample_count:int|None=None
    evidence_refs:tuple[FederatedRef,...]=()
    attributes:dict[str,Any]=field(default_factory=dict)

    def __post_init__(self):
        for name in ("quality","reliability"):
            v=getattr(self,name)
            if v is not None and not 0<=v<=1:raise ValueError(f"{name} outside [0,1]")
        if self.estimated_cost_usd is not None and self.estimated_cost_usd<0:raise ValueError("negative cost")

@dataclass(frozen=True)
class ResourceCandidateSnapshot:
    source_system:str
    schema_version:str
    request_digest:str
    fetched_at:str
    status:ExternalStatus
    candidates:tuple[ResourceCandidate,...]
    raw_response_digest:str
    advisory_ref:FederatedRef|None=None
    warnings:tuple[str,...]=()

    @property
    def snapshot_digest(self)->str:return digest(self)

@dataclass(frozen=True)
class DecisionAdvisory:
    adviser_system:str
    advisory_id:str
    method:str
    recommended_ref:FederatedRef|None
    alternative_refs:tuple[FederatedRef,...]
    excluded:tuple[dict[str,Any],...]
    evidence_snapshot_digest:str
    as_of:str
    authority:AuthorityKind=AuthorityKind.ADVISORY

    def __post_init__(self):
        if self.authority is not AuthorityKind.ADVISORY:
            raise ValueError("foreign route recommendation must remain ADVISORY")

@dataclass(frozen=True)
class CapabilityAssetView:
    external_ref:FederatedRef
    name:str
    capabilities:tuple[str,...]
    certified:bool
    status:str
    pricing_per_call:float|None=None
    posterior_mean:float|None=None
    sample_count:int=0
    transport_kind:str|None=None
    rights_ref:FederatedRef|None=None
    metadata:dict[str,Any]=field(default_factory=dict)

@dataclass(frozen=True)
class CapabilityExecutionRequest:
    request_id:str
    capability:str
    selected_asset_ref:FederatedRef
    arguments:dict[str,Any]
    max_spend_usd:float|None
    calls:int=1
    ttl_seconds:int=3600
    qdw_work_ref:FederatedRef|None=None
    qdw_route_digest:str|None=None

    def __post_init__(self):
        if self.selected_asset_ref.system!="forge":
            raise ValueError("capability exchange request must pin forge asset")
        if not self.selected_asset_ref.version:
            raise ValueError("forge execution must pin asset version")
        if self.calls<=0:raise ValueError("calls must be positive")

@dataclass(frozen=True)
class InvocationOutcome:
    invocation_ref:FederatedRef
    selected_asset_ref:FederatedRef
    status:str
    output:dict[str,Any]|None
    output_digest:str|None
    cost_usd:float|None
    nested_route_digest:str|None
    failure:str|None=None

    def __post_init__(self):
        if self.status=="VERIFIED":
            raise ValueError("execution adapter may not manufacture VERIFIED outcome")

@dataclass(frozen=True)
class VerificationCertificateRef:
    issuer_system:str
    certificate_id:str
    certificate_digest:str
    subject_ref:FederatedRef
    subject_output_digest:str
    policy_digest:str
    status:str
    verification_url:str|None=None
    signature:str|None=None

    def __post_init__(self):
        if self.status not in {"VERIFIED","REJECTED"}:raise ValueError("invalid certificate status")
        if not self.certificate_digest.startswith("sha256:"):raise ValueError("certificate digest required")

@dataclass(frozen=True)
class ExternalResponse:
    status:ExternalStatus
    payload:Any
    source_system:str
    fetched_at:str
    raw_digest:str
    warnings:tuple[str,...]=()
