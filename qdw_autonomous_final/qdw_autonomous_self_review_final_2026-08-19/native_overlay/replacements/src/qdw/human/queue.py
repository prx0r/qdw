"""HumanQueue v2 — strict state machine, atomic provenance and approval payload binding."""
from __future__ import annotations
import json
from typing import Any
from qdw.core import canonical_json,hash_object,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger

_ALLOWED={
    "REQUESTED":{"APPROVED","DECLINED","CANCELLED"},
    "APPROVED":{"COMPLETED","CANCELLED"},
    "DECLINED":set(),"COMPLETED":set(),"CANCELLED":set(),
}

class HumanQueue:
    def __init__(self,db:Database,ledger:Ledger):
        self.db,self.ledger=db,ledger

    @staticmethod
    def action_payload(*,action_type,title,instructions,product_id=None,factory_run_id=None,
                       work_node_id=None,estimated_cost_usd=None)->dict:
        return {
            "action_type":action_type,"title":title,"instructions":instructions,
            "product_id":product_id,"factory_run_id":factory_run_id,"work_node_id":work_node_id,
            "estimated_cost_usd":estimated_cost_usd,
        }

    def request(self,action_type:str,title:str,instructions:dict[str,Any],*,idempotency_key:str,
                product_id:str|None=None,factory_run_id:str|None=None,work_node_id:str|None=None,
                estimated_cost_usd:float|None=None)->str:
        payload=self.action_payload(
            action_type=action_type,title=title,instructions=instructions,product_id=product_id,
            factory_run_id=factory_run_id,work_node_id=work_node_id,estimated_cost_usd=estimated_cost_usd,
        )
        payload_hash=hash_object(payload)
        with self.db.tx(immediate=True) as con:
            old=con.execute("SELECT action_id,request_payload_hash FROM human_actions WHERE idempotency_key=?",
                            (idempotency_key,)).fetchone()
            if old:
                if old["request_payload_hash"]!=payload_hash:
                    raise ValueError("idempotency key reused with different payload")
                return old["action_id"]
            aid=new_id("human")
            con.execute("""INSERT INTO human_actions(
                action_id,product_id,factory_run_id,work_node_id,action_type,status,title,instructions_json,
                estimated_cost_usd,requested_at,idempotency_key,request_payload_hash
            ) VALUES(?,?,?,?,?,'REQUESTED',?,?,?,?,?,?)""",
            (aid,product_id,factory_run_id,work_node_id,action_type,title,
             canonical_json(instructions).decode(),estimated_cost_usd,utc_now(),idempotency_key,payload_hash))
            self.ledger.append_in_tx(con,"human.requested","human_action",aid,{
                "action_type":action_type,"request_payload_hash":payload_hash,
            })
        return aid

    def _transition(self,action_id,new_status,payload=None,*,actor_id:str)->None:
        if not actor_id or not actor_id.strip():raise ValueError("actor_id required")
        with self.db.tx(immediate=True) as con:
            row=con.execute("SELECT * FROM human_actions WHERE action_id=?",(action_id,)).fetchone()
            if not row:raise KeyError(action_id)
            if new_status not in _ALLOWED.get(row["status"],set()):
                raise ValueError(f"invalid transition {row['status']} -> {new_status}")
            now=utc_now()
            if new_status in {"APPROVED","DECLINED","CANCELLED"}:
                con.execute("""UPDATE human_actions SET status=?,decided_at=?,decision_json=?,
                    decision_actor=?,approved_payload_hash=? WHERE action_id=?""",
                    (new_status,now,canonical_json(payload or {}).decode(),actor_id,
                     row["request_payload_hash"] if new_status=="APPROVED" else None,action_id))
            else:
                con.execute("""UPDATE human_actions SET status=?,completed_at=?,result_json=?
                    WHERE action_id=?""",(new_status,now,canonical_json(payload or {}).decode(),action_id))
            self.ledger.append_in_tx(con,f"human.{new_status.lower()}","human_action",action_id,{
                "actor_id":actor_id,"request_payload_hash":row["request_payload_hash"],
                **(payload or {}),
            })

    def approve(self,action_id,actor_id,decision=None):self._transition(action_id,"APPROVED",decision,actor_id=actor_id)
    def decline(self,action_id,actor_id,decision=None):self._transition(action_id,"DECLINED",decision,actor_id=actor_id)
    def complete(self,action_id,actor_id,result=None):self._transition(action_id,"COMPLETED",result,actor_id=actor_id)
    def cancel(self,action_id,actor_id,reason=None):self._transition(action_id,"CANCELLED",reason,actor_id=actor_id)

    def require_approved(self,action_id:str,*,expected_payload:dict[str,Any])->dict:
        expected=hash_object(expected_payload)
        with self.db.connect() as con:
            row=con.execute("SELECT * FROM human_actions WHERE action_id=?",(action_id,)).fetchone()
        if not row:raise KeyError(action_id)
        if row["status"] not in {"APPROVED","COMPLETED"}:raise ValueError("action not approved")
        if row["approved_payload_hash"]!=expected:
            raise ValueError("APPROVAL_PAYLOAD_MISMATCH")
        return dict(row)

    def pending(self):
        with self.db.connect() as con:
            rows=con.execute("""SELECT * FROM human_actions WHERE status IN ('REQUESTED','APPROVED')
                ORDER BY requested_at""").fetchall()
        out=[]
        for row in rows:
            d=dict(row);d["instructions"]=json.loads(d.pop("instructions_json"))
            if d.get("decision_json"):d["decision"]=json.loads(d["decision_json"])
            out.append(d)
        return out
