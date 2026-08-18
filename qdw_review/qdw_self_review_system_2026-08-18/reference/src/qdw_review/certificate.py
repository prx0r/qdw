from __future__ import annotations
from datetime import UTC,datetime
from hashlib import sha256
from pathlib import Path
import json
from qdw_review.policy import evaluate

def _hash(x)->str:
    return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

class ReviewCertificateBuilder:
    def issue(self,report:dict,policy:dict,*,attack_results:list[dict],
              certifier_worker_id:str,producer_worker_id:str|None=None,
              output_path:str|Path|None=None)->dict:
        gate=evaluate(report,policy)
        subject=report.get("git_sha")
        if not subject:
            raise ValueError("review subject has no git SHA")
        if report.get("git_dirty"):
            raise ValueError("dirty repository cannot receive release review certificate")
        if producer_worker_id and producer_worker_id==certifier_worker_id:
            raise ValueError("producer cannot be independent certifier")
        required_attacks=set(policy.get("required_attacks",[]))
        by_id={x.get("attack_id"):x for x in attack_results}
        missing=sorted(required_attacks-set(by_id))
        failed=sorted(i for i in required_attacks if i in by_id and by_id[i].get("status")!="PASS")
        if missing or failed:
            raise ValueError(f"attack gate failed: missing={missing}, failed={failed}")
        if gate["status"]!="PASS":
            raise ValueError(f"review policy failed with {len(gate['blockers'])} blockers")

        reviewers=sorted((m["module_id"],m.get("version","")) for m in report.get("modules",[]))
        cert={
            "subject_git_sha":subject,
            "policy_hash":_hash(policy),
            "aggregate_report_hash":_hash(report),
            "reviewer_set_hash":_hash(reviewers),
            "attack_set_hash":_hash(sorted(attack_results,key=lambda x:x.get("attack_id",""))),
            "status":"REVIEW_CERTIFIED",
            "certifier_worker_id":certifier_worker_id,
            "producer_worker_id":producer_worker_id,
            "issued_at":datetime.now(UTC).isoformat().replace("+00:00","Z"),
        }
        cert["certificate_hash"]=_hash(cert)
        if output_path:
            Path(output_path).write_text(json.dumps(cert,indent=2),encoding="utf-8")
        return cert

    def verify_envelope(self,cert:dict)->bool:
        c=dict(cert);stored=c.pop("certificate_hash",None)
        return bool(stored) and stored==_hash(c) and c.get("status")=="REVIEW_CERTIFIED"
