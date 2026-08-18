from __future__ import annotations
from dataclasses import dataclass
from ..core import new_id,utc_now
from ..db import Database

@dataclass(frozen=True)
class CostEvent:
    category:str
    amount_usd:float
    provider:str|None=None
    quantity:float|None=None
    unit:str|None=None
    evidence_ref:str|None=None

class CostLedger:
    def __init__(self,db:Database):self.db=db
    def record(self,e:CostEvent,factory_run_id:str|None=None,node_id:str|None=None)->str:
        if e.amount_usd<0:raise ValueError("negative cost")
        cid=new_id("cost")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO cost_events(cost_event_id,factory_run_id,node_id,category,provider,
                amount_usd,quantity,unit,occurred_at,evidence_ref) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (cid,factory_run_id,node_id,e.category,e.provider,e.amount_usd,e.quantity,e.unit,utc_now(),e.evidence_ref))
        return cid
    def total_for_run(self,run_id:str)->float:
        with self.db.connect() as con:
            r=con.execute("""SELECT COALESCE(SUM(amount_usd),0) n FROM cost_events
                WHERE factory_run_id=?""",(run_id,)).fetchone()
        return float(r["n"])
