"""ProductRegistry v2 — explicit factory lineage, typed outcomes and ReleaseAuthorization."""
from __future__ import annotations
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any
import json

from qdw.core import canonical_json,hash_object,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger

class OutcomeAuthority(StrEnum):
    FIXTURE="fixture"
    MANUAL="manual"
    ESTIMATED="estimated"
    MEASURED="measured"

class ProductRegistry:
    def __init__(self,db:Database,ledger:Ledger):
        self.db,self.ledger=db,ledger

    def create_from_factory_run(self,name:str,slug:str,product_type:str,*,idea_id:str|None,
                                factory_id:str,factory_version:str,build_run_id:str)->str:
        with self.db.connect() as con:
            run=con.execute("SELECT * FROM factory_runs WHERE factory_run_id=?",(build_run_id,)).fetchone()
        if not run:raise ValueError("factory run not found")
        if run["factory_id"]!=factory_id or run["factory_version"]!=factory_version:
            raise ValueError("factory run lineage mismatch")
        return self._create(name,slug,product_type,idea_id=idea_id,factory_id=factory_id,
                            factory_version=factory_version,build_run_id=build_run_id)

    def import_external_product(self,name:str,slug:str,product_type:str,*,idea_id:str|None=None)->str:
        return self._create(name,slug,product_type,idea_id=idea_id,
                            factory_id=None,factory_version=None,build_run_id=None)

    def create(self,name:str,slug:str,product_type:str,*,idea_id:str|None=None,
               factory_id:str|None=None,factory_version:str|None=None,
               build_run_id:str|None=None)->str:
        """Compatibility entry point with strict lineage.

        All factory lineage fields must be present together; otherwise use import_external_product.
        """
        supplied=[factory_id is not None,factory_version is not None,build_run_id is not None]
        if any(supplied) and not all(supplied):
            raise ValueError("factory_id, factory_version and build_run_id must be supplied together")
        if all(supplied):
            return self.create_from_factory_run(
                name,slug,product_type,idea_id=idea_id,factory_id=factory_id,
                factory_version=factory_version,build_run_id=build_run_id,
            )
        return self.import_external_product(name,slug,product_type,idea_id=idea_id)

    def _create(self,name,slug,product_type,*,idea_id,factory_id,factory_version,build_run_id):
        pid=new_id("prod");now=utc_now()
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO products(
                product_id,idea_id,factory_id,factory_version,name,slug,product_type,status,
                build_run_id,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,'BUILDING',?,?,?)""",
            (pid,idea_id,factory_id,factory_version,name,slug,product_type,build_run_id,now,now))
            self.ledger.append_in_tx(con,"product.created","product",pid,{
                "name":name,"slug":slug,"idea_id":idea_id,"build_run_id":build_run_id,
            })
        return pid

    def release(self,product_id:str,release_authorization_id:str)->None:
        with self.db.tx(immediate=True) as con:
            product=con.execute("SELECT * FROM products WHERE product_id=?",(product_id,)).fetchone()
            if not product:raise KeyError(product_id)
            if product["status"]=="RELEASED":raise ValueError("product already released")
            auth=con.execute("""SELECT * FROM release_authorizations
                WHERE release_authorization_id=?""",(release_authorization_id,)).fetchone()
            if not auth:raise ValueError("release authorization not found")
            if auth["status"]!="AUTHORIZED":raise ValueError("release authorization not active")
            if auth["product_id"]!=product_id:raise ValueError("PRODUCT_MISMATCH")
            if auth["build_run_id"]!=product["build_run_id"]:raise ValueError("BUILD_RUN_MISMATCH")

            # Revalidate authorization and BuildCertificate envelopes/artifacts at the transition boundary.
            auth_json=json.loads(auth["authorization_json"])
            stored=auth_json.pop("authorization_hash",None)
            if stored!=hash_object(auth_json):raise ValueError("release authorization hash mismatch")
            bc=con.execute("""SELECT * FROM build_certificates_v2 WHERE build_certificate_id=?""",
                           (auth["build_certificate_id"],)).fetchone()
            if not bc:raise ValueError("build certificate missing")
            cert=json.loads(bc["certificate_json"])
            cert_hash=cert.pop("certificate_hash",None)
            if cert_hash!=hash_object(cert):raise ValueError("build certificate hash mismatch")
            if bc["artifact_set_hash"]!=auth["artifact_set_hash"]:
                raise ValueError("ARTIFACT_SET_MISMATCH")
            for art in cert.get("artifacts",[]):
                p=Path(art["path"])
                if not p.exists() or sha256(p.read_bytes()).hexdigest()!=art["sha256"]:
                    raise ValueError("ARTIFACT_SET_MISMATCH")

            now=utc_now()
            con.execute("""UPDATE products SET status='RELEASED',release_authorization_id=?,
                certificate_id=?,released_at=?,updated_at=? WHERE product_id=?""",
                (release_authorization_id,auth["build_certificate_id"],now,now,product_id))
            self.ledger.append_in_tx(con,"product.released","product",product_id,{
                "release_authorization_id":release_authorization_id,
                "build_certificate_id":auth["build_certificate_id"],
            })

    def passport(self,product_id:str)->dict[str,Any]:
        with self.db.connect() as con:
            p=con.execute("SELECT * FROM products WHERE product_id=?",(product_id,)).fetchone()
            if not p:raise KeyError(product_id)
            idea=con.execute("SELECT * FROM ideas WHERE idea_id=?",(p["idea_id"],)).fetchone() if p["idea_id"] else None
            genomes=con.execute("""SELECT genome_hash,genome_json,created_at FROM factory_genomes
                WHERE product_id=?""",(product_id,)).fetchall()
            outcomes=con.execute("""SELECT * FROM outcome_events WHERE product_id=?
                ORDER BY occurred_at""",(product_id,)).fetchall()
            auth=con.execute("""SELECT * FROM release_authorizations WHERE release_authorization_id=?""",
                             (p["release_authorization_id"],)).fetchone() if p["release_authorization_id"] else None
        return {
            "product":dict(p),"idea":dict(idea) if idea else None,
            "factory_genomes":[{**dict(g),"genome":json.loads(g["genome_json"])} for g in genomes],
            "release_authorization":dict(auth) if auth else None,
            "outcomes":[dict(x) for x in outcomes],
        }

    def outcome(self,product_id:str,metric:str,*,value:float|None=None,text_value:str|None=None,
                unit:str|None=None,source:str="manual",authority:OutcomeAuthority|str=OutcomeAuthority.MANUAL,
                learning_eligible:bool=False,evidence:dict[str,Any]|None=None,occurred_at:str|None=None)->str:
        if value is None and text_value is None:raise ValueError("outcome requires value or text")
        authority=OutcomeAuthority(authority)
        if learning_eligible and authority is not OutcomeAuthority.MEASURED:
            raise ValueError("only measured outcomes may be learning eligible")
        if authority is OutcomeAuthority.MEASURED and not evidence:
            raise ValueError("measured outcome requires evidence")
        oid=new_id("outcomeevent")
        with self.db.tx(immediate=True) as con:
            if not con.execute("SELECT 1 FROM products WHERE product_id=?",(product_id,)).fetchone():
                raise KeyError(product_id)
            con.execute("""INSERT INTO outcome_events(
                outcome_event_id,product_id,metric,value,text_value,unit,source,occurred_at,
                evidence_json,created_at,authority,learning_eligible
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (oid,product_id,metric,value,text_value,unit,source,occurred_at or utc_now(),
             canonical_json(evidence or {}).decode(),utc_now(),authority.value,1 if learning_eligible else 0))
            self.ledger.append_in_tx(con,"product.outcome","outcome_event",oid,{
                "product_id":product_id,"metric":metric,"authority":authority.value,
                "learning_eligible":learning_eligible,
            })
        return oid
