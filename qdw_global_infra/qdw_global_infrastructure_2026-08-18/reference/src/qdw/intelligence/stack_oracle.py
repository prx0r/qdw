from __future__ import annotations
import json, math
from dataclasses import dataclass
from typing import Any
from qdw.core.core import canonical_json,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.world.store import WorldStore

@dataclass(frozen=True)
class ResourceRecommendation:
    resource_id:str
    name:str
    score:float
    reasons:tuple[str,...]
    attributes:dict[str,Any]
    measurements:dict[str,float|str|None]

class StackOracle:
    """Versioned capability/resource registry. No single magical 'best' score is stored."""

    def __init__(self,db:Database,ledger:Ledger,world:WorldStore):
        self.db,self.ledger,self.world=db,ledger,world

    def ensure_capability(self,key:str,name:str,category:str,description:str="")->str:
        now=utc_now()
        with self.db.tx(immediate=True) as con:
            r=con.execute("SELECT capability_id FROM capabilities WHERE capability_key=?",(key,)).fetchone()
            if r:return r["capability_id"]
            cid=new_id("cap")
            con.execute("""INSERT INTO capabilities(capability_id,capability_key,name,category,description,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?)""",(cid,key,name,category,description,now,now))
        self.ledger.append("capability.created","capability",cid,{"key":key})
        return cid

    def register_resource(self,capability_key:str,name:str,*,resource_key:str,provider:str|None=None,
                          version:str|None=None,interface_kind:str|None=None,attributes:dict|None=None)->str:
        with self.db.connect() as con:
            c=con.execute("SELECT capability_id FROM capabilities WHERE capability_key=?",(capability_key,)).fetchone()
        if not c:raise KeyError(f"capability {capability_key}")
        provider_id=None
        if provider:
            provider_id=self.world.upsert_entity("provider",provider,external_key=provider.lower())
        now=utc_now()
        with self.db.tx(immediate=True) as con:
            old=con.execute("SELECT resource_id FROM resources WHERE resource_key=?",(resource_key,)).fetchone()
            if old:
                rid=old["resource_id"]
                con.execute("""UPDATE resources SET name=?,version=?,interface_kind=?,attributes_json=?,updated_at=?
                    WHERE resource_id=?""",(name,version,interface_kind,canonical_json(attributes or {}).decode(),now,rid))
            else:
                rid=new_id("res")
                con.execute("""INSERT INTO resources(resource_id,capability_id,provider_entity_id,resource_key,name,
                    version,interface_kind,attributes_json,status,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?, 'ACTIVE',?,?)""",
                    (rid,c["capability_id"],provider_id,resource_key,name,version,interface_kind,
                     canonical_json(attributes or {}).decode(),now,now))
        self.ledger.append("resource.registered","resource",rid,{"capability_key":capability_key,"resource_key":resource_key})
        return rid

    def measure(self,resource_id:str,metric:str,*,value:float|None=None,text_value:str|None=None,
                unit:str|None=None,confidence:float=1.0,observation_id:str|None=None,observed_at:str|None=None)->str:
        if value is None and text_value is None:raise ValueError("measurement needs value or text")
        mid=new_id("measure")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO resource_measurements(measurement_id,resource_id,metric,value,text_value,unit,
                observed_at,confidence,observation_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (mid,resource_id,metric,value,text_value,unit,observed_at or utc_now(),confidence,observation_id,utc_now()))
        self.ledger.append("resource.measured","measurement",mid,{"resource_id":resource_id,"metric":metric})
        return mid

    def _latest_measurements(self,resource_id:str)->dict[str,float|str|None]:
        with self.db.connect() as con:
            rows=con.execute("""SELECT * FROM resource_measurements WHERE resource_id=?
                ORDER BY observed_at DESC, created_at DESC""",(resource_id,)).fetchall()
        out={}
        for r in rows:
            if r["metric"] not in out:
                out[r["metric"]]=r["value"] if r["value"] is not None else r["text_value"]
        return out

    def recommend(self,capability_key:str,*,required_attributes:dict[str,Any]|None=None,
                  max_cost:float|None=None,min_quality:float|None=None,max_latency_ms:float|None=None,
                  weights:dict[str,float]|None=None,limit:int=10)->list[ResourceRecommendation]:
        required_attributes=required_attributes or {}
        weights=weights or {"quality":.55,"cost":.25,"latency_ms":.10,"reliability":.10}
        with self.db.connect() as con:
            rows=con.execute("""SELECT r.* FROM resources r JOIN capabilities c ON c.capability_id=r.capability_id
                WHERE c.capability_key=? AND r.status='ACTIVE'""",(capability_key,)).fetchall()
        recs=[]
        for r in rows:
            attrs=json.loads(r["attributes_json"])
            if any(attrs.get(k)!=v for k,v in required_attributes.items()):continue
            m=self._latest_measurements(r["resource_id"])
            cost=m.get("cost")
            quality=m.get("quality")
            latency=m.get("latency_ms")
            reliability=m.get("reliability")
            # hard constraints: unknown does not silently pass a required threshold.
            if max_cost is not None and (not isinstance(cost,(int,float)) or cost>max_cost):continue
            if min_quality is not None and (not isinstance(quality,(int,float)) or quality<min_quality):continue
            if max_latency_ms is not None and (not isinstance(latency,(int,float)) or latency>max_latency_ms):continue
            score=0.0; reasons=[]
            if isinstance(quality,(int,float)):
                score+=weights.get("quality",0)*max(0,min(1,float(quality)));reasons.append(f"quality={quality}")
            if isinstance(cost,(int,float)):
                # Starter normalization only. Raw metrics remain canonical.
                score+=weights.get("cost",0)*(1/(1+max(0,float(cost))));reasons.append(f"cost={cost}")
            if isinstance(latency,(int,float)):
                score+=weights.get("latency_ms",0)*(1/(1+max(0,float(latency))/1000));reasons.append(f"latency_ms={latency}")
            if isinstance(reliability,(int,float)):
                score+=weights.get("reliability",0)*max(0,min(1,float(reliability)));reasons.append(f"reliability={reliability}")
            recs.append(ResourceRecommendation(r["resource_id"],r["name"],score,tuple(reasons),attrs,m))
        return sorted(recs,key=lambda x:(-x.score,x.name))[:limit]
