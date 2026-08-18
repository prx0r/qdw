"""Factory registry v2 — immutable definitions and typed fixture certificate activation."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json
from qdw.core import hash_object,utc_now
from qdw.core.db import Database
from .base import FactoryDefinition

class FactoryRegistry:
    def __init__(self,db:Database):
        self.db=db

    def register_manifest(self,path:str|Path)->FactoryDefinition:
        m=json.loads(Path(path).read_text(encoding="utf-8"))
        d=FactoryDefinition.from_manifest(m)
        h=hash_object(m)
        with self.db.tx(immediate=True) as con:
            old=con.execute("""SELECT definition_hash FROM factory_definitions
                WHERE factory_id=? AND version=?""",(d.factory_id,d.version)).fetchone()
            if old and old["definition_hash"]!=h:
                raise ValueError("factory version immutable; bump version")
            con.execute("""INSERT OR IGNORE INTO factory_definitions(
                factory_id,version,definition_hash,manifest_json,status,created_at
            ) VALUES(?,?,?,?, 'CANDIDATE',?)""",
            (d.factory_id,d.version,h,json.dumps(m,sort_keys=True),utc_now()))
        return d

    def _verify_fixture(self,con,factory_id,version,certificate_id):
        factory=con.execute("""SELECT * FROM factory_definitions WHERE factory_id=? AND version=?""",
                            (factory_id,version)).fetchone()
        if not factory:raise KeyError((factory_id,version))
        manifest=json.loads(factory["manifest_json"])
        fixture_id=manifest["fixture"]["fixture_id"]
        row=con.execute("""SELECT * FROM fixture_certificates WHERE fixture_certificate_id=?""",
                        (certificate_id,)).fetchone()
        if not row:raise ValueError("fixture certificate not found")
        expected={
            "subject_type":"factory","subject_id":factory_id,"subject_version":version,
            "definition_hash":factory["definition_hash"],"fixture_id":fixture_id,
        }
        for key,value in expected.items():
            if row[key]!=value:raise ValueError(f"factory fixture certificate {key} mismatch")
        if row["status"]!="ACCEPTED":raise ValueError("fixture certificate not accepted")
        cert=json.loads(row["certificate_json"])
        stored=cert.pop("certificate_hash",None)
        if stored!=hash_object(cert):raise ValueError("fixture certificate hash mismatch")
        for art in cert.get("artifacts",[]):
            p=Path(art["path"])
            if not p.exists() or sha256(p.read_bytes()).hexdigest()!=art["sha256"]:
                raise ValueError("fixture artifact hash mismatch")
        return factory

    def activate(self,factory_id:str,version:str,fixture_certificate_id:str)->None:
        with self.db.tx(immediate=True) as con:
            self._verify_fixture(con,factory_id,version,fixture_certificate_id)
            con.execute("""UPDATE factory_definitions SET status='ACTIVE'
                WHERE factory_id=? AND version=?""",(factory_id,version))

    def get(self,factory_id:str,version:str)->dict:
        with self.db.connect() as con:
            row=con.execute("SELECT * FROM factory_definitions WHERE factory_id=? AND version=?",
                            (factory_id,version)).fetchone()
        if not row:raise KeyError((factory_id,version))
        return dict(row)

    def list(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("""SELECT factory_id,version,status,definition_hash
                FROM factory_definitions ORDER BY factory_id,version""").fetchall()]
