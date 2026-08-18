from __future__ import annotations
import json
from pathlib import Path
from ..core import hash_object,utc_now
from ..db import Database
from .base import FactoryDefinition

class FactoryRegistry:
    def __init__(self,db:Database):self.db=db

    def register_manifest(self,path:str|Path)->FactoryDefinition:
        m=json.loads(Path(path).read_text(encoding="utf-8"))
        d=FactoryDefinition.from_manifest(m); h=hash_object(m)
        with self.db.tx(immediate=True) as con:
            existing=con.execute("""SELECT definition_hash FROM factory_definitions
                WHERE factory_id=? AND version=?""",(d.factory_id,d.version)).fetchone()
            if existing and existing["definition_hash"]!=h:
                raise ValueError("factory version is immutable; bump version")
            con.execute("""INSERT OR IGNORE INTO factory_definitions(
                factory_id,version,definition_hash,manifest_json,status,created_at)
                VALUES(?,?,?,?,?,?)""",
                (d.factory_id,d.version,h,json.dumps(m,sort_keys=True),"CANDIDATE",utc_now()))
        return d

    def activate(self,factory_id:str,version:str,fixture_passed:bool)->None:
        if not fixture_passed:raise ValueError("fixture must pass before ACTIVE")
        with self.db.tx(immediate=True) as con:
            changed=con.execute("""UPDATE factory_definitions SET status='ACTIVE'
                WHERE factory_id=? AND version=?""",(factory_id,version)).rowcount
            if changed!=1:raise KeyError((factory_id,version))

    def list(self):
        with self.db.connect() as con:
            return [dict(r) for r in con.execute("""SELECT factory_id,version,status,definition_hash
                FROM factory_definitions ORDER BY factory_id,version""").fetchall()]
