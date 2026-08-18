from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from qdw.core.core import hash_object,new_id,utc_now
from qdw.core.db import Database
from qdw.core.ledger.events import Ledger
from qdw.core.graph.store import WorkGraphStore

class ContractorRegistry:
    """Versioned global callable teams. Specialization is part of identity."""

    def __init__(self,db:Database,ledger:Ledger):
        self.db,self.ledger=db,ledger

    def register_manifest(self,path:str|Path)->tuple[str,str]:
        m=json.loads(Path(path).read_text(encoding="utf-8"))
        required={"contractor_id","version","team","specialization","inputs","outputs","gates"}
        missing=required-set(m)
        if missing:raise ValueError(f"missing {sorted(missing)}")
        h=hash_object(m)
        with self.db.tx(immediate=True) as con:
            old=con.execute("""SELECT manifest_hash FROM contractor_definitions WHERE contractor_id=? AND version=?""",
                            (m["contractor_id"],m["version"])).fetchone()
            if old and old["manifest_hash"]!=h:
                raise ValueError("contractor version immutable; bump version")
            con.execute("""INSERT OR IGNORE INTO contractor_definitions(contractor_id,version,team,specialization,
                manifest_hash,manifest_json,status,created_at) VALUES(?,?,?,?,?,?,'ACTIVE',?)""",
                (m["contractor_id"],m["version"],m["team"],m["specialization"],h,json.dumps(m,sort_keys=True),utc_now()))
        self.ledger.append("contractor.registered","contractor",m["contractor_id"],
                           {"version":m["version"],"manifest_hash":h})
        return m["contractor_id"],m["version"]

    def get(self,contractor_id:str,version:str|None=None)->dict[str,Any]:
        with self.db.connect() as con:
            if version:
                r=con.execute("""SELECT * FROM contractor_definitions WHERE contractor_id=? AND version=?""",
                              (contractor_id,version)).fetchone()
            else:
                r=con.execute("""SELECT * FROM contractor_definitions WHERE contractor_id=?
                    ORDER BY created_at DESC LIMIT 1""",(contractor_id,)).fetchone()
        if not r:raise KeyError(contractor_id)
        d=dict(r);d["manifest"]=json.loads(d.pop("manifest_json"));return d

    def expand_to_graph(self,graphs:WorkGraphStore,graph_id:str,contractor_id:str,*,depends_on:list[str]|None=None,
                        product_id:str|None=None,factory_run_id:str|None=None,priority:float=0)->str:
        d=self.get(contractor_id);m=d["manifest"]
        node=graphs.add_node(graph_id,"contractor.run",f"{m['team']}:{m['specialization']}",
            {"contractor_id":contractor_id,"contractor_version":m["version"],"product_id":product_id,
             "factory_run_id":factory_run_id,"inputs":m["inputs"],"outputs":m["outputs"],"gates":m["gates"]},
            priority=priority,expected_cost=float(m.get("default_budget_usd",.05)),expected_value=.2)
        for dep in depends_on or []:
            graphs.add_edge(graph_id,dep,node)
        return node
