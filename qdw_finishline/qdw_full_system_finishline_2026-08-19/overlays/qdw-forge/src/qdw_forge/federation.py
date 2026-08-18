from __future__ import annotations
from typing import Any,Protocol
import httpx
from pydantic import BaseModel,model_validator

class FederatedSubject(BaseModel):
    system:str
    object_type:str
    object_id:str
    version:str|None=None
    revision:str|None=None
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
    def validate_ref(self):
        if self.status not in {"VERIFIED","REJECTED"}:raise ValueError("invalid certificate status")
        if not self.certificate_hash:raise ValueError("certificate hash required")
        return self

class CertificateEnvelope(BaseModel):
    certificate:CertificateReference

class CertificateResolver(Protocol):
    def resolve(self,certificate:CertificateReference)->dict[str,Any]: ...

class QDWCertificateResolver:
    def __init__(self,qdw_base_url:str,*,client:httpx.Client|None=None):
        self.base=qdw_base_url.rstrip("/")
        self.client=client or httpx.Client(timeout=20)
    def resolve(self,c:CertificateReference)->dict[str,Any]:
        if c.issuer_system!="qdw":raise PermissionError("untrusted certificate issuer")
        path=c.verification_url or f"/v1/federation/certificates/{c.certificate_id}"
        r=self.client.get(self.base+path)
        if r.status_code!=200:raise PermissionError(f"certificate resolution failed: {r.status_code}")
        raw=r.json()
        if raw.get("certificate_id")!=c.certificate_id:raise ValueError("certificate id mismatch")
        if raw.get("certificate_hash")!=c.certificate_hash:raise ValueError("certificate hash mismatch")
        if raw.get("status")!=c.status:raise ValueError("certificate status mismatch")
        return raw
