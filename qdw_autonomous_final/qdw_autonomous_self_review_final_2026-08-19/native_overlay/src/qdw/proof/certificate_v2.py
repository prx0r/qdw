"""BuildCertificate v2 issues only from a frozen VerificationRun."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import glob,json
from qdw.core import canonical_json,hash_object,new_id,utc_now
from .verification_service import VerificationService,_git_subject

class BuildCertificateV2:
    def __init__(self, verification: VerificationService):
        self.verification=verification

    def issue(self, verification_run_id: str, *, ledger_root: str = "") -> dict:
        ok,reason=self.verification.verify_evidence(verification_run_id)
        if not ok:
            raise ValueError(f"verification evidence invalid: {reason}")
        record=self.verification.run_record(verification_run_id)
        run=record["run"]
        cwd=Path(run["cwd"])

        current_sha,current_dirty=_git_subject(cwd)
        if current_sha!=run["subject_git_sha"]:
            raise ValueError("subject changed after verification")
        if current_dirty:
            raise ValueError("subject became dirty after verification")

        artifacts=json.loads(run["artifact_set_json"] or "[]")
        if hash_object(artifacts)!=run["artifact_set_hash"]:
            raise ValueError("stored artifact set hash mismatch")
        for art in artifacts:
            path=Path(art["path"])
            if not path.exists() or sha256(path.read_bytes()).hexdigest()!=art["sha256"]:
                raise ValueError("artifact changed after verification")

        cid=new_id("buildcert")
        cert={
            "schema":"qdw.build-certificate.v2",
            "build_certificate_id":cid,
            "verification_run_id":verification_run_id,
            "subject_git_sha":run["subject_git_sha"],
            "cwd":run["cwd"],
            "environment_hash":run["environment_hash"],
            "plan_hash":run["plan_hash"],
            "artifact_set_hash":run["artifact_set_hash"],
            "artifacts":artifacts,
            "ledger_root":ledger_root,
            "issued_at":utc_now(),
        }
        cert["certificate_hash"]=hash_object(cert)
        with self.verification.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO build_certificates_v2(
                build_certificate_id,verification_run_id,subject_git_sha,plan_hash,artifact_set_hash,
                ledger_root,certificate_json,certificate_hash,issued_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (cid,verification_run_id,run["subject_git_sha"],run["plan_hash"],
             run["artifact_set_hash"],ledger_root,canonical_json(cert).decode(),
             cert["certificate_hash"],cert["issued_at"]))
            self.verification.ledger.append_in_tx(
                con,"build_certificate.issued","build_certificate",cid,{
                    "verification_run_id":verification_run_id,
                    "subject_git_sha":run["subject_git_sha"],
                    "artifact_set_hash":run["artifact_set_hash"],
                }
            )
        return cert

    def verify(self, build_certificate_id: str) -> tuple[bool,str]:
        with self.verification.db.connect() as con:
            row=con.execute("SELECT * FROM build_certificates_v2 WHERE build_certificate_id=?",(build_certificate_id,)).fetchone()
        if not row:return False,"missing"
        cert=json.loads(row["certificate_json"])
        stored=cert.pop("certificate_hash",None)
        if stored!=hash_object(cert):return False,"certificate_hash"
        record=self.verification.run_record(row["verification_run_id"])
        if record["run"]["subject_git_sha"] != row["subject_git_sha"]:
            return False,"subject_binding"
        if cert.get("subject_git_sha") != row["subject_git_sha"]:
            return False,"certificate_subject"
        if cert.get("plan_hash") != record["run"]["plan_hash"] or row["plan_hash"] != record["run"]["plan_hash"]:
            return False,"plan_binding"
        run_artifact_hash=record["run"]["artifact_set_hash"]
        if row["artifact_set_hash"]!=run_artifact_hash or cert.get("artifact_set_hash")!=run_artifact_hash:
            return False,"artifact_set_binding"
        if cert.get("environment_hash")!=record["run"]["environment_hash"]:
            return False,"environment_binding"
        if cert.get("cwd")!=record["run"]["cwd"]:
            return False,"cwd_binding"
        ok,reason=self.verification.verify_evidence(row["verification_run_id"])
        if not ok:return False,"verification:"+reason
        for art in cert.get("artifacts",[]):
            p=Path(art["path"])
            if not p.exists() or sha256(p.read_bytes()).hexdigest()!=art["sha256"]:
                return False,"artifact_hash"
        return True,"ok"
