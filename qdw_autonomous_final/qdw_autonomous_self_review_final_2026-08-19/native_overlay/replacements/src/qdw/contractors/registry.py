"""Contractor registry v2 — immutable versions + typed fixture certificate activation."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
from qdw.core import hash_object,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger

class ContractorRegistry:
    def __init__(self,db:Database,ledger:Ledger):
        self.db,self.ledger=db,ledger

    def register_manifest(self,path:str|Path)->tuple[str,str]:
        m=json.loads(Path(path).read_text(encoding="utf-8"))
        required={"contractor_id","version","team","specialization","inputs","outputs","gates"}
        missing=required-set(m)
        if missing:raise ValueError(f"missing {sorted(missing)}")
        h=hash_object(m)
        with self.db.tx(immediate=True) as con:
            old=con.execute("""SELECT definition_hash FROM contractor_definitions
                WHERE contractor_id=? AND version=?""",(m["contractor_id"],m["version"])).fetchone()
            if old:
                if old["definition_hash"]!=h:raise ValueError("contractor version immutable; bump version")
                return m["contractor_id"],m["version"]
            con.execute("""INSERT INTO contractor_definitions(
                contractor_id,version,definition_hash,manifest_json,status,created_at
            ) VALUES(?,?,?,?, 'CANDIDATE',?)""",
            (m["contractor_id"],m["version"],h,json.dumps(m,sort_keys=True),utc_now()))
            self.ledger.append_in_tx(con,"contractor.registered","contractor",m["contractor_id"],{
                "version":m["version"],"definition_hash":h,
            })
        return m["contractor_id"],m["version"]

    def activate(self,contractor_id:str,version:str,fixture_certificate_id:str)->None:
        with self.db.tx(immediate=True) as con:
            definition=con.execute("""SELECT * FROM contractor_definitions
                WHERE contractor_id=? AND version=?""",(contractor_id,version)).fetchone()
            if not definition:raise KeyError((contractor_id,version))
            manifest=json.loads(definition["manifest_json"])
            fixture_id=(manifest.get("fixture") or {}).get("fixture_id")
            if not fixture_id:
                raise ValueError("contractor manifest must declare fixture.fixture_id before activation")
            cert=con.execute("SELECT * FROM fixture_certificates WHERE fixture_certificate_id=?",
                             (fixture_certificate_id,)).fetchone()
            if not cert:raise ValueError("fixture certificate not found")
            expected={
                "subject_type":"contractor","subject_id":contractor_id,"subject_version":version,
                "definition_hash":definition["definition_hash"],"fixture_id":fixture_id,
            }
            for k,v in expected.items():
                if cert[k]!=v:raise ValueError(f"contractor fixture certificate {k} mismatch")
            if cert["status"]!="ACCEPTED":raise ValueError("fixture certificate not accepted")
            payload=json.loads(cert["certificate_json"])
            stored=payload.pop("certificate_hash",None)
            if stored!=hash_object(payload):raise ValueError("fixture certificate hash mismatch")
            for art in payload.get("artifacts",[]):
                p=Path(art["path"])
                if not p.exists() or sha256(p.read_bytes()).hexdigest()!=art["sha256"]:
                    raise ValueError("fixture artifact hash mismatch")
            con.execute("""UPDATE contractor_definitions SET status='ACTIVE'
                WHERE contractor_id=? AND version=?""",(contractor_id,version))
            self.ledger.append_in_tx(con,"contractor.activated","contractor",contractor_id,{
                "version":version,"fixture_certificate_id":fixture_certificate_id,
            })

    def list(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("""SELECT contractor_id,version,status,definition_hash
                FROM contractor_definitions ORDER BY contractor_id,version""").fetchall()]
