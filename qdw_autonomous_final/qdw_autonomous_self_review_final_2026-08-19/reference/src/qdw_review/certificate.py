from __future__ import annotations
from datetime import UTC,datetime
from hashlib import sha256
import json
from .policy import ReviewPolicy,evaluate
from .models import ReviewReport

def _hash(x)->str:
    return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

class ReviewCertificateBuilder:
    def issue(self,report:ReviewReport,policy:ReviewPolicy,*,attack_results:list[dict],
              reviewer_definitions:list[dict],certifier_worker_id:str,
              producer_worker_id:str|None=None,remote_ci:bool|None=None)->dict:
        gate=evaluate(report,policy,attack_results,remote_ci)
        if gate["status"]!="PASS":
            raise ValueError("review policy failed: "+",".join(gate["reasons"]))
        if not report.subject.git_sha:
            raise ValueError("subject SHA missing")
        if policy.require_clean_subject and report.subject.dirty:
            raise ValueError("dirty subject")
        if producer_worker_id and producer_worker_id==certifier_worker_id:
            raise ValueError("producer cannot be independent certifier")
        defs=sorted(
            (d["contractor_id"],d["version"],d.get("definition_hash",""))
            for d in reviewer_definitions
        )
        cert={
            "schema":"qdw.review-certificate.v2",
            "status":"REVIEW_CERTIFIED",
            "subject_git_sha":report.subject.git_sha,
            "policy_id":policy.policy_id,
            "policy_hash":_hash(policy.__dict__),
            "report_hash":_hash(report.to_dict()),
            "reviewer_set_hash":_hash(defs),
            "attack_set_hash":_hash(sorted(attack_results,key=lambda x:x.get("attack_id",""))),
            "certifier_worker_id":certifier_worker_id,
            "producer_worker_id":producer_worker_id,
            "issued_at":datetime.now(UTC).isoformat().replace("+00:00","Z"),
        }
        cert["certificate_hash"]=_hash(cert)
        return cert

    def verify_envelope(self,cert:dict)->tuple[bool,str]:
        c=dict(cert);stored=c.pop("certificate_hash",None)
        if not stored or stored!=_hash(c):return False,"certificate_hash"
        if c.get("status")!="REVIEW_CERTIFIED":return False,"status"
        return True,"ok"
