from __future__ import annotations
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any
from .hashing import digest

class Status(StrEnum):
    OK="OK"; OK_EMPTY="OK_EMPTY"; STALE="STALE"; UNAVAILABLE="UNAVAILABLE"
    INCOMPATIBLE_PROTOCOL="INCOMPATIBLE_PROTOCOL"; FAILED="FAILED"

class AttemptState(StrEnum):
    DISCOVERING="DISCOVERING"; CANDIDATES_READY="CANDIDATES_READY"; ROUTED="ROUTED"
    LEASED="LEASED"; RUNNING="RUNNING"; SUCCEEDED_UNVERIFIED="SUCCEEDED_UNVERIFIED"
    VERIFYING="VERIFYING"; VERIFIED="VERIFIED"; COMMITTED="COMMITTED"; FAILED="FAILED"

@dataclass(frozen=True)
class Ref:
    system:str; kind:str; object_id:str
    version:str|None=None; digest_value:str|None=None

@dataclass(frozen=True)
class Route:
    route_id:str; source:str; capability:str
    fixed_cost:float|None=None; quality:float|None=None; active:bool=True
    external_ref:Ref|None=None
    def __post_init__(self):
        if self.fixed_cost is not None and self.fixed_cost<0: raise ValueError("negative cost")

@dataclass(frozen=True)
class Certificate:
    certificate_id:str
    issuer:str
    subject:Ref
    output_digest:str
    policy_digest:str
    status:str
    certificate_digest:str
    def __post_init__(self):
        if self.status not in {"VERIFIED","REJECTED"}: raise ValueError("bad cert status")

@dataclass(frozen=True)
class Invocation:
    invocation_id:str; lease_id:str; client_request_id:str
    asset_id:str; version:str; capability:str
    request_digest:str; status:str
    output:dict[str,Any]|None=None; output_digest:str|None=None
    cost:float=0.0

@dataclass(frozen=True)
class AssetManifest:
    asset_id:str; version:str; name:str; capabilities:tuple[str,...]
    per_call:float; transport:str="fixture"
    source_repo:str|None=None; source_commit:str|None=None; source_manifest_digest:str|None=None
    @property
    def manifest_digest(self): return digest(self)

@dataclass
class Lease:
    lease_id:str; asset_id:str; version:str; capability:str
    token_hash:str; calls_total:int; calls_used:int
    max_spend:float|None; spend:float
    operations:tuple[str,...]; active:bool=True

@dataclass(frozen=True)
class ObservationBatch:
    schema_version:str; source_system:str; cursor:str; source_revision:str
    observations:tuple[dict[str,Any],...]; proposals:tuple[dict[str,Any],...]
    @property
    def batch_digest(self): return digest(self)
