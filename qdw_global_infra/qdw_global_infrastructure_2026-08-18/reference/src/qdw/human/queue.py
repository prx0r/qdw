from __future__ import annotations
import json
from typing import Any
from qdw.core.core import canonical_json,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger

_ALLOWED = {
    "REQUESTED":{"APPROVED","DECLINED","CANCELLED"},
    "APPROVED":{"COMPLETED","CANCELLED"},
    "DECLINED":set(),
    "COMPLETED":set(),
    "CANCELLED":set(),
}

class HumanQueue:
    def __init__(self,db:Database,ledger:Ledger):
        self.db,self.ledger=db,ledger

    def request(self,action_type:str,title:str,instructions:dict[str,Any],*,idempotency_key:str,
                product_id:str|None=None,factory_run_id:str|None=None,work_node_id:str|None=None,
                estimated_cost_usd:float|None=None)->str:
        with self.db.tx(immediate=True) as con:
            old=con.execute("SELECT action_id FROM human_actions WHERE idempotency_key=?",(idempotency_key,)).fetchone()
            if old:return old["action_id"]
            aid=new_id("human")
            con.execute("""INSERT INTO human_actions(action_id,product_id,factory_run_id,work_node_id,action_type,status,
                title,instructions_json,estimated_cost_usd,requested_at,idempotency_key)
                VALUES(?,?,?,?,?,'REQUESTED',?,?,?,?,?)""",
                (aid,product_id,factory_run_id,work_node_id,action_type,title,
                 canonical_json(instructions).decode(),estimated_cost_usd,utc_now(),idempotency_key))
        self.ledger.append("human.requested","human_action",aid,
                           {"action_type":action_type,"product_id":product_id,"estimated_cost_usd":estimated_cost_usd})
        return aid

    def _transition(self,action_id:str,new_status:str,payload:dict[str,Any]|None=None)->None:
        with self.db.tx(immediate=True) as con:
            r=con.execute("SELECT status FROM human_actions WHERE action_id=?",(action_id,)).fetchone()
            if not r:raise KeyError(action_id)
            if new_status not in _ALLOWED.get(r["status"],set()):
                raise ValueError(f"invalid transition {r['status']} -> {new_status}")
            if new_status in {"APPROVED","DECLINED","CANCELLED"}:
                con.execute("""UPDATE human_actions SET status=?,decided_at=?,decision_json=? WHERE action_id=?""",
                    (new_status,utc_now(),canonical_json(payload or {}).decode(),action_id))
            elif new_status=="COMPLETED":
                con.execute("""UPDATE human_actions SET status=?,completed_at=?,result_json=? WHERE action_id=?""",
                    (new_status,utc_now(),canonical_json(payload or {}).decode(),action_id))
        self.ledger.append(f"human.{new_status.lower()}","human_action",action_id,payload or {})

    def approve(self,action_id:str,decision:dict[str,Any]|None=None): self._transition(action_id,"APPROVED",decision)
    def decline(self,action_id:str,decision:dict[str,Any]|None=None): self._transition(action_id,"DECLINED",decision)
    def complete(self,action_id:str,result:dict[str,Any]|None=None): self._transition(action_id,"COMPLETED",result)
    def cancel(self,action_id:str,reason:dict[str,Any]|None=None): self._transition(action_id,"CANCELLED",reason)

    def pending(self)->list[dict]:
        with self.db.connect() as con:
            rows=con.execute("""SELECT * FROM human_actions WHERE status IN ('REQUESTED','APPROVED')
                ORDER BY requested_at""").fetchall()
        out=[]
        for r in rows:
            d=dict(r);d["instructions"]=json.loads(d.pop("instructions_json"))
            if d.get("decision_json"):d["decision"]=json.loads(d["decision_json"])
            out.append(d)
        return out
