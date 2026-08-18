from __future__ import annotations
import json
from typing import Any
from qdw.core.core import canonical_json,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger

class WatchService:
    """Stores re-evaluation conditions. It does not silently mutate ideas."""

    def __init__(self,db:Database,ledger:Ledger):self.db,self.ledger=db,ledger

    def add(self,subject_type:str,subject_id:str,trigger_type:str,condition:dict[str,Any])->str:
        tid=new_id("watch")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO watch_triggers(trigger_id,subject_type,subject_id,trigger_type,condition_json,
                status,created_at) VALUES(?,?,?,?,?,'ACTIVE',?)""",
                (tid,subject_type,subject_id,trigger_type,canonical_json(condition).decode(),utc_now()))
        self.ledger.append("watch.created","watch_trigger",tid,{"subject_type":subject_type,"subject_id":subject_id})
        return tid

    def due_for_signal(self,signal:dict[str,Any])->list[dict]:
        """Generic exact-condition matcher; later policies can add domain-specific evaluators."""
        with self.db.connect() as con:
            rows=con.execute("SELECT * FROM watch_triggers WHERE status='ACTIVE'").fetchall()
        hits=[]
        for r in rows:
            cond=json.loads(r["condition_json"])
            if all(signal.get(k)==v for k,v in cond.items()):
                d=dict(r);d["condition"]=cond;hits.append(d)
        return hits

    def record_evaluation(self,trigger_id:str,result:dict[str,Any])->None:
        with self.db.tx(immediate=True) as con:
            con.execute("""UPDATE watch_triggers SET last_evaluated_at=?,last_result_json=? WHERE trigger_id=?""",
                        (utc_now(),canonical_json(result).decode(),trigger_id))
        self.ledger.append("watch.evaluated","watch_trigger",trigger_id,result)
