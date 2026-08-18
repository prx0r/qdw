from __future__ import annotations
from qdw.core import hash_object,new_id,utc_now
from .contracts import *
from .clients import ForgeClient

class ForgeExecutionAdapter:
    def __init__(self,client:ForgeClient,store,ledger,db):
        self.client,self.store,self.ledger,self.db=client,store,ledger,db

    def execute(self,request:CapabilityExecutionRequest)->ExternalInvocationOutcome:
        a=request.selected_asset
        if a.system!="forge" or not a.version:raise ValueError("must pin Forge asset@version")
        lease=self.client.lease({
          "capability":request.capability,"asset_id":a.object_id,"version":a.version,
          "calls":1,"max_spend_usd":request.max_spend_usd,"allowed_operations":["invoke"]
        })
        raw=self.client.invoke({
          "lease_token":lease["token"],"capability":request.capability,
          "arguments":request.arguments,"client_request_id":request.request_id
        })
        if raw["asset_id"]!=a.object_id or str(raw["version"])!=str(a.version):
            raise RuntimeError("FORGE_ASSET_SUBSTITUTION")
        inv=FederatedRef("forge","invocation",raw["invocation_id"],digest=hash_object(raw))
        outcome=ExternalInvocationOutcome(
          inv,a,raw["status"],raw.get("output"),raw.get("output_hash"),raw.get("cost_usd"),
          hash_object(raw["route_decision"]) if raw.get("route_decision") else None,raw.get("failure"))
        return outcome

    def bind_certificate(self,outcome:ExternalInvocationOutcome,cert:VerificationCertificateRef)->None:
        if cert.subject.system!="forge" or cert.subject.object_id!=outcome.invocation.object_id:
            raise ValueError("certificate subject mismatch")
        if outcome.output_digest and cert.output_digest!=outcome.output_digest:
            raise ValueError("certificate output mismatch")
        self.client.bind_certificate(outcome.invocation.object_id,{"certificate":{
          "issuer_system":cert.issuer_system,"certificate_id":cert.certificate_id,
          "certificate_hash":cert.certificate_digest,
          "subject":{"system":cert.subject.system,"object_type":cert.subject.object_type,
                     "object_id":cert.subject.object_id,"digest":cert.subject.digest},
          "subject_output_digest":cert.output_digest,"policy_hash":cert.policy_digest,
          "status":cert.status,"verification_url":cert.verification_url,"signature":cert.signature,
        }})
