from __future__ import annotations
from .models import InvocationStatus
from .federation import CertificateReference,CertificateResolver,validate_for_invocation

class InvocationVerificationService:
    def __init__(self,db,store,resolver:CertificateResolver):
        self.db,self.store,self.resolver=db,store,resolver

    def bind(self,invocation_service,invocation_id:str,certificate:CertificateReference):
        invocation=invocation_service.get(invocation_id)
        if invocation.status not in {InvocationStatus.SUCCEEDED_UNVERIFIED,InvocationStatus.FAILED}:
            raise ValueError("invocation not awaiting verification")
        validate_for_invocation(certificate,invocation)
        resolved=self.resolver.resolve(certificate)
        # Resolve authoritative status rather than trusting request body status.
        if resolved.get("status")!=certificate.status:
            raise ValueError("certificate resolved status mismatch")
        success=certificate.status=="VERIFIED"
        status=InvocationStatus.VERIFIED if success else InvocationStatus.REJECTED
        with self.db.tx(immediate=True) as con:
            con.execute("""UPDATE invocations SET status=?,verification_certificate_id=?
                           WHERE invocation_id=?""",(status.value,certificate.certificate_id,invocation_id))
        self.store.record_verified(
            invocation.asset_id,invocation.version,invocation.capability,
            success=success,cost_usd=float(invocation.cost_usd),
            certificate_id=certificate.certificate_id
        )
        return invocation_service.get(invocation_id)
