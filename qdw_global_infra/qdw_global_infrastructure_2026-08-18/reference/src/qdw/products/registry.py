from __future__ import annotations
import json
from typing import Any
from qdw.core.core import canonical_json,hash_object,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger

class ProductRegistry:
    def __init__(self,db:Database,ledger:Ledger):
        self.db,self.ledger=db,ledger

    def create(self,name:str,slug:str,product_type:str,*,idea_id:str|None=None,factory_id:str|None=None,
               factory_version:str|None=None,build_run_id:str|None=None)->str:
        pid=new_id("prod");now=utc_now()
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO products(product_id,idea_id,factory_id,factory_version,name,slug,product_type,
                status,build_run_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'BUILDING',?,?,?)""",
                (pid,idea_id,factory_id,factory_version,name,slug,product_type,build_run_id,now,now))
        self.ledger.append("product.created","product",pid,{"name":name,"slug":slug,"idea_id":idea_id})
        return pid

    def attach_urls(self,product_id:str,*,domain:str|None=None,repository_url:str|None=None,
                    deployment_url:str|None=None)->None:
        with self.db.tx(immediate=True) as con:
            if not con.execute("SELECT 1 FROM products WHERE product_id=?",(product_id,)).fetchone():raise KeyError(product_id)
            con.execute("""UPDATE products SET domain=COALESCE(?,domain),repository_url=COALESCE(?,repository_url),
                deployment_url=COALESCE(?,deployment_url),updated_at=? WHERE product_id=?""",
                (domain,repository_url,deployment_url,utc_now(),product_id))
        self.ledger.append("product.urls","product",product_id,
                           {"domain":domain,"repository_url":repository_url,"deployment_url":deployment_url})

    def release(self,product_id:str,certificate_id:str)->None:
        with self.db.tx(immediate=True) as con:
            changed=con.execute("""UPDATE products SET status='RELEASED',certificate_id=?,released_at=?,updated_at=?
                WHERE product_id=? AND status!='RELEASED'""",(certificate_id,utc_now(),utc_now(),product_id)).rowcount
            if changed!=1:raise ValueError("product missing or already released")
        self.ledger.append("product.released","product",product_id,{"certificate_id":certificate_id})

    def add_genome(self,product_id:str,genome:dict[str,Any])->str:
        gh=hash_object(genome);gid=new_id("genome")
        with self.db.tx(immediate=True) as con:
            old=con.execute("SELECT genome_id FROM factory_genomes WHERE genome_hash=?",(gh,)).fetchone()
            if old:return old["genome_id"]
            con.execute("""INSERT INTO factory_genomes(genome_id,product_id,genome_hash,genome_json,created_at)
                VALUES(?,?,?,?,?)""",(gid,product_id,gh,canonical_json(genome).decode(),utc_now()))
        self.ledger.append("product.genome","factory_genome",gid,{"product_id":product_id,"genome_hash":gh})
        return gid

    def outcome(self,product_id:str,metric:str,*,value:float|None=None,text_value:str|None=None,
                unit:str|None=None,source:str="manual",evidence:dict[str,Any]|None=None,occurred_at:str|None=None)->str:
        if value is None and text_value is None:raise ValueError("outcome requires value or text")
        oid=new_id("outcomeevent")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO outcome_events(outcome_event_id,product_id,metric,value,text_value,unit,source,
                occurred_at,evidence_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (oid,product_id,metric,value,text_value,unit,source,occurred_at or utc_now(),
                 canonical_json(evidence or {}).decode(),utc_now()))
        self.ledger.append("product.outcome","outcome_event",oid,{"product_id":product_id,"metric":metric})
        return oid

    def passport(self,product_id:str)->dict[str,Any]:
        with self.db.connect() as con:
            p=con.execute("SELECT * FROM products WHERE product_id=?",(product_id,)).fetchone()
            if not p:raise KeyError(product_id)
            idea=con.execute("SELECT * FROM ideas WHERE idea_id=?",(p["idea_id"],)).fetchone() if p["idea_id"] else None
            genomes=con.execute("SELECT genome_hash,genome_json,created_at FROM factory_genomes WHERE product_id=?",
                                (product_id,)).fetchall()
            outcomes=con.execute("SELECT * FROM outcome_events WHERE product_id=? ORDER BY occurred_at",
                                 (product_id,)).fetchall()
            pubs=con.execute("""SELECT p.*,d.name surface_name,d.kind surface_kind FROM publications p
                JOIN distribution_surfaces d ON d.surface_id=p.surface_id WHERE p.product_id=?""",(product_id,)).fetchall()
            domains=con.execute("SELECT * FROM domains WHERE product_id=?",(product_id,)).fetchall()
        return {
            "product":dict(p),
            "idea":dict(idea) if idea else None,
            "factory_genomes":[{**dict(g),"genome":json.loads(g["genome_json"])} for g in genomes],
            "outcomes":[dict(x) for x in outcomes],
            "publications":[dict(x) for x in pubs],
            "domains":[dict(x) for x in domains],
        }
