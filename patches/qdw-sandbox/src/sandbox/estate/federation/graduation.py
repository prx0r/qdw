from __future__ import annotations
from dataclasses import asdict
from ..contracts.capability import CapabilityRequest
from ..contracts.resources import ResourceDescriptor,ResourceProfile

PRODUCTION_AUTHORITY_DISABLED={"EstateRouter","EstateVerificationService","EstateScheduler"}

def export_capability_request(req:CapabilityRequest)->dict:
    return {"schema_version":"qdw-federation-capability/1","source_system":"sandbox",
            "authority":"ADVISORY","request":asdict(req),"content_hash":req.content_hash}

def export_resource(r:ResourceDescriptor,profile:ResourceProfile|None=None)->dict:
    return {"schema_version":"qdw-federation-resource/1","source_system":"sandbox",
            "authority":"ADVISORY","resource":asdict(r),
            "profile":asdict(profile) if profile else None,
            "resource_hash":r.content_hash}

def assert_not_production_authority(component:str):
    if component in PRODUCTION_AUTHORITY_DISABLED:
        raise PermissionError(f"{component} is incubator-only; QDW owns production authority")
