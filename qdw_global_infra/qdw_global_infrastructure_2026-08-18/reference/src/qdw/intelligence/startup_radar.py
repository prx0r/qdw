from __future__ import annotations
import json
from qdw.core.core import canonical_json,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.world.store import WorldStore

class StartupRadar:
    def __init__(self,db:Database,ledger:Ledger,world:WorldStore):
        self.db,self.ledger,self.world=db,ledger,world

    def record_company_event(self,company_name:str,event_type:str,event_at:str,*,external_key:str|None=None,
                             amount_usd:float|None=None,stage:str|None=None,
                             attributes:dict|None=None,observation_id:str|None=None)->str:
        company_id=self.world.upsert_entity("company",company_name,external_key=external_key,attributes=attributes or {})
        eid=new_id("startup")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO startup_events(startup_event_id,company_entity_id,event_type,event_at,
                amount_usd,stage,attributes_json,observation_id,created_at)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (eid,company_id,event_type,event_at,amount_usd,stage,canonical_json(attributes or {}).decode(),
                 observation_id,utc_now()))
        self.ledger.append("startup.event","startup_event",eid,
                           {"company_id":company_id,"event_type":event_type,"event_at":event_at})
        return eid

    def recent(self,event_type:str|None=None,limit:int=50)->list[dict]:
        q="""SELECT s.*,e.canonical_name company_name FROM startup_events s
             JOIN entities e ON e.entity_id=s.company_entity_id"""
        args=[]
        if event_type:
            q+=" WHERE s.event_type=?";args.append(event_type)
        q+=" ORDER BY s.event_at DESC LIMIT ?";args.append(limit)
        with self.db.connect() as con:
            out=[]
            for r in con.execute(q,args).fetchall():
                d=dict(r);d["attributes"]=json.loads(d.pop("attributes_json"));out.append(d)
        return out

    def category_counts(self,attribute:str="category")->dict[str,int]:
        counts={}
        for row in self.recent(limit=10000):
            key=str(row["attributes"].get(attribute) or "unknown")
            counts[key]=counts.get(key,0)+1
        return counts
