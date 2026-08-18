from __future__ import annotations
import json
from qdw.core import canonical_json,hash_object,new_id,utc_now
from .contracts import FederatedRef,VerificationCertificateRef

class ExternalCertificateService:
    """Issue federation certificates only from QDW's canonical VerificationService evidence."""

    def __init__(self,db,ledger,verification):
        self.db,self.ledger,self.verification=db,ledger,verification

    def issue(self,*,verification_run_id:str,subject:FederatedRef,output_digest:str)->VerificationCertificateRef:
        ok,reason=self.verification.verify_evidence(verification_run_id)
        record=self.verification.run_record(verification_run_id)
        run=record["run"]
        policy_hash=run["plan_hash"]
        status="VERIFIED" if ok else "REJECTED"
        cid=new_id("fedcert")
        payload={
          "schema":"qdw.federation-certificate.v2",
          "issuer_system":"qdw","certificate_id":cid,
          "subject":{"system":subject.system,"object_type":subject.object_type,
                     "object_id":subject.object_id,"version":subject.version,
                     "revision":subject.revision,"digest":subject.digest},
          "output_digest":output_digest,"verification_run_id":verification_run_id,
          "policy_hash":policy_hash,"status":status,"issued_at":utc_now(),
        }
        ch=hash_object(payload);payload["certificate_hash"]=ch
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO federation_certificates_v2(
              certificate_id,issuer_system,subject_system,subject_type,subject_id,subject_digest,
              output_digest,policy_id,policy_hash,status,certificate_json,certificate_hash,issued_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid,"qdw",subject.system,subject.object_type,subject.object_id,subject.digest,
             output_digest,verification_run_id,policy_hash,status,
             canonical_json(payload).decode(),ch,payload["issued_at"]))
            self.ledger.append_in_tx(con,"federation.certificate_issued","federation_certificate",cid,{
              "subject_system":subject.system,"subject_type":subject.object_type,
              "subject_id":subject.object_id,"status":status,"verification_run_id":verification_run_id,
            })
        return VerificationCertificateRef(
          issuer_system="qdw",certificate_id=cid,certificate_digest=ch,subject=subject,
          output_digest=output_digest,policy_digest=policy_hash,status=status,
          verification_url=f"/v1/federation/certificates/{cid}")

    def get(self,certificate_id:str)->dict:
        with self.db.connect() as con:
            r=con.execute("SELECT certificate_json FROM federation_certificates_v2 WHERE certificate_id=?",
                          (certificate_id,)).fetchone()
        if not r:raise KeyError(certificate_id)
        return json.loads(r["certificate_json"])

    def verify_reference(self,ref:VerificationCertificateRef)->dict:
        payload=self.get(ref.certificate_id)
        stored=payload.pop("certificate_hash")
        if stored!=hash_object(payload):raise ValueError("certificate hash mismatch")
        if stored!=ref.certificate_digest:raise ValueError("certificate reference hash mismatch")
        if payload["subject"]["object_id"]!=ref.subject.object_id:raise ValueError("certificate subject mismatch")
        if payload["output_digest"]!=ref.output_digest:raise ValueError("certificate output mismatch")
        return payload
