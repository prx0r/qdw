"""WorkGraphStore v2 — frozen DAGs, atomic provenance, attempts and leases."""
from __future__ import annotations
import json
from datetime import UTC,datetime,timedelta
from typing import Any

from qdw.core import canonical_json,hash_object,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger

class WorkGraphStore:
    def __init__(self,db:Database,ledger:Ledger):
        self.db,self.ledger=db,ledger

    def _require_graph(self,con,graph_id:str,*states:str):
        row=con.execute("SELECT * FROM work_graphs WHERE graph_id=?",(graph_id,)).fetchone()
        if not row:raise KeyError(graph_id)
        if states and row["status"] not in states:
            raise RuntimeError(f"graph {graph_id} is {row['status']}, expected {states}")
        return row

    def create_graph(self,factory_run_id:str|None=None,graph_id:str|None=None)->str:
        gid=graph_id or new_id("graph")
        with self.db.tx(immediate=True) as con:
            con.execute("""INSERT INTO work_graphs(
                graph_id,factory_run_id,status,created_at,graph_hash,structure_hash,frozen_at,graph_revision
            ) VALUES(?,?,'DRAFT',?,NULL,NULL,NULL,1)""",(gid,factory_run_id,utc_now()))
            self.ledger.append_in_tx(con,"graph.created","work_graph",gid,{"factory_run_id":factory_run_id})
        return gid

    def add_node(self,graph_id:str,kind:str,title:str,payload:dict[str,Any],*,priority:float=0,
                 expected_value:float|None=None,expected_cost:float|None=None,
                 quality_floor:float|None=None,max_retries:int=2,
                 idempotency_key:str|None=None,node_id:str|None=None)->str:
        nid=node_id or new_id("node")
        now=utc_now()
        with self.db.tx(immediate=True) as con:
            self._require_graph(con,graph_id,"DRAFT")
            if idempotency_key:
                old=con.execute("SELECT node_id FROM work_nodes WHERE idempotency_key=?",(idempotency_key,)).fetchone()
                if old:return old["node_id"]
            con.execute("""INSERT INTO work_nodes(
                node_id,graph_id,kind,title,state,priority,expected_value,expected_cost,quality_floor,
                max_retries,idempotency_key,payload_json,created_at,updated_at
            ) VALUES(?,?,?,?, 'PENDING',?,?,?,?,?,?,?,?,?)""",
            (nid,graph_id,kind,title,priority,expected_value,expected_cost,quality_floor,max_retries,
             idempotency_key,canonical_json(payload).decode(),now,now))
            self.ledger.append_in_tx(con,"node.created","work_node",nid,{
                "graph_id":graph_id,"kind":kind,"title":title,
            })
        return nid

    @staticmethod
    def _cycles(nodes:set[str],edges:list[tuple[str,str]])->list[list[str]]:
        adj={n:[] for n in nodes}
        for a,b in edges:
            if a in adj:adj[a].append(b)
        white,gray,black=0,1,2
        color={n:white for n in nodes}
        stack=[];cycles=[]
        def dfs(u):
            color[u]=gray;stack.append(u)
            for v in adj.get(u,()):
                if v not in color:continue
                if color[v]==white:dfs(v)
                elif color[v]==gray:
                    i=stack.index(v) if v in stack else 0
                    cycles.append(stack[i:]+[v])
            stack.pop();color[u]=black
        for n in sorted(nodes):
            if color[n]==white:dfs(n)
        return cycles

    def add_edge(self,graph_id:str,from_node:str,to_node:str,relation:str="blocks")->None:
        if from_node==to_node:raise ValueError("self dependency")
        with self.db.tx(immediate=True) as con:
            self._require_graph(con,graph_id,"DRAFT")
            rows=con.execute("SELECT node_id FROM work_nodes WHERE graph_id=?",(graph_id,)).fetchall()
            nodes={r["node_id"] for r in rows}
            if from_node not in nodes or to_node not in nodes:
                raise ValueError("edge nodes must belong to graph")
            current=[(r["from_node"],r["to_node"]) for r in con.execute(
                "SELECT from_node,to_node FROM work_edges WHERE graph_id=? AND relation='blocks'",(graph_id,)
            ).fetchall()]
            proposed=current+([(from_node,to_node)] if relation=="blocks" else [])
            cycles=self._cycles(nodes,proposed)
            if cycles:
                raise ValueError("adding edge creates cycle: "+" -> ".join(cycles[0]))
            con.execute("""INSERT OR IGNORE INTO work_edges(
                graph_id,from_node,to_node,relation
            ) VALUES(?,?,?,?)""",(graph_id,from_node,to_node,relation))
            self.ledger.append_in_tx(con,"edge.created","work_graph",graph_id,{
                "from_node":from_node,"to_node":to_node,"relation":relation,
            })

    def validate_dag(self,graph_id:str)->list[str]:
        with self.db.connect() as con:
            nodes={r["node_id"] for r in con.execute(
                "SELECT node_id FROM work_nodes WHERE graph_id=?",(graph_id,)
            ).fetchall()}
            edges=[(r["from_node"],r["to_node"]) for r in con.execute(
                "SELECT from_node,to_node FROM work_edges WHERE graph_id=? AND relation='blocks'",(graph_id,)
            ).fetchall()]
        return [" -> ".join(x) for x in self._cycles(nodes,edges)]

    def freeze(self,graph_id:str)->str:
        with self.db.tx(immediate=True) as con:
            self._require_graph(con,graph_id,"DRAFT")
            nodes=[dict(r) for r in con.execute("""SELECT node_id,kind,title,priority,expected_value,
                expected_cost,quality_floor,max_retries,idempotency_key,payload_json
                FROM work_nodes WHERE graph_id=? ORDER BY node_id""",(graph_id,)).fetchall()]
            edges=[dict(r) for r in con.execute("""SELECT from_node,to_node,relation FROM work_edges
                WHERE graph_id=? ORDER BY from_node,to_node,relation""",(graph_id,)).fetchall()]
            cycles=self._cycles({x["node_id"] for x in nodes},[(x["from_node"],x["to_node"]) for x in edges if x["relation"]=="blocks"])
            if cycles:raise ValueError("cannot freeze cyclic graph")
            structure_hash=hash_object({"nodes":nodes,"edges":edges})
            now=utc_now()
            con.execute("""UPDATE work_graphs SET status='FROZEN',graph_hash=?,structure_hash=?,frozen_at=?
                WHERE graph_id=?""",(structure_hash,structure_hash,now,graph_id))
            self.ledger.append_in_tx(con,"graph.frozen","work_graph",graph_id,{"structure_hash":structure_hash})
        return structure_hash

    def refresh_ready(self,graph_id:str)->int:
        now=utc_now()
        with self.db.tx(immediate=True) as con:
            graph=self._require_graph(con,graph_id,"FROZEN","RUNNING")
            if graph["status"]=="FROZEN":
                con.execute("UPDATE work_graphs SET status='RUNNING' WHERE graph_id=?",(graph_id,))
                self.ledger.append_in_tx(con,"graph.started","work_graph",graph_id,{})
            rows=con.execute("""SELECT n.node_id FROM work_nodes n
                WHERE n.graph_id=? AND n.state IN ('PENDING','RETRY_WAIT')
                AND NOT EXISTS(
                    SELECT 1 FROM work_edges e
                    JOIN work_nodes blocker ON blocker.node_id=e.from_node
                    WHERE e.graph_id=n.graph_id AND e.to_node=n.node_id
                      AND e.relation='blocks' AND blocker.state!='SUCCEEDED'
                )""",(graph_id,)).fetchall()
            for r in rows:
                con.execute("UPDATE work_nodes SET state='READY',updated_at=? WHERE node_id=?",(now,r["node_id"]))
                self.ledger.append_in_tx(con,"node.ready","work_node",r["node_id"],{"graph_id":graph_id})
        return len(rows)

    def claim_ready(self,worker_id:str,lease_seconds:int=900,graph_id:str|None=None):
        from qdw.core.graph.scheduler import Candidate,choose
        with self.db.connect() as con:
            params=[];where="state='READY'"
            if graph_id:
                graph=con.execute("SELECT status FROM work_graphs WHERE graph_id=?",(graph_id,)).fetchone()
                if not graph or graph["status"]!="RUNNING":
                    raise RuntimeError("graph not RUNNING")
                where+=" AND graph_id=?";params.append(graph_id)
            rows=con.execute(f"SELECT * FROM work_nodes WHERE {where} ORDER BY created_at",params).fetchall()
        if not rows:return None
        candidates=[Candidate(
            r["node_id"],r["expected_value"],r["expected_cost"],1.0,0.0,0.0
        ) for r in rows]
        chosen=choose(candidates)
        if chosen is None:return None
        now=datetime.now(UTC)
        now_s=now.isoformat().replace("+00:00","Z")
        until=(now+timedelta(seconds=lease_seconds)).isoformat().replace("+00:00","Z")
        with self.db.tx(immediate=True) as con:
            changed=con.execute("""UPDATE work_nodes SET state='LEASED',lease_owner=?,lease_until=?,
                attempt_count=attempt_count+1,updated_at=? WHERE node_id=? AND state='READY'""",
                (worker_id,until,now_s,chosen.node_id)).rowcount
            if changed!=1:return None
            row=con.execute("SELECT * FROM work_nodes WHERE node_id=?",(chosen.node_id,)).fetchone()
            attempt_id=new_id("attempt")
            con.execute("""INSERT INTO work_attempts(
                attempt_id,node_id,attempt_no,worker_id,lease_started_at,lease_until,status
            ) VALUES(?,?,?,?,?,?,'LEASED')""",
            (attempt_id,row["node_id"],row["attempt_count"],worker_id,now_s,until))
            self.ledger.append_in_tx(con,"node.claimed","work_node",row["node_id"],{
                "worker_id":worker_id,"lease_until":until,"attempt_id":attempt_id,
            })
            claimed=dict(row)
        claimed["payload"]=json.loads(claimed.pop("payload_json"))
        claimed["attempt_id"]=attempt_id
        return claimed

    def start(self,node_id:str,worker_id:str)->None:
        with self.db.tx(immediate=True) as con:
            n=con.execute("SELECT state,lease_owner,attempt_count FROM work_nodes WHERE node_id=?",(node_id,)).fetchone()
            if not n or n["state"]!="LEASED" or n["lease_owner"]!=worker_id:raise RuntimeError("invalid lease")
            now=utc_now()
            con.execute("UPDATE work_nodes SET state='RUNNING',updated_at=? WHERE node_id=?",(now,node_id))
            con.execute("""UPDATE work_attempts SET status='RUNNING',started_at=?
                WHERE node_id=? AND attempt_no=?""",(now,node_id,n["attempt_count"]))
            self.ledger.append_in_tx(con,"node.started","work_node",node_id,{"worker_id":worker_id})

    def verifying(self,node_id:str)->None:
        with self.db.tx(immediate=True) as con:
            n=con.execute("SELECT state,attempt_count FROM work_nodes WHERE node_id=?",(node_id,)).fetchone()
            if not n or n["state"]!="RUNNING":raise RuntimeError("node not RUNNING")
            now=utc_now()
            con.execute("UPDATE work_nodes SET state='VERIFYING',updated_at=? WHERE node_id=?",(now,node_id))
            con.execute("""UPDATE work_attempts SET status='VERIFYING'
                WHERE node_id=? AND attempt_no=?""",(node_id,n["attempt_count"]))
            self.ledger.append_in_tx(con,"node.verifying","work_node",node_id,{})

    def complete(self,node_id:str,result:dict[str,Any])->None:
        with self.db.tx(immediate=True) as con:
            n=con.execute("SELECT state,attempt_count,graph_id FROM work_nodes WHERE node_id=?",(node_id,)).fetchone()
            if not n or n["state"]!="VERIFYING":raise RuntimeError("node not VERIFYING")
            now=utc_now();rh=hash_object(result)
            con.execute("""UPDATE work_nodes SET state='SUCCEEDED',result_json=?,lease_owner=NULL,
                lease_until=NULL,updated_at=? WHERE node_id=?""",(canonical_json(result).decode(),now,node_id))
            con.execute("""UPDATE work_attempts SET status='SUCCEEDED',finished_at=?,result_hash=?
                WHERE node_id=? AND attempt_no=?""",(now,rh,node_id,n["attempt_count"]))
            self.ledger.append_in_tx(con,"node.succeeded","work_node",node_id,{"result_hash":rh})
            self._maybe_finish_graph_in_tx(con,n["graph_id"])

    def fail(self,node_id:str,failure:dict[str,Any],retryable:bool)->str:
        with self.db.tx(immediate=True) as con:
            n=con.execute("""SELECT state,attempt_count,max_retries,graph_id FROM work_nodes
                WHERE node_id=?""",(node_id,)).fetchone()
            if not n:raise KeyError(node_id)
            if n["state"] not in {"LEASED","RUNNING","VERIFYING"}:
                raise RuntimeError(f"illegal failure from {n['state']}")
            state="RETRY_WAIT" if retryable and n["attempt_count"]<n["max_retries"] else "FAILED"
            now=utc_now();fh=hash_object(failure)
            con.execute("""UPDATE work_nodes SET state=?,result_json=?,lease_owner=NULL,lease_until=NULL,
                updated_at=? WHERE node_id=?""",(state,canonical_json(failure).decode(),now,node_id))
            con.execute("""UPDATE work_attempts SET status='FAILED',finished_at=?,failure_hash=?
                WHERE node_id=? AND attempt_no=?""",(now,fh,node_id,n["attempt_count"]))
            self.ledger.append_in_tx(con,"node.failed","work_node",node_id,{
                "state":state,"failure_hash":fh,"retryable":retryable,
            })
            if state=="FAILED":
                self._maybe_finish_graph_in_tx(con,n["graph_id"])
        return state

    def reclaim_stale(self,now:datetime|None=None)->int:
        now=now or datetime.now(UTC);now_s=now.isoformat().replace("+00:00","Z")
        count=0
        with self.db.tx(immediate=True) as con:
            rows=con.execute("""SELECT node_id,attempt_count,max_retries,graph_id FROM work_nodes
                WHERE state IN ('LEASED','RUNNING') AND lease_until IS NOT NULL AND lease_until<?""",(now_s,)).fetchall()
            for n in rows:
                terminal=n["attempt_count"]>=n["max_retries"]
                state="FAILED" if terminal else "READY"
                con.execute("""UPDATE work_nodes SET state=?,lease_owner=NULL,lease_until=NULL,updated_at=?
                    WHERE node_id=?""",(state,now_s,n["node_id"]))
                con.execute("""UPDATE work_attempts SET status='EXPIRED',finished_at=?
                    WHERE node_id=? AND attempt_no=?""",(now_s,n["node_id"],n["attempt_count"]))
                self.ledger.append_in_tx(con,
                    "node.lease_expired_failed" if terminal else "node.lease_reclaimed",
                    "work_node",n["node_id"],{"attempt_count":n["attempt_count"]})
                if terminal:
                    self._maybe_finish_graph_in_tx(con,n["graph_id"])
                count+=1
        return count

    def _maybe_finish_graph_in_tx(self,con,graph_id:str)->None:
        pending=con.execute("""SELECT COUNT(*) n FROM work_nodes WHERE graph_id=?
            AND state NOT IN ('SUCCEEDED','FAILED')""",(graph_id,)).fetchone()["n"]
        if pending:return
        failed=con.execute(
            "SELECT COUNT(*) n FROM work_nodes WHERE graph_id=? AND state='FAILED'",(graph_id,)
        ).fetchone()["n"]
        status="FAILED" if failed else "SUCCEEDED"
        current=con.execute("SELECT status FROM work_graphs WHERE graph_id=?",(graph_id,)).fetchone()
        if current and current["status"]!=status:
            con.execute("UPDATE work_graphs SET status=? WHERE graph_id=?",(status,graph_id))
            self.ledger.append_in_tx(con,"graph.finished","work_graph",graph_id,{"status":status})
