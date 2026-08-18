from __future__ import annotations
from pydantic import BaseModel,Field,model_validator
from typing import Any,Protocol

class FederatedSubject(BaseModel):
    system:str
    object_type:str
    object_id:str
    digest:str|None=None

class CertificateReference(BaseModel):
    issuer_system:str
    certificate_id:str
    certificate_hash:str
    subject:FederatedSubject
    subject_output_digest:str
    policy_hash:str
    status:str
    verification_url:str|None=None
    signature:str|None=None

    @model_validator(mode="after")
    def valid(self):
        if self.status not in {"VERIFIED","REJECTED"}:raise ValueError("invalid certificate status")
        if not self.certificate_hash.startswith("sha256:"):raise ValueError("certificate hash required")
        return self

class CertificateResolver(Protocol):
    def resolve(self,certificate:CertificateReference)->dict[str,Any]: ...

class HTTPQDWCertificateResolver:
    """Optional resolver for Forge deployments that trust a QDW verification endpoint."""
    def __init__(self,client,allowed_issuers:set[str]|None=None):
        self.client=client;self.allowed_issuers=allowed_issuers or {"qdw"}

    def resolve(self,c:CertificateReference)->dict[str,Any]:
        if c.issuer_system not in self.allowed_issuers:raise PermissionError("certificate issuer not trusted")
        # `client` is injected; no global network dependency in unit tests.
        raw=self.client.get_certificate(c.certificate_id)
        if raw.get("certificate_hash")!=c.certificate_hash:raise ValueError("certificate hash mismatch")
        return raw

def validate_for_invocation(c:CertificateReference,invocation)->bool:
    if c.subject.system!="forge" or c.subject.object_type!="invocation":
        raise ValueError("certificate subject type mismatch")
    if c.subject.object_id!=invocation.invocation_id:
        raise ValueError("certificate invocation mismatch")
    if invocation.output_hash and c.subject_output_digest!=invocation.output_hash:
        raise ValueError("certificate output hash mismatch")
    return True
