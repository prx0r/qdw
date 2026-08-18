from __future__ import annotations
from typing import Any
from ..models import FederatedRef
from ..hashing import digest

class SandboxEstateAdapter:
    """Compatibility/graduation adapter for qdw-sandbox Estate contracts."""

    def capability_request(self,estate:dict[str,Any])->dict[str,Any]:
        c=estate.get("constraints") or {}
        return {
            "request_id":str(estate["request_id"]),
            "capability":str(estate["capability"]),
            "objective":str(estate["objective"]),
            "verification_policy":str(estate["verification_policy"]),
            "budget":{
                "max_cost_usd":c.get("max_cost_usd"),
                "max_wall_seconds":c.get("max_wall_seconds",900),
            },
            "permissions":{
                "network":c.get("network","none"),
                "external_writes":bool(c.get("external_writes",False)),
                "human_escalation":bool(c.get("human_escalation",False)),
            },
            "required_resource_kinds":tuple(c.get("required_resource_kinds") or ()),
            "forbidden_resource_ids":tuple(c.get("forbidden_resource_ids") or ()),
            "quality_floor":estate.get("quality_floor"),
            "expected_value_usd":estate.get("expected_value_usd"),
            "input_refs":tuple(estate.get("input_refs") or ()),
            "context_refs":tuple(estate.get("context_refs") or ()),
            "external_ref":FederatedRef("sandbox","estate_capability_request",str(estate["request_id"]),
                                        digest=digest(estate)),
        }

    def resource_descriptor(self,r:dict[str,Any])->dict[str,Any]:
        return {
            "external_ref":FederatedRef("sandbox","estate_resource",str(r["resource_id"]),
                                        version=r.get("version"),digest=digest(r)),
            "resource_id":r["resource_id"],
            "kind":str(r["kind"]),
            "name":r["name"],
            "capabilities":tuple(r.get("capabilities") or ()),
            "interface_kind":r.get("interface_kind"),
            "attributes":dict(r.get("attributes") or {}),
            "active":bool(r.get("active",True)),
        }

    @staticmethod
    def production_authority_allowed(component:str)->bool:
        # Explicitly retire competing Estate authorities from production.
        return component not in {"EstateRouter","EstateVerificationService","EstateScheduler"}
