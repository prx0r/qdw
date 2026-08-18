from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
from qdw.core import canonical_json,hash_object,new_id,utc_now

def artifact_set(paths)->tuple[list[dict],str]:
    arts=[]
    for raw in sorted(str(Path(p).resolve()) for p in paths):
        p=Path(raw)
        if not p.exists() or not p.is_file():
            raise ValueError(f"missing fixture artifact {p}")
        arts.append({"path":raw,"sha256":sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size})
    return arts,hash_object(arts)

class FixtureCertificateService:
    def __init__(self,db,ledger,build_certificates):
        self.db,self.ledger,self.build_certificates=db,ledger,build_certificates

    def issue(self,*,subject_type:str,subject_id:str,subject_version:str,definition_hash:str,
              fixture_id:str,factory_run_id:str|None,artifact_paths,acceptance_plan_hash:str,
              build_certificate_id:str|None,independent_worker_id:str)->dict:
        if subject_type not in {"factory","contractor"}:
            raise ValueError("invalid fixture subject type")
        if not acceptance_plan_hash:raise ValueError("acceptance_plan_hash required")
        if not independent_worker_id:raise ValueError("independent_worker_id required")
        if not build_certificate_id:raise ValueError("build_certificate_id required for fixture certification")
        arts,aset=artifact_set(artifact_paths)
        ok,reason=self.build_certificates.verify(build_certificate_id)
        if not ok:raise ValueError("invalid build certificate: "+reason)
        with self.db.connect() as con:
            bc=con.execute("SELECT artifact_set_hash FROM build_certificates_v2 WHERE build_certificate_id=?",
                           (build_certificate_id,)).fetchone()
        if not bc or bc["artifact_set_hash"]!=aset:
            raise ValueError("fixture artifacts do not match build certificate artifact set")
        cid=new_id("fixturecert")
        cert={
            "schema":"qdw.fixture-certificate.v2",
            "fixture_certificate_id":cid,
            "subject_type":subject_type,
            "subject_id":subject_id,
            "subject_version":subject_version,
            "definition_hash":definition_hash,
            "fixture_id":fixture_id,
            "factory_run_id":factory_run_id,
            "artifacts":arts,
            "artifact_set_hash":aset,
            "acceptance_plan_hash":acceptance_plan_hash,
            "build_certificate_id":build_certificate_id,
            "independent_worker_id":independent_worker_id,
            "status":"ACCEPTED",
            "issued_at":utc_now(),
        }
        cert["certificate_hash"]=hash_object(cert)
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO fixture_certificates(
                fixture_certificate_id,subject_type,subject_id,subject_version,definition_hash,fixture_id,
                factory_run_id,artifact_set_hash,acceptance_plan_hash,build_certificate_id,
                independent_worker_id,status,certificate_json,certificate_hash,issued_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cid,subject_type,subject_id,subject_version,definition_hash,fixture_id,factory_run_id,aset,
             acceptance_plan_hash,build_certificate_id,independent_worker_id,"ACCEPTED",
             canonical_json(cert).decode(),cert["certificate_hash"],cert["issued_at"]))
            self.ledger.append_in_tx(con,"fixture_certificate.issued","fixture_certificate",cid,{
                "subject_type":subject_type,"subject_id":subject_id,"subject_version":subject_version,
            })
        return cert

    def verify_binding(self,certificate_id:str,*,subject_type:str,subject_id:str,subject_version:str,
                       definition_hash:str,fixture_id:str)->dict:
        with self.db.connect() as con:
            row=con.execute("SELECT * FROM fixture_certificates WHERE fixture_certificate_id=?",(certificate_id,)).fetchone()
        if not row:raise ValueError("fixture certificate not found")
        expected={
            "subject_type":subject_type,"subject_id":subject_id,"subject_version":subject_version,
            "definition_hash":definition_hash,"fixture_id":fixture_id,
        }
        for k,v in expected.items():
            if row[k]!=v:raise ValueError(f"fixture certificate {k} mismatch")
        if row["status"]!="ACCEPTED":raise ValueError("fixture certificate not accepted")
        cert=json.loads(row["certificate_json"])
        stored=cert.pop("certificate_hash",None)
        if stored!=hash_object(cert):raise ValueError("fixture certificate hash mismatch")
        for art in cert.get("artifacts",[]):
            p=Path(art["path"])
            if not p.exists() or sha256(p.read_bytes()).hexdigest()!=art["sha256"]:
                raise ValueError("fixture artifact hash mismatch")
        return dict(row)

class ReleaseAuthorizationService:
    def __init__(self,db,ledger,build_certificates):
        self.db,self.ledger,self.build_certificates=db,ledger,build_certificates

    def issue(self,*,product_id:str,build_run_id:str,artifact_paths,build_certificate_id:str,
              review_certificate_id:str|None,policy_hash:str)->dict:
        ok,reason=self.build_certificates.verify(build_certificate_id)
        if not ok:raise ValueError("invalid build certificate: "+reason)
        with self.db.connect() as con:
            product=con.execute("SELECT * FROM products WHERE product_id=?",(product_id,)).fetchone()
            if not product:raise KeyError(product_id)
            if product["build_run_id"]!=build_run_id:raise ValueError("BUILD_RUN_MISMATCH")
            review=None
            if review_certificate_id:
                review=con.execute("SELECT * FROM review_certificates WHERE review_certificate_id=?",
                                   (review_certificate_id,)).fetchone()
                if not review or review["status"]!="REVIEW_CERTIFIED":
                    raise ValueError("invalid review certificate")
        arts,aset=artifact_set(artifact_paths)
        with self.db.connect() as con:
            bc=con.execute("SELECT * FROM build_certificates_v2 WHERE build_certificate_id=?",
                           (build_certificate_id,)).fetchone()
        if not bc or bc["artifact_set_hash"]!=aset:
            raise ValueError("ARTIFACT_SET_MISMATCH")
        if review is not None:
            if review["subject_git_sha"]!=bc["subject_git_sha"]:
                raise ValueError("REVIEW_BUILD_SUBJECT_MISMATCH")
            if review["policy_hash"]!=policy_hash:
                raise ValueError("REVIEW_POLICY_MISMATCH")
            rc=json.loads(review["certificate_json"])
            stored=rc.pop("certificate_hash",None)
            if stored!=hash_object(rc) or stored!=review["certificate_hash"]:
                raise ValueError("REVIEW_CERTIFICATE_HASH_MISMATCH")
        aid=new_id("releaseauth")
        auth={
            "schema":"qdw.release-authorization.v2",
            "release_authorization_id":aid,"product_id":product_id,"build_run_id":build_run_id,
            "artifact_set_hash":aset,"build_certificate_id":build_certificate_id,
            "subject_git_sha":bc["subject_git_sha"],
            "review_certificate_id":review_certificate_id,"policy_hash":policy_hash,
            "status":"AUTHORIZED","issued_at":utc_now(),
        }
        auth["authorization_hash"]=hash_object(auth)
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO release_authorizations(
                release_authorization_id,product_id,build_run_id,artifact_set_hash,build_certificate_id,
                review_certificate_id,policy_hash,status,authorization_json,authorization_hash,issued_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (aid,product_id,build_run_id,aset,build_certificate_id,review_certificate_id,policy_hash,
             "AUTHORIZED",canonical_json(auth).decode(),auth["authorization_hash"],auth["issued_at"]))
            self.ledger.append_in_tx(con,"release.authorization","release_authorization",aid,{
                "product_id":product_id,"build_run_id":build_run_id,
            })
        return auth
