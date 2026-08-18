from __future__ import annotations
from .hashing import digest
from .models import Certificate,Invocation,Ref

class QDWVerifier:
    def __init__(self,policy="qdw.external-invocation.v1"):self.policy_digest=digest({"policy":policy})
    def verify(self,inv:Invocation):
        passed=inv.status=="SUCCEEDED_UNVERIFIED" and inv.output is not None and inv.output_digest is not None
        output_digest=inv.output_digest or digest({"failed":inv.invocation_id})
        body={"invocation":inv.invocation_id,"output":output_digest,"policy":self.policy_digest,
              "status":"VERIFIED" if passed else "REJECTED"}
        cid="cert_"+digest(body).split(":",1)[1][:20]
        return Certificate(cid,"qdw",Ref("forge","invocation",inv.invocation_id),
                           output_digest,self.policy_digest,
                           "VERIFIED" if passed else "REJECTED",digest(body))
