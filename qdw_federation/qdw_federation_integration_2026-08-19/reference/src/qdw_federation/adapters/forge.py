from __future__ import annotations
from typing import Any,Protocol
from ..models import *
from ..hashing import digest

class ForgeTransport(Protocol):
    def list_assets(self,capability:str)->list[dict[str,Any]]: ...
    def create_lease(self,body:dict[str,Any])->dict[str,Any]: ...
    def invoke(self,body:dict[str,Any])->dict[str,Any]: ...
    def bind_certificate(self,invocation_id:str,body:dict[str,Any])->dict[str,Any]: ...

class ForgeAdapter:
    system="forge"

    def __init__(self,transport:ForgeTransport):self.transport=transport

    def assets(self,capability:str)->tuple[CapabilityAssetView,...]:
        out=[]
        for a in self.transport.list_assets(capability):
            ref=FederatedRef(
                "forge","capability_asset",str(a["asset_id"]),
                version=str(a["version"]),digest=str(a.get("manifest_hash") or digest(a))
            )
            rights=a.get("rights")
            rref=None
            if rights:
                rref=FederatedRef("forge","data_rights",str(rights.get("rights_id") or rights.get("id") or "rights"),
                                  version=rights.get("version"),digest=digest(rights))
            out.append(CapabilityAssetView(
                ref,str(a.get("name") or a["asset_id"]),tuple(a.get("capabilities") or ()),
                certified=bool(a.get("certificate_id")),
                status=str(a.get("status","CANDIDATE")),
                pricing_per_call=(a.get("pricing") or {}).get("per_call"),
                posterior_mean=a.get("posterior_mean"),
                sample_count=int(a.get("sample_count") or 0),
                transport_kind=(a.get("transport") or {}).get("kind") if isinstance(a.get("transport"),dict) else a.get("transport_kind"),
                rights_ref=rref,metadata={"certificate_id":a.get("certificate_id")},
            ))
        return tuple(out)

    def execute(self,request:CapabilityExecutionRequest)->InvocationOutcome:
        # Pin lease to QDW's final asset/version choice. This prevents hidden rerouting.
        selected=request.selected_asset_ref
        lease_body={
            "capability":request.capability,
            "asset_id":selected.object_id,
            "version":selected.version,
            "calls":request.calls,
            "max_spend_usd":request.max_spend_usd,
            "ttl_seconds":request.ttl_seconds,
            "allowed_operations":["invoke"],
        }
        lease_resp=self.transport.create_lease(lease_body)
        token=lease_resp["token"]
        inv=self.transport.invoke({
            "lease_token":token,
            "capability":request.capability,
            "arguments":request.arguments,
            "client_request_id":request.request_id,
        })
        # Critical anti-substitution check.
        if str(inv["asset_id"])!=selected.object_id or str(inv["version"])!=str(selected.version):
            raise RuntimeError("FORGE_ASSET_SUBSTITUTION")
        iref=FederatedRef("forge","invocation",str(inv["invocation_id"]),digest=digest(inv))
        return InvocationOutcome(
            iref,selected,str(inv["status"]),inv.get("output"),inv.get("output_hash"),
            inv.get("cost_usd"),
            digest(inv.get("route_decision")) if inv.get("route_decision") else None,
            inv.get("failure"),
        )

    def bind_certificate(self,outcome:InvocationOutcome,certificate:VerificationCertificateRef)->None:
        if certificate.subject_ref.system!="forge" or certificate.subject_ref.object_type!="invocation":
            raise ValueError("certificate subject is not forge invocation")
        if certificate.subject_ref.object_id!=outcome.invocation_ref.object_id:
            raise ValueError("certificate invocation mismatch")
        if outcome.output_digest and certificate.subject_output_digest!=outcome.output_digest:
            raise ValueError("certificate output digest mismatch")
        # New desired wire format: no caller-authored `passed` boolean.
        body={
            "certificate":{
                "issuer_system":certificate.issuer_system,
                "certificate_id":certificate.certificate_id,
                "certificate_hash":certificate.certificate_digest,
                "subject":{
                    "system":certificate.subject_ref.system,
                    "object_type":certificate.subject_ref.object_type,
                    "object_id":certificate.subject_ref.object_id,
                    "digest":certificate.subject_ref.digest,
                },
                "subject_output_digest":certificate.subject_output_digest,
                "policy_hash":certificate.policy_digest,
                "status":certificate.status,
                "verification_url":certificate.verification_url,
                "signature":certificate.signature,
            }
        }
        self.transport.bind_certificate(outcome.invocation_ref.object_id,body)
