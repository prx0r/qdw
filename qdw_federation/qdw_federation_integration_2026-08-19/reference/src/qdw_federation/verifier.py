from __future__ import annotations
from .models import *
from .hashing import digest

class ReferenceQDWVerifier:
    """Deterministic test verifier that binds certificate to the exact Forge invocation/output."""

    def __init__(self,policy_digest:str="sha256:reference-policy"):self.policy_digest=policy_digest

    def verify_invocation(self,outcome:InvocationOutcome,work_ref:FederatedRef)->VerificationCertificateRef:
        passed=outcome.status=="SUCCEEDED_UNVERIFIED" and bool(outcome.output_digest)
        subject=FederatedRef(
            "forge","invocation",outcome.invocation_ref.object_id,
            digest=outcome.invocation_ref.digest,
        )
        body={
            "issuer_system":"qdw","subject":subject,"output_digest":outcome.output_digest,
            "policy":self.policy_digest,"status":"VERIFIED" if passed else "REJECTED",
            "work_ref":work_ref,
        }
        return VerificationCertificateRef(
            issuer_system="qdw",
            certificate_id="cert_"+digest(body).split(":",1)[1][:20],
            certificate_digest=digest(body),
            subject_ref=subject,
            subject_output_digest=outcome.output_digest or digest({"no-output":outcome.failure}),
            policy_digest=self.policy_digest,
            status="VERIFIED" if passed else "REJECTED",
        )
